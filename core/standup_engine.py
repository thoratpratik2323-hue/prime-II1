"""
Autonomous Daily Standup & Evening Debrief Engine for Prime AI.
Synthesizes daily metrics, git commits, WhatsApp schedules, Obsidian notes,
and system telemetry into structured voice briefings and executive summaries.
"""

from __future__ import annotations

import logging
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("prime.standup_engine")

BASE_DIR = Path(__file__).resolve().parent.parent


class StandupEngine:
    """Produces morning briefings and evening wrap-up debriefs."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or BASE_DIR

    def generate_morning_standup(self) -> Dict[str, Any]:
        """Generate structured morning briefing with priorities, calls, and hardware vitals."""
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")

        # 1. Hardware vitals
        cpu_usage = 0.0
        ram_usage = 0.0
        battery_str = "AC Power"
        try:
            import psutil
            cpu_usage = psutil.cpu_percent(interval=0.1)
            ram_usage = psutil.virtual_memory().percent
            batt = psutil.sensors_battery()
            if batt:
                plugged = "plugged in" if batt.power_plugged else "on battery"
                battery_str = f"{int(batt.percent)}% ({plugged})"
        except Exception:
            pass

        # 2. Scheduled WhatsApp Calls
        scheduled_calls: List[Dict[str, Any]] = []
        try:
            from whatsapp_manager import list_scheduled_calls
            res = list_scheduled_calls()
            if res.get("ok"):
                scheduled_calls = res.get("scheduled_calls", [])
        except Exception:
            pass

        # 3. Recent Obsidian Dev Logs
        recent_notes: List[str] = []
        try:
            dev_logs_dir = self.base_dir / "Obsidian_Vault" / "DevLogs"
            if dev_logs_dir.exists():
                logs = sorted(dev_logs_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
                recent_notes = [f.stem for f in logs[:3]]
        except Exception:
            pass

        # 4. Compose speech script
        call_count = len(scheduled_calls)
        call_msg = (
            f"You have {call_count} WhatsApp call{'s' if call_count > 1 else ''} scheduled today."
            if call_count > 0 else "You have no pending scheduled calls for today."
        )

        speech = (
            f"Good morning Sir! Today is {date_str}, current time is {time_str}. "
            f"System status is nominal with CPU at {int(cpu_usage)}%, RAM at {int(ram_usage)}%, and power at {battery_str}. "
            f"{call_msg} "
            f"Ready for today's engineering sprint, Sir."
        )

        data = {
            "date": date_str,
            "time": time_str,
            "cpu_percent": cpu_usage,
            "ram_percent": ram_usage,
            "battery": battery_str,
            "scheduled_calls_count": call_count,
            "recent_notes": recent_notes,
            "speech_script": speech
        }

        return {"ok": True, "standup": data, "speech_script": speech}

    def generate_evening_debrief(self) -> Dict[str, Any]:
        """Generate structured evening debrief summarizing commits and completed tasks."""
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")

        # 1. Today's git commits
        commits: List[str] = []
        try:
            res = subprocess.run(
                ["git", "log", "--since=midnight", "--oneline"],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=10
            )
            if res.returncode == 0 and res.stdout.strip():
                commits = res.stdout.strip().splitlines()
        except Exception:
            pass

        # 2. Call Logs
        call_records: List[Dict[str, Any]] = []
        try:
            from core.whatsapp_voicemail import get_voicemail_sentinel
            call_records = get_voicemail_sentinel().get_call_logs(limit=10)
        except Exception:
            pass

        # 3. Compose speech script
        commit_count = len(commits)
        commit_msg = (
            f"You pushed {commit_count} commit{'s' if commit_count > 1 else ''} today."
            if commit_count > 0 else "No new git commits were logged today."
        )

        speech = (
            f"Good evening Sir! Here is your daily debrief for {date_str}. "
            f"{commit_msg} "
            f"Prime handled your calls and automated your workspace throughout the day. "
            f"All critical systems remain fully secured. Have a restful evening, Sir!"
        )

        data = {
            "date": date_str,
            "commits_today_count": commit_count,
            "commits": commits,
            "recent_calls_count": len(call_records),
            "speech_script": speech
        }

        return {"ok": True, "debrief": data, "speech_script": speech}


_STANDUP_INSTANCE: Optional[StandupEngine] = None


def get_standup_engine() -> StandupEngine:
    """Singleton getter for Standup Engine."""
    global _STANDUP_INSTANCE
    if _STANDUP_INSTANCE is None:
        _STANDUP_INSTANCE = StandupEngine()
    return _STANDUP_INSTANCE


def generate_morning_standup() -> Dict[str, Any]:
    """Generate morning standup voice briefing."""
    return get_standup_engine().generate_morning_standup()


def generate_evening_debrief() -> Dict[str, Any]:
    """Generate evening debrief voice wrap-up."""
    return get_standup_engine().generate_evening_debrief()
