"""
Voice Engine for Prime AI.
Provides high-fidelity Voice Synthesis featuring Mark-LIV's signature Gemini "Charon" voice,
Microsoft Edge-TTS neural voices, and offline Windows SAPI5 fallback.
Includes speech recognition with ambient noise adjustment.
"""

from __future__ import annotations

import asyncio
import logging
import os
import queue
import re
import tempfile
import threading
import wave
from typing import Callable, Dict, List, Optional

import edge_tts
import pygame
import pyttsx3
import speech_recognition as sr
from config import config

log = logging.getLogger("prime.voice")

# Mark-LIV Voice Directory
MARK_LIV_GEMINI_VOICES: Dict[str, str] = {
    "charon": "Charon",       # Mark-LIV signature JARVIS (deep, authoritative)
    "puck": "Puck",           # Upbeat, energetic
    "fenrir": "Fenrir",       # Excitable, dynamic
    "kore": "Kore",           # Firm, confident
    "aoede": "Aoede",         # Breezy, calm
}

EDGE_NEURAL_VOICES: Dict[str, str] = {
    "ryan": "en-GB-RyanNeural",              # British JARVIS
    "guy": "en-US-GuyNeural",                # Mark-LIV fallback male
    "christopher": "en-US-ChristopherNeural",# American deep male
}


