"""
actions/dictation_manager.py
System-Wide Native Dictation & Window Typing for Prime AI.
Enables Prime to act as a system-wide speech dictation assistant:
Transcribes voice in real-time and inserts the text directly into
whichever application window is currently active/focused (VS Code,
WhatsApp, Chrome, Notepad, Word, Slack, etc.) using safe clipboard
injection with full clipboard preservation.
"""

from __future__ import annotations

import ctypes
import logging
import threading
import time
from typing import Any, Dict, Optional

import pyperclip

log = logging.getLogger("prime.dictation")

# Win32 API Constants for Keyboard Simulation
VK_CONTROL = 0x11
VK_V = 0x56
VK_RETURN = 0x0D
KEYEVENTF_KEYUP = 0x0002

_DICTATION_ACTIVE = False
_DICTATION_THREAD: Optional[threading.Thread] = None
_DICTATION_STOP_EVENT = threading.Event()


def _get_active_window_title() -> str:
    """Returns the title of the currently focused foreground window on Windows."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "Unknown"
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value or "Active Window"
    except Exception:
        return "Active Window"


def _simulate_paste():
    """Simulates Ctrl+V using Win32 keybd_event with safety delays."""
    user32 = ctypes.windll.user32
    # Ctrl down
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    time.sleep(0.02)
    # V down
    user32.keybd_event(VK_V, 0, 0, 0)
    time.sleep(0.02)
    # V up
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)
    # Ctrl up
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.04)


def _simulate_enter():
    """Simulates Enter key press."""
    user32 = ctypes.windll.user32
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)


def insert_text_into_active_window(
    text: str,
    append_newline: bool = False,
    restore_clipboard: bool = True,
) -> Dict[str, Any]:
    """
    Inserts text directly into the currently focused window at the cursor position.
    Preserves original clipboard contents so the user's copied data is not lost.
    """
    if not text:
        return {"ok": False, "error": "No text provided for dictation."}

    target_window = _get_active_window_title()
    orig_clipboard = None

    try:
        if restore_clipboard:
            try:
                orig_clipboard = pyperclip.paste()
            except Exception:
                orig_clipboard = None

        # Copy text to clipboard
        pyperclip.copy(text)
        time.sleep(0.03)

        # Trigger native paste in focused window
        _simulate_paste()

        if append_newline:
            time.sleep(0.02)
            _simulate_enter()

        # Restore original clipboard
        if restore_clipboard and orig_clipboard is not None:
            time.sleep(0.08)
            try:
                pyperclip.copy(orig_clipboard)
            except Exception:
                pass

        log.info("Dictated %d chars into '%s'", len(text), target_window)
        return {
            "ok": True,
            "target_window": target_window,
            "characters_inserted": len(text),
            "text": text,
            "message": f"Successfully inserted text into '{target_window}'.",
        }
    except Exception as e:
        log.error("Failed to insert text into active window: %s", e)
        return {"ok": False, "error": f"Failed to insert text: {e}"}


def get_dictation_status() -> Dict[str, Any]:
    """Returns whether live dictation listener mode is active."""
    return {
        "ok": True,
        "is_active": _DICTATION_ACTIVE,
        "active_window": _get_active_window_title(),
    }


def start_dictation_session(append_newline: bool = False) -> Dict[str, Any]:
    """
    Starts background live voice dictation. Whatever the user speaks into
    the microphone is typed directly into the active window in real time.
    """
    global _DICTATION_ACTIVE, _DICTATION_THREAD, _DICTATION_STOP_EVENT

    if _DICTATION_ACTIVE:
        return {"ok": True, "message": "Dictation session is already active.", "active_window": _get_active_window_title()}

    _DICTATION_STOP_EVENT.clear()
    _DICTATION_ACTIVE = True

    def _worker():
        import speech_recognition as sr
        from actions.vocal_isolation import apply_vocal_isolation

        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.5

        log.info("Dictation background worker started.")
        while not _DICTATION_STOP_EVENT.is_set():
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    while not _DICTATION_STOP_EVENT.is_set():
                        try:
                            audio = recognizer.listen(source, timeout=2.0, phrase_time_limit=10.0)
                            # Transcribe with Google Speech / local
                            text = recognizer.recognize_google(audio, language="en-US").strip()
                            if text:
                                if any(cmd in text.lower() for cmd in ("stop dictation", "exit dictation", "band karo dictation")):
                                    _DICTATION_STOP_EVENT.set()
                                    break
                                insert_text_into_active_window(text + " ", append_newline=append_newline)
                        except sr.WaitTimeoutError:
                            continue
                        except sr.UnknownValueError:
                            continue
                        except Exception as loop_e:
                            log.debug("Dictation recognition cycle error: %s", loop_e)
                            time.sleep(0.2)
            except Exception as e:
                log.warning("Dictation microphone error: %s. Retrying in 1s...", e)
                time.sleep(1.0)

        global _DICTATION_ACTIVE
        _DICTATION_ACTIVE = False
        log.info("Dictation background worker stopped.")

    _DICTATION_THREAD = threading.Thread(target=_worker, daemon=True)
    _DICTATION_THREAD.start()

    return {
        "ok": True,
        "is_active": True,
        "active_window": _get_active_window_title(),
        "message": "Live voice dictation session started. Speak into your mic to type into the active window.",
    }


def stop_dictation_session() -> Dict[str, Any]:
    """Stops the live background dictation session."""
    global _DICTATION_ACTIVE, _DICTATION_STOP_EVENT
    _DICTATION_STOP_EVENT.set()
    _DICTATION_ACTIVE = False
    return {"ok": True, "is_active": False, "message": "Dictation session stopped."}
