"""
actions/sentry_protocol.py — Workstation Sentry & Intrusion Defense Protocol for Ultron AI.

Provides autonomous workstation surveillance when the user is away:
  - Webcam motion & human face detection via OpenCV Haar Cascade
  - Workstation perimeter defense (mouse movement / keyboard touch detection)
  - Captures timestamped intruder snapshots to ~/Pictures/Ultron_Sentry/
  - Speaks an imposing Ultron intruder warning via TTS
  - Dispatches immediate Telegram alerts with intruder photo attached
  - Arming countdown, cooldown pacing, and graceful disarm
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False

try:
    import requests
    _REQUESTS = True
except ImportError:
    _REQUESTS = False

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False


# ── Configuration & State ───────────────────────────────────────────────────

_BASE_DIR = Path(__file__).resolve().parent.parent
_SENTRY_DIR = Path.home() / "Pictures" / "Ultron_Sentry"

_sentry_thread: threading.Thread | None = None
_sentry_active = False
_sentry_state = "DISARMED"       # DISARMED | ARMING | ARMED
_sentry_lock = threading.Lock()
_detection_count = 0
_last_alert_time = 0.0
_arm_delay_sec = 10              # Seconds before arming
_alert_cooldown_sec = 25         # Cooldown between spoken alerts / dispatches


def _get_telegram_creds() -> tuple[str, str]:
    """Retrieve telegram_bot_token and telegram_chat_id from config/api_keys.json."""
    cfg_path = _BASE_DIR / "config" / "api_keys.json"
    if not cfg_path.exists():
        return "", ""
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return str(data.get("telegram_bot_token", "")).strip(), str(data.get("telegram_chat_id", "")).strip()
    except Exception:
        return "", ""


def _send_telegram_photo(photo_path: Path, caption: str) -> bool:
    """Send intruder snapshot directly to Telegram Bot."""
    if not _REQUESTS:
        return False
    token, chat_id = _get_telegram_creds()
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(photo_path, "rb") as f:
            resp = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": f},
                timeout=12,
            )
            return resp.status_code == 200
    except Exception as e:
        print(f"[Sentry] Telegram alert error: {e}")
        return False


def _lock_workstation() -> bool:
    """Instantly locks the Windows workstation to defend the perimeter."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            print("[Sentry] 🔒 [LOCKDOWN] Workstation locked via Windows user32.LockWorkStation()")
            return True
        except Exception as e:
            print(f"[Sentry] Workstation lock failed: {e}")
    return False


