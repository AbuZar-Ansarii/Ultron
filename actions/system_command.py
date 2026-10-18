"""
system_command.py — Run shell, PowerShell, and terminal commands on the computer.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import os
import platform
import subprocess
from typing import Optional

_OS = platform.system()
_WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW} if _OS == "Windows" else {}


def execute_system_command(command: str, shell_type: str = "powershell", timeout_secs: int = 20) -> str:
    """Execute a shell or PowerShell command and return captured output."""
    cmd = (command or "").strip()
    if not cmd:
        return "No command provided to execute."

    # Prevent obvious self-destructive accidental commands
    dangerous_keywords = ["format c:", "rmdir /s /q c:\\windows", "del /f /s /q c:\\windows"]
    for danger in dangerous_keywords:
        if danger in cmd.lower():
            return f"Command execution blocked: '{cmd}' contains a destructive system pattern."

    timeout = max(2, min(int(timeout_secs or 20), 60))
    shell_choice = (shell_type or "powershell").lower().strip()

    try:
        if _OS == "Windows":
            if shell_choice == "cmd":
                args = ["cmd.exe", "/c", cmd]
            else:
                args = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd]
        else:
            args = ["/bin/bash", "-c", cmd]

        res = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            **_WIN_HIDE
        )

        stdout = (res.stdout or "").strip()
        stderr = (res.stderr or "").strip()

        if res.returncode == 0:
            if not stdout and not stderr:
                return f"Command executed successfully (exit code 0, no output)."
            output = stdout or stderr
            if len(output) > 1500:
                output = output[:1500] + "\n... [output truncated for brevity]"
            return output
        else:
            err = stderr or stdout or f"Exit code {res.returncode}"
            if len(err) > 1200:
                err = err[:1200] + "... [truncated]"
            return f"Command failed (exit code {res.returncode}):\n{err}"

    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds: '{cmd}'"
    except Exception as e:
        return f"Execution error: {e}"


def system_command_handler(parameters: dict, **kwargs) -> str:
    cmd = parameters.get("command", "")
    shell_type = parameters.get("shell", "powershell")
    timeout = parameters.get("timeout", 20)
    return execute_system_command(cmd, shell_type=shell_type, timeout_secs=timeout)


TOOL = {
    "name": "system_command",
    "description": (
        "Executes a system shell / PowerShell / Command Prompt command directly on the PC. "
        "Use when user asks to run a command, ping a server, check network config (ipconfig), "
        "query disk usage, run git commands, install packages (pip, npm, winget), or execute CLI tools."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "command": {
                "type": "STRING",
                "description": "The exact command line string to run (e.g. 'ipconfig', 'ping 8.8.8.8 -n 4', 'dir', 'winget search vlc')"
            },
            "shell": {
                "type": "STRING",
                "description": "Shell to use: 'powershell' (default) or 'cmd'"
            },
            "timeout": {
                "type": "INTEGER",
                "description": "Timeout in seconds (default: 20, max: 60)"
            }
        },
        "required": ["command"]
    },
    "handler": system_command_handler
}
