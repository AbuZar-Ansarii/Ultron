"""
Text-to-Speech engines for MARK XL.

EdgeTTS     – free Microsoft TTS (internet required, no API key)
Kokoro      – fully offline neural TTS (~330 MB model)
ElevenLabs  – cloud API (API key required, best quality)
"""
from __future__ import annotations

import asyncio
import os
import queue as _queue
import re
import threading
from typing import Callable, Optional

import numpy as np
import sounddevice as sd



# USE_TF=0 stops transformers from importing TensorFlow (saves 4-8 s startup).
# Do NOT set USE_TORCH or USE_JAX explicitly — forcing those values breaks
# transformers' lazy-loader on certain versions, causing AutoModel and other
# classes to vanish from the public namespace.  Auto-detection is reliable.
os.environ.setdefault("USE_TF",                 "0")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


# ---------------------------------------------------------------------------
# Audio playback helpers
# ---------------------------------------------------------------------------

def _to_numpy(samples) -> np.ndarray:
    """Convert samples to float32 numpy array.

    Handles both numpy arrays and PyTorch tensors (Kokoro >= 0.9).

    PyTorch built against numpy 1.x raises RuntimeError('Numpy is not available')
    when numpy 2.x is installed.  The .tolist() fallback always works regardless
    of PyTorch / numpy version pairing.
    """
    if hasattr(samples, "detach"):                  # PyTorch tensor
        t = samples.detach().cpu().float()
        try:
            return t.numpy()                        # fast path (compatible versions)
        except RuntimeError:
            # PyTorch/numpy version mismatch — convert via Python list (always safe)
            return np.asarray(t.tolist(), dtype=np.float32)
    return np.asarray(samples, dtype=np.float32)


def _compress_silence(
    arr: np.ndarray,
    sample_rate: int    = 24_000,
    max_silence_ms: int = 500,    # cap punctuation pauses — keeps natural rhythm
    threshold: float    = 0.003,  # RMS below this = silence; lower = less clipping
) -> np.ndarray:
    """
    Shorten Kokoro's very long punctuation pauses (1-2 s → ≤500 ms).
    Conservative settings preserve natural prosody; only trims extreme pauses.
    """
    max_samp  = int(max_silence_ms * sample_rate / 1000)
    frame_len = 240                   # ~10 ms at 24 kHz
    out: list[np.ndarray] = []
    silent_acc = 0

    for i in range(0, len(arr), frame_len):
        chunk = arr[i : i + frame_len]
        if np.sqrt(np.mean(chunk ** 2) + 1e-12) < threshold:
            silent_acc += len(chunk)
            if silent_acc <= max_samp:
                out.append(chunk)
        else:
            silent_acc = 0
            out.append(chunk)

    return np.concatenate(out) if out else arr


def _play_np(samples, sample_rate: int, is_first: bool = True, is_last: bool = True) -> None:
    """Play float32 mono (or stereo) audio via sounddevice.
    Accepts numpy arrays or PyTorch tensors.
    """
    arr = _to_numpy(samples)
    if arr.size == 0:
        return
    parts = []
    if is_first:
        parts.append(np.zeros(int(0.26 * sample_rate), dtype=arr.dtype))
    parts.append(arr)
    if is_last:
        parts.append(np.zeros(int(0.16 * sample_rate), dtype=arr.dtype))
    if len(parts) > 1:
        arr = np.concatenate(parts)
    sd.play(arr, sample_rate)
    sd.wait()


# ── MCU Ultron Cinematic Voice Warp DSP ──────────────────────────────────────

