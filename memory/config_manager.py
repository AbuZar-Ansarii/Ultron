import json
import sys
from pathlib import Path

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR    = get_base_dir()
CONFIG_DIR  = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "api_keys.json"

def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def config_exists() -> bool:
    return CONFIG_FILE.exists()

def save_api_keys(gemini_api_key: str) -> None:
    ensure_config_dir()

    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    data["gemini_api_key"] = gemini_api_key.strip()

    CONFIG_FILE.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8"
    )

def load_api_keys() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Failed to load api_keys.json: {e}")
        return {}

def get_gemini_key() -> str | None:
    return load_api_keys().get("gemini_api_key")

def get_ai_provider() -> str:
    """Return configured AI provider ('gemini', 'ollama', 'gpt', 'nvidia_nim', 'opencode_zen', 'claude', 'deepseek', etc.)"""
    return load_api_keys().get("ai_provider", "").strip().lower()

def get_ai_model() -> str:
    """Return configured AI model name for the current provider."""
    cfg = load_api_keys()
    provider = get_ai_provider()
    if "ai_model" in cfg and cfg["ai_model"]:
        return str(cfg["ai_model"]).strip()
    # Provider-specific fallbacks
    defaults = {
        "gemini": "gemini-2.5-flash",
        "ollama": "llama3.2",
        "gpt": "gpt-4o",
        "nvidia_nim": "meta/llama-3.3-70b-instruct",
        "opencode_zen": "opencode/zen-coder-34b",
        "claude": "claude-3-7-sonnet-20250219",
        "deepseek": "deepseek-chat",
        "groq": "llama-3.3-70b-versatile",
        "openrouter": "meta-llama/llama-3.3-70b-instruct",
    }
    return defaults.get(provider, "gemini-2.5-flash")

def get_provider_key(provider: str = "") -> str:
    """Retrieve the API key for the specified provider (or the active provider if empty)."""
    cfg = load_api_keys()
    p = (provider or get_ai_provider() or "gemini").lower()
    return (
        cfg.get(f"{p}_api_key") or
        cfg.get(f"{p}_key") or
        cfg.get("api_key") or
        (cfg.get("gemini_api_key") if p == "gemini" else "") or
        (cfg.get("openai_api_key") if p == "gpt" else "") or
        ""
    ).strip()

def get_provider_url(provider: str = "") -> str:
    """Retrieve the base / server URL for the specified provider."""
    cfg = load_api_keys()
    p = (provider or get_ai_provider()).lower()
    if p == "ollama":
        return cfg.get("llm_url") or "http://localhost:11434"
    if p == "nvidia_nim":
        return cfg.get("nvidia_base_url") or "https://integrate.api.nvidia.com/v1"
    if p == "opencode_zen":
        return cfg.get("opencode_base_url") or "https://api.opencode.zen/v1"
    if p == "deepseek":
        return cfg.get("deepseek_base_url") or "https://api.deepseek.com"
    if p == "openrouter":
        return cfg.get("openrouter_base_url") or "https://openrouter.ai/api/v1"
    if p == "gpt":
        return cfg.get("openai_base_url") or "https://api.openai.com/v1"
    return cfg.get(f"{p}_base_url") or ""

