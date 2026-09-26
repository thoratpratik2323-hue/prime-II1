"""
Proactive Terminal Error Sentinel & Auto-Fix Interceptor for Prime AI.
Monitors command execution streams, analyzes tracebacks, identifies missing dependencies or port conflicts,
and generates auto-healing remediation commands.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

log = logging.getLogger("prime.terminal_sentinel")

# Common Python module to PyPI package mappings
MODULE_NAME_MAPPINGS: Dict[str, str] = {
    "cv2": "opencv-python",
    "PIL": "pillow",
    "sklearn": "scikit-learn",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "serial": "pyserial",
    "jwt": "pyjwt",
    "speech_recognition": "SpeechRecognition",
    "fitz": "PyMuPDF",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "xlsxwriter": "XlsxWriter",
    "Bio": "biopython",
    "google.generativeai": "google-generativeai",
    "openai": "openai",
    "groq": "groq",
}


class TerminalSentinel:
    """Interprets terminal errors, maps root causes, and recommends/executes auto-healing commands."""

    def __init__(self):
        self.history: List[Dict[str, Any]] = []

    def intercept_error(
        self,
        command: str,
        stderr: str,
        stdout: str = "",
        exit_code: int = 1
    ) -> Dict[str, Any]:
        """
        Analyze terminal command failure output and return structured diagnosis and auto-fix.
        """
        combined = f"{stderr}\n{stdout}".strip()
        analysis = self._diagnose(command, combined, exit_code)
        
        entry = {
            "command": command,
            "exit_code": exit_code,
            "diagnosis": analysis,
        }
        self.history.append(entry)
        return analysis

    def _diagnose(self, command: str, error_text: str, exit_code: int) -> Dict[str, Any]:
        # 1. Missing Python Module
        py_match = re.search(r"(?:ModuleNotFoundError|ImportError):\s*No module named ['\"]([^'\"]+)['\"]", error_text)
        if py_match:
            mod_raw = py_match.group(1).split(".")[0]
            pkg_name = MODULE_NAME_MAPPINGS.get(mod_raw, mod_raw)
            fix_cmd = f"pip install {pkg_name}"
            return {
                "detected": True,
                "error_type": "missing_python_module",
                "target": pkg_name,
                "summary": f"Python module '{mod_raw}' is missing.",
                "explanation": f"The script requires '{pkg_name}' which is not installed in the active Python environment.",
                "suggested_fix": f"Install via pip: {fix_cmd}",
                "auto_heal_command": fix_cmd,
                "can_auto_heal": True
            }

        # 2. Node / NPM missing package
        node_match = re.search(r"Cannot find module ['\"]([^'\"]+)['\"]", error_text)
        if node_match:
            pkg_name = node_match.group(1)
            fix_cmd = f"npm install {pkg_name}"
            return {
                "detected": True,
                "error_type": "missing_node_module",
                "target": pkg_name,
                "summary": f"Node module '{pkg_name}' is not found.",
                "explanation": f"Node.js runtime could not locate '{pkg_name}' in node_modules.",
                "suggested_fix": f"Install package: {fix_cmd}",
                "auto_heal_command": fix_cmd,
                "can_auto_heal": True
            }

        # 3. Port conflict (EADDRINUSE)
        port_match = re.search(r"(?:listen EADDRINUSE.*?:|port\s+)(\d{2,5})", error_text, re.IGNORECASE)
        if port_match:
            port = port_match.group(1)
            fix_cmd = f"Stop-Process -Id (Get-NetTCPConnection -LocalPort {port}).OwningProcess -Force"
            return {
                "detected": True,
                "error_type": "port_in_use",
                "target": port,
                "summary": f"Port {port} is already in use by another process.",
                "explanation": f"A service or process is currently holding port {port}.",
                "suggested_fix": f"Kill the conflicting process on port {port}.",
                "auto_heal_command": fix_cmd,
                "can_auto_heal": True
            }

        # 4. Git Lock file blocking operations
        if "index.lock" in error_text:
            fix_cmd = "Remove-Item -Force .git/index.lock"
            return {
                "detected": True,
                "error_type": "git_lock_error",
                "target": ".git/index.lock",
                "summary": "Git index lock file is preventing git operations.",
                "explanation": "A previous git process crashed or exited uncleanly leaving index.lock.",
                "suggested_fix": "Remove the stale .git/index.lock file.",
                "auto_heal_command": fix_cmd,
                "can_auto_heal": True
            }

        # 5. Permission Denied
        if "PermissionError" in error_text or "EACCES" in error_text:
            return {
                "detected": True,
                "error_type": "permission_denied",
                "target": "system",
                "summary": "Access or permission denied while executing command.",
                "explanation": "The current process lacks administrator privileges or the target file is locked.",
                "suggested_fix": "Run terminal as Administrator or check file locks.",
                "auto_heal_command": "",
                "can_auto_heal": False
            }

        # 6. Generic or undetected error
        return {
            "detected": False,
            "error_type": "unknown_terminal_error",
            "target": command,
            "summary": f"Command exited with code {exit_code}.",
            "explanation": error_text[:300] if error_text else "No stderr details provided.",
            "suggested_fix": "Review syntax or inspect logs.",
            "auto_heal_command": "",
            "can_auto_heal": False
        }

    def auto_heal(self, fix_command: str) -> Dict[str, Any]:
        """
        Safely execute the auto-healing remediation command.
        """
        if not fix_command or not fix_command.strip():
            return {"ok": False, "error": "No auto-heal command provided."}

        cmd_clean = fix_command.strip()
        log.info("Executing auto-heal command: %s", cmd_clean)
        try:
            res = subprocess.run(
                cmd_clean,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            ok = (res.returncode == 0)
            return {
                "ok": ok,
                "command": cmd_clean,
                "exit_code": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "message": "Auto-heal completed successfully." if ok else "Auto-heal command failed."
            }
        except Exception as e:
            log.error("Failed to run auto-heal: %s", e)
            return {"ok": False, "error": f"Failed to execute auto-heal: {e}"}


_SENTINEL_INSTANCE: Optional[TerminalSentinel] = None


def get_terminal_sentinel() -> TerminalSentinel:
    """Singleton getter for the terminal error sentinel."""
    global _SENTINEL_INSTANCE
    if _SENTINEL_INSTANCE is None:
        _SENTINEL_INSTANCE = TerminalSentinel()
    return _SENTINEL_INSTANCE


def intercept_terminal_error(command: str, stderr: str, stdout: str = "", exit_code: int = 1) -> Dict[str, Any]:
    """Inspect and generate an auto-fix for a terminal command error."""
    sentinel = get_terminal_sentinel()
    diagnosis = sentinel.intercept_error(command, stderr, stdout, exit_code)
    return {
        "ok": True,
        "diagnosis": diagnosis
    }
