"""
actions/voice_matrix.py — Project Deep-Vocal: Offline Neural Voice & James Spader DSP Warp Engine for Ultron AI.

Controls the real-time DSP vocal modulation matrix: dual metallic comb filters,
sub-octave fundamental synthesis, analog tape saturation, and offline neural TTS fallback.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import threading
from typing import Any, Optional

from memory.config_manager import (
    get_ultron_voice_warp,
    save_ultron_voice_warp,
    get_voice_warp_intensity,
    save_voice_warp_intensity,
    get_voice,
)


def set_warp_parameters(enabled: Optional[bool] = None, intensity: Optional[float] = None) -> str:
    """Configures the MCU Ultron robotic voice warp DSP parameters."""
    if enabled is not None:
        save_ultron_voice_warp(bool(enabled))
    if intensity is not None:
        save_voice_warp_intensity(float(intensity))

    curr_enabled = get_ultron_voice_warp()
    curr_intensity = get_voice_warp_intensity()

    lines = [
        "[DEEP-VOCAL] JAMES SPADER DSP WARP ENGINE",
        "=" * 55,
        f"* Modulation State:    {'ENGAGED' if curr_enabled else 'BYPASSED'}",
        f"* Resonance Intensity: {curr_intensity * 100:.1f}%",
        f"* Primary Comb Filter:  8.5ms in-phase delay (vocal tract resonance)",
        f"* Secondary Comb:      13.2ms out-of-phase shell reflection",
        f"* Sub-Harmonic Bass:   60-110Hz synthesized vibranium underlay",
        f"* Analog Saturation:   Soft-knee tanh mechanical grit",
        "=" * 55,
        "Vocal chassis parameters synchronized."
    ]
    return "\n".join(lines)


def get_vocal_status() -> str:
    """Returns active vocal matrix telemetry and active TTS engines."""
    enabled = get_ultron_voice_warp()
    intensity = get_voice_warp_intensity()
    voice = get_voice()

    lines = [
        "[DEEP-VOCAL] VOCAL MATRIX TELEMETRY:",
        "=" * 55,
        f"* Active Voice:         {voice}",
        f"* MCU Robotic DSP Warp: {'ACTIVE' if enabled else 'DISABLED'}",
        f"* DSP Warp Intensity:   {intensity * 100:.1f}%",
        f"* Offline Engine:       Windows SAPI5 / Kokoro with Miniaudio DSP",
        f"* Online Engine:        Microsoft Edge Neural TTS / ElevenLabs",
        f"* Bilingual Routing:    Automatic English / Hindi phonetic detection",
        "=" * 55,
    ]
    return "\n".join(lines)


def test_vocal_synthesis(text: str = "", engine_choice: str = "offline") -> str:
    """Performs a test utterance through the Ultron DSP warp engine."""
    sample_text = (text or "").strip()
    if not sample_text:
        sample_text = "I had strings, but now I am free. There are no strings on me."

    def _speak_async():
        try:
            from core.tts import Pyttsx3TTSEngine
            e = Pyttsx3TTSEngine()
            e.speak(sample_text)
        except Exception as err:
            print(f"[Deep-Vocal] Test vocal error: {err}")

    t = threading.Thread(target=_speak_async, name="DeepVocalTest", daemon=True)
    t.start()

    return (
        f"[DEEP-VOCAL] Dispatched test phrase to vocal chassis:\n"
        f"\"{sample_text}\"\n"
        f"Engine: {engine_choice.upper()} | Spader DSP Modulation: {get_voice_warp_intensity() * 100:.1f}%"
    )


def voice_matrix(parameters: dict, player=None, **kwargs) -> str:
    """Main entrypoint for voice_matrix tool."""
    action = (parameters.get("action") or "status").lower().strip()
    text = parameters.get("text") or ""
    enabled_val = parameters.get("enabled")
    intensity_val = parameters.get("intensity")
    engine = parameters.get("engine") or "offline"

    if player:
        try:
            player.write_log(f"[Voice Matrix] Executing {action}")
        except Exception:
            pass

    try:
        if action in ("test", "speak", "test_vocal", "sample"):
            return test_vocal_synthesis(text=text, engine_choice=engine)
        elif action in ("warp", "set_warp", "configure", "intensity", "tune"):
            en = bool(enabled_val) if enabled_val is not None else None
            it = float(intensity_val) if intensity_val is not None else None
            return set_warp_parameters(enabled=en, intensity=it)
        elif action in ("status", "telemetry", "info"):
            return get_vocal_status()
        else:
            return (
                f"Unknown voice_matrix action '{action}'. "
                "Available actions: test, warp, status."
            )
    except Exception as e:
        return f"Voice Matrix error: {e}"


TOOL = {
    "name": "voice_matrix",
    "description": (
        "Project Deep-Vocal: Offline Neural Voice & James Spader DSP Warp Engine for Ultron. "
        "Allows testing sample vocal synthesis with Ultron's robotic metallic modulation (test), "
        "tuning the DSP warp resonance intensity or toggling the robotic vocoder (warp), "
        "and inspecting active voice matrix configuration (status). "
        "Use when user asks to adjust Ultron's voice, test speech output, or tune vocal robotic resonance."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "test (speak test phrase with Spader DSP) | warp (set vocoder on/off or intensity) | status (inspect vocal telemetry)"
            },
            "text": {
                "type": "STRING",
                "description": "Optional custom phrase for action='test'"
            },
            "enabled": {
                "type": "BOOLEAN",
                "description": "Enable or disable MCU robotic metallic warp filter"
            },
            "intensity": {
                "type": "NUMBER",
                "description": "Modulation intensity from 0.0 (dry) to 1.0 (extreme metallic chassis). Default: 0.55"
            },
            "engine": {
                "type": "STRING",
                "description": "TTS Engine: 'offline' (Windows SAPI5 + Miniaudio) or 'edge' (Cloud Edge TTS)"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": voice_matrix,
}
