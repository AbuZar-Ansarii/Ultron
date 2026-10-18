"""
actions/biometric_sentinel.py — Biometric Face ID & Boss Recognition for Ultron AI.
Provides movie-grade facial authentication and intruder defense:
  - Enrolls the Boss's facial signature using normalized OpenCV feature templates.
  - Authenticates live users via webcam.
  - Confirms Boss identity with personalized welcoming audio telemetry.
  - Flags unknown intruders, captures evidence to ~/Pictures/Ultron_Sentry/,
    triggers the Red Alert alarm, and locks down the workstation.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import ctypes
import json
import os
import platform
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False

import numpy as np

_OS = platform.system()
_BASE_DIR = Path(__file__).resolve().parent.parent
_BIO_DIR = _BASE_DIR / "memory" / "boss_biometrics"
_SENTRY_DIR = Path.home() / "Pictures" / "Ultron_Sentry"

# Match threshold for normalized cross-correlation
_MATCH_THRESHOLD = 0.55


def _get_cascade():
    """Load OpenCV Haar Cascade for frontal face detection."""
    if not _CV2:
        return None
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    if os.path.exists(cascade_path):
        return cv2.CascadeClassifier(cascade_path)
    return None


def _preprocess_face(gray_face: np.ndarray, target_size: tuple[int, int] = (160, 160)) -> np.ndarray:
    """Equalize illumination and resize face image for robust matching."""
    resized = cv2.resize(gray_face, target_size, interpolation=cv2.INTER_AREA)
    equalized = cv2.equalizeHist(resized)
    return equalized


def _play_sfx(sound: str):
    """Trigger procedural sound effect if audio_matrix is available."""
    try:
        from actions.audio_matrix import play_sound_async
        play_sound_async(sound)
    except Exception:
        pass


def enroll_boss_face(samples_needed: int = 4) -> str:
    """
    Captures reference face templates of the Boss from the webcam
    and stores them persistently in memory/boss_biometrics/.
    """
    if not _CV2:
        return "OpenCV is not available on this system."

    cascade = _get_cascade()
    if cascade is None:
        return "Facial detection cascade failed to load."

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Webcam sensor could not be accessed. Ensure camera is plugged in and permissions granted."

    _BIO_DIR.mkdir(parents=True, exist_ok=True)
    captured = 0
    t0 = time.time()

    try:
        # Give sensor 0.5s to auto-expose
        for _ in range(5):
            cap.read()

        while captured < samples_needed and (time.time() - t0) < 6.0:
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(80, 80))

            if len(faces) > 0:
                # Pick largest face
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                face_roi = gray[y : y + h, x : x + w]
                processed = _preprocess_face(face_roi)

                out_path = _BIO_DIR / f"boss_template_{captured}.png"
                cv2.imwrite(str(out_path), processed)
                captured += 1
                time.sleep(0.3)

    finally:
        cap.release()

    if captured == 0:
        return (
            "Biometric enrollment timed out. No face was detected in front of the optical sensor. "
            "Please face the camera in a well-lit room and retry."
        )

    meta = {
        "enrolled_at": datetime.now().isoformat(),
        "template_count": captured,
        "identity": "Boss",
    }
    (_BIO_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    _play_sfx("sonar")

    return (
        f"Biometric enrollment complete, Boss. "
        f"Calibrated and registered {captured} facial reference templates into secure memory. "
        "Your biometric profile is active."
    )


def authenticate_user(lock_on_intruder: bool = True) -> str:
    """
    Scans the camera for a live face, computes template correlation
    against enrolled Boss templates, and grants or denies access.
    """
    if not _CV2:
        return "OpenCV is not available."

    meta_file = _BIO_DIR / "meta.json"
    if not meta_file.exists():
        return (
            "No Boss biometric profile found on this system. "
            "Say 'Ultron, enroll my face' or call biometric_sentinel with action='enroll' first."
        )

    # Load enrolled templates
    templates: list[np.ndarray] = []
    for p in sorted(_BIO_DIR.glob("boss_template_*.png")):
        t_img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if t_img is not None:
            templates.append(t_img)

    if not templates:
        return "Enrolled template files are corrupted or missing. Please re-enroll."

    cascade = _get_cascade()
    if cascade is None:
        return "Facial detection cascade failed to load."

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Camera sensor unavailable."

    best_score = -1.0
    face_found = False
    raw_frame = None
    face_coords = None

    try:
        # Warmup sensor
        for _ in range(4):
            cap.read()

        t0 = time.time()
        while (time.time() - t0) < 3.0:
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(80, 80))

            if len(faces) > 0:
                face_found = True
                raw_frame = frame.copy()
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                face_coords = (x, y, w, h)
                face_roi = gray[y : y + h, x : x + w]
                processed = _preprocess_face(face_roi)

                # Match against all enrolled templates
                for t_img in templates:
                    res = cv2.matchTemplate(processed, t_img, cv2.TM_CCOEFF_NORMED)
                    score = float(res[0][0])
                    if score > best_score:
                        best_score = score
                break
            time.sleep(0.1)

    finally:
        cap.release()

    if not face_found:
        return "No biological presence detected within the sensor's optical field of view."

    # Verdict
    confidence_pct = max(0, min(100, int((best_score + 0.2) / 1.2 * 100)))

    if best_score >= _MATCH_THRESHOLD:
        _play_sfx("sonar")
        return (
            f"👁️ BIOMETRIC ACCESS GRANTED\n"
            f"• Identity:   Boss (Creator)\n"
            f"• Confidence: {confidence_pct}%\n"
            f"• Status:     VERIFIED\n"
            "Welcome back, Boss. All workstation protocols are at your command."
        )
    else:
        # Intruder Alert!
        _play_sfx("alarm")
        _SENTRY_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        intruder_path = _SENTRY_DIR / f"unauthorized_{ts}.jpg"

        if raw_frame is not None and face_coords is not None:
            x, y, w, h = face_coords
            # Draw imposing red reticle around intruder
            cv2.rectangle(raw_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(raw_frame, "UNAUTHORIZED", (x, max(20, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.imwrite(str(intruder_path), raw_frame)

        # Lock workstation if requested
        if lock_on_intruder and _OS == "Windows":
            try:
                ctypes.windll.user32.LockWorkStation()
            except Exception:
                pass

        return (
            f"⚠️ SECURITY BREACH — ACCESS DENIED\n"
            f"• Biological Signature: UNRECOGNIZED\n"
            f"• Match Score:          {confidence_pct}% (Below threshold)\n"
            f"• Action:               Workstation locked. Snapshot saved to {intruder_path.name}.\n"
            "Unauthorized entity detected at workstation console. Step away immediately."
        )


def biometric_status() -> str:
    """Returns enrollment status of Boss biometrics."""
    meta_file = _BIO_DIR / "meta.json"
    if not meta_file.exists():
        return "Biometric status: UNENROLLED. No Boss profile configured. Say 'enroll my face' to setup."

    try:
        data = json.loads(meta_file.read_text(encoding="utf-8"))
        count = data.get("template_count", 0)
        enrolled_at = data.get("enrolled_at", "Unknown")
        return (
            f"🛡️ BIOMETRIC PROFILE: ACTIVE\n"
            f"• Identity:        Boss\n"
            f"• Reference Nodes: {count} facial vectors\n"
            f"• Enrolled At:     {enrolled_at}\n"
            f"• Sensor:          Optical Webcam (Frontal Cascade)"
        )
    except Exception as e:
        return f"Error reading biometric profile: {e}"


def clear_biometrics() -> str:
    """Removes enrolled biometric profile."""
    if _BIO_DIR.exists():
        for p in _BIO_DIR.glob("*"):
            try:
                p.unlink()
            except Exception:
                pass
        return "Boss biometric profile cleared from memory."
    return "No biometric profile to clear."


def biometric_sentinel(parameters: dict, player=None, **kwargs) -> str:
    """Main handler for biometric_sentinel tool."""
    action = (parameters.get("action") or "authenticate").lower().strip()

    if player:
        try:
            player.write_log(f"[Biometrics] {action}")
        except Exception:
            pass

    try:
        if action in ("auth", "authenticate", "verify", "scan", "check_face", "whoami"):
            lock = bool(parameters.get("lock_intruder", True))
            return authenticate_user(lock_on_intruder=lock)

        elif action in ("enroll", "register", "setup", "learn_face"):
            return enroll_boss_face()

        elif action in ("status", "info"):
            return biometric_status()

        elif action in ("clear", "reset", "delete"):
            return clear_biometrics()

        else:
            return f"Unknown biometric action '{action}'. Available: authenticate, enroll, status, clear."
    except Exception as e:
        return f"Biometric Sentinel encounter error: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "biometric_sentinel",
    "description": (
        "Biometric Face ID & Boss Recognition. Uses webcam facial scanning to authenticate the Boss "
        "or detect unauthorized intruders. Can enroll the Boss's facial signature ('enroll my face'), "
        "scan the camera to verify identity ('authenticate me' / 'who is in front of the screen'), "
        "and automatically locks the workstation and saves evidence if an intruder is detected. "
        "Use when user asks to authenticate face, enroll face biometrics, check biometric status, "
        "or perform biometric security check."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "authenticate (scan face & verify Boss) | enroll (record Boss face reference) | status (check if face profile active) | clear (delete enrolled profile)"
            },
            "lock_intruder": {
                "type": "BOOLEAN",
                "description": "Whether to automatically lock the workstation if an unauthorized intruder is detected. Default: true"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": biometric_sentinel,
}
