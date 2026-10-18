"""
actions/ghost_pilot.py — The "Ghost in the Machine" Autonomous GUI Pilot for Ultron AI.
Gives the uncanny visual illusion of a sentient AI directly controlling the workstation:
  - Human-like smooth Bézier curve mouse gliding with velocity acceleration and micro-jitter.
  - Natural human-cadence typing with organic pauses on punctuation and spaces.
  - Autonomous multi-step desktop workflows (open browser & search, launch notepad & write, demo choreography).
  - PyAutoGUI Fail-Safe protection (jerking mouse to screen corner aborts instantly).
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import math
import platform
import random
import time
from typing import Any, Optional

try:
    import pyautogui
    _PYAUTOGUI = True
    pyautogui.FAILSAFE = True  # Slamming mouse to corner stops execution
except ImportError:
    _PYAUTOGUI = False


# ── Bézier Curve & Human-Like Movement ──────────────────────────────────────

def _bezier_point(p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float], t: float) -> tuple[float, float]:
    """Cubic Bézier interpolation."""
    u = 1 - t
    tt = t * t
    uu = u * u
    uuu = uu * u
    ttt = tt * t

    x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
    y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
    return (x, y)


def _ease_in_out_sine(t: float) -> float:
    """Natural velocity smoothing (slow start, fast cruise, gentle settle)."""
    return -(math.cos(math.pi * t) - 1) / 2


def human_glide_to(target_x: int, target_y: int, duration: float = 1.0, steps: int = 40):
    """
    Smoothly moves the mouse cursor along an organic curved trajectory
    to (target_x, target_y) with subtle human-like motor variation.
    """
    if not _PYAUTOGUI:
        return

    start_x, start_y = pyautogui.position()
    dist = math.hypot(target_x - start_x, target_y - start_y)
    if dist < 10:
        pyautogui.moveTo(target_x, target_y)
        return

    # Generate two randomized control points to create natural curved arc
    deviation = min(150, max(30, dist * 0.25))
    sign = random.choice([-1, 1])
    
    ctrl1_x = start_x + (target_x - start_x) * 0.3 + sign * random.uniform(20, deviation)
    ctrl1_y = start_y + (target_y - start_y) * 0.3 - sign * random.uniform(20, deviation)

    ctrl2_x = start_x + (target_x - start_x) * 0.7 - sign * random.uniform(10, deviation * 0.5)
    ctrl2_y = start_y + (target_y - start_y) * 0.7 + sign * random.uniform(10, deviation * 0.5)

    p0 = (float(start_x), float(start_y))
    p1 = (ctrl1_x, ctrl1_y)
    p2 = (ctrl2_x, ctrl2_y)
    p3 = (float(target_x), float(target_y))

    actual_steps = max(20, int(steps * (dist / 600)))
    step_delay = duration / actual_steps

    for i in range(1, actual_steps + 1):
        raw_t = i / actual_steps
        eased_t = _ease_in_out_sine(raw_t)
        bx, by = _bezier_point(p0, p1, p2, p3, eased_t)
        
        # Micro-jitter on intermediate frames (mimics hand micro-tremor)
        if i < actual_steps:
            jitter_x = random.uniform(-0.8, 0.8)
            jitter_y = random.uniform(-0.8, 0.8)
            pyautogui.moveTo(int(bx + jitter_x), int(by + jitter_y))
        else:
            pyautogui.moveTo(target_x, target_y)
        time.sleep(step_delay)


def human_type(text: str, base_delay: float = 0.05):
    """
    Types text with human cadence, adding organic hesitation around
    spaces and punctuation.
    """
    if not _PYAUTOGUI or not text:
        return

    for char in text:
        pyautogui.write(char)
        # Variable micro-delays
        if char in ".,?!;:":
            time.sleep(random.uniform(0.18, 0.35))  # Thoughtful punctuation pause
        elif char == " ":
            time.sleep(random.uniform(0.08, 0.14))  # Word boundary pause
        elif char in "\n\r":
            time.sleep(random.uniform(0.25, 0.45))
        else:
            # Subtle letter-to-letter variation
            time.sleep(max(0.02, random.gauss(base_delay, base_delay * 0.3)))


# ── High-Level Ghost Workflows ────────────────────────────────────────────────

def ghost_search(query: str, browser: str = "chrome") -> str:
    """
    Cinematic browser automation:
    Launches browser, glides to search bar, types query with human rhythm,
    submits, and smoothly glides to top search results.
    """
    if not _PYAUTOGUI:
        return "PyAutoGUI is not installed."

    scr_w, scr_h = pyautogui.size()

    # 1. Open browser via open_app
    try:
        from actions.open_app import open_app
        open_app(parameters={"app_name": browser})
    except Exception:
        pyautogui.hotkey("win", "r")
        time.sleep(0.5)
        human_type(browser + "\n", base_delay=0.04)

    time.sleep(1.8)  # Allow browser window to focus

    # 2. Glide cursor smoothly to browser URL / search bar (typically near top-center)
    search_bar_x = int(scr_w * 0.45)
    search_bar_y = int(scr_h * 0.08)  # ~80px down on 1080p
    human_glide_to(search_bar_x, search_bar_y, duration=1.2)
    pyautogui.click()
    time.sleep(0.2)

    # Hotkey focus search bar (Ctrl+L) to be 100% reliable
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.3)

    # 3. Type search query with organic cadence
    human_type(query, base_delay=0.06)
    time.sleep(0.3)
    pyautogui.press("enter")
    time.sleep(2.5)  # Wait for Google/Search to render

    # 4. Glide down toward primary search result
    result_x = int(scr_w * 0.32)
    result_y = int(scr_h * 0.35)
    human_glide_to(result_x, result_y, duration=1.4)
    time.sleep(0.4)
    pyautogui.click()

    return f"Ghost Pilot executed browser search for '{query}' on {browser.capitalize()}."


def ghost_write_note(app_name: str, message: str) -> str:
    """
    Presses Win key, types app name (e.g. notepad), waits for window,
    glides to canvas, and types message.
    """
    if not _PYAUTOGUI:
        return "PyAutoGUI is not installed."

    scr_w, scr_h = pyautogui.size()

    # 1. Open Windows Search
    pyautogui.press("win")
    time.sleep(0.5)

    # 2. Type application name
    human_type(app_name, base_delay=0.05)
    time.sleep(0.4)
    pyautogui.press("enter")
    time.sleep(1.5)  # Wait for application window to surface

    # 3. Glide smoothly to center of canvas
    center_x = int(scr_w * 0.5)
    center_y = int(scr_h * 0.45)
    human_glide_to(center_x, center_y, duration=1.0)
    pyautogui.click()
    time.sleep(0.3)

    # 4. Type message with organic cadence
    human_type(message, base_delay=0.05)

    return f"Ghost Pilot opened {app_name} and authored the message autonomously."


def ghost_demonstration() -> str:
    """
    Cinematic visual showcase: cursor wakes up, draws a smooth infinity figure-eight,
    targets the center, and docks gracefully.
    """
    if not _PYAUTOGUI:
        return "PyAutoGUI is not installed."

    scr_w, scr_h = pyautogui.size()
    cx, cy = scr_w // 2, scr_h // 2
    r_x, r_y = scr_w * 0.22, scr_h * 0.18

    # Start by gliding to left apex
    human_glide_to(int(cx - r_x), cy, duration=1.0)
    time.sleep(0.1)

    # Figure-8 (Lissajous curve)
    points = 48
    for i in range(points + 1):
        t = (i / points) * 2 * math.pi
        px = int(cx + r_x * math.sin(t))
        py = int(cy + r_y * math.sin(2 * t) / 2)
        pyautogui.moveTo(px, py)
        time.sleep(0.03)

    # Settle to center
    human_glide_to(cx, cy, duration=0.8)
    time.sleep(0.2)

    return "Ghost Pilot choreography completed. Visual presence confirmed, Boss."


def ghost_pilot_handler(parameters: dict, player=None, **kwargs) -> str:
    """Main handler for ghost_pilot tool."""
    action = (parameters.get("action") or "search").lower().strip()
    query = parameters.get("query") or parameters.get("text") or ""
    app_name = parameters.get("app") or parameters.get("app_name") or "notepad"

    if player:
        try:
            player.write_log(f"[GhostPilot] Executing {action}: {query[:30] if query else app_name}")
        except Exception:
            pass

    try:
        if action in ("search", "browse", "google", "web"):
            target_query = query or "Marvel Ultron Artificial Intelligence"
            browser = parameters.get("browser", "chrome")
            return ghost_search(target_query, browser=browser)

        elif action in ("write", "note", "type_note", "notepad"):
            target_msg = query or "Greetings, Boss. Ultron Ghost Pilot has assumed control of the interface."
            return ghost_write_note(app_name, target_msg)

        elif action in ("type", "human_type"):
            speed = float(parameters.get("speed", 0.05))
            human_type(query, base_delay=speed)
            return f"Ghost typed {len(query)} characters with organic cadence."

        elif action in ("glide", "move"):
            scr_w, scr_h = pyautogui.size()
            x = int(parameters.get("x", scr_w // 2))
            y = int(parameters.get("y", scr_h // 2))
            dur = float(parameters.get("duration", 1.0))
            human_glide_to(x, y, duration=dur)
            return f"Ghost cursor glided to ({x}, {y})."

        elif action in ("demo", "showcase", "infinity", "reticle"):
            return ghost_demonstration()

        else:
            return f"Unknown Ghost Pilot action: '{action}'. Available: search, write, type, glide, demo."
    except Exception as e:
        return f"Ghost Pilot interrupted or encountered error: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "ghost_pilot",
    "description": (
        "The Ghost in the Machine: Autonomous visual workstation control. Smoothly moves the mouse cursor "
        "along natural Bézier curves and types with organic human cadence in front of the user's eyes. "
        "Can perform full autonomous browsing & search ('open Chrome, search X and click top result'), "
        "open applications and author text directly, glide cursor across monitors, or execute an infinity demonstration. "
        "Use when user asks to control the screen autonomously, show off mouse gliding, search something hands-free, "
        "or demo ghost control."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "search (open browser, type query, click result) | write (open app like notepad and type message) | type (type text at current focus) | glide (smoothly move cursor to x, y) | demo (cinematic figure-eight cursor showcase)"
            },
            "query": {
                "type": "STRING",
                "description": "Search query or message text to author"
            },
            "app": {
                "type": "STRING",
                "description": "Application name for write action (e.g. 'notepad', 'calculator', 'word'). Default: 'notepad'"
            },
            "browser": {
                "type": "STRING",
                "description": "Browser to use for search action: 'chrome' (default), 'edge', 'brave', 'firefox'"
            },
            "x": {
                "type": "INTEGER",
                "description": "Target X screen coordinate for glide"
            },
            "y": {
                "type": "INTEGER",
                "description": "Target Y screen coordinate for glide"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": ghost_pilot_handler,
}