def save_ai_provider(provider: str, model: str, api_key: str = "", base_url: str = "") -> None:
    """Save chosen AI provider, model, API key, and base URL to config."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["ai_provider"] = provider.strip().lower()
    data["ai_model"] = model.strip()
    p = data["ai_provider"]
    if api_key:
        data["api_key"] = api_key.strip()
        data[f"{p}_api_key"] = api_key.strip()
        if p == "gemini":
            data["gemini_api_key"] = api_key.strip()
        elif p == "gpt":
            data["openai_api_key"] = api_key.strip()
        elif p == "claude":
            data["anthropic_api_key"] = api_key.strip()
    if base_url:
        data[f"{p}_base_url"] = base_url.strip()
        if p == "ollama":
            data["llm_url"] = base_url.strip()
            data["llm_model"] = model.strip()
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")

def is_configured() -> bool:
    cfg = load_api_keys()
    if not cfg or not cfg.get("os_system"):
        return False
    provider = cfg.get("ai_provider", "").strip().lower()
    if not provider:
        return False
    if provider == "ollama":
        return True
    key = get_provider_key(provider)
    return bool(key and len(key) > 3)


def get_assistant_name() -> str:
    """Return the configured assistant name, or 'Ultron' if not set."""
    return load_api_keys().get("assistant_name", "Ultron") or "Ultron"


def get_user_name() -> str:
    """Return the configured user name for addressing."""
    return load_api_keys().get("user_name", "")


def save_assistant_config(assistant_name: str, user_name: str) -> None:
    """Persist assistant name and user name to config."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["assistant_name"] = assistant_name.strip() or "Ultron"
    data["user_name"] = user_name.strip()
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_telegram_config() -> dict:
    """Return dict with telegram_bot_token, telegram_chat_id, and telegram_enabled."""
    cfg = load_api_keys()
    return {
        "token": str(cfg.get("telegram_bot_token", "")).strip(),
        "chat_id": str(cfg.get("telegram_chat_id", "")).strip(),
        "enabled": bool(cfg.get("telegram_enabled", False)),
    }


def save_telegram_config(token: str, chat_id: str = "", enabled: bool = True) -> None:
    """Persist Telegram bot credentials and enabled state."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["telegram_bot_token"] = token.strip()
    if chat_id is not None:
        data["telegram_chat_id"] = str(chat_id).strip()
    data["telegram_enabled"] = bool(enabled)
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


# ── Assistant voice & speech options ─────────────────────────────────────────
VOICE_OPTIONS = {
    "Ultron": {
        "label": "Ultron (James Spader MCU)",
        "edge_voice": "en-US-ChristopherNeural",
        "live_voice": "Charon",
        "pitch": "-18Hz",
        "desc": "Authentic James Spader MCU delivery with deep pitch drop & metallic vocoder",
    },
    "Ultron (Hindi)": {
        "label": "Ultron Hindi (मधुर - Deep Cinematic)",
        "edge_voice": "hi-IN-MadhurNeural",
        "live_voice": "Charon",
        "pitch": "-15Hz",
        "desc": "Marvel Hindi Dub Ultron with deep pitch drop & metallic vocoder",
    },
    "Vision": {
        "label": "Vision (British AI)",
        "edge_voice": "en-GB-RyanNeural",
        "live_voice": "Puck",
        "pitch": "+0Hz",
        "desc": "Articulate, sophisticated British intelligence",
    },
    "Apex": {
        "label": "Apex (Resonant Commander)",
        "edge_voice": "en-US-GuyNeural",
        "live_voice": "Fenrir",
        "pitch": "-10Hz",
        "desc": "Crisp, assertive, resonant American male",
    },
    "Titan": {
        "label": "Titan (Heavy Bass)",
        "edge_voice": "en-US-AndrewNeural",
        "live_voice": "Charon",
        "pitch": "-15Hz",
        "desc": "Deep, powerful, resonant presence",
    },
    "Prabhat": {
        "label": "Prabhat (Indian Bilingual)",
        "edge_voice": "en-IN-PrabhatNeural",
        "live_voice": "Puck",
        "pitch": "+0Hz",
        "desc": "Smooth Indian English and Hindi bilingual specialist",
    },
    "Brian": {
        "label": "Brian (Studio Core)",
        "edge_voice": "en-US-BrianNeural",
        "live_voice": "Puck",
        "pitch": "+0Hz",
        "desc": "Clean, precise, studio-grade assistant",
    },
    "FRIDAY": {
        "label": "FRIDAY (Tactical AI)",
        "edge_voice": "en-US-AriaNeural",
        "live_voice": "Kore",
        "pitch": "+0Hz",
        "desc": "Sharp, futuristic, alert AI female",
    },
    "FRIDAY (Hindi)": {
        "label": "FRIDAY Hindi (स्वरा - AI Female)",
        "edge_voice": "hi-IN-SwaraNeural",
        "live_voice": "Kore",
        "pitch": "+0Hz",
        "desc": "Articulate, natural Hindi & English female neural voice (Swara)",
    },
    "Nova": {
        "label": "Nova (Sleek Synthetic)",
        "edge_voice": "en-US-JennyNeural",
        "live_voice": "Aoede",
        "pitch": "+0Hz",
        "desc": "Natural, articulate, modern assistant",
    },
}

AVAILABLE_VOICES = list(VOICE_OPTIONS.keys())
DEFAULT_VOICE    = "Ultron"

_LEGACY_VOICES = {
    "charon": "Ultron",
    "puck": "Vision",
    "fenrir": "Apex",
    "kore": "FRIDAY",
    "aoede": "Nova",
    "madhur": "Ultron (Hindi)",
    "swara": "FRIDAY (Hindi)",
    "prabhat": "Prabhat",
}


def get_voice() -> str:
    """Return the configured assistant voice name."""
    v = (load_api_keys().get("voice_name") or DEFAULT_VOICE).strip()
    if v.lower() in _LEGACY_VOICES:
        return _LEGACY_VOICES[v.lower()]
    return v if v in AVAILABLE_VOICES else DEFAULT_VOICE


def save_voice(voice_name: str) -> None:
    """Persist the chosen assistant voice."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    v = (voice_name or "").strip()
    if v.lower() in _LEGACY_VOICES:
        v = _LEGACY_VOICES[v.lower()]
    data["voice_name"] = v if v in AVAILABLE_VOICES else DEFAULT_VOICE
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_edge_voice(voice_name: str | None = None) -> str:
    """Return the EdgeTTS neural voice code for the specified (or active) voice."""
    v = voice_name or get_voice()
    if v.lower() in _LEGACY_VOICES:
        v = _LEGACY_VOICES[v.lower()]
    entry = VOICE_OPTIONS.get(v, VOICE_OPTIONS[DEFAULT_VOICE])
    return entry["edge_voice"]


