"""
actions/macro_protocol.py — Vibranium Protocol Engine & Battle Modes for Ultron AI.
Chains complex workstation multi-step actions into single-phrase voice triggers:
  - Protocol Lockdown (stealth mode, minimize, mute, lock workstation, arm sentry)
  - Protocol Code / Focus (developer tools launch, audio tuning, workstation prep)
  - Protocol Cinema / Media (audio boost, display dimming, media launch)
  - Protocol Gaming / Overclock (high performance power plan, gaming hubs launch)
  - Protocol Night / Sleep (volume mute, cleanup, sleep state)
  - User-defined custom protocols stored persistently in memory/protocols.json.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import ctypes
import json
import os
import platform
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Optional

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

_OS = platform.system()
_WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW} if _OS == "Windows" else {}
_BASE_DIR = Path(__file__).resolve().parent.parent
_PROTOCOLS_FILE = _BASE_DIR / "memory" / "protocols.json"


def _load_custom_protocols() -> dict[str, dict]:
    """Load user-defined custom protocols from memory/protocols.json."""
    if not _PROTOCOLS_FILE.exists():
        return {}
    try:
        return json.loads(_PROTOCOLS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_custom_protocols(data: dict[str, dict]) -> bool:
    """Save user-defined protocols to memory/protocols.json."""
    try:
        _PROTOCOLS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PROTOCOLS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False


def _set_power_plan_high_performance() -> bool:
    """Set Windows power scheme to High Performance."""
    if _OS != "Windows":
        return False
    try:
        # High Performance GUID
        subprocess.run(["powercfg", "/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"], **_WIN_HIDE)
        return True
    except Exception:
        return False


def _mute_audio():
    """Mute master volume."""
    if _PYAUTOGUI:
        pyautogui.press("volumemute")


def _minimize_all_windows():
    """Minimize all open windows to desktop."""
    if _PYAUTOGUI:
        pyautogui.hotkey("win", "d")


def _lock_screen():
    """Lock Windows workstation immediately."""
    if _OS == "Windows":
        try:
            ctypes.windll.user32.LockWorkStation()
        except Exception:
            pass


def _launch_app_by_name(name: str):
    """Launch app via open_app action logic."""
    try:
        from actions.open_app import open_app
        open_app(parameters={"app_name": name})
    except Exception:
        try:
            if _OS == "Windows":
                subprocess.Popen(f"start {name}", shell=True, **_WIN_HIDE)
        except Exception:
            pass


# ── Built-in Protocols ────────────────────────────────────────────────────────

def _play_sfx_quiet(sound: str):
    """Fire and forget sound effect."""
    try:
        from actions.audio_matrix import play_sound_async
        play_sound_async(sound)
    except Exception:
        pass


def _execute_lockdown(player=None) -> str:
    """Lockdown protocol: hide windows, mute, arm sentry, lock workstation."""
    _play_sfx_quiet("alarm")
    _minimize_all_windows()
    time.sleep(0.3)
    _mute_audio()
    time.sleep(0.2)

    # Arm Sentry Protocol if available
    sentry_status = "unarmed"
    try:
        from actions.sentry_protocol import activate_sentry
        activate_sentry(player=player)
        sentry_status = "armed"
    except Exception:
        pass

    _lock_screen()

    return (
        "Protocol Lockdown engaged, Boss. "
        "Workstation displays cleared, master audio suppressed, "
        f"workstation locked, and Sentry surveillance {sentry_status}."
    )


def _execute_code(player=None) -> str:
    """Focus / Code protocol: launch development environment, tune audio."""
    _play_sfx_quiet("repulsor")
    launched = []
    for app in ["vscode", "terminal"]:
        _launch_app_by_name(app)
        launched.append(app)

    return (
        "Protocol Code engaged, Boss. "
        f"Development tools deployed ({', '.join(launched)}). "
        "Workstation primed for execution."
    )


def _execute_cinema(player=None) -> str:
    """Cinema / Media protocol: audio boost, dim lights/screen."""
    _play_sfx_quiet("sonar")
    if _PYAUTOGUI:
        # Increase volume slightly
        for _ in range(3):
            pyautogui.press("volumeup")

    return (
        "Protocol Cinema active, Boss. "
        "Audio dynamics leveled. The stage is set."
    )


def _execute_gaming(player=None) -> str:
    """Gaming protocol: high performance power plan, launch gaming hubs."""
    _play_sfx_quiet("bass_drop")
    _set_power_plan_high_performance()
    _launch_app_by_name("discord")

    return (
        "Protocol Gaming initiated, Boss. "
        "High Performance power governor unlocked, communication link (Discord) online."
    )


def _execute_night(player=None) -> str:
    """Night / Sleep protocol: mute, empty trash, lock workstation."""
    _play_sfx_quiet("power_down")
    _mute_audio()
    try:
        from actions.purge_protocol import execute_purge
        execute_purge(include_recycle_bin=True, include_dev=False)
    except Exception:
        pass
    _lock_screen()

    return (
        "Protocol Night executed. "
        "Audio muted, digital caches purged, workstation locked. Goodnight, Boss."
    )


_BUILTIN_PROTOCOLS = {
    "lockdown": ("Minimizes windows, mutes audio, locks workstation, and arms sentry surveillance.", _execute_lockdown),
    "stealth":  ("Minimizes windows, mutes audio, locks workstation, and arms sentry surveillance.", _execute_lockdown),
    "code":     ("Deploys VS Code and terminal environment for focused development.", _execute_code),
    "focus":    ("Deploys VS Code and terminal environment for focused development.", _execute_code),
    "cinema":   ("Tunes audio dynamics and sets up multimedia presentation.", _execute_cinema),
    "media":    ("Tunes audio dynamics and sets up multimedia presentation.", _execute_cinema),
    "gaming":   ("Activates High Performance power plan and launches Discord/Steam.", _execute_gaming),
    "boost":    ("Activates High Performance power plan and launches Discord/Steam.", _execute_gaming),
    "night":    ("Mutes audio, purges temporary cache, and locks workstation for the night.", _execute_night),
    "sleep":    ("Mutes audio, purges temporary cache, and locks workstation for the night.", _execute_night),
}


def list_all_protocols() -> str:
    """List all available built-in and user-defined protocols."""
    customs = _load_custom_protocols()
    lines = [
        "⚡ ULTRON VIBRANIUM PROTOCOL REGISTRY",
        "─" * 45,
        "BUILT-IN PROTOCOLS:",
    ]
    seen = set()
    for name, (desc, _) in _BUILTIN_PROTOCOLS.items():
        if desc in seen:
            continue
        seen.add(desc)
        lines.append(f"  • Protocol {name.upper()}: {desc}")

    if customs:
        lines.append("\nCUSTOM USER PROTOCOLS:")
        for cname, cdata in customs.items():
            desc = cdata.get("description", "User-defined macro")
            lines.append(f"  • Protocol {cname.upper()}: {desc}")
    else:
        lines.append("\n(No custom protocols registered yet. Create one with action='create'.)")

    lines.append("─" * 45)
    lines.append("Say 'Ultron, activate protocol <name>' to execute.")
    return "\n".join(lines)


def run_protocol(name: str, player=None) -> str:
    """Execute a built-in or custom protocol by name."""
    clean = (name or "").lower().strip().replace("protocol", "").strip()
    if not clean:
        return "No protocol name specified. Call list_all_protocols or specify a protocol name."

    # 1. Check built-in
    if clean in _BUILTIN_PROTOCOLS:
        _, handler = _BUILTIN_PROTOCOLS[clean]
        return handler(player=player)

    # 2. Check custom
    customs = _load_custom_protocols()
    if clean in customs:
        proto = customs[clean]
        apps = proto.get("apps", [])
        for app in apps:
            _launch_app_by_name(app)
            time.sleep(0.5)
        cmd = proto.get("command")
        if cmd:
            try:
                subprocess.Popen(cmd, shell=True, **_WIN_HIDE)
            except Exception:
                pass
        msg = proto.get("response") or f"Custom Protocol '{clean}' executed successfully."
        return f"{msg} (Launched: {', '.join(apps) if apps else 'configured tasks'})"

    return f"Protocol '{clean}' not found in registry. Say 'list protocols' to view available protocols."


def create_custom_protocol(name: str, description: str = "", apps: list[str] | None = None, command: str = "", response_msg: str = "") -> str:
    """Register a new persistent custom protocol."""
    clean = (name or "").lower().strip().replace("protocol", "").strip()
    if not clean:
        return "Invalid protocol name."

    customs = _load_custom_protocols()
    customs[clean] = {
        "description": description or f"Custom user protocol for {clean}",
        "apps": apps or [],
        "command": command or "",
        "response": response_msg or f"Protocol {clean.capitalize()} initialized, Boss.",
    }
    if _save_custom_protocols(customs):
        return f"Protocol '{clean}' registered in persistent registry. You can now invoke it with 'Ultron, activate protocol {clean}'."
    return "Failed to save protocol to disk."


def macro_protocol(parameters: dict, player=None, **kwargs) -> str:
    """Main entrypoint for macro_protocol tool."""
    action = (parameters.get("action") or "run").lower().strip()
    proto_name = parameters.get("protocol_name") or parameters.get("name") or ""

    if player:
        try:
            player.write_log(f"[Protocol] {action} {proto_name}")
        except Exception:
            pass

    try:
        if action in ("run", "execute", "start", "activate"):
            return run_protocol(proto_name, player=player)

        elif action in ("list", "show", "all"):
            return list_all_protocols()

        elif action in ("create", "add", "register", "new"):
            apps = parameters.get("apps")
            if isinstance(apps, str):
                apps = [a.strip() for a in apps.split(",") if a.strip()]
            desc = parameters.get("description", "")
            cmd = parameters.get("command", "")
            resp = parameters.get("response", "")
            return create_custom_protocol(proto_name, description=desc, apps=apps, command=cmd, response_msg=resp)

        elif action in ("delete", "remove"):
            clean = proto_name.lower().strip().replace("protocol", "").strip()
            customs = _load_custom_protocols()
            if clean in customs:
                del customs[clean]
                _save_custom_protocols(customs)
                return f"Custom protocol '{clean}' deleted."
            return f"Protocol '{clean}' not found in custom registry."

        else:
            return f"Unknown protocol action '{action}'. Available: run, list, create, delete."
    except Exception as e:
        return f"Protocol Engine error ({action}): {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "macro_protocol",
    "description": (
        "Vibranium Protocol Engine & Battle Modes. Executes chained, multi-step workstation automation routines "
        "with a single voice command. Built-in protocols: 'lockdown' (stealth/minimize/mute/lock/arm sentry), "
        "'code' / 'focus' (launch VS Code and terminal, prep workstation), 'cinema' / 'media' (audio tuning & presentation), "
        "'gaming' / 'boost' (high performance power plan & game hubs), 'night' / 'sleep' (mute, purge cache, lock workstation). "
        "Also supports creating and listing custom user macros. Use when user says 'Protocol Lockdown', 'Protocol Code', "
        "'Protocol Gaming', 'Protocol Night', or asks to list/create custom automation protocols."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "run (execute a protocol) | list (show all protocols) | create (save custom protocol) | delete (remove custom protocol)"
            },
            "protocol_name": {
                "type": "STRING",
                "description": "Name of the protocol (e.g. 'lockdown', 'code', 'gaming', 'cinema', 'night', or a custom protocol name)"
            },
            "description": {
                "type": "STRING",
                "description": "For action='create': Brief description of what this custom protocol does"
            },
            "apps": {
                "type": "STRING",
                "description": "For action='create': Comma-separated app names to launch (e.g. 'chrome, vscode, spotify')"
            },
            "command": {
                "type": "STRING",
                "description": "For action='create': Optional shell command line to execute"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": macro_protocol,
}
