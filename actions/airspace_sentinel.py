"""
actions/airspace_sentinel.py — Physical Airspace & Bluetooth Sentinel ("RF Recon Protocol") for Ultron AI.

Scans local physical RF airspace for Bluetooth Low Energy (BLE) beacons, smartphones, smartwatches,
AirTags, and nearby Wi-Fi access points. Detects lingering unknown devices and audits airspace security.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import time
from typing import Any, Optional

try:
    import bleak
    _BLEAK = True
except ImportError:
    _BLEAK = False

_OS = platform.system()
_WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW} if _OS == "Windows" else {}
_BASE_DIR = Path(__file__).resolve().parent.parent
_AIRSPACE_DB = _BASE_DIR / "memory" / "airspace_registry.json"


def _load_registry() -> dict[str, Any]:
    """Load known devices and scan history."""
    if _AIRSPACE_DB.exists():
        try:
            with open(_AIRSPACE_DB, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"whitelist": {}, "seen": {}}


def _save_registry(data: dict[str, Any]) -> None:
    _AIRSPACE_DB.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(_AIRSPACE_DB, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _estimate_distance(rssi: int) -> str:
    """Rough proximity estimate based on BLE RSSI in dBm."""
    if rssi >= -60:
        return "IMMEDIATE (< 1.5m / Same Room)"
    elif rssi >= -75:
        return "NEAR (1.5m – 4m / Adjacent Space)"
    elif rssi >= -88:
        return "FAR (4m – 10m / Outer Perimeter)"
    return "WEAK SIGNAL (> 10m)"


async def _scan_ble_async(timeout_sec: float = 4.0) -> list[dict[str, Any]]:
    """Scan BLE airspace using Bleak."""
    devices_out: list[dict[str, Any]] = []
    if not _BLEAK:
        return devices_out

    try:
        scanner = bleak.BleakScanner()
        discovered = await scanner.discover(timeout=timeout_sec, return_adv=True)
        for d, adv in discovered.values():
            rssi = adv.rssi if adv else (d.rssi if hasattr(d, "rssi") else -99)
            name = d.name or adv.local_name or "Unknown BLE Beacon"
            devices_out.append({
                "address": d.address.upper(),
                "name": name,
                "rssi": rssi,
                "distance": _estimate_distance(rssi),
            })
    except Exception as e:
        print(f"[Airspace Sentinel] BLE scan exception: {e}")
    return devices_out


def scan_bluetooth(timeout: float = 4.0) -> str:
    """Scan local physical airspace for active Bluetooth devices."""
    lines = [
        "📡 PHYSICAL AIRSPACE SENTINEL — BLUETOOTH RF RECON",
        "─" * 60,
    ]

    ble_devices: list[dict[str, Any]] = []

    if _BLEAK:
        try:
            loop = asyncio.new_event_loop()
            try:
                ble_devices = loop.run_until_complete(_scan_ble_async(timeout_sec=timeout))
            finally:
                loop.close()
        except Exception as e:
            lines.append(f"Notice: Bleak async scan: {e}")

    # Fallback to system query if BLE scan returned 0
    if not ble_devices:
        if _OS == "Windows":
            try:
                cmd = ["powershell", "-NoProfile", "-Command", "Get-PnpDevice -Class Bluetooth | Where-Object {$_.Status -eq 'OK'} | Select-Object -Property FriendlyName, InstanceId | ConvertTo-Json"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5, **_WIN_HIDE)
                if res.stdout.strip():
                    try:
                        data = json.loads(res.stdout)
                        if isinstance(data, dict):
                            data = [data]
                        for item in data:
                            fname = item.get("FriendlyName") or "Bluetooth Device"
                            iid = item.get("InstanceId") or "LOCAL_DEVICE"
                            ble_devices.append({
                                "address": iid.split("_")[-1][:17].upper() if "_" in iid else iid[:17],
                                "name": fname,
                                "rssi": -65,
                                "distance": "PAIRED / LOCAL RADIO",
                            })
                    except Exception:
                        pass
            except Exception:
                pass
        elif _OS == "Darwin":
            try:
                res = subprocess.run(["system_profiler", "SPBluetoothDataType"], capture_output=True, text=True, timeout=5)
                for line in (res.stdout or "").splitlines():
                    if "Address:" in line:
                        addr = line.split("Address:", 1)[1].strip()
                        ble_devices.append({
                            "address": addr.upper(),
                            "name": "Apple Bluetooth Endpoint",
                            "rssi": -65,
                            "distance": "PAIRED / LOCAL RADIO",
                        })
            except Exception:
                pass
        else:
            # Linux bluetoothctl fallback
            try:
                res = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True, timeout=4)
                for line in (res.stdout or "").splitlines():
                    parts = line.split()
                    if len(parts) >= 3 and parts[0] == "Device":
                        addr = parts[1]
                        name = " ".join(parts[2:])
                        ble_devices.append({
                            "address": addr.upper(),
                            "name": name,
                            "rssi": -65,
                            "distance": "PAIRED / LOCAL RADIO",
                        })
            except Exception:
                pass

    if not ble_devices:
        return "Airspace scan completed. No active Bluetooth transmissions detected within RF range."

    registry = _load_registry()
    whitelist = registry.get("whitelist", {})
    seen = registry.get("seen", {})
    now_ts = time.time()

    ble_devices.sort(key=lambda x: x["rssi"], reverse=True)

    for d in ble_devices:
        addr = d["address"]
        name = d["name"]
        rssi = d["rssi"]
        dist = d["distance"]

        # Track history
        if addr not in seen:
            seen[addr] = {"name": name, "first_seen": now_ts, "last_seen": now_ts, "count": 1}
        else:
            seen[addr]["last_seen"] = now_ts
            seen[addr]["count"] = seen[addr].get("count", 1) + 1

        is_trusted = addr in whitelist
        trust_tag = "✅ [WHITELISTED / TRUSTED]" if is_trusted else "⚠️ [UNVERIFIED TRANSMITTER]"

        lines.append(f"• {name:<26} | RSSI: {rssi:>4} dBm | {addr}")
        lines.append(f"    └─ Proximity: {dist} | {trust_tag}")

    _save_registry({"whitelist": whitelist, "seen": seen})

    lines.append("─" * 60)
    lines.append(f"Airspace Scan Complete: {len(ble_devices)} RF transmitters detected within perimeter.")
    return "\n".join(lines)


def scan_wifi_airspace() -> str:
    """Scan and analyze over-the-air Wi-Fi access points and signal beacons across Windows, macOS, and Linux."""
    lines = [
        "📡 OVER-THE-AIR WI-FI SPECTRUM RECON",
        "─" * 60,
    ]
    networks: list[dict[str, Any]] = []

    if _OS == "Windows":
        try:
            res = subprocess.run(["netsh", "wlan", "show", "networks", "mode=bssid"], capture_output=True, text=True, timeout=5, **_WIN_HIDE)
            out = res.stdout or ""
            current_ssid = "Hidden Network"

            for line in out.splitlines():
                line_str = line.strip()
                if line_str.startswith("SSID "):
                    parts = line_str.split(":", 1)
                    if len(parts) > 1:
                        current_ssid = parts[1].strip() or "Hidden Network"
                elif line_str.startswith("BSSID "):
                    parts = line_str.split(":", 1)
                    bssid = parts[1].strip() if len(parts) > 1 else "Unknown"
                    networks.append({"ssid": current_ssid, "bssid": bssid, "signal": "N/A", "channel": "N/A", "cipher": "N/A"})
                elif line_str.startswith("Signal") and networks:
                    networks[-1]["signal"] = line_str.split(":", 1)[1].strip()
                elif line_str.startswith("Channel") and networks:
                    networks[-1]["channel"] = line_str.split(":", 1)[1].strip()
                elif line_str.startswith("Authentication") and networks:
                    networks[-1]["cipher"] = line_str.split(":", 1)[1].strip()
        except Exception as e:
            return f"Wi-Fi airspace scan failed: {e}"

    elif _OS == "Darwin":
        try:
            airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
            if os.path.exists(airport_path):
                res = subprocess.run([airport_path, "-s"], capture_output=True, text=True, timeout=5)
                for line in (res.stdout or "").splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 6:
                        ssid = parts[0]
                        bssid = parts[1]
                        rssi = parts[2]
                        chan = parts[3]
                        sec = " ".join(parts[6:])
                        networks.append({"ssid": ssid, "bssid": bssid, "signal": f"{rssi} dBm", "channel": chan, "cipher": sec})
        except Exception as e:
            return f"macOS Wi-Fi airspace scan failed: {e}"

    else:
        # Linux
        try:
            res = subprocess.run(["nmcli", "-t", "-f", "ssid,bssid,signal,chan,security", "dev", "wifi"], capture_output=True, text=True, timeout=5)
            for line in (res.stdout or "").splitlines():
                parts = line.split(":")
                if len(parts) >= 5:
                    ssid = parts[0] or "Hidden Network"
                    bssid = parts[1]
                    signal = f"{parts[2]}%"
                    chan = parts[3]
                    sec = parts[4]
                    networks.append({"ssid": ssid, "bssid": bssid, "signal": signal, "channel": chan, "cipher": sec})
        except Exception as e:
            return f"Linux Wi-Fi airspace scan failed: {e}"

    if not networks:
        return "No wireless networks detected in immediate airspace."

    for net in networks[:12]:
        lines.append(f"• SSID: {net['ssid']:<22} | Signal: {net['signal']:<7} | Ch: {net['channel']:<3} | MAC: {net['bssid']}")
        lines.append(f"    └─ Auth: {net['cipher']}")

    lines.append("─" * 60)
    lines.append(f"Airspace mapped: {len(networks)} wireless access point beacons detected.")
    return "\n".join(lines)


def whitelist_device(address: str, name: str = "") -> str:
    """Register a trusted personal device to suppress unverified transmitter warnings."""
    clean_addr = (address or "").strip().upper()
    if not clean_addr:
        return "Please specify a Bluetooth MAC address or device identifier to whitelist."

    registry = _load_registry()
    whitelist = registry.get("whitelist", {})
    whitelist[clean_addr] = {
        "name": name or "User Trusted Device",
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
    registry["whitelist"] = whitelist
    _save_registry(registry)
    return f"Device '{name or clean_addr}' [{clean_addr}] has been added to Ultron's Trusted Airspace Whitelist."


def airspace_sentinel(parameters: dict, player=None, **kwargs) -> str:
    """Main entrypoint for airspace_sentinel tool."""
    action = (parameters.get("action") or "scan_ble").lower().strip()
    target_addr = parameters.get("address") or ""
    device_name = parameters.get("name") or ""
    timeout = float(parameters.get("timeout") or 4.0)

    if player:
        try:
            player.write_log(f"[Airspace Sentinel] Executing {action}")
        except Exception:
            pass

    try:
        if action in ("scan_ble", "ble", "bluetooth", "devices", "recon"):
            return scan_bluetooth(timeout=timeout)
        elif action in ("scan_wifi", "wifi_air", "airwaves", "spectrum"):
            return scan_wifi_airspace()
        elif action in ("whitelist", "trust", "add_trusted"):
            return whitelist_device(address=target_addr, name=device_name)
        else:
            return (
                f"Unknown airspace action '{action}'. "
                "Available actions: scan_ble, scan_wifi, whitelist."
            )
    except Exception as e:
        return f"Airspace Sentinel encountered error: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "airspace_sentinel",
    "description": (
        "Physical Airspace & Bluetooth Sentinel ('RF Recon Protocol') for Ultron. "
        "Scans physical local RF airspace for Bluetooth Low Energy devices, phones, watches, and beacons (scan_ble), "
        "inspects over-the-air Wi-Fi access point spectrums and BSSIDs (scan_wifi), "
        "and whitelists trusted personal hardware (whitelist). "
        "Use whenever user asks to scan Bluetooth devices, check nearby wireless airwaves, or audit physical airspace."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "scan_ble (scan Bluetooth LE airspace) | scan_wifi (scan over-the-air Wi-Fi BSSIDs) | whitelist (register a trusted device MAC)"
            },
            "address": {
                "type": "STRING",
                "description": "Bluetooth MAC address for whitelisting (e.g. 'AA:BB:CC:DD:EE:FF')."
            },
            "name": {
                "type": "STRING",
                "description": "Friendly name for trusted device (e.g. 'My iPhone 15', 'Galaxy Watch')."
            },
            "timeout": {
                "type": "NUMBER",
                "description": "Scan duration in seconds. Default: 4.0."
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": airspace_sentinel,
}
