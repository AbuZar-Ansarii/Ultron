"""
actions/cloud_watchtower.py — Cloud & Server Watchtower ("DevOps Overseer") for Ultron AI.

Monitors live cloud infrastructure, homelab servers, web APIs, and GitHub repository health.
Audits server response latency, uptime status, and GitHub CI/CD workflows.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import concurrent.futures
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Any, Optional

try:
    import requests
    _REQUESTS = True
except ImportError:
    _REQUESTS = False

_BASE_DIR = Path(__file__).resolve().parent.parent
_FLEET_PATH = _BASE_DIR / "memory" / "server_fleet.json"
_CONFIG_PATH = _BASE_DIR / "config" / "api_keys.json"


def _get_fleet() -> list[dict[str, str]]:
    """Load monitored server fleet."""
    if _FLEET_PATH.exists():
        try:
            with open(_FLEET_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return [
        {"name": "Google DNS", "url": "https://dns.google"},
        {"name": "Cloudflare Speed", "url": "https://speed.cloudflare.com"},
        {"name": "GitHub Status", "url": "https://www.githubstatus.com"},
    ]


def _save_fleet(fleet: list[dict[str, str]]) -> None:
    _FLEET_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(_FLEET_PATH, "w", encoding="utf-8") as f:
            json.dump(fleet, f, indent=2)
    except Exception:
        pass


def _get_github_token() -> str:
    """Retrieve github_token from config/api_keys.json."""
    if not _CONFIG_PATH.exists():
        return ""
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("github_token", "").strip()
    except Exception:
        return ""


def check_endpoint_health(url: str) -> str:
    """Audit single server endpoint latency and status."""
    if not _REQUESTS:
        return "requests library is required for health checking."

    clean_url = (url or "").strip()
    if not clean_url.startswith("http"):
        clean_url = f"https://{clean_url}"

    lines = [
        f"🛰️ ENDPOINT HEALTH AUDIT — {clean_url}",
        "─" * 55,
    ]

    t0 = time.time()
    try:
        resp = requests.get(clean_url, timeout=8.0, headers={"User-Agent": "Ultron-DevOps-Sentinel/1.0"})
        lat_ms = (time.time() - t0) * 1000

        status_badge = "🟢 200 OK" if resp.status_code == 200 else f"⚠️ {resp.status_code} {resp.reason}"
        lines.append(f"• HTTP Status:     {status_badge}")
        lines.append(f"• Latency:         {lat_ms:.1f} ms")
        lines.append(f"• Server Header:   {resp.headers.get('Server', 'Hidden / Cloudflare')}")
        lines.append(f"• Payload Size:    {len(resp.content):,} bytes")
        lines.append(f"• Encoding:        {resp.encoding or 'UTF-8'}")
    except Exception as e:
        lines.append(f"• Status:          🔴 UNREACHABLE / TIMEOUT")
        lines.append(f"• Diagnostic:      {e}")

    lines.append("─" * 55)
    return "\n".join(lines)


def probe_fleet() -> str:
    """Audit all endpoints in the server fleet in parallel."""
    if not _REQUESTS:
        return "requests library required for fleet auditing."

    fleet = _get_fleet()
    lines = [
        f"🛰️ CLOUD FLEET WATCHTOWER — UPTIME MATRIX",
        f"Auditing {len(fleet)} targets across production perimeter...",
        "─" * 60,
    ]

    results: list[dict[str, Any]] = []

    def _probe(item: dict[str, str]):
        name = item.get("name", "Server")
        url = item.get("url", "")
        t0 = time.time()
        try:
            r = requests.get(url, timeout=5.0, headers={"User-Agent": "Ultron-DevOps-Sentinel/1.0"})
            lat = (time.time() - t0) * 1000
            results.append({"name": name, "url": url, "status": r.status_code, "lat": lat, "ok": r.status_code < 400})
        except Exception:
            results.append({"name": name, "url": url, "status": 0, "lat": 999.0, "ok": False})

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        ex.map(_probe, fleet)

    results.sort(key=lambda x: (not x["ok"], x["lat"]))

    for r in results:
        badge = f"🟢 {r['status']}" if r["ok"] else "🔴 DOWN"
        lines.append(f"• {r['name']:<20} | {badge:<8} | {r['lat']:>5.1f} ms | {r['url']}")

    lines.append("─" * 60)
    up_count = sum(1 for r in results if r["ok"])
    lines.append(f"Fleet Summary: {up_count}/{len(fleet)} nodes operational. Infrastructure secure.")
    return "\n".join(lines)


def check_github_repo(repo: str) -> str:
    """Audit GitHub repository commits and issues."""
    clean_repo = (repo or "").strip().rstrip("/")
    # Format: owner/repo
    if "github.com/" in clean_repo:
        clean_repo = clean_repo.split("github.com/")[-1]

    if "/" not in clean_repo:
        return "Please specify repository in 'owner/repo' format (e.g. 'torvalds/linux', 'langchain-ai/langchain')."

    lines = [
        f"🛰️ GITHUB REPOSITORY WATCH — {clean_repo}",
        "─" * 55,
    ]

    token = _get_github_token()
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Ultron-DevOps-Sentinel/1.0"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        resp = requests.get(f"https://api.github.com/repos/{clean_repo}", headers=headers, timeout=6.0)
        if resp.status_code == 200:
            d = resp.json()
            lines.append(f"• Repository:     {d.get('full_name')}")
            lines.append(f"• Stars / Forks:  ⭐ {d.get('stargazers_count', 0):,} | 🍴 {d.get('forks_count', 0):,}")
            lines.append(f"• Open Issues:    {d.get('open_issues_count', 0):,}")
            lines.append(f"• Default Branch: {d.get('default_branch', 'main')}")
            lines.append(f"• Last Pushed:    {d.get('pushed_at', 'N/A')[:10]}")
        else:
            lines.append(f"• API Status:     HTTP {resp.status_code} ({resp.reason})")

        # Get latest commit
        c_resp = requests.get(f"https://api.github.com/repos/{clean_repo}/commits?per_page=1", headers=headers, timeout=5.0)
        if c_resp.status_code == 200 and c_resp.json():
            latest = c_resp.json()[0]
            sha = latest.get("sha", "")[:7]
            author = latest.get("commit", {}).get("author", {}).get("name", "Unknown")
            msg = latest.get("commit", {}).get("message", "").splitlines()[0]
            lines.append(f"• Latest Commit:  [{sha}] by {author}: '{msg[:60]}'")
    except Exception as e:
        lines.append(f"GitHub query failed: {e}")

    lines.append("─" * 55)
    return "\n".join(lines)


def add_fleet_target(url: str, name: str = "") -> str:
    """Add a new server to the watched fleet."""
    clean_url = (url or "").strip()
    if not clean_url:
        return "Please specify a URL or domain."
    if not clean_url.startswith("http"):
        clean_url = f"https://{clean_url}"

    fleet = _get_fleet()
    fleet_name = name or clean_url.split("//")[-1].split("/")[0]
    fleet.append({"name": fleet_name, "url": clean_url})
    _save_fleet(fleet)
    return f"Target '{fleet_name}' ({clean_url}) registered into Ultron Server Fleet."


def cloud_watchtower(parameters: dict, player=None, **kwargs) -> str:
    """Main entrypoint for cloud_watchtower tool."""
    action = (parameters.get("action") or "fleet").lower().strip()
    target_url = parameters.get("url") or parameters.get("target") or ""
    repo = parameters.get("repo") or ""
    name = parameters.get("name") or ""

    if player:
        try:
            player.write_log(f"[Cloud Watchtower] Action: {action}")
        except Exception:
            pass

    try:
        if action in ("fleet", "watch_fleet", "status", "uptime"):
            return probe_fleet()
        elif action in ("health", "check", "ping", "test"):
            return check_endpoint_health(url=target_url)
        elif action in ("github", "repo", "git"):
            return check_github_repo(repo=repo or target_url)
        elif action in ("add", "add_target", "register"):
            return add_fleet_target(url=target_url, name=name)
        else:
            return (
                f"Unknown watchtower action '{action}'. "
                "Available actions: fleet, health, github, add_target."
            )
    except Exception as e:
        return f"Cloud Watchtower encountered error: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "cloud_watchtower",
    "description": (
        "Cloud & Server Watchtower ('DevOps Overseer') for Ultron. "
        "Audits server uptime and response latency across your monitored server fleet (fleet), "
        "checks single website or API endpoint health (health), "
        "monitors GitHub repository commits and open issues (github), "
        "and registers new server targets into the watch fleet (add_target). "
        "Use whenever user asks to check server status, monitor a website, or inspect GitHub repos."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "fleet (audit full server uptime matrix) | health (check single URL health) | github (inspect repo commits & issues) | add_target (add server to watch fleet)"
            },
            "url": {
                "type": "STRING",
                "description": "Target website or API URL for health checking or adding to fleet."
            },
            "repo": {
                "type": "STRING",
                "description": "GitHub repo in 'owner/repo' format (e.g. 'torvalds/linux')."
            },
            "name": {
                "type": "STRING",
                "description": "Friendly name for server when adding to fleet."
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": cloud_watchtower,
}