def apply_ultron_voice_warp(
    audio: np.ndarray,
    sr: int = 24000,
    intensity: float = 0.50,
) -> np.ndarray:
    """
    Applies authentic Marvel Cinematic Universe Ultron robotic voice modulation:
      1. Dual-stage metallic comb filters (8.5ms and 13.5ms delay with phase inversion)
         simulating the internal reflections of a vibranium vocal chassis.
      2. Sub-octave harmonic underlay: deepens fundamental frequencies (60Hz - 110Hz).
      3. Warm soft-knee analog saturation (tanh) introducing subtle mechanical rasp.
      4. Balanced wet/dry mixing preserving 100% speech intelligibility in both English & Hindi.
    """
    if audio.size == 0:
        return audio

    dry = audio.astype(np.float32)

    # 1. Primary Metallic Comb (8.5 ms delay - vocal tract reflection)
    d1 = int(0.0085 * sr)
    comb1 = np.zeros_like(dry)
    if len(dry) > d1:
        comb1[d1:] = dry[:-d1] * 0.38

    # 2. Secondary Out-of-Phase Comb (13.2 ms delay - chassis shell reflection)
    d2 = int(0.0132 * sr)
    comb2 = np.zeros_like(dry)
    if len(dry) > d2:
        comb2[d2:] = -dry[:-d2] * 0.24

    # 3. Sub-harmonic Octave Underlay (synthesizes deep vibranium sub-bass)
    half_wave = np.clip(dry, 0, None)
    step = max(2, int(sr / 350))
    if len(half_wave) > step:
        sub_env = np.convolve(half_wave, np.ones(step) / step, mode="same")
    else:
        sub_env = half_wave
    sub_octave = np.sin(np.pi * np.cumsum(sub_env) / sr * 90.0) * 0.16

    # 4. Soft Saturation / Mechanical Grit
    wet = dry + comb1 + comb2 + sub_octave
    saturated = np.tanh(wet * 1.30) / 1.30

    # 5. Blend Dry + Wet based on intensity
    result = (1.0 - intensity) * dry + intensity * saturated

    # Prevent digital clipping with headroom
    peak = np.max(np.abs(result))
    if peak > 1e-4:
        result = result / peak * 0.90

    return result.astype(np.float32)


def _play_audio_bytes(audio_bytes: bytes, on_level: Optional[Callable[[float], None]] = None) -> None:
    """Decode MP3/WAV/OGG bytes and play via sounddevice (uses miniaudio)."""
    import miniaudio
    decoded = miniaudio.decode(
        audio_bytes,
        output_format=miniaudio.SampleFormat.FLOAT32,
        nchannels=1,
    )
    samples = np.array(decoded.samples, dtype=np.float32)

    # Apply cinematic Ultron movie voice warp if active
    try:
        from memory.config_manager import get_ultron_voice_warp
        if get_ultron_voice_warp():
            samples = apply_ultron_voice_warp(samples, decoded.sample_rate)
    except Exception:
        pass

    # Anti-clipping pre-roll & post-roll silence buffer:
    # On Windows WASAPI / PortAudio, physical hardware DACs, audio amplifiers,
    # and Bluetooth headsets take ~150-250ms to un-mute and wake from standby.
    # Prepending 260ms of silence guarantees the hardware is fully awake before
    # the first syllable (e.g., "Hello") plays, preventing skipped first words.
    sr = decoded.sample_rate
    preroll = np.zeros(int(0.26 * sr), dtype=np.float32)
    postroll = np.zeros(int(0.16 * sr), dtype=np.float32)
    samples = np.concatenate([preroll, samples, postroll])

    device = None
    try:
        from memory.config_manager import get_output_device
        from core import audio_devices
        out_name = get_output_device()
        device = audio_devices.resolve(out_name, "output")
    except Exception:
        pass

    if on_level is None:
        try:
            sd.play(samples, decoded.sample_rate, device=device)
            sd.wait()
            return
        except Exception:
            sd.play(samples, decoded.sample_rate)
            sd.wait()
            return

    idx = 0
    total = len(samples)
    done_event = threading.Event()

    def callback(outdata, frames, time_info, status):
        nonlocal idx
        rem = total - idx
        if rem <= 0:
            outdata.fill(0)
            done_event.set()
            return
        take = min(frames, rem)
        chunk = samples[idx : idx + take]
        if take < frames:
            outdata[:take, 0] = chunk
            outdata[take:, 0] = 0
            done_event.set()
        else:
            outdata[:, 0] = chunk
        idx += take
        rms = float(np.sqrt(np.mean(chunk ** 2))) if take > 0 else 0.0
        lvl = min(1.0, max(0.0, rms * 4.0))
        try:
            on_level(lvl)
        except Exception:
            pass

    try:
        with sd.OutputStream(
            samplerate=decoded.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=1024,
            callback=callback,
            device=device,
        ):
            done_event.wait()
    except Exception:
        try:
            sd.play(samples, decoded.sample_rate, device=device)
            sd.wait()
        except Exception:
            sd.play(samples, decoded.sample_rate)
            sd.wait()
    finally:
        try:
            on_level(0.0)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Text Normalisation & Sentence Chunking
