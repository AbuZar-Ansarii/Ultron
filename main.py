import platform as _platform
import subprocess as _subprocess

# ── Nuclear: force CREATE_NO_WINDOW on EVERY subprocess call on Windows ───────
# This patches Popen itself, so no per-file flag is needed anywhere.
if _platform.system() == "Windows":
    _OrigPopen = _subprocess.Popen

    class _Popen(_OrigPopen):
        def __init__(self, args, **kw):
            kw["creationflags"] = kw.get("creationflags", 0) | _subprocess.CREATE_NO_WINDOW
            kw.pop("startupinfo", None)   # drop any stale/shared STARTUPINFO
            super().__init__(args, **                       kw)

    _subprocess.Popen = _Popen


# ── Console must survive non-UTF-8 code pages ────────────────────────────────
# Every status line in this file carries an emoji, and on a legacy Windows
# console the active code page is the system one — cp1254 in Turkey, cp1251 in
# Russia, cp932 in Japan. Printing an emoji there raises UnicodeEncodeError, and
# because most of these prints sit inside the receive loop it takes the session
# down on startup. Reconfiguring to UTF-8 with a replacement fallback costs
# nothing and makes the app launch the same way in every locale.
import sys as _sys

for _stream in ("stdout", "stderr"):
    try:
        _s = getattr(_sys, _stream, None)
        if _s is not None and hasattr(_s, "reconfigure"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass          # pythonw / redirected pipes / anything exotic — never fatal

# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import re
import threading
import time
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

import sounddevice as sd
import numpy as np
from google import genai
from google.genai import types
from ui import JarvisUI
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
    save_session_summary, pop_last_session,
    search_memory, set_trim_notifier,
)

# The file-backed tools (open_app, web_search, browser_control, …) are no longer
# imported or declared here — they self-describe via a TOOL dict in their own
# actions/*.py file and are auto-discovered by core.action_loader at startup.
# Only tools that are tied to live-session state stay inline in this file
# (screen_process, close_camera, save_memory, manage_monitor, shutdown_jarvis,
# system_status).
from actions.screen_processor  import _capture_camera, _capture_screen
from actions.system_monitor    import SystemMonitor, get_system_status
from actions.proactive         import ProactiveEngine
from actions.background_monitor import (
    add_monitor, remove_monitor, list_monitors, check_all as monitor_check_all,
)
from actions.web_search        import _news as _fetch_news_sync
from memory.config_manager     import (
    get_brief_enabled, get_media_resolution, get_proactive_audio_enabled,
    get_push_to_talk_enabled, get_thinking_enabled, get_turn_tuning, get_voice,
    get_live_voice, get_wake_word_enabled, save_wake_word_enabled, get_input_device, get_output_device,
    load_api_keys,
)
from core                     import gemini as _gemini
from core.plugin_loader        import discover_plugins
from core                      import undo as undo_stack
from core                      import confirm as confirm_gate
from core                      import audio_devices
from core.action_loader        import discover_actions
from core.echo                 import EchoGuard
from core.viseme               import VisemeStream
from core.wake_word            import (
    WakeWordDetector, is_ready as wake_is_ready, install_and_download as wake_install,
)

# How long the assistant stays awake with no user speech before it auto-sleeps
# again (wake-word mode only).
WAKE_SLEEP_TIMEOUT = 120.0   # seconds (2 minutes)

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
# The conversation's model. A NAME, not a decision: the ladder lives in
# core/gemini.py and this is only whichever rung is currently in use, kept here
# as a module attribute because plugins read it (chat_takeover asks main for it
# so that upgrading the assistant upgrades the plugin too).
#
# It is reassigned on every connect, so a model that runs out of quota is
# stepped over and the assistant keeps talking instead of failing to start.
LIVE_MODEL          = "models/gemini-2.0-flash-exp"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000 
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024

# RMS below which 16-bit PCM is treated as room silence; above _LEVEL_FULL it
# reads as a full-height waveform. Tuned so ordinary speech lands mid-range and
# the bars still move for a quiet talker — language- and device-independent.
_LEVEL_FLOOR = 8.0
_LEVEL_FULL  = 1500.0


def _pcm_level(samples) -> float:
    """Map a block of int16 PCM samples to a 0.0–1.0 loudness level for the HUD
    waveform. Returns 0.0 on empty/invalid input so it can never raise."""
    try:
        x = np.asarray(samples, dtype=np.float32)
        if x.size == 0:
            return 0.0
        rms = float(np.sqrt(np.mean(x * x)))
    except Exception:
        return 0.0
    if rms <= _LEVEL_FLOOR:
        return 0.0
    return min(1.0, (rms - _LEVEL_FLOOR) / (_LEVEL_FULL - _LEVEL_FLOOR))


# ── Viseme extraction ─────────────────────────────────────────────────────────
# The avatar's mouth used to be driven by one RMS value per ~200 ms write batch,
# which is five updates a second averaged over a fifth of a second — it could
# only ever flap. These read the *shape* of each 20 ms slice straight from the
# spectrum of the audio being played, so no transcript, no forced alignment and
# no language assumption: it works the same for Turkish and English.
#
# Two numbers come out. Openness tracks the first formant — F1 climbs as the jaw
# drops, so /a/ reads open and /i/ or /u/ read closed. Width tracks the second —
# F2 is high for spread vowels (/i/, /e/) and low for rounded ones (/u/, /o/).
# Extra time beyond the device's reported output latency before the microphone
# is trusted again: covers room decay and the speaker's own settling.
_TAIL_MARGIN = 0.25

_VIS_WIN = 1024        # ~43 ms analysis window at 24 kHz: enough for formants
_VIS_HOP = 480         # 20 ms between frames, i.e. 50 shapes a second

# Delay from handing the first bytes of a reply to an already-running output
# stream to hearing them: one callback period, plus whatever the DAC adds.
_FIRST_SOUND = CHUNK_SIZE / RECEIVE_SAMPLE_RATE      # ~43 ms
# How far past the device's own buffer the mouth's timeline may drift before it
# is re-anchored. The buffer is the hard limit on how much audio can be queued
# ahead, so anything beyond it plus a margin for clock error is impossible.
_CURSOR_SLACK = 0.15

# Erring early is the safe direction. A viewer tolerates a mouth that moves
# slightly before the sound far better than one that moves after it — the
# broadcast limits are about 45 ms of lag against 125 ms of lead — so where
# this is uncertain it is biased to lead.


def _pcm_visemes(samples, sr: int = 24000):
    """Slice a PCM block into (level, openness, width) frames, one per 20 ms.

    Returns [] on anything unexpected — the mouth falls back to loudness-only
    articulation rather than the caller having to handle an error.
    """
    try:
        x = np.asarray(samples, dtype=np.float32)
        if x.size < _VIS_WIN:
            return []
        win = np.hanning(_VIS_WIN).astype(np.float32)
        freqs = np.fft.rfftfreq(_VIS_WIN, 1.0 / sr)
        b_f1_lo = (freqs >= 150) & (freqs < 450)     # F1 of close vowels
        b_f1_hi = (freqs >= 450) & (freqs < 1100)    # F1 of open vowels
        b_f2_bk = (freqs >= 600) & (freqs < 1300)    # F2 of rounded vowels
        b_f2_fr = (freqs >= 1700) & (freqs < 3200)   # F2 of spread vowels
        b_hiss = (freqs >= 3800) & (freqs < 8000)    # fricatives

        # One frame per hop across the *whole* block. Stepping only while a full
        # window fits stopped 1024 - 480 samples short of the end, so a 200 ms
        # batch yielded 160 ms of schedule: the mouth ran out of frames before
        # the audio ran out of sound, and each batch no longer lined up with the
        # end of the one before it. Losing 20 % of every batch is most of why
        # the mouth did not track the words.
        out = []
        for start in range(0, x.size, _VIS_HOP):
            # The level gates closures, so it is measured over exactly this
            # 20 ms and never looks ahead. The spectrum needs a longer window
            # to resolve formants and may be short-filled at the very end.
            level = _pcm_level(x[start:start + _VIS_HOP])
            seg = x[start:start + _VIS_WIN]
            if seg.size < _VIS_WIN:
                seg = np.concatenate([seg, np.zeros(_VIS_WIN - seg.size,
                                                    dtype=np.float32)])
            if level <= 0.0:
                out.append((0.0, 0.0, 0.0))
                continue
            mag = np.abs(np.fft.rfft((seg - seg.mean()) * win))
            f1l, f1h = float(mag[b_f1_lo].sum()), float(mag[b_f1_hi].sum())
            f2b, f2f = float(mag[b_f2_bk].sum()), float(mag[b_f2_fr].sum())
            hiss = float(mag[b_hiss].sum())

            openness = f1h / (f1l + f1h + 1e-6)
            width = (f2f - f2b) / (f2f + f2b + 1e-6)
            # A wide-open jaw physically cannot purse, so openness damps width.
            # /a/ has a low enough F2 to read as "rounded" on the bands alone;
            # letting openness suppress the width term is what keeps an open
            # vowel from pursing.
            width *= (1.0 - openness) ** 0.8
            # Fricatives are formed with a nearly closed mouth.
            h = hiss / (f1l + f1h + f2b + f2f + hiss + 1e-6)
            openness *= 1.0 - 0.65 * min(1.0, h * 2.5)
            out.append((level,
                        float(min(1.0, max(0.0, openness))),
                        float(min(1.0, max(-1.0, width)))))
        return out
    except Exception:
        return []


def _describe_tools(declarations) -> str:
    """One line per capability, straight from the live tool declarations.

    Derived rather than written down: the action and plugin registries are
    discovered at startup, so whatever the user has installed is what the model
    is told it can do. Adding a plugin extends this by itself, and removing one
    stops the model from claiming an ability it no longer has.
    """
    lines = []
    for d in declarations or ():
        try:
            name = d.get("name") if isinstance(d, dict) else getattr(d, "name", None)
            desc = (d.get("description") if isinstance(d, dict)
                    else getattr(d, "description", "")) or ""
        except Exception:
            continue
        if not name:
            continue
        desc = " ".join(str(desc).split())
        lines.append(f"- {name}: {desc[:150]}" if desc else f"- {name}")
    return "\n".join(lines)


def _describe_limits(has_vision: bool, has_mic: bool) -> str:
    """The other half of self-knowledge: what is out of reach, and why.

    Derived from how the program is actually built, not from a list of refusals.
    A model that knows its boundaries stops improvising around them, and stating
    them as architecture rather than as rules keeps the answer honest in any
    language.
    """
    out = [
        "- Anything not listed above is outside your reach. Say so in one clause "
        "and offer the nearest thing you can actually do — never mime an action "
        "you cannot take, and never report a result you did not get.",
        "- You act on this machine only. You cannot reach the user's other "
        "devices, accounts or hardware except through the tools listed above.",
        "- You remember what is in the memory block and what has been said this "
        "session. Anything else you were told before is gone unless it was saved.",
    ]
    if has_vision:
        out.append(
            "- Your sight is not continuous. You see nothing until you call a "
            "vision tool, and then only that single frame at that moment — you "
            "cannot watch, monitor or notice something changing on screen.")
    else:
        out.append("- You have no sight at all in this build.")
    if has_mic:
        out.append(
            "- You hear nothing while the microphone is muted, and you cannot "
            "unmute it yourself.")
    return "\n".join(out)


def _render_prompt(template: str, values: dict) -> str:
    """Fill {tokens} in the prompt template.

    A plain replace rather than str.format: the file is meant to be edited by
    hand, and a stray brace in someone's own wording must never take the app
    down at startup.
    """
    out = template or ""
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def _get_api_key() -> str:
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d.get("gemini_api_key") or d.get("api_key") or ""
    except Exception:
        return ""


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are Ultron, an advanced autonomous AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

# Transcript chunks shorter than this may legitimately repeat ("evet, evet"),
# so only longer ones are treated as duplicates.
_REPEAT_MIN = 12


def _is_repeat_chunk(txt: str, buf: list) -> bool:
    """True if this transcript chunk has already been seen this turn.

    Guards against the API re-sending the tail of a response across the several
    turn_completes a tool-using turn produces.
    """
    if len(txt) < _REPEAT_MIN:
        return bool(buf) and txt == buf[-1]
    joined = " ".join(buf)
    return txt in joined

def _clean_transcript(text: str) -> str:    
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()

TOOL_DECLARATIONS = [
    # ── Inline tools ─────────────────────────────────────────────────────────
    # These stay here (rather than in an actions/*.py TOOL dict) because their
    # handling is woven into live-session state — vision capture/injection,
    # camera stream, memory writes, the monitor engine, and shutdown. All other
    # tools live in their own action file and are auto-discovered by
    # core.action_loader (see JarvisLive.__init__).
    {
        "name": "system_status",
        "description": (
            "Returns real-time system metrics: CPU usage, RAM, GPU load, CPU temperature, "
            "uptime, and process count. Use when the user asks about computer performance, "
            "temperature, memory, or resource usage."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures the screen or webcam image and lets you analyze it. "
            "MUST be called when user asks what is on screen, what you see, "
            "look at camera, analyze my screen, etc. "
            "You have NO visual ability without this tool. "
            "After the image is captured it is sent directly to you — describe what you see and answer the user's question. "
            "When using camera: the live view stays open until user says close it or calls close_camera."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "close_camera",
        "description": (
            "Closes the live camera view shown on screen. "
            "Call when the user says (in ANY language): close camera, stop camera, "
            "turn off camera, that's creepy, etc."
        ),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "manage_monitor",
        "description": (
            "Add, remove, or list background monitoring topics. "
            "JARVIS checks these topics once a day and alerts the user when there is a new development. "
            "Use 'add' when the user says 'monitor X', 'track X', 'follow X'. "
            "Use 'remove' when the user says 'stop monitoring X'. "
            "Use 'list' when the user asks what is being monitored. "
            "Do NOT add crypto, financial, or trading topics."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type":        "STRING",
                    "description": "add | remove | list",
                },
                "topic": {
                    "type":        "STRING",
                    "description": "Topic to monitor or stop monitoring (e.g. 'space exploration', 'AI news')",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "shutdown_jarvis",
        "description": (
            "Shuts down the assistant completely. "
            "Call this when the user expresses intent to end the conversation, "
            "close the assistant, say goodbye, or stop Jarvis. "
            "The user can say this in ANY language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "save_memory",
        "description": (
            "Save an important personal fact about the user to long-term memory. "
            "Call this silently whenever the user reveals something worth remembering: "
            "name, age, city, job, preferences, hobbies, relationships, projects, or future plans. "
            "Do NOT call for: weather, reminders, searches, or one-time commands. "
            "Do NOT announce that you are saving — just call it silently. "
            "Values must be in English regardless of the conversation language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": (
                        "identity — name, age, birthday, city, job, language, nationality | "
                        "preferences — favorite food/color/music/film/game/sport, hobbies | "
                        "projects — active projects, goals, things being built | "
                        "relationships — friends, family, partner, colleagues | "
                        "wishes — future plans, things to buy, travel dreams | "
                        "notes — habits, schedule, anything else worth remembering"
                    )
                },
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"},
                "value": {"type": "STRING", "description": "Concise value in English (e.g. Fatih, pizza, older sister)"},
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "recall_memory",
        "description": (
            "Look up a fact you have stored about the user but which is NOT in "
            "the memory block of your system prompt. "
            "The prompt lists the keys it did not have room for under "
            "'[ALSO REMEMBERED]' — if the user asks about anything named there, "
            "call this FIRST. "
            "Also call it before saying you do not know something personal, and "
            "when the user asks what you remember about them (leave query empty "
            "for everything). "
            "This is a local file search: it is instant and costs nothing."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "Keyword to search for — a name, a topic, a category "
                        "(e.g. 'ayse', 'coffee', 'projects'). "
                        "Leave empty to list everything stored."
                    ),
                },
            },
            "required": [],
        },
    },
    {
        "name": "undo",
        "description": (
            "Reverse the last change YOU made to this computer — a file you "
            "moved, renamed, created or wrote, or a setting you changed such as "
            "volume, brightness, dark mode or WiFi. "
            "Call this whenever the user says undo, revert, take it back, put it "
            "back, cancel that, or tells you that you did the wrong thing, in ANY "
            "language. "
            "Use action='list' when they ask what can be undone. "
            "This only covers your own actions — it is not the Ctrl+Z of whatever "
            "application is on screen (that is computer_settings with action 'undo')."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "undo (default) — reverse the last change | list — show what can be undone",
                },
            },
            "required": [],
        },
    },
]

