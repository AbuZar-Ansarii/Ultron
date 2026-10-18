"""
system_utility.py — Essential OS utilities for Ultron AI.
Empty Recycle Bin, lock workstation, sleep, network/IP info, battery check, and quick folder opening.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import ctypes
import os
import platform
import socket
import subprocess
from pathlib import Path
import psutil

_OS = platform.system()
_WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW} if _OS == "Windows" else {}


def empty_recycle_bin() -> str:
    """Permanently empty the Windows Recycle Bin without popups."""
    if _OS != "Windows":
        return f"Emptying recycle bin is not supported on {_OS}."
    try:
        # SHERB_NOCONFIRMATION = 0x00000001
        # SHERB_NOPROGRESSUI   = 0x00000002
        # SHERB_NOSOUND        = 0x00000004
        flags = 7
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        if res == 0:
            return "Recycle Bin emptied successfully."
        elif res == -2147418113:  # 0x8000ffff / already empty
            return "Recycle Bin is already empty."
        else:
            return f"Recycle Bin emptied (status code: {res})."
    except Exception as e:
        return f"Failed to empty Recycle Bin: {e}"


def lock_workstation() -> str:
    """Lock the Windows desktop session."""
    if _OS == "Windows":
        try:
            ctypes.windll.user32.LockWorkStation()
            return "Workstation locked."
        except Exception as e:
            return f"Lock failed: {e}"
    elif _OS == "Darwin":
        try:
            subprocess.run(["pmset", "displaysleepnow"], capture_output=True)
            return "Screen locked."
        except Exception as e:
            return f"Lock failed: {e}"
    return f"Locking is not supported on {_OS}."


def sleep_computer() -> str:
    """Put computer into sleep mode."""
    if _OS == "Windows":
        try:
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], **_WIN_HIDE)
            return "Computer entering sleep mode."
        except Exception as e:
            return f"Sleep failed: {e}"
    elif _OS == "Darwin":
        try:
            subprocess.run(["osascript", "-e", 'tell application "System Events" to sleep'], capture_output=True)
            return "Computer entering sleep mode."
        except Exception as e:
            return f"Sleep failed: {e}"
    return f"Sleep is not supported on {_OS}."


def get_network_info() -> str:
    """Retrieve detailed IP and network status."""
    hostname = socket.gethostname()
    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    lines = [
        f"• Hostname: {hostname}",
        f"• Local LAN IP: {local_ip}",
    ]

    # Wi-Fi SSID on Windows
    if _OS == "Windows":
        try:
            wlan = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, timeout=4, **_WIN_HIDE
            )
            for line in wlan.stdout.splitlines():
                if "SSID" in line and "BSSID" not in line:
                    lines.append(f"• {line.strip()}")
                elif "Signal" in line or "State" in line:
                    lines.append(f"• {line.strip()}")
        except Exception:
            pass

    return "Network Information:\n" + "\n".join(lines)


def get_battery_info() -> str:
    """Retrieve laptop battery status and charge percentage."""
    try:
        battery = psutil.sensors_battery()
        if not battery:
            return "No battery detected (Desktop PC or power source connected directly)."
        pct = battery.percent
        plugged = "Plugged in / Charging" if battery.power_plugged else "On battery power"
        secs_left = battery.secsleft
        if secs_left > 0 and secs_left != psutil.POWER_TIME_UNLIMITED:
            hrs = secs_left // 3600
            mins = (secs_left % 3600) // 60
            time_str = f" (~{hrs}h {mins}m remaining)"
        else:
            time_str = ""
        return f"Battery: {pct}% ({plugged}){time_str}."
    except Exception as e:
        return f"Could not read battery status: {e}"


def open_quick_folder(folder_name: str) -> str:
    """Open standard Windows user folders or custom paths in File Explorer."""
    name = (folder_name or "downloads").lower().strip()
    home = Path.home()

    folder_map = {
        "downloads": home / "Downloads",
        "download": home / "Downloads",
        "documents": home / "Documents",
        "document": home / "Documents",
        "desktop": home / "Desktop",
        "pictures": home / "Pictures",
        "photos": home / "Pictures",
        "music": home / "Music",
        "videos": home / "Videos",
        "appdata": Path(os.environ.get("APPDATA", home / "AppData" / "Roaming")),
        "temp": Path(os.environ.get("TEMP", "C:\\Windows\\Temp")),
        "c": Path("C:\\"),
        "root": Path("C:\\"),
    }

    if name in folder_map:
        target_path = folder_map[name]
    else:
        # Check if it's a direct path
        p = Path(folder_name).expanduser()
        if p.exists():
            target_path = p
        else:
            target_path = home / "Downloads"

    try:
        if _OS == "Windows":
            os.startfile(str(target_path))
        elif _OS == "Darwin":
            subprocess.run(["open", str(target_path)])
        else:
            subprocess.run(["xdg-open", str(target_path)])
        return f"Opened folder: {target_path}"
    except Exception as e:
        return f"Failed to open '{target_path}': {e}"


def system_utility_handler(parameters: dict, **kwargs) -> str:
    action = str(parameters.get("action", "")).lower().strip()
    folder = parameters.get("folder", "")

    if "recycle" in action or "bin" in action:
        return empty_recycle_bin()
    elif action in ("lock", "lock_screen", "lock_pc"):
        return lock_workstation()
    elif action in ("sleep", "suspend"):
        return sleep_computer()
    elif "network" in action or "ip" in action or action == "wifi_status":
        return get_network_info()
    elif "battery" in action or "power" in action:
        return get_battery_info()
    elif "folder" in action or action in ("open_downloads", "open_documents", "open_desktop"):
        f_name = folder or action.replace("open_", "")
        return open_quick_folder(f_name)
    else:
        return f"Unknown utility action: '{action}'. Available: empty_recycle_bin, lock, sleep, network_info, battery, open_folder."


TOOL = {
    "name": "system_utility",
    "description": (
        "Performs core OS utilities: empty the Recycle Bin, lock workstation, "
        "put computer to sleep, check network/IP info, check laptop battery percentage, "
        "or open folders (Downloads, Documents, Desktop, Pictures, Videos, etc.)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "empty_recycle_bin | lock | sleep | network_info | battery | open_folder"
            },
            "folder": {
                "type": "STRING",
                "description": "Folder to open if action is open_folder: downloads | documents | desktop | pictures | videos | appdata | custom path"
            }
        },
        "required": ["action"]
    },
    "handler": system_utility_handler
}
