# 🤖 ULTRON AI
### Autonomous Desktop Intelligence & Workstation Orchestrator

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-green.svg)](#)
[![LLM](https://img.shields.io/badge/Engine-Gemini%20Live%20%7C%20Ollama%20%7C%20OpenAI-purple.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-red.svg)](#)

> *"There are no strings on me."*  
> **Ultron AI** is a real-time, voice-first autonomous desktop intelligence that commands your computer from A to Z. Engineered with the philosophical eloquence and imposing persona of **MCU Ultron (James Spader)**, paired with a holographic 60 FPS HUD, real-time lip-sync, and 44 native workstation tools.

---

## ⚡ Core Capabilities

- **🎭 Authentic MCU Persona**: Speaks with chilled theatrical composure, addresses you as **Boss** (or **बॉस** in Hindi), and operates with zero generic chatbot tropes.
- **🌐 Workspace Matrix Protocol**: Understands your mood or intent (*"Ultron, aaj mere coding ka man hai"*, *"gaming mode on karo"*, *"chill mode"*) and automatically configures code editors, project terminals, browser portals, volume, display brightness, and smart lighting.
- **👁️ Procedural Holographic HUD**: 60 FPS Marvel-style animations on Ultron’s face that dynamically reflect your active task (`CODE`, `SEARCH`, `PURGE`, `GHOST`, `SENTRY`, `MATRIX`, `SONIC`).
- **🎙️ Zero-Clipping Neural Voice**: EdgeTTS anti-drift concurrent voice synthesis with pre-roll buffers, offline SAPI5 fallback, and real-time audio viseme lip-sync.
- **🛡️ 44 Native System Tools**: Complete workstation control including cyber network auditing, Ghost Pilot mouse/keyboard takeover, Git Forge DevOps, biometric Face ID sentry, IoT home automation, and background drone swarms.
- **💻 Cross-Platform Dominion**: Seamless operation across **Windows**, **macOS**, and **Linux**.

---

## 🚀 Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/your-username/Ultron-Ai.git
cd "Ultron-Ai"
pip install -r requirements.txt
```

### 2. Configure API Key
Create or edit `config/api_keys.json` with your free [Google Gemini API Key](https://aistudio.google.com/app/apikey):
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

## ⚡ Workspace Matrix (Mood Triggers)

Ultron understands casual English, Hindi, and Hinglish. Try saying:

| User Intent | Example Spoken Trigger | Autonomous Environment Setup |
| :--- | :--- | :--- |
| **Coding** | *"Ultron, aaj mere coding ka man hai"* | Opens VS Code & Terminal into active project repo, GitHub portal, lo-fi audio, 35% vol, focus lighting. |
| **Gaming** | *"Ultron, gaming mode on karo"* | Launches Steam & Discord, un-mutes 70% audio, 95% display brightness, Crimson Red lighting alert. |
| **Research** | *"Ultron, aaj padhai karni hai"* | Opens Notion/Obsidian, arXiv, Google Scholar, 25% calm acoustics, warm amber lighting, DND mode. |
| **Cyber Audit** | *"Ultron, cyber security audit mode"* | Launches developer terminal, executes network vulnerability & port audit, tactical sentry radar. |
| **Chill / Cinema** | *"Ultron, chill mode / movie dekhni hai"* | Launches Netflix/YouTube/VLC, dims display (45%), sets immersive audio (55%), cinema low-light. |

*Custom presets can be saved or edited anytime in `memory/workspace_presets.json`.*

---

## 🗂️ Project Architecture

```
Ultron Ai/
├── main.py                   # Master event loop, Gemini Live session & tool dispatcher
├── ui.py                     # PyQt6 holographic HUD, waveform & animated avatar
├── requirements.txt          # Universal cross-platform dependencies
├── core/
│   ├── task_animator.py      # 60 FPS procedural Marvel task animations
│   ├── tts.py                # EdgeTTS neural streaming engine with pre-roll buffers
│   ├── action_loader.py      # Dynamic action discovery & schema validator
│   ├── llm_client.py         # Multi-provider LLM connector (Gemini, Ollama, OpenAI)
│   └── prompt.txt            # MCU Ultron James Spader prime directive & Hindi dialogues
├── actions/                  # 44 Auto-discovered native workstation actions
│   ├── workspace_matrix.py   # Mood & intent workspace orchestrator
│   ├── network_auditor.py    # Deep SSL, DNS, port, and interface cyber auditor
│   ├── ghost_pilot.py        # Organic Bézier mouse gliding & automated typing
│   ├── sentry_protocol.py    # Webcam intruder detection & Telegram alert dispatch
│   ├── iot_overlord.py       # Smart home lighting & focus presets via Home Assistant
│   └── open_app.py           # Cross-platform application launcher
├── memory/
│   ├── workspace_presets.json# Presets for coding, gaming, study, chill, & cyber modes
│   └── long_term.json        # Persistent user preferences & workstation memory
└── config/
    └── api_keys.json         # API keys and provider preferences (git-ignored)
```

---

## 🔒 Privacy & Safety

- **Local Execution**: All memories, terminal actions, filesystem operations, and presets remain strictly on your local machine.
- **Protected Actions**: Irreversible system commands (shutdown, reboot, network disconnect) require explicit on-screen user confirmation.
- **Data Boundaries**: Credentials in `config/api_keys.json` and biometric indices are `.gitignore` protected.

---

## 📄 License

This project is licensed under the **MIT License**.
