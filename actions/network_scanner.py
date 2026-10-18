"""
actions/network_scanner.py — Network Sentinel & LAN Overlord for Ultron AI.
Scans local perimeter devices, probes open ports, inspects Wi-Fi telemetry,
tests connection latency & download throughput, and identifies public network footprint.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import platform
import re
import socket
import subprocess
import time
from typing import Any, Optional

try:
    import requests
    _REQUESTS = True
except ImportError:
    _REQUESTS = False

_OS = platform.system()
_WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW} if _OS == "Windows" else {}

# Common service ports mapped to names
_COMMON_PORTS: dict[int, str] = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    135: "RPC",
    139: "NetBIOS",
    443: "HTTPS",
    445: "SMB",
    1433: "MSSQL",
    1521: "Oracle",
    3000: "Node/React Dev",
    3306: "MySQL",
    3389: "RDP",
    5000: "Flask Dev",
    5432: "PostgreSQL",
    6379: "Redis",
    8000: "FastAPI/Dev Server",
    8080: "HTTP Proxy/Alt",
    8443: "HTTPS Alt",
    11434: "Ollama LLM",
    27017: "MongoDB",
}


def _get_local_ip() -> str:
    """Determine the active local outbound LAN IP."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def _ping_host(ip: str, timeout_ms: int = 250) -> bool:
    """Quick ICMP or socket ping to check if an IP is active across Windows, macOS, and Linux."""
    if _OS == "Windows":
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), ip]
    elif _OS == "Darwin":
        cmd = ["ping", "-c", "1", "-t", "1", ip]
    else:
        cmd = ["ping", "-c", "1", "-W", "1", ip]
    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **_WIN_HIDE)
        if res.returncode == 0:
            return True
    except Exception:
        pass

    # High-speed TCP connect probe fallback (ports 80, 443, 53, 22)
    for probe_port in (80, 443, 53, 22):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.12)
                if s.connect_ex((ip, probe_port)) == 0:
                    return True
        except Exception:
            pass
    return False


def _resolve_hostname(ip: str) -> str:
    """Attempt reverse DNS lookup for an IP."""
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except Exception:
        return "Unknown"


def scan_lan(quick: bool = True) -> str:
    """
    Scans the local subnet for active connected devices using ARP & ping sweeps.
    Compatible across Windows, macOS, and Linux.
    Returns a formatted inventory of all nodes on the Boss's network.
    """
    local_ip = _get_local_ip()
    if local_ip == "127.0.0.1":
        return "Unable to determine active network interface. Verify your network adapter is connected."

    parts = local_ip.split(".")
    subnet_prefix = ".".join(parts[:3])

    # Sweep common gateway & device IPs in parallel to warm the ARP cache
    targets = [f"{subnet_prefix}.{i}" for i in range(1, 255 if not quick else 35)]
    # Always include the router and user's IP
    if f"{subnet_prefix}.1" not in targets:
        targets.append(f"{subnet_prefix}.1")
    if local_ip not in targets:
        targets.append(local_ip)

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        list(executor.map(lambda ip: _ping_host(ip, timeout_ms=200), targets))

    # Parse system ARP table cross-platform
    devices: list[dict[str, str]] = []
    try:
        arp_res = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=5, **_WIN_HIDE)
        arp_out = arp_res.stdout or ""

        # Handles Windows (192.168.1.1 00-11-22-33-44-55 dynamic)
        # macOS (? (192.168.1.1) at 0:11:22:33:44:55 on en0 ifscope [ethernet])
        # Linux (? (192.168.1.1) at 00:11:22:33:44:55 [ether] on eth0)
        for line in arp_out.splitlines():
            m_ip = re.search(r"(?:^|\s|\()([0-9]{1,3}(?:\.[0-9]{1,3}){3})(?:\s|\)|$)", line)
            m_mac = re.search(r"([0-9a-fA-F]{1,2}(?:[:-][0-9a-fA-F]{1,2}){5})", line)
            if m_ip and m_mac:
                ip = m_ip.group(1)
                raw_mac = m_mac.group(1).lower().replace("-", ":")
                # Normalize 1-digit hex components (e.g. 0:11 -> 00:11)
                mac = ":".join(f"{int(x, 16):02x}" for x in raw_mac.split(":"))
                # Filter out multicast and broadcast ranges
                if ip.startswith("224.") or ip.startswith("239.") or ip.endswith(".255"):
                    continue
                if mac in ("ff:ff:ff:ff:ff:ff", "00:00:00:00:00:00"):
                    continue
                devices.append({
                    "ip": ip,
                    "mac": mac,
                    "type": "dynamic",
                    "is_self": (ip == local_ip),
                    "is_gateway": (ip == f"{subnet_prefix}.1"),
                })
    except Exception as e:
        return f"ARP scan failed: {e}"

    if not devices:
        return f"Perimeter scan completed on subnet {subnet_prefix}.0/24. Only your workstation ({local_ip}) is detected."

    # Reverse resolve hostnames concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        future_to_dev = {executor.submit(_resolve_hostname, d["ip"]): d for d in devices}
        for future in concurrent.futures.as_completed(future_to_dev):
            dev = future_to_dev[future]
            dev["hostname"] = future.result()

    # Build Ultron report
    lines = [
        f"🛡️ PERIMETER SCAN — Subnet {subnet_prefix}.0/24",
        f"Total active nodes discovered: {len(devices)}",
        "─" * 45,
    ]

    for d in sorted(devices, key=lambda x: [int(p) for p in x["ip"].split(".")]):
        tag = " [THIS WORKSTATION]" if d["is_self"] else (" [GATEWAY/ROUTER]" if d["is_gateway"] else "")
        host = f" ({d['hostname']})" if d['hostname'] != "Unknown" else ""
        lines.append(f"• IP: {d['ip']:<15} | MAC: {d['mac']} | Host:{host}{tag}")

    lines.append("─" * 45)
    lines.append("Network perimeter mapped and verified, Boss.")
    return "\n".join(lines)


