"""
actions/stapler_dictation.py
System-Wide Instant Dictation Engine ("Stapler") for Prime AI.
Inspired by Munder Difflin's 'Stapler' dictation & meeting transcriber (replaces Wispr Flow / Granola).

Key Features:
1. System-Wide Global Hotkey: Ctrl + Alt + Space triggers instant voice dictation anywhere on Windows.
2. Direct-to-Focused-Window Injection: Automatically injects transcribed text into whichever window has focus
   (VS Code, Chrome, Discord, WhatsApp, Notepad, Excel, Terminal).
3. Clipboard Preservation: Backs up and restores the operator's original clipboard after injection.
4. Non-Blocking Native Message Pump: Uses native user32.RegisterHotKey with zero CPU overhead.
"""

from __future__ import annotations

import ctypes
import logging
import threading
import time
from typing import Any, Dict, Optional

import pyautogui
import speech_recognition as sr
import win32clipboard
import win32con
import win32gui

logger = logging.getLogger("prime.stapler")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

HOTKEY_ID = 8821
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
VK_SPACE = 0x20
WM_HOTKEY = 0x0312


class StaplerDictationEngine:
    """Manages system-wide global dictation hotkey and text injection."""

    _instance: Optional["StaplerDictationEngine"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "StaplerDictationEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.enabled = False
        self._stop_event = threading.Event()
        self._hotkey_thread: Optional[threading.Thread] = None
        self._is_recording = False
        self._record_lock = threading.Lock()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

    def start(self) -> bool:
        """Start global hotkey listener daemon."""
        if self.enabled:
            return True
        self._stop_event.clear()
        self._hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True, name="StaplerHotkeyThread")
        self._hotkey_thread.start()
        self.enabled = True
        logger.info("Stapler System-Wide Dictation active (HotKey: Ctrl+Alt+Space).")
        return True

    def stop(self) -> bool:
        """Stop global hotkey listener daemon."""
        if not self.enabled:
            return True
        self._stop_event.set()
        # Post WM_QUIT to unblock message loop
        if self._hotkey_thread and self._hotkey_thread.ident:
            user32.PostThreadMessageW(self._hotkey_thread.ident, win32con.WM_QUIT, 0, 0)
        self.enabled = False
        logger.info("Stapler System-Wide Dictation deactivated.")
        return True

    def toggle(self) -> bool:
        """Toggle dictation daemon on or off."""
        if self.enabled:
            self.stop()
            return False
        else:
            self.start()
            return True

    def _play_chime(self, freq: int = 800, duration_ms: int = 80):
        """Play discreet acoustic blip for audio feedback."""
        try:
            import winsound
            winsound.Beep(freq, duration_ms)
        except Exception:
            pass

    def record_and_inject(self) -> Dict[str, Any]:
        """Record a single voice utterance and inject directly into the foreground window."""
        with self._record_lock:
            if self._is_recording:
                return {"ok": False, "message": "Already recording"}
            self._is_recording = True

        target_hwnd = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(target_hwnd) if target_hwnd else "Unknown"

        logger.info("[Stapler] Listening for dictation into '%s'...", window_title)
        self._play_chime(1000, 60)

        transcription = ""
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                # Listen with 4s phrase limit for quick dictation bursts
                audio = self.recognizer.listen(source, timeout=4.0, phrase_time_limit=10.0)

            self._play_chime(1200, 50)
            transcription = self.recognizer.recognize_google(audio).strip()
            logger.info("[Stapler] Transcribed: '%s'", transcription)

            if transcription:
                self._inject_text(transcription, target_hwnd)
                self._play_chime(1500, 60)
                return {
                    "ok": True,
                    "text": transcription,
                    "target_window": window_title,
                    "message": f"Injected '{transcription}' into {window_title}",
                }
            else:
                return {"ok": False, "message": "No speech detected"}

        except sr.WaitTimeoutError:
            logger.debug("[Stapler] Dictation timed out waiting for speech")
            self._play_chime(500, 70)
            return {"ok": False, "message": "Listening timed out"}
        except sr.UnknownValueError:
            logger.debug("[Stapler] Could not understand audio")
            self._play_chime(450, 70)
            return {"ok": False, "message": "Could not understand audio"}
        except Exception as e:
            logger.error("[Stapler] Dictation error: %s", e)
            return {"ok": False, "message": str(e)}
        finally:
            with self._record_lock:
                self._is_recording = False

    def _inject_text(self, text: str, target_hwnd: int):
        """Safely injects text into the target window using clipboard paste with state preservation."""
        if not text:
            return

        # Ensure target window still has focus
        try:
            if target_hwnd and win32gui.IsWindow(target_hwnd):
                win32gui.SetForegroundWindow(target_hwnd)
                time.sleep(0.05)
        except Exception:
            pass

        # 1. Backup existing clipboard content
        old_clipboard = ""
        has_old = False
        try:
            for _ in range(3):
                try:
                    win32clipboard.OpenClipboard()
                    try:
                        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                            old_clipboard = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                            has_old = True
                    finally:
                        win32clipboard.CloseClipboard()
                    break
                except Exception:
                    time.sleep(0.02)
        except Exception:
            pass

        # 2. Put transcribed text into clipboard and simulate Ctrl+V
        pasted_ok = False
        try:
            for _ in range(3):
                try:
                    win32clipboard.OpenClipboard()
                    try:
                        win32clipboard.EmptyClipboard()
                        win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text + " ")
                    finally:
                        win32clipboard.CloseClipboard()
                    pasted_ok = True
                    break
                except Exception:
                    time.sleep(0.02)

            if pasted_ok:
                time.sleep(0.04)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.08)
            else:
                pyautogui.typewrite(text + " ", interval=0.01)

        except Exception as paste_err:
            logger.warning("[Stapler] Clipboard paste failed (%s), using direct typewrite", paste_err)
            try:
                pyautogui.typewrite(text + " ", interval=0.01)
            except Exception:
                pass

        # 3. Restore previous clipboard content after small delay
        if has_old:
            def _restore():
                time.sleep(0.5)
                for _ in range(3):
                    try:
                        win32clipboard.OpenClipboard()
                        try:
                            win32clipboard.EmptyClipboard()
                            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, old_clipboard)
                        finally:
                            win32clipboard.CloseClipboard()
                        break
                    except Exception:
                        time.sleep(0.03)
            threading.Thread(target=_restore, daemon=True).start()

    def _hotkey_loop(self):
        """Native Windows message pump listening for Ctrl+Alt+Space with PeekMessageW."""
        thread_id = kernel32.GetCurrentThreadId()
        registered = user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_ALT, VK_SPACE)
        if not registered:
            logger.warning("Could not register Stapler HotKey (Ctrl+Alt+Space). It may already be in use.")
            return

        logger.info("Stapler HotKey message pump started on thread %d", thread_id)
        msg = ctypes.wintypes.MSG()
        PM_REMOVE = 0x0001

        try:
            while not self._stop_event.is_set():
                if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                    if msg.message == win32con.WM_QUIT:
                        break
                    if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                        # Spawn record and inject in a separate thread so message pump is never blocked
                        threading.Thread(target=self.record_and_inject, daemon=True, name="StaplerWorker").start()

                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                else:
                    time.sleep(0.02)
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID)
            logger.info("Stapler HotKey message pump exited and unregistered.")


stapler_engine = StaplerDictationEngine()