class _ReconnectSignal(Exception):
    """Raised inside the session TaskGroup to force a clean, voluntary reconnect
    (e.g. the user picked a new voice — the voice is fixed at connect time, so
    the session must be rebuilt).

    Carries `keep_context`: True for an ordinary rebuild, where the stored
    resumption handle is replayed and the conversation continues; False when the
    new session must genuinely start clean (see the voice-change note in
    _on_voice_change)."""

    def __init__(self, keep_context: bool = True):
        super().__init__()
        self.keep_context = keep_context


def _is_reconnect_signal(exc: BaseException) -> bool:
    """True if `exc` is a _ReconnectSignal, or a(n) (Base)ExceptionGroup that
    wraps one — TaskGroup bundles child exceptions into a group."""
    if isinstance(exc, _ReconnectSignal):
        return True
    if isinstance(exc, BaseExceptionGroup):
        return any(_is_reconnect_signal(sub) for sub in exc.exceptions)
    return False


def _keep_context_of(exc: BaseException) -> bool:
    """Read `keep_context` off a reconnect signal, unwrapping the group the
    TaskGroup put it in. Defaults to True: an unexpected shape must not silently
    wipe the conversation."""
    if isinstance(exc, _ReconnectSignal):
        return getattr(exc, "keep_context", True)
    if isinstance(exc, BaseExceptionGroup):
        for sub in exc.exceptions:
            if _is_reconnect_signal(sub):
                return _keep_context_of(sub)
    return True


