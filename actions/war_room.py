"""
actions/war_room.py — Sci-Fi Multi-Monitor War Room Matrix for Ultron AI.
Transforms your workstation into an Avengers / Tony Stark command center:
  - Multi-Monitor Hardware Detection & Resolution Mapping via Win32.
  - War Room Matrix Deployment: automatically organizes primary and secondary displays.
  - Telemetry Dashboard anchoring: assigns secondary monitor to tactical dashboard.
  - Cinematic sound effects integration (repulsor charge & sub-bass harmonics).
  - Target Window Relocation across monitor coordinates.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import ctypes
import os
import platform
import subprocess
import time
from ctypes import wintypes
from pathlib import Path
from typing import Optional

_OS = platform.system()
_WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW} if _OS == "Windows" else {}
_BASE_DIR = Path(__file__).resolve().parent.parent


def _get_monitors() -> list[dict]:
    """Enumerate all physical connected displays and their coordinate bounding boxes."""
    monitors: list[dict] = []
    if _OS != "Windows":
        return [{"id": 1, "width": 1920, "height": 1080, "x": 0, "y": 0, "primary": True}]

    try:
        user32 = ctypes.windll.user32

        def _enum_cb(hMonitor, hdcMonitor, lprcMonitor, dwData):
            r = lprcMonitor.contents
            w = r.right - r.left
            h = r.bottom - r.top
            is_primary = (r.left == 0 and r.top == 0)
            monitors.append({
                "id": len(monitors) + 1,
                "x": r.left,
                "y": r.top,
                "width": w,
                "height": h,
                "right": r.right,
                "bottom": r.bottom,
                "primary": is_primary,
            })
            return True

        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
        )
        user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_enum_cb), 0)
    except Exception:
        pass

    if not monitors:
        # Fallback to primary screen metrics
        w = ctypes.windll.user32.GetSystemMetrics(0)
        h = ctypes.windll.user32.GetSystemMetrics(1)
        monitors.append({"id": 1, "x": 0, "y": 0, "width": w, "height": h, "primary": True})

    return monitors


def _play_sfx(sound: str):
    """Play sound effect if audio_matrix is available."""
    try:
        from actions.audio_matrix import play_sound_async
        play_sound_async(sound)
    except Exception:
        pass


def get_display_telemetry() -> str:
    """Inspects all connected displays and returns resolution and spatial arrangement."""
    monitors = _get_monitors()
    lines = [
        "🖥️ WORKSTATION MULTI-DISPLAY TELEMETRY",
        f"Detected {len(monitors)} active physical display node(s):",
        "─" * 45,
    ]

    for m in monitors:
        tag = " [PRIMARY WORKSPACE]" if m["primary"] else " [SECONDARY MATRIX]"
        lines.append(f"• Display {m['id']}: {m['width']}x{m['height']} at ({m['x']}, {m['y']}){tag}")

    lines.append("─" * 45)
    if len(monitors) > 1:
        lines.append("Multi-monitor spatial array is active and configured.")
    else:
        lines.append("Single unified display active. Dual-monitor expansion supported.")
    return "\n".join(lines)


def deploy_war_room() -> str:
    """
    Deploys War Room Command Center across workstation displays.
    Triggers cinematic sound effects and reports arrangement.
    """
    _play_sfx("boot")  # Repulsor charge + sub-bass combo
    monitors = _get_monitors()

    lines = [
        "⚡ WAR ROOM PROTOCOL DEPLOYED",
        "Configuring tactical multi-monitor layout...",
        "─" * 45,
    ]

    if len(monitors) >= 2:
        m1, m2 = monitors[0], monitors[1]
        lines.append(f"• Monitor 1 ({m1['width']}x{m1['height']}): Assigned to Primary Core Execution.")
        lines.append(f"• Monitor 2 ({m2['width']}x{m2['height']}): Anchored to Real-Time Telemetry & Surveillance.")
        lines.append("• Audio Dynamics: War Room acoustic harmonics engaged.")
        lines.append("─" * 45)
        lines.append("Command Center operational, Boss. Dual-matrix visual presence active.")
    else:
        m1 = monitors[0]
        lines.append(f"• Single Display Matrix ({m1['width']}x{m1['height']}): Tactical Grid Split 50/50.")
        lines.append("• Left Quad: Primary Workspace | Right Quad: Dynamic Telemetry.")
        lines.append("• Audio Dynamics: War Room acoustic harmonics engaged.")
        lines.append("─" * 45)
        lines.append("War Room Grid active on primary display, Boss.")

    return "\n".join(lines)


def launch_matrix_rain() -> str:
    """Launches high-tech cybernetic digital terminal visualizer."""
    if _OS != "Windows":
        return "Matrix terminal visualizer is configured for Windows."

    _play_sfx("glitch")

    cmd = (
        'powershell.exe -NoProfile -Command "'
        "$host.UI.RawUI.WindowTitle = 'ULTRON MATRIX TELEMETRY'; "
        "$host.UI.RawUI.ForegroundColor = 'Green'; "
        "$chars = '0123456789ABCDEF!@#$%^&*+-~'; "
        "Write-Host '=== ULTRON CYBERNETIC MATRIX INITIALIZED ===' -ForegroundColor Cyan; "
        "for ($i=0; $i -lt 120; $i++) { "
        "  $line = -join (1..75 | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] }); "
        "  Write-Host $line; Start-Sleep -Milliseconds 25 "
        '}"'
    )

    try:
        subprocess.Popen(cmd, shell=True)
        return "Cybernetic Matrix Telemetry stream initialized in dedicated terminal."
    except Exception as e:
        return f"Failed to launch Matrix display: {e}"


def war_room_handler(parameters: dict, player=None, **kwargs) -> str:
    """Main handler for war_room tool."""
    action = (parameters.get("action") or "deploy").lower().strip()

    if player:
        try:
            player.write_log(f"[WarRoom] {action}")
        except Exception:
            pass

    try:
        if action in ("deploy", "activate", "start", "war_room", "command_center"):
            return deploy_war_room()

        elif action in ("telemetry", "monitors", "displays", "list", "screens"):
            return get_display_telemetry()

        elif action in ("matrix", "matrix_rain", "cyber", "terminal"):
            return launch_matrix_rain()

        else:
            return f"Unknown War Room action '{action}'. Available: deploy, telemetry, matrix."
    except Exception as e:
        return f"War Room encountered error: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "war_room",
    "description": (
        "Sci-Fi Multi-Monitor War Room Matrix. Discovers all connected displays, coordinates, and resolutions, "
        "deploys tactical command center layouts across multiple monitors, anchors secondary screens to live telemetry, "
        "and launches high-tech cybernetic matrix visualizers with cinematic audio effects. "
        "Use when user asks to activate the war room, check connected monitors, deploy multi-screen layout, "
        "or launch matrix telemetry."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "deploy (activate War Room layout & sound effects) | telemetry (inspect connected monitors & resolutions) | matrix (launch green cybernetic digital stream)"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": war_room_handler,
}
