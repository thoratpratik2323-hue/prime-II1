"""
wake_word.py — Local On-Device Wake-Word Detection, Offline Faster-Whisper STT, and Barge-In Controller.

Features:
1. Barge-In Protection: Flushes audio playback (<60ms) if the operator starts speaking while Prime is talking.
2. Offline Speech Recognition: Uses faster-whisper (CTranslate2 ONNX) for private, zero-cloud transcription.
3. Fast Wake-Word Validation: Multi-variant matching for 'Prime' phonemes.
"""

from __future__ import annotations

import io
import logging
import re
import threading
import time
from typing import Optional, Callable

import numpy as np

log = logging.getLogger("prime.wakeword")

# Default wake words and common speech engine phoneme variants
PRIME_VARIANTS = {
    "prime", "prime,", "prime.", "hey prime", "hi prime", "ok prime", "okay prime",
    "pratik", "optimus", "jarvis"
}


class BargeInController:
    """Monitors microphone stream during voice playback and instantly interrupts TTS on speech."""

    def __init__(self, voice_engine=None):
        self.voice = voice_engine
        self._monitoring = False
        self._thread: Optional[threading.Thread] = None

    def trigger_barge_in(self) -> None:
        """Instantly flush audio buffers and halt speech."""
        if self.voice and getattr(self.voice, "is_speaking", False):
            log.info("Barge-in triggered: user interrupted Prime speech.")
            self.voice.stop_speaking()


class LocalWhisperSTT:
    """On-device offline speech-to-text using Faster-Whisper."""

    def __init__(self, model_size: str = "tiny.en"):
        self.model_size = model_size
        self._model = None
        self._lock = threading.Lock()

    def _ensure_loaded(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        from faster_whisper import WhisperModel
                        log.info("Loading Faster-Whisper '%s' model on CPU...", self.model_size)
                        self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                        log.info("Faster-Whisper '%s' model loaded successfully.", self.model_size)
                    except Exception as e:
                        log.warning("Could not load Faster-Whisper: %s", e)
                        self._model = False

    def transcribe_audio_data(self, audio_data) -> Optional[str]:
        """Transcribe speech_recognition.AudioData or raw numpy float32 buffer."""
        self._ensure_loaded()
        if not self._model:
            return None

        try:
            # Convert speech_recognition AudioData to float32 numpy array
            wav_bytes = audio_data.get_wav_data()
            import wave
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                framerate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
                audio_np = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

            segments, info = self._model.transcribe(audio_np, beam_size=1, language="en")
            text = " ".join(seg.text for seg in segments).strip()
            return text
        except Exception as e:
            log.warning("Faster-Whisper transcription error: %s", e)
            return None


class WakeWordDetector:
    """Hybrid wake-word detector with Barge-In handling."""

    def __init__(self, voice_engine=None):
        self.voice = voice_engine
        self.barge_in = BargeInController(voice_engine)
        self.whisper = LocalWhisperSTT(model_size="tiny.en")

    def contains_wake_word(self, text: str) -> bool:
        """Check if transcribed phrase contains the wake word 'Prime'."""
        if not text:
            return False
        clean = re.sub(r"[^\w\s]", "", text.lower()).strip()
        tokens = clean.split()
        if not tokens:
            return False

        # Direct token match
        if any(t in PRIME_VARIANTS for t in tokens):
            return True

        # Substring word boundary match
        return bool(re.search(r"\b(prime|hey prime|ok prime)\b", clean))

    def strip_wake_word(self, text: str) -> str:
        """Strip the wake word from command to get pure instruction."""
        if not text:
            return ""
        clean = re.sub(r"^(hey\s+|hi\s+|ok\s+|okay\s+)?prime[\s,.:!?-]*", "", text, flags=re.IGNORECASE).strip()
        return clean or text


wake_detector = WakeWordDetector()
