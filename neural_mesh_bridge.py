"""
neural_mesh_bridge.py — Seamless Cross-Device Omnipresence & Neural Mesh Bridge.
Securely links PC, mobile smartphones, and tablets into a unified reactive layer:
1. Bidirectional Clipboard Synchronization (Phone <-> PC)
2. Real-Time Telemetry & Proactive Notification Push (SSE)
3. Remote Voice/Text Cockpit & One-Tap Hardware Quick Actions
4. Local LAN Pairing & Dynamic Token Security
"""

from __future__ import annotations

import json
import logging
import os
import queue
import secrets
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

log = logging.getLogger("prime.neural_mesh")

TOKEN_FILE = Path(__file__).resolve().parent / "data" / "mesh_token.json"


class NeuralMeshBridge:
    """
    Central hub bridging Windows Host PC with mobile devices on LAN.
    """

    def __init__(self):
        self._auth_token = self._load_or_generate_token()
        self._event_queues: List[queue.Queue] = []
        self._lock = threading.Lock()

        # Clipboard tracking state
        self._last_local_clipboard: str = ""
        self._stop_event = threading.Event()
        self._clipboard_thread: Optional[threading.Thread] = None

    def _load_or_generate_token(self) -> str:
        """Load or create persistent 6-character hex PIN/token for pairing."""
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        if TOKEN_FILE.exists():
            try:
                data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
                if "token" in data and len(data["token"]) >= 6:
                    return data["token"]
            except Exception:
                pass

        new_tok = secrets.token_hex(4).upper()  # 8-char secure PIN
        try:
            TOKEN_FILE.write_text(json.dumps({"token": new_tok, "created_at": datetime.now().isoformat()}), encoding="utf-8")
        except Exception:
            pass
        return new_tok

    @property
    def auth_token(self) -> str:
        return self._auth_token

    def verify_token(self, token: Optional[str]) -> bool:
        if not token:
            return False
        return secrets.compare_digest(token.strip().upper(), self._auth_token)

    def start_clipboard_sync(self) -> None:
        """Start background polling thread to detect local PC clipboard changes."""
        if self._clipboard_thread and self._clipboard_thread.is_alive():
            return
        self._stop_event.clear()
        self._clipboard_thread = threading.Thread(
            target=self._clipboard_watcher_loop,
            daemon=True,
            name="PrimeClipboardMeshWatcher"
        )
        self._clipboard_thread.start()
        log.info("Neural Mesh: Clipboard synchronization active.")

    def stop(self) -> None:
        self._stop_event.set()

    def _get_pc_clipboard(self) -> str:
        """Safely fetch current text from Windows clipboard."""
        if sys.platform != "win32":
            return ""
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                    return data or ""
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            pass
        return ""

    def set_pc_clipboard(self, text: str) -> bool:
        """Set Windows host clipboard text (pushed from mobile device)."""
        if sys.platform != "win32" or not text:
            return False
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
                self._last_local_clipboard = text
                log.info("Neural Mesh: Updated PC clipboard from mobile device (%d chars)", len(text))
                return True
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            log.warning("Could not set PC clipboard: %s", e)
            return False

    def _clipboard_watcher_loop(self) -> None:
        """Watch PC clipboard and broadcast changes to connected mobile devices."""
        self._last_local_clipboard = self._get_pc_clipboard()
        while not self._stop_event.is_set():
            try:
                curr = self._get_pc_clipboard()
                if curr and curr != self._last_local_clipboard:
                    self._last_local_clipboard = curr
                    self.broadcast_event({
                        "type": "clipboard_update",
                        "data": curr[:5000],  # Bound to 5KB
                        "timestamp": datetime.now().isoformat(),
                    })
            except Exception:
                pass
            self._stop_event.wait(1.5)

    def subscribe_events(self) -> queue.Queue:
        """Register a new SSE listener queue for a connected device."""
        q: queue.Queue = queue.Queue(maxsize=50)
        with self._lock:
            self._event_queues.append(q)
        return q

    def unsubscribe_events(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._event_queues:
                self._event_queues.remove(q)

    def broadcast_event(self, event_data: Dict[str, Any]) -> None:
        """Broadcast real-time event to all connected devices."""
        with self._lock:
            dead = []
            for q in self._event_queues:
                try:
                    q.put_nowait(event_data)
                except queue.Full:
                    dead.append(q)
            for d in dead:
                if d in self._event_queues:
                    self._event_queues.remove(d)

    def push_notification(self, title: str, message: str, priority: str = "normal") -> None:
        """Push a high-priority notification to all mobile/wearable endpoints."""
        self.broadcast_event({
            "type": "notification",
            "title": title,
            "message": message,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
        })

    def execute_remote_action(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute one-tap hardware quick action requested from mobile phone."""
        params = params or {}
        action = action.lower().strip()

        if action == "lock_pc":
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                return {"ok": True, "result": "Host workstation locked successfully."}
            return {"ok": False, "error": "Not supported on this platform."}

        elif action == "mute_pc":
            from tool_definitions import execute_tool
            return execute_tool("muteVolume", {})

        elif action == "play_pause":
            from tool_definitions import execute_tool
            return execute_tool("mediaControl", {"action": "play_pause"})

        elif action == "screenshot_preview":
            from PIL import ImageGrab
            import io
            import base64
            im = ImageGrab.grab()
            im.thumbnail((800, 450))
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=65)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return {"ok": True, "image_b64": f"data:image/jpeg;base64,{b64}"}

        elif action == "get_telemetry":
            return {
                "ok": True,
                "cpu_percent": psutil.cpu_percent(interval=None),
                "ram_percent": psutil.virtual_memory().percent,
                "battery": getattr(psutil.sensors_battery(), "percent", "AC"),
                "time": datetime.now().strftime("%I:%M:%S %p"),
            }

        return {"ok": False, "error": f"Unknown action '{action}'"}


mesh_bridge = NeuralMeshBridge()
