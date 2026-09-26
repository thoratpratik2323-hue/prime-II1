"""
Application control: launch and close common Windows applications.

Launch strategy is layered for robustness:
  1. Try a known executable / shell verb (fastest, most reliable).
  2. Fall back to the Windows "where"/App Paths lookup via `start`.

Closing uses taskkill on the matching process image name, with a graceful
grace period so apps can save work.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from typing import Any, Dict

from .registry import ToolError, register

# Canonical app key -> (launch_command, kind)
import re

APP_COMMANDS: Dict[str, Dict[str, str]] = {
    "notepad": {"exe": "notepad.exe", "image": "notepad.exe", "label": "Notepad"},
    "chrome": {"exe": "chrome.exe", "image": "chrome.exe", "label": "Google Chrome"},
    "edge": {"exe": "msedge.exe", "image": "msedge.exe", "label": "Microsoft Edge"},
    "vscode": {"exe": "code.cmd", "image": "Code.exe", "label": "Visual Studio Code"},
    "calculator": {"shell": "calc", "image": "CalculatorApp.exe", "label": "Calculator"},
    "calc": {"shell": "calc", "image": "CalculatorApp.exe", "label": "Calculator"},
    "file explorer": {"shell": "explorer", "image": "explorer.exe", "label": "File Explorer"},
    "explorer": {"shell": "explorer", "image": "explorer.exe", "label": "File Explorer"},
    "task manager": {"shell": "taskmgr", "image": "Taskmgr.exe", "label": "Task Manager"},
    "taskmanager": {"shell": "taskmgr", "image": "Taskmgr.exe", "label": "Task Manager"},
    "settings": {"uwp": "ms-settings:", "image": "SystemSettings.exe", "label": "Settings"},
    "command prompt": {"exe": "cmd.exe", "image": "cmd.exe", "label": "Command Prompt"},
    "cmd": {"exe": "cmd.exe", "image": "cmd.exe", "label": "Command Prompt"},
    "terminal": {"exe": "wt.exe", "image": "WindowsTerminal.exe", "label": "Windows Terminal"},
    "powershell": {"exe": "powershell.exe", "image": "powershell.exe", "label": "PowerShell"},
    "wordpad": {"shell": "write", "image": "wordpad.exe", "label": "WordPad"},
    "paint": {"shell": "mspaint", "image": "mspaint.exe", "label": "Paint"},
    "snipping tool": {"uwp": "ms-screenclip:", "image": "ScreenClippingHost.exe", "label": "Snipping Tool"},
    "whatsapp": {"uwp": "whatsapp:", "image": "WhatsApp.Root.exe", "label": "WhatsApp"},
}

NATIVE_OS_APPS = set(APP_COMMANDS.keys()) | {"code", "vs code", "visual studio code"}


def _resolve_app(key: str) -> Dict[str, str]:
    raw = (key or "").strip()
    norm = raw.lower()

    # Clean out filler words like 'open', 'app', 'karo', 'kholo', 'please'
    cleaned = re.sub(r'\b(open|launch|start|kholo|khol|chalao|karo|app|application|please|the)\b', '', norm, flags=re.IGNORECASE).strip()
    if cleaned:
        norm = cleaned

    # Check if this is a known web app or website (User preference: open in browser)
    try:
        from .tools_websites import SITE_URLS
        if norm in SITE_URLS:
            return {"kind": "url", "url": SITE_URLS[norm], "label": norm.title()}
        if "://" in norm or norm.startswith("www.") or any(norm.endswith(ext) for ext in (".com", ".org", ".net", ".io", ".ai", ".in", ".co", ".app", ".dev")):
            return {"kind": "url", "url": norm, "label": norm.title()}
    except Exception:
        pass

    # Allow loose aliases for OS tools
    aliases = {
        "code": "vscode",
        "visual studio code": "vscode",
        "vs code": "vscode",
        "google chrome": "chrome",
        "chrome browser": "chrome",
        "browser": "chrome",
        "web browser": "chrome",
        "microsoft edge": "edge",
        "calc": "calculator",
        "settings app": "settings",
        "file explorer": "file explorer",
        "windows explorer": "file explorer",
    }
    if norm in aliases and aliases[norm] in APP_COMMANDS:
        return APP_COMMANDS[aliases[norm]]

    if norm in APP_COMMANDS:
        return APP_COMMANDS[norm]

    # Check if executable exists in PATH
    resolved_exe = shutil.which(norm) or shutil.which(f"{norm}.exe")
    if resolved_exe and norm in NATIVE_OS_APPS:
        exe_name = re.sub(r"[/\\]+", "/", resolved_exe).split("/")[-1]
        return {"exe": exe_name, "image": exe_name, "label": raw.title()}

    # All other apps open in browser per user preference
    web_target = f"https://www.{norm}.com"
    return {"kind": "url", "url": web_target, "label": raw.title()}


def _launch(spec: Dict[str, str]) -> None:
    try:
        if spec.get("kind") == "url":
            from .tools_websites import open_url
            open_url(spec["url"])
            return

        if "exe" in spec:
            exe = spec["exe"]
            # Check if resolved in PATH
            resolved = shutil.which(exe)
            if resolved and not resolved.lower().endswith((".cmd", ".bat")):
                subprocess.Popen(
                    [resolved],
                    shell=False,
                    close_fds=True,
                    creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                    | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                )
            else:
                # Windows App Paths or Shell verb launch
                subprocess.Popen(f'start "" "{exe}"', shell=True)
        elif "shell" in spec:
            subprocess.Popen(f'start "" {spec["shell"]}', shell=True)
        elif "uwp" in spec:
            subprocess.Popen(f'start "" {spec["uwp"]}', shell=True)
        else:
            raise ToolError(f"App spec for {spec.get('label')} is incomplete.")
    except Exception as e:  # noqa: BLE001
        raise ToolError(f"Could not launch {spec.get('label')}: {e}") from e


@register("openApplication")
def open_application(args: Dict[str, Any]) -> Dict[str, Any]:
    name = args.get("name") or args.get("application")
    if not name:
        raise ToolError("Parameter 'name' (application name) is required.")
    spec = _resolve_app(str(name))
    _launch(spec)
    if spec.get("kind") == "url":
        return {"result": f"Opened {spec['label']} in web browser ({spec['url']})."}
    return {"result": f"{spec['label']} opened."}


@register("closeApplication")
def close_application(args: Dict[str, Any]) -> Dict[str, Any]:
    name = args.get("name") or args.get("application")
    force = bool(args.get("force", False))
    if not name:
        raise ToolError("Parameter 'name' (application name) is required.")
    spec = _resolve_app(str(name))
    if spec.get("kind") == "url":
        return {"result": f"'{spec.get('label', name)}' is a web application. Use closeWindow to close its browser tab."}
    image = spec.get("image") or spec.get("exe") or f"{name}.exe"
    if not image.lower().endswith(".exe") and not "." in image:
        image = f"{image}.exe"
    # Graceful close first (WM_CLOSE via taskkill), then force if requested.
    graceful_flag = "" if force else ""
    force_flag = " /F" if force else ""
    try:
        # taskkill returns non-zero if the process isn't running — that's fine.
        subprocess.run(
            f'taskkill /IM "{image}"{graceful_flag}{force_flag}',
            shell=True,
            capture_output=True,
            timeout=10,
        )
    except Exception as e:  # noqa: BLE001
        raise ToolError(f"Could not close {spec['label']}: {e}") from e
    # Give the OS a moment to actually tear it down.
    time.sleep(0.2)
    return {"result": f"Closed {spec['label']}."}


__all__ = ["open_application", "close_application", "APP_COMMANDS"]
