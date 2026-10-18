"""
actions/audio_matrix.py — Cinematic Sci-Fi SFX Soundboard & Audio Matrix for Ultron AI.
Procedurally synthesizes and plays movie-grade MCU sound effects in real time:
  - Repulsor Power-up / Ion Charge
  - Red Alert / Lockdown Klaxon Siren
  - Mechanical Servo & Hydraulic Motion
  - Cinematic Sub-bass Earthquake Drop
  - Cybernetic Data Stream / Glitch Burst
  - Ethereal Sonar Detection Ping
  - Power Down / Systems Deactivate
  - Custom audio file playback from sound_effects/ directory
  - Robotic Ultron audio voice modulation & speech delivery
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import math
import os
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import sounddevice as sd
    _SD = True
except ImportError:
    _SD = False

_SAMPLE_RATE = 44100
_BASE_DIR = Path(__file__).resolve().parent.parent
_SFX_DIR = _BASE_DIR / "sound_effects"


# ── Procedural Sci-Fi Sound Synthesizer ──────────────────────────────────────

def _normalize(audio: np.ndarray, peak: float = 0.85) -> np.ndarray:
    """Normalize float32 audio to prevent clipping."""
    max_val = np.max(np.abs(audio))
    if max_val > 1e-5:
        return (audio / max_val * peak).astype(np.float32)
    return audio.astype(np.float32)


def synth_repulsor(duration: float = 0.8) -> np.ndarray:
    """Iron Man / Ultron repulsor charge & ion whine."""
    t = np.linspace(0, duration, int(_SAMPLE_RATE * duration), endpoint=False)
    # Exponential frequency sweep from 60 Hz to 1200 Hz
    f_sweep = 60 + 1140 * (t / duration) ** 2.2
    phase = 2 * np.pi * np.cumsum(f_sweep) / _SAMPLE_RATE
    carrier = np.sin(phase)
    # Resonant harmonic whine
    harm = 0.35 * np.sin(phase * 2.5) + 0.15 * np.sin(phase * 4.0)
    # Rapid attack, intense sustained high note, quick release
    env = np.clip(t / 0.12, 0, 1) * np.exp(-1.5 * (duration - t))
    return _normalize((carrier + harm) * env)


def synth_alarm(pulses: int = 3, pulse_duration: float = 0.28) -> np.ndarray:
    """Deep dual-tone Red Alert klaxon siren."""
    chunks = []
    for _ in range(pulses):
        t = np.linspace(0, pulse_duration, int(_SAMPLE_RATE * pulse_duration), endpoint=False)
        # Dual frequencies with vibrato
        vibrato = 1 + 0.05 * np.sin(2 * np.pi * 12 * t)
        tone1 = np.sin(2 * np.pi * 380 * vibrato * t)
        tone2 = 0.5 * np.sin(2 * np.pi * 570 * vibrato * t)
        env = np.sin(np.pi * (t / pulse_duration)) ** 1.5  # Smooth bell envelope
        chunks.append((tone1 + tone2) * env)
        # Short gap between pulses
        gap = np.zeros(int(_SAMPLE_RATE * 0.08), dtype=np.float32)
        chunks.append(gap)
    return _normalize(np.concatenate(chunks))


def synth_bass_drop(duration: float = 1.2) -> np.ndarray:
    """Cinematic 80 Hz -> 28 Hz earthquake sub-bass drop."""
    t = np.linspace(0, duration, int(_SAMPLE_RATE * duration), endpoint=False)
    f_sweep = 85 * np.exp(-2.2 * t) + 28
    phase = 2 * np.pi * np.cumsum(f_sweep) / _SAMPLE_RATE
    # Slight saturation distortion for warmth
    sub = np.sin(phase) + 0.2 * np.sin(phase * 2)
    env = np.exp(-2.5 * t)
    return _normalize(np.tanh(sub * 1.5) * env)


def synth_servo(duration: float = 0.3) -> np.ndarray:
    """Pneumatic hydraulic hiss + mechanical servo pitch."""
    t = np.linspace(0, duration, int(_SAMPLE_RATE * duration), endpoint=False)
    # White noise for pneumatic release
    noise = np.random.uniform(-0.15, 0.15, len(t))
    # Gear whine frequency curve
    f_whine = 450 + 600 * np.sin(np.pi * (t / duration))
    whine = 0.4 * np.sin(2 * np.pi * np.cumsum(f_whine) / _SAMPLE_RATE)
    env = np.sin(np.pi * (t / duration))
    return _normalize((noise + whine) * env)


def synth_sonar(duration: float = 0.9) -> np.ndarray:
    """Clean high-tech sonar / radar detection ping with resonant decay."""
    t = np.linspace(0, duration, int(_SAMPLE_RATE * duration), endpoint=False)
    freq = 1350 * np.exp(-0.8 * t)
    ping = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * (freq * 2) * t)
    env = np.exp(-5.5 * t)
    return _normalize(ping * env)


def synth_glitch(duration: float = 0.4) -> np.ndarray:
    """Rapid cybernetic data packet stream burst."""
    samples = int(_SAMPLE_RATE * duration)
    audio = np.zeros(samples, dtype=np.float32)
    step = int(_SAMPLE_RATE * 0.02)
    for i in range(0, samples, step):
        chunk_len = min(step, samples - i)
        t = np.linspace(0, chunk_len / _SAMPLE_RATE, chunk_len, endpoint=False)
        f = np.random.choice([1600, 2200, 3100, 4400, 5800, 850])
        tone = np.sin(2 * np.pi * f * t) * np.random.choice([0.4, 0.7, 1.0])
        audio[i : i + chunk_len] = tone
    return _normalize(audio * 0.7)


def synth_power_down(duration: float = 0.9) -> np.ndarray:
    """Dying power whine and systems deactivating."""
    t = np.linspace(0, duration, int(_SAMPLE_RATE * duration), endpoint=False)
    f_sweep = 650 * np.exp(-3.0 * t) + 20
    phase = 2 * np.pi * np.cumsum(f_sweep) / _SAMPLE_RATE
    hum = np.sin(phase) + 0.25 * np.sin(phase * 3)
    env = (1 - t / duration) ** 1.8
    return _normalize(hum * env)


_SYNTH_MAP = {
    "repulsor": synth_repulsor,
    "charge": synth_repulsor,
    "power_up": synth_repulsor,
    "alarm": synth_alarm,
    "klaxon": synth_alarm,
    "red_alert": synth_alarm,
    "lockdown": synth_alarm,
    "bass_drop": synth_bass_drop,
    "drop": synth_bass_drop,
    "thud": synth_bass_drop,
    "servo": synth_servo,
    "hydraulic": synth_servo,
    "mechanical": synth_servo,
    "sonar": synth_sonar,
    "ping": synth_sonar,
    "radar": synth_sonar,
    "glitch": synth_glitch,
    "data": synth_glitch,
    "matrix": synth_glitch,
    "power_down": synth_power_down,
    "shutdown": synth_power_down,
    "deactivate": synth_power_down,
}


# ── Audio Playback Engine ───────────────────────────────────────────────────

def play_sound_async(sound_name: str) -> bool:
    """Play a procedural sound effect or local file asynchronously."""
    if not _SD:
        return False

    name = (sound_name or "repulsor").lower().strip()

    # 1. Check custom user sound file
    custom_wav = _SFX_DIR / f"{name}.wav"
    if custom_wav.exists():
        def _play_wav():
            try:
                import miniaudio
                decoded = miniaudio.decode(custom_wav.read_bytes(), output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1)
                sd.play(np.array(decoded.samples, dtype=np.float32), decoded.sample_rate)
                sd.wait()
            except Exception:
                pass
        threading.Thread(target=_play_wav, daemon=True).start()
        return True

    # 2. Procedural synthesis fallback
    synth_fn = _SYNTH_MAP.get(name, synth_repulsor)
    audio = synth_fn()

    def _play_proc():
        try:
            sd.play(audio, _SAMPLE_RATE)
            sd.wait()
        except Exception:
            pass

    threading.Thread(target=_play_proc, daemon=True).start()
    return True


def play_cinematic_boot() -> str:
    """Dual sequence: repulsor ion charge followed immediately by sub-bass drop."""
    rep = synth_repulsor(0.65)
    gap = np.zeros(int(_SAMPLE_RATE * 0.05), dtype=np.float32)
    drop = synth_bass_drop(1.0)
    combo = np.concatenate([rep, gap, drop])

    def _play():
        try:
            sd.play(combo, _SAMPLE_RATE)
            sd.wait()
        except Exception:
            pass

    threading.Thread(target=_play, daemon=True).start()
    return "Cinematic Boot sequence dispatched. Repulsor ionization and sub-bass harmonics engaged."


def list_available_sfx() -> str:
    """Returns catalog of available sci-fi sound effects."""
    lines = [
        "🔊 ULTRON SCI-FI AUDIO MATRIX CATALOG",
        "─" * 45,
        "PROCEDURAL SOUND GENERATORS:",
        "  • repulsor / charge   — Iron Man / Ultron ion charging whine",
        "  • alarm / klaxon      — Red Alert tactical emergency siren",
        "  • bass_drop / drop    — Deep 30Hz cinematic earthquake impact",
        "  • servo / hydraulic   — Mechanical pneumatic motion whirr",
        "  • sonar / ping        — Crystal high-tech detection radar ping",
        "  • glitch / matrix     — High-speed cybernetic data stream burst",
        "  • power_down          — Descending systems deactivation whine",
        "─" * 45,
        "Say 'Ultron, play sound <name>' or 'Ultron, soundboard alarm' to trigger.",
    ]
    return "\n".join(lines)


def audio_matrix_handler(parameters: dict, player=None, **kwargs) -> str:
    """Main handler for audio_matrix tool."""
    action = (parameters.get("action") or "play").lower().strip()
    sound = (parameters.get("sound") or parameters.get("name") or "repulsor").lower().strip()

    if player:
        try:
            player.write_log(f"[AudioMatrix] {action} {sound}")
        except Exception:
            pass

    try:
        if action in ("play", "sfx", "sound", "trigger"):
            ok = play_sound_async(sound)
            if ok:
                return f"Dispatched cinematic sound effect: '{sound}'."
            return f"Audio output system unavailable."

        elif action in ("boot", "cinematic_boot", "charge_and_drop"):
            return play_cinematic_boot()

        elif action in ("warp", "voice_warp", "movie_voice", "vocoder"):
            from memory.config_manager import get_ultron_voice_warp, save_ultron_voice_warp
            # check parameters for state
            state_param = parameters.get("state")
            if state_param is not None:
                new_state = bool(state_param)
            elif sound in ("off", "disable", "bypass", "false", "stop"):
                new_state = False
            elif sound in ("on", "enable", "activate", "true", "start"):
                new_state = True
            else:
                new_state = not get_ultron_voice_warp()
            save_ultron_voice_warp(new_state)
            status_text = "ENGAGED (Metallic Vibranium Resonance Active)" if new_state else "BYPASSED (Standard Speech Output)"
            play_sound_async("sonar" if new_state else "power_down")
            return f"MCU Ultron Movie Voice Warp: {status_text}."

        elif action in ("list", "catalog", "sounds"):
            return list_available_sfx()

        else:
            return f"Unknown audio matrix action '{action}'. Available: play, boot, list."
    except Exception as e:
        return f"Audio Matrix error: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "audio_matrix",
    "description": (
        "Cinematic Sci-Fi SFX Soundboard & Audio Matrix. Procedurally synthesizes and plays movie-grade "
        "Marvel/Ultron sound effects in real time: 'repulsor' (ion charge whine), 'alarm' (Red Alert klaxon), "
        "'bass_drop' (30Hz earthquake sub-bass), 'servo' (pneumatic mechanical whirr), 'sonar' (high-tech radar ping), "
        "'glitch' (data burst stream), 'power_down' (systems deactivation), or 'boot' (cinematic charge + sub-bass combo). "
        "Use whenever user asks to play a sound effect, sound alarm, repulsor sound, bass drop, or show off audio effects."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "play (play sound effect) | boot (cinematic repulsor + bass drop combo) | list (view all available SFX)"
            },
            "sound": {
                "type": "STRING",
                "description": "Name of the sound effect: 'repulsor', 'alarm', 'bass_drop', 'servo', 'sonar', 'glitch', 'power_down'. Default: 'repulsor'"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": audio_matrix_handler,
}
