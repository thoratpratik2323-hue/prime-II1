"""
core/dots_mailbox.py
Asynchronous Stigmergy & Mailbox Protocol for Prime Dots.
Inspired by Munder Difflin's git-backed inbox/outbox architecture.

Features:
1. Isolated Per-Dot Mailboxes: inbox/, outbox/, .done/, .sent/ inside data/dots/<dot_id>/
2. Atomic Delivery: Messages written via temp file and atomic rename (zero locks / zero conflicts).
3. Routing Engine: Background router moves messages from sender outbox to recipient inbox.
4. UI Telemetry Stream: Emits visual envelope events (sender, recipient, coordinates) for the 2D Office Floor.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("prime.dots.mailbox")

DOTS_BASE_DIR = Path(__file__).resolve().parent.parent / "data" / "dots"


class DotsMailbox:
    """Manages the inbox and outbox for a specific Prime Dot."""

    def __init__(self, dot_id: str):
        self.dot_id = dot_id
        self.mailbox_dir = DOTS_BASE_DIR / self.dot_id / "mailbox"
        self.inbox_dir = self.mailbox_dir / "inbox"
        self.inbox_done_dir = self.inbox_dir / ".done"
        self.outbox_dir = self.mailbox_dir / "outbox"
        self.sent_dir = self.outbox_dir / ".sent"

        # Ensure directory structure exists
        self.inbox_done_dir.mkdir(parents=True, exist_ok=True)
        self.sent_dir.mkdir(parents=True, exist_ok=True)

    def send_message(
        self,
        recipient_id: str,
        subject: str,
        body: str,
        action: str = "data_share",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Drop a message into the dot's outbox for delivery by the router."""
        msg_id = f"msg_{uuid.uuid4().hex[:10]}"
        timestamp = datetime.now().isoformat()
        message = {
            "id": msg_id,
            "sender": self.dot_id,
            "recipient": recipient_id,
            "action": action,
            "subject": subject,
            "body": body,
            "payload": payload or {},
            "timestamp": timestamp,
            "status": "queued",
        }

        # Write atomically via temp file to avoid partial reads
        temp_path = self.outbox_dir / f"tmp_{msg_id}.tmp"
        target_path = self.outbox_dir / f"{int(time.time()*1000)}_{msg_id}.json"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(message, f, indent=2)
            os.replace(str(temp_path), str(target_path))
            logger.info("[Mailbox %s] Queued message %s to %s", self.dot_id, msg_id, recipient_id)
        except Exception as e:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            raise e

        return message

    def read_inbox(self, mark_as_done: bool = True) -> List[Dict[str, Any]]:
        """Read and drain unread messages from the dot's inbox."""
        messages: List[Dict[str, Any]] = []
        if not self.inbox_dir.exists():
            return messages

        json_files = sorted(self.inbox_dir.glob("*.json"))
        for file_path in json_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    msg = json.load(f)
                messages.append(msg)

                if mark_as_done:
                    # Move to .done directory for audit trail
                    done_target = self.inbox_done_dir / file_path.name
                    shutil.move(str(file_path), str(done_target))
            except Exception as e:
                logger.error("[Mailbox %s] Failed to read inbox file %s: %s", self.dot_id, file_path.name, e)

        return messages

    def get_unread_count(self) -> int:
        """Returns the count of unprocessed messages currently in inbox."""
        if not self.inbox_dir.exists():
            return 0
        return len(list(self.inbox_dir.glob("*.json")))


class DotsMailboxRouter:
    """Autonomous routing engine that moves messages from sender outboxes to recipient inboxes."""

    _instance: Optional["DotsMailboxRouter"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "DotsMailboxRouter":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._flight_events: List[Dict[str, Any]] = []  # In-flight envelope events for 2D UI
        self._flight_lock = threading.Lock()
        self._dispatch_lock = threading.RLock()
        self.start()

    def start(self):
        """Starts background mailbox routing thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._route_loop, daemon=True, name="DotsMailboxRouter")
        self._thread.start()
        logger.info("DotsMailboxRouter daemon started.")

    def stop(self):
        """Stops background mailbox routing thread."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("DotsMailboxRouter daemon stopped.")

    def dispatch_pending(self) -> int:
        """Single-pass delivery of all pending messages across all Dot outboxes."""
        with self._dispatch_lock:
            delivered_count = 0
            if not DOTS_BASE_DIR.exists():
                return 0

            for dot_dir in DOTS_BASE_DIR.iterdir():
                if not dot_dir.is_dir():
                    continue
                outbox = dot_dir / "mailbox" / "outbox"
                if not outbox.exists():
                    continue

                for msg_file in sorted(outbox.glob("*.json")):
                    if not msg_file.exists():
                        continue
                    try:
                        with open(msg_file, "r", encoding="utf-8") as f:
                            msg = json.load(f)

                        recipient_id = msg.get("recipient")
                        sender_id = msg.get("sender")
                        if not recipient_id:
                            continue

                        # Deliver to recipient inbox
                        recipient_inbox = DOTS_BASE_DIR / recipient_id / "mailbox" / "inbox"
                        recipient_inbox.mkdir(parents=True, exist_ok=True)

                        target_name = msg_file.name
                        target_file = recipient_inbox / target_name

                        # Copy to recipient inbox
                        shutil.copy2(str(msg_file), str(target_file))

                        # Move from outbox to sent with retry for Windows lock release
                        sent_dir = outbox / ".sent"
                        sent_dir.mkdir(parents=True, exist_ok=True)
                        dest_file = sent_dir / target_name
                        moved = False
                        for _ in range(4):
                            try:
                                if msg_file.exists():
                                    shutil.move(str(msg_file), str(dest_file))
                                moved = True
                                break
                            except (PermissionError, OSError):
                                time.sleep(0.04)

                        if not moved and msg_file.exists():
                            try:
                                shutil.copy2(str(msg_file), str(dest_file))
                                msg_file.unlink(missing_ok=True)
                            except Exception:
                                pass

                        delivered_count += 1
                        logger.info("[Router] Delivered %s from %s -> %s", msg.get("id"), sender_id, recipient_id)

                        # Register visual envelope flight event for 2D Office Floor
                        with self._flight_lock:
                            self._flight_events.append({
                                "id": msg.get("id"),
                                "sender": sender_id,
                                "recipient": recipient_id,
                                "subject": msg.get("subject", "Task Update"),
                                "action": msg.get("action", "data_share"),
                                "timestamp": time.time(),
                            })
                            # Keep last 50 events
                            if len(self._flight_events) > 50:
                                self._flight_events = self._flight_events[-50:]

                    except Exception as e:
                        logger.error("[Router] Error routing %s: %s", msg_file.name, e)

            return delivered_count

    def get_recent_flights(self, seconds_window: float = 30.0) -> List[Dict[str, Any]]:
        """Get visual envelope flights that occurred within the time window."""
        now = time.time()
        with self._flight_lock:
            return [
                ev for ev in self._flight_events
                if (now - ev["timestamp"]) <= seconds_window
            ]

    def _route_loop(self):
        while not self._stop_event.is_set():
            try:
                self.dispatch_pending()
            except Exception as e:
                logger.error("[Router Loop] Error: %s", e)
            self._stop_event.wait(timeout=1.0)


# Global singleton instance
mailbox_router = DotsMailboxRouter()
