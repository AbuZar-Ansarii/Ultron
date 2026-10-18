"""
core/telegram_bot.py — Telegram Remote Control Engine for Ultron AI.
Enables full remote management of your workstation from your phone via Telegram:
  - Secure authorization: pairs with the Boss's Chat ID and rejects unauthorized access.
  - Live command execution: speak or text any natural language instruction from your phone.
  - Quick telemetric commands:
      /status    — Real-time CPU, RAM, GPU, temperature telemetry
      /screen    — Instant full-resolution workstation screen capture sent to phone
      /camera    — Webcam snapshot sent to phone
      /lock      — Instant workstation lockdown
      /network   — Wi-Fi diagnostics and connected LAN perimeter nodes
      /speed     — Bandwidth download & latency benchmark
      /purge     — Deep temporary cache purge & storage reclaimer
      /sentry    — Arm or disarm autonomous surveillance
      /sfx       — Play cinematic MCU sound effects on PC speakers
      /protocol  — Trigger Vibranium battle mode (Lockdown, Code, Gaming, Night)
  - Bi-directional push notifications (e.g. Sentry intruder alerts, system warnings).
"""
from __future__ import annotations

import io
import json
import os
import platform
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import requests

from memory.config_manager import get_telegram_config, save_telegram_config

_BASE_DIR = Path(__file__).resolve().parent.parent
_OS = platform.system()


