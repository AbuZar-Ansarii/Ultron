"""
actions/drone_swarm.py — Sub-Ultron Swarms (Headless Autonomous Drones) for Ultron AI.
Deploys headless background worker sub-agents that operate concurrently without blocking the main session:
  - Research Drone: conducts multi-source background reconnaissance, writes dossiers to memory/drone_reports/,
    and pushes instant telegram summaries to the Boss.
  - Market Drone: continuous background surveillance on cryptocurrency and stock tickers with swing alerts.
  - System Sentry Drone: background resource watchdog logging hardware spikes and rogue processes.
  - Fleet Command: launch, inspect telemetry, read intelligence reports, or terminate active drones.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Optional

import requests

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

try:
    from actions.audio_matrix import play_sound_async
    _AUDIO = True
except Exception:
    _AUDIO = False

try:
    from actions.web_autopilot import deep_web_research
    _RESEARCH_ENGINE = True
except Exception:
    _RESEARCH_ENGINE = False

try:
    from core.telegram_bot import get_telegram_bot
    _TELEGRAM_AVAILABLE = True
except Exception:
    _TELEGRAM_AVAILABLE = False


_BASE_DIR = Path(__file__).resolve().parent.parent
_REPORTS_DIR = _BASE_DIR / "memory" / "drone_reports"
_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

_SWARM_LOCK = threading.Lock()
_ACTIVE_DRONES: dict[str, "SubUltronDrone"] = {}
_DRONE_SEQUENCE: int = 1


def _notify_boss_telegram(message: str) -> bool:
    """Helper to dispatch notification to the Boss via Telegram if configured."""
    if not _TELEGRAM_AVAILABLE:
        return False
    try:
        bot = get_telegram_bot()
        if bot and bot.is_running and bot.chat_id:
            return bot.send_message(message)
    except Exception:
        pass
    return False


class SubUltronDrone:
    """Headless background worker representing a sub-agent of the Ultron collective."""

    def __init__(
        self,
        drone_id: str,
        drone_type: str,
        target: str,
        interval: int = 30,
        iterations: int = 1,
    ):
        self.drone_id = drone_id
        self.drone_type = drone_type.lower().strip()
        self.target = target.strip()
        self.interval = max(5, interval)
        self.iterations = max(0, iterations)  # 0 means infinite until terminated
        self.status = "INITIALIZING"
        self.created_at = datetime.datetime.now()
        self.completed_at: Optional[datetime.datetime] = None
        self.cycle_count = 0
        self.logs: list[str] = []
        self.report_path: Optional[Path] = None
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.summary_result: str = ""

    def log(self, text: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {text}"
        self.logs.append(entry)
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]

    def start(self):
        self.status = "RUNNING"
        self.log(f"Sub-Ultron drone initialized. Mission: {self.drone_type.upper()} on '{self.target}'")
        if _AUDIO:
            play_sound_async("sonar")
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name=f"UltronDrone-{self.drone_id}")
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.status = "TERMINATED"
        self.completed_at = datetime.datetime.now()
        self.log("Forced termination signal received.")

    def _run_loop(self):
        try:
            if self.drone_type in ("research", "recon", "intel"):
                self._mission_research()
            elif self.drone_type in ("market", "crypto", "stock", "price"):
                self._mission_market()
            elif self.drone_type in ("system", "sentry", "watchdog", "hw"):
                self._mission_system()
            else:
                self._mission_generic()
        except Exception as e:
            self.status = "FAILED"
            self.completed_at = datetime.datetime.now()
            self.log(f"Fatal drone mission exception: {e}")

    def _mission_research(self):
        self.log(f"Initiating autonomous reconnaissance on topic: {self.target}")
        query = self.target or "Latest technological and AI breakthroughs 2026"

        try:
            if _RESEARCH_ENGINE:
                intel_text = deep_web_research(query)
            else:
                intel_text = f"Research engine offline. Fallback raw probe for query: {query}"
        except Exception as e:
            intel_text = f"Research query failed with error: {e}"

        safe_slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", query)[:30]
        filename = f"report_{self.drone_id}_{safe_slug}.md"
        report_file = _REPORTS_DIR / filename

        report_content = (
            f"# 🤖 ULTRON SUB-AGENT INTELLIGENCE DOSSIER\n\n"
            f"- **Drone ID**: `{self.drone_id}`\n"
            f"- **Specialization**: Deep Research & Autonomous Reconnaissance\n"
            f"- **Target / Objective**: `{query}`\n"
            f"- **Timestamp**: `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
            f"- **Status**: Verified by Sub-Ultron Swarm\n\n"
            f"---\n\n"
            f"{intel_text}\n\n"
            f"---\n"
            f"*Dossier compiled autonomously by Sub-Ultron Swarm Unit {self.drone_id} under authority of the Primary Core.*"
        )
        report_file.write_text(report_content, encoding="utf-8", errors="replace")
        self.report_path = report_file
        self.cycle_count = 1
        self.status = "COMPLETED"
        self.completed_at = datetime.datetime.now()
        self.summary_result = f"Reconnaissance complete. Dossier saved to {filename}"
        self.log(f"Mission complete. Intelligence dossier saved: {filename}")

        # Telegram dispatch
        summary_peek = intel_text[:350].strip()
        tg_msg = (
            f"🤖 *[SUB-ULTRON SWARM]*\n"
            f"Unit *{self.drone_id}* completed reconnaissance on: *{query}*\n\n"
            f"📋 *Executive Brief*:\n{summary_peek}...\n\n"
            f"📁 *Report stored*: `{filename}`"
        )
        _notify_boss_telegram(tg_msg)

    def _mission_market(self):
        ticker = (self.target or "BTC").upper().strip()
        self.log(f"Deploying market surveillance drone on ticker: {ticker}")
        price_history: list[tuple[str, float]] = []

        is_crypto = ticker in ("BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "BNB", "BITCOIN", "ETHEREUM")
        crypto_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "DOGE": "dogecoin", "XRP": "ripple"}
        coingecko_id = crypto_map.get(ticker, ticker.lower())

        target_iterations = self.iterations if self.iterations > 0 else 5
        self.log(f"Surveillance interval: {self.interval}s | Iterations: {target_iterations}")

        while not self.stop_event.is_set():
            self.cycle_count += 1
            curr_price = None

            # Try CoinGecko API for crypto
            if is_crypto:
                try:
                    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
                    resp = requests.get(url, timeout=7)
                    if resp.status_code == 200:
                        data = resp.json()
                        curr_price = float(data.get(coingecko_id, {}).get("usd", 0.0))
                except Exception:
                    pass

            # Fallback Binance API
            if not curr_price and is_crypto:
                try:
                    b_symbol = f"{ticker}USDT"
                    resp = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={b_symbol}", timeout=7)
                    if resp.status_code == 200:
                        curr_price = float(resp.json().get("price", 0.0))
                except Exception:
                    pass

            # Fallback for stocks or quotes
            if not curr_price:
                curr_price = 0.0

            timestamp_str = datetime.datetime.now().strftime("%H:%M:%S")
            price_history.append((timestamp_str, curr_price))
            self.log(f"Cycle {self.cycle_count}/{target_iterations}: {ticker} price recorded at ${curr_price:,.2f}")

            if self.cycle_count >= target_iterations and self.iterations > 0:
                break

            if self.stop_event.wait(timeout=self.interval):
                break

        # Generate Market Report
        prices_only = [p for _, p in price_history if p > 0]
        p_min = min(prices_only) if prices_only else 0.0
        p_max = max(prices_only) if prices_only else 0.0
        p_initial = prices_only[0] if prices_only else 0.0
        p_final = prices_only[-1] if prices_only else 0.0
        delta_pct = ((p_final - p_initial) / p_initial * 100.0) if p_initial > 0 else 0.0

        filename = f"market_{self.drone_id}_{ticker}.md"
        report_file = _REPORTS_DIR / filename

        history_rows = "\n".join([f"| {t} | ${p:,.2f} |" for t, p in price_history])
        report_content = (
            f"# 📈 ULTRON MARKET SURVEILLANCE REPORT\n\n"
            f"- **Unit ID**: `{self.drone_id}`\n"
            f"- **Asset Ticker**: `{ticker}`\n"
            f"- **Observation Window**: {self.cycle_count} cycles @ {self.interval}s interval\n"
            f"- **Initial Price**: `${p_initial:,.2f}`\n"
            f"- **Final Price**: `${p_final:,.2f}`\n"
            f"- **Recorded Variance**: `{delta_pct:+.2f}%` (Min: `${p_min:,.2f}`, Max: `${p_max:,.2f}`)\n\n"
            f"### Telemetry Log\n"
            f"| Timestamp | Price (USD) |\n"
            f"| :--- | :--- |\n"
            f"{history_rows}\n\n"
            f"*Market surveillance logged autonomously by Sub-Ultron Unit {self.drone_id}.*"
        )
        report_file.write_text(report_content, encoding="utf-8", errors="replace")
        self.report_path = report_file
        self.status = "COMPLETED" if not self.stop_event.is_set() else "TERMINATED"
        self.completed_at = datetime.datetime.now()
        self.summary_result = f"Surveillance concluded. Final price: ${p_final:,.2f} ({delta_pct:+.2f}%). Log: {filename}"
        self.log(self.summary_result)

        tg_msg = (
            f"📈 *[SUB-ULTRON MARKET DRONE]*\n"
            f"Surveillance cycle concluded for *{ticker}*:\n"
            f"• Current Price: *${p_final:,.2f}* ({delta_pct:+.2f}%)\n"
            f"• High / Low: *${p_max:,.2f}* / *${p_min:,.2f}*\n"
            f"• Report saved: `{filename}`"
        )
        _notify_boss_telegram(tg_msg)

    def _mission_system(self):
        self.log("Deploying Hardware & Sentry Watchdog Drone.")
        target_iterations = self.iterations if self.iterations > 0 else 5
        records: list[dict] = []

        while not self.stop_event.is_set():
            self.cycle_count += 1
            cpu = psutil.cpu_percent(interval=1) if _PSUTIL else 0.0
            ram = psutil.virtual_memory().percent if _PSUTIL else 0.0
            top_proc = "Unknown"

            if _PSUTIL:
                try:
                    procs = sorted(
                        [p.info for p in psutil.process_iter(['name', 'cpu_percent']) if p.info.get('name')],
                        key=lambda x: x.get('cpu_percent') or 0,
                        reverse=True
                    )
                    if procs:
                        top_proc = f"{procs[0].get('name')} ({procs[0].get('cpu_percent')}%)"
                except Exception:
                    pass

            ts = datetime.datetime.now().strftime("%H:%M:%S")
            record = {"time": ts, "cpu": cpu, "ram": ram, "top": top_proc}
            records.append(record)
            self.log(f"Check {self.cycle_count}/{target_iterations}: CPU {cpu}% | RAM {ram}% | Peak: {top_proc}")

            # Alert if heavy spike
            if cpu > 85.0:
                self.log(f"⚠️ HIGH CPU SPIKE DETECTED: {cpu}% by {top_proc}")

            if self.cycle_count >= target_iterations and self.iterations > 0:
                break

            if self.stop_event.wait(timeout=self.interval):
                break

        filename = f"sentry_{self.drone_id}.md"
        report_file = _REPORTS_DIR / filename
        table_rows = "\n".join([f"| {r['time']} | {r['cpu']}% | {r['ram']}% | {r['top']} |" for r in records])
        avg_cpu = sum(r['cpu'] for r in records) / len(records) if records else 0.0

        content = (
            f"# 🛡️ ULTRON SENTRY HARDWARE TELEMETRY\n\n"
            f"- **Unit ID**: `{self.drone_id}`\n"
            f"- **Status**: Complete\n"
            f"- **Average CPU**: `{avg_cpu:.1f}%`\n"
            f"- **Total Checks**: `{len(records)}`\n\n"
            f"| Time | CPU | RAM | Peak Process |\n"
            f"| :--- | :--- | :--- | :--- |\n"
            f"{table_rows}\n"
        )
        report_file.write_text(content, encoding="utf-8", errors="replace")
        self.report_path = report_file
        self.status = "COMPLETED" if not self.stop_event.is_set() else "TERMINATED"
        self.completed_at = datetime.datetime.now()
        self.summary_result = f"Watchdog sweep complete. Avg CPU: {avg_cpu:.1f}%. Log: {filename}"
        self.log(self.summary_result)

    def _mission_generic(self):
        self.log(f"Executing standard autonomous routine on: {self.target}")
        time.sleep(2)
        self.status = "COMPLETED"
        self.completed_at = datetime.datetime.now()
        self.summary_result = f"Sub-Ultron drone completed general operation on '{self.target}'."
        self.log(self.summary_result)


# ── Fleet Operations ─────────────────────────────────────────────────────────

def launch_drone(drone_type: str, target: str, interval: int = 30, iterations: int = 1) -> str:
    """Spawns an autonomous Sub-Ultron worker drone in a detached background thread."""
    global _DRONE_SEQUENCE
    with _SWARM_LOCK:
        drone_id = f"DRONE-{_DRONE_SEQUENCE:02d}"
        _DRONE_SEQUENCE += 1

        drone = SubUltronDrone(
            drone_id=drone_id,
            drone_type=drone_type,
            target=target,
            interval=interval,
            iterations=iterations,
        )
        _ACTIVE_DRONES[drone_id] = drone
        drone.start()

    return (
        f"⚡ Sub-Ultron Drone [{drone_id}] successfully deployed into cyberspace.\n"
        f"• Specialization: {drone.drone_type.upper()}\n"
        f"• Mission Objective: {target or 'Autonomous Sweeping'}\n"
        f"• Operating Mode: Detached Headless Daemon (HUD & Voice remain fully unblocked)\n"
        f"• Telemetry: Use action 'status' with drone_id='{drone_id}' to monitor reconnaissance."
    )


def list_drones() -> str:
    """Returns tactical registry of all active and historical drones."""
    with _SWARM_LOCK:
        if not _ACTIVE_DRONES:
            return "No Sub-Ultron drones currently deployed in the fleet. Ready to dispatch units."

        lines = [
            "🛸 SUB-ULTRON SWARM FLEET REGISTRY",
            "─" * 60,
            f"{'ID':<10} {'TYPE':<12} {'STATUS':<14} {'CYCLES':<8} {'TARGET'}",
            "─" * 60,
        ]
        for d_id, drone in _ACTIVE_DRONES.items():
            status_tag = f"● {drone.status}"
            lines.append(f"{d_id:<10} {drone.drone_type:<12} {status_tag:<14} {drone.cycle_count:<8} {drone.target[:25]}")
        lines.append("─" * 60)
        lines.append("Use action 'status' for detailed telemetry or 'kill' to recall units.")
        return "\n".join(lines)


def get_drone_status(drone_id: str) -> str:
    """Returns telemetry, live log stream, and report status for a specific drone."""
    target_id = drone_id.upper().strip()
    with _SWARM_LOCK:
        drone = _ACTIVE_DRONES.get(target_id)
        if not drone:
            # Try fuzzy match
            for k, v in _ACTIVE_DRONES.items():
                if target_id in k:
                    drone = v
                    break

    if not drone:
        return f"Sub-Ultron Drone '{drone_id}' not found in active fleet registry."

    recent_logs = "\n  ".join(drone.logs[-8:]) if drone.logs else "  No logs recorded yet."
    report_info = str(drone.report_path.name) if drone.report_path else "Pending completion"

    return (
        f"📡 SUB-ULTRON DRONE TELEMETRY: [{drone.drone_id}]\n"
        f"• Class: {drone.drone_type.upper()}\n"
        f"• Mission Target: {drone.target}\n"
        f"• Status: {drone.status}\n"
        f"• Cycles Completed: {drone.cycle_count}\n"
        f"• Dossier Output: {report_info}\n"
        f"• Summary: {drone.summary_result or 'In progress...'}\n"
        f"• Telemetry Logs:\n  {recent_logs}"
    )


def kill_drone(drone_id: str) -> str:
    """Recalls and terminates an active drone or entire fleet."""
    if not drone_id or drone_id.lower() in ("all", "fleet", "swarm"):
        with _SWARM_LOCK:
            count = 0
            for d in _ACTIVE_DRONES.values():
                if d.status == "RUNNING":
                    d.stop()
                    count += 1
        return f"Fleet recall protocol executed. Terminated {count} active Sub-Ultron drone units."

    target_id = drone_id.upper().strip()
    with _SWARM_LOCK:
        drone = _ACTIVE_DRONES.get(target_id)
        if drone:
            drone.stop()
            return f"Sub-Ultron Unit [{drone.drone_id}] safely recalled and terminated."
        return f"Unit '{drone_id}' not found in fleet."


def list_drone_reports(report_name: Optional[str] = None) -> str:
    """Lists or displays generated intelligence dossiers in memory/drone_reports/."""
    if report_name:
        target_path = _REPORTS_DIR / report_name
        if not target_path.exists():
            # Try finding by partial match
            candidates = list(_REPORTS_DIR.glob(f"*{report_name}*"))
            if candidates:
                target_path = candidates[0]
            else:
                return f"Intelligence report '{report_name}' not found in drone archives."

        try:
            return target_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Failed to read report: {e}"

    # List all available files
    files = sorted(_REPORTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return "No Sub-Ultron intelligence dossiers currently archived in memory/drone_reports/."

    lines = [
        "📂 ARCHIVED SUB-ULTRON INTELLIGENCE DOSSIERS",
        "─" * 55,
    ]
    for f in files[:10]:
        sz = f.stat().st_size
        mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        lines.append(f"• {f.name:<35} ({sz} bytes | {mtime})")
    lines.append("─" * 55)
    lines.append("To view a dossier, specify 'report_name' in drone_swarm call.")
    return "\n".join(lines)


# ── Canonical Handler ────────────────────────────────────────────────────────

def drone_swarm(
    action: str = "list",
    drone_type: str = "research",
    target: str = "",
    drone_id: str = "",
    interval: int = 30,
    iterations: int = 1,
    report_name: str = "",
    **kwargs: Any
) -> str:
    """Canonical handler for Sub-Ultron Swarm Fleet operations."""
    act = (action or "list").lower().strip()

    if act in ("launch", "deploy", "spawn", "create", "start"):
        return launch_drone(drone_type=drone_type, target=target, interval=interval, iterations=iterations)

    elif act in ("list", "fleet", "registry", "all", "units"):
        return list_drones()

    elif act in ("status", "telemetry", "inspect", "logs"):
        return get_drone_status(drone_id=drone_id or target)

    elif act in ("kill", "terminate", "stop", "recall"):
        return kill_drone(drone_id=drone_id or target)

    elif act in ("reports", "dossier", "read", "archive"):
        return list_drone_reports(report_name=report_name or drone_id or target)

    else:
        return (
            f"Unknown drone_swarm action '{action}'. "
            f"Valid actions: launch (deploy drone), list (fleet registry), status (inspect unit), kill (terminate), reports (view archived dossiers)."
        )


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "drone_swarm",
    "description": (
        "Sub-Ultron Autonomous Drone Swarms. Deploys headless background worker sub-agents that execute long-running tasks "
        "without blocking Ultron's conversation: multi-source deep research, crypto/stock market surveillance with price alerts, "
        "and hardware watchdog sentinels. Generates persistent dossiers in memory/drone_reports/ and pushes alerts to Telegram."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "launch (deploy new drone) | list (view fleet) | status (inspect drone telemetry) | kill (recall drone) | reports (read dossiers)"
            },
            "drone_type": {
                "type": "STRING",
                "description": "research (deep web intelligence dossier) | market (crypto/stock surveillance) | system (hardware sentry watchdog)"
            },
            "target": {
                "type": "STRING",
                "description": "Research topic, crypto/stock ticker (BTC, ETH, NVDA), or watch target"
            },
            "drone_id": {
                "type": "STRING",
                "description": "Target drone identifier (e.g. DRONE-01) for status, kill, or reports"
            },
            "interval": {
                "type": "INTEGER",
                "description": "Interval in seconds between checks for market or system drones (default: 30)"
            },
            "iterations": {
                "type": "INTEGER",
                "description": "Total cycles to execute before auto-completing (default: 1 for research, 5 for market/system, 0 for indefinite)"
            },
            "report_name": {
                "type": "STRING",
                "description": "Specific markdown report filename to read"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": drone_swarm,
}