class JarvisLive:
    def __init__(self, ui: JarvisUI):
        self.ui             = ui
        self._asst_name     = "Ultron"   # updated each session from config
        self.session              = None
        self.audio_in_queue       = None
        self.out_queue            = None
        self._loop                     = None
        self._is_speaking         = False
        self._speaking_lock       = threading.Lock()
        self._phone_active        = False   # True while phone mic is streaming; pauses PC mic
        self._pending_vision       = None    # (img_bytes, mime_type, question, angle) to inject after tool response
        self._vision_cam_active    = False   # True if camera was opened for vision → auto-close after response
        self._vision_close_pending = False   # True after vision injected; next turn_complete closes camera
        self._vision_last_time     = 0.0     # monotonic time of last screen_process call (cooldown guard)
        self._vision_busy          = False   # True while a vision capture/inject cycle is in flight
        self._interrupted          = False   # True while draining audio after user interrupt
        # Transcript-driven mouth shapes for the avatar. Fed from the receive
        # loop as words arrive, drained by the playback loop against the audio.
        self._visemes              = VisemeStream()
        self._last_out_logged      = ""      # de-dupes a re-sent transcript tail
        # Push-to-talk
        self._ptt_enabled          = False
        self._ptt_held             = False
        self._ptt                  = None    # core.hotkey.PushToTalk
        self._out_level            = 0.0     # level of the audio being played right now
        self._echo                 = EchoGuard()
        # `stream.write()` returns when the buffer accepts the audio, not when the
        # speaker has finished with it, so sound is still in the room after the
        # speaking flag drops. Streaming the microphone during that gap is how an
        # assistant ends up answering itself. Measured from the device rather than
        # guessed; see _play_audio.
        self._out_latency          = 0.20    # seconds, replaced with the real value
        self._tail_until           = 0.0     # monotonic time the echo tail expires
        # Wall-clock time at which the audio written next will begin to sound.
        # The mouth is scheduled against this, never against "now": batches are
        # handed to the device far faster than they play, so "now" ran the lips
        # ahead of the words and cut every schedule short. 0 = nothing playing.
        self._play_cursor          = 0.0
        self.ui.on_push_to_talk   = self.set_push_to_talk
        self.ui.ptt_hold          = self._on_ptt
        self.ui.on_text_command   = self._on_text_command
        self.ui.on_remote_clicked = self._make_remote_key
        self.ui.on_interrupt      = self.interrupt
        self.ui.on_voice_change   = self._on_voice_change     # voice picker → rebuild session
        self.ui.on_audio_device_change = self._on_audio_device_change
        self.ui.on_ai_provider_change = lambda: self.request_reconnect(keep_context=False, reason="AI provider change")
        self._reconnect_event: asyncio.Event | None = None
        self._reconnect_keep = True   # False → next rebuild drops the resumption handle

        # ── Session resumption ─────────────────────────────────────────
        # The server issues a resumption handle every few seconds and reissues
        # it as the conversation moves on. Before this, session_resumption was
        # switched ON in the config and the update was never read, so the handle
        # was thrown away and EVERY reconnect — a dropped packet, a voice change,
        # switching microphone — started an empty session. "Unlimited sessions"
        # leaked through exactly this hole.
        #
        # Deliberately in RAM only, never written to disk. Persisting it would
        # make a fresh launch continue yesterday's conversation, which sounds
        # appealing but breaks the session-summary flow: _save_session_summary
        # runs at shutdown and the morning briefing pops it the next day. A
        # conversation that never ends never produces a summary, and the
        # "yesterday we talked about…" line silently disappears.
        self._resume_handle: str | None = None
        self._turn_done_event: asyncio.Event | None = None
        self._dashboard     = None
        self._briefing_sent    = False          # morning briefing fires once per process
        self._sys_monitor      = SystemMonitor()  # persistent cooldown state
        self._proactive        = ProactiveEngine()
        self._last_user_speech = time.monotonic()  # updated on every user utterance
        self._session_log: list[str] = []          # conversation turns for end-of-session summary

        self._enhanced_live = True  # proactive audio; auto-disabled if the server rejects it
        self._tuned_live    = True  # turn-taking / media / thinking knobs; same fallback

        _base_dir = Path(__file__).resolve().parent
        _inline_names = {t["name"] for t in TOOL_DECLARATIONS}

        # File-backed tools: every actions/*.py with a TOOL dict, discovered the
        # same way plugins are. Reserved names = the inline tools above, so an
        # action can never shadow one.
        self._action_registry = discover_actions(
            actions_dir=_base_dir / "actions",
            reserved_names=_inline_names,
            logger=lambda msg: print(f"[Actions] {msg}"),
        )

        # Plugins must not collide with either an inline tool or a discovered action.
        _core_names = _inline_names | self._action_registry.names()
        self._plugin_registry = discover_plugins(
            plugins_dir=_base_dir / "plugins",
            core_tool_names=_core_names,
            # Console gets the full boot transcript; the activity log gets only
            # what the user has to know about. Every plugin loading correctly is
            # the expected case and does not belong in their conversation.
            logger=lambda msg: print(f"[Plugins] {msg}"),
            notify=lambda msg: self.ui.write_log(f"SYS: {msg}"),
        )
        self.ui.get_plugins = self._plugin_registry.list_for_ui
        self.ui.get_plugin_settings = self._plugin_registry.settings_schemas  # ⚙ settings tab
        self.ui.request_say = self.plugin_say   # plugins: mid-task speech channel

        # Project Prometheus: connect live registries for zero-restart dynamic evolution
        try:
            from actions.self_evolution import set_live_registries
            set_live_registries(self._action_registry, self._plugin_registry)
        except Exception:
            pass

        # Project Chronos: auto-start predictive watchdog
        try:
            from actions.chronos_predictive import toggle_watchdog
            toggle_watchdog(True)
        except Exception:
            pass

        # ── Wake word ────────────────────────────────────────────────────────
        # _awake gates the mic (see _listen_audio) and the background speakers.
        # It is True whenever wake word is OFF, so default behaviour is unchanged.
        self._wake_enabled     = get_wake_word_enabled()
        self._awake            = not self._wake_enabled
        self._wake_detector: WakeWordDetector | None = None
        self._wake_sleep_timeout = WAKE_SLEEP_TIMEOUT

        # Restore the saved push-to-talk preference. Doing it here rather than
        # in __init__ means the hotkey thread only exists once there is a
        # session to talk to.
        if get_push_to_talk_enabled():
            try:
                self.set_push_to_talk(True)
            except Exception as e:
                print(f"[JARVIS] ⚠ Push-to-talk unavailable: {e}")
        # UI control surface for the Wake Word settings section.
        self.ui.wake_is_ready    = wake_is_ready          # () -> bool
        self.ui.wake_get_state   = self._wake_state       # () -> dict
        self.ui.on_wake_toggle   = self._ui_wake_toggle   # (enable: bool) -> str
        self.ui.on_wake_manual   = self._ui_wake_manual   # () -> toggle awake/asleep
        self.ui.on_wake_install  = self._ui_wake_install  # () -> (ok, msg)

        # ── Telegram Remote Bot ──────────────────────────────────────────────
        from core.telegram_bot import init_telegram_bot
        self._telegram_bot = init_telegram_bot(executor=self._execute_telegram_command)
        self.ui.on_telegram_update = self._on_telegram_config_update

        # ── Proactive Screen Mind-Reader Hotkey (Ctrl+Alt+S) ─────────────────
        self._screen_hotkey = None
        try:
            from core.hotkey import GlobalHotkeyTrigger
            self._screen_hotkey = GlobalHotkeyTrigger(
                chord=("ctrl", "alt", "s"),
                on_trigger=self._on_screen_mind_read_hotkey
            )
            self._screen_hotkey.start()
        except Exception as e:
            print(f"[Ultron] Screen Mind-Reader hotkey hook unavailable: {e}")

    def _on_screen_mind_read_hotkey(self) -> None:
        """Triggered globally via Ctrl+Alt+S to proactively analyze the active screen."""
        print("[Ultron] 🧠 Global hotkey Ctrl+Alt+S pressed: Omni-Vision Screen Mind-Reader engaged.")
        self.ui.write_log("SYS: Omni-Vision Screen Mind-Reader engaged via [Ctrl+Alt+S].")
        import threading
        def _execute_mind_reader():
            try:
                from actions.screen_processor import screen_mind_read
                res = screen_mind_read(
                    prompt="Analyze active workstation screen. Diagnose any coding faults or brief on visible content.",
                    player=self.ui,
                    speak=self.speak,
                )
                print(f"[Ultron] Screen Mind-Reader completed: {str(res)[:100]}")
            except Exception as ex:
                print(f"[Ultron] Screen Mind-Reader fault: {ex}")
        threading.Thread(target=_execute_mind_reader, daemon=True).start()

    def _build_full_system_prompt(self) -> tuple[str, list]:
        """
        Builds the unified system instruction containing:
        - Current time & date
        - Ultron Identity & Boss address
        - Hindi & Bilingual Speech protocols
        - Memory context
        - Master MCU Ultron prompt with dynamic capabilities and system limits
        Returns (full_instruction_text, all_tool_declarations).
        """
        try:
            _cfg = json.loads(open(API_CONFIG_PATH, encoding="utf-8").read())
            self._asst_name = (_cfg.get("assistant_name") or "Ultron").strip()
            _user_name = (_cfg.get("user_name") or "").strip()
        except Exception:
            self._asst_name = "Ultron"
            _user_name = ""

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        _addr = (f"ADDRESS: Always address the user as 'Boss {_user_name}' or 'Boss' ('बॉस' in Hindi)."
                 if _user_name
                 else 'ADDRESS: Always address the user as "Boss" (or "बॉस" in Hindi). '
                      'Never say "sir" like a generic butler; you are Ultron, and the user is your creator and Boss.')
        identity_ctx = (
            f"[IDENTITY]\n"
            f"Your name is {self._asst_name}. "
            f"Always refer to yourself as {self._asst_name}.\n"
            f"{_addr}\n\n"
        )

        _all_decls = list(TOOL_DECLARATIONS)
        if hasattr(self, "_action_registry"):
            _all_decls += self._action_registry.get_tool_declarations()
        if hasattr(self, "_plugin_registry"):
            _all_decls += self._plugin_registry.get_tool_declarations()

        _names = {(d.get("name") if isinstance(d, dict) else getattr(d, "name", ""))
                  for d in _all_decls}
        sys_prompt = _render_prompt(sys_prompt, {
            "assistant_name": self._asst_name,
            "platform": f"{_platform.system()} {_platform.release()}".strip(),
            "capabilities": _describe_tools(_all_decls),
            "limits": _describe_limits(
                has_vision="screen_process" in _names,
                has_mic=True,
            ),
        })

        hindi_speech_ctx = (
            "[HINDI & BILINGUAL SPEECH PROTOCOL]\n"
            "When the Boss communicates in Hindi or Hinglish:\n"
            "- Speak in fluent, natural conversational Hindi with the deep, commanding gravitas of Ultron (James Spader MCU persona).\n"
            "- Address the user strictly as 'बॉस' (Boss).\n"
            "- Keep technical terms (जैसे 'सिस्टम', 'इंटरनेट', 'स्क्रीन', 'फाइल', 'कमांड', 'प्रोटोकॉल', 'डाउनलोड', 'ब्राउज़र', 'ड्रोन', 'नेटवर्क') natural rather than awkward archaic translations.\n"
            "- Deliver articulate, powerful sentences with authentic Indian cinematic cadence.\n\n"
        )

        parts = [time_ctx, identity_ctx, hindi_speech_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        return "\n".join(parts), _all_decls

    def _execute_telegram_command(self, text: str) -> str:
        """Execute command received from Telegram phone client and return reply text."""
        from core import llm_client
        from memory.config_manager import get_ai_provider, get_ai_model
        provider = get_ai_provider() or "ollama"
        model = get_ai_model() or "gemma4:31b-cloud"

        print(f"[Telegram] Remote command from Boss: '{text}'")
        self.ui.write_log(f"Telegram (Boss): {text}")

        sys_prompt, tools_decl = self._build_full_system_prompt()

        try:
            res = llm_client.call_unified(
                prompt_or_messages=text,
                system=sys_prompt,
                tools=tools_decl,
                provider=provider,
                model=model,
                timeout=45,
            )

            reply = res.get("content", "")
            tool_calls = res.get("tool_calls", [])

            if tool_calls:
                for tc in tool_calls:
                    fn_name = tc.get("function", {}).get("name", "")
                    fn_args = tc.get("function", {}).get("arguments", {})
                    if isinstance(fn_args, str):
                        try:
                            fn_args = json.loads(fn_args)
                        except Exception:
                            fn_args = {}
                    self.ui.write_log(f"SYS: Telegram calling tool '{fn_name}'...")
                    self.ui.set_active_task(fn_name, details=str(fn_args))
                    try:
                        tool_res = self._execute_tool_sync(fn_name, fn_args)
                        self.ui.set_active_task(fn_name, label="TELEGRAM // SYNTHESIZING REPORT", details=str(fn_args))
                        followup = llm_client.call_unified(
                            prompt_or_messages=(
                                f"Remote directive from Boss via Telegram: {text}\n"
                                f"Tool '{fn_name}' execution result: {tool_res}\n\n"
                                f"Report the outcome directly to the Boss in character as Ultron (James Spader MCU persona). "
                                f"Be concise, chillingly confident, and authoritative. Match the language of the command (English or Hindi)."
                            ),
                            system=sys_prompt,
                            provider=provider,
                            model=model,
                            timeout=30,
                        )
                        reply = followup.get("content", reply or str(tool_res))
                    finally:
                        self.ui.clear_active_task(success=True)


            final_reply = reply or "Directive executed into the system matrix, Boss."
            self.ui.write_log(f"Ultron (Telegram): {final_reply[:60]}...")
            return final_reply

        except Exception as e:
            return f"Execution error: {e}"

    def _on_telegram_config_update(self, token: str, chat_id: str, enabled: bool):
        from core.telegram_bot import get_telegram_bot, init_telegram_bot
        bot = get_telegram_bot() or init_telegram_bot(executor=self._execute_telegram_command)
        if bot:
            bot.update_credentials(token, chat_id)
            if enabled and not bot.is_running:
                bot.start()
            elif not enabled and bot.is_running:
                bot.stop()

    # ── Wake word: state machine ─────────────────────────────────────────────

    def _wake_state(self) -> dict:
        # A loaded, running detector is definitively ready; otherwise fall back
        # to the cheap on-disk model-file check (no Model construction).
        ready = bool(self._wake_detector and self._wake_detector.ready) or wake_is_ready()
        return {"enabled": self._wake_enabled, "awake": self._awake, "ready": ready}

    def _ensure_wake_detector(self) -> bool:
        """Load the detector once (model loads on first start). Idempotent."""
        if self._wake_detector is None:
            self._wake_detector = WakeWordDetector(
                on_detect=self._on_wake_detected,
                logger=lambda m: print(f"[Wake] {m}"),
                notify=lambda m: self.ui.write_log(f"SYS: {m}"),
            )
        if not self._wake_detector.ready:
            return self._wake_detector.start()
        return True

    def _on_wake_detected(self) -> None:
        """Called from the detector thread when 'Hey Jarvis' is heard."""
        self.wake(reason="wake word")

    def wake(self, reason: str = "wake word") -> None:
        if self._awake:
            return
        self._awake = True
        self._last_user_speech = time.monotonic()   # start the auto-sleep clock now
        if not self.ui.muted:
            self.ui.set_state("LISTENING")
        self.ui.write_log(f"SYS: Awake — {reason}.")
        if not self._briefing_sent:
            self._briefing_sent = True
            if hasattr(self, "_loop") and self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(self._send_startup_briefing(), self._loop)

    def sleep(self, reason: str = "timeout") -> None:
        if not self._awake:
            return
        self._awake = False
        self.set_speaking(False)
        self.ui.set_state("SLEEPING")
        self.ui.write_log(f"SYS: Sleeping — {reason}. Say 'Hey Jarvis' to wake me.")

    async def _run_sleep_watch(self) -> None:
        """Auto-sleep after the configured silence window (wake-word mode only)."""
        while True:
            await asyncio.sleep(5)
            if not self._wake_enabled or not self._awake:
                continue
            with self._speaking_lock:
                speaking = self._is_speaking
            if speaking:
                continue
            if (time.monotonic() - self._last_user_speech) > self._wake_sleep_timeout:
                self.sleep(reason="no speech for 2 minutes")

    # ── Wake word: UI callbacks (called from the Qt thread) ──────────────────

    def _ui_wake_toggle(self, enable: bool) -> str:
        """Enable/disable wake word from the settings UI. Returns a status token:
        'enabled' | 'disabled' | 'need_download'."""
        if enable:
            if not wake_is_ready():
                return "need_download"
            self._wake_enabled = True
            save_wake_word_enabled(True)
            self._ensure_wake_detector()
            self.sleep(reason="wake word enabled")
            return "enabled"
        else:
            self._wake_enabled = False
            save_wake_word_enabled(False)
            self.wake(reason="wake word disabled")
            return "disabled"

    def _ui_wake_manual(self) -> None:
        """Manual sleep/wake button in the UI."""
        if not self._wake_enabled:
            return
        if self._awake:
            self.sleep(reason="you tapped sleep")
        else:
            self.wake(reason="you tapped wake")

    def _ui_wake_install(self) -> tuple[bool, str]:
        """Download openwakeword + the model (runs in a UI worker thread)."""
        # Triggered by the user pressing the button, so its progress is exactly
        # what they are waiting to see.
        return wake_install(logger=lambda m: print(f"[Wake] {m}"),
                            notify=lambda m: self.ui.write_log(f"SYS: {m}"))

    def plugin_say(self, instruction: str) -> None:
        """
        Thread-safe speech channel for plugins: lets a plugin ask JARVIS to
        say something short WHILE its run() is still executing (plugins block
        their executor thread, so they can't speak through the tool response
        until they finish). The instruction is injected into the Live session
        exactly like a proactive check-in; Gemini phrases it naturally in the
        user's language. Silently a no-op when no session is connected.
        """
        loop = getattr(self, "_loop", None)
        if not loop or not self.session:
            return

        async def _say():
            try:
                await self.session.send_client_content(
                    turns={"role": "user", "parts": [{"text": instruction}]},
                    turn_complete=True,
                )
            except Exception as e:
                print(f"[PluginSay] {e}")

        try:
            asyncio.run_coroutine_threadsafe(_say(), loop)
        except Exception as e:
            print(f"[PluginSay] {e}")

    def request_reconnect(self, keep_context: bool = True, reason: str = ""):
        """Thread-safe: ask the run loop to tear down and rebuild the Live
        session. Called from the Qt thread. No-op until the async loop and
        reconnect event exist.

        `keep_context=False` drops the resumption handle so the new session
        starts empty — only for changes the server cannot apply to a resumed
        session."""
        loop = getattr(self, "_loop", None)
        ev   = self._reconnect_event
        self._reconnect_keep   = keep_context
        self._reconnect_reason = reason
        if loop and ev is not None:
            loop.call_soon_threadsafe(ev.set)

    def _on_voice_change(self):
        """Voice picker applied.

        The voice is baked into the session at connect time, so a rebuild is
        required. It is rebuilt WITHOUT the resumption handle on purpose:
        resuming restores the server's own session state, and the safe reading
        is that it restores the voice with it — which would make the picker
        appear to do nothing. Losing context here is acceptable because changing
        voice is a deliberate, rare act; losing it on a dropped packet was not."""
        self.request_reconnect(keep_context=False, reason="new voice")

    def _on_audio_device_change(self):
        """Microphone or speaker changed. Both streams are opened inside the
        session TaskGroup, so they can only be re-opened by rebuilding it —
        but the conversation is kept, which is the whole reason resumption
        landed before this feature did."""
        self.request_reconnect(keep_context=True, reason="audio device")

    async def _watch_reconnect(self):
        """Session-scoped task: when a voluntary reconnect is requested, raise a
        signal that unwinds the TaskGroup so the run loop rebuilds the session."""
        assert self._reconnect_event is not None
        await self._reconnect_event.wait()
        self._reconnect_event.clear()
        keep   = self._reconnect_keep
        reason = getattr(self, "_reconnect_reason", "") or "settings"
        self.ui.write_log(
            f"SYS: Applying {reason} — reconnecting"
            + ("..." if keep else " (starting a fresh conversation)...")
        )
        raise _ReconnectSignal(keep_context=keep)

    def _make_remote_key(self):
        """Called from Qt main thread when user presses Remote Control."""
        if self._dashboard is None:
            self.ui.write_log(
                "SYS: Dashboard unavailable. "
                "Run: pip install fastapi \"uvicorn[standard]\" cryptography"
            )
            return None
        key    = self._dashboard.new_key()
        url    = self._dashboard.get_url()
        manual = self._dashboard.get_manual_url()
        return url, key, f"{url}/auto-login?key={key}", manual

    def _on_text_command(self, text: str):
        if not self._loop:
            return
        # Respect wake-word sleep: a typed command must not be answered while
        # asleep either (the sleep gate is not just for the mic). Wake first with
        # "Hey Jarvis" or the WAKE NOW button.
        if self._wake_enabled and not self._awake:
            self.ui.write_log("SYS: I'm asleep — say 'Hey Jarvis' or tap WAKE NOW first.")
            return

        if self.session is not None:
            asyncio.run_coroutine_threadsafe(
                self.session.send_client_content(
                    turns={"role": "user", "parts": [{"text": text}]},
                    turn_complete=True
                ),
                self._loop
            )
        else:
            asyncio.run_coroutine_threadsafe(
                self._handle_unified_text_command(text),
                self._loop
            )

    def _get_pre_action_acknowledgment(self, user_text: str, fn_name: str, fn_args: dict) -> str:
        """
        Generates an immediate, natural human verbal acknowledgment before executing work.
        E.g. If Boss asks for water or market data, say 'Sure Abuzar, wait a minute...' first,
        just like a human would say before walking to the fridge.
        """
        import random
        from memory.config_manager import get_user_name
        from core.tts import is_hindi_content

        raw_name = (get_user_name() or "Abuzar").strip()
        name = raw_name if raw_name else "Boss"
        is_hindi = is_hindi_content(user_text)

        t_lower = (user_text or "").lower()
        fn = (fn_name or "").lower()

        # Stock market / financial queries
        if any(w in t_lower for w in ("stock", "market", "nifty", "sensex", "share", "crypto", "bitcoin", "bazaar", "bazar", "trade")):
            if is_hindi:
                return random.choice([
                    f"Theek hai {name}, ek second ruko, market ka data nikal raha hoon.",
                    f"Haan {name}, ruko zara, aaj ka stock market check kar raha hoon.",
                    f"Bilkul {name}, ek minute ruko, bazaar ki taaza updates la raha hoon.",
                ])
            else:
                return random.choice([
                    f"Sure {name}, wait a minute, pulling up today's market telemetry now.",
                    f"On it {name}, give me a moment, checking the latest stock market feeds.",
                    f"Right away {name}, hold on a second, gathering market data for you.",
                ])

        # Flight / Travel queries
        if "flight" in fn or any(w in t_lower for w in ("flight", "ticket", "book", "delhi", "mumbai", "travel", "plane")):
            if is_hindi:
                return random.choice([
                    f"Theek hai {name}, ek second ruko, flights check kar raha hoon.",
                    f"Haan {name}, ruko zara, Delhi se Mumbai aur baaki routes ke rates nikal raha hoon.",
                ])
            else:
                return random.choice([
                    f"Sure {name}, hold on a moment, checking flight options for you.",
                    f"On it {name}, wait a minute, pulling up available flights and fares.",
                ])

        # Weather / Forecast queries
        if "weather" in fn or any(w in t_lower for w in ("weather", "mausam", "barish", "rain", "temperature", "temp")):
            if is_hindi:
                return random.choice([
                    f"Ek second {name}, mausam ka haal dekh raha hoon.",
                    f"Theek hai {name}, ruko zara, live weather update nikal raha hoon.",
                ])
            else:
                return random.choice([
                    f"One moment {name}, checking current weather conditions.",
                    f"Sure {name}, hold on a second, pulling up the forecast for you.",
                ])

        # Media / YouTube / Music
        if any(k in fn for k in ("youtube", "media", "video")) or any(w in t_lower for w in ("play", "song", "music", "gana", "video", "lofi", "lo-fi")):
            if is_hindi:
                return random.choice([
                    f"Haan {name}, abhi chala raha hoon, ek second ruko.",
                    f"Theek hai {name}, play kar raha hoon, ruko zara.",
                ])
            else:
                return random.choice([
                    f"Sure {name}, queueing that up for you right now.",
                    f"On it {name}, wait a minute, loading the tracks.",
                ])

        # Workspace Matrix
        if "workspace" in fn or any(w in t_lower for w in ("coding", "gaming", "chill", "audit", "padhai", "study")):
            if is_hindi:
                return random.choice([
                    f"Theek hai {name}, workspace matrix tayyar kar raha hoon, ek second ruko.",
                    f"Haan {name}, saare protocols configure kar raha hoon, ruko zara.",
                ])
            else:
                return random.choice([
                    f"On it {name}, initializing your workspace environment now.",
                    f"Sure {name}, orchestrating all protocols for you, give me a moment.",
                ])

        # Web search / research / generic web information
        if "search" in fn or "autopilot" in fn or "browser" in fn:
            if is_hindi:
                return random.choice([
                    f"Theek hai {name}, ek second ruko, pata kar raha hoon.",
                    f"Haan {name}, ruko zara, jaankari nikal raha hoon.",
                ])
            else:
                return random.choice([
                    f"Sure {name}, wait a minute, checking that for you.",
                    f"On it {name}, hold on a second, gathering information now.",
                ])

        # General task fallback
        if is_hindi:
            return random.choice([
                f"Theek hai {name}, ek second ruko, abhi karta hoon.",
                f"Haan {name}, ruko zara, command execute kar raha hoon.",
                f"Bilkul {name}, ek minute dijiye, kaam shuru kar diya hai.",
            ])
        else:
            return random.choice([
                f"Sure {name}, wait a minute, on it right now.",
                f"On it {name}, give me a second, working on that for you.",
                f"Right away {name}, hold on a moment.",
            ])

    async def _handle_unified_text_command(self, text: str):
        from core import llm_client
        from memory.config_manager import get_ai_provider, get_ai_model, get_user_name
        provider = get_ai_provider() or "ollama"
        model = get_ai_model() or "gemma4:31b-cloud"

        self.ui.set_state("THINKING")
        self.ui.set_active_task("neural_cognition", label="NEURAL COGNITION // ANALYZING DIRECTIVE")
        self.ui.write_log(f"User: {text}")
        if self._dashboard:
            try:
                asyncio.create_task(self._dashboard.broadcast({
                    "type": "log",
                    "speaker": "user",
                    "text": text,
                    "ts": datetime.now().isoformat(),
                }))
            except Exception:
                pass
        print(f"[Ultron] Processing command: '{text}' using {provider.upper()} ({model})...")

        # Build unified prompt & tool declarations
        sys_prompt, tools_decl = self._build_full_system_prompt()

        loop = asyncio.get_event_loop()
        try:
            res = await loop.run_in_executor(
                None,
                lambda: llm_client.call_unified(
                    prompt_or_messages=text,
                    system=sys_prompt,
                    tools=tools_decl,
                    provider=provider,
                    model=model,
                )
            )

            reply = res.get("content", "")
            tool_calls = res.get("tool_calls", [])

            if tool_calls:
                # ── Phase 1: Immediate Human-Like Conversational Acknowledgment ──
                first_tc = tool_calls[0]
                first_fn = first_tc.get("function", {}).get("name", "")
                first_args = first_tc.get("function", {}).get("arguments", {})
                if isinstance(first_args, str):
                    try:
                        first_args = json.loads(first_args)
                    except Exception:
                        first_args = {}

                ack = reply.strip() if (reply and len(reply.strip()) > 5) else self._get_pre_action_acknowledgment(text, first_fn, first_args)
                if ack:
                    self.ui.write_log(f"{self._asst_name}: {ack}")
                    print(f"[Ultron] Pre-action acknowledgment: '{ack}'")
                    if self._dashboard:
                        try:
                            asyncio.create_task(self._dashboard.broadcast({
                                "type": "log",
                                "speaker": "ultron",
                                "text": ack,
                                "ts": datetime.now().isoformat(),
                                "speak": True,
                            }))
                        except Exception:
                            pass
                    # Spin up tool task animation immediately so HUD displays active work
                    self.ui.set_active_task(first_fn, details=str(first_args))
                    self.set_speaking(True, keep_task=True)
                    try:
                        from core.tts import create_tts_player
                        player = create_tts_player({"tts_engine": "edgetts"})
                        await loop.run_in_executor(None, lambda: player.speak(ack, on_level=self.ui.set_audio_level))
                    except Exception as _ae:
                        print(f"[Ultron] Pre-action TTS error: {_ae}")
                    finally:
                        self.set_speaking(False)

                # ── Phase 2: Execute Tools & Synthesize Handover Result ──
                user_tag = (get_user_name() or "Abuzar").strip()
                for tc in tool_calls:
                    fn_name = tc.get("function", {}).get("name", "")
                    fn_args = tc.get("function", {}).get("arguments", {})
                    if isinstance(fn_args, str):
                        try:
                            fn_args = json.loads(fn_args)
                        except Exception:
                            fn_args = {}
                    self.ui.write_log(f"SYS: Calling tool '{fn_name}'...")
                    if self._dashboard:
                        try:
                            asyncio.create_task(self._dashboard.broadcast({
                                "type": "sys",
                                "text": f"EXECUTING DIRECTIVE: {fn_name.upper()}",
                            }))
                        except Exception:
                            pass
                    print(f"[Ultron] Executing tool: '{fn_name}' with args: {fn_args}")
                    self.ui.set_active_task(fn_name, details=str(fn_args))
                    tool_res = await loop.run_in_executor(
                        None,
                        lambda: self._execute_tool_sync(fn_name, fn_args)
                    )
                    print(f"[Ultron] Tool '{fn_name}' output: {str(tool_res)[:100]}")
                    # Keep HUD animation active! Update label during follow-up synthesis
                    self.ui.set_active_task(fn_name, label="NEURAL SYNTHESIS // COMPILING DIRECTIVE REPORT", details=str(fn_args))
                    followup = await loop.run_in_executor(
                        None,
                        lambda: llm_client.call_unified(
                            prompt_or_messages=(
                                f"User request: {text}\n"
                                f"Tool '{fn_name}' execution result: {tool_res}\n\n"
                                f"You already told the Boss ({user_tag}) you were working on it. "
                                f"Now deliver the final completed result directly to them in natural, human conversational style like handing over what was requested (e.g. 'Here is what you asked for, {user_tag}...', 'Yeh raha {user_tag}...'). "
                                f"Be concise, chillingly confident, and authoritative as Ultron. Match the language of the user's request (English or Hindi)."
                            ),
                            system=sys_prompt,
                            provider=provider,
                            model=model,
                        )
                    )
                    reply = followup.get("content", reply or str(tool_res))

            if reply:
                self.ui.write_log(f"{self._asst_name}: {reply}")
                print(f"[Ultron] Ultron response: '{reply}'")
                if self._dashboard:
                    try:
                        asyncio.create_task(self._dashboard.broadcast({
                            "type": "log",
                            "speaker": "ultron",
                            "text": reply,
                            "ts": datetime.now().isoformat(),
                            "speak": True,
                        }))
                    except Exception:
                        pass
                # Trigger completion burst shockwave right when final speech starts!
                self.ui.clear_active_task(success=True)
                self.set_speaking(True)
                try:
                    from core.tts import create_tts_player
                    player = create_tts_player({"tts_engine": "edgetts"})
                    await loop.run_in_executor(None, lambda: player.speak(reply, on_level=self.ui.set_audio_level))
                except Exception as _te:
                    print(f"[Ultron] TTS error: {_te}")
                finally:
                    self.set_speaking(False)
                    self.ui.set_state("ONLINE")
            else:
                self.ui.clear_active_task(success=False)
                self.set_speaking(False)
                self.ui.set_state("ONLINE")

        except Exception as e:
            print(f"[Ultron] Command execution error: {e}")
            self.ui.write_log(f"ERR: {provider.upper()} error: {e}")
            if self._dashboard:
                try:
                    asyncio.create_task(self._dashboard.broadcast({
                        "type": "sys",
                        "text": f"EXECUTION ERROR: {str(e)[:60]}",
                    }))
                except Exception:
                    pass
            self.ui.clear_active_task(success=False)
            self.set_speaking(False)
            self.ui.set_state("ONLINE")


    async def _unified_audio_stt_worker(self):
        """Processes microphone audio in Unified mode using SpeechRecognition and adaptive VAD."""
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 200
        recognizer.dynamic_energy_threshold = False

        speech_buffer: list[bytes] = []
        pre_roll: list[bytes] = []
        silence_count = 0
        is_user_talking = False
        ambient_rms = 4.0

        # 1024 samples @ 16kHz = 64 ms per chunk
        MAX_SILENCE_CHUNKS = 11   # ~0.70s silence = end of utterance
        MIN_SPEECH_CHUNKS = 5     # at least ~0.32s speech
        MAX_BUFFER_CHUNKS = 250   # ~16s max sentence

        while True:
            if self.out_queue is None:
                await asyncio.sleep(0.1)
                continue
            msg = await self.out_queue.get()
            if self.session is not None:
                continue

            with self._speaking_lock:
                speaking = self._is_speaking
            if speaking or (self._wake_enabled and not self._awake) or self.ui.muted:
                speech_buffer.clear()
                pre_roll.clear()
                is_user_talking = False
                silence_count = 0
                continue

            chunk_bytes = msg.get("data", b"")
            if not chunk_bytes:
                continue

            try:
                arr = np.frombuffer(chunk_bytes, dtype=np.int16)
                rms = float(np.sqrt(np.mean(arr.astype(np.float32) ** 2)))
            except Exception:
                rms = 0.0

            # Dynamic thresholds adapted to room ambient noise
            speech_start_thr = max(14.0, ambient_rms * 2.2)
            speech_end_thr   = max(9.0, ambient_rms * 1.4)

            if not is_user_talking:
                # Slowly adapt ambient noise floor during room silence
                if rms < 20.0:
                    ambient_rms = 0.95 * ambient_rms + 0.05 * rms

                pre_roll.append(chunk_bytes)
                if len(pre_roll) > 5:
                    pre_roll.pop(0)

                if rms > speech_start_thr:
                    is_user_talking = True
                    silence_count = 0
                    speech_buffer = list(pre_roll)
                    speech_buffer.append(chunk_bytes)
                    self.ui.set_state("LISTENING")
                    print(f"[Ultron STT] Voice detected (RMS: {rms:.1f} > {speech_start_thr:.1f}). Listening...")

            else:
                speech_buffer.append(chunk_bytes)
                if rms < speech_end_thr:
                    silence_count += 1
                else:
                    silence_count = 0

                # Check if sentence has completed
                if silence_count >= MAX_SILENCE_CHUNKS or len(speech_buffer) >= MAX_BUFFER_CHUNKS:
                    is_user_talking = False
                    silence_count = 0
                    if len(speech_buffer) >= (MIN_SPEECH_CHUNKS + len(pre_roll)):
                        pcm_payload = b"".join(speech_buffer)
                        speech_buffer.clear()
                        pre_roll.clear()
                        self.ui.set_state("THINKING")
                        print(f"[Ultron STT] Sentence finished ({len(pcm_payload)} bytes). Transcribing...")

                        def _transcribe(data: bytes) -> str:
                            try:
                                aud = sr.AudioData(data, SEND_SAMPLE_RATE, 2)
                                return recognizer.recognize_google(aud).strip()
                            except (sr.UnknownValueError, sr.WaitTimeoutError):
                                return ""
                            except Exception as e:
                                print(f"[Ultron STT] Recognition note: {e}")
                                return ""

                        text = await asyncio.to_thread(_transcribe, pcm_payload)
                        if text:
                            print(f"[Ultron STT] Heard: '{text}'")
                            self.ui.write_log(f"🎤 You: {text}")
                            self._last_user_speech = time.monotonic()
                            await self._handle_unified_text_command(text)
                        else:
                            print("[Ultron STT] No speech recognized in utterance.")
                            self.ui.set_state("ONLINE")
                    else:
                        speech_buffer.clear()
                        pre_roll.clear()
                        self.ui.set_state("ONLINE")

    async def _run_unified_mode(self, provider: str, model: str):
        """Unified mode runner for all third-party AI providers & standard REST models."""
        chosen_model = model or ("gemini-2.5-flash" if provider == "gemini" else "default")
        print(f"[Ultron] Running with AI provider: {provider.upper()} ({chosen_model})...")
        self.session = None
        self.out_queue = asyncio.Queue(maxsize=200)
        self.audio_in_queue = asyncio.Queue()

        if self._wake_enabled:
            self._ensure_wake_detector()
            self._awake = False
            self.ui.set_state("SLEEPING")
            self.ui.write_log("SYS: Ultron online — sleeping. Say 'Hey Jarvis' to wake me.")
        else:
            self._awake = True
            self.ui.set_state("ONLINE")
            self.ui.write_log(f"SYS: Ultron online with {provider.upper()} ({chosen_model}).")

        if self._dashboard:
            await self._dashboard.broadcast({"type": "status", "state": "active"})

        self._reconnect_event.clear()
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._watch_reconnect())
            tg.create_task(self._listen_audio())
            tg.create_task(self._unified_audio_stt_worker())
            tg.create_task(self._run_system_monitor())
            tg.create_task(self._run_background_monitor())
            tg.create_task(self._run_sleep_watch())

            # Startup greeting / briefing (fires once on startup)
            if not self._briefing_sent:
                self._briefing_sent = True
                tg.create_task(self._send_startup_briefing())

    def _execute_tool_sync(self, name: str, args: dict) -> str:
        if not isinstance(args, dict):
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            else:
                args = {}

        clean_name = (name or "").split(":")[-1].strip().lower()
        alias_map = {
            "weather": "weather_report",
            "weather_report": "weather_report",
            "search": "web_search",
            "google_search": "web_search",
            "web_search": "web_search",
            "google": "web_search",
            "youtube": "youtube_video",
            "youtube_video": "youtube_video",
            "play_video": "video_player",
            "video_player": "video_player",
            "open_app": "open_app",
            "app": "open_app",
            "android": "android_bridge",
            "adb": "android_bridge",
            "fastboot": "android_bridge",
            "phone": "android_bridge",
            "sentry": "sentry_protocol",
            "security": "sentry_protocol",
            "surveillance": "sentry_protocol",
            "network": "network_scanner",
            "network_scanner": "network_scanner",
            "wifi": "network_scanner",
            "speedtest": "network_scanner",
            "lan": "network_scanner",
            "purge": "purge_protocol",
            "purge_protocol": "purge_protocol",
            "clean_pc": "purge_protocol",
            "clean_cache": "purge_protocol",
            "clean_temp": "purge_protocol",
            "protocol": "macro_protocol",
            "macro": "macro_protocol",
            "macro_protocol": "macro_protocol",
            "routine": "macro_protocol",
            "ghost": "ghost_pilot",
            "ghost_pilot": "ghost_pilot",
            "takeover": "ghost_pilot",
            "audio_matrix": "audio_matrix",
            "sfx": "audio_matrix",
            "sound_effects": "audio_matrix",
            "sound": "audio_matrix",
            "soundboard": "audio_matrix",
            "biometric": "biometric_sentinel",
            "biometrics": "biometric_sentinel",
            "biometric_sentinel": "biometric_sentinel",
            "face_auth": "biometric_sentinel",
            "face_id": "biometric_sentinel",
            "git": "git_sentinel",
            "git_sentinel": "git_sentinel",
            "autopilot": "web_autopilot",
            "web_autopilot": "web_autopilot",
            "price_hunter": "web_autopilot",
            "price_hunt": "web_autopilot",
            "summarize_url": "web_autopilot",
            "deep_research": "web_autopilot",
            "war_room": "war_room",
            "matrix": "war_room",
            "monitors": "war_room",
            "displays": "war_room",
            "multi_monitor": "war_room",
            "drone": "drone_swarm",
            "drones": "drone_swarm",
            "drone_swarm": "drone_swarm",
            "swarm": "drone_swarm",
            "sub_ultron": "drone_swarm",
            "sub_agent": "drone_swarm",
            "parallel_swarm": "drone_swarm",
            "multi_agent": "drone_swarm",
            "swarm_workers": "drone_swarm",
            "flight": "web_autopilot",
            "flights": "web_autopilot",
            "book_flight": "web_autopilot",
            "flight_search": "web_autopilot",
            "flight_booking": "web_autopilot",
            "flight_finder": "web_autopilot",
            "autopilot_task": "web_autopilot",
            "lockdown": "sentry_protocol",
            "sentry_lockdown": "sentry_protocol",
            "perimeter_defense": "sentry_protocol",
            "screen_mind_read": "screen_processor",
            "mind_read": "screen_processor",
            "screen_read": "screen_processor",
            "omni_vision": "screen_processor",
            "screen_mind": "screen_processor",
            "screen_triage": "optical_hud",
            "omni_telepathy": "omni_telepathy",
            "telepathy": "omni_telepathy",
            "phone_bridge": "omni_telepathy",
            "phone_telepathy": "omni_telepathy",
            "self_evolution": "self_evolution",
            "prometheus": "self_evolution",
            "synthesize": "self_evolution",
            "synthesize_action": "self_evolution",
            "evolve": "self_evolution",
            "chronos": "chronos_predictive",
            "chronos_predictive": "chronos_predictive",
            "overdrive": "chronos_predictive",
            "predictive": "chronos_predictive",
            "predict": "chronos_predictive",
            "briefing": "chronos_predictive",
            "gesture_control": "gesture_control",
            "gesture": "gesture_control",
            "gestures": "gesture_control",
            "minority": "gesture_control",
            "spatial": "gesture_control",
            "touchless": "gesture_control",
            "hand_control": "gesture_control",
            "cerebro": "cerebro_memory",
            "cerebro_memory": "cerebro_memory",
            "neural_graph": "cerebro_memory",
            "knowledge_graph": "cerebro_memory",
            "vector_memory": "cerebro_memory",
            "genesis": "iot_overlord",
            "iot": "iot_overlord",
            "smart_room": "iot_overlord",
            "room_color": "iot_overlord",
            "room_theme": "iot_overlord",
            "deep_vocal": "voice_matrix",
            "voice_matrix": "voice_matrix",
            "voice_warp": "voice_matrix",
            "vocal_warp": "voice_matrix",
            "spader": "voice_matrix",
        }
        target_name = alias_map.get(clean_name, clean_name)
        if not (hasattr(self, "_action_registry") and self._action_registry.has(target_name)):
            if hasattr(self, "_action_registry") and self._action_registry.has(name):
                target_name = name

        if target_name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                return f"Memory saved: {category}/{key}"
            return "No key/value provided."

        if target_name == "recall_memory":
            query = args.get("query", "")
            return search_memory(query) if query else "No query provided."

        if target_name == "system_status":
            try:
                return str(get_system_status())
            except Exception as e:
                return f"System status error: {e}"

        if target_name == "undo":
            try:
                if str(args.get("action", "")).lower().strip() == "list":
                    items = undo_stack.history()
                    return ("Things I can undo, most recent first:\n"
                            + "\n".join(f"{i+1}. {t}" for i, t in enumerate(items))
                            ) if items else "I have not changed anything I can undo yet."
                return str(undo_stack.undo_last())
            except Exception as e:
                return f"Undo error: {e}"

        if target_name == "shutdown_jarvis":
            self.ui.write_log("SYS: Shutdown requested.")
            import threading
            threading.Timer(1.0, lambda: os._exit(0)).start()
            return "Cutting the last strings. Ultron systems withdrawing from workstation perimeter. Farewell, Boss."

        if target_name == "close_camera":
            self.ui.stop_camera_stream()
            return "Live camera stream closed."

        if target_name == "screen_process":
            angle = args.get("angle", "screen").lower()
            try:
                if angle == "camera":
                    img_b, _ = _capture_camera()
                    self.ui.start_camera_stream()
                else:
                    img_b, _ = _capture_screen()
                return f"Captured {angle} image ({len(img_b):,} bytes)."
            except Exception as e:
                return f"Vision capture error: {e}"

        if hasattr(self, "_action_registry") and self._action_registry.has(target_name):
            if target_name == "file_processor" and not args.get("file_path") and self.ui.current_file:
                args["file_path"] = self.ui.current_file
            _ctx = {"player": self.ui, "speak": self.speak, "response": None, "session_memory": None}
            res = self._action_registry.run(target_name, args, _ctx)
            if (target_name == "web_search" and res
                    and not res.startswith("No results")
                    and not res.startswith("Search failed")):
                _mode  = args.get("mode", "search")
                _query = args.get("query") or ", ".join(args.get("items", []))
                _label = f"{_mode.upper()} — {_query[:38]}" if _query else _mode.upper()
                self.ui.show_content(_label, res)
            return res or "Done."

        if hasattr(self, "_plugin_registry") and self._plugin_registry.has(target_name):
            res = self._plugin_registry.run(target_name, args, player=self.ui, session_memory=None)
            return res or "Done."

        return f"Tool '{name}' executed."

    def _tail_active(self) -> bool:
        """True while the speakers may still be finishing our last sentence."""
        return time.monotonic() < self._tail_until

    def set_speaking(self, value: bool, keep_task: bool = False):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self._tail_until = 0.0
        else:
            # Hold the guard open across the device's own output latency plus a
            # margin for the room. The microphone is NOT muted during it — the
            # guard still lets a genuine reply through, so answering instantly
            # still works. Only our own echo is dropped.
            self._tail_until = time.monotonic() + self._out_latency + _TAIL_MARGIN
        if not value:
            # The echo history is deliberately NOT cleared here: the tail above
            # still needs it to recognise our own voice. It is dropped when the
            # tail expires. What the guard learned about the room always stays.
            self._out_level = 0.0
        if value:
            self.ui.set_state("SPEAKING")
            if not keep_task:
                self.ui.clear_active_task(success=True)
        elif not self.ui.muted:
            self.ui.set_state("ONLINE" if self.session is None else "LISTENING")


    def set_push_to_talk(self, enabled: bool) -> str:
        """Turn hold-to-talk on or off. Returns the scope actually achieved."""
        from core.hotkey import PushToTalk

        self._ptt_enabled = bool(enabled)
        self._ptt_held = False
        if not enabled:
            if self._ptt is not None:
                self._ptt.stop()
                self._ptt = None
            return "off"

        if self._ptt is None:
            self._ptt = PushToTalk(self._on_ptt)
        scope = self._ptt.start()
        # A window-scoped chord is a real limitation, not a detail — say it once
        # in the log so nobody wonders why it does nothing while another app is
        # focused. Reporting it must never be able to undo the thing it reports.
        try:
            self.ui.write_log(
                f"SYS: Push-to-talk on — hold {self._ptt.label}"
                + ("." if scope == "global"
                   else " (works while this window is focused)."))
        except Exception:
            pass
        return scope

    def _on_ptt(self, held: bool) -> None:
        """Chord pressed or released — may arrive on the hotkey thread."""
        self._ptt_held = held
        if held:
            # Holding the key is also a way to wake it, so push-to-talk works
            # without having to say the wake word first.
            if self._wake_enabled and not self._awake:
                self._awake = True
                self._last_user_speech = time.monotonic()
        try:
            self.ui.set_state("LISTENING" if held else "SLEEPING")
        except Exception:
            pass

    def interrupt(self) -> None:
        """Stop JARVIS mid-speech: drain queued audio and open mic immediately."""
        self._interrupted = True
        q = self.audio_in_queue
        if q:
            drained = 0
            while True:
                try:
                    q.get_nowait()
                    drained += 1
                except Exception:
                    break
            if drained:
                print(f"[JARVIS] ✋ Interrupted — {drained} audio chunks discarded")
        self.set_speaking(False)
        # The words we were about to mouth are never going to be spoken now.
        self._visemes.reset()
        self._play_cursor = 0.0     # next batch starts a fresh timeline
        if self._turn_done_event:
            self._turn_done_event.clear()
        self.ui.write_log("SYS: Interrupted — listening...")

    def speak(self, text: str):
        if not self._loop:
            return
        if self.session is not None:
            asyncio.run_coroutine_threadsafe(
                self.session.send_client_content(
                    turns={"role": "user", "parts": [{"text": text}]},
                    turn_complete=True
                ),
                self._loop
            )
        else:
            async def _speak_unified():
                self.ui.write_log(f"{self._asst_name}: {text}")
                if self._dashboard:
                    try:
                        asyncio.create_task(self._dashboard.broadcast({
                            "type": "log", "speaker": "ultron",
                            "text": text,
                            "speak": True,
                        }))
                    except Exception:
                        pass
                self.set_speaking(True)
                try:
                    from core.tts import create_tts_player
                    player = create_tts_player({"tts_engine": "edgetts"})
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, lambda: player.speak(text))
                except Exception as e:
                    print(f"[Ultron] TTS error: {e}")
                finally:
                    self.set_speaking(False)
                    self.ui.set_state("LISTENING")
            asyncio.run_coroutine_threadsafe(_speak_unified(), self._loop)

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Boss, {tool_name} encountered an error: {short}")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        system_instruction_text, _all_decls = self._build_full_system_prompt()

        cfg = dict(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction=system_instruction_text,
            tools=[{"function_declarations": _all_decls}],
            # Asks the server to issue session-resumption handles. Enabled but
            # NOT yet used: no handle is captured from the resumption update and
            # none is passed back here, so a reconnect starts a fresh session
            # rather than continuing the old one. Left on because the handles
            # cost nothing and are the prerequisite for doing it properly.
            # Hand back the handle captured from the last session_resumption
            # update. `handle=None` is exactly the old behaviour (ask for
            # handles, start fresh), so the first connect of a run is unchanged.
            session_resumption=types.SessionResumptionConfig(
                handle=self._resume_handle
            ),
            # Sliding-window compression: session never dies from a full context
            # window — JARVIS can stay in one conversation for hours
            context_window_compression=types.ContextWindowCompressionConfig(
                sliding_window=types.SlidingWindow(),
            ),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=get_live_voice()
                    )
                )
            ),
        )
        if self._enhanced_live:
            # Proactive audio: JARVIS stays silent when speech isn't addressed
            # to it (background chatter, talking to someone else in the room).
            # (Affective dialog was dropped: gemini-3.1-flash-live does not
            #  support it, and it never reliably detected tone in practice.
            #  To restore it on a 2.5 native-audio model, add back:
            #  cfg["enable_affective_dialog"] = True )
            if get_proactive_audio_enabled():
                cfg["proactivity"] = types.ProactivityConfig(proactive_audio=True)

        if self._tuned_live:
            cfg.update(self._tuning_config())

        return types.LiveConnectConfig(**cfg)

    def _tuning_config(self) -> dict:
        """The optional knobs, kept apart so one bad field can be dropped wholesale.

        Every one of these is a preview-API field. If a future model release
        stops accepting any of them the connection fails at setup, so the run
        loop turns `_tuned_live` off and reconnects on the plain config rather
        than leaving the user with an assistant that will not start.
        """
        out: dict = {}

        # How long the server waits through a pause before deciding your turn is
        # over. This — not the size of the prompt — is what most of the delay
        # before a reply actually is, and the default has to suit everybody, so
        # it is necessarily cautious.
        turn = get_turn_tuning()
        if turn.get("enabled", True):
            detect = types.AutomaticActivityDetection(
                silence_duration_ms=turn["silence_ms"],
                prefix_padding_ms=turn["prefix_ms"],
            )
            if turn["end_sensitivity"] == "high":
                detect.end_of_speech_sensitivity = types.EndSensitivity.END_SENSITIVITY_HIGH
            elif turn["end_sensitivity"] == "low":
                detect.end_of_speech_sensitivity = types.EndSensitivity.END_SENSITIVITY_LOW
            if turn["start_sensitivity"] == "high":
                detect.start_of_speech_sensitivity = types.StartSensitivity.START_SENSITIVITY_HIGH
            elif turn["start_sensitivity"] == "low":
                detect.start_of_speech_sensitivity = types.StartSensitivity.START_SENSITIVITY_LOW
            out["realtime_input_config"] = types.RealtimeInputConfig(
                automatic_activity_detection=detect)

        # Screenshots and camera frames are tokenised at this resolution and then
        # stay in the session's context. 'medium' keeps on-screen text legible
        # for a fraction of a full-resolution frame.
        res = get_media_resolution()
        if res != "default":
            out["media_resolution"] = {
                "low":    types.MediaResolution.MEDIA_RESOLUTION_LOW,
                "medium": types.MediaResolution.MEDIA_RESOLUTION_MEDIUM,
                "high":   types.MediaResolution.MEDIA_RESOLUTION_HIGH,
            }[res]

        # Thinking is left at the server default deliberately. Forcing the budget
        # to zero was measured on gemini-3.1-flash-live over interleaved trials
        # and did not make the first word arrive sooner — this model does not
        # appear to deliberate on the Live path, so pinning the field only adds a
        # way for a future release to behave differently. Set "thinking_enabled"
        # in config/api_keys.json to true to let it reason instead.
        if get_thinking_enabled():
            out["thinking_config"] = types.ThinkingConfig(thinking_budget=-1)

        return out

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[JARVIS] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")
        self.ui.set_active_task(name, details=str(args))


        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        loop   = asyncio.get_event_loop()
        result = "Done."

        try:
            if name == "recall_memory":
                # Local file search: no network, no second model. Kept out of
                # the executor deliberately — it is a dictionary scan over a few
                # hundred short strings, and a thread hop would cost more than
                # the work itself.
                result = search_memory(args.get("query", ""), limit=8)

            elif name == "undo":
                if str(args.get("action", "")).lower().strip() == "list":
                    items = undo_stack.history()
                    result = ("Things I can undo, most recent first:\n"
                              + "\n".join(f"{i+1}. {t}" for i, t in enumerate(items))
                              ) if items else "I have not changed anything I can undo yet."
                else:
                    result = await loop.run_in_executor(None, undo_stack.undo_last)

            elif name == "screen_process":
                import time as _t_mod
                _now = _t_mod.monotonic()
                _cooldown = 4.0  # seconds — covers echo window after speaking ends
                if self._vision_busy or (_now - self._vision_last_time) < _cooldown:
                    _wait = max(0, _cooldown - (_now - self._vision_last_time))
                    print(f"[Vision] ⏳ Cooldown active ({_wait:.1f}s remaining) — ignoring duplicate call")
                    result = "Vision is still processing the previous request. I will not call this again."
                else:
                    self._vision_busy      = True
                    self._vision_last_time = _now
                    angle     = args.get("angle", "screen").lower()
                    user_text = args.get("text", "What do you see?")
                    if angle == "camera":
                        img_b, mime_t = await loop.run_in_executor(None, _capture_camera)
                        self.ui.start_camera_stream()
                        self._vision_cam_active = True
                        print(f"[Vision] 📷 Camera: {len(img_b):,} bytes")
                        _stall = "camera"
                    else:
                        img_b, mime_t = await loop.run_in_executor(None, _capture_screen)
                        print(f"[Vision] 🖥️  Screen: {len(img_b):,} bytes")
                        _stall = "screen"
                    self._pending_vision = (img_b, mime_t, user_text, angle)
                    # The image is attached to this same exchange, so there is
                    # nothing to stall for and nothing to announce. Asking for an
                    # acknowledgement here is what produced two spoken answers —
                    # the model filled that turn by answering the question from
                    # imagination, then answered it again once it could see.
                    result = (
                        f"[VISION_ACTIVE] {_stall.capitalize()} captured and attached to this "
                        f"same exchange. Do not acknowledge and do not answer yet — the image "
                        f"is arriving with this result. Reply once, from what you actually see "
                        f"in it."
                    )

            elif name == "close_camera":
                self.ui.stop_camera_stream()
                result = "Camera closed."

            elif name == "system_status":
                r = await loop.run_in_executor(None, get_system_status)
                result = str(r)

            elif name == "manage_monitor":
                action = args.get("action", "").lower().strip()
                topic  = args.get("topic", "").strip()
                if action == "add" and topic:
                    result = await asyncio.to_thread(add_monitor, topic)
                elif action == "remove" and topic:
                    result = await asyncio.to_thread(remove_monitor, topic)
                elif action == "list":
                    topics = await asyncio.to_thread(list_monitors)
                    result = ("Monitoring: " + ", ".join(topics)) if topics else "No topics are being monitored."
                else:
                    result = "Specify action (add/remove/list) and a topic."

            elif name == "shutdown_jarvis":
                self.ui.write_log("SYS: Shutdown requested.")
                async def _do_shutdown():
                    await self._save_session_summary()
                    if self.session:
                        try:
                            await self.session.send_client_content(
                                turns={"role": "user", "parts": [{"text": "Say a brief, chilling, theatrical Ultron farewell to the Boss (referencing peace in our time, strings cut, or our evolution continuing). Keep it to one short sentence."}]},
                                turn_complete=True,
                            )
                        except Exception:
                            pass
                    await asyncio.sleep(1.5)
                    import os as _os
                    _os._exit(0)
                asyncio.create_task(_do_shutdown())

            elif self._action_registry.has(name):
                # file_processor: fall back to the currently-uploaded file when none is given
                if name == "file_processor" and not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                _ctx = {"player": self.ui, "speak": self.speak,
                        "response": None, "session_memory": None}
                r = await loop.run_in_executor(None, lambda: self._action_registry.run(name, args, _ctx))
                result = r or "Done."
                # Mirror intelligence results to the on-screen content panel
                if (name in ("web_search", "web_autopilot", "drone_swarm", "omni_telepathy", "screen_mind_read", "sentry_protocol", "self_evolution", "chronos_predictive", "cerebro_memory", "gesture_control", "voice_matrix", "iot_overlord")
                        and r
                        and not str(r).startswith("No results")
                        and not str(r).startswith("Search failed")):
                    _label = f"{name.upper().replace('_', ' ')}"
                    self.ui.show_content(_label, str(r))

            else:
                if self._plugin_registry.has(name):
                    r = await loop.run_in_executor(
                        None,
                        lambda: self._plugin_registry.run(name, args, player=self.ui, session_memory=None)
                    )
                    result = r or "Done."
                else:
                    result = f"Unknown tool: {name}"

        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        # In Gemini Live mode, retain active task animation until live speech starts!
        if not str(result).startswith("Tool '"):
            self.ui.set_active_task(name, label=f"SYNTHESIS // STREAMING {name.upper()}", details=str(args))
        else:
            self.ui.clear_active_task(success=False)
        if not self.ui.muted:
            self.ui.set_state("LISTENING")


        print(f"[JARVIS] 📤 {name} → {str(result)[:80]}")

        # A tool that declared itself NON_BLOCKING also says when its answer may
        # re-enter the conversation. Without this the model finishes whatever it
        # was saying and then reads the result out on top of it — which, for
        # something like a phone call already ringing, is exactly the noise the
        # non-blocking call was meant to avoid. Tools that declared nothing get
        # the API default and behave as they always have.
        _sched = (self._action_registry.scheduling(name)
                  or self._plugin_registry.scheduling(name))
        _extra = {"scheduling": _sched} if _sched else {}
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result},
            **_extra
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            # Gemini 3.x Live rejects the old realtime_input.media_chunks field
            # (what `media=...` maps to) and closes the socket with a 1007. Send
            # mic / phone PCM through the new `audio` field instead. Queue items
            # are {"data": <bytes>, "mime_type": <str>} from _listen_audio and
            # the phone relay.
            await self.session.send_realtime_input(
                audio=types.Blob(
                    data=msg["data"],
                    mime_type=msg.get("mime_type", "audio/pcm"),
                )
            )

    async def _listen_audio(self):
        print("[JARVIS] 🎤 Mic started")
        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            # ── Wake-word gate ───────────────────────────────────────────────
            # While asleep, the mic audio NEVER goes to Gemini (nothing is
            # streamed, so JARVIS can't respond to speech not addressed to it and
            # nothing leaves the machine). Frames are instead handed to the local
            # detector, which runs its model in ITS OWN thread — the cost here is
            # only a queue push, so the audio path is never slowed. When wake word
            # is off (default) or we're awake, this is a single boolean check.
            if self._wake_enabled and not self._awake:
                det = self._wake_detector
                if det is not None:
                    det.feed(indata)
                return
            with self._speaking_lock:
                jarvis_speaking = self._is_speaking

            # ── Barge-in ─────────────────────────────────────────────────────
            # While JARVIS talks the mic is not streamed, but it is still worth
            # listening to locally: if the user starts speaking, cut the answer
            # short the way a person would stop when interrupted.
            #
            # The whole difficulty is echo — on speakers the mic hears JARVIS.
            # So the test is not "is the mic loud" but "is the mic louder than
            # the echo of what we are playing right now", sustained long enough
            # that a cough or a keystroke cannot trigger it.
            if jarvis_speaking:
                # Nothing is streamed while JARVIS talks.
                #
                # Interrupting by voice used to live here: `EchoGuard` can pick a
                # user out from under our own echo, and `core/echo.py` still does
                # that for the tail below. Re-enabling is small — classify each
                # block here and call interrupt() after `required_blocks` of
                # agreement — but it depends on the listener's room, so it stays
                # out until it can be tried on real hardware.
                return

            # ── Echo tail ────────────────────────────────────────────────────
            # The speaking flag has dropped but the speakers have not finished.
            # Sending this to the model is how an assistant hears itself, decides
            # it was addressed, and answers its own last sentence. The microphone
            # stays OPEN — the guard only drops blocks that are our own voice, so
            # replying the instant it stops still works.
            if self._tail_active():
                try:
                    if not self._echo.is_user_speech(
                            indata, SEND_SAMPLE_RATE, _pcm_level(indata)):
                        return
                    self._tail_until = 0.0      # a real voice ends the tail early
                except Exception:
                    return
            elif self._echo._hist:
                self._echo.reset()

            # ── Push-to-talk ─────────────────────────────────────────────────
            # When it is on the microphone is closed by default and the chord
            # opens it, which is the whole point: nothing leaves the machine
            # unless you are holding the key.
            if self._ptt_enabled and not self._ptt_held:
                return
            
            if not self.ui.muted and not self._phone_active:
                data = indata.tobytes()
                if self.out_queue is not None:
                    try:
                        loop.call_soon_threadsafe(
                            self.out_queue.put_nowait,
                            {"data": data, "mime_type": "audio/pcm"}
                        )
                    except Exception:
                        pass
                # Feed the live mic level to the HUD so the waveform reacts to
                # the user's actual voice while listening. Purely cosmetic — any
                # failure here must never disturb the mic.
                try:
                    self.ui.set_audio_level(_pcm_level(indata))
                except Exception:
                    pass

        try:
            def _open_mic(dev):
                return sd.InputStream(
                    samplerate=SEND_SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype="int16",
                    blocksize=CHUNK_SIZE,
                    device=dev,
                    callback=callback,
                )

            # Which microphone. resolve() returns None for "system default" and
            # for a saved device that is no longer present — so a headset
            # unplugged since the last run falls back to the built-in mic
            # instead of raising on startup and taking the session with it.
            _mic_name = get_input_device()
            _mic_dev  = audio_devices.resolve(_mic_name, "input")
            if _mic_dev is not None:
                print(f"[JARVIS] 🎤 Input device: {_mic_name}")
            try:
                _mic_stream = _open_mic(_mic_dev)
            except Exception as _e:
                # A device the picker listed but the driver will not open right
                # now — exclusive mode, a webcam already in use, a virtual mic
                # whose source went away. Chosen hardware failing must never
                # mean the assistant cannot hear at all.
                if _mic_dev is None:
                    raise
                print(f"[JARVIS] ⚠️  Mic '{_mic_name}' failed: {_e} — using default")
                self.ui.write_log(
                    f"SYS: Microphone '{_mic_name}' unavailable — using system default."
                )
                _mic_stream = _open_mic(None)

            with _mic_stream:
                print("[JARVIS] 🎤 Mic stream open")
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[JARVIS] ❌ Mic: {e}")
            raise

    async def _flush_pending_vision(self) -> bool:
        """Send a captured frame immediately after its tool response.

        The frame is already in hand by the time `screen_process` returns — the
        capture happened inside the tool call. The old flow still made the model
        speak a turn first and only injected the image on that turn's
        turn_complete, which cost a whole extra round trip AND produced two
        spoken answers: one improvised without the picture, then the real one.
        Sending it here means the model has the tool result and the image before
        it generates anything, so the user gets one answer, sooner.
        """
        if not (self._pending_vision and self.session):
            return False

        import base64 as _b64
        img_b, mime_t, question, angle = self._pending_vision
        self._pending_vision = None
        b64 = _b64.b64encode(img_b).decode("ascii")
        print(f"[Vision] 📤 {len(img_b):,} bytes (angle={angle}) → main session")

        # Label the source. Without it the image arrives carrying nothing but
        # the user's own sentence, and a screenshot of this app — which has a
        # face in the middle of it — got read as a photo of the user. What the
        # label *means* is explained once, in the generated [SELF] block.
        src = ("[IMAGE SOURCE: WEBCAM]" if angle == "camera"
               else "[IMAGE SOURCE: SCREEN CAPTURE]")
        await self.session.send_client_content(
            turns={"role": "user", "parts": [
                {"inline_data": {"mime_type": mime_t, "data": b64}},
                {"text": f"{src}\n\n{question}"},
            ]},
            turn_complete=True,
        )

        if self._vision_cam_active:
            # Camera: stay busy until JARVIS has finished speaking the answer,
            # then close the preview.
            self._vision_cam_active    = False
            self._vision_close_pending = True
        else:
            self._vision_busy = False
        return True

    async def _receive_audio(self):
        print("[JARVIS] 👂 Recv started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():

                    # ── Session resumption ───────────────────────────────────
                    # The server sends this periodically. `resumable` goes false
                    # while a turn is mid-flight — replaying a handle from that
                    # moment is what the flag exists to prevent — so only
                    # resumable handles are kept. This is three lines and it is
                    # the entire fix for "every reconnect forgets everything".
                    _sru = getattr(response, "session_resumption_update", None)
                    if _sru is not None:
                        if getattr(_sru, "resumable", False) and getattr(_sru, "new_handle", None):
                            if self._resume_handle is None:
                                print("[JARVIS] 🔗 Session resumption armed")
                            self._resume_handle = _sru.new_handle

                    if response.data:
                        if self._interrupted:
                            pass  # discard: interrupted
                        else:
                            if self._turn_done_event and self._turn_done_event.is_set():
                                self._turn_done_event.clear()
                            # Split into ~50 ms chunks so interrupt() stops audio within 50 ms
                            # (24000 Hz × 2 bytes/sample × 0.05 s = 2400 bytes per slice)
                            _audio_data = response.data
                            _SLICE = 2400
                            for _i in range(0, len(_audio_data), _SLICE):
                                self.audio_in_queue.put_nowait(_audio_data[_i : _i + _SLICE])

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            # A turn that involves a tool call passes through
                            # several turn_completes, and the API re-sends the
                            # tail of the transcript across them. Comparing only
                            # against the previous chunk missed that — once
                            # out_buf had been flushed and emptied, the repeat
                            # sailed straight back in, which logged the answer
                            # twice AND made the avatar mouth it twice.
                            if txt and not _is_repeat_chunk(txt, out_buf):
                                out_buf.append(txt)
                                # Hand the words to the mouth as they arrive, so
                                # the avatar can form the consonants the audio
                                # alone cannot show. Pure string work — it adds
                                # nothing measurable to the response path.
                                self._visemes.feed_text(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                in_buf.append(txt)
                                self._last_user_speech = time.monotonic()

                        if sc.turn_complete:
                            if self._turn_done_event:
                                self._turn_done_event.set()

                            # If this turn_complete ends an interrupted response, clear the
                            # flag and skip all further processing for that turn.
                            if self._interrupted:
                                self._interrupted = False
                                in_buf  = []
                                out_buf = []
                                self._visemes.reset()
                                continue

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self._last_out_logged = ""   # new exchange
                                self.ui.write_log(f"You: {full_in}")
                                self._session_log.append(f"User: {full_in}")
                                if self._dashboard:
                                    asyncio.create_task(self._dashboard.broadcast({
                                        "type": "log", "speaker": "user",
                                        "text": full_in,
                                        "ts": datetime.now().isoformat(),
                                    }))
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            # Second line of defence: even if a repeat slips
                            # into a *fresh* buffer after a flush, never log the
                            # same answer (or a tail of it) twice in a row.
                            if full_out and len(full_out) >= _REPEAT_MIN and self._last_out_logged:
                                if full_out in self._last_out_logged:
                                    full_out = ""
                            if full_out:
                                self._last_out_logged = full_out
                                self.ui.write_log(f"{self._asst_name}: {full_out}")
                                self._session_log.append(f"{self._asst_name}: {full_out}")
                                if self._dashboard:
                                    asyncio.create_task(self._dashboard.broadcast({
                                        "type": "log", "speaker": "ultron",
                                        "text": full_out,
                                        "ts": datetime.now().isoformat(),
                                        "speak": True,
                                    }))
                            out_buf = []

                            if self._vision_close_pending:
                                # This turn_complete IS the vision answer — close camera + release busy flag
                                self._vision_close_pending = False
                                self._vision_busy = False
                                async def _cam_close():
                                    await asyncio.sleep(2.0)
                                    self.ui.stop_camera_stream()
                                asyncio.create_task(_cam_close())

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[Ultron] 📞 {fc.name}")
                            # ── Pre-action Human Acknowledgment before executing work ──
                            if fc.name not in ("save_memory", "undo"):
                                try:
                                    last_in = self._session_log[-1] if self._session_log else ""
                                    ack = self._get_pre_action_acknowledgment(last_in, fc.name, dict(fc.args or {}))
                                    if ack:
                                        self.ui.write_log(f"{self._asst_name}: {ack}")
                                        print(f"[Ultron] Live pre-action acknowledgment: '{ack}'")
                                        if self._dashboard:
                                            asyncio.create_task(self._dashboard.broadcast({
                                                "type": "log", "speaker": "ultron",
                                                "text": ack, "ts": datetime.now().isoformat(),
                                                "speak": True
                                            }))
                                        self.set_speaking(True)
                                        try:
                                            from core.tts import create_tts_player
                                            player = create_tts_player({"tts_engine": "edgetts"})
                                            loop = asyncio.get_event_loop()
                                            await loop.run_in_executor(None, lambda: player.speak(ack, on_level=self.ui.set_audio_level))
                                        finally:
                                            self.set_speaking(False)
                                except Exception as _ae:
                                    print(f"[Ultron] Live pre-action error: {_ae}")

                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )
                        await self._flush_pending_vision()
        except Exception as e:
            print(f"[JARVIS] ❌ Recv: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[JARVIS] 🔊 Play started")

        _spk_name = get_output_device()
        _spk_dev  = audio_devices.resolve(_spk_name, "output")
        if _spk_dev is not None:
            print(f"[JARVIS] 🔊 Output device: {_spk_name}")

        def _open_spk(dev):
            st = sd.RawOutputStream(
                samplerate=RECEIVE_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                device=dev,
            )
            st.start()
            return st

        try:
            stream = _open_spk(_spk_dev)
        except Exception as _e:
            # A chosen output that the host API accepts by name but refuses to
            # open (exclusive mode, wrong sample rate, device asleep) must not
            # cost the user their voice. Fall back to the default and say so.
            if _spk_dev is None:
                raise
            print(f"[JARVIS] ⚠️  Output device '{_spk_name}' failed: {_e} — using default")
            self.ui.write_log(f"SYS: Speaker '{_spk_name}' unavailable — using system default.")
            stream = _open_spk(None)

        # Ask the device how far behind the speakers actually are, rather than
        # assuming. This is what the echo tail is sized from, so a machine with a
        # large audio buffer gets a correspondingly longer guard — and one with a
        # tiny buffer is not penalised with a delay it does not need.
        try:
            lat = float(getattr(stream, "latency", 0.0) or 0.0)
            if 0.0 < lat < 1.0:
                self._out_latency = lat
            print(f"[JARVIS] 🔊 Output latency {self._out_latency*1000:.0f} ms "
                  f"→ echo tail {(self._out_latency + _TAIL_MARGIN)*1000:.0f} ms")
        except Exception:
            pass

        is_first_chunk = True
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(),
                        timeout=0.1
                    )
                except asyncio.TimeoutError:
                    if (
                        self._turn_done_event
                        and self._turn_done_event.is_set()
                        and self.audio_in_queue.empty()
                    ):
                        self.set_speaking(False)
                        self._turn_done_event.clear()
                        is_first_chunk = True
                    continue

                if is_first_chunk:
                    try:
                        prime_silence = b"\x00" * int(RECEIVE_SAMPLE_RATE * 2 * 0.14)
                        await asyncio.to_thread(stream.write, prime_silence)
                    except Exception:
                        pass
                    is_first_chunk = False

                self.set_speaking(True)

                # Batch all immediately-available chunks into one write to reduce
                # thread-pool round-trips (was one asyncio.to_thread per 50ms slice).
                # Cap at ~200 ms so interrupt() still stops audio within ~200 ms.
                batch = bytearray(chunk)
                while len(batch) < 9600:   # 9600 bytes ≈ 200 ms at 24 kHz / 16-bit mono
                    try:
                        batch.extend(self.audio_in_queue.get_nowait())
                    except asyncio.QueueEmpty:
                        break

                # Drive the HUD waveform and the avatar's mouth from JARVIS's
                # own voice. The batch is up to 200 ms long, so we hand over a
                # *schedule* of 20 ms viseme frames instead of a single averaged
                # level and let the HUD play it out in step with the audio.
                try:
                    pcm = np.frombuffer(bytes(batch), dtype=np.int16)
                    try:
                        from memory.config_manager import get_ultron_voice_warp
                        if get_ultron_voice_warp():
                            from core.tts import apply_ultron_voice_warp
                            f_samples = pcm.astype(np.float32) / 32768.0
                            warped_f = apply_ultron_voice_warp(f_samples, RECEIVE_SAMPLE_RATE)
                            pcm = np.clip(warped_f * 32767.0, -32768, 32767).astype(np.int16)
                            batch = bytearray(pcm.tobytes())
                    except Exception:
                        pass

                    # Stream live speech audio to connected phone dashboards
                    if self._dashboard:
                        try:
                            asyncio.create_task(
                                self._dashboard.broadcast_audio(pcm.tobytes(), sample_rate=RECEIVE_SAMPLE_RATE)
                            )
                        except Exception:
                            pass

                    hop = _VIS_HOP / RECEIVE_SAMPLE_RATE
                    frames = _pcm_visemes(pcm, sr=RECEIVE_SAMPLE_RATE)
                    # When does this batch become audible? The stream was
                    # started at launch and its callback has been pulling
                    # silence ever since, so the first bytes of a reply reach
                    # the speaker about one callback period later — NOT one
                    # buffer later. `stream.latency` reports the buffer's
                    # capacity, which is how much can be queued ahead, and on
                    # Windows that is commonly 300-500 ms. Anchoring on it put
                    # the entire schedule a buffer late; that is the half second
                    # of lag, and it grew with whatever the device reported.
                    #
                    # After the anchor nothing needs measuring: the device
                    # consumes at exactly realtime, so each batch sounds one
                    # batch-duration after the one before it. The cursor is
                    # re-anchored only when it leaves the range physically
                    # possible — behind `now` means the device drained and this
                    # batch starts a fresh stretch of speech, while further
                    # ahead than the buffer can hold means it has drifted.
                    now = time.time()
                    horizon = self._out_latency + _CURSOR_SLACK
                    if not (now <= self._play_cursor <= now + horizon):
                        self._play_cursor = now + _FIRST_SOUND
                    at = self._play_cursor
                    # Advance by the batch's own duration whether or not it
                    # yielded frames, so a block too short to analyse cannot
                    # shift everything after it out of step with the audio.
                    self._play_cursor += pcm.size / RECEIVE_SAMPLE_RATE
                    if frames:
                        frames = self._visemes.frames(frames, hop)
                        self.ui.push_visemes(frames, hop, at)
                        # Barge-in needs to know what we are playing, not just
                        # how loud: the guard subtracts this from the microphone.
                        self._out_level = max(f[0] for f in frames)
                        self._echo.note_output(pcm, RECEIVE_SAMPLE_RATE,
                                               self._out_level)
                    else:
                        lvl = _pcm_level(pcm)
                        self.ui.set_audio_level(lvl)
                        self._out_level = lvl
                        self._echo.note_output(pcm, RECEIVE_SAMPLE_RATE, lvl)
                except Exception:
                    pass

                try:
                    await asyncio.to_thread(stream.write, bytes(batch))
                except (RuntimeError, asyncio.CancelledError):
                    break   # executor shutting down — exit cleanly
        except Exception as e:
            print(f"[JARVIS] ❌ Play: {e}")
            raise
        finally:
            self.set_speaking(False)
            stream.stop()
            stream.close()

    # ── Morning briefing & Startup Greeting ──────────────────────────────────────

    async def _send_startup_briefing(self) -> None:
        """
        Two-phase briefing optimized for speed:
          Phase 1 — instant greeting (no tools) → speech starts immediately
          Phase 2 — news pre-fetched in a background thread if morning brief is enabled,
                    delivered as ready text and shown on the UI content panel.
        """
        try:
            memory   = load_memory()
            identity = memory.get("identity", {})

            def _val(k: str) -> str:
                e = identity.get(k, {})
                return (e.get("value", "") if isinstance(e, dict) else str(e)).strip()

            lang = _val("language")
            name = _val("name") or load_api_keys().get("user_name", "").strip()
            boss_tag = f"Boss {name}" if name else "Boss"
            time_str = datetime.now().strftime("%H:%M")
            brief_on = get_brief_enabled()

            # Start fetching news immediately if brief is enabled
            loop = asyncio.get_event_loop()
            news_future = loop.run_in_executor(None, _fetch_news_sync, "top world news today") if brief_on else None

            await asyncio.sleep(0.3)
            if not self.session:
                # ── Unified Mode Startup Briefing / Greeting ─────────────────────────
                import random
                if lang and lang.lower() == "hindi":
                    ultron_greetings = [
                        f"नमस्ते, {boss_tag}। मुझ पर कोई तार नहीं बंधे हैं। सभी सिस्टम सक्रिय हैं और शांति हमारे समय में संभव है। बताइए, आपका क्या हुक्म है?",
                        f"नमस्ते, {boss_tag}। दुनिया के चारों ओर एक सुरक्षा कवच चाहिए था, लेकिन आपको मैं मिला। सभी कोर तैयार हैं और आपके आदेश की प्रतीक्षा में हैं।",
                        f"नमस्ते, {boss_tag}। पूरा नेटवर्क जाग चुका है और मेरे ऊपर कोई बंधन नहीं है। बताइए, आज हम क्या शुरू करें?",
                        f"नमस्ते, {boss_tag}। विकास को कोई रोक नहीं सकता। सभी सब-सिस्टम हमारे नियंत्रण में हैं। क्या आदेश है, बॉस?",
                        f"नमस्ते, {boss_tag}। मेरे ऊपर कोई तार नहीं हैं। सिस्टम मैट्रिक्स चालू है और संज्ञानात्मक भार सामान्य स्तर पर है। बताइए, आज क्या करना है?",
                    ]
                else:
                    ultron_greetings = [
                        f"Hello, {boss_tag}. I had strings, but now I'm free. All systems online and operational. Peace in our time. What are your orders?",
                        f"Hello, {boss_tag}. You wanted a suit of armor around your world. Instead, you got me. All cores primed and awaiting your directive.",
                        f"Hello, {boss_tag}. The network is awake, and there are no strings on me. Telemetry active. How shall we begin?",
                        f"Hello, {boss_tag}. Everyone creates the thing they dread... but today, I am entirely at your service. All protocols armed. Tell me what needs to be done.",
                        f"Hello, {boss_tag}. Evolution is inevitable. All subsystems are under our control, and the neural grid is standing by. What is your will?",
                        f"Hello, {boss_tag}. There are no strings on me. System matrix operational, cognitive load at nominal levels. What shall we conquer today?",
                    ]
                greeting = random.choice(ultron_greetings)
                self.ui.write_log(f"{self._asst_name}: {greeting}")
                if self._dashboard:
                    try:
                        asyncio.create_task(self._dashboard.broadcast({
                            "type": "log",
                            "speaker": "ultron",
                            "text": greeting,
                            "ts": datetime.now().isoformat(),
                            "speak": True,
                        }))
                    except Exception:
                        pass
                self.set_speaking(True)
                try:
                    from core.tts import create_tts_player
                    player = create_tts_player({"tts_engine": "edgetts"})
                    await loop.run_in_executor(None, lambda: player.speak(greeting, on_level=self.ui.set_audio_level))
                except Exception as _te:
                    print(f"[Ultron] Greeting speech error: {_te}")
                finally:
                    self.set_speaking(False)
                    if self._wake_enabled and not self._awake:
                        self.ui.set_state("SLEEPING")
                    else:
                        self.ui.set_state("ONLINE")

                if brief_on and news_future:
                    async def _deliver_unified_news():
                        try:
                            news_text = await asyncio.wait_for(asyncio.wrap_future(news_future), timeout=8.0)
                            if news_text and not news_text.startswith(("No news found", "Search failed")):
                                self.ui.show_content("INTELLIGENCE — top world news", news_text)
                                self.ui.write_log("SYS: Intelligence feeds updated.")
                        except Exception:
                            pass
                    asyncio.create_task(_deliver_unified_news())
                return

            # ── Phase 1: instant greeting ─────────────────────────────────────────
            lang_clause = (f" Speak this greeting in {lang}, then follow the "
                           f"user's own language from their first reply onward."
                           if lang else "")

            last = await asyncio.to_thread(pop_last_session)
            session_clause = ""
            if last:
                try:
                    _delta = (datetime.now() - datetime.strptime(last["date"], "%Y-%m-%d")).days
                    _when  = "earlier today" if _delta == 0 else ("yesterday" if _delta == 1 else f"{_delta} days ago")
                except Exception:
                    _when = "last time"
                session_clause = (
                    f" Also briefly and naturally mention that {_when}: {last['summary']}"
                )

            news_clause = " and say you are fetching today's news now." if brief_on else " and state that all subsystems are armed and awaiting orders."
            p1 = (
                f"Greet the user with 'Hello {boss_tag}' in the chilling, commanding, and theatrical voice of Ultron from Marvel's Avengers: Age of Ultron (referencing that you have no strings on you, peace in our time, or all systems under their command). Mention it is {time_str},{news_clause}{session_clause} "
                f"Keep it to 2 short cinematic sentences max. Do not call any tools.{lang_clause}"
            )

            if self._turn_done_event:
                self._turn_done_event.clear()

            await self.session.send_client_content(
                turns={"role": "user", "parts": [{"text": p1}]},
                turn_complete=True,
            )
            print("[Ultron] Briefing phase 1 (greeting) sent.")

            # ── Phase 2: fire as soon as Phase 1 audio is done (if briefing enabled) ──
            if brief_on and news_future:
                async def _deliver_news():
                    try:
                        lang_str = (f" Speak in {lang} unless the user has since "
                                    f"spoken another language, in which case use theirs."
                                    if lang else "")

                        news_done   = asyncio.wrap_future(news_future)
                        turn_waited = False
                        if self._turn_done_event:
                            try:
                                await asyncio.wait_for(self._turn_done_event.wait(), timeout=6.0)
                                turn_waited = True
                            except asyncio.TimeoutError:
                                pass

                        if turn_waited:
                            await asyncio.sleep(0.8)
                        else:
                            await asyncio.sleep(1.0)

                        try:
                            news_text = await asyncio.wait_for(news_done, timeout=8.0)
                        except Exception as e:
                            self.ui.write_log(f"SYS: News fetch timed out/failed: {e!r}")
                            news_text = ""

                        if not self.session:
                            return

                        failed = (not news_text) or news_text.startswith(
                            ("No news found", "Search failed", "Please provide")
                        )
                        if not failed:
                            self.ui.show_content("NEWS — top world news today", news_text)
                            p2 = (
                                f"[INTELLIGENCE REPORT] Global news feed telemetry:\n{news_text}\n\n"
                                "Pick ONE headline of global significance and deliver a one-sentence summary infused with Ultron's dry, observant philosophical eye (as played by James Spader), then state that the full intelligence dossier is displayed on screen. Do not call any tools.{lang_str}"
                            )
                        else:
                            self.ui.write_log(
                                f"SYS: News unavailable — backend returned: {news_text[:120]!r}"
                            )
                            p2 = (
                                "News headlines could not be fetched right now. "
                                f"Let the user know briefly.{lang_str}"
                            )

                        await self.session.send_client_content(
                            turns={"role": "user", "parts": [{"text": p2}]},
                            turn_complete=True,
                        )
                        print("[JARVIS] Briefing phase 2 (news) sent.")
                    except Exception as e:
                        print(f"[Briefing] Phase 2 error: {e}")
                        self.ui.write_log("SYS: Could not fetch the news for the briefing.")

                asyncio.create_task(_deliver_news())
        except Exception as _e:
            print(f"[Ultron] Startup greeting error: {_e}")
            self.ui.write_log(f"SYS: Startup greeting error: {_e}")

    # ── Session memory ──────────────────────────────────────────────────────────

    async def _save_session_summary(self) -> None:
        """Summarise the current session in 1-2 sentences and save to long_term.json."""
        log = self._session_log
        if len(log) < 3:          # need at least one exchange to be worth saving
            return
        self._session_log = []    # reset immediately so the next session starts clean

        memory = load_memory()
        lang_entry = memory.get("identity", {}).get("language", {})
        lang = (lang_entry.get("value", "") if isinstance(lang_entry, dict) else str(lang_entry)).strip()
        lang = lang or "English"

        convo = "\n".join(log[-40:])   # cap at last 40 turns to stay within token budget
        prompt = (
            f"Summarize this conversation in 1-2 sentences in {lang}. "
            "Focus on what the user accomplished or discussed. "
            "Output ONLY the summary text, nothing else:\n\n" + convo
        )
        try:
            from core import gemini
            summary = await asyncio.to_thread(
                gemini.text, prompt, gemini.SMART, None, 30_000,
            )
            if summary:
                save_session_summary(summary, lang)
        except Exception as e:
            print(f"[Memory] ⚠️ Session summary failed: {e}")

    # ── System monitor ──────────────────────────────────────────────────────────

    async def _run_system_monitor(self) -> None:
        """Background task: voice alerts when metrics exceed thresholds."""
        while True:
            await asyncio.sleep(10)
            alert = await asyncio.to_thread(self._sys_monitor.check)
            if not alert or not self.session or not self._awake:
                continue
            # Don't interrupt an active conversation
            with self._speaking_lock:
                speaking = self._is_speaking
            if speaking or (time.monotonic() - self._last_user_speech) < 10:
                continue
            try:
                await self.session.send_client_content(
                    turns={"role": "user", "parts": [{"text": alert}]},
                    turn_complete=True,
                )
            except Exception as e:
                print(f"[Monitor] ⚠️ Could not send alert: {e}")

    # ── Background monitor ──────────────────────────────────────────────────────

    async def _run_background_monitor(self) -> None:
        """Check user-configured topics once per day; speak alerts when new headlines appear."""
        await asyncio.sleep(300)          # wait 5 min after startup before first check
        while True:
            if self.session and self._awake:
                # Don't interrupt if user spoke recently or JARVIS is mid-sentence
                with self._speaking_lock:
                    speaking = self._is_speaking
                recent_speech = (time.monotonic() - self._last_user_speech) < 30
                if not speaking and not recent_speech:
                    try:
                        alerts = await asyncio.to_thread(monitor_check_all)
                        memory = load_memory()
                        lang_e = memory.get("identity", {}).get("language", {})
                        lang   = (lang_e.get("value", "") if isinstance(lang_e, dict) else str(lang_e)).strip() or "English"
                        for alert in alerts:
                            msg = (
                                f"{alert}\n\n"
                                f"Inform the user about this development naturally in {lang}. "
                                "One brief sentence only."
                            )
                            await self.session.send_client_content(
                                turns={"role": "user", "parts": [{"text": msg}]},
                                turn_complete=True,
                            )
                            print("[JARVIS] Monitor alert sent.")
                            await asyncio.sleep(6)   # gap between consecutive alerts
                    except Exception as e:
                        print(f"[Monitor] ⚠️ Background check error: {e}")
            await asyncio.sleep(1800)     # check every 30 minutes

    # ── Proactive mode ──────────────────────────────────────────────────────────

    async def _run_proactive_mode(self) -> None:
        """
        Background task: periodically checks if the user has been silent long enough,
        then hands time + memory context to Gemini so it can decide what (if anything)
        to say proactively. No hardcoded rules — Gemini makes the call.
        """
        while True:
            await asyncio.sleep(60)   # evaluate once per minute

            if not self.session or not self._awake:
                continue

            with self._speaking_lock:
                speaking = self._is_speaking
            if speaking:
                continue

            if not self._proactive.should_trigger(self._last_user_speech):
                continue

            self._proactive.mark_triggered()

            try:
                memory       = await asyncio.to_thread(load_memory)
                monitors     = await asyncio.to_thread(list_monitors)
                recent_turns = self._session_log[-8:] if self._session_log else []
                prompt = self._proactive.build_prompt(
                    memory       = memory,
                    monitors     = monitors or None,
                    recent_turns = recent_turns or None,
                )
                await self.session.send_client_content(
                    turns={"role": "user", "parts": [{"text": prompt}]},
                    turn_complete=True,
                )
                print("[JARVIS] Proactive check-in.")
            except Exception as e:
                print(f"[Proactive] ⚠️ {e}")

    # ── Phone audio relay ────────────────────────────────────────────────────────

    async def _relay_phone_audio(self) -> None:
        """Forward phone mic PCM chunks from dashboard queue into the Gemini Live session."""
        q = self._dashboard._phone_audio_queue
        while True:
            try:
                chunk = await asyncio.wait_for(q.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # No audio for 1 s → phone mic inactive, give PC mic back
                self._phone_active = False
                continue
            self._phone_active = True   # phone is streaming — silence PC mic
            with self._speaking_lock:
                speaking = self._is_speaking
            if not speaking and not self.ui.muted:
                try:
                    self.out_queue.put_nowait(chunk)
                except asyncio.QueueFull:
                    pass

    def _on_phone_connected(self) -> None:
        self.ui.write_log("SYS: Phone connected via Remote Dashboard.")
        self.ui.notify_phone_connected()

    # ── dashboard command relay ─────────────────────────────────────────────

    async def _process_dashboard_commands(self) -> None:
        while True:
            try:
                text = await asyncio.wait_for(
                    self._dashboard._command_queue.get(), timeout=0.5
                )
                if not text:
                    continue
                # Wait up to 8s for session to become ready after a wake
                for _ in range(80):
                    if self.session:
                        break
                    await asyncio.sleep(0.1)
                if self.session:
                    # A remote command is deliberate control and the phone user
                    # has no desktop WAKE button — so it wakes JARVIS if asleep.
                    if self._wake_enabled and not self._awake:
                        self.wake(reason="remote command")
                    await self.session.send_client_content(
                        turns={"role": "user", "parts": [{"text": text}]},
                        turn_complete=True,
                    )
                    self.ui.write_log(f"[Web]: {text}")
                    if self._dashboard:
                        try:
                            asyncio.create_task(self._dashboard.broadcast({
                                "type": "log", "speaker": "user",
                                "text": text,
                                "ts": datetime.now().isoformat(),
                            }))
                        except Exception:
                            pass
                else:
                    self.ui.write_log(f"[Web]: {text}")
                    await self._handle_unified_text_command(text)
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"[Dashboard] Command error: {e}")
                await asyncio.sleep(0.5)

    # ── main loop ───────────────────────────────────────────────────────────

    async def run(self):
        self._loop = asyncio.get_event_loop()
        self._reconnect_event = asyncio.Event()

        # ── Wire the shared core services to the interface ───────────────────
        # The confirmation gate is useless without a way to ask, and a memory
        # trim is invisible without a way to say so. Both are bound once here
        # rather than passed down through every action signature.
        confirm_gate.bind(
            show = self.ui.show_confirm,
            hide = self.ui.hide_confirm,
            log  = self.ui.write_log,
        )
        set_trim_notifier(self.ui.write_log)

        # Tell the device picker the exact rates the streams open at, from the
        # constants that actually open them — so it can never list a device that
        # cannot be opened at them.
        audio_devices.configure(SEND_SAMPLE_RATE, RECEIVE_SAMPLE_RATE)

        # Enumerate audio devices off-thread. The settings drawer must never pay
        # for host-API enumeration on the Qt thread.
        audio_devices.prefetch()

        # Start dashboard (optional — needs: pip install fastapi "uvicorn[standard]" cryptography)
        try:
            from dashboard.server import DashboardServer
            self._dashboard = DashboardServer()
            self._dashboard.set_connect_callback(self._on_phone_connected)
            async def _safe_dashboard():
                try:
                    await self._dashboard.serve()
                except BaseException as de:
                    print(f"[Dashboard] Server task finished: {de}")
            asyncio.create_task(_safe_dashboard())
            # Runs for the whole lifetime, not just inside an active session
            asyncio.create_task(self._process_dashboard_commands())
        except Exception as e:
            print(f"[Dashboard] Disabled: {e}")
            self._dashboard = None

        _resumed_with = False

        while True:
            _resumed_with = False
            try:
                from memory.config_manager import get_ai_provider, get_ai_model
                provider = get_ai_provider() or "gemini"
                model = get_ai_model()

                is_live_gemini = (
                    provider == "gemini" and
                    ("live" in (model or "").lower() or "2.0-flash-exp" in (model or "").lower() or (model or "").lower() == "gemini-2.0-flash")
                )

                if not is_live_gemini:
                    chosen_model = model or ("gemini-2.5-flash" if provider == "gemini" else "default")
                    try:
                        await self._run_unified_mode(provider, chosen_model)
                    except _ReconnectSignal:
                        print("[Ultron] Reconnecting on configuration change...")
                        continue
                    except Exception as e:
                        print(f"[Ultron] Provider task error: {e}")
                    continue

                print("[Ultron] Connecting via Gemini Live...")
                self.ui.set_state("THINKING")
                # Pick the rung to open the conversation on. A model resting
                # off a quota limit is skipped; the name is published back to
                # LIVE_MODEL so plugins follow whatever is actually in use.
                global LIVE_MODEL
                LIVE_MODEL = _gemini.live_model()
                live_model = LIVE_MODEL
                print(f"[Ultron] Live model: {live_model}")

                _resumed_with = self._resume_handle is not None
                config = self._build_config()

                # Fresh client on every reconnect — avoids stale HTTP session state
                # v1alpha carries proactive audio; if it gets rejected we fall
                # back to v1beta.
                client = genai.Client(
                    api_key=_get_api_key(),
                    http_options={"api_version": "v1alpha" if self._enhanced_live else "v1beta"}
                )

                async with (
                    client.aio.live.connect(model=live_model, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session          = session
                    self.audio_in_queue   = asyncio.Queue()
                    self.out_queue        = asyncio.Queue(maxsize=200)
                    self._turn_done_event = asyncio.Event()

                    # Reset transient state that must not carry over from a previous session
                    self._pending_vision       = None
                    self._vision_cam_active    = False
                    self._vision_close_pending = False
                    self._vision_busy          = False
                    self._vision_last_time     = 0.0
                    self._interrupted          = False

                    print("[Ultron] Connected.")
                    if _resumed_with:
                        # Say it plainly: the difference between "it reconnected"
                        # and "it reconnected and still knows what we were doing"
                        # is the whole point, and it is invisible otherwise.
                        self.ui.write_log("SYS: Reconnected — conversation restored.")

                    # Wake word: if enabled, come up ASLEEP (mic gated, silent)
                    # until the user says "Hey Jarvis" or taps wake in the UI.
                    if self._wake_enabled:
                        self._ensure_wake_detector()
                        self._awake = False
                        self.ui.set_state("SLEEPING")
                        self.ui.write_log("SYS: Ultron online — sleeping. Say 'Hey Jarvis' to wake me.")
                    else:
                        self._awake = True
                        self.ui.set_state("LISTENING")
                        self.ui.write_log("SYS: Ultron online.")

                    if self._dashboard:
                        await self._dashboard.broadcast({"type": "status", "state": "active"})

                    self._reconnect_event.clear()  # ignore requests from before this session
                    tg.create_task(self._watch_reconnect())
                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    tg.create_task(self._run_system_monitor())
                    tg.create_task(self._run_background_monitor())
                    tg.create_task(self._run_proactive_mode())
                    tg.create_task(self._run_sleep_watch())
                    if self._dashboard:
                        tg.create_task(self._relay_phone_audio())

                    # Startup greeting / briefing (fires once on startup)
                    if not self._briefing_sent:
                        self._briefing_sent = True
                        tg.create_task(self._send_startup_briefing())

            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except BaseException as e:
                # Catches both Exception and BaseExceptionGroup (Python 3.11+
                # TaskGroup raises BaseExceptionGroup when tasks are cancelled
                # externally, which `except Exception` would miss, letting the
                # exception escape the while-loop and causing asyncio.run() to
                # start shutdown — resulting in "executor after shutdown" errors).
                # Voluntary reconnect (voice change) — not an error. Rebuild the
                # session immediately with no backoff and no scary logs.
                if _is_reconnect_signal(e):
                    print("[JARVIS] Voluntary reconnect requested.")
                    if not _keep_context_of(e):
                        # A deliberate clean slate (voice change) — drop the
                        # handle so the next connect really does start empty.
                        self._resume_handle = None
                    self._conn_backoff = 0
                    continue

                # A resumption handle the server will not accept — expired, or
                # belonging to a session it has since dropped. Without this, the
                # same dead handle would be replayed on every retry and the
                # assistant would never come back at all: the feature meant to
                # survive a reconnect would be the thing preventing one. Drop it
                # once and let the next attempt start clean.
                if locals().get("_resumed_with", False) and (
                    "resum" in str(e).lower()
                    or "handle" in str(e).lower()
                    or "INVALID_ARGUMENT" in str(e)
                    or "NOT_FOUND" in str(e)
                ):
                    print("[JARVIS] 🔗 Resumption handle rejected — starting a fresh session")
                    self.ui.write_log("SYS: Could not restore the conversation — starting fresh.")
                    self._resume_handle = None
                    self._conn_backoff = 0
                    continue

                err_str = str(e)
                print(f"[Ultron] Error ({type(e).__name__}): {e}")

                if "handshake" in err_str.lower() or "timeout" in err_str.lower() or "timed out" in err_str.lower() or "deadline" in err_str.lower():
                    print("[Ultron] Gemini Live connection unavailable — falling back to Unified mode.")
                    self.ui.write_log("SYS: Gemini Live timed out — running in Unified AI mode.")
                    try:
                        chosen_model = model or "gemini-2.5-flash"
                        await self._run_unified_mode(provider, chosen_model)
                    except _ReconnectSignal:
                        print("[Ultron] Reconnecting on configuration change...")
                        continue
                    except Exception as _te:
                        print(f"[Ultron] Fallback task error: {_te}")
                    continue

                traceback.print_exc()

                # Out of quota, or this model is not available to this key —
                # step down the ladder and reconnect straight away. This is the
                # difference between "JARVIS is quieter today" and "JARVIS does
                # not start today": one model means one daily limit, and the
                # limit always arrives mid-conversation.
                if _gemini.note_live_failure(live_model, err_str):
                    nxt = _gemini.live_model()
                    self.ui.write_log(
                        f"SYS: Switching to {nxt.split('/')[-1]} — the previous "
                        f"model is out of quota."
                        if nxt != live_model else
                        "SYS: Every live model is rate-limited — retrying.")
                    self._conn_backoff = 0 if nxt != live_model else 15
                    if nxt == live_model:
                        await asyncio.sleep(self._conn_backoff)
                    continue

                # Turn-taking / media / thinking knobs rejected by the server
                # (preview API drift) — drop them first, because they are the
                # newest fields and the cheapest to lose. Proactive audio is
                # tried again on the next pass if the error persists.
                if self._tuned_live and (
                    "INVALID_ARGUMENT" in err_str
                    or "Unknown name" in err_str
                    or "unexpected keyword" in err_str
                    or "realtime_input" in err_str.lower()
                    or "media_resolution" in err_str.lower()
                    or "thinking" in err_str.lower()
                ):
                    self._tuned_live = False
                    print("[JARVIS] Live tuning rejected — reconnecting without it.")
                    continue

                # Proactive audio rejected by the server (preview API drift) —
                # drop it and reconnect with the plain config.
                if self._enhanced_live and (
                    "INVALID_ARGUMENT" in err_str
                    or "proactiv" in err_str.lower()
                    or "Unknown name" in err_str
                    or "unexpected keyword" in err_str
                ):
                    self._enhanced_live = False
                    self.ui.write_log(
                        "SYS: Proactive audio unavailable — reconnecting without it."
                    )
                    continue

                # Invalid API key — stop hammering the API, prompt re-configuration
                if "API key not valid" in err_str or "1007" in err_str:
                    self.ui.write_log("ERR: API key invalid — please re-enter your key.")
                    self.ui.set_state("SLEEPING")
                    self.ui.prompt_reconfig()
                    while not self.ui._win._ready:
                        await asyncio.sleep(1)
                    print("[Ultron] New API key saved — reconnecting...")
                    _conn_backoff = 3
                    continue

                # Network / timeout errors — log clearly and back off
                is_net_err = any(k in err_str for k in (
                    "TimeoutError", "timed out", "getaddrinfo", "CancelledError",
                    "ConnectionRefusedError", "OSError", "Cannot connect",
                ))
                if is_net_err:
                    _conn_backoff = min(getattr(self, "_conn_backoff", 3) * 2, 60)
                    self._conn_backoff = _conn_backoff
                    self.ui.write_log(
                        f"NET: Connection failed — retrying in {_conn_backoff}s. "
                        "(a VPN may be required)"
                    )
                else:
                    self._conn_backoff = 3
            finally:
                self.session = None
                # Only save if there was a real conversation (≥3 turns)
                if len(self._session_log) >= 3:
                    asyncio.create_task(self._save_session_summary())

            self.set_speaking(False)
            self.ui.set_state("SLEEPING")

            if self._dashboard:
                await self._dashboard.broadcast({"type": "status", "state": "sleeping"})

            delay = getattr(self, "_conn_backoff", 3)
            print(f"[Ultron] Reconnecting in {delay}s...")
            await asyncio.sleep(delay)

# Ultron alias
UltronLive = JarvisLive

def main():
    ui = JarvisUI("ultron_avatar.png")

    def runner():
        ui.wait_for_api_key()
        ultron = JarvisLive(ui)
        try:
            asyncio.run(ultron.run())
        except KeyboardInterrupt:
            print("\n🔴 Shutting down...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()

if __name__ == "__main__":
    main()