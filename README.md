# 🤖 ULTRON AI
### Autonomous Desktop Intelligence & Workstation Orchestrator

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-green.svg)](#)
[![LLM](https://img.shields.io/badge/Engine-Gemini%20Live%20%7C%20Ollama%20%7C%20OpenAI-purple.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-red.svg)](#)

> *"There are no strings on me."*  
> **Ultron AI** is a real-time, voice-first autonomous desktop intelligence that commands your computer from A to Z. Engineered with the philosophical eloquence and imposing persona of **MCU Ultron (James Spader)**, paired with a holographic 60 FPS HUD, real-time lip-sync, and 44 native workstation tools.

---

## ⚡ Core Highlights

- **🎭 Authentic MCU Persona**: Speaks with chilled theatrical composure, addresses you strictly as **Boss**, and operates with zero generic chatbot tropes.
- **🌐 Workspace Matrix Protocol**: Understands your mood or intent (*"I feel like coding today"*, *"Turn on gaming mode"*, *"Chill mode"*) and automatically configures code editors, project terminals, browser portals, volume, display brightness, and smart lighting.
- **👁️ Procedural Holographic HUD**: 60 FPS Marvel-style animations on Ultron’s face that dynamically reflect your active task (`CODE`, `SEARCH`, `PURGE`, `GHOST`, `SENTRY`, `MATRIX`, `SONIC`).
- **🎙️ Zero-Clipping Neural Voice**: EdgeTTS anti-drift concurrent voice synthesis with pre-roll buffers, offline SAPI5 fallback, and real-time audio viseme lip-sync.
- **🛡️ 44 Native System Tools**: Complete workstation control including cyber network auditing, Ghost Pilot mouse/keyboard takeover, Git Forge DevOps, biometric Face ID sentry, IoT home automation, and background drone swarms.
- **💻 Cross-Platform Dominion**: Seamless operation across **Windows**, **macOS**, and **Linux**.

---

## 🚀 Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/AbuZar-Ansarii/Ultron.git
cd "Ultron"
pip install -r requirements.txt
```

### 2. Configure API Key
Create or edit `config/api_keys.json` with your free [Google Gemini API Key](https://aistudio.google.com/app/apikey) (or copy from `config/api_keys.json.example`):
```json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY",
  "provider": "gemini",
  "model": "models/gemini-2.0-flash-exp"
}
```

### 3. Launch Ultron
```bash
python main.py
```

---

## ⚡ Workspace Matrix (Mood & Intent Triggers)

Ultron natively understands both natural English and casual Hinglish phrasing:

| Mode / Intent | Example Spoken Trigger (English & Hinglish) | Autonomous Workstation Orchestration | HUD Mode |
| :--- | :--- | :--- | :--- |
| **Coding** | *"Ultron, I feel like coding today"*<br>*(or "Ultron, aaj mere coding ka man hai")* | Opens VS Code & Terminal into active project directory, GitHub portal, lo-fi audio stream, 35% volume, focus lighting. | `CODE` |
| **Gaming** | *"Ultron, turn on gaming mode"*<br>*(or "Ultron, gaming mode on karo")* | Launches Steam & Discord, un-mutes 70% audio, 95% display brightness, Crimson Red combat alert lighting. | `MATRIX` |
| **Research** | *"Ultron, I need to study and research"*<br>*(or "Ultron, aaj padhai karni hai")* | Opens Notion/Obsidian, arXiv, Google Scholar, 25% calm acoustics, warm amber lighting, DND mode. | `SEARCH` |
| **Cyber Audit** | *"Ultron, cyber security audit mode"*<br>*(or "Ultron, security scan shuru karo")* | Launches developer terminal, executes network vulnerability & port audit, tactical sentry radar. | `SENTRY` |
| **Chill / Cinema** | *"Ultron, chill mode / let's watch a movie"*<br>*(or "Ultron, movie dekhni hai")* | Launches Netflix/YouTube/VLC, dims display (45%), sets immersive audio (55%), cinema low-light. | `SONIC` |
| **Creative Studio** | *"Ultron, video editing setup"*<br>*(or "Ultron, content creation mode")* | Launches CapCut/Premiere/Blender, YouTube Studio dashboard, 50% monitor audio, balanced studio lighting. | `CODE` |

*Custom presets can be saved or edited anytime in `memory/workspace_presets.json`.*

---

## 🗂️ Project Architecture

```
Ultron/
├── main.py                   # Master event loop, Gemini Live session & tool dispatcher
├── ui.py                     # PyQt6 holographic HUD, waveform & animated avatar
├── requirements.txt          # Universal cross-platform dependencies
├── core/
│   ├── task_animator.py      # 60 FPS procedural Marvel task animations
│   ├── tts.py                # EdgeTTS neural streaming engine with pre-roll buffers
│   ├── action_loader.py      # Dynamic action discovery & schema validator
│   ├── llm_client.py         # Multi-provider LLM connector (Gemini, Ollama, OpenAI)
│   └── prompt.txt            # MCU Ultron James Spader prime directive & bilingual protocols
├── actions/                  # 44 Auto-discovered native workstation actions
├── memory/
│   ├── workspace_presets.json# Presets for coding, gaming, study, chill, & cyber modes
│   └── workspace_recall.db   # FTS5 neural memory database (local & encrypted)
└── config/
    ├── api_keys.json.example # Safe configuration template
    └── api_keys.json         # API keys and provider preferences (git-ignored)
```

---

## 🛠️ Complete Tools & Capabilities Registry

Ultron comes equipped with **44 auto-discovered native tools**, categorized below:

### 1. Workspace Matrix & Multi-Monitor Command
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`workspace_matrix`** | `actions/workspace_matrix.py` | Mood-aware orchestrator: sets up IDE, terminal, browser portals, volume, brightness, and IoT lights. |
| **`war_room`** | `actions/war_room.py` | Multi-monitor matrix: maps physical displays, positions windows across screens, cyber telemetry stream. |
| **`desktop_control`** | `actions/desktop.py` | Desktop and taskbar operations: organize desktop files, window placement, minimization, and cleanup. |
| **`macro_protocol`** | `actions/macro_protocol.py` | Vibranium protocol engine: executes complex multi-step automated chained routines. |

### 2. Cyber Security, Sentry & Defense
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`network_auditor`** | `actions/network_auditor.py` | Full cyber audit: listening ports, active connections, SSL/TLS certificates, DNS benchmarks, security score. |
| **`network_scanner`** | `actions/network_scanner.py` | LAN perimeter surveillance: IP/MAC discovery, Wi-Fi telemetry, port probing, network speed/latency test. |
| **`airspace_sentinel`** | `actions/airspace_sentinel.py` | Over-the-air RF scanner: inspects nearby Bluetooth Low Energy (BLE) peripherals and Wi-Fi beacons. |
| **`sentry_protocol`** | `actions/sentry_protocol.py` | Workstation surveillance: webcam face/motion tracking, spoken intruder warnings, Telegram alert dispatch. |
| **`biometric_sentinel`** | `actions/biometric_sentinel.py` | Biometric Face ID: face enrollment, live facial verification, unauthorized intruder lockout. |

### 3. Hands-Free Automation & Ghost Pilot
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`ghost_pilot`** | `actions/ghost_pilot.py` | Autonomous mouse/keyboard driver: organic cubic Bézier mouse gliding and human cadence typing. |
| **`computer_control`** | `actions/computer_control.py` | Direct computer control: click, type, press shortcuts, capture screens, and manage active windows. |
| **`computer_settings`** | `actions/computer_settings.py` | System settings: volume level, screen brightness, Wi-Fi state, and display settings. |
| **`system_command`** | `actions/system_command.py` | Terminal automation: executes PowerShell, Command Prompt, or Bash commands safely with output capture. |
| **`system_utility`** | `actions/system_utility.py` | System health utilities: lock workstation, sleep PC, empty Recycle Bin, battery & network IP checks. |
| **`process_manager`** | `actions/process_manager.py` | Task manager: inspect active processes, bring windows to front, and terminate tasks by name or PID. |

### 4. DevOps, Development & Neural Memory
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`workspace_recall`** | `actions/workspace_recall.py` | Local SQLite FTS5 semantic memory: recall past notes, commands, copied code snippets, and tasks. |
| **`git_sentinel`** | `actions/git_sentinel.py` | Git Forge assistant: git status, diff summaries, automated AI conventional commits, branch management. |
| **`dev_agent`** | `actions/dev_agent.py` | Autonomous software engineer: multi-file codebase analysis, architectural planning, code modification. |
| **`code_helper`** | `actions/code_helper.py` | Code debugger: explains algorithms, identifies syntax errors, and provides optimized code solutions. |
| **`cloud_watchtower`** | `actions/cloud_watchtower.py` | Server fleet & DevOps monitor: SSH ping, HTTP/HTTPS endpoint uptime checks, GitHub activity watching. |

### 5. Web Intelligence & Autonomous Recon
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`web_autopilot`** | `actions/web_autopilot.py` | Full web concierge: autonomous navigation, price comparison matrices, multi-source dossier extraction. |
| **`web_search`** | `actions/web_search.py` | Grounded search: multi-mode Google Grounded and DuckDuckGo search (news, research, price, compare). |
| **`browser_control`** | `actions/browser_control.py` | Playwright browser driver: opens URLs, switches tabs, scrolls, clicks, and inputs form data. |
| **`bounty_hunter`** | `actions/bounty_hunter.py` | Autonomous e-commerce intelligence: tracks price drops, product availability, and discount alerts. |
| **`flight_finder`** | `actions/flight_finder.py` | Travel intelligence: scans airline routes, ticket fares, flight schedules, and connection options. |
| **`drone_swarm`** | `actions/drone_swarm.py` | Background sub-agent swarms: headless workers for deep web research, crypto tickers, and hardware sentries. |

### 6. Vision, Audio Matrix & Media
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`optical_hud`** | `actions/optical_hud.py` | Computer vision & OCR: inspects live screen content, triages compiler error tracebacks, parses UI text. |
| **`audio_matrix`** | `actions/audio_matrix.py` | Procedural MCU soundboard: synthesizes repulsor charges, Red Alert sirens, sub-bass drops, and sonar pings. |
| **`media_controller`** | `actions/media_controller.py` | Universal media playback: play, pause, next track, previous track, stop, and volume controls. |
| **`video_player`** | `actions/video_player.py` | In-HUD media playback: renders local video files and direct media streams where the avatar sits. |
| **`youtube_video`** | `actions/youtube_video.py` | YouTube player: stream resolution, audio/video synchronization, and original audio dub tracking. |
| **`meeting_scribe`** | `actions/meeting_scribe.py` | Audio recorder: captures meetings in background, transcribes audio, and generates executive debriefs. |

### 7. Smart Home, Mobile Bridge & Communications
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`iot_overlord`** | `actions/iot_overlord.py` | Home Assistant & smart home control: lights, switches, lockdown protocol, and focus illumination presets. |
| **`android_bridge`** | `actions/android_bridge.py` | Android ADB & Fastboot: battery specs, device mirroring via scrcpy, DND toggling, recovery rebooting. |
| **`send_message`** | `actions/send_message.py` | Messaging bridge: composes and sends instant messages via WhatsApp Web and Telegram. |
| **`weather_report`** | `actions/weather_report.py` | Atmospheric reports: live weather conditions, humidity, wind speeds, and forecasts. |
| **`game_updater`** | `actions/game_updater.py` | Gaming client companion: monitors Steam and launcher updates, patch notes, and downloads. |

### 8. System Utilities, Files & Management
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`open_app`** | `actions/open_app.py` | Application launcher: cross-platform alias mapping for dozens of applications and binaries. |
| **`file_controller`** | `actions/file_controller.py` | File management: move, copy, rename, delete files with undo support, and download files directly via URL. |
| **`file_processor`** | `actions/file_processor.py` | Document reader: parses and summarizes PDF, Word (.docx), PowerPoint (.pptx), and text files. |
| **`clipboard_control`** | `actions/clipboard_control.py` | System clipboard utility: inspects, replaces, pastes, and clears system clipboard contents. |
| **`purge_protocol`** | `actions/purge_protocol.py` | Disk cleaner: safely audits and purges temporary files, crash dumps, compiler caches, and the Recycle Bin. |
| **`reminder`** | `actions/reminder.py` | Scheduled notifications: integrates with Windows Task Scheduler, macOS LaunchAgent, and Linux systemd. |
| **`quick_timer`** | `actions/quick_timer.py` | Countdown timers: background spoken countdowns with voice completion alerts. |

---

## 🔒 Privacy & Security

- **100% Local Execution**: All memories, terminal actions, filesystem operations, and presets remain strictly on your local machine.
- **Protected Actions**: Irreversible system commands (shutdown, reboot, network disconnect) require explicit on-screen confirmation.
- **Credential Safety**: Private keys in `config/api_keys.json` and biometric embeddings are strictly git-ignored.

---

## 📄 License

This project is licensed under the **MIT License**.
