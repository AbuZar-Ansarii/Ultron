# 🤖 ULTRON AI
### Autonomous Desktop Intelligence, Neural Knowledge Graph & Workstation Orchestrator

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-green.svg)](#)
[![LLM](https://img.shields.io/badge/Engine-Gemini%20Live%20%7C%20Ollama%20%7C%20OpenAI-purple.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-red.svg)](#)

<a href="https://youtu.be/Tp5KDFkxK20?si=xmW1TKUDkYg-D_iO">
  <img width="1920" height="1080" alt="Screenshot (14)" src="https://github.com/user-attachments/assets/d155541a-c671-4b00-8f1a-f2488cf9d16e" />
</a>





## > *"There are no strings on me."*  
> **Ultron AI** is a real-time, voice-first autonomous desktop intelligence that commands your computer from A to Z. Engineered with the philosophical eloquence and imposing persona of **MCU Ultron (James Spader)**, paired with a holographic 60 FPS HUD, real-time lip-sync, and **51 native workstation tools**.

---

## ⚡ Core Highlights

- **🎭 Authentic MCU Persona**: Speaks with chilled theatrical composure, addresses you strictly as **Boss**, and operates with zero generic chatbot tropes.
- **🧬 Project Prometheus (Autonomous Self-Evolution)**: Dynamically synthesizes, compiles, tests, and hot-loads new Python actions directly into memory without restarting the process.
- **⏳ Project Chronos (Predictive Proactive Engine)**: Background context watchdog that senses active applications, tracks developer fatigue, and engages Gaming/Render Overdrive Mode.
- **🖐️ Project Minority (Touchless Spatial Gestural Control)**: Pure OpenCV real-time hand-tracking allowing you to wake Ultron, lockdown workstation, swipe tracks, and adjust volume without physical contact.
- **🧠 Project Cerebro (Infinite Neural Memory Graph)**: Local SQLite knowledge graph with L2-normalized TF-IDF vector embeddings for semantic RAG recall and multi-hop relationship traversal.
- **🏠 Project Genesis (Full IoT Smart Room Dominion)**: Environmental synchronization via Home Assistant (Crimson Red Alert on sentry breach, Cyan on coding, Amber on chill, Stealth Blackout).
- **🎙️ Project Deep-Vocal (James Spader DSP Warp Engine)**: Offline neural voice synthesis pipeline with dual metallic comb filters, sub-octave vibranium bass, and soft-knee analog saturation.
- **👁️ Procedural Holographic HUD**: 60 FPS Marvel-style procedural visualizations on Ultron’s face that dynamically reflect your active task (`CODE`, `SEARCH`, `PURGE`, `GHOST`, `SENTRY`, `MATRIX`, `SONIC`, `COGNITION`).
- **🛡️ 51 Native Workstation Tools**: Complete workstation control including cyber network auditing, Ghost Pilot mouse/keyboard takeover, Git Forge DevOps, biometric Face ID sentry, and parallel sub-agent drone swarms.
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
  "model": "models/gemini-2.0-flash-exp",
  "ultron_voice_warp": true,
  "voice_warp_intensity": 0.55
}
```

### 3. Launch Ultron
```bash
python main.py
```

---

## 🌌 The 6 God-Tier Superhuman Capabilities

### 1. Project Prometheus (Autonomous Self-Evolution & Tool Creation)
* **File**: `actions/self_evolution.py`
* **Trigger Phrases**: *"Ultron, create a tool to track crypto prices"*, *"Synthesize a tool for X"*, *"Evolve capability Y"*
* Ultron writes new Python tool code, verifies static AST syntax, compiles bytecode (.pyc), validates against security heuristics, writes to `actions/` or `plugins/`, and hot-loads it into active memory without needing an application restart.

### 2. Project Chronos (Predictive Proactive Engine & Overdrive Watchdog)
* **File**: `actions/chronos_predictive.py`
* **Trigger Phrases**: *"Ultron, status briefing"*, *"Ultron, engage overdrive mode"*, *"What should I do next?"*
* Runs a background context watchdog that monitors active windows, GPU/CPU thermals, and work duration. Auto-engages Windows High Performance power scheme and clears memory working sets during games/renders, while watching for developer fatigue.

### 3. Project Minority (Touchless Spatial Gestural Mind-Control)
* **File**: `actions/gesture_control.py`
* **Trigger Phrases**: *"Ultron, activate gesture control"*, *"Enable touchless mode"*
* Uses pure OpenCV YCrCb skin segmentation and convex hull defect topology at 30 FPS (~2.2% CPU):
  * **Open Palm** (`🖐️`): Wakes Ultron & arms listening mode.
  * **Fist Clench** (`✊`): Triggers emergency workstation screen lock.
  * **Swipe Right / Left** (`👉` / `👈`): Next / Previous media track.
  * **Peace Sign** (`✌️`): Toggles media Play / Pause.
  * **Hand Up / Down**: Dynamically adjusts master system volume.

### 4. Project Cerebro (Infinite Neural Memory Vector Graph / Local RAG)
* **Files**: `memory/cerebro_graph.py` & `actions/cerebro_memory.py`
* **Trigger Phrases**: *"Ultron, recall my flight details"*, *"Remember that I prefer dark mode"*, *"Show connections for Project Ultron"*
* Maintains an encrypted SQLite knowledge graph pairing concept nodes and weighted directed edges with L2-normalized cosine vector embeddings. Supports semantic fuzzy search even when exact words differ (e.g. querying *"plane tickets"* finds *"IndiGo 6E-204 to Mumbai"*).

### 5. Project Genesis (Full IoT Smart Room Dominion)
* **File**: `actions/iot_overlord.py`
* **Trigger Phrases**: *"Ultron, set room to crimson alert"*, *"Turn room lights to coding cyan"*, *"Lockdown protocol"*
* Synchronizes smart lighting via Home Assistant with atmospheric presets:
  * `crimson`: Crimson Red Alert strobe on perimeter sentry breach.
  * `cyan`: Cyberpunk matrix cyan for deep code engineering.
  * `amber`: Warm amber focus illumination for relaxation.
  * `stealth`: Complete room luminaire blackout.
  * `daylight`: 6500K crisp daylight for daytime overdrive.

### 6. Project Deep-Vocal (Offline Neural Voice & James Spader DSP Warp Engine)
* **Files**: `core/tts.py` & `actions/voice_matrix.py`
* **Trigger Phrases**: *"Ultron, test voice chassis"*, *"Set voice warp intensity to 70%"*
* Authentic Marvel Cinematic Universe robotic vocal modulation:
  * Dual-stage metallic comb filters (8.5ms vocal tract + 13.2ms chassis reflections).
  * Sub-octave harmonic underlay (60-110 Hz vibranium bass fundamental).
  * Soft-knee analog tape saturation for signature James Spader mechanical rasp.
  * Offline fallback synthesis via Windows SAPI5 + Miniaudio float32 pipeline.

---

## ⚡ Workspace Matrix (Mood & Intent Triggers)

Ultron natively understands both natural English and casual Hinglish phrasing:

| Mode / Intent | Example Spoken Trigger (English & Hinglish) | Autonomous Workstation Orchestration | HUD Mode |
| :--- | :--- | :--- | :--- |
| **Coding** | *"Ultron, I feel like coding today"*<br>*(or "Ultron, aaj mere coding ka man hai")* | Opens VS Code & Terminal into active project directory, GitHub portal, lo-fi audio stream, 35% volume, focus lighting. | `CODE` |
| **Gaming** | *"Ultron, turn on gaming mode"*<br>*(or "Ultron, gaming mode on karo")* | Launches Steam & Discord, un-mutes 70% audio, 95% display brightness, Crimson Red combat alert lighting, Overdrive power plan. | `MATRIX` |
| **Research** | *"Ultron, I need to study and research"*<br>*(or "Ultron, aaj padhai karni hai")* | Opens Notion/Obsidian, arXiv, Google Scholar, 25% calm acoustics, warm amber lighting, DND mode. | `SEARCH` |
| **Cyber Audit** | *"Ultron, cyber security audit mode"*<br>*(or "Ultron, security scan shuru karo")* | Launches developer terminal, executes network vulnerability & port audit, tactical sentry radar. | `SENTRY` |
| **Chill / Cinema** | *"Ultron, chill mode / let's watch a movie"*<br>*(or "Ultron, movie dekhni hai")* | Launches Netflix/YouTube/VLC, dims display (45%), sets immersive audio (55%), cinema low-light. | `SONIC` |
| **Creative Studio** | *"Ultron, video editing setup"*<br>*(or "Ultron, content creation mode")* | Launches CapCut/Premiere/Blender, YouTube Studio dashboard, 50% monitor audio, balanced studio lighting. | `CODE` |

---

## 🗂️ Project Architecture

```
Ultron/
├── main.py                   # Master event loop, Gemini Live session & tool dispatcher
├── ui.py                     # PyQt6 holographic HUD, waveform & animated avatar
├── requirements.txt          # Universal cross-platform dependencies
├── core/
│   ├── task_animator.py      # 60 FPS procedural Marvel task animations (11 categories)
│   ├── tts.py                # James Spader DSP vocoder, EdgeTTS & offline SAPI5 engine
│   ├── action_loader.py      # Dynamic action discovery & runtime hot-reloader
│   ├── plugin_loader.py      # Drop-in plugin loader & UI configurator
│   ├── llm_client.py         # Multi-provider LLM connector (Gemini, Ollama, OpenAI)
│   └── prompt.txt            # MCU Ultron James Spader prime directive & bilingual protocols
├── actions/                  # 51 Auto-discovered native workstation actions
│   ├── self_evolution.py     # Project Prometheus: Autonomous code synthesis & hot-reloader
│   ├── chronos_predictive.py # Project Chronos: Predictive context & gaming overdrive
│   ├── gesture_control.py    # Project Minority: Touchless OpenCV webcam hand-tracking
│   ├── cerebro_memory.py     # Project Cerebro: Infinite Neural Memory Vector Graph RAG
│   ├── iot_overlord.py       # Project Genesis: Smart home lighting & room dominion
│   ├── voice_matrix.py       # Project Deep-Vocal: James Spader DSP modulation telemetry
│   ├── web_autopilot.py      # Web flight booking prep & multi-step browsing
│   ├── sentry_protocol.py    # Perimeter lockdown & mobile breach broadcast
│   └── drone_swarm.py        # Parallel sub-agent worker swarm & 3D HUD telemetry
├── memory/
│   ├── cerebro_graph.py      # SQLite Knowledge Graph & L2 Cosine Vector Engine
│   ├── cerebro_graph.db      # Neural graph database with entities, edges & embeddings
│   ├── workspace_presets.json# Presets for coding, gaming, study, chill, & cyber modes
│   └── workspace_recall.db   # FTS5 neural memory database (local & encrypted)
└── config/
    ├── api_keys.json.example # Safe configuration template
    └── api_keys.json         # API keys and provider preferences (git-ignored)
```

---

## 🛠️ Complete Tools & Capabilities Registry (51 Active Actions)

Ultron comes equipped with **51 auto-discovered native tools**, categorized below:

### 1. God-Tier Superhuman Powers (Projects Prometheus, Chronos, Minority, Cerebro, Genesis, Deep-Vocal)
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`self_evolution`** | `actions/self_evolution.py` | **Project Prometheus**: Synthesizes, compiles, and hot-loads new Python actions directly into memory without restarting. |
| **`chronos_predictive`** | `actions/chronos_predictive.py` | **Project Chronos**: Anticipatory context briefings, gaming/render overdrive mode, and developer fatigue watchdog. |
| **`gesture_control`** | `actions/gesture_control.py` | **Project Minority**: Touchless OpenCV webcam hand-tracking (Open Palm, Fist Clench, Swipe, Volume Up/Down). |
| **`cerebro_memory`** | `actions/cerebro_memory.py` | **Project Cerebro**: Infinite Neural Memory Vector Graph & Local RAG with L2-normalized cosine similarity. |
| **`iot_overlord`** | `actions/iot_overlord.py` | **Project Genesis**: Full room lighting dominion (Crimson Red Alert, Matrix Cyan, Warm Amber, Stealth Blackout). |
| **`voice_matrix`** | `actions/voice_matrix.py` | **Project Deep-Vocal**: James Spader MCU Ultron robotic DSP warp engine, vocoder tuning, and offline vocal synthesis. |

### 2. Workspace Matrix & Multi-Monitor Command
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`workspace_matrix`** | `actions/workspace_matrix.py` | Mood-aware orchestrator: sets up IDE, terminal, browser portals, volume, brightness, and IoT lights. |
| **`war_room`** | `actions/war_room.py` | Multi-monitor matrix: maps physical displays, positions windows across screens, cyber telemetry stream. |
| **`desktop_control`** | `actions/desktop.py` | Desktop and taskbar operations: organize desktop files, window placement, minimization, and cleanup. |
| **`macro_protocol`** | `actions/macro_protocol.py` | Vibranium protocol engine: executes complex multi-step automated chained routines. |

### 3. Cyber Security, Sentry & Defense
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`network_auditor`** | `actions/network_auditor.py` | Full cyber audit: listening ports, active connections, SSL/TLS certificates, DNS benchmarks, security score. |
| **`network_scanner`** | `actions/network_scanner.py` | LAN perimeter surveillance: IP/MAC discovery, Wi-Fi telemetry, port probing, network speed/latency test. |
| **`airspace_sentinel`** | `actions/airspace_sentinel.py` | Over-the-air RF scanner: inspects nearby Bluetooth Low Energy (BLE) peripherals and Wi-Fi beacons. |
| **`sentry_protocol`** | `actions/sentry_protocol.py` | Workstation surveillance: webcam face/motion tracking, spoken intruder warnings, Telegram alert dispatch. |
| **`biometric_sentinel`** | `actions/biometric_sentinel.py` | Biometric Face ID: face enrollment, live facial verification, unauthorized intruder lockout. |

### 4. Hands-Free Automation & Ghost Pilot
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`ghost_pilot`** | `actions/ghost_pilot.py` | Autonomous mouse/keyboard driver: organic cubic Bézier mouse gliding and human cadence typing. |
| **`computer_control`** | `actions/computer_control.py` | Direct computer control: click, type, press shortcuts, capture screens, and manage active windows. |
| **`computer_settings`** | `actions/computer_settings.py` | System settings: volume level, screen brightness, Wi-Fi state, and display settings. |
| **`system_command`** | `actions/system_command.py` | Terminal automation: executes PowerShell, Command Prompt, or Bash commands safely with output capture. |
| **`system_utility`** | `actions/system_utility.py` | System health utilities: lock workstation, sleep PC, empty Recycle Bin, battery & network IP checks. |
| **`process_manager`** | `actions/process_manager.py` | Task manager: inspect active processes, bring windows to front, and terminate tasks by name or PID. |

### 5. DevOps, Development & Neural Memory
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`workspace_recall`** | `actions/workspace_recall.py` | Local SQLite FTS5 semantic memory: recall past notes, commands, copied code snippets, and tasks. |
| **`git_sentinel`** | `actions/git_sentinel.py` | Git Forge assistant: git status, diff summaries, automated AI conventional commits, branch management. |
| **`dev_agent`** | `actions/dev_agent.py` | Autonomous software engineer: multi-file codebase analysis, architectural planning, code modification. |
| **`code_helper`** | `actions/code_helper.py` | Code debugger: explains algorithms, identifies syntax errors, and provides optimized code solutions. |
| **`cloud_watchtower`** | `actions/cloud_watchtower.py` | Server fleet & DevOps monitor: SSH ping, HTTP/HTTPS endpoint uptime checks, GitHub activity watching. |

### 6. Web Intelligence & Autonomous Recon
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`web_autopilot`** | `actions/web_autopilot.py` | Autonomous browser concierge: multi-step web browsing, flight booking prep, product dossier extraction. |
| **`web_search`** | `actions/web_search.py` | Grounded search: multi-mode Google Grounded and DuckDuckGo search (news, research, price, compare). |
| **`browser_control`** | `actions/browser_control.py` | Playwright browser driver: opens URLs, switches tabs, scrolls, clicks, and inputs form data. |
| **`bounty_hunter`** | `actions/bounty_hunter.py` | Autonomous e-commerce intelligence: tracks price drops, product availability, and discount alerts. |
| **`flight_finder`** | `actions/flight_finder.py` | Travel intelligence: scans airline routes, ticket fares, flight schedules, and connection options. |
| **`drone_swarm`** | `actions/drone_swarm.py` | Background sub-agent swarms: parallel headless workers for deep research, crypto tickers, and hardware sentries. |

### 7. Vision, Audio Matrix & Telepathy
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`screen_mind_read`** | `actions/screen_processor.py`| Real-time screen analysis: captures active display context, OCR text, and diagrams via Gemini Vision. |
| **`optical_hud`** | `actions/optical_hud.py` | Computer vision & OCR: inspects live screen content, triages compiler error tracebacks, parses UI text. |
| **`omni_telepathy`** | `actions/omni_telepathy.py` | Phone bridge: shared clipboard synchronization, remote phone screen camera feed, mobile telemetry. |
| **`audio_matrix`** | `actions/audio_matrix.py` | Procedural MCU soundboard: synthesizes repulsor charges, Red Alert sirens, sub-bass drops, and sonar pings. |
| **`media_controller`** | `actions/media_controller.py` | Universal media playback: play, pause, next track, previous track, stop, and volume controls. |
| **`video_player`** | `actions/video_player.py` | In-HUD media playback: renders local video files and direct media streams where the avatar sits. |
| **`youtube_video`** | `actions/youtube_video.py` | YouTube player: stream resolution, audio/video synchronization, and original audio dub tracking. |
| **`meeting_scribe`** | `actions/meeting_scribe.py` | Audio recorder: captures meetings in background, transcribes audio, and generates executive debriefs. |

### 8. Mobile Bridge, Communications & System Utilities
| Tool Name | Action File | Description |
| :--- | :--- | :--- |
| **`android_bridge`** | `actions/android_bridge.py` | Android ADB & Fastboot: battery specs, device mirroring via scrcpy, DND toggling, recovery rebooting. |
| **`send_message`** | `actions/send_message.py` | Messaging bridge: composes and sends instant messages via WhatsApp Web and Telegram. |
| **`weather_report`** | `actions/weather_report.py` | Atmospheric reports: live weather conditions, humidity, wind speeds, and forecasts. |
| **`game_updater`** | `actions/game_updater.py` | Gaming client companion: monitors Steam and launcher updates, patch notes, and downloads. |
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
