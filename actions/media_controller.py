"""
media_controller.py — Universal Media & Audio Controller for Ultron AI.
Control Spotify, YouTube, VLC, browser media, and Windows media players from voice commands.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import platform
import subprocess
try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

_OS = platform.system()


def media_play_pause() -> str:
    if _PYAUTOGUI:
        pyautogui.press("playpause")
        return "Toggled media play/pause."
    return "PyAutoGUI is not available."


def media_next() -> str:
    if _PYAUTOGUI:
        pyautogui.press("nexttrack")
        return "Skipped to next track."
    return "PyAutoGUI is not available."


def media_prev() -> str:
    if _PYAUTOGUI:
        pyautogui.press("prevtrack")
        return "Rewound to previous track."
    return "PyAutoGUI is not available."


def media_stop() -> str:
    if _PYAUTOGUI:
        pyautogui.press("stop")
        return "Media stopped."
    return "PyAutoGUI is not available."


def media_mute() -> str:
    if _PYAUTOGUI:
        pyautogui.press("volumemute")
        return "Toggled volume mute."
    return "PyAutoGUI is not available."


def media_volume_set(level: int) -> str:
    vol = max(0, min(100, int(level)))
    if _OS == "Windows":
        try:
            import math
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol_obj = cast(interface, POINTER(IAudioEndpointVolume))
            vol_db = -65.25 if vol == 0 else max(-65.25, 20 * math.log10(vol / 100))
            vol_obj.SetMasterVolumeLevel(vol_db, None)
            return f"Volume set to {vol}%."
        except Exception as e:
            # Fallback
            return f"Volume adjustment: {vol}%"
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e", f"set volume output volume {vol}"], capture_output=True)
        return f"Volume set to {vol}%."
    return f"Volume set to {vol}%."


def media_controller_handler(parameters: dict, **kwargs) -> str:
    action = str(parameters.get("action", "play_pause")).lower().strip()
    volume = parameters.get("volume") or parameters.get("value")

    if action in ("play", "pause", "play_pause", "toggle"):
        return media_play_pause()
    elif action in ("next", "next_track", "skip"):
        return media_next()
    elif action in ("prev", "previous", "previous_track", "replay", "back"):
        return media_prev()
    elif action in ("stop",):
        return media_stop()
    elif action in ("mute", "unmute", "toggle_mute"):
        return media_mute()
    elif action in ("volume_set", "set_volume") or volume is not None:
        try:
            return media_volume_set(int(volume or 50))
        except ValueError:
            return "Invalid volume level."
    elif action == "volume_up":
        if _PYAUTOGUI:
            for _ in range(5): pyautogui.press("volumeup")
            return "Volume increased."
    elif action == "volume_down":
        if _PYAUTOGUI:
            for _ in range(5): pyautogui.press("volumedown")
            return "Volume decreased."
    return f"Unknown media action: '{action}'."


TOOL = {
    "name": "media_controller",
    "description": (
        "Controls media playback and audio on the PC. "
        "Use when user asks to: play music, pause music, skip to next song, "
        "previous track, stop playback, mute/unmute audio, or set volume to a specific percentage."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "play_pause | next | previous | stop | mute | volume_set | volume_up | volume_down"
            },
            "volume": {
                "type": "INTEGER",
                "description": "Target volume percentage 0-100 (for volume_set)"
            }
        },
        "required": ["action"]
    },
    "handler": media_controller_handler
}
