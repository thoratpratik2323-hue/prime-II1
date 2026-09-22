"""
prime_operator.py — Proactive Autonomous Background Operator for Prime AI.
Inherited from OpenJarvis persistent operator architecture.

Monitors system vitals, schedule routines, and operator habits in the background,
proactively alerting or assisting Pratik Thorat without waiting for a command.
"""

from __future__ import annotations

import os
import sys
import time
import json
import psutil
import threading
from datetime import datetime, time as dtime
from typing import Optional, Callable, Dict, Any

from rich.console import Console

console = Console()

def get_system_idle_seconds() -> float:
    """Return seconds since user last moved mouse or pressed key on Windows."""
    if sys.platform != "win32":
        return 0.0
    try:
        import ctypes
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
    except Exception:
        pass
    return 0.0


class PrimeOperator:
    """
    Autonomous Proactive Background Operator.
    Runs continuous background sentinels for:
    1. System Health & RAM Sentinel (warns on memory leaks / high load)
    2. Battery Alert Sentinel (alerts when unplugged & dropping low)
    3. Eye Strain / Hydration Rest Sentinel (prompts after 90m continuous sessions)
    4. Scheduled Morning Briefing Sentinel
    5. Workspace Git Sentinel (flags uncommitted files at end of day)
    """

    def __init__(self, voice_engine=None, tool_executor: Optional[Callable] = None):
        self.voice = voice_engine
        self.tool_executor = tool_executor
        self._enabled = os.getenv("PROACTIVE_OPERATOR", "true").lower() in ("true", "1", "yes")
        self._dnd_mode = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # State tracking to avoid annoying repeating alarms
        self._last_ram_warning = 0.0
        self._last_battery_warning = 0.0
        self._last_rest_reminder = time.time()
        self._briefing_done_today: Optional[str] = None
        self._git_check_done_today: Optional[str] = None
        self._high_ram_streak = 0
        self._check_interval = 30  # seconds between sentinel sweeps

    def is_dnd(self) -> bool:
        return self._dnd_mode

    def set_dnd(self, val: bool) -> None:
        self._dnd_mode = bool(val)
        console.print(f"[bold cyan]DND Mode:[/bold cyan] {'ON (Muted proactive voice)' if self._dnd_mode else 'OFF'}")

    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, val: bool) -> None:
        self._enabled = bool(val)
        try:
            from dotenv import set_key
            from config import ENV_PATH
            set_key(str(ENV_PATH), "PROACTIVE_OPERATOR", "true" if self._enabled else "false")
        except Exception:
            pass

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="PrimeProactiveOperator")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _speak(self, text: str) -> None:
        if self._dnd_mode:
            return

        idle_sec = get_system_idle_seconds()
        if idle_sec > 300:  # User idle > 5 minutes
            return

        if self.voice and getattr(self.voice, "tts_enabled", True):
            try:
                self.voice.speak(text)
            except Exception:
                pass

    def _worker_loop(self) -> None:
        # Initial sleep so cockpit boots up cleanly first
        time.sleep(15)

        while not self._stop_event.is_set():
            if not self._enabled:
                time.sleep(5)
                continue

            try:
                self._check_system_vitals()
                self._check_battery()
                self._check_wellness_rest()
                self._check_scheduled_briefing()
                self._check_workspace_git()
            except Exception as e:
                # Never crash the operator thread
                time.sleep(2)

            self._stop_event.wait(self._check_interval)

    def _check_system_vitals(self) -> None:
        """Check RAM & CPU. If RAM > 88% for 3 consecutive checks, warn operator."""
        now = time.time()
        ram = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=None)

        if ram.percent >= 88.0:
            self._high_ram_streak += 1
        else:
            self._high_ram_streak = 0

        # Only warn if high RAM persists for >= 3 sweeps and at least 20 minutes since last warning
        if self._high_ram_streak >= 3 and (now - self._last_ram_warning > 1200):
            self._last_ram_warning = now
            msg = f"Pratik, host memory usage is very high at {ram.percent:.0f} percent. You may want to close unused browser tabs or heavy background processes."
            console.print(f"\n[bold yellow]🤖 PROACTIVE OPERATOR:[/bold yellow] [dim]{msg}[/dim]")
            self._speak(msg)

    def _check_battery(self) -> None:
        """Alert if laptop is on battery and falls below 20%."""
        now = time.time()
        try:
            battery = psutil.sensors_battery()
            if battery and not battery.power_plugged:
                if battery.percent <= 20 and (now - self._last_battery_warning > 1800):
                    self._last_battery_warning = now
                    msg = f"Attention Pratik, battery is down to {battery.percent} percent. Please connect your charger soon."
                    console.print(f"\n[bold red]⚡ BATTERY SENTINEL:[/bold red] [bold yellow]{msg}[/bold yellow]")
                    self._speak(msg)
        except Exception:
            pass

    def _check_wellness_rest(self) -> None:
        """Remind operator to rest eyes and hydrate after 90 minutes of continuous activity."""
        now = time.time()
        if now - self._last_rest_reminder > 5400:  # 90 minutes
            self._last_rest_reminder = now
            msg = "Pratik, you have been working hard for over 90 minutes. Remember to hydrate and rest your eyes for 2 minutes."
            console.print(f"\n[bold bright_cyan]☕ WELLNESS SENTINEL:[/bold bright_cyan] [dim]{msg}[/dim]")
            self._speak(msg)

    def _check_scheduled_briefing(self) -> None:
        """Trigger morning briefing automatically between 08:30 and 09:30 once per day."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        if self._briefing_done_today == today_str:
            return

        now_dt = datetime.now()
        # Between 8:30 AM and 9:30 AM
        if (now_dt.hour == 8 and now_dt.minute >= 30) or (now_dt.hour == 9 and now_dt.minute <= 30):
            self._briefing_done_today = today_str
            msg = "Good morning Pratik! Proactive operator is preparing your daily briefing."
            console.print(f"\n[bold bright_green]🌅 PROACTIVE SENTINEL:[/bold bright_green] [dim]{msg}[/dim]")
            self._speak(msg)
            if self.tool_executor:
                try:
                    res = self.tool_executor("morningBriefing", {"action": "briefing"})
                    if res.get("ok"):
                        briefing_text = str(res.get("result", ""))
                        self._speak(briefing_text[:300])
                except Exception:
                    pass

    def _check_workspace_git(self) -> None:
        """Remind operator about uncommitted git files at end of day (18:00 - 21:00)."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        if self._git_check_done_today == today_str:
            return

        now_dt = datetime.now()
        if 18 <= now_dt.hour <= 21:
            try:
                import subprocess
                from pathlib import Path
                res = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    cwd=str(Path(__file__).resolve().parent),
                    timeout=5,
                )
                if res.returncode == 0 and res.stdout.strip():
                    self._git_check_done_today = today_str
                    count = len(res.stdout.strip().splitlines())
                    msg = f"Pratik, you have {count} uncommitted file changes in your workspace. You may want to commit your progress before signing off."
                    console.print(f"\n[bold magenta]📦 WORKSPACE GIT SENTINEL:[/bold magenta] [dim]{msg}[/dim]")
                    self._speak(msg)
            except Exception:
                pass

    def get_status(self) -> Dict[str, Any]:
        """Return live diagnostic status of proactive sentinels."""
        ram = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        bat_str = f"{battery.percent}% ({'Plugged' if battery.power_plugged else 'Discharging'})" if battery else "N/A"
        return {
            "enabled": self._enabled,
            "running": self._thread is not None and self._thread.is_alive(),
            "dnd_mode": self._dnd_mode,
            "check_interval_sec": self._check_interval,
            "ram_percent": ram.percent,
            "battery": bat_str,
            "briefing_completed_today": self._briefing_done_today == datetime.now().strftime("%Y-%m-%d"),
            "sentinels": [
                "System Vitals Sentinel (RAM/CPU)",
                "Battery Discharge Sentinel",
                "Wellness / Hydration Rest Sentinel",
                "Morning Briefing Autonomous Trigger",
                "Workspace Git Sentinel (End-of-day changes)",
            ]
        }


# Global singleton instance
from voice_engine import voice
from tool_definitions import execute_tool

operator = PrimeOperator(voice_engine=voice, tool_executor=execute_tool)
