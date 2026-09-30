"""
actions/os1_briefing.py
Autonomous Proactive Daily & System Briefing for Prime AI (Inspired by debpalash/OS1).

Provides an intelligent, warm conversational debrief combining:
1. Hardware & battery status
2. Active Git branch & uncommitted changes
3. WhatsApp unread messages & focus status
4. Second Brain / Obsidian recent notes
5. Warm spoken greeting ready for Prime's voice engine
"""

import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import obsidian_rag
import whatsapp_manager
from actions.her_companion import her_engine

logger = logging.getLogger("prime.os1.briefing")


class OS1BriefingEngine:
    """Aggregates system telemetry, pending work, and messages into a proactive conversational briefing."""

    def __init__(self):
        pass

    def _get_system_vitals(self) -> Dict[str, Any]:
        vitals = {
            "cpu_percent": 0.0,
            "ram_percent": 0.0,
            "free_disk_gb": 0.0,
            "battery_percent": None
        }
        try:
            import psutil
            vitals["cpu_percent"] = psutil.cpu_percent(interval=None)
            vitals["ram_percent"] = psutil.virtual_memory().percent
            usage = psutil.disk_usage(os.path.abspath(os.sep))
            vitals["free_disk_gb"] = round(usage.free / (1024**3), 1)
            batt = psutil.sensors_battery()
            if batt:
                vitals["battery_percent"] = batt.percent
        except Exception as e:
            logger.debug(f"Vitals retrieval error: {e}")
        return vitals

    def _get_git_summary(self) -> Dict[str, Any]:
        cwd = Path.cwd()
        branch = "main"
        uncommitted_count = 0
        try:
            b_out = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, cwd=cwd, timeout=3)
            if b_out.returncode == 0 and b_out.stdout.strip():
                branch = b_out.stdout.strip()
            s_out = subprocess.run(["git", "status", "-s"], capture_output=True, text=True, cwd=cwd, timeout=3)
            if s_out.returncode == 0:
                uncommitted_count = len([l for l in s_out.stdout.splitlines() if l.strip()])
        except Exception:
            pass
        return {"repo": cwd.name, "branch": branch, "uncommitted_changes": uncommitted_count}

    def _get_whatsapp_summary(self) -> Dict[str, Any]:
        try:
            status = whatsapp_manager.check_unread_whatsapp_messages()
            return {
                "unread_count": status.get("unread_count", 0),
                "has_unread": status.get("has_unread", False),
                "focus_mode": status.get("focus_mode", False)
            }
        except Exception:
            return {"unread_count": 0, "has_unread": False, "focus_mode": False}

    def _get_obsidian_recent_note(self) -> Dict[str, Any]:
        try:
            notes = obsidian_rag.list_notes(recursive=True)
            if notes:
                recent = notes[0]
                return {"recent_note": recent}
        except Exception:
            pass
        return {"recent_note": "No notes found"}

    def generate_briefing(self) -> Dict[str, Any]:
        """Synthesize proactive spoken debrief."""
        now = datetime.now()
        hour = now.hour
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        vitals = self._get_system_vitals()
        git_info = self._get_git_summary()
        wa_info = self._get_whatsapp_summary()
        obsidian_info = self._get_obsidian_recent_note()

        # Build natural conversational paragraphs
        lines = [f"{greeting}, sir. Prime is active and your workspace is ready."]

        # Hardware line
        batt_str = f", running on battery at {vitals['battery_percent']}%" if vitals.get('battery_percent') is not None else ""
        lines.append(
            f"System vitals look stable—CPU is at {vitals['cpu_percent']}%, RAM at {vitals['ram_percent']}%, "
            f"and you have {vitals['free_disk_gb']} GB free storage{batt_str}."
        )

        # Work / Git line
        if git_info["uncommitted_changes"] > 0:
            lines.append(f"In your repository '{git_info['repo']}' on branch '{git_info['branch']}', you have {git_info['uncommitted_changes']} uncommitted changes.")
        else:
            lines.append(f"Your repository '{git_info['repo']}' is clean on branch '{git_info['branch']}'.")

        # Communications
        if wa_info["unread_count"] > 0:
            lines.append(f"You have {wa_info['unread_count']} unread WhatsApp messages waiting.")

        # Second Brain memory
        if obsidian_info.get("recent_note") and obsidian_info["recent_note"] != "No notes found":
            note_name = Path(obsidian_info["recent_note"]).stem
            lines.append(f"Last time you were in your Second Brain reviewing '{note_name}'.")

        spoken_briefing = " ".join(lines)

        return {
            "ok": True,
            "timestamp": now.isoformat(),
            "spoken_text": spoken_briefing,
            "vitals": vitals,
            "git": git_info,
            "whatsapp": wa_info,
            "second_brain": obsidian_info
        }


# Global singleton
briefing_engine = OS1BriefingEngine()


def generate_os1_briefing() -> Dict[str, Any]:
    return briefing_engine.generate_briefing()
