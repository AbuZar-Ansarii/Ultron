"""
actions/android_bridge.py — Android Mobile Bridge & Fastboot Controller for Ultron AI.

Provides full control over connected Android devices:
  - List connected devices in ADB or Fastboot mode
  - Device info (model, Android version, battery level, storage, IP)
  - Reboot device into recovery, bootloader, fastboot, edl, or system
  - Push files (e.g. TWRP recoveries, Magisk zips, ROMs) straight to /sdcard/Download/
  - Pull files from phone to PC
  - Install APKs directly
  - Zero-latency phone screen mirroring via scrcpy
  - Capture phone screenshots to PC
  - Fastboot partition flashing
  - Custom shell commands
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path


def _resolve_pc_path(raw: str) -> Path:
    raw = (raw or "").strip().strip('"').strip("'")
    if not raw:
        return Path.home() / "Downloads"

    shortcuts = {
        "desktop": Path.home() / "Desktop",
        "downloads": Path.home() / "Downloads",
        "documents": Path.home() / "Documents",
        "pictures": Path.home() / "Pictures",
        "home": Path.home(),
    }
    lower = raw.lower()
    if lower in shortcuts:
        return shortcuts[lower]

    head, sep, rest = raw.replace("\\", "/").partition("/")
    if sep and head.lower() in shortcuts:
        return shortcuts[head.lower()] / rest if rest else shortcuts[head.lower()]

    return Path(raw).expanduser()


def _find_binary(name: str) -> str:
    """Find binary executable from PATH or standard Windows install directories."""
    found = shutil.which(name)
    if found:
        return found

    candidates = {
        "adb": [
            r"C:\platform-tools\adb.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
            r"C:\Program Files (x86)\Minimal ADB and Fastboot\adb.exe",
        ],
        "fastboot": [
            r"C:\platform-tools\fastboot.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\fastboot.exe"),
            r"C:\Program Files (x86)\Minimal ADB and Fastboot\fastboot.exe",
        ],
        "scrcpy": [
            r"C:\scrcpy-win64-v4.0\scrcpy.exe",
            r"C:\scrcpy\scrcpy.exe",
            r"C:\Program Files\scrcpy\scrcpy.exe",
        ],
    }
    for cand in candidates.get(name.lower(), []):
        if os.path.exists(cand):
            return cand
    return name


def _run_cmd(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Execute a binary command safely with timeout and UTF-8 decode."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return -1, "", str(e)


# ── Action Handlers ──────────────────────────────────────────────────────────

def list_devices() -> str:
    adb_bin = _find_binary("adb")
    fb_bin = _find_binary("fastboot")

    code, out, err = _run_cmd([adb_bin, "devices", "-l"])
    fb_code, fb_out, fb_err = _run_cmd([fb_bin, "devices"])

    lines = []
    # Parse ADB
    adb_devices = []
    if code == 0 and out:
        for line in out.splitlines()[1:]:
            line = line.strip()
            if not line or line.startswith("*"):
                continue
            parts = line.split()
            dev_id = parts[0]
            status = parts[1] if len(parts) > 1 else "unknown"
            details = " ".join(parts[2:]) if len(parts) > 2 else ""
            adb_devices.append(f"📱 ADB: {dev_id} [{status}] {details}")

    # Parse Fastboot
    fb_devices = []
    if fb_code == 0 and fb_out:
        for line in fb_out.splitlines():
            line = line.strip()
            if line:
                fb_devices.append(f"⚡ Fastboot: {line}")

    if not adb_devices and not fb_devices:
        return (
            "No Android devices detected.\n"
            "Ensure your phone is plugged in with USB debugging enabled, "
            "or put into Fastboot mode."
        )

    res = "Connected Mobile Devices:\n"
    if adb_devices:
        res += "\n".join(adb_devices) + "\n"
    if fb_devices:
        res += "\n".join(fb_devices) + "\n"
    return res.strip()


def get_device_info() -> str:
    adb_bin = _find_binary("adb")
    code, out, _ = _run_cmd([adb_bin, "get-state"])
    if code != 0 or out != "device":
        # Check if in fastboot
        fb_bin = _find_binary("fastboot")
        _, fb_out, _ = _run_cmd([fb_bin, "devices"])
        if fb_out:
            return f"Device is in Fastboot / Bootloader mode: {fb_out}"
        return "No authorized ADB device connected. Unlock phone and tap 'Allow USB debugging'."

    # Query properties
    queries = {
        "Model": [adb_bin, "shell", "getprop", "ro.product.model"],
        "Brand": [adb_bin, "shell", "getprop", "ro.product.brand"],
        "Codename": [adb_bin, "shell", "getprop", "ro.product.device"],
        "Android Version": [adb_bin, "shell", "getprop", "ro.build.version.release"],
        "Security Patch": [adb_bin, "shell", "getprop", "ro.build.version.security_patch"],
    }
    info = {}
    for label, cmd in queries.items():
        _, val, _ = _run_cmd(cmd, timeout=5)
        info[label] = val or "Unknown"

    # Query battery
    _, b_out, _ = _run_cmd([adb_bin, "shell", "dumpsys", "battery"], timeout=5)
    level = re.search(r"level:\s*(\d+)", b_out)
    status = re.search(r"status:\s*(\d+)", b_out)
    if level:
        info["Battery"] = f"{level.group(1)}%"
        if status and status.group(1) == "2":
            info["Battery"] += " (Charging)"

    # Query storage
    _, df_out, _ = _run_cmd([adb_bin, "shell", "df", "-h", "/sdcard"], timeout=5)
    for line in df_out.splitlines():
        if "/sdcard" in line or "/storage" in line or "emulated" in line:
            parts = line.split()
            if len(parts) >= 5:
                info["Internal Storage Free"] = f"{parts[3]} of {parts[1]}"
            break

    # Query IP
    _, ip_out, _ = _run_cmd([adb_bin, "shell", "ip", "-f", "inet", "addr", "show", "wlan0"], timeout=5)
    ip_match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", ip_out)
    if ip_match:
        info["Wi-Fi IP"] = ip_match.group(1)

    lines = [f"{k}: {v}" for k, v in info.items()]
    return "📱 Android Device Telemetry:\n" + "\n".join(f"  • {line}" for line in lines)


def reboot_device(target: str = "system") -> str:
    target = (target or "system").lower().strip()
    adb_bin = _find_binary("adb")
    fb_bin = _find_binary("fastboot")

    # If currently in fastboot
    _, fb_out, _ = _run_cmd([fb_bin, "devices"], timeout=5)
    if fb_out:
        if target in ("bootloader", "fastboot"):
            _run_cmd([fb_bin, "reboot-bootloader"], timeout=10)
            return "Rebooting bootloader in Fastboot mode."
        elif target == "recovery":
            _run_cmd([fb_bin, "reboot", "recovery"], timeout=10)
            return "Rebooting into Recovery from Fastboot."
        else:
            _run_cmd([fb_bin, "reboot"], timeout=10)
            return "Rebooting Android device into system."

    # ADB reboot targets
    if target in ("recovery", "bootloader", "fastboot", "edl", "sideload"):
        code, out, err = _run_cmd([adb_bin, "reboot", target], timeout=15)
        if code == 0:
            return f"Command sent: Device is now rebooting into {target.upper()} mode."
        return f"Failed to reboot into {target}: {err or out}"
    else:
        code, out, err = _run_cmd([adb_bin, "reboot"], timeout=15)
        if code == 0:
            return "Command sent: Device is rebooting into Android system."
        return f"Reboot failed: {err or out}"


def push_file(pc_path: str, phone_path: str = "/sdcard/Download/") -> str:
    source = _resolve_pc_path(pc_path)
    if not source.exists():
        return f"Local source file not found: {source}"

    adb_bin = _find_binary("adb")
    dest = (phone_path or "/sdcard/Download/").strip()
    if not dest.endswith("/"):
        dest += "/"

    code, out, err = _run_cmd([adb_bin, "push", str(source), dest], timeout=120)
    if code == 0:
        return f"Successfully pushed '{source.name}' to phone '{dest}'."
    return f"Failed to push file: {err or out}"


def pull_file(phone_path: str, pc_dest: str = "downloads") -> str:
    target_dir = _resolve_pc_path(pc_dest)
    target_dir.mkdir(parents=True, exist_ok=True)

    adb_bin = _find_binary("adb")
    code, out, err = _run_cmd([adb_bin, "pull", phone_path, str(target_dir)], timeout=120)
    if code == 0:
        return f"Successfully pulled '{phone_path}' to '{target_dir}'."
    return f"Failed to pull file: {err or out}"


def install_apk(apk_path: str) -> str:
    source = _resolve_pc_path(apk_path)
    if not source.exists() or source.suffix.lower() != ".apk":
        return f"APK file not found or invalid: {source}"

    adb_bin = _find_binary("adb")
    code, out, err = _run_cmd([adb_bin, "install", "-r", str(source)], timeout=180)
    if code == 0 and "Success" in out:
        return f"Successfully installed '{source.name}' on device."
    return f"APK installation failed: {err or out}"


def mirror_screen() -> str:
    scrcpy_bin = _find_binary("scrcpy")
    if not os.path.exists(scrcpy_bin) and not shutil.which("scrcpy"):
        return (
            "scrcpy executable not found. "
            "Please ensure scrcpy is installed at C:\\scrcpy-win64-v4.0\\ or on PATH."
        )

    try:
        subprocess.Popen(
            [scrcpy_bin, "--window-title=Ultron Mobile Mirror", "--always-on-top"],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        )
        return "Ultron Mobile Mirror (scrcpy) launched successfully."
    except Exception as e:
        return f"Could not launch scrcpy: {e}"


def take_screenshot(pc_dest: str = "downloads") -> str:
    dest_dir = _resolve_pc_path(pc_dest)
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"phone_screenshot_{int(time.time())}.png"
    target_file = dest_dir / filename

    adb_bin = _find_binary("adb")
    try:
        with open(target_file, "wb") as f:
            proc = subprocess.run([adb_bin, "exec-out", "screencap", "-p"], stdout=f, timeout=15)
        if proc.returncode == 0 and target_file.exists() and target_file.stat().st_size > 1000:
            return f"Phone screenshot captured and saved to '{target_file}'."
        target_file.unlink(missing_ok=True)
        return "Failed to capture phone screenshot."
    except Exception as e:
        return f"Screenshot error: {e}"


def flash_partition(partition: str, image_path: str) -> str:
    partition = (partition or "").strip().lower()
    if not partition:
        return "Must specify target partition (e.g. recovery, boot)."

    source = _resolve_pc_path(image_path)
    if not source.exists():
        return f"Image file not found: {source}"

    fb_bin = _find_binary("fastboot")
    _, fb_out, _ = _run_cmd([fb_bin, "devices"], timeout=5)
    if not fb_out:
        return "Device is not in Fastboot mode! Reboot phone to bootloader first."

    code, out, err = _run_cmd([fb_bin, "flash", partition, str(source)], timeout=90)
    if code == 0:
        return f"Fastboot: Partition '{partition}' successfully flashed with '{source.name}'."
    return f"Fastboot flash failed: {err or out}"


def run_shell(command: str) -> str:
    command = (command or "").strip()
    if not command:
        return "No shell command specified."

    adb_bin = _find_binary("adb")
    code, out, err = _run_cmd([adb_bin, "shell", command], timeout=30)
    output = out or err or "(no output)"
    if len(output) > 800:
        output = output[:800] + "... [truncated]"
    return f"ADB Shell Output:\n{output}"


# ── Unified Dispatcher ───────────────────────────────────────────────────────

def android_bridge(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "devices").lower().strip()
    file_path = params.get("file_path", "")
    phone_path = params.get("phone_path", "/sdcard/Download/")
    target = params.get("target", "system")
    partition = params.get("partition", "recovery")
    command = params.get("command", "")

    if player:
        player.write_log(f"[android] {action} {file_path or target or ''}")

    try:
        if action in ("devices", "list", "status"):
            return list_devices()
        elif action in ("info", "battery", "telemetry"):
            return get_device_info()
        elif action == "reboot":
            return reboot_device(target)
        elif action == "push":
            return push_file(file_path, phone_path)
        elif action == "pull":
            return pull_file(phone_path, file_path or "downloads")
        elif action == "install":
            return install_apk(file_path)
        elif action in ("mirror", "scrcpy", "screen_mirror"):
            return mirror_screen()
        elif action == "screenshot":
            return take_screenshot(file_path or "downloads")
        elif action == "flash":
            return flash_partition(partition, file_path)
        elif action == "shell":
            return run_shell(command)
        else:
            return f"Unknown Android action: '{action}'. Available: devices, info, reboot, push, pull, install, mirror, screenshot, flash, shell."
    except Exception as e:
        return f"Android Bridge error ({action}): {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "android_bridge",
    "description": "Controls connected Android mobile devices via ADB & Fastboot: list devices, check device telemetry/battery/storage/model, push/pull files (e.g. TWRP recoveries, Magisk, ROMs), install APKs, reboot into recovery/bootloader/EDL, flash partitions with fastboot, capture phone screenshots, and launch zero-latency phone screen mirroring (scrcpy).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "devices | info | reboot | push | pull | install | mirror | screenshot | flash | shell"
            },
            "target": {
                "type": "STRING",
                "description": "Reboot target: recovery | bootloader | fastboot | edl | system"
            },
            "file_path": {
                "type": "STRING",
                "description": "Path on PC for push/install/flash/pull (e.g. downloads/twrp-3.7.0_9-0-fajita.img, or APK path)"
            },
            "phone_path": {
                "type": "STRING",
                "description": "Path on phone for push/pull (defaults to /sdcard/Download/)"
            },
            "partition": {
                "type": "STRING",
                "description": "Partition for fastboot flash action (e.g. recovery, boot)"
            },
            "command": {
                "type": "STRING",
                "description": "Command string for shell action (e.g. input keyevent 26, getprop)"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": android_bridge,
}