def _broadcast_dashboard_breach(reason: str, photo_name: str) -> None:
    """Transmits instant breach telemetry & vibration alert to connected mobile phones."""
    try:
        from dashboard.server import broadcast_breach
        broadcast_breach({
            "reason": reason,
            "photo": photo_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        print(f"[Sentry] 📱 [TELEPATHY] Intrusion alert transmitted to connected mobile devices.")
    except Exception as e:
        print(f"[Sentry] Dashboard breach broadcast error: {e}")


def _speak_alert(player=None) -> None:
    """Speak the imposing Ultron intruder warning."""
    warning = "You are interfering with things you cannot begin to understand. Step away from this workstation, or I will deal with you myself."
    if player and hasattr(player, "speak"):
        try:
            threading.Thread(target=lambda: player.speak(warning), daemon=True).start()
            return
        except Exception:
            pass

    # Direct EdgeTTS fallback
    try:
        from core.tts import create_tts_player
        p = create_tts_player({"tts_engine": "edgetts"})
        threading.Thread(target=lambda: p.speak(warning), daemon=True).start()
    except Exception as e:
        print(f"[Sentry] TTS speech warning error: {e}")


# ── Surveillance Worker ─────────────────────────────────────────────────────

def _sentry_worker(player=None):
    global _sentry_active, _sentry_state, _detection_count, _last_alert_time

    _SENTRY_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[Sentry] Arming countdown initiated ({_arm_delay_sec}s)...")
    _sentry_state = "ARMING"

    # Arming countdown
    for i in range(_arm_delay_sec):
        if not _sentry_active:
            _sentry_state = "DISARMED"
            return
        time.sleep(1)

    with _sentry_lock:
        _sentry_state = "ARMED"
    print("[Sentry] [ARMED] Sentry Protocol armed. Workstation surveillance active.")

    # Try opening webcam
    cap = None
    face_cascade = None
    if _CV2:
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                cap.release()
                cap = None
            else:
                cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
                if os.path.exists(cascade_path):
                    face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            print(f"[Sentry] Camera init exception: {e}")
            cap = None

    last_mouse_pos = pyautogui.position() if _PYAUTOGUI else (0, 0)
    prev_gray = None

    while _sentry_active:
        now = time.monotonic()
        breach_detected = False
        breach_reason = ""
        intruder_frame = None

        # 1. Camera Surveillance
        if cap and cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_blurred = cv2.GaussianBlur(gray, (21, 21), 0)

                # Check Face Detection first
                if face_cascade:
                    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))
                    if len(faces) > 0:
                        breach_detected = True
                        breach_reason = f"Human face detected ({len(faces)} person)"
                        for (x, y, w, h) in faces:
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                            cv2.putText(frame, "TARGET IDENTIFIED", (x, y - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                # Check Motion Detection if no face detected yet
                if not breach_detected and prev_gray is not None:
                    delta = cv2.absdiff(prev_gray, gray_blurred)
                    thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
                    motion_score = cv2.countNonZero(thresh)
                    if motion_score > 5000:  # Significant physical motion in room
                        breach_detected = True
                        breach_reason = f"Perimeter motion breach (delta: {motion_score})"

                prev_gray = gray_blurred
                intruder_frame = frame

        # 2. Perimeter Touch Fallback (Mouse movement)
        if not breach_detected and _PYAUTOGUI:
            curr_mouse_pos = pyautogui.position()
            dx = abs(curr_mouse_pos[0] - last_mouse_pos[0])
            dy = abs(curr_mouse_pos[1] - last_mouse_pos[1])
            if dx > 40 or dy > 40:
                breach_detected = True
                breach_reason = f"Physical input breach: Mouse moved to {curr_mouse_pos}"
            last_mouse_pos = curr_mouse_pos

        # Trigger Breach Actions
        if breach_detected and (now - _last_alert_time) >= _alert_cooldown_sec:
            _last_alert_time = now
            _detection_count += 1
            timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            photo_name = f"intruder_{timestamp_str}.jpg"
            photo_path = _SENTRY_DIR / photo_name

            print(f"[Sentry] [BREACH ALERT] #{_detection_count}: {breach_reason}")

            # Save snapshot
            if intruder_frame is not None and _CV2:
                # Add HUD watermark
                header_text = f"ULTRON SENTRY BREACH | {timestamp_str} | {breach_reason}"
                cv2.putText(intruder_frame, header_text, (20, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
                cv2.imwrite(str(photo_path), intruder_frame)
            elif _PYAUTOGUI:
                # Fallback desktop screenshot
                screenshot = pyautogui.screenshot()
                screenshot.save(str(photo_path))

            # Voice Alarm
            _speak_alert(player)

            # Instant Workstation Lockdown
            _lock_workstation()

            # Mobile Telepathy Uplink Alert
            _broadcast_dashboard_breach(breach_reason, photo_name)

            # Telegram Alert
            if photo_path.exists():
                caption = (
                    f"ULTRON SENTRY PROTOCOL ALERT\n"
                    f"Workstation perimeter breach detected!\n"
                    f"Reason: {breach_reason}\n"
                    f"Action: Workstation locked via Windows API\n"
                    f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Snapshot: {photo_name}"
                )
                dispatched = _send_telegram_photo(photo_path, caption)
                if dispatched:
                    print(f"[Sentry] [TELEGRAM] Intruder snapshot dispatched to Telegram.")

        time.sleep(0.3)

    # Cleanup
    if cap:
        cap.release()
    _sentry_state = "DISARMED"
    print("[Sentry] Sentry surveillance loop terminated.")


# ── Action Interface ─────────────────────────────────────────────────────────

def activate_sentry(player=None) -> str:
    global _sentry_thread, _sentry_active, _sentry_state, _detection_count
    with _sentry_lock:
        if _sentry_active and _sentry_state in ("ARMING", "ARMED"):
            return f"Sentry Protocol is already {_sentry_state}. Workstation perimeter is active."

        _sentry_active = True
        _detection_count = 0
        _sentry_thread = threading.Thread(target=_sentry_worker, args=(player,), daemon=True)
        _sentry_thread.start()

    camera_msg = "Webcam visual tracking enabled." if _CV2 else "Perimeter touch monitoring active."
    return (
        f"Sentry Protocol initialized. Arming countdown active ({_arm_delay_sec} seconds). "
        f"{camera_msg} Step away from the workstation."
    )


def deactivate_sentry() -> str:
    global _sentry_active, _sentry_state
    with _sentry_lock:
        if not _sentry_active:
            return "Sentry Protocol is not active."
        _sentry_active = False
        _sentry_state = "DISARMED"

    return f"Sentry Protocol disarmed. Stand down. Recorded {_detection_count} breach event(s)."


def sentry_status() -> str:
    token, chat_id = _get_telegram_creds()
    telegram_status = "Connected" if (token and chat_id) else "Not configured (set in api_keys.json)"
    snapshots = list(_SENTRY_DIR.glob("intruder_*.jpg")) if _SENTRY_DIR.exists() else []

    return (
        f"[SENTRY] Protocol Status:\n"
        f"  - State: {_sentry_state}\n"
        f"  - Breaches Detected: {_detection_count}\n"
        f"  - Arming Delay: {_arm_delay_sec}s\n"
        f"  - Alert Cooldown: {_alert_cooldown_sec}s\n"
        f"  - Telegram Alerts: {telegram_status}\n"
        f"  - Stored Snapshots: {len(snapshots)} in {_SENTRY_DIR}"
    )


def sentry_gallery() -> str:
    if not _SENTRY_DIR.exists():
        return "No Sentry snapshots directory found."
    files = sorted(_SENTRY_DIR.glob("intruder_*.jpg"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return "No intruder breaches recorded yet. Gallery is clean."

    lines = [f"Recent Sentry Captures ({len(files)} total):"]
    for f in files[:8]:
        size_kb = f.stat().st_size / 1024
        ts = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"  • {f.name} ({size_kb:.1f} KB) — {ts}")
    if len(files) > 8:
        lines.append(f"  ... and {len(files) - 8} more in {_SENTRY_DIR}")
    return "\n".join(lines)


def instant_lockdown(player=None) -> str:
    """Immediate tactical perimeter lockdown."""
    _lock_workstation()
    _broadcast_dashboard_breach("Manual Tactical Lockdown Triggered", "lockdown_manual.jpg")
    _speak_alert(player)
    activate_sentry(player)
    return "Tactical lockdown engaged. Workstation locked down, perimeter alarms active, and Sentry Protocol armed. Step away."


# ── Unified Dispatcher ───────────────────────────────────────────────────────

def sentry_protocol(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "status").lower().strip()

    if player:
        player.write_log(f"[sentry] {action}")

    try:
        if action in ("activate", "arm", "start", "enable"):
            return activate_sentry(player)
        elif action in ("deactivate", "disarm", "stop", "disable"):
            return deactivate_sentry()
        elif action in ("lockdown", "lock", "lock_pc", "intruder_lockdown"):
            return instant_lockdown(player)
        elif action in ("status", "check", "info"):
            return sentry_status()
        elif action in ("gallery", "snapshots", "logs", "breaches"):
            return sentry_gallery()
        else:
            return f"Unknown Sentry action: '{action}'. Available: activate, deactivate, lockdown, status, gallery."
    except Exception as e:
        return f"Sentry Protocol error ({action}): {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "sentry_protocol",
    "description": (
        "Workstation Autonomous Sentry & Perimeter Defense Protocol. Autonomously monitors webcam and physical inputs "
        "for human presence/intruders when the user is away, locks down the Windows operating system (user32.LockWorkStation), "
        "captures timestamped intruder snapshots to Pictures/Ultron_Sentry/, delivers a chilling Ultron vocal warning, "
        "and dispatches instant Telegram & Mobile Dashboard breach alerts. "
        "Actions: activate (arm surveillance), deactivate (disarm), lockdown (immediate workstation lock + arm sentry), status, gallery."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "activate (arm sentry mode) | deactivate (disarm) | lockdown (instant Windows lock & arm) | status (check security state) | gallery (view intruder captures)"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": sentry_protocol,
}
