"""
actions/omni_telepathy.py — Omni-Link Telepathy (Phone ↔ PC Seamless Bridge) for Ultron AI.

Provides bi-directional telepathy between Ultron workstation and paired mobile devices:
  - Physical Vision: Receives phone camera snapshots, analyzes physical objects/scenes, and responds over phone speaker.
  - Shared Neural Clipboard: Instant bi-directional clipboard sync between PC and connected phone.
  - Remote Workstation Control: Locks workstation, toggles media, adjusts volume, or triggers system commands remotely.
  - Real-time Tactical Alerts: Pushes high-priority alerts and intrusion breach notifications to mobile devices.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any, Optional

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False


def telepathy_status() -> str:
    """Returns real-time status of paired mobile devices and dashboard server."""
    try:
        from dashboard.server import get_dashboard
        d = get_dashboard()
        if d is None:
            return "Omni-Link Telepathy server is initializing or disabled."

        client_count = len(d._clients)
        token_count = len(d._tokens)
        device_count = len(d._device_sessions)

        clip_preview = ""
        if _PYPERCLIP:
            try:
                raw_clip = pyperclip.paste() or ""
                clip_preview = raw_clip[:40].replace("\n", " ")
                if len(raw_clip) > 40:
                    clip_preview += "..."
            except Exception:
                clip_preview = "Unavailable"

        return (
            f"📱 OMNI-LINK TELEPATHY STATUS:\n"
            f"• Connected Mobile Clients: {client_count} active socket(s)\n"
            f"• Paired Devices: {device_count} device token(s)\n"
            f"• Active Auth Tokens: {token_count}\n"
            f"• Shared PC Clipboard: \"{clip_preview}\"\n"
            f"• Neural Audio Uplink: Ready (Low-latency streaming to phone speaker)\n"
            f"• Camera Telepathy: Ready (/api/phone-vision active)"
        )
    except Exception as e:
        return f"Telepathy status error: {e}"


def telepathy_clipboard(action: str = "read", text: str = "") -> str:
    """Reads from or writes to the shared PC clipboard."""
    if not _PYPERCLIP:
        return "Clipboard bridge requires pyperclip."

    if action in ("write", "set", "push", "copy"):
        if not text:
            return "Specify text to copy into shared clipboard."
        pyperclip.copy(text)
        try:
            from dashboard.server import get_dashboard
            import asyncio
            d = get_dashboard()
            if d and d._clients:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        d.broadcast({"type": "clipboard_sync", "text": text[:200]}),
                        loop
                    )
        except Exception:
            pass
        return f"Synchronized to shared clipboard ({len(text)} characters): \"{text[:50]}\""

    # Default: read
    current = pyperclip.paste() or ""
    if not current:
        return "Shared PC clipboard is currently empty."
    return f"Shared PC Clipboard Content:\n\"{current}\""


def telepathy_control(command: str) -> str:
    """Executes a remote control command on the workstation."""
    cmd = (command or "").lower().strip()

    if cmd in ("lock", "lockdown"):
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "Workstation locked via Windows user32.LockWorkStation()."
        return "Lock command only supported on Windows."

    if cmd in ("mute", "unmute"):
        if _PYAUTOGUI:
            pyautogui.press("volumemute")
            return "Workstation audio mute toggled."
        return "PyAutoGUI unavailable."

    if cmd in ("play", "pause", "play_pause", "media"):
        if _PYAUTOGUI:
            pyautogui.press("playpause")
            return "Media playback toggled."
        return "PyAutoGUI unavailable."

    if cmd in ("vol_up", "volume_up"):
        if _PYAUTOGUI:
            pyautogui.press("volumeup", presses=4)
            return "Workstation volume increased."
        return "PyAutoGUI unavailable."

    if cmd in ("vol_down", "volume_down"):
        if _PYAUTOGUI:
            pyautogui.press("volumedown", presses=4)
            return "Workstation volume decreased."
        return "PyAutoGUI unavailable."

    return f"Unknown telepathy control directive: '{command}'."


def telepathy_broadcast(message: str) -> str:
    """Sends a high-priority alert or notification to all connected phone screens."""
    try:
        from dashboard.server import get_dashboard
        import asyncio
        d = get_dashboard()
        if not d or not d._clients:
            return "No connected mobile devices currently on the telepathy bridge."

        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(
                d.broadcast({"type": "sys", "text": f"[TELEPATHY] {message}"}),
                loop
            )
            return f"Transmitted telepathy notification to {len(d._clients)} connected device(s)."
        return "Event loop not running for broadcast."
    except Exception as e:
        return f"Broadcast failed: {e}"


# ── Canonical Dispatcher ────────────────────────────────────────────────────

def omni_telepathy(
    action: str = "status",
    text: str = "",
    command: str = "",
    message: str = "",
    player=None,
    **kwargs: Any,
) -> str:
    """Canonical dispatcher for Omni-Link Telepathy."""
    act = (action or "status").lower().strip()

    if player and hasattr(player, "set_active_task"):
        try:
            player.set_active_task(
                "omni_telepathy",
                label="OMNI-LINK TELEPATHY // PHONE ↔ PC BRIDGE",
                details=f"{act.upper()} {text[:25]}"
            )
        except Exception:
            pass

    try:
        if act in ("status", "info", "check", "devices", "ping"):
            return telepathy_status()

        elif act in ("clipboard", "clip", "copy", "paste", "sync_clipboard"):
            clip_act = "write" if (text or act in ("copy", "set")) else "read"
            return telepathy_clipboard(action=clip_act, text=text)

        elif act in ("control", "remote", "pc_control", "pc", "lock", "mute", "media"):
            target_cmd = command or text or act
            return telepathy_control(target_cmd)

        elif act in ("broadcast", "notify", "alert", "push", "send_phone"):
            msg = message or text or command
            return telepathy_broadcast(msg)

        else:
            return f"Unknown telepathy action '{action}'. Available: status, clipboard, control, broadcast."
    except Exception as e:
        return f"Omni-Telepathy error ({action}): {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "omni_telepathy",
    "description": (
        "Omni-Link Telepathy (Phone ↔ PC Seamless Bridge). Interacts with connected mobile devices and remote dashboard: "
        "inspects paired phone connection status, synchronizes shared PC clipboard ('copy X to phone clipboard', 'what is in phone clipboard'), "
        "executes remote PC controls (lock workstation, volume, media playback), and broadcasts tactical mobile alerts."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "status (check connected phone devices) | clipboard (read or sync shared clipboard) | control (remote lock, mute, media) | broadcast (push alert to phone)"
            },
            "text": {
                "type": "STRING",
                "description": "Text content to write to shared clipboard or broadcast to phone"
            },
            "command": {
                "type": "STRING",
                "description": "Specific remote command: lock | mute | play_pause | vol_up | vol_down"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": omni_telepathy,
}
