"""
ambient_spatial_sentinel.py — Ambient Vision & Multimodal Spatial Tracking Engine.
Continuously perceives operator workflow, detects stagnation/stuck states,
compiler errors, and fatigue, and proactively assists without requiring explicit commands.
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil
from PIL import Image, ImageGrab, ImageStat

log = logging.getLogger("prime.ambient_vision")

# Keywords indicating terminal or compiler errors
ERROR_SIGNATURES = [
    "syntaxerror", "typeerror", "referenceerror", "nameerror", "indexerror", "keyerror",
    "failed to compile", "compilation failed", "build failed", "traceback (most recent call last)",
    "fatal error", "uncaught exception", "error: cannot find module", "npm err!", "pip._vendor",
    "panic:", "segmentation fault", "nullpointerexception", "assertionerror", "exit status 1",
    "cargo build error", "tsc --noemit failed"
]

FATIGUE_APPS = ["code.exe", "devenv.exe", "windowsterminal.exe", "powershell.exe", "cmd.exe", "pycharm64.exe"]


class WorkflowState:
    """Represents a snapshot of the operator's current workflow."""

    def __init__(
        self,
        timestamp: float,
        window_title: str,
        process_name: str,
        screen_hash: str,
        is_coding_or_terminal: bool,
        error_detected: bool = False,
        error_snippet: str = "",
    ):
        self.timestamp = timestamp
        self.window_title = window_title
        self.process_name = process_name
        self.screen_hash = screen_hash
        self.is_coding_or_terminal = is_coding_or_terminal
        self.error_detected = error_detected
        self.error_snippet = error_snippet


