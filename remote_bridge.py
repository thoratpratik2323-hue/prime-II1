"""
Remote Neural Mesh Out-of-Home Link & Telegram Webhook Bridge for Prime AI.
Allows dispatching remote push alerts to mobile/Telegram/webhooks when away from the PC,
and securely executes authenticated remote commands (/lock, /status, /call, /note, /schedule).
"""

from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("prime.remote_bridge")

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "config" / "settings.json"
ALERTS_LOG = BASE_DIR / "data" / "remote_alerts.jsonl"


class RemoteBridge:
    """Out-of-Home bridge connecting Prime to Telegram, Webhooks, and remote control channels."""

    def __init__(self, settings_path: Optional[Path] = None):
        self.settings_path = settings_path or SETTINGS_FILE
        self.alerts_file = ALERTS_LOG
        self.start_time = time.time()

    def _load_settings(self) -> Dict[str, Any]:
        if not self.settings_path.exists():
            return {}
        try:
            return json.loads(self.settings_path.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("Could not read settings.json: %s", e)
            return {}

    def send_remote_alert(
        self,
        title: str,
        message: str,
        level: str = "info",
        destination: str = "auto"
    ) -> Dict[str, Any]:
        """
        Send a high-priority push alert to configured remote endpoints (Telegram / Webhook / Log).
        """
        timestamp = datetime.now().isoformat()
        alert_payload = {
            "timestamp": timestamp,
            "level": level.upper(),
            "title": title,
            "message": message,
            "destination": destination
        }

        # 1. Always append to local alerts ledger
        try:
            self.alerts_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.alerts_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert_payload) + "\n")
        except Exception as e:
            log.warning("Failed to append alert to ledger: %s", e)

        settings = self._load_settings()
        telegram_token = settings.get("telegram_bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN")
        telegram_chat = settings.get("telegram_chat_id") or os.environ.get("TELEGRAM_CHAT_ID")
        webhook_url = settings.get("remote_webhook_url") or os.environ.get("PRIME_REMOTE_WEBHOOK")

        delivered_channels = []

        # 2. Telegram Dispatch
        if telegram_token and telegram_chat and destination in ("auto", "telegram"):
            try:
                import requests
                emoji = "🚨" if level == "critical" else "⚠️" if level == "warning" else "ℹ️"
                text = f"{emoji} *[PRIME {level.upper()}]* *{title}*\n\n{message}\n\n_Sent: {timestamp}_"
                resp = requests.post(
                    f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                    json={"chat_id": telegram_chat, "text": text, "parse_mode": "Markdown"},
                    timeout=5
                )
                if resp.status_code == 200:
                    delivered_channels.append("telegram")
            except Exception as e:
                log.warning("Telegram alert dispatch failed: %s", e)

        # 3. Webhook Dispatch
        if webhook_url and destination in ("auto", "webhook"):
            try:
                import requests
                resp = requests.post(webhook_url, json=alert_payload, timeout=5)
                if resp.status_code in (200, 201, 204):
                    delivered_channels.append("webhook")
            except Exception as e:
                log.warning("Webhook alert dispatch failed: %s", e)

        status_msg = f"Alert delivered via: {', '.join(delivered_channels)}" if delivered_channels else "Alert saved to local buffer (no live remote channel connected)."
        return {
            "ok": True,
            "message": status_msg,
            "delivered": delivered_channels,
            "alert": alert_payload
        }

    def execute_remote_command(self, raw_command: str) -> Dict[str, Any]:
        """
        Execute an authenticated remote command received from Telegram or mobile bridge.
        Commands:
          /status
          /lock
          /call <recipient> [voice|video]
          /note <content>
          /schedule <recipient> <time> [voice|video]
        """
        cmd_str = (raw_command or "").strip()
        if not cmd_str:
            return {"ok": False, "error": "Empty command."}

        parts = cmd_str.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""

        if command in ("/status", "status"):
            return self._handle_status()
        elif command in ("/lock", "lock"):
            return self._handle_lock()
        elif command in ("/call", "call"):
            return self._handle_call(args)
        elif command in ("/note", "note"):
            return self._handle_note(args)
        elif command in ("/schedule", "schedule"):
            return self._handle_schedule(args)
        elif command in ("/help", "help", "?"):
            return {
                "ok": True,
                "output": (
                    "🤖 Prime Remote Commands:\n"
                    "• /status - Check workstation health & uptime\n"
                    "• /lock - Lock workstation immediately\n"
                    "• /call <contact> [voice|video] - Trigger WhatsApp call\n"
                    "• /note <text> - Crystallize quick note into Obsidian\n"
                    "• /schedule <contact> <time> [voice|video] - Schedule WhatsApp call\n"
                    "• /help - Display this manual"
                )
            }
        else:
            return {"ok": False, "error": f"Unknown remote command: '{command}'. Send /help for options."}

    def _handle_status(self) -> Dict[str, Any]:
        uptime_sec = int(time.time() - self.start_time)
        hrs, rem = divmod(uptime_sec, 3600)
        mins, secs = divmod(rem, 60)
        uptime_str = f"{hrs}h {mins}m {secs}s"

        cpu_str = "N/A"
        ram_str = "N/A"
        try:
            import psutil
            cpu_str = f"{psutil.cpu_percent()}%"
            ram_str = f"{psutil.virtual_memory().percent}%"
        except Exception:
            pass

        report = (
            f"📊 PRIME STATUS REPORT\n"
            f"• OS: {platform.system()} {platform.release()}\n"
            f"• CPU: {cpu_str} | RAM: {ram_str}\n"
            f"• Uptime: {uptime_str}\n"
            f"• Mode: Headless Voice / Out-of-Home Mesh Active"
        )
        return {"ok": True, "output": report}

    def _handle_lock(self) -> Dict[str, Any]:
        try:
            import ctypes
            if platform.system() == "Windows":
                ctypes.windll.user32.LockWorkStation()
            else:
                subprocess.run("gnome-screensaver-command -l", shell=True)
            return {"ok": True, "output": "🔒 Workstation locked successfully."}
        except Exception as e:
            return {"ok": False, "error": f"Failed to lock workstation: {e}"}

    def _handle_call(self, args: str) -> Dict[str, Any]:
        if not args:
            return {"ok": False, "error": "Usage: /call <recipient> [voice|video]"}
        tokens = args.split()
        call_type = "voice"
        if tokens[-1].lower() in ("video", "voice", "vid"):
            call_type = "video" if "vid" in tokens[-1].lower() else "voice"
            recipient = " ".join(tokens[:-1])
        else:
            recipient = " ".join(tokens)

        try:
            from whatsapp_manager import make_whatsapp_call
            res = make_whatsapp_call(recipient, call_type)
            return {"ok": True, "output": res.get("message", "Call initiated.")}
        except Exception as e:
            return {"ok": False, "error": f"WhatsApp call initiation error: {e}"}

    def _handle_note(self, content: str) -> Dict[str, Any]:
        if not content:
            return {"ok": False, "error": "Usage: /note <note text>"}
        try:
            from core.vector_memory import crystallize_dev_log
            res = crystallize_dev_log(summary=content[:60], details=content, tags=["remote_note"])
            return {"ok": True, "output": res.get("message", "Note crystallized in Obsidian.")}
        except Exception as e:
            return {"ok": False, "error": f"Failed to save note: {e}"}

    def _handle_schedule(self, args: str) -> Dict[str, Any]:
        if not args:
            return {"ok": False, "error": "Usage: /schedule <contact> at <time> [voice|video]"}
        try:
            from whatsapp_manager import schedule_whatsapp_call
            # parse e.g. "Mummy at 5:00 PM" or "Pratik tomorrow at 10 AM"
            call_type = "voice"
            text = args
            if " video" in text.lower():
                call_type = "video"
                text = text.replace(" video", "").replace(" Video", "")
            elif " voice" in text.lower():
                call_type = "voice"
                text = text.replace(" voice", "").replace(" Voice", "")

            # split on 'at' or 'in' or 'for'
            parts = re.split(r"\s+(?:at|for|in)\s+", text, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2:
                recipient, time_str = parts[0].strip(), parts[1].strip()
            else:
                tokens = text.split()
                recipient = tokens[0]
                time_str = " ".join(tokens[1:])

            res = schedule_whatsapp_call(recipient, time_str, call_type=call_type)
            return {"ok": res.get("ok", False), "output": res.get("message") or res.get("error")}
        except Exception as e:
            return {"ok": False, "error": f"Schedule WhatsApp call error: {e}"}


_REMOTE_BRIDGE_INSTANCE: Optional[RemoteBridge] = None


def get_remote_bridge() -> RemoteBridge:
    """Singleton getter for the remote bridge."""
    global _REMOTE_BRIDGE_INSTANCE
    if _REMOTE_BRIDGE_INSTANCE is None:
        _REMOTE_BRIDGE_INSTANCE = RemoteBridge()
    return _REMOTE_BRIDGE_INSTANCE


def send_remote_alert(title: str, message: str, level: str = "info", destination: str = "auto") -> Dict[str, Any]:
    """Helper function to dispatch a remote alert."""
    return get_remote_bridge().send_remote_alert(title, message, level, destination)


def handle_remote_command(command: str) -> Dict[str, Any]:
    """Helper function to execute an authenticated remote command."""
    return get_remote_bridge().execute_remote_command(command)