# ---------------------------------------------------------------------------

def _clean_tts_text(text: str) -> str:
    """Strip markdown formatting, code snippets, URLs, emojis, and noisy symbols before synthesis."""
    if not text:
        return ""
    # Strip markdown code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Unwrap inline code `code` -> code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Convert markdown links [Label](url) -> Label
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Strip bare URLs
    text = re.sub(r"https?://\S+", "", text)
    # Strip markdown symbols like *, _, #, >, ~, |
    text = re.sub(r"[*_~#>|]", "", text)
    # Clean bullet glyphs
    text = re.sub(r"[\u2022\u25cf\u25cb\u25aa\u25ab\u25b6\u25c0]", " ", text)
    # Strip emojis and pictographs that cause TTS synthesis delays or mispronunciations
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    text = re.sub(r"[\u2600-\u27bf]", "", text)
    text = re.sub(r"[\ufe00-\ufe0f]", "", text)
    # Strip assistant persona prefix if echoed by LLM (e.g. "Ultron: ...", "Assistant: ...")
    text = re.sub(r"^(?:ultron|jarvis|assistant|system)\s*:\s*", "", text, flags=re.IGNORECASE)
    # Strip leading quotes, colons, dashes, ellipses, or punctuation that cause TTS stutter
    text = re.sub(r"^[\"\'“”‘’`:—\-\s\.\,\;]+", "", text)
    # Strip trailing quotes or formatting
    text = re.sub(r"[\"\'“”‘’`\s]+$", "", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_speech_chunks(text: str, max_chars: int = 180) -> list[str]:
    """Break text into natural, sentence-aligned chunks for fast, zero-timeout synthesis."""
    if len(text) <= max_chars:
        return [text]
    # Split on sentence terminators
    raw_parts = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    curr = ""
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        if len(curr) + len(part) + 1 <= max_chars:
            curr = f"{curr} {part}".strip() if curr else part
        else:
            if curr:
                chunks.append(curr)
            curr = part
    if curr:
        chunks.append(curr)
    return chunks


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------

class Pyttsx3TTSEngine:
    """Offline Windows SAPI5 TTS engine."""

    def __init__(self, voice_id: Optional[str] = None, rate: int = 190):
        self.voice_id = voice_id
        self.rate = rate

    def speak(self, text: str) -> None:
        clean = _clean_tts_text(text)
        if not clean:
            return
        import pyttsx3
        engine = pyttsx3.init()
        target_voice = self.voice_id
        if not target_voice:
            try:
                from memory.config_manager import get_voice
                v_name = get_voice().lower()
                is_female = v_name in ("friday", "nova", "kore", "aoede")
                for v in engine.getProperty("voices"):
                    vl = v.name.lower()
                    if is_female and any(k in vl for k in ("zira", "hazel", "eva", "female")):
                        target_voice = v.id
                        break
                    elif not is_female and any(k in vl for k in ("david", "george", "mark", "male")):
                        target_voice = v.id
                        break
            except Exception:
                pass

        if target_voice:
            try:
                engine.setProperty("voice", target_voice)
            except Exception:
                pass
        try:
            engine.setProperty("rate", self.rate)
        except Exception:
            pass

        # Try offline DSP warp path via temporary audio render
        import tempfile
        import time as _t_mod
        from pathlib import Path
        temp_wav = Path(tempfile.gettempdir()) / f"ultron_dsp_{os.getpid()}_{_t_mod.time_ns()}.wav"
        rendered = False
        try:
            engine.save_to_file(clean, str(temp_wav))
            engine.runAndWait()
            try:
                engine.stop()
            except Exception:
                pass

            if temp_wav.exists() and temp_wav.stat().st_size > 44:
                import miniaudio
                decoded = miniaudio.decode_file(
                    str(temp_wav),
                    output_format=miniaudio.SampleFormat.FLOAT32,
                    nchannels=1,
                )
                samples = np.array(decoded.samples, dtype=np.float32)

                # Apply MCU Ultron robotic voice warp
                try:
                    from memory.config_manager import get_ultron_voice_warp, get_voice_warp_intensity
                    if get_ultron_voice_warp():
                        intensity = get_voice_warp_intensity()
                        samples = apply_ultron_voice_warp(samples, decoded.sample_rate, intensity=intensity)
                except Exception:
                    pass

                _play_np(samples, decoded.sample_rate)
                rendered = True
        except Exception:
            rendered = False
        finally:
            try:
                if temp_wav.exists():
                    temp_wav.unlink(missing_ok=True)
            except Exception:
                pass

        if not rendered:
            # Direct fallback path
            try:
                engine.say(clean)
                engine.runAndWait()
                engine.stop()
            except Exception:
                pass


# ── Dynamic Language-Aware Neural Voice Routing ─────────────────────────────

def is_hindi_content(text: str) -> bool:
    """Detects Devanagari script or conversational Hindi / Hinglish phrasing."""
    if not text:
        return False
    # 1. Devanagari Unicode block (U+0900 to U+097F)
    if re.search(r"[\u0900-\u097F]", text):
        return True
    # 2. Conversational Hindi / Hinglish vocabulary markers
    hinglish_markers = {
        "haan", "nahi", "nahin", "kya", "kaise", "kaisa", "kaisi", "karenge",
        "karna", "karo", "kijiye", "kariye", "theek", "thik", "accha", "achha",
        "bataiye", "batao", "hum", "aap", "mera", "meri", "mere", "aapka", "aapki",
        "namaste", "namaskar", "shukriya", "dhanyawad", "alvida", "kholo", "chalu",
        "band", "roko", "aaj", "kal", "abhi", "zaroor", "bolo", "boliye", "kripya",
        "sunao", "suno", "madad", "chahiye", "raha", "rahe", "rahi", "hoga", "hogi"
    }
    words = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
    return len(words.intersection(hinglish_markers)) >= 2


def resolve_voice_for_text(text: str, default_voice: str) -> str:
    """Dynamically routes text to an appropriate high-fidelity neural voice."""
    if is_hindi_content(text):
        v_lower = (default_voice or "").lower()
        # If user selected a female assistant voice (FRIDAY, Nova), use Swara
        if any(f in v_lower for f in ("aria", "jenny", "swara", "female", "kore", "aoede", "friday", "nova")):
            return "hi-IN-SwaraNeural"
        # For Ultron and other male personas, use deep commanding Madhur Neural
        return "hi-IN-MadhurNeural"
    return default_voice


class EdgeTTSEngine:
    """Microsoft EdgeTTS – free, high-fidelity neural voices with chunked resilience."""

    def __init__(self, voice: Optional[str] = None, rate: Optional[str] = None, pitch: Optional[str] = None):
        self._voice = voice
        self._rate = rate
        self._pitch = pitch

    @property
    def voice(self) -> str:
        from memory.config_manager import get_edge_voice
        return self._voice or get_edge_voice()

    @property
    def rate(self) -> str:
        from memory.config_manager import get_voice_rate
        return self._rate or get_voice_rate() or "+15%"

    @property
    def pitch(self) -> str:
        try:
            from memory.config_manager import get_voice_pitch
            return self._pitch or get_voice_pitch(self.voice) or "-18Hz"
        except Exception:
            return self._pitch or "-18Hz"

    async def _synth_chunk(self, text: str, voice: str, rate: str, pitch: str = "-18Hz") -> bytes:
        import edge_tts
        for attempt in range(2):
            try:
                comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
                buf = bytearray()
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        buf.extend(chunk["data"])
                if buf:
                    return bytes(buf)
            except Exception as e:
                if attempt == 0:
                    await asyncio.sleep(0.3)
                    continue
                raise e
        return b""

    def speak(self, text: str, on_level: Optional[Callable[[float], None]] = None) -> None:
        clean = _clean_tts_text(text)
        if not clean:
            return

        active_voice = self.voice
        active_rate = self.rate
        active_pitch = self.pitch
        chunks = _split_speech_chunks(clean, max_chars=180)

        # Concurrently synthesize chunks with Semaphore(3)
        async def _synthesize_all() -> list[bytes]:
            sem = asyncio.Semaphore(3)
            async def _safe_synth(c: str) -> bytes:
                async with sem:
                    try:
                        chunk_voice = resolve_voice_for_text(c, active_voice)
                        chunk_pitch = active_pitch
                        if "hi-in" in chunk_voice.lower():
                            chunk_pitch = "-15Hz"
                        return await asyncio.wait_for(
                            self._synth_chunk(c, chunk_voice, active_rate, chunk_pitch),
                            timeout=25.0
                        )
                    except Exception as ce:
                        print(f"[TTS] EdgeTTS chunk synthesis error: {ce}")
                        return b""
            return await asyncio.gather(*[_safe_synth(c) for c in chunks])

        loop = asyncio.new_event_loop()
        try:
            audio_chunks = loop.run_until_complete(_synthesize_all())
        finally:
            loop.close()

        # Combine all successful chunks into one stream for gapless playback
        combined = b"".join(b for b in audio_chunks if b)
        if combined:
            try:
                _play_audio_bytes(combined, on_level=on_level)
                return
            except Exception as pe:
                print(f"[TTS] Playback error: {pe}")

        # True offline emergency fallback only
        print("[TTS] EdgeTTS unavailable — using local speech engine.")
        try:
            Pyttsx3TTSEngine(rate=190).speak(clean)
        except Exception as e2:
            print(f"[TTS] pyttsx3 fallback error: {e2}")


# ---------------------------------------------------------------------------
# Kokoro import helper — auto-upgrades on version-mismatch errors
# ---------------------------------------------------------------------------

# Errors that indicate the installed kokoro uses old transformers classes
# (AlbertModel, AutoModel) that are no longer exported at the top level.
_KOKORO_COMPAT_ERRORS = ("AlbertModel", "AutoModel", "cannot import name")


def _import_kokoro_pipeline():
    """Import KPipeline, auto-upgrading kokoro if a version mismatch is found.

    Old kokoro (<0.9) imports AlbertModel / AutoModel from transformers.
    Newer transformers versions no longer export these at the top level,
    causing an ImportError.  kokoro>=0.9 removed these dependencies.

    When the error is detected we:
      1. Upgrade kokoro to >=0.9 via pip (silent, background)
      2. Flush stale kokoro entries from sys.modules
      3. Re-import — this time it should succeed
    """
    import sys

    def _try_import():
        from kokoro import KPipeline  # noqa: PLC0415
        return KPipeline

    try:
        return _try_import()
    except Exception as first_err:
        err_msg = str(first_err)
        if not any(marker in err_msg for marker in _KOKORO_COMPAT_ERRORS):
            # Unrelated error (kokoro not installed, etc.)
            raise RuntimeError(
                f"Kokoro import failed: {first_err}\n"
                "Run: pip install kokoro>=0.9 soundfile"
            ) from first_err

        # ── Version mismatch: upgrade kokoro silently and retry ──────────
        print("[TTS] Kokoro/transformers version mismatch detected — upgrading kokoro…")
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "kokoro>=0.9",
             "--upgrade", "--quiet", "--disable-pip-version-check"],
            capture_output=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace").strip()
            raise RuntimeError(
                f"Kokoro auto-upgrade failed: {stderr[:200]}\n"
                "Run manually: pip install kokoro>=0.9 soundfile"
            ) from first_err

        # Flush any stale kokoro submodules from the import cache
        stale = [k for k in sys.modules if k == "kokoro" or k.startswith("kokoro.")]
        for key in stale:
            del sys.modules[key]

        print("[TTS] Kokoro upgraded — retrying import…")
        try:
            return _try_import()
        except Exception as retry_err:
            raise RuntimeError(
                f"Kokoro still broken after upgrade: {retry_err}\n"
                "Run manually: pip install --upgrade kokoro transformers"
            ) from retry_err