def speed_and_latency_test() -> str:
    """
    Measures latency to primary DNS targets (Cloudflare 1.1.1.1, Google 8.8.8.8)
    and estimates download throughput via high-speed HTTP chunk download.
    """
    lines = ["⚡ NETWORK PERFORMANCE & LATENCY ANALYSIS", "─" * 45]

    # 1. Latency test
    endpoints = [
        ("Cloudflare DNS", "1.1.1.1"),
        ("Google DNS", "8.8.8.8"),
    ]

    for name, ip in endpoints:
        try:
            if _OS == "Windows":
                cmd = ["ping", "-n", "3", "-w", "1000", ip]
            else:
                cmd = ["ping", "-c", "3", ip]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=6, **_WIN_HIDE)
            # Find average latency from output
            match = re.search(r"Average = (\d+)ms", res.stdout, re.IGNORECASE)
            if not match:
                match = re.search(r"avg = [\d.]+/([\d.]+)/", res.stdout, re.IGNORECASE)
            
            if match:
                avg_ms = match.group(1)
                lines.append(f"• Latency to {name} ({ip}): {avg_ms} ms")
            else:
                lines.append(f"• Latency to {name} ({ip}): Responded (normal)")
        except Exception:
            lines.append(f"• Latency to {name} ({ip}): Unreachable or timed out")

    # 2. Throughput test (Download 10MB chunk from Cloudflare CDN)
    if _REQUESTS:
        try:
            test_url = "https://speed.cloudflare.com/__down?bytes=10000000"  # 10 MB
            t0 = time.time()
            resp = requests.get(test_url, timeout=10, stream=True)
            total_bytes = 0
            if resp.status_code == 200:
                for chunk in resp.iter_content(chunk_size=65536):
                    total_bytes += len(chunk)
                    if time.time() - t0 > 5.0:  # Cap test at 5 seconds
                        break
                elapsed = time.time() - t0
                if elapsed > 0.1 and total_bytes > 0:
                    mbps = (total_bytes * 8) / (elapsed * 1_000_000)
                    lines.append(f"• Effective Download Throughput: {mbps:.2f} Mbps ({total_bytes / (1024*1024):.1f} MB in {elapsed:.2f}s)")
        except Exception as e:
            lines.append(f"• Throughput benchmark skipped: {e}")

    lines.append("─" * 45)
    lines.append("Diagnostic complete, Boss. Bandwidth and latency verified.")
    return "\n".join(lines)


def port_scan(target: str = "localhost", ports: list[int] | None = None) -> str:
    """
    Scans specified or standard ports on a target IP or domain to detect open services.
    """
    host = (target or "localhost").strip()
    try:
        resolved_ip = socket.gethostbyname(host)
    except Exception as e:
        return f"Failed to resolve host '{host}': {e}"

    scan_ports = ports or list(_COMMON_PORTS.keys())
    open_ports: list[tuple[int, str]] = []

    def _check_port(port: int):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.4)
            if s.connect_ex((resolved_ip, port)) == 0:
                service = _COMMON_PORTS.get(port, "Unknown Service")
                open_ports.append((port, service))

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
        executor.map(_check_port, scan_ports)

    open_ports.sort(key=lambda x: x[0])

    lines = [
        f"🔍 PORT SURVEILLANCE — Target: {host} ({resolved_ip})",
        f"Scanned {len(scan_ports)} ports.",
        "─" * 40,
    ]

    if not open_ports:
        lines.append("No open ports detected in the tested range. The target is hardened or filtered.")
    else:
        lines.append(f"Discovered {len(open_ports)} listening ports:")
        for port, service in open_ports:
            lines.append(f"  • Port {port:<5} [{service}] — OPEN")

    lines.append("─" * 40)
    return "\n".join(lines)