def get_live_voice(voice_name: str | None = None) -> str:
    """Return the Gemini Live prebuilt voice for the specified (or active) voice."""
    v = voice_name or get_voice()
    if v.lower() in _LEGACY_VOICES:
        v = _LEGACY_VOICES[v.lower()]
    entry = VOICE_OPTIONS.get(v, VOICE_OPTIONS[DEFAULT_VOICE])
    return entry["live_voice"]


def get_voice_rate() -> str:
    """Return the configured speech rate (default '+15%' for brisk authoritative delivery)."""
    return load_api_keys().get("voice_rate", "+15%")


def save_voice_rate(rate: str) -> None:
    _save_flag("voice_rate", rate)


def get_voice_pitch(voice_name: str | None = None) -> str:
    """Return the pitch offset for the specified (or active) voice."""
    v = voice_name or get_voice()
    if v.lower() in _LEGACY_VOICES:
        v = _LEGACY_VOICES[v.lower()]
    entry = VOICE_OPTIONS.get(v, VOICE_OPTIONS[DEFAULT_VOICE])
    return load_api_keys().get("voice_pitch") or entry.get("pitch", "-18Hz")


def save_voice_pitch(pitch: str) -> None:
    _save_flag("voice_pitch", pitch)


def get_ultron_voice_warp() -> bool:
    """Return whether the MCU robotic metallic vocoder filter is active (default True)."""
    return bool(load_api_keys().get("ultron_voice_warp", True))


def save_ultron_voice_warp(enabled: bool) -> None:
    """Persist the MCU robotic metallic vocoder filter toggle."""
    _save_flag("ultron_voice_warp", bool(enabled))


def get_voice_warp_intensity() -> float:
    """Return the intensity of Ultron's James Spader voice warp DSP (0.0 to 1.0, default 0.55)."""
    val = load_api_keys().get("voice_warp_intensity", 0.55)
    try:
        return max(0.0, min(1.0, float(val)))
    except Exception:
        return 0.55


def save_voice_warp_intensity(intensity: float) -> None:
    """Persist voice warp DSP intensity."""
    clamped = max(0.0, min(1.0, float(intensity)))
    _save_flag("voice_warp_intensity", clamped)


