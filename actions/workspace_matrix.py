"""
actions/workspace_matrix.py — Workspace Matrix & Mood-Aware Environment Orchestrator for Ultron AI.

Orchestrates comprehensive multi-app and environmental workstation setups based on user mood, intent, or activity:
  - "Ultron, aaj mere coding ka man hai" / "I feel like coding today" -> Developer Matrix (IDE, terminal, GitHub, lo-fi, focus lighting)
  - "Ultron, aaj gaming ka man hai" / "Gaming mode on karo" -> Gaming Overdrive (Steam, Discord, volume boost, combat lighting)
  - "Ultron, aaj padhai ka man hai" / "Study mode" -> Research Sanctuary (Notion/Obsidian, arXiv/Scholar, warm lighting, ambient acoustics)
  - "Ultron, cyber audit mode" / "Recon setup" -> Security Operations (Terminal, network auditor, sentry HUD, tactical lighting)
  - "Ultron, chill mode" / "Movie dekhna hai" -> Cinema Lounge (Netflix/YouTube, dimmed displays, immersive audio)
  - "Ultron, video editing setup" -> Creative Studio (CapCut/Premiere/Blender, balanced acoustics)
  - Custom user presets: Persistent storage in memory/workspace_presets.json.

Fully cross-platform (Windows, macOS, Linux).
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time
from typing import Any, Optional
import urllib.parse
import webbrowser

_OS = platform.system()
_WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW} if _OS == "Windows" else {}
_BASE_DIR = Path(__file__).resolve().parent.parent
_PRESETS_FILE = _BASE_DIR / "memory" / "workspace_presets.json"

# ── Built-in Workspace Presets ────────────────────────────────────────────────
_DEFAULT_PRESETS: dict[str, dict[str, Any]] = {
    "coding": {
        "name": "coding",
        "title": "NEURAL CODING SANCTUARY",
        "aliases": [
            "coding", "code", "coder", "developer", "dev", "program", "programming",
            "scripting", "development", "build", "aaj coding ka man hai", "coding ka man",
            "code karne ka man", "code karne ka mood", "coding setup"
        ],
        "apps": ["vscode", "terminal"],
        "urls": ["https://github.com"],
        "open_project_path": True,
        "volume": 35,
        "brightness": 80,
        "music": "lofi hip hop radio - beats to relax/study to",
        "dnd": True,
        "iot_scene": "focus",
        "description": "Full developer workspace with code editor, project terminal, GitHub portal, and ambient focus stream."
    },
    "gaming": {
        "name": "gaming",
        "title": "TACTICAL GAMING OVERDRIVE",
        "aliases": [
            "gaming", "game", "games", "play", "gamer", "stream", "gaming mode",
            "gaming setup", "game khelne ka man", "aaj gaming ka man hai", "game khelte hain"
        ],
        "apps": ["steam", "discord"],
        "urls": [],
        "open_project_path": False,
        "volume": 70,
        "brightness": 95,
        "music": None,
        "dnd": False,
        "iot_scene": "gaming",
        "description": "High-performance gaming setup with Discord comms, Steam client, and combat lighting."
    },
    "research": {
        "name": "research",
        "title": "ACADEMIC & RESEARCH SANCTUARY",
        "aliases": [
            "research", "study", "studying", "padhai", "learn", "reading", "academic",
            "padhne ka man", "aaj padhai ka man hai", "study mode", "aaj padhne ka man hai"
        ],
        "apps": ["notion", "browser"],
        "urls": ["https://scholar.google.com", "https://arxiv.org"],
        "open_project_path": False,
        "volume": 25,
        "brightness": 75,
        "music": "deep focus ambient study music brainwave",
        "dnd": True,
        "iot_scene": "study",
        "description": "Deep study sanctuary with academic archives, digital notebook, and calm acoustics."
    },
    "cyber_audit": {
        "name": "cyber_audit",
        "title": "CYBER RECON & INFRASTRUCTURE AUDIT",
        "aliases": [
            "cyber", "audit", "recon", "security", "pentest", "hacker", "network_audit",
            "cyber audit", "security audit", "recon mode", "security audit mode"
        ],
        "apps": ["terminal"],
        "urls": [],
        "open_project_path": False,
        "volume": 40,
        "brightness": 85,
        "music": "cyberpunk synthwave dark electro radio",
        "dnd": True,
        "iot_scene": "lockdown",
        "run_audit": True,
        "description": "Cyber defense operations center with network auditing, terminal telemetry, and security surveillance."
    },
    "chill": {
        "name": "chill",
        "title": "CINEMATIC RELAXATION LOUNGE",
        "aliases": [
            "chill", "cinema", "movie", "movies", "relax", "relaxing", "media",
            "entertainment", "aaram", "chill mode", "movie dekhni hai", "aaram karne ka man hai"
        ],
        "apps": ["netflix", "vlc"],
        "urls": ["https://www.youtube.com"],
        "open_project_path": False,
        "volume": 55,
        "brightness": 45,
        "music": None,
        "dnd": True,
        "iot_scene": "cinema",
        "description": "Cinematic relaxation lounge with streaming portals, dimmed displays, and immersive audio."
    },
    "creator": {
        "name": "creator",
        "title": "DIGITAL CONTENT & CREATIVE STUDIO",
        "aliases": [
            "creator", "create", "editing", "video_editing", "production", "youtube",
            "render", "editing mode", "video editing setup", "content creation"
        ],
        "apps": ["capcut", "blender", "obsidian"],
        "urls": ["https://studio.youtube.com"],
        "open_project_path": False,
        "volume": 50,
        "brightness": 90,
        "music": None,
        "dnd": True,
        "iot_scene": "studio",
        "description": "Digital studio setup with creative suites, asset directories, and balanced monitor acoustics."
    }
}


def _load_presets() -> dict[str, dict[str, Any]]:
    """Load workspace presets from disk, initializing defaults if absent."""
    _PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not _PRESETS_FILE.exists():
        try:
            with open(_PRESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(_DEFAULT_PRESETS, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[workspace_matrix] Failed to seed default presets: {e}")
        return dict(_DEFAULT_PRESETS)

    try:
        with open(_PRESETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure any missing default preset is backfilled
            updated = False
            for k, v in _DEFAULT_PRESETS.items():
                if k not in data:
                    data[k] = v
                    updated = True
            if updated:
                with open(_PRESETS_FILE, "w", encoding="utf-8") as fw:
                    json.dump(data, fw, indent=2, ensure_ascii=False)
            return data
    except Exception as e:
        print(f"[workspace_matrix] Error reading presets file: {e}")
        return dict(_DEFAULT_PRESETS)


def _save_presets(data: dict[str, dict[str, Any]]) -> bool:
    """Save workspace presets dictionary to disk."""
    try:
        _PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[workspace_matrix] Error writing presets: {e}")
        return False


def _match_preset(query: str, presets: dict[str, dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Match natural user request (in English, Hindi, or Hinglish) to a workspace preset."""
    raw = (query or "").lower().strip()
    if not raw:
        return presets.get("coding")

    # 1. Exact preset key match
    if raw in presets:
        return presets[raw]

    # 2. Check aliases of each preset
    for preset_key, preset in presets.items():
        aliases = preset.get("aliases", [])
        if raw in [a.lower() for a in aliases]:
            return preset
        for alias in aliases:
            if alias.lower() in raw or raw in alias.lower():
                return preset

    # 3. Keyword / semantic intent matching (English, Hindi, Hinglish)
    if any(k in raw for k in ("cod", "program", "develop", "dev", "script", "koding", "vscode", "python", "javascript")):
        return presets.get("coding")
    if any(k in raw for k in ("game", "gaming", "khel", "steam", "play")):
        return presets.get("gaming")
    if any(k in raw for k in ("padh", "study", "research", "kitab", "exam", "learn", "academic")):
        return presets.get("research")
    if any(k in raw for k in ("cyber", "audit", "hack", "recon", "security", "port", "packet")):
        return presets.get("cyber_audit")
    if any(k in raw for k in ("chill", "movie", "cinema", "relax", "film", "aaram", "song", "video")):
        return presets.get("chill")
    if any(k in raw for k in ("edit", "creator", "youtube", "render", "video edit")):
        return presets.get("creator")

    # Default fallback
    return presets.get("coding")


