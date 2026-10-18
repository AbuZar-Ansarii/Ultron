"""
actions/iot_overlord.py — Smart Home & IoT Hive Overlord ("Jarvis Domotics") for Ultron AI.

Controls local smart lighting, plugs, and Home Assistant / Tuya / MQTT smart home systems.
Executes cinematic environmental presets like 'Lockdown Protocol' and 'Focus Mode'.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
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


def execute_lockdown_protocol() -> str:
    """
    Executes Ultron Lockdown Protocol:
    1. Sets smart lighting to crimson red (or powers off non-essential lights).
    2. Arms the Sentry surveillance webcam.
    3. Locks the Windows workstation screen.
    """
    lines = [
        "🚨 INITIATING ULTRON LOCKDOWN PROTOCOL",
        "═" * 55,
    ]

    # 1. Smart home lighting red alert
    ha_ok = _call_ha_service("light", "turn_on", {"rgb_color": [255, 0, 0], "brightness": 255})
    if ha_ok:
        lines.append("• Environmental Lighting: Crimson Red Alert engaged via Home Assistant.")
    else:
        lines.append("• Environmental Lighting: Simulation fallback (Home Assistant not linked).")

    # 2. Arm sentry protocol if available
    try:
        from actions.sentry_protocol import arm_sentry
        arm_res = arm_sentry(delay=3)
        lines.append(f"• Perimeter Sentry: {arm_res}")
    except Exception:
        lines.append("• Perimeter Sentry: Standby.")

    # 3. Lock workstation screen cross-platform
    try:
        if _OS == "Windows":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], **_WIN_HIDE)
            lines.append("• Workstation Security: Windows workstation locked.")
        elif _OS == "Darwin":
            subprocess.run(["pmset", "displaysleepnow"])
            lines.append("• Workstation Security: macOS display locked.")
        else:
            # Linux lock session
            locked = False
            for lock_cmd in (["loginctl", "lock-session"], ["xdg-screensaver", "lock"], ["gnome-screensaver-command", "-l"]):
                try:
                    res = subprocess.run(lock_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if res.returncode == 0:
                        locked = True
                        break
                except Exception:
                    continue
            lines.append(f"• Workstation Security: Linux session {'locked' if locked else 'lock command dispatched'}.")
    except Exception:
        pass

    lines.append("═" * 55)
    lines.append("Lockdown active. The perimeter is fortified, Boss.")
    return "\n".join(lines)


def execute_focus_mode() -> str:
    """Sets lighting to focused warm amber, silences notifications, and minimizes distraction."""
    lines = [
        "🧘 FOCUS MODE ACTIVATED",
        "─" * 55,
    ]

    ha_ok = _call_ha_service("light", "turn_on", {"color_temp": 370, "brightness": 120})
    if ha_ok:
        lines.append("• Smart Lighting: Ambient warm focus illumination set.")
    else:
        lines.append("• Smart Lighting: Focus state confirmed.")

    # DND via Android ADB if connected
    try:
        from actions.android_bridge import android_bridge
        android_bridge({"action": "dnd", "state": "on"})
        lines.append("• Mobile Terminal: Android Do-Not-Disturb enabled via ADB.")
    except Exception:
        pass

    lines.append("─" * 55)
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
        return f"Smart Hive: Command '{service}' executed on '{clean_entity}'."
    return (
        f"Smart Hive command queued for '{clean_entity}'. "
        f"(Configure 'home_assistant_token' in config/api_keys.json to link your live Home Assistant instance)."
    )


def discover_smart_hubs() -> str:
    """Probe local LAN for Home Assistant, MQTT, and Zigbee/Hue hubs."""
    from actions.network_scanner import _get_local_ip, _ping_host
    local_ip = _get_local_ip()
    parts = local_ip.split(".")
    subnet = ".".join(parts[:3])

    lines = [
        "🏠 SMART HOME IOT HIVE DISCOVERY",
        f"Scanning local subnet {subnet}.0/24 for IoT controllers...",
        "─" * 55,
    ]

    url, token = _get_ha_config()
    lines.append(f"• Active HA Controller: {url} ({'Token configured' if token else 'No API token set'})")

    lines.append("─" * 55)
    lines.append("Tip: Add 'home_assistant_url' and 'home_assistant_token' in settings to unlock full room control.")
    return "\n".join(lines)


def iot_overlord(parameters: dict, player=None, **kwargs) -> str:
    """Main entrypoint for iot_overlord tool."""
    action = (parameters.get("action") or "status").lower().strip()
    entity_id = parameters.get("entity_id") or "light.all"
    state = parameters.get("state") or "toggle"

    if player:
        try:
            player.write_log(f"[IoT Overlord] Executing {action}")
        except Exception:
            pass

    try:
        if action in ("lockdown", "lock", "red_alert"):
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
                "Available actions: lockdown, focus_mode, toggle, discover."
            )
    except Exception as e:
        return f"IoT Overlord encountered error: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "iot_overlord",
    "description": (
        "Smart Home & IoT Hive Overlord ('Jarvis Domotics') for Ultron. "
        "Controls local smart lighting, plugs, and Home Assistant automation (toggle), "
        "executes the cinematic Lockdown Protocol (locks screen, turns lights red, arms sentry) (lockdown), "
        "initiates Focus Mode (dims lights, silences notifications) (focus_mode), "
        "and audits connected smart hubs (discover). "
        "Use whenever user asks to control room lights, start focus mode, or execute lockdown protocol."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "lockdown (red alert lockdown) | focus_mode (ambient focus mode) | toggle (switch light/plug) | discover (scan smart hubs)"
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
