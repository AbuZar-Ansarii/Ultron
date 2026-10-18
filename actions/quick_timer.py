"""
quick_timer.py — Countdown timer and desktop notification action for Ultron AI.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import threading
import time
from typing import Optional


def _run_timer(seconds: int, message: str, speak_cb=None, player_cb=None):
    """Wait in a background thread and then announce completion."""
    time.sleep(seconds)
    msg = f"Timer complete: {message or 'Time is up!'}"
    if player_cb and hasattr(player_cb, "write_log"):
        player_cb.write_log(f"⏰ {msg}")
    if speak_cb and callable(speak_cb):
        try:
            speak_cb(msg)
        except Exception:
            pass


def start_countdown_timer(seconds: int, message: str = "", speak_cb=None, player_cb=None) -> str:
    secs = max(1, int(seconds))
    mins = secs // 60
    rem_secs = secs % 60
    time_desc = f"{mins} minute(s)" if mins and not rem_secs else f"{mins}m {rem_secs}s" if mins else f"{secs} seconds"

    t = threading.Thread(
        target=_run_timer,
        args=(secs, message, speak_cb, player_cb),
        daemon=True
    )
    t.start()
    return f"Timer set for {time_desc} ({message or 'countdown'}). I will alert you when it expires."


def quick_timer_handler(parameters: dict, speak=None, player=None, **kwargs) -> str:
    action = str(parameters.get("action", "timer")).lower().strip()
    seconds = parameters.get("seconds") or 0
    minutes = parameters.get("minutes") or 0
    message = parameters.get("message", "Timer finished")

    total_secs = int(seconds) + int(minutes) * 60
    if total_secs <= 0:
        total_secs = 60  # Default 1 minute

    return start_countdown_timer(total_secs, message=message, speak_cb=speak, player_cb=player)


TOOL = {
    "name": "quick_timer",
    "description": (
        "Sets a quick countdown timer or alarm that alerts the user when time is up. "
        "Use when user says: 'set a timer for 5 minutes', 'timer for 30 seconds', 'remind me in 2 minutes'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "minutes": {
                "type": "INTEGER",
                "description": "Number of minutes"
            },
            "seconds": {
                "type": "INTEGER",
                "description": "Number of seconds"
            },
            "message": {
                "type": "STRING",
                "description": "Timer label or alert message (e.g. 'check oven', 'tea ready')"
            }
        },
        "required": []
    },
    "handler": quick_timer_handler
}