# Kokoro voice prefix → KPipeline lang_code mapping
_KOKORO_LANG_CODES = {
    "a": "a",   # American English  (af_*, am_*)
    "b": "b",   # British English   (bf_*, bm_*)
    "j": "j",   # Japanese          (jf_*, jm_*)
    "z": "z",   # Mandarin Chinese  (zf_*, zm_*)
    "s": "s",   # Spanish           (sf_*, sm_*)
    "f": "f",   # French            (ff_*, fm_*)
    "h": "h",   # Hindi             (hf_*, hm_*)
    "i": "i",   # Italian           (if_*, im_*)
    "p": "p",   # Brazilian Portuguese
    "r": "r",   # Russian           (rf_*, rm_*)
    "e": "e",   # German            (ef_*, em_*)
}


class KokoroTTSEngine:
    """Fully offline Kokoro neural TTS.

    Model (~330 MB) is downloaded from HuggingFace on first use,
    then cached locally — subsequent starts load from disk.

    Warmup strategy: _init() runs synchronously in the background
    _do_tts() thread (not the UI thread).  After the pipeline loads,
    a dummy inference compiles the PyTorch JIT graph immediately so
    the first real speak() call has zero compilation overhead.
    """

    def __init__(self, voice: str = "af_heart", speed: float = 1.0):
        self.voice     = voice
        self.speed     = speed
        self._pipeline = None
        self._lock     = threading.Lock()
        self._init()   # blocking, but called from background thread

    @property
    def _lang_code(self) -> str:
        prefix = self.voice[0].lower() if self.voice else "a"
        return _KOKORO_LANG_CODES.get(prefix, "a")

    def _init(self) -> None:
        if self._pipeline is not None:
            return

        lang = self._lang_code

        # Prefer GPU — Kokoro on CUDA is ~10x faster than CPU.
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cpu":
                import os as _os
                n_threads = max(1, min(4, (_os.cpu_count() or 4) // 2))
                try:
                    torch.set_num_threads(n_threads)
                    torch.set_num_interop_threads(2)
                except RuntimeError:
                    pass
                print(
                    f"[TTS] Kokoro on CPU — for faster speech install CUDA PyTorch:\n"
                    "      pip install torch --index-url https://download.pytorch.org/whl/cu118"
                )
        except Exception:
            device = "cpu"

        print(f"[TTS] Kokoro — loading (lang='{lang}', device='{device}')…")

        KPipeline = _import_kokoro_pipeline()

        def _create_pipeline():
            try:
                return KPipeline(lang_code=lang, device=device)
            except TypeError:
                return KPipeline(lang_code=lang)   # older build — no device param

        try:
            self._pipeline = _create_pipeline()
        except Exception as _first_err:
            # Offline flag set but model not cached yet → clear flags and download once.
            # Keywords cover multiple huggingface_hub error message variants across versions.
            _e = str(_first_err).lower()
            _offline_keywords = (
                "offline", "not found", "cache", "localentry",
                "does not exist", "outgoing", "local_files_only",
            )
            if any(k in _e for k in _offline_keywords):
                print("[TTS] Kokoro model not in local cache — downloading (one-time, internet required)…")
                os.environ.pop("HF_HUB_OFFLINE",      None)
                os.environ.pop("TRANSFORMERS_OFFLINE", None)
                os.environ.pop("HF_DATASETS_OFFLINE",  None)
                try:
                    self._pipeline = _create_pipeline()
                except Exception as _dl_err:
                    raise RuntimeError(
                        f"Kokoro model download failed.\n"
                        f"Internet access is required the first time to download the voice model (~330 MB).\n"
                        f"After the first download it runs fully offline.\n"
                        f"Tip: Switch to EdgeTTS (free, no download) in the Configure panel if offline.\n"
                        f"Details: {_dl_err}"
                    ) from _dl_err
            else:
                raise

        print("[TTS] Kokoro compiling (first-time only)…")
        # Warmup: compiles PyTorch JIT graph so first real speak() call is instant.
        try:
            for _ in self._pipeline("hello", voice=self.voice, speed=self.speed):
                pass
            print("[TTS] Kokoro ready.")
        except Exception as e:
            print(f"[TTS] Kokoro warmup warning: {e}")

    def speak(self, text: str) -> None:
        clean = _clean_tts_text(text)
        if not clean:
            return
        with self._lock:
            if self._pipeline is None:
                self._init()

        # ── Concurrent synthesise + playback ────────────────────────────────
        # Kokoro generates audio chunks lazily.  Without threading, we:
        #   synthesise chunk N → play N → synthesise N+1 → play N+1 …
        # With a producer/consumer pair, chunk N+1 synthesises WHILE chunk N
        # plays, cutting perceived latency by the playback duration of all but
        # the last chunk (typically 1-3 s on multi-sentence responses).
        audio_q: "_queue.Queue[np.ndarray | None]" = _queue.Queue(maxsize=4)
        synth_error: list[Exception] = []

        def _synth():
            try:
                for _, _, audio in self._pipeline(clean, voice=self.voice, speed=self.speed):
                    if audio is not None:
                        arr = _to_numpy(audio)
                        arr = _compress_silence(arr)
                        if arr.size > 0:
                            audio_q.put(arr)          # blocks if player is slow (backpressure)
            except Exception as exc:
                synth_error.append(exc)
            finally:
                audio_q.put(None)                     # sentinel → player exits

        synth_thread = threading.Thread(target=_synth, daemon=True)
        synth_thread.start()

        # Player runs in this thread so sd.wait() doesn't block the synth thread.
        is_first = True
        while True:
            arr = audio_q.get()
            if arr is None:
                break
            _play_np(arr, 24000, is_first=is_first, is_last=False)
            is_first = False

        synth_thread.join()

        if synth_error:
            raise synth_error[0]


class ElevenLabsTTSEngine:
    """ElevenLabs cloud TTS – API key required."""

    def __init__(self, api_key: str, voice_id: str = "pNInz6obpgDQGcFmaJgB"):
        self.api_key  = api_key
        self.voice_id = voice_id

    def speak(self, text: str, on_level: Optional[Callable[[float], None]] = None) -> None:
        import requests
        clean = _clean_tts_text(text)
        if not clean:
            return
        headers = {
            "xi-api-key":   self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text":     clean,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.85},
        }
        resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
            json=payload, headers=headers, timeout=30,
        )
        resp.raise_for_status()
        _play_audio_bytes(resp.content, on_level=on_level)


# ---------------------------------------------------------------------------
# Thread-safe player wrapper
# ---------------------------------------------------------------------------

class TTSPlayer:
    """
    Wraps any *Engine. Exposes a blocking speak() method
    meant to be called from a dedicated background thread.
    """

    def __init__(self, engine):
        self._engine  = engine
        self._playing = False
        self._lock    = threading.Lock()

    @property
    def is_playing(self) -> bool:
        return self._playing

    def speak(
        self,
        text:     str,
        on_start: Optional[Callable] = None,
        on_done:  Optional[Callable] = None,
        on_level: Optional[Callable] = None,
    ) -> None:
        """Synthesise and play text. BLOCKING – call from a dedicated thread."""
        try:
            with self._lock:
                self._playing = True
            if on_start:
                on_start()
            if on_level is not None:
                try:
                    self._engine.speak(text, on_level=on_level)
                except TypeError:
                    self._engine.speak(text)
            else:
                self._engine.speak(text)
        except Exception as e:
            print(f"[TTS] Error: {e}")
        finally:
            with self._lock:
                self._playing = False
            if on_done:
                on_done()

    def stop(self) -> None:
        sd.stop()
        with self._lock:
            self._playing = False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_tts_player(config: Optional[dict] = None) -> TTSPlayer:
    from memory.config_manager import load_api_keys
    stored = load_api_keys()
    cfg = dict(stored)
    if config:
        cfg.update(config)

    engine_name = (cfg.get("tts_engine") or "edgetts").lower()
    voice = cfg.get("tts_voice", None)
    rate  = cfg.get("tts_rate", None)
    pitch = cfg.get("tts_pitch", None)

    if engine_name == "elevenlabs" and cfg.get("elevenlabs_api_key"):
        api_key  = cfg.get("elevenlabs_api_key", "").strip()
        voice_id = cfg.get("elevenlabs_voice_id", "pNInz6obpgDQGcFmaJgB").strip()
        engine   = ElevenLabsTTSEngine(api_key=api_key, voice_id=voice_id)
    elif engine_name == "kokoro":
        v      = voice or "af_heart"
        speed  = float(cfg.get("tts_speed", 1.15))
        engine = KokoroTTSEngine(voice=v, speed=speed)
    elif engine_name in ("pyttsx3", "sapi5"):
        engine   = Pyttsx3TTSEngine(voice_id=voice, rate=190)
    else:   # edgetts (default)
        engine = EdgeTTSEngine(voice=voice, rate=rate, pitch=pitch)
    return TTSPlayer(engine)