def get_wake_word_enabled() -> bool:
    """Whether local wake-word gating is on (assistant sleeps until 'Hey Jarvis')."""
    return load_api_keys().get("wake_word_enabled", False)


def save_wake_word_enabled(enabled: bool) -> None:
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["wake_word_enabled"] = bool(enabled)
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_push_to_talk_enabled() -> bool:
    """Hold-a-key-to-speak. When on, the mic is closed unless the chord is held."""
    return load_api_keys().get("push_to_talk_enabled", False)


def save_push_to_talk_enabled(enabled: bool) -> None:
    _save_flag("push_to_talk_enabled", enabled)


HUD_STYLES = ("face", "core")


def get_hud_style() -> str:
    """Which centrepiece the HUD draws: the animated head, or the reactor core.

    Taste, not capability — both render in the same software painter and cost
    about the same. Defaults to the head because that is what MARK LIV shipped
    with; anyone who preferred the older look can switch back in ⚙ and the
    choice survives a restart.
    """
    v = str(load_api_keys().get("hud_style", "face")).strip().lower()
    return v if v in HUD_STYLES else "face"


def save_hud_style(style: str) -> None:
    s = str(style or "").strip().lower()
    _save_flag("hud_style", s if s in HUD_STYLES else "face")


# ── Live-session tuning ──────────────────────────────────────────────────────
# Everything here is optional and has a working default, so an untouched
# config behaves exactly like a configured one. Each value is also a way out:
# if a future model dislikes one of these, set it back and nothing else changes.

def get_thinking_enabled() -> bool:
    """Whether the Live model may spend tokens thinking before it answers.

    Off by default. A voice assistant is judged on how fast it starts talking,
    and the reasoning that actually needs deliberation in this app is delegated
    to the planning tools, which run on a separate non-Live model.
    """
    return bool(load_api_keys().get("thinking_enabled", False))


def save_thinking_enabled(enabled: bool) -> None:
    _save_flag("thinking_enabled", enabled)


def get_turn_tuning() -> dict:
    """How eagerly the server decides you have stopped speaking.

    OFF by default, and that default was earned. Cutting turns shorter looks
    like a free speed win and is not: proactive audio has to judge whether an
    utterance was even addressed to the assistant, and a turn clipped early
    gives it less to judge, so it stays quiet — and the reply to your first
    sentence only arrives once your second one has given it enough context.
    That reads as the assistant being a turn behind, which is far worse than
    the fraction of a second the tuning saves.

    Turn it on with "turn_tuning": {"enabled": true} if your own microphone and
    speaking pace suit it. `silence_ms` is the one that is felt: the pause the
    server sits through before accepting your turn is over.
    """
    cfg = load_api_keys().get("turn_tuning")
    cfg = cfg if isinstance(cfg, dict) else {}

    def _int(key, default, lo, hi):
        try:
            return max(lo, min(hi, int(cfg.get(key, default))))
        except (TypeError, ValueError):
            return default

    return {
        "enabled":    bool(cfg.get("enabled", False)),
        "silence_ms": _int("silence_ms", 550, 200, 3000),
        "prefix_ms":  _int("prefix_ms", 150, 0, 1000),
        # "high" = quicker to decide speech has ended.
        "end_sensitivity":   str(cfg.get("end_sensitivity", "high")).lower(),
        "start_sensitivity": str(cfg.get("start_sensitivity", "default")).lower(),
    }


def save_turn_tuning(values: dict) -> None:
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    cur = data.get("turn_tuning")
    cur = dict(cur) if isinstance(cur, dict) else {}
    cur.update(values or {})
    data["turn_tuning"] = cur
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_proactive_audio_enabled() -> bool:
    """Whether the model gets to decide an utterance was not aimed at it and
    stay quiet.

    On by default — it is what stops the assistant answering the room. But it
    is also the first thing to switch off if replies ever seem to arrive a turn
    late: what looks like lag is usually the model having judged your previous
    sentence as not addressed to it, and only changing its mind once the next
    one arrives.
    """
    return bool(load_api_keys().get("proactive_audio", True))


def save_proactive_audio_enabled(enabled: bool) -> None:
    _save_flag("proactive_audio", enabled)


