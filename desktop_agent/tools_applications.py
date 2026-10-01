"""
Application control: launch and close common Windows applications.

Launch strategy is layered for robustness:
  1. Try a known executable / shell verb (fastest, most reliable).
  2. Fall back to the Windows "where"/App Paths lookup via `start`.

Closing uses taskkill on the matching process image name, with a graceful
grace period so apps can save work.
"""

from __future__ import annotations

import os
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
    "spotify": {"exe": "Spotify.exe", "image": "Spotify.exe", "label": "Spotify"},
    "discord": {"exe": "Discord.exe", "image": "Discord.exe", "label": "Discord"},
    "telegram": {"exe": "Telegram.exe", "image": "Telegram.exe", "label": "Telegram"},
    "steam": {"exe": "steam.exe", "image": "steam.exe", "label": "Steam"},
    "vlc": {"exe": "vlc.exe", "image": "vlc.exe", "label": "VLC Media Player"},
    "firefox": {"exe": "firefox.exe", "image": "firefox.exe", "label": "Mozilla Firefox"},
    "word": {"exe": "WINWORD.EXE", "image": "WINWORD.EXE", "label": "Microsoft Word"},
    "excel": {"exe": "EXCEL.EXE", "image": "EXCEL.EXE", "label": "Microsoft Excel"},
    "powerpoint": {"exe": "POWERPNT.EXE", "image": "POWERPNT.EXE", "label": "Microsoft PowerPoint"},
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
    name = args.get("name") or args.get("application") or args.get("app") or args.get("target")
    force = bool(args.get("force", True))  # Default True on Windows so browsers/Electron apps close reliably
    if not name:
        from .tools_windows import close_window
        return close_window({})

    # 1. Clean out English/Hinglish action keywords and filler
    raw = str(name).strip()
    cleaned = re.sub(
        r'\b(close|exit|quit|kill|stop|terminate|band\s*karo|band\s*kar\s*do|hatao|khatam\s*karo|app|application|window|program|the|please)\b',
        '',
        raw,
        flags=re.IGNORECASE
    ).strip()
    target = cleaned if cleaned else raw
    key = target.lower()

    if not key or key in ("app", "application", "window", "this", "current", "active", "ye", "yeh", "is", "isko"):
        from .tools_windows import close_window
        return close_window({})


    # 2. Check canonical aliases
    aliases = {
        "google chrome": "chrome",
        "chrome browser": "chrome",
        "browser": "chrome",
        "web browser": "chrome",
        "internet": "chrome",
        "code": "vscode",
        "vs code": "vscode",
        "visual studio code": "vscode",
        "calc": "calculator",
        "calc.exe": "calculator",
        "taskmgr": "taskmanager",
        "task manager": "taskmanager",
        "explorer": "file explorer",
        "windows explorer": "file explorer",
    }
    resolved_key = aliases.get(key, key)

    # 3. Determine candidate process image names
    candidate_images = set()
    label = target.title()

    if resolved_key in APP_COMMANDS:
        spec = APP_COMMANDS[resolved_key]
        label = spec.get("label", label)
        if spec.get("image"):
            candidate_images.add(spec["image"].lower())
        if spec.get("exe"):
            candidate_images.add(spec["exe"].lower())

    # Add direct key variations
    if key.endswith(".exe"):
        candidate_images.add(key)
    else:
        candidate_images.add(f"{key}.exe")
        candidate_images.add(key)

    # 4. Search and terminate matching processes via psutil
    killed_count = 0
    matched_names = set()

    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                p_name = (proc.info['name'] or '').lower()
                p_exe = (proc.info['exe'] or '').lower()

                # Match against candidate images or key substring
                is_match = False
                if any(cand == p_name or (cand.endswith('.exe') and cand == p_name) for cand in candidate_images):
                    is_match = True
                elif key in p_name or (p_exe and key in os.path.basename(p_exe)):
                    # Avoid accidentally killing system processes
                    if p_name not in ("svchost.exe", "explorer.exe", "csrss.exe", "lsass.exe", "services.exe", "smss.exe", "system"):
                        is_match = True

                if is_match:
                    matched_names.add(proc.info['name'])
                    try:
                        proc.terminate()
                        killed_count += 1
                    except Exception:
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass

    # 5. Force kill tree via Windows taskkill if processes were found or for candidate images
    time.sleep(0.3)
    target_kill_images = set(matched_names)
    for c in candidate_images:
        if c.endswith(".exe"):
            target_kill_images.add(c)
        else:
            target_kill_images.add(f"{c}.exe")

    for img in target_kill_images:
        try:
            # /F (force) and /T (tree) ensures multi-process apps like Chrome, VSCode, Spotify close
            res = subprocess.run(
                f'taskkill /F /T /IM "{img}"',
                shell=True,
                capture_output=True,
                timeout=5,
            )
            if res.returncode == 0:
                killed_count += 1
        except Exception:
            pass

    # 6. Fallback: Close GUI window by title if process wasn't found by exe
    if killed_count == 0:
        try:
            import pygetwindow as gw
            windows = gw.getAllWindows()
            for w in windows:
                if w.title and key in w.title.lower():
                    w.close()
                    killed_count += 1
                    return {"result": f"Closed window '{w.title}'."}
        except Exception:
            pass

    if killed_count > 0:
        return {"result": f"Closed {label}."}

    return {"result": f"No running application found matching '{target}'."}


__all__ = ["open_application", "close_application", "APP_COMMANDS"]