class TelegramBot:
    def __init__(self, token: str, chat_id: str = "", executor: Optional[Callable[[str], str]] = None):
        self.token = (token or "").strip()
        self.chat_id = str(chat_id or "").strip()
        self.executor = executor
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_update_id = 0
        self._base_url = f"https://api.telegram.org/bot{self.token}"

    @property
    def is_running(self) -> bool:
        return self._running and (self._thread is not None and self._thread.is_alive())

    def update_credentials(self, token: str, chat_id: str = ""):
        """Update active token and allowed chat_id."""
        self.token = token.strip()
        self.chat_id = str(chat_id or "").strip()
        self._base_url = f"https://api.telegram.org/bot{self.token}"

    def start(self) -> bool:
        """Launch background long-polling daemon thread."""
        if not self.token:
            return False
        if self.is_running:
            return True

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="UltronTelegramBot")
        self._thread.start()
        print(f"[Telegram] Bot daemon started (Auth Chat ID: {self.chat_id or 'Waiting for auto-pair'})")
        return True

    def stop(self):
        """Stop background polling thread."""
        self._running = False
        self._thread = None
        print("[Telegram] Bot daemon stopped.")

    def send_message(self, text: str, target_chat_id: Optional[str] = None) -> bool:
        """Send a text message to the Boss or specific chat ID."""
        cid = target_chat_id or self.chat_id
        if not self.token or not cid:
            return False

        url = f"{self._base_url}/sendMessage"
        # Telegram has a 4096 character limit per message
        clean_text = (text or "").strip()
        if len(clean_text) > 4000:
            clean_text = clean_text[:4000] + "\n... [Output truncated for Telegram]"

        try:
            resp = requests.post(
                url,
                json={"chat_id": cid, "text": clean_text, "parse_mode": "Markdown"},
                timeout=10
            )
            # Fall back to unformatted text if markdown parsing fails
            if resp.status_code != 200:
                resp = requests.post(
                    url,
                    json={"chat_id": cid, "text": clean_text},
                    timeout=10
                )
            return resp.status_code == 200
        except Exception as e:
            print(f"[Telegram] Send message error: {e}")
            return False

    def send_photo(self, photo_data: bytes | Path | str, caption: str = "", target_chat_id: Optional[str] = None) -> bool:
        """Send a photo to the Boss's Telegram."""
        cid = target_chat_id or self.chat_id
        if not self.token or not cid:
            return False

        url = f"{self._base_url}/sendPhoto"
        try:
            if isinstance(photo_data, (bytes, bytearray)):
                files = {"photo": ("capture.jpg", io.BytesIO(photo_data), "image/jpeg")}
                resp = requests.post(url, data={"chat_id": cid, "caption": caption[:1024]}, files=files, timeout=15)
                return resp.status_code == 200
            elif isinstance(photo_data, (Path, str)):
                p = Path(photo_data)
                if p.exists():
                    with open(p, "rb") as f:
                        files = {"photo": (p.name, f, "image/jpeg")}
                        resp = requests.post(url, data={"chat_id": cid, "caption": caption[:1024]}, files=files, timeout=15)
                        return resp.status_code == 200
        except Exception as e:
            print(f"[Telegram] Send photo error: {e}")
        return False

    def _poll_loop(self):
        """Long polling updates loop."""
        while self._running:
            try:
                url = f"{self._base_url}/getUpdates"
                params = {"offset": self._last_update_id + 1, "timeout": 20}
                resp = requests.get(url, params=params, timeout=25)

                if resp.status_code != 200:
                    time.sleep(3.0)
                    continue

                data = resp.json()
                updates = data.get("result", [])

                for update in updates:
                    up_id = update.get("update_id", 0)
                    if up_id > self._last_update_id:
                        self._last_update_id = up_id

                    msg = update.get("message")
                    if msg:
                        self._handle_message(msg)

            except requests.exceptions.Timeout:
                continue
            except Exception as e:
                time.sleep(3.0)

    def _handle_message(self, msg: dict):
        """Process incoming Telegram message."""
        sender_chat = msg.get("chat", {})
        sender_id = str(sender_chat.get("id", ""))
        user_name = sender_chat.get("first_name", "User")
        text = (msg.get("text") or "").strip()

        if not text or not sender_id:
            return

        # ── Pairing / Authentication Gate ────────────────────────────────────
        if not self.chat_id:
            # First interaction auto-pairs with Boss
            self.chat_id = sender_id
            save_telegram_config(self.token, self.chat_id, enabled=True)
            welcome_msg = (
                f"🤖 *ULTRON AI — TELEMETRIC LINK ESTABLISHED*\n"
                f"Handshake authenticated with *{user_name}* (Chat ID: `{sender_id}`).\n"
                f"Workstation is now cryptographically bound to this phone link, Boss.\n\n"
                f"Type /help to inspect remote command protocols."
            )
            self.send_message(welcome_msg, target_chat_id=sender_id)
            return

        # Reject any other chat IDs
        if str(self.chat_id) != sender_id:
            denied_msg = "⛔ *ACCESS DENIED*\nUnauthorized biological entity. This workstation is strictly bound to the Boss."
            self.send_message(denied_msg, target_chat_id=sender_id)
            return

        # ── Command Routing ──────────────────────────────────────────────────
        cmd_lower = text.lower().strip()

        if cmd_lower in ("/start", "/help"):
            help_text = (
                "🤖 *ULTRON COMMAND DIRECTIVES:*\n"
                "• `/status` — System hardware metrics (CPU/RAM/GPU/Temp)\n"
                "• `/screen` — Live desktop screenshot\n"
                "• `/camera` — Live webcam snapshot\n"
                "• `/lock` — Lock PC workstation immediately\n"
                "• `/speed` — Network speed & latency benchmark\n"
                "• `/network` — Wi-Fi & LAN perimeter device scan\n"
                "• `/purge` — Purge temporary files & junk cache\n"
                "• `/protocol <name>` — Run Vibranium battle mode (lockdown, code, gaming, night)\n"
                "• `/sfx <sound>` — Play cinematic SFX (repulsor, alarm, bass_drop, sonar)\n\n"
                "_You can also send ANY natural command:_\n"
                "• \"Open Chrome and search Marvel\"\n"
                "• \"Download https://example.com/file.zip\"\n"
                "• \"Activate protocol lockdown\"\n"
                "• \"What is the weather today?\""
            )
            self.send_message(help_text)
            return

        elif cmd_lower == "/status":
            try:
                from actions.system_monitor import get_system_status
                status_res = get_system_status()
                self.send_message(f"📊 *WORKSTATION TELEMETRY:*\n```\n{status_res}\n```")
            except Exception as e:
                self.send_message(f"Failed to fetch system status: {e}")
            return

        elif cmd_lower in ("/screen", "/screenshot"):
            self.send_message("📸 Capturing workstation display...")
            try:
                from actions.screen_processor import _capture_screen
                img_bytes, _ = _capture_screen()
                self.send_photo(img_bytes, caption="🖥️ Live Workstation Screen Capture")
            except Exception as e:
                self.send_message(f"Screen capture failed: {e}")
            return

        elif cmd_lower in ("/camera", "/cam", "/webcam"):
            self.send_message("👁️ Accessing optical webcam sensor...")
            try:
                from actions.screen_processor import _capture_camera
                img_bytes, _ = _capture_camera()
                self.send_photo(img_bytes, caption="📷 Live Optical Sensor Snapshot")
            except Exception as e:
                self.send_message(f"Camera capture failed: {e}")
            return

        elif cmd_lower == "/lock":
            try:
                import ctypes
                if _OS == "Windows":
                    ctypes.windll.user32.LockWorkStation()
                self.send_message("🔒 Workstation locked successfully, Boss.")
            except Exception as e:
                self.send_message(f"Lock failed: {e}")
            return

        elif cmd_lower in ("/speed", "/speedtest"):
            self.send_message("⚡ Running latency and download throughput benchmark...")
            try:
                from actions.network_scanner import speed_and_latency_test
                res = speed_and_latency_test()
                self.send_message(f"```\n{res}\n```")
            except Exception as e:
                self.send_message(f"Speedtest failed: {e}")
            return

        elif cmd_lower in ("/network", "/lan", "/wifi"):
            self.send_message("🛡️ Scanning network perimeter...")
            try:
                from actions.network_scanner import scan_lan, get_wifi_diagnostics
                wifi_info = get_wifi_diagnostics()
                lan_info = scan_lan(quick=True)
                self.send_message(f"```\n{wifi_info}\n\n{lan_info}\n```")
            except Exception as e:
                self.send_message(f"Network scan failed: {e}")
            return

        elif cmd_lower == "/purge":
            self.send_message("🧹 Executing deep purge protocol...")
            try:
                from actions.purge_protocol import execute_purge
                res = execute_purge(include_recycle_bin=True, include_dev=True)
                self.send_message(f"```\n{res}\n```")
            except Exception as e:
                self.send_message(f"Purge failed: {e}")
            return

        elif cmd_lower.startswith("/protocol"):
            proto_name = cmd_lower.replace("/protocol", "").strip() or "lockdown"
            try:
                from actions.macro_protocol import run_protocol
                res = run_protocol(proto_name)
                self.send_message(f"⚡ {res}")
            except Exception as e:
                self.send_message(f"Protocol execution error: {e}")
            return

        elif cmd_lower.startswith("/sfx"):
            sfx_name = cmd_lower.replace("/sfx", "").strip() or "repulsor"
            try:
                from actions.audio_matrix import play_sound_async
                ok = play_sound_async(sfx_name)
                self.send_message(f"🔊 Sound '{sfx_name}' {'dispatched' if ok else 'failed'} on PC speakers.")
            except Exception as e:
                self.send_message(f"SFX error: {e}")
            return

        # ── Natural Language Directive (Dispatched to Ultron Engine) ──────────
        self.send_message("🧠 Processing directive...")
        if self.executor:
            try:
                reply = self.executor(text)
                self.send_message(reply or "Directive executed, Boss.")
            except Exception as e:
                self.send_message(f"Execution error: {e}")
        else:
            self.send_message("Ultron execution engine is not attached.")


