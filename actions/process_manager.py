"""
process_manager.py — Process and task manager action for Ultron AI.
Inspect, list, search, and terminate processes on the PC.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import os
import platform
import subprocess
import psutil

_OS = platform.system()
_WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW} if _OS == "Windows" else {}


def list_top_processes(limit: int = 10, sort_by: str = "memory") -> str:
    """Return a formatted table of top running processes by CPU or Memory."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = p.info
            if info and info.get("name"):
                procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    key = "cpu_percent" if sort_by.lower() == "cpu" else "memory_percent"
    top = sorted(procs, key=lambda x: x.get(key) or 0.0, reverse=True)[:limit]

    lines = [f"Top {len(top)} processes (sorted by {sort_by.upper()}):"]
    for p in top:
        pid = p.get("pid", 0)
        name = p.get("name", "unknown")
        cpu = p.get("cpu_percent") or 0.0
        mem = p.get("memory_percent") or 0.0
        lines.append(f"• {name} (PID: {pid}) — RAM: {mem:.1f}% | CPU: {cpu:.1f}%")
    return "\n".join(lines)


def find_processes(query: str) -> str:
    """Search for running processes matching a query name."""
    q = (query or "").lower().strip()
    if not q:
        return "No search query provided."

    matches = []
    for p in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            name = (p.info.get("name") or "").lower()
            if q in name:
                matches.append(f"• {p.info.get('name')} (PID: {p.info.get('pid')}) — RAM: {p.info.get('memory_percent', 0):.1f}%")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not matches:
        return f"No running processes matching '{query}' found."
    return f"Found {len(matches)} process(es) matching '{query}':\n" + "\n".join(matches[:15])


def kill_process(target: str | int) -> str:
    """Terminate process by name or PID."""
    target_str = str(target or "").strip()
    if not target_str:
        return "No process name or PID specified to terminate."

    # If numeric PID
    if target_str.isdigit():
        pid = int(target_str)
        try:
            p = psutil.Process(pid)
            name = p.name()
            p.terminate()
            p.wait(timeout=3)
            return f"Successfully terminated process {name} (PID {pid})."
        except psutil.TimeoutExpired:
            p.kill()
            return f"Force killed process (PID {pid})."
        except psutil.NoSuchProcess:
            return f"Process with PID {pid} was not found."
        except Exception as e:
            return f"Failed to terminate PID {pid}: {e}"

    # Target by process name
    q = target_str.lower()
    if not q.endswith(".exe") and _OS == "Windows":
        q_exe = q + ".exe"
    else:
        q_exe = q

    killed = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            name = (p.info.get("name") or "").lower()
            if name == q or name == q_exe or q in name:
                pid = p.info.get("pid")
                proc = psutil.Process(pid)
                proc.terminate()
                killed.append(f"{p.info.get('name')} (PID {pid})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not killed:
        return f"No running process matching '{target_str}' was found."
    return f"Terminated {len(killed)} process(es): {', '.join(killed)}."


def focus_window_by_name(title_or_name: str) -> str:
    """Bring a window to the front by title or app name."""
    t = (title_or_name or "").strip()
    if not t:
        return "No window title specified."
    if _OS == "Windows":
        cmd = f"""
        Add-Type @"
            using System;
            using System.Runtime.InteropServices;
            public class WinApi {{
                [DllImport("user32.dll")]
                [return: MarshalAs(UnmanagedType.Bool)]
                public static extern bool SetForegroundWindow(IntPtr hWnd);
                [DllImport("user32.dll")]
                public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
            }}
"@
        $proc = Get-Process | Where-Object {{ $_.MainWindowTitle -like '*{t}*' -or $_.ProcessName -like '*{t}*' }} | Select-Object -First 1
        if ($proc -and $proc.MainWindowHandle -ne 0) {{
            [WinApi]::ShowWindow($proc.MainWindowHandle, 9)
            [WinApi]::SetForegroundWindow($proc.MainWindowHandle)
            Write-Output "FOCUSED"
        }} else {{
            Write-Output "NOT_FOUND"
        }}
        """
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=5, **_WIN_HIDE
            )
            if "FOCUSED" in (res.stdout or ""):
                return f"Window '{t}' brought to foreground."
            return f"Could not find an active window matching '{t}'."
        except Exception as e:
            return f"Focus failed: {e}"
    return f"Window focusing is not supported on {_OS}."


def process_manager_handler(parameters: dict, **kwargs) -> str:
    action = str(parameters.get("action", "list")).lower().strip()
    target = parameters.get("target") or parameters.get("name") or parameters.get("process") or ""
    limit = int(parameters.get("limit", 10))
    sort_by = str(parameters.get("sort_by", "memory")).lower().strip()

    if action in ("list", "top", "show"):
        return list_top_processes(limit=limit, sort_by=sort_by)
    elif action in ("kill", "terminate", "stop", "close"):
        return kill_process(target)
    elif action in ("find", "search", "check"):
        return find_processes(target)
    elif action in ("focus", "foreground", "switch_to"):
        return focus_window_by_name(target)
    else:
        return f"Unknown action '{action}'. Supported actions: list, kill, find, focus."


TOOL = {
    "name": "process_manager",
    "description": (
        "Inspects, lists, and manages running processes on the PC. "
        "Use when user asks to: list running tasks/processes, find what apps are using the most RAM/CPU, "
        "kill/close an app or process by name (e.g. 'kill chrome', 'close notepad', 'kill PID 1234'), "
        "search for a running process, or switch/bring a window to the front."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action to perform: 'list' (top processes), 'kill' (terminate process), 'find' (search processes), 'focus' (bring to front)"
            },
            "target": {
                "type": "STRING",
                "description": "Process name (e.g. 'chrome', 'notepad.exe'), PID (e.g. '1234'), or window title to focus"
            },
            "limit": {
                "type": "INTEGER",
                "description": "Number of processes to list (default: 10)"
            },
            "sort_by": {
                "type": "STRING",
                "description": "'memory' (default) or 'cpu'"
            }
        },
        "required": ["action"]
    },
    "handler": process_manager_handler
}