class AmbientSpatialSentinel:
    """
    Perception Sentinel that runs an ambient background loop to track workflow,
    detect when the user is stuck, diagnose errors, and proactively suggest assistance.
    """

    def __init__(
        self,
        voice_engine: Any = None,
        tool_executor: Optional[Callable] = None,
        check_interval_sec: float = 12.0,
    ):
        self.voice = voice_engine
        self.tool_executor = tool_executor
        self.check_interval_sec = check_interval_sec

        self._enabled = os.getenv("AMBIENT_VISION_ENABLED", "true").lower() in ("true", "1", "yes")
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # State tracking
        self._history: List[WorkflowState] = []
        self._last_stuck_alert: float = 0.0
        self._last_fatigue_alert: float = 0.0
        self._consecutive_stagnant_checks: int = 0
        self._consecutive_error_checks: int = 0
        self._session_start_time: float = time.time()
        self._last_proactive_suggestion: str = ""

    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, val: bool) -> None:
        self._enabled = bool(val)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._perception_loop,
            daemon=True,
            name="PrimeAmbientSpatialSentinel"
        )
        self._thread.start()
        log.info("Ambient Spatial Perception Sentinel started.")

    def stop(self) -> None:
        self._stop_event.set()

    def get_active_window_info(self) -> Tuple[str, str]:
        """Retrieve active window title and executable name on Windows."""
        if sys.platform != "win32":
            return "", ""
        try:
            import win32gui
            import win32process

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return "", ""

            title = win32gui.GetWindowText(hwnd).strip()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proc = psutil.Process(pid)
                pname = proc.name().lower()
            except Exception:
                pname = ""
            return title, pname
        except Exception:
            return "", ""

    def _get_fast_screen_hash(self) -> str:
        """Capture a low-res thumbnail and compute a fast perceptual visual hash."""
        try:
            # Grab full screen and resize to 120x68 grayscale thumbnail for ultra-fast, zero-overhead comparison
            im = ImageGrab.grab()
            thumb = im.resize((120, 68)).convert("L")
            # Downsample and hash
            pixels = list(thumb.getdata())
            # Simple average hash
            avg = sum(pixels) / len(pixels)
            bits = "".join("1" if p > avg else "0" for p in pixels)
            return hashlib.md5(bits.encode("utf-8")).hexdigest()
        except Exception as e:
            log.debug("Screen hash error: %s", e)
            return ""

    def _perception_loop(self) -> None:
        """Continuous non-blocking visual and spatial perception loop."""
        # Initial settling pause
        time.sleep(10)

        while not self._stop_event.is_set():
            if not self._enabled:
                time.sleep(5)
                continue

            try:
                self._perceive_cycle()
            except Exception as e:
                log.debug("Perception cycle error: %s", e)

            self._stop_event.wait(self.check_interval_sec)

    def _perceive_cycle(self) -> None:
        # Performance & Battery Optimization: If user is idle (AFK > 90s), skip screen capture
        try:
            from prime_operator import get_system_idle_seconds
            if get_system_idle_seconds() > 90.0:
                return
        except Exception:
            pass

        now = time.time()
        title, pname = self.get_active_window_info()
        title_lower = title.lower()

        # If system is locked or screen saver active
        if not title:
            return

        is_dev = any(app in pname for app in FATIGUE_APPS) or any(
            ide in title_lower for ide in ["visual studio code", "vscode", "pycharm", "terminal", "powershell", "cmd", "bash"]
        )

        screen_hash = self._get_fast_screen_hash()

        # Check for error keywords in the window title
        error_detected = any(err in title_lower for err in ERROR_SIGNATURES)
        error_snippet = title if error_detected else ""

        current_state = WorkflowState(
            timestamp=now,
            window_title=title,
            process_name=pname,
            screen_hash=screen_hash,
            is_coding_or_terminal=is_dev,
            error_detected=error_detected,
            error_snippet=error_snippet,
        )

        # Track history (keep last 30 states ~ 6 minutes of continuous perception)
        self._history.append(current_state)
        if len(self._history) > 30:
            self._history.pop(0)

        # 1. Evaluate Stagnation / Stuck State
        self._evaluate_stuck_state(current_state)

        # 2. Evaluate Continuous Fatigue
        self._evaluate_fatigue(now, is_dev)

    def _evaluate_stuck_state(self, current: WorkflowState) -> None:
        """Detect if operator is repeatedly failing or frozen on the same compiler/code error."""
        if len(self._history) < 6:
            return

        now = time.time()
        recent = self._history[-6:]  # Last ~72 seconds

        # Check if same screen hash persists while in coding/terminal
        same_hash = all(s.screen_hash == current.screen_hash and s.screen_hash != "" for s in recent)
        has_error = any(s.error_detected for s in recent) or any(
            any(err in s.window_title.lower() for err in ERROR_SIGNATURES) for s in recent
        )

        if has_error:
            self._consecutive_error_checks += 1
        else:
            self._consecutive_error_checks = max(0, self._consecutive_error_checks - 1)

        # Trigger proactive intervention if stuck on error for > 4 checks (~48 seconds) or identical code screen > 3 minutes
        is_stuck = (self._consecutive_error_checks >= 4) or (same_hash and current.is_coding_or_terminal and len(self._history) >= 15)

        if is_stuck and (now - self._last_stuck_alert > 900):  # At most once per 15 mins
            self._last_stuck_alert = now
            self._trigger_proactive_stuck_intervention(current)

    def _trigger_proactive_stuck_intervention(self, state: WorkflowState) -> None:
        """Trigger gentle multimodal assistance when stuck."""
        log.info("Stuck state detected in %s (%s). Generating proactive assistance...", state.process_name, state.window_title)

        suggestion = (
            f"Pratik, I noticed you've been working through an issue in {state.process_name}. "
            "Would you like me to analyze the screen, inspect the error trace, and suggest a fix?"
        )
        self._last_proactive_suggestion = suggestion

        # Log to rich console and notify
        try:
            from rich.console import Console
            c = Console()
            c.print(f"\n[bold bright_cyan]👁️ AMBIENT VISION SENTINEL:[/bold bright_cyan] [italic yellow]{suggestion}[/italic yellow]")
        except Exception:
            pass

        # Speak if voice engine available and not DND
        if self.voice and getattr(self.voice, "tts_enabled", True):
            try:
                self.voice.speak(suggestion)
            except Exception:
                pass

        # Broadcast to mobile bridge if available
        try:
            from neural_mesh_bridge import mesh_bridge
            mesh_bridge.push_notification("Ambient Vision Assist", suggestion, priority="high")
        except Exception:
            pass

    def _evaluate_fatigue(self, now: float, is_dev: bool) -> None:
        """Evaluate continuous focus duration and posture/rest signals."""
        session_duration = now - self._session_start_time
        if session_duration > 5400 and (now - self._last_fatigue_alert > 3600):  # 90 minutes continuous
            self._last_fatigue_alert = now
            alert = "Pratik, you've maintained intense focus for an hour and a half. A 2-minute water break will recharge your mental clarity."
            if self.voice and getattr(self.voice, "tts_enabled", True):
                try:
                    self.voice.speak(alert)
                except Exception:
                    pass

    def force_analyze_workflow(self) -> Dict[str, Any]:
        """Perform an immediate high-resolution multimodal diagnostic of the current screen."""
        title, pname = self.get_active_window_info()
        diag: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "active_window": title,
            "process": pname,
            "recent_stuck_detected": self._consecutive_error_checks >= 2,
            "last_suggestion": self._last_proactive_suggestion,
        }

        # Multimodal Gemini Screen Analysis
        try:
            from desktop_agent.tools_screenshot import analyze_screen_with_ai
            vision_res = analyze_screen_with_ai({
                "prompt": "Inspect the active developer window. Identify the code or terminal errors, explain the root cause, and give the exact fix."
            })
            diag["ai_screen_analysis"] = vision_res
        except Exception as e:
            diag["ai_screen_analysis"] = f"Vision analysis skipped: {e}"

        return diag

    def get_status(self) -> Dict[str, Any]:
        title, pname = self.get_active_window_info()
        return {
            "enabled": self._enabled,
            "running": self._thread is not None and self._thread.is_alive(),
            "active_window": title,
            "active_process": pname,
            "consecutive_error_checks": self._consecutive_error_checks,
            "last_suggestion": self._last_proactive_suggestion,
            "history_depth": len(self._history),
        }


# Singleton instance
from voice_engine import voice
from tool_definitions import execute_tool

ambient_sentinel = AmbientSpatialSentinel(voice_engine=voice, tool_executor=execute_tool)
