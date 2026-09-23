"""
Windows auto-start management for Prime AI.

Configures automatic launch upon Windows boot via:
  1. Windows Registry HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\PrimeAI
  2. Windows User Startup Folder: %APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\PrimeAI.vbs

Launches Prime AI in the background with the 24/7 ambient microphone and voice engine active immediately upon login.
"""

from __future__ import annotations

import os
import shutil
import sys
from typing import Any, Dict

from .registry import ToolError, register

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "PrimeAI"
LAUNCHER_BAT = "start-prime.bat"
LAUNCHER_VBS = "start-prime-background.vbs"


def _project_root() -> str:
    """Return the Prime project root."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _launcher_bat_path() -> str:
    return os.path.join(_project_root(), LAUNCHER_BAT)


def _launcher_vbs_path() -> str:
    return os.path.join(_project_root(), LAUNCHER_VBS)


def _startup_folder() -> str:
    return os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")


def _startup_vbs_path() -> str:
    return os.path.join(_startup_folder(), "PrimeAI.vbs")


def _ensure_launchers_exist():
    """Ensure both batch and silent VBS launchers exist in the project root."""
    root = _project_root()
    bat_path = _launcher_bat_path()
    vbs_path = _launcher_vbs_path()

    if not os.path.isfile(bat_path):
        py_exe = sys.executable or "python"
        bat_content = f'@echo off\r\nchcp 65001 >nul\r\ncd /d "{root}"\r\n"{py_exe}" prime.py\r\n'
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

    if not os.path.isfile(vbs_path):
        vbs_content = f'Set WshShell = CreateObject("WScript.Shell")\r\nWshShell.Run "cmd /c ""{bat_path}""", 0, False\r\n'
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_content)


def _is_windows() -> bool:
    return sys.platform.startswith("win") or os.name == "nt"


# --- Registry helpers ---

def _open_run_key(write: bool = True):
    if not _is_windows():
        raise ToolError("Auto-start is only supported on Windows.")
    import winreg
    flags = (winreg.KEY_SET_VALUE | winreg.KEY_READ) if write else winreg.KEY_READ
    return winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, flags)


def _read_run_value() -> str | None:
    if not _is_windows():
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return str(value)
    except Exception:
        return None


# --- Tools ---

@register("enableAutoStart")
def enable_auto_start(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Enable Prime AI auto-start on Windows boot via Registry and Startup folder."""
    if not _is_windows():
        raise ToolError("Auto-start is only supported on Windows.")

    _ensure_launchers_exist()
    vbs_path = _launcher_vbs_path()
    command = f'wscript.exe "{vbs_path}"'

    # 1. Registry HKCU Run Key (Standard Windows auto-start)
    try:
        import winreg
        with _open_run_key(write=True) as key:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command)
    except Exception as e:
        raise ToolError(f"Could not write startup registry entry: {e}") from e

    # 2. Clean up any legacy Startup folder entry to prevent duplicate instances
    startup_vbs = _startup_vbs_path()
    try:
        if os.path.isfile(startup_vbs):
            os.remove(startup_vbs)
    except Exception:
        pass

    return {
        "result": "Prime AI auto-start ENABLED via Registry Run key. Prime will start automatically whenever your PC boots up with 24/7 mic active.",
        "enabled": True,
        "launcher": vbs_path,
        "registry_key": f"HKCU\\{RUN_KEY_PATH}\\{VALUE_NAME}",
        "startup_folder_entry": None,
    }


@register("disableAutoStart")
def disable_auto_start(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Disable Prime AI auto-start on Windows boot."""
    if not _is_windows():
        raise ToolError("Auto-start is only supported on Windows.")

    # 1. Remove Registry Key
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except Exception:
        pass

    # 2. Remove Startup Folder File
    startup_vbs = _startup_vbs_path()
    if os.path.isfile(startup_vbs):
        try:
            os.remove(startup_vbs)
        except Exception:
            pass

    return {
        "result": "Prime AI auto-start DISABLED. Prime will no longer start on boot.",
        "enabled": False,
    }


@register("getAutoStartStatus")
def get_auto_start_status(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Check if Prime AI auto-start is currently enabled."""
    if not _is_windows():
        return {"result": "Auto-start is only supported on Windows.", "enabled": False}

    reg_val = _read_run_value()
    startup_vbs = _startup_vbs_path()
    vbs_exists = os.path.isfile(startup_vbs)

    enabled = (reg_val is not None) or vbs_exists
    msg = (
        "Prime AI Auto-Start is ENABLED (PC start hote hi Prime automatically launch hoga)."
        if enabled
        else "Prime AI Auto-Start is DISABLED."
    )
    return {
        "result": msg,
        "enabled": enabled,
        "registry_target": reg_val,
        "startup_folder_entry": startup_vbs if vbs_exists else None,
    }
