"""
desktop_agent/tools_android.py — Android Device Automation Tools for Prime AI.
Exposes ADB control over Android phones directly to LLM function calling.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from actions.android_manager import android_manager
from .registry import ToolError, register


@register("androidListDevices")
def android_list_devices(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """List all connected Android devices (USB or Wi-Fi)."""
    return android_manager.list_devices()


@register("androidConnect")
def android_connect(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Connect to an Android device wirelessly over Wi-Fi.
    Args:
        host (str): IP address or host:port (e.g. '192.168.1.100' or '192.168.1.100:5555')
        port (int, optional): Port, default 5555.
    """
    args = args or {}
    host = args.get("host") or args.get("ip") or args.get("address") or ""
    if not host:
        return {"ok": False, "error": "Missing 'host' or 'ip' address of Android phone."}
    port = int(args.get("port") or 5555)
    return android_manager.connect_device(host, port)


@register("androidBattery")
def android_battery(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Get Android phone battery percentage, charging state, and thermals."""
    return android_manager.get_battery_status()


@register("androidUnlock")
def android_unlock(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Wake screen and dismiss lock screen on Android phone."""
    return android_manager.wake_and_unlock()


@register("androidLock")
def android_lock(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Put Android phone screen to sleep."""
    return android_manager.lock_screen()


@register("androidOpenApp")
def android_open_app(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Open an application on Android phone.
    Args:
        app_name (str): Name of app ('youtube', 'whatsapp', 'spotify', 'camera', 'maps', 'settings', 'chrome')
    """
    args = args or {}
    app_name = args.get("app_name") or args.get("name") or args.get("app") or ""
    if not app_name:
        return {"ok": False, "error": "Missing 'app_name' to launch on phone."}
    return android_manager.open_app(app_name)


@register("androidNotifications")
def android_notifications(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Read recent notifications and messages from Android phone."""
    args = args or {}
    limit = int(args.get("limit") or 5)
    return android_manager.read_notifications(limit=limit)


@register("androidMediaControl")
def android_media_control(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Control media playback on Android phone.
    Args:
        action (str): 'play_pause', 'play', 'pause', 'next', 'prev', 'volume_up', 'volume_down'
    """
    args = args or {}
    action = args.get("action") or "play_pause"
    return android_manager.media_control(action)
