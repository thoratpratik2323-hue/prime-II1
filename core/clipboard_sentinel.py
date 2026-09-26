"""
Intelligent Clipboard Memory & Auto-Explainer Sentinel for Prime AI.
Maintains a searchable history buffer of copied snippets, classifies content types,
and provides instant voice-ready explanations or formatting for code, tracebacks, and JSON.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("prime.clipboard_sentinel")


def get_current_clipboard() -> str:
    """Safely fetch current text from Windows clipboard."""
    try:
        import pyperclip
        return pyperclip.paste() or ""
    except Exception:
        try:
            import ctypes
            from ctypes import wintypes
            CF_UNICODETEXT = 13
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            if not user32.OpenClipboard(None):
                return ""
            try:
                handle = user32.GetClipboardData(CF_UNICODETEXT)
                if not handle:
                    return ""
                kernel32.GlobalLock.restype = ctypes.c_wchar_p
                ptr = kernel32.GlobalLock(handle)
                text = str(ptr) if ptr else ""
                kernel32.GlobalUnlock(handle)
                return text
            finally:
                user32.CloseClipboard()
        except Exception as e:
            log.debug("Clipboard reading error: %s", e)
            return ""


def set_current_clipboard(text: str) -> bool:
    """Safely set text into Windows clipboard."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        return False


class ClipboardSentinel:
    """Tracks clipboard events and provides contextual diagnosis and auto-formatting."""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.history: List[Dict[str, Any]] = []

    def classify_snippet(self, text: str) -> str:
        """Categorize clipboard content into structured types."""
        t = text.strip()
        if not t:
            return "empty"

        if re.search(r"Traceback \(most recent call last\):", t) or "Error:" in t or "Exception:" in t:
            return "traceback"

        if (t.startswith("{") and t.endswith("}")) or (t.startswith("[") and t.endswith("]")):
            try:
                json.loads(t)
                return "json"
            except Exception:
                pass

        if re.match(r"^https?://[^\s]+$", t):
            return "url"

        if any(kw in t for kw in ["def ", "class ", "import ", "from ", "elif ", "return "]) and ":" in t:
            return "python"

        if any(kw in t for kw in ["const ", "let ", "var ", "function", "console.log", "=>"]):
            return "javascript"

        if re.match(r"^(pip|npm|git|docker|curl|python|pnpm|yarn)\s+", t):
            return "shell_command"

        return "text"

    def record_clip(self, text: str) -> Optional[Dict[str, Any]]:
        """Record a newly copied snippet into the history buffer."""
        t = text.strip()
        if not t:
            return None

        # Deduplicate if matches previous clip
        if self.history and self.history[-1]["text"] == t:
            return self.history[-1]

        clip_type = self.classify_snippet(t)
        preview = t[:120].replace("\n", " ") + ("..." if len(t) > 120 else "")
        entry = {
            "id": f"clip_{int(time.time())}_{len(self.history)}",
            "timestamp": datetime.now().isoformat(),
            "time_str": datetime.now().strftime("%I:%M:%S %p"),
            "type": clip_type,
            "length": len(t),
            "preview": preview,
            "text": t
        }
        self.history.append(entry)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        return entry

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return latest items from clipboard buffer (newest first)."""
        current = get_current_clipboard()
        if current:
            self.record_clip(current)
        return self.history[-limit:][::-1]

    def explain_snippet(self, text: str = "") -> Dict[str, Any]:
        """Explain the contents of the given text or the active clipboard."""
        target = text.strip() or get_current_clipboard().strip()
        if not target:
            return {"ok": False, "error": "Clipboard is empty."}

        self.record_clip(target)
        snippet_type = self.classify_snippet(target)

        # 1. Traceback Analysis
        if snippet_type == "traceback":
            match = re.search(r"(\w+Error|\w+Exception):\s*(.*)", target)
            err_name = match.group(1) if match else "Error"
            err_desc = match.group(2) if match else "Unspecified traceback exception"
            explanation = (
                f"🚨 **Traceback Detected: {err_name}**\n"
                f"• Details: {err_desc}\n"
                f"• Tip: Check module imports, variable definitions, or type constraints on the line indicated."
            )
            return {
                "ok": True,
                "type": "traceback",
                "error_name": err_name,
                "explanation": explanation,
                "snippet": target[:300]
            }

        # 2. JSON Validation and formatting
        if snippet_type == "json":
            try:
                parsed = json.loads(target)
                keys = list(parsed.keys()) if isinstance(parsed, dict) else f"Array of {len(parsed)} items"
                return {
                    "ok": True,
                    "type": "json",
                    "explanation": f"Valid JSON data containing: {keys}.",
                    "snippet": target[:200]
                }
            except Exception as e:
                return {
                    "ok": False,
                    "type": "invalid_json",
                    "explanation": f"Malformed JSON: {e}",
                    "snippet": target[:200]
                }

        # 3. Python Code Analysis
        if snippet_type == "python":
            lines = target.splitlines()
            defs = [l.strip() for l in lines if l.strip().startswith("def ") or l.strip().startswith("class ")]
            explanation = (
                f"🐍 **Python Code Block** ({len(lines)} lines)\n"
                f"• Declared symbols: {', '.join(defs[:4]) if defs else 'Script statements'}"
            )
            return {
                "ok": True,
                "type": "python",
                "explanation": explanation,
                "snippet": target[:300]
            }

        # 4. URL
        if snippet_type == "url":
            return {
                "ok": True,
                "type": "url",
                "explanation": f"Web URL: {target}",
                "snippet": target
            }

        # 5. General text
        return {
            "ok": True,
            "type": "text",
            "explanation": f"Plain text ({len(target)} chars): {target[:120]}...",
            "snippet": target[:200]
        }

    def format_json_clip(self, text: str = "") -> Dict[str, Any]:
        """Parse, pretty-print, and write JSON back to clipboard."""
        target = text.strip() or get_current_clipboard().strip()
        if not target:
            return {"ok": False, "error": "Clipboard is empty."}

        try:
            parsed = json.loads(target)
            formatted = json.dumps(parsed, indent=2)
            set_current_clipboard(formatted)
            self.record_clip(formatted)
            return {
                "ok": True,
                "message": "JSON formatted and copied back to clipboard.",
                "formatted": formatted[:300] + ("..." if len(formatted) > 300 else "")
            }
        except Exception as e:
            return {"ok": False, "error": f"Failed to parse JSON: {e}"}


_CLIPBOARD_INSTANCE: Optional[ClipboardSentinel] = None


def get_clipboard_sentinel() -> ClipboardSentinel:
    """Singleton getter for clipboard sentinel."""
    global _CLIPBOARD_INSTANCE
    if _CLIPBOARD_INSTANCE is None:
        _CLIPBOARD_INSTANCE = ClipboardSentinel()
    return _CLIPBOARD_INSTANCE


def get_clipboard_history(limit: int = 10) -> Dict[str, Any]:
    """Retrieve recent clipboard history."""
    items = get_clipboard_sentinel().get_history(limit)
    return {"ok": True, "total": len(items), "history": items}


def explain_clipboard_snippet(text: str = "") -> Dict[str, Any]:
    """Explain what is currently on the clipboard or in the given text snippet."""
    return get_clipboard_sentinel().explain_snippet(text)


def format_clipboard_json(text: str = "") -> Dict[str, Any]:
    """Format and prettify JSON text on the clipboard."""
    return get_clipboard_sentinel().format_json_clip(text)