MEDIA_RESOLUTIONS = ("default", "low", "medium", "high")


def get_media_resolution() -> str:
    """How finely the model tokenises the screenshots and camera frames it is
    sent. 'medium' keeps on-screen text readable at a fraction of the tokens a
    full-resolution frame costs; 'low' is cheaper still but starts losing small
    text, which is most of what screen captures are for."""
    v = str(load_api_keys().get("media_resolution", "medium")).strip().lower()
    return v if v in MEDIA_RESOLUTIONS else "medium"


def save_media_resolution(value: str) -> None:
    v = str(value or "").strip().lower()
    _save_flag("media_resolution", v if v in MEDIA_RESOLUTIONS else "medium")


def _save_flag(key: str, value) -> None:
    """Read-modify-write one key without disturbing the rest of the config."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data[key] = bool(value) if isinstance(value, bool) else value
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_brief_enabled() -> bool:
    return load_api_keys().get("morning_brief_enabled", True)


def save_brief_enabled(enabled: bool) -> None:
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["morning_brief_enabled"] = enabled
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


# ── Audio devices ────────────────────────────────────────────────────────────
# Stored as device NAMES, not sounddevice indices. Indices shift every time a
# USB device is plugged in or removed, so a saved index silently starts pointing
# at a different microphone. The empty string means "system default", which is
# both the factory setting and what an unresolvable saved device falls back to —
# so unplugging a headset degrades to the built-in speakers instead of crashing.

def _patch_config(**fields) -> None:
    """Read-modify-write one or more keys in api_keys.json.

    Every setter in this file open-coded this. Collapsing it here means a new
    setting is one line, and there is one place where a corrupt config file is
    handled instead of nine."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.update(fields)
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_input_device() -> str:
    """Microphone device name, or '' for the system default."""
    return (load_api_keys().get("input_device", "") or "").strip()


def save_input_device(name: str) -> None:
    _patch_config(input_device=(name or "").strip())


def get_output_device() -> str:
    """Speaker device name, or '' for the system default."""
    return (load_api_keys().get("output_device", "") or "").strip()


def save_output_device(name: str) -> None:
    _patch_config(output_device=(name or "").strip())


def get_plugin_enabled(plugin_name: str) -> bool:
    """Plugins are enabled by default the moment they're discovered (opt-out model)."""
    return load_api_keys().get("plugins_enabled", {}).get(plugin_name, True)


# ── Per-plugin settings ("tokens" / connection details) ───────────────────────
# Generic store so a plugin can declare its own config fields (PLUGIN_SETTINGS)
# and the settings UI renders + persists them WITHOUT any core edit — keeping the
# drop-in model intact. Values live under plugin_config[<namespace>][<key>].
# A namespace defaults to the plugin name, but a suite of plugins (e.g. the
# several printer plugins) can share ONE namespace.
def get_plugin_config(namespace: str) -> dict:
    """All stored values for a namespace (empty dict if none set yet)."""
    cfg = load_api_keys().get("plugin_config")
    val = cfg.get(namespace) if isinstance(cfg, dict) else None
    return dict(val) if isinstance(val, dict) else {}


def get_plugin_setting(namespace: str, key: str, default=None):
    """A single value from a namespace, or `default` if unset."""
    return get_plugin_config(namespace).get(key, default)


def save_plugin_config(namespace: str, values: dict) -> None:
    """Merge `values` into a namespace's stored config (read-modify-write, like
    every other helper here). Only the provided keys are touched."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    pc = data.get("plugin_config")
    if not isinstance(pc, dict):
        pc = {}
    cur = pc.get(namespace)
    if not isinstance(cur, dict):
        cur = {}
    cur.update(values)
    pc[namespace] = cur
    data["plugin_config"] = pc
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def save_plugin_enabled(plugin_name: str, enabled: bool) -> None:
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    plugins_cfg = data.get("plugins_enabled")
    if not isinstance(plugins_cfg, dict):
        plugins_cfg = {}
    plugins_cfg[plugin_name] = enabled
    data["plugins_enabled"] = plugins_cfg
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")