class VoiceEngine:
    def __init__(self):
        self.tts_queue: queue.Queue[Optional[str]] = queue.Queue()
        self.tts_thread: Optional[threading.Thread] = None
        self._shutdown = threading.Event()
        self._abort_utterance = threading.Event()
        self._is_speaking = False
        self._tts_enabled = config.voice_output
        self.current_voice = config.tts_voice or "Charon"
        self._genai_client = None
        self._genai_api_key = None

        # Speech recognition
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

        # Initialize pygame mixer for audio playback
        try:
            pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=2048)
        except Exception as e:
            log.warning("Could not init pygame.mixer: %s", e)

        # Start TTS background worker
        self._start_tts_worker()

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    @property
    def tts_enabled(self) -> bool:
        return self._tts_enabled

    @tts_enabled.setter
    def tts_enabled(self, val: bool):
        self._tts_enabled = bool(val)

    def set_voice(self, voice_name: str) -> str:
        """Set active voice (e.g. 'charon', 'puck', 'fenrir', 'ryan', 'guy', 'david')."""
        clean = (voice_name or '').strip().lower()
        if not clean:
            return self.current_voice
        resolved = None

        if clean in MARK_LIV_GEMINI_VOICES:
            resolved = MARK_LIV_GEMINI_VOICES[clean]
        elif clean in [v.lower() for v in MARK_LIV_GEMINI_VOICES.values()]:
            resolved = next(v for v in MARK_LIV_GEMINI_VOICES.values() if v.lower() == clean)
        elif clean in EDGE_NEURAL_VOICES:
            resolved = EDGE_NEURAL_VOICES[clean]
        elif clean in [v.lower() for v in EDGE_NEURAL_VOICES.values()]:
            resolved = next(v for v in EDGE_NEURAL_VOICES.values() if v.lower() == clean)
        elif clean in ("david", "offline", "sapi5", "pyttsx3"):
            resolved = "david"
        else:
            # Direct match
            resolved = voice_name.strip()

        self.current_voice = resolved
        config.set_voice(resolved)
        return resolved

    def get_available_voices(self) -> Dict[str, List[str]]:
        return {
            "mark_liv_gemini": list(MARK_LIV_GEMINI_VOICES.values()),
            "edge_neural": list(EDGE_NEURAL_VOICES.values()),
            "offline": ["Microsoft David"],
        }

    def _start_tts_worker(self):
        self._shutdown.clear()
        self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.tts_thread.start()

    def _tts_worker(self):
        """Worker thread that executes TTS playback."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            while not self._shutdown.is_set():
                try:
                    text = self.tts_queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                if text is None:
                    break

                if not self._tts_enabled or not text.strip():
                    self.tts_queue.task_done()
                    continue

                self._abort_utterance.clear()
                self._is_speaking = True
                try:
                    played = False
                    curr = self.current_voice.strip()

                    # 1. Check if configured for Mark-LIV Gemini voice (Charon, Puck, Fenrir, etc.)
                    is_gemini_voice = curr in MARK_LIV_GEMINI_VOICES.values() or curr.lower() in MARK_LIV_GEMINI_VOICES
                    if is_gemini_voice and config.gemini_api_key:
                        target_voice = MARK_LIV_GEMINI_VOICES.get(curr.lower(), curr)
                        played = self._speak_gemini_tts(text, target_voice)

                    # 2. If not Gemini or Gemini failed, try Edge-TTS Neural voice
                    if not played and curr.lower() != "david":
                        edge_voice = EDGE_NEURAL_VOICES.get(curr.lower(), curr if 'neural' in curr.lower() else 'en-GB-RyanNeural')
                        played = loop.run_until_complete(self._speak_edge_tts(text, edge_voice))

                    # 3. Final Fallback: Offline pyttsx3 (Microsoft David)
                    if not played:
                        self._speak_pyttsx3_male(text)

                except Exception as e:
                    log.warning("TTS pipeline error: %s. Falling back to pyttsx3", e)
                    try:
                        self._speak_pyttsx3_male(text)
                    except Exception:
                        pass
                finally:
                    self._is_speaking = False
                    self.tts_queue.task_done()
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
            except Exception:
                pass

    def _speak_gemini_tts(self, text: str, voice_name: str = "Charon") -> bool:
        """Mark-LIV Signature: Synthesize using Google Gemini Speech API (gemini-2.5-flash-preview-tts).
        Uses in-memory PCM playback via sounddevice when available (no disk I/O).
        """
        try:
            if not self._genai_client or self._genai_api_key != config.gemini_api_key:
                from google import genai
                self._genai_client = genai.Client(api_key=config.gemini_api_key)
                self._genai_api_key = config.gemini_api_key
            
            from google.genai import types
            
            resp = self._genai_client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name
                            )
                        )
                    )
                )
            )

            candidate = resp.candidates[0] if (resp and resp.candidates) else None
            content = getattr(candidate, 'content', None) if candidate else None
            if not content or not getattr(content, 'parts', None):
                return False
            inline_data = getattr(content.parts[0], 'inline_data', None)
            if not inline_data or not getattr(inline_data, 'data', None):
                return False
            raw_pcm = inline_data.data
            if isinstance(raw_pcm, str):
                import base64
                raw_pcm = base64.b64decode(raw_pcm)

            # Try in-memory playback via sounddevice (zero disk I/O)
            try:
                import sounddevice as sd
                import numpy as np
                audio_array = np.frombuffer(raw_pcm, dtype=np.int16).astype(np.float32) / 32768.0
                sd.play(audio_array, samplerate=24000, blocking=False)
                # Wait for playback with abort support
                while sd.get_stream().active and not self._abort_utterance.is_set():
                    sd.sleep(50)
                if self._abort_utterance.is_set():
                    sd.stop()
                return True
            except Exception as sd_err:
                log.debug("sounddevice playback failed (%s), falling back to pygame", sd_err)

            # Fallback: pygame via temp file
            temp_wav = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_wav = f.name
                with wave.open(temp_wav, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    wf.writeframes(raw_pcm)

                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=2048)
                clock = pygame.time.Clock()
                try:
                    pygame.mixer.music.load(temp_wav)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy() and not self._abort_utterance.is_set():
                        clock.tick(15)
                finally:
                    try:
                        pygame.mixer.music.stop()
                        pygame.mixer.music.unload()
                    except Exception:
                        pass
                return True
            finally:
                if temp_wav and os.path.exists(temp_wav):
                    try:
                        os.remove(temp_wav)
                    except Exception:
                        pass

        except Exception as e:
            log.debug("Gemini TTS (%s) failed: %s", voice_name, e)
            return False

    async def _speak_edge_tts(self, text: str, voice_name: str = "en-GB-RyanNeural") -> bool:
        """Synthesize with Edge-TTS neural voice and play via pygame."""
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_file = f.name

            comm = edge_tts.Communicate(
                text,
                voice_name,
                rate="+5%",
                volume="+0%",
                pitch="+0Hz"
            )
            await comm.save(temp_file)

            if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
                return False

            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=2048)

            clock = pygame.time.Clock()
            try:
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy() and not self._abort_utterance.is_set():
                    clock.tick(15)
            finally:
                try:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                except Exception:
                    pass

            return True
        except Exception as e:
            log.debug("Edge-TTS speech error: %s", e)
            return False
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    def _speak_pyttsx3_male(self, text: str):
        """Offline fallback using Windows native male voice (David)."""
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", config.voice_rate)
            engine.setProperty("volume", config.voice_volume)

            voices = engine.getProperty("voices")
            for v in voices:
                if "david" in v.name.lower() or "male" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break

            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            log.warning("pyttsx3 offline fallback error: %s", e)

    def speak(self, text: str):
        """Queue text to be spoken."""
        if not self._tts_enabled or not text:
            return
        clean_text = self._sanitize_for_tts(text)
        if clean_text:
            # Check audio cache first
            if clean_text in self._audio_cache:
                self._play_cached_audio(clean_text)
                return
            self.tts_queue.put(clean_text)

    def speak_streamed(self, token_iterator):
        """Accept an iterator/generator of text chunks (streaming LLM tokens).
        Buffers tokens into complete sentences and dispatches each sentence
        to TTS immediately — so sentence 1 plays while the LLM generates sentence 2.
        
        Returns the full accumulated text.
        """
        if not self._tts_enabled:
            # Still consume the iterator to get full text
            return "".join(token_iterator)

        buffer = ""
        full_text = ""
        sentence_endings = re.compile(r'([.!?;:\n])\s*')

        for token in token_iterator:
            if self._abort_utterance.is_set():
                full_text += token
                continue
            buffer += token
            full_text += token

            # Split on sentence boundaries
            parts = sentence_endings.split(buffer)
            if len(parts) > 2:
                # We have at least one complete clause + punctuation
                clause = parts[0] + parts[1]
                buffer = "".join(parts[2:])

                clean = self._sanitize_for_tts(clause)
                if clean and len(clean) > 3:  # Skip tiny fragments
                    self.tts_queue.put(clean)

        # Flush remaining buffer
        if buffer.strip():
            clean = self._sanitize_for_tts(buffer)
            if clean:
                self.tts_queue.put(clean)

        return full_text

    # ── Audio Phrase Cache ──────────────────────────────────────────────
    _audio_cache: dict = {}
    _CACHE_MAX = 50

    def cache_phrase(self, text: str, pcm_data: bytes, sample_rate: int = 24000):
        """Cache a synthesized phrase for instant replay."""
        if len(self._audio_cache) >= self._CACHE_MAX:
            # Evict oldest entry
            oldest = next(iter(self._audio_cache))
            del self._audio_cache[oldest]
        self._audio_cache[text] = (pcm_data, sample_rate)

    def _play_cached_audio(self, text: str):
        """Play a cached audio phrase directly from memory."""
        entry = self._audio_cache.get(text)
        if not entry:
            return
        pcm_data, sample_rate = entry
        try:
            import sounddevice as sd
            import numpy as np
            audio = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
            self._is_speaking = True
            sd.play(audio, samplerate=sample_rate, blocking=False)
            while sd.get_stream().active and not self._abort_utterance.is_set():
                sd.sleep(50)
            if self._abort_utterance.is_set():
                sd.stop()
        except Exception:
            # Fallback: queue normally
            self.tts_queue.put(text)
        finally:
            self._is_speaking = False

    def stop_speaking(self):
        """Cancel ongoing and queued speech."""
        self._abort_utterance.set()
        while not self.tts_queue.empty():
            try:
                self.tts_queue.get_nowait()
                self.tts_queue.task_done()
            except Exception:
                break
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

    def _sanitize_for_tts(self, text: str) -> str:
        if not isinstance(text, str):
            text = str(text)
        text = re.sub(r'```[\s\S]*?```', ' [Code block omitted] ', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)  # inline code
        text = re.sub(r'https?://\S+', '', text)  # URLs
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # markdown links
        text = re.sub(r'[*_~]+([^*_~]+)[*_~]+', r'\1', text)  # bold/italic/strike
        text = re.sub(r'<[^>]+>', '', text)  # strip XML/HTML tags
        text = re.sub(r'^[#*>\-\s]+', '', text, flags=re.MULTILINE)  # headers/bullets
        text = re.sub(r'\|[^\n]+\|', ' ', text)  # tables
        text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u27bf\ufe00-\ufe0f]', '', text)  # emojis+symbols
        return re.sub(r'\s+', ' ', text).strip()

    def listen(self, status_callback: Optional[Callable[[str], None]] = None) -> Optional[str]:
        """Listen to the default microphone and return recognized text.
        Uses on-device Faster-Whisper first for zero cloud latency, with Google Speech fallback.
        """
        try:
            with sr.Microphone() as source:
                if status_callback:
                    status_callback("Adjusting for background noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.8)

                if status_callback:
                    status_callback("Listening... (speak now)")
                audio = self.recognizer.listen(source, timeout=6, phrase_time_limit=15)

                if status_callback:
                    status_callback("Transcribing speech...")

                # Try local offline Faster-Whisper first
                text = None
                try:
                    from wake_word import wake_detector
                    text = wake_detector.whisper.transcribe_audio_data(audio)
                except Exception:
                    pass

                # Fallback to Google Web Speech
                if not text:
                    text = self.recognizer.recognize_google(audio)

                return text.strip() if text else None
        except sr.WaitTimeoutError:
            if status_callback:
                status_callback("Listening timed out (no speech detected).")
            return None
        except sr.UnknownValueError:
            if status_callback:
                status_callback("Could not understand audio.")
            return None
        except sr.RequestError as e:
            if status_callback:
                status_callback(f"Speech recognition service error: {e}")
            return None
        except Exception as e:
            if status_callback:
                status_callback(f"Microphone error: {e}")
            return None

    def listen_one_shot(self, timeout: int = 7) -> Optional[str]:
        """One-shot listen helper for CLI interactive triggers."""
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=12)

                # Try local offline Faster-Whisper first
                text = None
                try:
                    from wake_word import wake_detector
                    text = wake_detector.whisper.transcribe_audio_data(audio)
                except Exception:
                    pass

                if not text:
                    text = self.recognizer.recognize_google(audio)

                return text.strip() if text else None
        except Exception:
            return None


voice = VoiceEngine()
