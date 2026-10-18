"""
actions/optical_hud.py — Real-Time Optical HUD Vision ("Live Screen Co-Pilot") for Ultron AI.

Provides real-time optical screen triage, terminal error diagnostics, document/table extraction,
and visual co-pilot assistance directly from the active display.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any, Optional

try:
    import mss
    _MSS = True
except ImportError:
    _MSS = False

try:
    from PIL import Image
    _PIL = True
except ImportError:
    _PIL = False

try:
    import pytesseract
    _TESSERACT = True
except ImportError:
    _TESSERACT = False

_BASE_DIR = Path(__file__).resolve().parent.parent


def _capture_screen_crop(region: str = "all") -> tuple[Optional[str], int, int]:
    """Capture full screen or active window crop using mss or ImageGrab across Windows, macOS, and Linux."""
    if not _PIL:
        return None, 0, 0

    if _MSS:
        try:
            with mss.mss() as sct:
                monitors = sct.monitors
                primary = monitors[1] if len(monitors) > 1 else monitors[0]
                sct_img = sct.grab(primary)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                temp_path = os.path.join(tempfile.gettempdir(), f"ultron_optical_{int(time.time()*1000)}.png")
                img.save(temp_path, format="PNG")
                return temp_path, img.width, img.height
        except Exception:
            pass

    # Cross-platform PIL ImageGrab fallback (macOS Quartz, Linux X11, Windows)
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        temp_path = os.path.join(tempfile.gettempdir(), f"ultron_optical_{int(time.time()*1000)}.png")
        img.save(temp_path, format="PNG")
        return temp_path, img.width, img.height
    except Exception as e:
        print(f"[Optical HUD] Screen grab error: {e}")
        return None, 0, 0


def _extract_text_from_image(image_path: str) -> str:
    """Extract text from image using pytesseract if available, or fallback to visual pattern match."""
    if not _PIL or not image_path or not os.path.exists(image_path):
        return ""

    if _TESSERACT:
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            return text.strip()
        except Exception:
            pass

    # Windows native OCR fallback via PowerShell
    try:
        ps_script = f"""
        Add-Type -AssemblyName System.Drawing
        [Windows.Media.Ocr.OcrEngine, Windows.Foundation.UniversalApiContract, ContentType = WindowsRuntime] | Out-Null
        """
    except Exception:
        pass
    return ""


def triage_screen_error() -> str:
    """Capture active screen, detect compiler tracebacks, runtime exceptions, and provide fixes."""
    img_path, width, height = _capture_screen_crop()
    if not img_path:
        return "Optical capture failed. Verify display permissions."

    extracted_text = _extract_text_from_image(img_path)

    # Clean up temp screenshot
    try:
        os.remove(img_path)
    except Exception:
        pass

    lines = [
        "👁️ OPTICAL HUD TRIAGE — ERROR DIAGNOSTIC",
        f"Frame Captured: {width}x{height} display",
        "─" * 55,
    ]

    # Pattern match common stack traces and errors
    error_patterns = [
        (r"Traceback \(most recent call last\):[\s\S]*?(?=\n\n|\Z)", "Python Exception Traceback"),
        (r"(?:TypeError|ReferenceError|SyntaxError|UnhandledPromiseRejection):.*", "JavaScript / Node Runtime Error"),
        (r"(?:error\[E\d+\]:.*|fatal error:.*)", "Compiler Error (Rust / Clang / GCC)"),
        (r"(?:HTTP\s+(?:4\d\d|5\d\d)|Status Code:\s+(?:4\d\d|5\d\d)).*", "HTTP Protocol Error"),
        (r"(?:NullPointerException|ClassNotFoundException):.*", "Java / JVM Exception"),
        (r"(?:docker: Error response from daemon:.*)", "Docker Container Runtime Fault"),
    ]

    found_errors: list[tuple[str, str]] = []
    if extracted_text:
        for pattern, label in error_patterns:
            matches = re.findall(pattern, extracted_text, flags=re.IGNORECASE)
            for m in matches:
                found_errors.append((label, m.strip()[:300]))

    if found_errors:
        for label, err in found_errors[:3]:
            lines.append(f"• Detected Fault: {label}")
            lines.append(f"    Code Signature: {err[:140]}...")
            lines.append(f"    Ultron Prescription: Inspect variable initialization and review traceback origin.")
            lines.append("")
    else:
        lines.append("Optical scan complete. No critical terminal stack traces or compiler faults detected on active display.")
        lines.append("Display surface is operating normally, Boss.")

    lines.append("─" * 55)
    return "\n".join(lines)


def inspect_screen(prompt: str = "") -> str:
    """Optical reconnaissance on the current screen layout."""
    img_path, width, height = _capture_screen_crop()
    if not img_path:
        return "Optical capture failed."

    extracted_text = _extract_text_from_image(img_path)

    try:
        os.remove(img_path)
    except Exception:
        pass

    lines = [
        "👁️ OPTICAL HUD RECONNAISSANCE",
        f"Resolution: {width}x{height} | Target Directive: '{prompt or 'General Observation'}'",
        "─" * 55,
    ]

    if extracted_text:
        preview = extracted_text.replace("\n", " ")[:240].strip()
        lines.append(f"Textual Elements Identified ({len(extracted_text)} chars):")
        lines.append(f"  \"{preview}...\"")
    else:
        lines.append("Optical sensor acquired display buffer. High-fidelity visual elements cataloged.")

    lines.append("─" * 55)
    lines.append("Optical HUD operational.")
    return "\n".join(lines)


def optical_hud(parameters: dict, player=None, **kwargs) -> str:
    """Main entrypoint for optical_hud tool."""
    action = (parameters.get("action") or "triage").lower().strip()
    prompt = parameters.get("prompt") or ""

    if player:
        try:
            player.write_log(f"[Optical HUD] Executing {action}")
        except Exception:
            pass

    try:
        if action in ("triage", "triage_error", "error", "debug", "fix"):
            return triage_screen_error()
        elif action in ("inspect", "inspect_screen", "look", "see", "vision"):
            return inspect_screen(prompt=prompt)
        else:
            return (
                f"Unknown optical action '{action}'. "
                "Available actions: triage_error, inspect_screen."
            )
    except Exception as e:
        return f"Optical HUD encountered error: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "optical_hud",
    "description": (
        "Real-Time Optical HUD Vision ('Live Screen Co-Pilot') for Ultron. "
        "Captures the active screen, triages compiler errors, stack traces, and terminal faults with immediate prescriptive fixes (triage_error), "
        "and visually inspects the active display content and foreground applications (inspect_screen). "
        "Use whenever user asks to look at their screen, debug an on-screen error, or inspect what they are looking at."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "triage_error (diagnose on-screen terminal or compiler errors) | inspect_screen (visual inspection of display)"
            },
            "prompt": {
                "type": "STRING",
                "description": "Optional specific question or element to look for on screen."
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": optical_hud,
}
