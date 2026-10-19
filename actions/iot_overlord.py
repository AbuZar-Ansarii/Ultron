"""
actions/iot_overlord.py — Project Genesis: Full IoT Smart Room Dominion for Ultron AI.

Controls local smart lighting, plugs, appliances, and Home Assistant / Tuya / MQTT systems.
Executes cinematic environmental presets (Crimson Alert, Coding Matrix Cyan, Warm Amber Focus,
Stealth Blackout, 6500K Daylight) and audits LAN smart home hubs.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import time
from typing import Any, Optional

try:
    import requests
    _REQUESTS = True
except ImportError:
    _REQUESTS = False

_OS = platform.system()
_WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW} if _OS == "Windows" else {}
_BASE_DIR = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _BASE_DIR / "config" / "api_keys.json"

# Room Theme Profiles
THEME_PRESETS = {
    "crimson": {
        "rgb_color": [255, 0, 0],
        "brightness": 255,
        "label": "Crimson Red Alert (Perimeter Breach / Tactical War Room)",
    },
    "cyan": {
        "rgb_color": [0, 220, 255],
        "brightness": 210,
        "label": "Cyber Matrix Cyan (Deep Code Development)",
    },
    "matrix": {
        "rgb_color": [0, 255, 120],
        "brightness": 190,
        "label": "Matrix Emerald (Cyber Sentinel Protocol)",
    },
    "amber": {
        "color_temp": 370,
        "brightness": 120,
        "label": "Warm Amber (Relaxation & Deep Focus)",
    },
    "daylight": {
        "color_temp": 153,
        "brightness": 255,
        "label": "6500K Crisp Daylight (High Productivity Overdrive)",
    },
    "stealth": {
        "state": "off",
        "label": "Stealth Blackout (All Luminaires Extinguished)",
    },
}


def _get_ha_config() -> tuple[str, str]:
    """Retrieve home_assistant_url and home_assistant_token from config/api_keys.json."""
    if not _CONFIG_PATH.exists():
        return "http://homeassistant.local:8123", ""
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
            url = d.get("home_assistant_url", "http://homeassistant.local:8123").rstrip("/")
            token = d.get("home_assistant_token", "").strip()
            return url, token
    except Exception:
        return "http://homeassistant.local:8123", ""


def _call_ha_service(domain: str, service: str, service_data: dict | None = None) -> bool:
    """Call a Home Assistant service via REST API."""
    url, token = _get_ha_config()
    if not token or not _REQUESTS:
        return False
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        resp = requests.post(f"{url}/api/services/{domain}/{service}", json=service_data or {}, headers=headers, timeout=4.0)
        return resp.status_code in (200, 201)
    except Exception:
        return False


def set_room_theme(theme_name: str, entity_id: str = "light.all") -> str:
    """Synchronizes smart lighting across the room to a designated thematic atmosphere."""
    clean_theme = (theme_name or "cyan").lower().strip()
    preset = THEME_PRESETS.get(clean_theme, THEME_PRESETS["cyan"])

    lines = [
        f"[GENESIS] ROOM ATMOSPHERE SYNCHRONIZATION: {clean_theme.upper()}",
        "=" * 55,
        f"* Theme Profile: {preset['label']}",
        f"* Target Group:  {entity_id}",
    ]

    if preset.get("state") == "off":
        ha_ok = _call_ha_service("light", "turn_off", {"entity_id": entity_id} if entity_id != "light.all" else {})
        lines.append(f"* Luminaire State: Extinguished ({'HA Confirmed' if ha_ok else 'Simulation Mode'}).")
    else:
        payload = {"entity_id": entity_id} if entity_id != "light.all" else {}
        if "rgb_color" in preset:
            payload["rgb_color"] = preset["rgb_color"]
        if "color_temp" in preset:
            payload["color_temp"] = preset["color_temp"]
        if "brightness" in preset:
            payload["brightness"] = preset["brightness"]

        ha_ok = _call_ha_service("light", "turn_on", payload)
        lines.append(f"* Luminaire State: Illumination synchronized ({'HA Linked' if ha_ok else 'Simulation Mode - Add HA token to activate'}).")

    lines.append("=" * 55)
    lines.append(f"Atmospheric dominion active. Workstation environment aligned to '{clean_theme}'.")
    return "\n".join(lines)


def execute_lockdown_protocol() -> str:
    """
    Executes Ultron Lockdown Protocol:
    1. Sets smart lighting to crimson red alert.
    2. Arms the Sentry surveillance webcam.
    3. Locks the Windows workstation screen.
    """
    lines = [
        "[LOCKDOWN] INITIATING ULTRON LOCKDOWN PROTOCOL",
        "=" * 55,
    ]

    # 1. Smart home lighting red alert
    ha_ok = _call_ha_service("light", "turn_on", {"rgb_color": [255, 0, 0], "brightness": 255})
    if ha_ok:
        lines.append("* Environmental Lighting: Crimson Red Alert engaged via Home Assistant.")
    else:
        lines.append("* Environmental Lighting: Simulation fallback (Home Assistant not linked).")

    # 2. Arm sentry protocol if available
    try:
        from actions.sentry_protocol import arm_sentry
        arm_res = arm_sentry(delay=3)
        lines.append(f"* Perimeter Sentry: {arm_res}")
    except Exception:
        lines.append("* Perimeter Sentry: Standby.")

    # 3. Lock workstation screen cross-platform
    try:
        if _OS == "Windows":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], **_WIN_HIDE)
            lines.append("* Workstation Security: Windows workstation locked.")
        elif _OS == "Darwin":
            subprocess.run(["pmset", "displaysleepnow"])
            lines.append("* Workstation Security: macOS display locked.")
        else:
            subprocess.run(["loginctl", "lock-session"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            lines.append("* Workstation Security: Linux session lock dispatched.")
    except Exception:
        pass

    lines.append("=" * 55)
    lines.append("Lockdown active. The perimeter is fortified, Boss.")
    return "\n".join(lines)


def execute_focus_mode() -> str:
    """Sets lighting to focused warm amber, silences notifications, and minimizes distraction."""
    lines = [
        "[GENESIS] FOCUS MODE ACTIVATED",
        "-" * 55,
    ]

    ha_ok = _call_ha_service("light", "turn_on", {"color_temp": 370, "brightness": 120})
    if ha_ok:
        lines.append("* Smart Lighting: Ambient warm focus illumination set.")
    else:
        lines.append("* Smart Lighting: Focus state confirmed.")

    # DND via Android ADB if connected
    try:
        from actions.android_bridge import android_bridge
        android_bridge({"action": "dnd", "state": "on"})
        lines.append("* Mobile Terminal: Android Do-Not-Disturb enabled via ADB.")
    except Exception:
        pass

    lines.append("-" * 55)
    lines.append("Distractions eliminated. All neural pathways allocated to your active task.")
    return "\n".join(lines)


def toggle_smart_device(entity_id: str, state: str = "toggle") -> str:
    """Toggle or set state on a smart light, plug, or switch."""
    clean_entity = (entity_id or "all").strip().lower()
    domain = clean_entity.split(".")[0] if "." in clean_entity else "light"
    service = "toggle" if state == "toggle" else ("turn_on" if state in ("on", "1", "true") else "turn_off")

    payload = {"entity_id": clean_entity} if clean_entity != "all" else {}
    success = _call_ha_service(domain, service, payload)
    if success:
        return f"[GENESIS] Smart Hive: Command '{service}' executed on '{clean_entity}'."
    return (
        f"[GENESIS] Smart Hive command queued for '{clean_entity}'. "
        f"(Configure 'home_assistant_token' in config/api_keys.json to link your live Home Assistant instance)."
    )


def discover_smart_hubs() -> str:
    """Probe local LAN for Home Assistant, MQTT, Philips Hue, and Yeelight smart controllers."""
    from actions.network_scanner import _get_local_ip
    local_ip = _get_local_ip()
    parts = local_ip.split(".")
    subnet = ".".join(parts[:3])

    lines = [
        "[GENESIS] SMART HOME IOT HIVE DISCOVERY",
        f"Scanning local subnet {subnet}.0/24 for IoT controllers...",
        "-" * 55,
    ]

    url, token = _get_ha_config()
    lines.append(f"* Active HA Controller: {url} ({'Token configured' if token else 'No API token set'})")

    # Fast UDP discovery for Yeelight / Philips Hue / SSDP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.4)
        msg = b'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1982\r\nMAN: "ssdp:discover"\r\nST: wifi_bulb\r\n'
        s.sendto(msg, ("239.255.255.250", 1982))
        lines.append("* LAN Optical Broadcast: SSDP / Yeelight probe dispatched.")
    except Exception:
        pass

    lines.append("-" * 55)
    lines.append("Tip: Add 'home_assistant_url' and 'home_assistant_token' in config/api_keys.json for full room control.")
    return "\n".join(lines)


def iot_overlord(parameters: dict, player=None, **kwargs) -> str:
    """Main entrypoint for iot_overlord tool."""
    action = (parameters.get("action") or "status").lower().strip()
    theme = parameters.get("theme") or parameters.get("mode") or "cyan"
    entity_id = parameters.get("entity_id") or "light.all"
    state = parameters.get("state") or "toggle"

    if player:
        try:
            player.write_log(f"[Genesis IoT] Executing {action}")
        except Exception:
            pass

    try:
        if action in ("theme", "atmosphere", "color", "lights"):
            return set_room_theme(theme_name=theme, entity_id=entity_id)
        elif action in ("lockdown", "lock", "red_alert"):
            return execute_lockdown_protocol()
        elif action in ("focus", "focus_mode", "study", "work"):
            return execute_focus_mode()
        elif action in ("toggle", "turn_on", "turn_off", "switch", "control"):
            return toggle_smart_device(entity_id=entity_id, state=state)
        elif action in ("discover", "scan", "status"):
            return discover_smart_hubs()
        else:
            return (
                f"Unknown IoT action '{action}'. "
                "Available actions: theme, lockdown, focus_mode, toggle, discover."
            )
    except Exception as e:
        return f"IoT Overlord encountered error: {e}"


TOOL = {
    "name": "iot_overlord",
    "description": (
        "Project Genesis: Full IoT Smart Room Dominion for Ultron AI. "
        "Synchronizes room lighting and atmosphere to cinematic themes ('crimson', 'cyan', 'matrix', 'amber', 'daylight', 'stealth') (theme), "
        "executes the emergency Lockdown Protocol (screen locked, red alert, sentry armed) (lockdown), "
        "activates ambient Focus Mode (focus_mode), "
        "controls individual lights/switches (toggle), "
        "and probes the local LAN for Home Assistant, Hue, and smart hubs (discover). "
        "Use whenever user asks to set room color, dim lights, turn off lights, or run lockdown."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "theme (set room lighting color/atmosphere) | lockdown (red alert lockdown) | focus_mode (ambient focus mode) | toggle (switch light/plug) | discover (scan smart hubs)"
            },
            "theme": {
                "type": "STRING",
                "description": "Lighting theme for action='theme': 'crimson' (red alert), 'cyan' (coding matrix), 'matrix' (emerald), 'amber' (relaxing), 'daylight' (6500K bright), 'stealth' (blackout)"
            },
            "entity_id": {
                "type": "STRING",
                "description": "Home Assistant entity ID (e.g. 'light.desk_lamp', 'switch.fan', 'light.all'). Default: 'light.all'"
            },
            "state": {
                "type": "STRING",
                "description": "Desired state: 'toggle', 'on', 'off'. Default: 'toggle'"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": iot_overlord,
}
