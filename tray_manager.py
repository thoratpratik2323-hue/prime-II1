"""
tray_manager.py — Windows System Tray Control for Prime AI.
Provides a persistent, zero-overhead taskbar icon with status indicators,
mic mute/unmute toggles, telemetry balloons, and clean shutdown controls.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from typing import Optional

from PIL import Image, ImageDraw
import pystray

log = logging.getLogger("prime.tray")

_TRAY_ICON: Optional[pystray.Icon] = None
_IS_MUTED: bool = False


def _create_icon_image(is_muted: bool = False) -> Image.Image:
    """Generate dynamic high-DPI tray icon (64x64 RGBA). Green when active, red when muted."""
    image = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    if is_muted:
        # Crimson Red outer ring & fill
        draw.ellipse((4, 4, 60, 60), fill=(180, 20, 20), outline=(255, 60, 60), width=3)
        draw.line((18, 18, 46, 46), fill=(255, 255, 255), width=4)
        draw.line((18, 46, 46, 18), fill=(255, 255, 255), width=4)
    else:
        # Emerald Green outer ring & cockpit core
        draw.ellipse((4, 4, 60, 60), fill=(10, 30, 20), outline=(0, 255, 170), width=3)
        # Inner neon pulse
        draw.ellipse((14, 14, 50, 50), fill=(0, 200, 115))
        # Stylized 'P' letter in center
        draw.polygon([(24, 20), (36, 20), (42, 26), (36, 32), (24, 32)], fill=(255, 255, 255))
        draw.rectangle([(24, 20), (28, 44)], fill=(255, 255, 255))

    return image


def toggle_mic_mute(icon=None, item=None):
    """Toggle microphone listening state."""
    global _IS_MUTED
    _IS_MUTED = not _IS_MUTED
    try:
        from voice_engine import voice
        voice.tts_enabled = not _IS_MUTED
    except Exception:
        pass

    if _TRAY_ICON:
        _TRAY_ICON.icon = _create_icon_image(_IS_MUTED)
        status_str = "MUTED (Paused)" if _IS_MUTED else "LIVE (Listening 24/7)"
        _TRAY_ICON.title = f"Prime AI — {status_str}"
        try:
            _TRAY_ICON.notify(f"Prime Microphone is now {status_str}", "Prime AI Cockpit")
        except Exception:
            pass


def open_cockpit_window(icon=None, item=None):
    """Bring the Prime terminal to focus, or open a new Cockpit console."""
    try:
        from desktop_agent.tools_gui import focus_window
        res = focus_window("prime")
        if res.get("ok"):
            return
    except Exception:
        pass

    try:
        cmd = ["cmd.exe", "/c", "start", "cmd.exe", "/k", "python prime.py"]
        subprocess.Popen(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    except Exception as e:
        log.warning("Could not launch Prime cockpit: %s", e)


def show_system_telemetry(icon=None, item=None):
    """Display quick Windows telemetry balloon notification."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()
        batt_str = f"{battery.percent}%" if battery else "Desktop (AC)"
        msg = f"CPU: {cpu}% | RAM: {ram}%\nPower: {batt_str}\nStatus: {'MUTED' if _IS_MUTED else 'ONLINE'}"
        if _TRAY_ICON:
            _TRAY_ICON.notify(msg, "⚡ Prime AI Telemetry")
    except Exception as e:
        if _TRAY_ICON:
            _TRAY_ICON.notify(f"Status: Online | Error reading telemetry: {e}", "Prime AI")


def stop_prime_application(icon=None, item=None):
    """Cleanly stop Prime AI and exit."""
    log.info("Stop requested via System Tray. Shutting down...")
    try:
        from single_instance import release_single_instance, prevent_system_sleep
        prevent_system_sleep(False)
        release_single_instance()
    except Exception:
        pass

    if _TRAY_ICON:
        try:
            _TRAY_ICON.stop()
        except Exception:
            pass

    # Exit process cleanly
    os._exit(0)


def start_tray_icon() -> None:
    """Launch the System Tray Icon in a background daemon thread."""
    global _TRAY_ICON

    menu = pystray.Menu(
        pystray.MenuItem("⚡ Prime AI :: Autonomous Cockpit", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🎙️ Toggle Mic Mute", toggle_mic_mute, checked=lambda item: _IS_MUTED),
        pystray.MenuItem("🖥️ Open Neural Cockpit", open_cockpit_window),
        pystray.MenuItem("📊 System Telemetry", show_system_telemetry),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🛑 Stop Prime", stop_prime_application),
    )

    _TRAY_ICON = pystray.Icon(
        name="PrimeAI",
        icon=_create_icon_image(is_muted=False),
        title="Prime AI — LIVE (Listening 24/7)",
        menu=menu,
    )

    def _run():
        try:
            log.info("System Tray Icon loop started.")
            _TRAY_ICON.run()
        except Exception as e:
            log.warning("System Tray error: %s", e)

    tray_thread = threading.Thread(target=_run, name="PrimeSystemTray", daemon=True)
    tray_thread.start()
