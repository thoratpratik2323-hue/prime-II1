"""
WhatsApp Voicemail & Auto-Responder Sentinel for Prime AI.
Handles Do-Not-Disturb (DND) focus modes, logs incoming and missed calls,
and delivers automated polite voicemail responses via WhatsApp when the operator is busy.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("prime.whatsapp_voicemail")

BASE_DIR = Path(__file__).resolve().parent.parent
LEDGER_FILE = BASE_DIR / "data" / "voicemail_ledger.json"
CONFIG_FILE = BASE_DIR / "config" / "dnd_state.json"


class VoicemailSentinel:
    """Manages call interception, DND focus sessions, and voicemail dispatch."""

    def __init__(self, ledger_file: Optional[Path] = None, config_file: Optional[Path] = None):
        self.ledger_file = ledger_file or LEDGER_FILE
        self.config_file = config_file or CONFIG_FILE
        self._load_dnd_state()

    def _load_dnd_state(self) -> None:
        self.dnd_enabled = False
        self.dnd_reason = "Deep focus session"
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                self.dnd_enabled = bool(data.get("dnd_enabled", False))
                self.dnd_reason = data.get("dnd_reason", "Deep focus session")
            except Exception as e:
                log.warning("Could not read DND config: %s", e)

    def _save_dnd_state(self) -> None:
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            self.config_file.write_text(
                json.dumps({"dnd_enabled": self.dnd_enabled, "dnd_reason": self.dnd_reason}, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            log.warning("Could not save DND config: %s", e)

    def set_dnd(self, enabled: bool, reason: str = "") -> Dict[str, Any]:
        """Enable or disable Do-Not-Disturb focus mode."""
        self.dnd_enabled = bool(enabled)
        if reason.strip():
            self.dnd_reason = reason.strip()
        self._save_dnd_state()
        state_str = "ENABLED" if self.dnd_enabled else "DISABLED"
        msg = f"Do-Not-Disturb mode is now {state_str}. Reason: '{self.dnd_reason}'." if self.dnd_enabled else "Do-Not-Disturb mode is now DISABLED. Prime is taking live calls."
        return {
            "ok": True,
            "dnd_enabled": self.dnd_enabled,
            "dnd_reason": self.dnd_reason,
            "message": msg
        }

    def get_dnd_status(self) -> Dict[str, Any]:
        """Return current DND state and reason."""
        return {
            "ok": True,
            "dnd_enabled": self.dnd_enabled,
            "dnd_reason": self.dnd_reason
        }

    def _load_ledger(self) -> List[Dict[str, Any]]:
        if not self.ledger_file.exists():
            return []
        try:
            return json.loads(self.ledger_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_ledger(self, entries: List[Dict[str, Any]]) -> None:
        try:
            self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
            self.ledger_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        except Exception as e:
            log.warning("Failed to save voicemail ledger: %s", e)

    def log_call(self, caller: str, call_type: str = "voice", status: str = "missed", note: str = "") -> Dict[str, Any]:
        """Log an incoming, missed, or auto-responded call."""
        ledger = self._load_ledger()
        entry = {
            "id": f"call_{int(time.time())}",
            "timestamp": datetime.now().isoformat(),
            "time_str": datetime.now().strftime("%I:%M %p, %d %b"),
            "caller": caller,
            "call_type": call_type,
            "status": status,
            "note": note
        }
        ledger.append(entry)
        # Keep latest 200 calls
        if len(ledger) > 200:
            ledger = ledger[-200:]
        self._save_ledger(ledger)
        return entry

    def get_call_logs(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Retrieve recent call records."""
        ledger = self._load_ledger()
        return ledger[-limit:][::-1]

    def handle_incoming_call(self, caller: str, call_type: str = "voice", dispatch_message: bool = True) -> Dict[str, Any]:
        """
        Interprets an incoming WhatsApp call event.
        If DND is active, logs missed call and sends automated voicemail follow-up.
        """
        now_str = datetime.now().strftime("%I:%M %p")
        if self.dnd_enabled:
            # Generate voicemail message
            voicemail_msg = (
                f"Namaste! Pratik sir is currently occupied in a {self.dnd_reason}. "
                f"Prime AI has safely logged your {call_type} call at {now_str}. "
                f"He will reach out as soon as his focus session completes."
            )
            # Log the call
            entry = self.log_call(
                caller=caller,
                call_type=call_type,
                status="auto_responded",
                note=f"Voicemail sent: {self.dnd_reason}"
            )

            # Attempt to send WhatsApp message if manager is available
            dispatched = False
            if dispatch_message:
                try:
                    from whatsapp_manager import send_whatsapp
                    send_res = send_whatsapp(caller, voicemail_msg)
                    dispatched = bool(send_res.get("ok"))
                except Exception as e:
                    log.warning("Could not send automated WhatsApp voicemail: %s", e)

            return {
                "ok": True,
                "action": "auto_responded",
                "caller": caller,
                "call_type": call_type,
                "dnd_active": True,
                "voicemail_text": voicemail_msg,
                "message_dispatched": dispatched,
                "log_entry": entry
            }
        else:
            entry = self.log_call(
                caller=caller,
                call_type=call_type,
                status="operator_alerted",
                note="DND inactive, alerted operator."
            )
            return {
                "ok": True,
                "action": "notify_operator",
                "caller": caller,
                "call_type": call_type,
                "dnd_active": False,
                "message": f"Incoming WhatsApp {call_type} call from {caller}.",
                "log_entry": entry
            }


_VOICEMAIL_INSTANCE: Optional[VoicemailSentinel] = None


def get_voicemail_sentinel() -> VoicemailSentinel:
    """Singleton getter for voicemail sentinel."""
    global _VOICEMAIL_INSTANCE
    if _VOICEMAIL_INSTANCE is None:
        _VOICEMAIL_INSTANCE = VoicemailSentinel()
    return _VOICEMAIL_INSTANCE


def set_dnd_mode(enabled: bool, reason: str = "") -> Dict[str, Any]:
    """Enable or disable DND focus mode."""
    return get_voicemail_sentinel().set_dnd(enabled, reason)


def get_call_logs(limit: int = 15) -> Dict[str, Any]:
    """Get list of recent calls from the voicemail ledger."""
    logs = get_voicemail_sentinel().get_call_logs(limit)
    return {"ok": True, "total": len(logs), "calls": logs}


def handle_voicemail_event(caller: str, call_type: str = "voice", dispatch_message: bool = True) -> Dict[str, Any]:
    """Process an incoming call with automated voicemail handling."""
    return get_voicemail_sentinel().handle_incoming_call(caller, call_type, dispatch_message=dispatch_message)