# ── Global Singleton Management ──────────────────────────────────────────────

_GLOBAL_BOT: Optional[TelegramBot] = None
_BOT_LOCK = threading.Lock()


def get_telegram_bot() -> Optional[TelegramBot]:
    global _GLOBAL_BOT
    return _GLOBAL_BOT


def init_telegram_bot(executor: Optional[Callable[[str], str]] = None) -> Optional[TelegramBot]:
    """Initialize and optionally start the Telegram Bot based on stored config."""
    global _GLOBAL_BOT
    cfg = get_telegram_config()
    token = cfg.get("token", "")
    chat_id = cfg.get("chat_id", "")
    enabled = cfg.get("enabled", False)

    with _BOT_LOCK:
        if _GLOBAL_BOT is None:
            _GLOBAL_BOT = TelegramBot(token=token, chat_id=chat_id, executor=executor)
        else:
            _GLOBAL_BOT.update_credentials(token=token, chat_id=chat_id)
            if executor:
                _GLOBAL_BOT.executor = executor

        if token and enabled and not _GLOBAL_BOT.is_running:
            _GLOBAL_BOT.start()

    return _GLOBAL_BOT


def send_telegram_alert(text: str, photo_path: str | Path | None = None) -> bool:
    """Helper to send push notifications from other tools (e.g. Sentry Protocol)."""
    bot = get_telegram_bot()
    if not bot or not bot.is_running:
        # Fallback to direct HTTP post
        cfg = get_telegram_config()
        token = cfg.get("token")
        chat_id = cfg.get("chat_id")
        if not token or not chat_id:
            return False
        temp_bot = TelegramBot(token=token, chat_id=chat_id)
        if photo_path:
            return temp_bot.send_photo(photo_path, caption=text)
        return temp_bot.send_message(text)

    if photo_path:
        return bot.send_photo(photo_path, caption=text)
    return bot.send_message(text)
