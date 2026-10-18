"""
clipboard_control.py — Clipboard assistant for Ultron AI.
Read, copy to, or clear the system clipboard from voice commands.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False


def get_clipboard() -> str:
    if not _PYPERCLIP:
        return "pyperclip is not installed. Run: pip install pyperclip"
    try:
        text = pyperclip.paste()
        if not text:
            return "The clipboard is currently empty."
        if len(text) > 800:
            preview = text[:800] + "... [truncated]"
            return f"Clipboard content ({len(text)} characters):\n{preview}"
        return f"Clipboard content:\n{text}"
    except Exception as e:
        return f"Could not read clipboard: {e}"


def set_clipboard(text: str) -> str:
    if not _PYPERCLIP:
        return "pyperclip is not installed. Run: pip install pyperclip"
    try:
        val = str(text or "")
        pyperclip.copy(val)
        return f"Copied {len(val)} characters to clipboard."
    except Exception as e:
        return f"Could not copy to clipboard: {e}"


def clear_clipboard() -> str:
    if not _PYPERCLIP:
        return "pyperclip is not installed. Run: pip install pyperclip"
    try:
        pyperclip.copy("")
        return "Clipboard cleared."
    except Exception as e:
        return f"Could not clear clipboard: {e}"


def clipboard_control_handler(parameters: dict, **kwargs) -> str:
    action = str(parameters.get("action", "get")).lower().strip()
    text = parameters.get("text", "")

    if action in ("get", "read", "paste", "show", "view"):
        return get_clipboard()
    elif action in ("set", "copy", "write"):
        return set_clipboard(text)
    elif action in ("clear", "empty"):
        return clear_clipboard()
    else:
        return f"Unknown clipboard action: '{action}'. Use 'get', 'set', or 'clear'."


TOOL = {
    "name": "clipboard_control",
    "description": (
        "Controls the system clipboard. "
        "Use when the user asks: 'what is in my clipboard?', 'read my clipboard', "
        "'copy this to my clipboard', or 'clear my clipboard'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "'get' (read clipboard), 'set' (copy text to clipboard), 'clear' (empty clipboard)"
            },
            "text": {
                "type": "STRING",
                "description": "Text to copy to clipboard (required for 'set')"
            }
        },
        "required": ["action"]
    },
    "handler": clipboard_control_handler
}