def get_public_ip_info() -> str:
    """Retrieve external public IP, ISP provider, and geolocation telemetry."""
    if not _REQUESTS:
        return "Network requests library is not available."

    try:
        resp = requests.get("https://ipapi.co/json/", timeout=5)
        if resp.status_code == 200:
            d = resp.json()
            return (
                f"🌍 EXTERNAL NETWORK TELEMETRY:\n"
                f"• Public IP:    {d.get('ip', 'Unknown')}\n"
                f"• ISP / Org:    {d.get('org', 'Unknown')}\n"
                f"• Location:     {d.get('city', '')}, {d.get('region', '')}, {d.get('country_name', '')}\n"
                f"• Timezone:     {d.get('timezone', 'Unknown')}\n"
                f"• ASN:          {d.get('asn', 'Unknown')}"
            )
        # Fallback to ipify
        ip_resp = requests.get("https://api64.ipify.org?format=json", timeout=4)
        if ip_resp.status_code == 200:
            return f"Public IP: {ip_resp.json().get('ip', 'Unknown')}"
        return "Unable to resolve public IP info."
    except Exception as e:
        return f"Public IP query failed: {e}"


def get_wifi_diagnostics() -> str:
    """Retrieve Wi-Fi adapter telemetry, signal strength, SSID, and cipher across Windows, macOS, and Linux."""
    if _OS == "Windows":
        try:
            res = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=4, **_WIN_HIDE)
            output = res.stdout or ""
            if not output.strip() or "There is no wireless interface" in output:
                return "No wireless interface detected on this workstation."

            fields: dict[str, str] = {}
            for line in output.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k_clean = k.strip()
                    v_clean = v.strip()
                    if k_clean:
                        fields[k_clean] = v_clean

            lines = [
                "📡 WI-FI ADAPTER TELEMETRY (Windows):",
                f"• SSID:           {fields.get('SSID', 'Disconnected')}",
                f"• Signal Quality: {fields.get('Signal', 'N/A')}",
                f"• Radio Type:     {fields.get('Radio type', 'N/A')}",
                f"• Channel:        {fields.get('Channel', 'N/A')}",
                f"• Receive Rate:   {fields.get('Receive rate (Mbps)', 'N/A')} Mbps",
                f"• Transmit Rate:  {fields.get('Transmit rate (Mbps)', 'N/A')} Mbps",
                f"• State:          {fields.get('State', 'N/A')}",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"Wi-Fi diagnostic failed: {e}"

    elif _OS == "Darwin":
        try:
            airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
            if os.path.exists(airport_path):
                res = subprocess.run([airport_path, "-I"], capture_output=True, text=True, timeout=4)
                fields = dict(re.findall(r"\s*([^:]+):\s*(.+)", res.stdout or ""))
                return "\n".join([
                    "📡 WI-FI ADAPTER TELEMETRY (macOS):",
                    f"• SSID:           {fields.get('SSID', 'Disconnected')}",
                    f"• BSSID:          {fields.get('BSSID', 'N/A')}",
                    f"• Signal (RSSI):  {fields.get('agrCtlRSSI', 'N/A')} dBm",
                    f"• Noise:          {fields.get('agrCtlNoise', 'N/A')} dBm",
                    f"• Channel:        {fields.get('channel', 'N/A')}",
                    f"• Transmit Rate:  {fields.get('lastTxRate', 'N/A')} Mbps",
                    f"• Security:       {fields.get('link auth', 'N/A')}",
                ])
            res = subprocess.run(["networksetup", "-getairportnetwork", "en0"], capture_output=True, text=True, timeout=3)
            return f"📡 WI-FI (macOS): {res.stdout.strip()}"
        except Exception as e:
            return f"macOS Wi-Fi diagnostic failed: {e}"

    else:
        # Linux
        try:
            res = subprocess.run(["nmcli", "-t", "-f", "active,ssid,bssid,signal,chan,security", "dev", "wifi"], capture_output=True, text=True, timeout=4)
            for line in (res.stdout or "").splitlines():
                parts = line.split(":")
                if parts and parts[0] == "yes":
                    ssid = parts[1] if len(parts) > 1 else "Unknown"
                    bssid = parts[2] if len(parts) > 2 else "N/A"
                    signal = parts[3] if len(parts) > 3 else "N/A"
                    chan = parts[4] if len(parts) > 4 else "N/A"
                    sec = parts[5] if len(parts) > 5 else "N/A"
                    return "\n".join([
                        "📡 WI-FI ADAPTER TELEMETRY (Linux):",
                        f"• SSID:           {ssid}",
                        f"• BSSID:          {bssid}",
                        f"• Signal Quality: {signal}%",
                        f"• Channel:        {chan}",
                        f"• Security:       {sec}",
                    ])
            res = subprocess.run(["iwconfig"], capture_output=True, text=True, timeout=3)
            return f"📡 WI-FI (Linux iwconfig):\n{res.stdout[:300]}"
        except Exception as e:
            return f"Linux Wi-Fi diagnostic failed: {e}"


def network_scanner(parameters: dict, player=None, **kwargs) -> str:
    """Main entrypoint for network_scanner tool."""
    action = (parameters.get("action") or "scan_lan").lower().strip()
    target = parameters.get("target") or "localhost"
    ports_input = parameters.get("ports")

    if player:
        try:
            player.write_log(f"[Network] Executing {action} (Target: {target})")
        except Exception:
            pass

    try:
        if action in ("scan", "scan_lan", "devices", "lan", "perimeter"):
            quick = bool(parameters.get("quick", True))
            return scan_lan(quick=quick)

        elif action in ("speedtest", "speed", "latency", "ping"):
            return speed_and_latency_test()

        elif action in ("port_scan", "ports", "services"):
            parsed_ports = None
            if isinstance(ports_input, list):
                parsed_ports = [int(p) for p in ports_input if str(p).isdigit()]
            elif isinstance(ports_input, str) and ports_input:
                parsed_ports = [int(p.strip()) for p in ports_input.split(",") if p.strip().isdigit()]
            return port_scan(target=target, ports=parsed_ports)

        elif action in ("public_ip", "ip", "external", "geo"):
            return get_public_ip_info()

        elif action in ("wifi", "wifi_info", "wireless", "signal"):
            return get_wifi_diagnostics()

        elif action in ("audit", "security", "security_posture", "posture", "listening_ports", "listening", "ssl", "ssl_audit", "dns", "dns_audit", "interfaces", "connections"):
            try:
                from actions.network_auditor import network_auditor as auditor_func
                return auditor_func(parameters, player=player, **kwargs)
            except Exception as ae:
                return f"Network audit delegation failed: {ae}"

        else:
            return (
                f"Unknown network action '{action}'. "
                "Available actions: scan_lan, speedtest, port_scan, public_ip, wifi_info, audit, listening_ports, ssl_audit, dns_audit, interfaces, connections."
            )
    except Exception as e:
        return f"Network Sentinel encounter error: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "network_scanner",
    "description": (
        "Network Sentinel, LAN Overlord & Infrastructure Auditor. Scans local network perimeter for all connected devices (IP, MAC, hostnames), "
        "tests bandwidth speed and latency (Cloudflare/Google ping & throughput), scans open ports/services, audits local listening ports & processes, "
        "inspects SSL/TLS certificates & ciphers, benchmarks DNS resolvers, inspects network adapter MTU/IP telemetry, and evaluates overall security posture. "
        "Use whenever user asks to scan Wi-Fi, check connected devices, test internet speed, audit ports, check SSL certificates, or inspect network security."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "scan_lan (discover connected devices) | speedtest (latency & download speed) | port_scan (scan open ports on target) | listening_ports (audit local open ports & PIDs) | ssl_audit (inspect SSL/TLS cert & cipher) | dns_audit (benchmark DNS resolvers & records) | interfaces (adapter & gateway audit) | security_posture (master security score) | public_ip (external IP info) | wifi_info (Wi-Fi diagnostics)"
            },
            "target": {
                "type": "STRING",
                "description": "Target hostname, IP, or domain for port_scan, ssl_audit, or dns_audit (e.g. 'localhost', 'google.com', '192.168.1.1'). Default: 'localhost'"
            },
            "ports": {
                "type": "STRING",
                "description": "Optional comma-separated port numbers for port_scan (e.g. '80,443,8000,11434')."
            },
            "quick": {
                "type": "BOOLEAN",
                "description": "For scan_lan: true for fast scan (first 35 IPs), false for full /24 sweep. Default: true."
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": network_scanner,
}