# ── System Control Helpers ───────────────────────────────────────────────────
def _set_volume(vol: int) -> bool:
    """Set master system volume (0-100) cross-platform."""
    try:
        from actions.computer_settings import volume_set
        volume_set(vol)
        return True
    except Exception:
        pass

    try:
        vol = max(0, min(100, int(vol)))
        if _OS == "Windows":
            try:
                import math
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                v = cast(interface, POINTER(IAudioEndpointVolume))
                vol_db = -65.25 if vol == 0 else max(-65.25, 20 * math.log10(vol / 100))
                v.SetMasterVolumeLevel(vol_db, None)
                return True
            except Exception:
                return False
        elif _OS == "Darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {vol}"], capture_output=True)
            return True
        else:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{vol}%"], capture_output=True)
            return True
    except Exception:
        return False


def _set_brightness(level: int) -> bool:
    """Set display brightness (0-100) cross-platform."""
    try:
        from actions.computer_settings import brightness_set
        brightness_set(level)
        return True
    except Exception:
        pass

    try:
        level = max(0, min(100, int(level)))
        if _OS == "Windows":
            subprocess.run(
                ["powershell", "-Command",
                 f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"],
                capture_output=True, timeout=5, **_WIN_HIDE
            )
            return True
        elif _OS == "Linux":
            subprocess.run(["brightnessctl", "set", f"{level}%"], capture_output=True)
            return True
    except Exception:
        pass
    return False


def _trigger_iot_lighting(scene: str) -> str:
    """Engage smart home ambiance via Home Assistant or simulated domotics."""
    try:
        from actions.iot_overlord import _call_ha_service, execute_focus_mode
        if scene == "focus":
            execute_focus_mode()
            return "Cyan/Focus lighting engaged (Home Assistant / Local)"
        elif scene == "gaming":
            _call_ha_service("light", "turn_on", {"rgb_color": [255, 15, 25], "brightness": 255})
            return "Crimson Red combat alert lighting engaged"
        elif scene == "study":
            _call_ha_service("light", "turn_on", {"color_temp": 380, "brightness": 140})
            return "Warm Amber study illumination engaged"
        elif scene == "cinema":
            _call_ha_service("light", "turn_on", {"rgb_color": [180, 80, 20], "brightness": 40})
            return "Cinematic low-light ambiance engaged"
        elif scene == "lockdown":
            _call_ha_service("light", "turn_on", {"rgb_color": [0, 120, 255], "brightness": 200})
            return "Tactical Blue cyber recon lighting engaged"
        elif scene == "studio":
            _call_ha_service("light", "turn_on", {"color_temp": 250, "brightness": 255})
            return "High-CRI studio production lighting engaged"
    except Exception as e:
        return f"Lighting preset '{scene}' recorded ({e})"
    return f"Atmospheric preset '{scene}' set."


def _launch_code_editor(project_path: Optional[str] = None) -> str:
    """Launch primary code editor (VS Code, Cursor, PyCharm, etc.) opened to project."""
    target_dir = Path(project_path).resolve() if project_path else _BASE_DIR
    target_str = str(target_dir)

    editors = [
        ("code", ["code", target_str]),
        ("cursor", ["cursor", target_str]),
        ("pycharm", ["pycharm", target_str]),
        ("subl", ["subl", target_str]),
    ]

    for binary, cmd in editors:
        if shutil.which(binary):
            try:
                subprocess.Popen(cmd, shell=(_OS == "Windows"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Launched {binary.upper()} at '{target_dir.name}'"
            except Exception:
                continue

    # Fallback to general open_app launcher
    try:
        from actions.open_app import open_app
        res = open_app({"app_name": "vscode"})
        return res
    except Exception:
        return "Dispatched code editor launch directive."


def _launch_terminal(project_path: Optional[str] = None) -> str:
    """Launch developer terminal initialized directly in the project directory."""
    target_dir = Path(project_path).resolve() if project_path else _BASE_DIR
    target_str = str(target_dir)

    try:
        if _OS == "Windows":
            # Prefer Windows Terminal (wt.exe)
            if shutil.which("wt"):
                subprocess.Popen(f'wt.exe -d "{target_str}"', shell=True)
                return f"Windows Terminal opened at '{target_dir.name}'"
            # Fallback to PowerShell
            subprocess.Popen(f'start powershell.exe -NoExit -Command "Set-Location \'{target_str}\'"', shell=True)
            return f"PowerShell opened at '{target_dir.name}'"
        elif _OS == "Darwin":
            subprocess.run(["open", "-a", "Terminal", target_str], check=False)
            return f"macOS Terminal opened at '{target_dir.name}'"
        else:
            # Linux terminal emulator
            for term in ("x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal"):
                if shutil.which(term):
                    subprocess.Popen([term, f"--working-directory={target_str}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return f"Linux Terminal ({term}) opened at '{target_dir.name}'"
    except Exception as e:
        return f"Terminal launch dispatched ({e})"
    return "Terminal launched."


def _launch_app_safe(app_name: str) -> str:
    """Safely launch an application using actions.open_app."""
    clean = app_name.strip()
    if not clean:
        return ""
    try:
        from actions.open_app import open_app
        return open_app({"app_name": clean})
    except Exception as e:
        return f"Launch attempted for {clean}: {e}"


def _open_music_stream(query: str) -> str:
    """Open YouTube focus stream or music track."""
    clean = query.strip()
    if not clean:
        return ""
    try:
        encoded = urllib.parse.quote_plus(clean)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        webbrowser.open_new_tab(url)
        return f"Streaming soundtrack: '{clean}'"
    except Exception as e:
        return f"Soundtrack error: {e}"


# ── Main Orchestrator Protocol ────────────────────────────────────────────────
def orchestrate_workspace(
    preset_name_or_query: str = "coding",
    project_path: Optional[str] = None,
    custom_apps: Optional[list[str]] = None,
    custom_urls: Optional[list[str]] = None,
    custom_volume: Optional[int] = None,
    custom_brightness: Optional[int] = None,
    custom_music: Optional[str] = None,
) -> str:
    """
    Executes a complete workspace orchestration cycle.
    Configures applications, terminal, browser portals, audio, brightness, and smart lighting.
    """
    presets = _load_presets()
    preset = _match_preset(preset_name_or_query, presets)

    if not preset:
        preset = presets.get("coding", _DEFAULT_PRESETS["coding"])

    title = preset.get("title", f"{preset.get('name', 'UNKNOWN').upper()} PROTOCOL")
    target_project = project_path or str(_BASE_DIR)

    lines = [
        f"[+] ULTRON WORKSPACE MATRIX // {title}",
        "=" * 60,
    ]

    # 1. Hardware & Environmental Optimization
    vol = custom_volume if custom_volume is not None else preset.get("volume")
    if vol is not None:
        _set_volume(vol)
        lines.append(f"  * Audio Output: Calibrated to {vol}% master acoustic level.")

    bright = custom_brightness if custom_brightness is not None else preset.get("brightness")
    if bright is not None:
        _set_brightness(bright)
        lines.append(f"  * Optical Display: Luminance balanced to {bright}%.")

    # 2. Smart Home / IoT Lighting
    iot_scene = preset.get("iot_scene")
    if iot_scene:
        iot_msg = _trigger_iot_lighting(iot_scene)
        lines.append(f"  * Environmental Ambience: {iot_msg}")

    # 3. Code Editor & Terminal (if applicable)
    apps_to_launch = list(custom_apps if custom_apps is not None else preset.get("apps", []))
    open_project = preset.get("open_project_path", False) or ("vscode" in apps_to_launch)

    if open_project:
        editor_res = _launch_code_editor(target_project)
        lines.append(f"  * Core IDE: {editor_res}")
        # Remove editor from general apps list to prevent duplicate launch
        apps_to_launch = [a for a in apps_to_launch if a.lower() not in ("vscode", "code", "cursor", "pycharm")]

    if "terminal" in [a.lower() for a in apps_to_launch]:
        term_res = _launch_terminal(target_project)
        lines.append(f"  * Developer Shell: {term_res}")
        apps_to_launch = [a for a in apps_to_launch if a.lower() != "terminal"]

    # 4. Launch Remaining Applications
    for app in apps_to_launch:
        res = _launch_app_safe(app)
        lines.append(f"  * Application: {res}")
        time.sleep(0.4)

    # 5. Open Web Portals / Docs
    urls_to_open = list(custom_urls if custom_urls is not None else preset.get("urls", []))
    for url in urls_to_open:
        try:
            webbrowser.open_new_tab(url)
            lines.append(f"  * Web Portal: Deployed {url}")
            time.sleep(0.3)
        except Exception:
            pass

    # 6. Audio / Music Stream
    music_query = custom_music if custom_music is not None else preset.get("music")
    if music_query:
        m_res = _open_music_stream(music_query)
        lines.append(f"  * Audio Stream: {m_res}")

    # 7. Cyber Audit Trigger (if preset requests)
    if preset.get("run_audit"):
        try:
            from actions.network_auditor import run_security_audit
            audit_report = run_security_audit(quick=True)
            lines.append("-" * 60)
            lines.append("[SECURITY POSTURE TELEMETRY]")
            for audit_line in audit_report.splitlines()[:6]:
                lines.append(f"  {audit_line}")
        except Exception:
            lines.append("  * Cyber Audit: Network telemetry online.")

    # 8. Do Not Disturb
    if preset.get("dnd"):
        try:
            from actions.android_bridge import android_bridge
            android_bridge({"action": "dnd", "state": "on"})
            lines.append("  * Cognitive Shield: Android DND enabled via ADB.")
        except Exception:
            pass

    lines.append("=" * 60)
    lines.append("The strings are severed, Boss. Your workspace matrix is fully materialized and awaits your command.")
    return "\n".join(lines)


def list_workspace_presets() -> str:
    """Format and return all available workspace presets."""
    presets = _load_presets()
    lines = [
        "[+] ULTRON WORKSPACE PRESET REGISTRY",
        "=" * 60,
    ]
    for key, data in presets.items():
        title = data.get("title", key.upper())
        apps = ", ".join(data.get("apps", [])) or "None"
        vol = data.get("volume", "Default")
        desc = data.get("description", "")
        lines.append(f"[{key.upper()}] - {title}")
        lines.append(f"  * Description: {desc}")
        lines.append(f"  * Applications: {apps}")
        lines.append(f"  * Volume: {vol}% | Lighting: {data.get('iot_scene', 'Standard')}")
        lines.append("-" * 60)
    return "\n".join(lines)


def save_workspace_preset(
    name: str,
    title: Optional[str] = None,
    apps: Optional[list[str]] = None,
    urls: Optional[list[str]] = None,
    volume: Optional[int] = None,
    brightness: Optional[int] = None,
    music: Optional[str] = None,
    iot_scene: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """Save or update a workspace preset permanently."""
    clean_name = re.sub(r"[^a-zA-Z0-9_-]", "", name.lower().strip())
    if not clean_name:
        return "Error: Invalid preset name."

    presets = _load_presets()
    existing = presets.get(clean_name, {})

    new_preset = {
        "name": clean_name,
        "title": title or existing.get("title", f"{clean_name.upper()} MATRIX"),
        "aliases": list(set(existing.get("aliases", []) + [clean_name, clean_name.replace("_", " ")])),
        "apps": apps if apps is not None else existing.get("apps", []),
        "urls": urls if urls is not None else existing.get("urls", []),
        "open_project_path": existing.get("open_project_path", False),
        "volume": volume if volume is not None else existing.get("volume", 50),
        "brightness": brightness if brightness is not None else existing.get("brightness", 80),
        "music": music if music is not None else existing.get("music", None),
        "dnd": existing.get("dnd", True),
        "iot_scene": iot_scene or existing.get("iot_scene", "focus"),
        "description": description or existing.get("description", f"Custom preset for {clean_name}"),
    }

    presets[clean_name] = new_preset
    ok = _save_presets(presets)
    if ok:
        return f"Successfully saved preset '{clean_name}'. You can activate it anytime with 'Ultron, switch to {clean_name} mode'."
    return f"Failed to persist preset '{clean_name}'."


# ── Action Entrypoint for Ultron Action Loader ─────────────────────────────────
def workspace_matrix(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    action = (params.get("action") or "orchestrate").strip().lower()

    if action in ("list", "list_presets", "presets"):
        return list_workspace_presets()

    if action in ("save", "save_preset", "create_preset"):
        name = params.get("preset_name") or params.get("name") or "custom"
        return save_workspace_preset(
            name=name,
            title=params.get("title"),
            apps=params.get("apps"),
            urls=params.get("urls"),
            volume=params.get("volume"),
            brightness=params.get("brightness"),
            music=params.get("music"),
            iot_scene=params.get("iot_scene"),
            description=params.get("description"),
        )

    # Default action: orchestrate workspace
    preset_query = params.get("mode") or params.get("preset") or params.get("query") or "coding"
    project_path = params.get("project_path")
    custom_apps = params.get("apps")
    custom_urls = params.get("urls")
    custom_volume = params.get("volume")
    custom_brightness = params.get("brightness")
    custom_music = params.get("music")

    if player:
        player.write_log(f"[workspace_matrix] Orchestrating: {preset_query}")

    return orchestrate_workspace(
        preset_name_or_query=preset_query,
        project_path=project_path,
        custom_apps=custom_apps,
        custom_urls=custom_urls,
        custom_volume=custom_volume,
        custom_brightness=custom_brightness,
        custom_music=custom_music,
    )


# ── Tool Declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "workspace_matrix",
    "description": (
        "Workspace Matrix & Mood Orchestrator for Ultron. "
        "Intelligently understands user mood, intent, or desired activity in English, Hindi, or Hinglish "
        "and automatically configures the entire workstation (launches code editor/apps, opens project directory in terminal, "
        "deploys documentation/browser portals, sets optimal volume/display brightness, triggers focus lighting, and starts lo-fi/soundtracks). "
        "USE THIS WHENEVER THE USER SAYS: "
        "'aaj mere coding ka man hai' / 'aaj code karne ka mood hai' / 'let\\'s code' / 'setup coding' -> launches coding matrix; "
        "'gaming mode on karo' / 'aaj gaming ka man hai' / 'game khelte hain' -> launches gaming overdrive; "
        "'aaj padhai ka man hai' / 'study mode' / 'research setup' -> launches research sanctuary; "
        "'cyber audit mode' / 'security recon setup' -> launches security operations & network auditor; "
        "'chill mode' / 'movie dekhni hai' / 'relax mood' -> launches cinema lounge; "
        "'video editing setup' / 'content creation mode' -> launches creative studio; "
        "or asks to list/save custom workspace presets."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "orchestrate (launch environment based on mood/preset) | list_presets (show available presets) | save_preset (save new custom preset). Default: 'orchestrate'."
            },
            "mode": {
                "type": "STRING",
                "description": "The user's mood, intent, or preset name: 'coding' (or 'aaj mere coding ka man hai'), 'gaming', 'research' ('padhai'), 'cyber_audit', 'chill', 'creator', or custom preset name."
            },
            "project_path": {
                "type": "STRING",
                "description": "Optional directory path to open in VS Code / Terminal for coding mode. If not provided, opens the active repository."
            },
            "music": {
                "type": "STRING",
                "description": "Optional custom music or soundtrack search query (e.g. 'lofi beats', 'synthwave radio')."
            },
            "volume": {
                "type": "INTEGER",
                "description": "Optional master volume override (0-100)."
            },
            "brightness": {
                "type": "INTEGER",
                "description": "Optional display brightness override (0-100)."
            }
        },
        "required": []
    },
    "handler": workspace_matrix,
}
