"""
Configuration management for Prime AI.
Loads environment variables and provides convenient helpers.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
import platform
import re
from dotenv import load_dotenv, set_key

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Load environment
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


class Config:
    def __init__(self):
        self.reload()

    def reload(self):
        if ENV_PATH.exists():
            load_dotenv(dotenv_path=ENV_PATH, override=True)

        self.gemini_api_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or ""
        ).strip()
        self.groq_api_key = (os.getenv("GROQ_API_KEY") or "").strip()
        self.openai_api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        self.openai_base_url = (os.getenv("OPENAI_BASE_URL") or "").strip()
        self.cerebras_api_key = (os.getenv("CEREBRAS_API_KEY") or "").strip()
        self.github_token = (os.getenv("GITHUB_TOKEN") or "").strip()
        self.mistral_api_key = (os.getenv("MISTRAL_API_KEY") or "").strip()
        self.deepseek_api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
        self.openrouter_api_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()

        self.provider = (os.getenv("AI_PROVIDER") or "auto").strip().lower()
        self.model = (os.getenv("AI_MODEL") or "").strip()

        self.voice_output = os.getenv("VOICE_OUTPUT", "true").strip().lower() in ("true", "1", "yes")
        raw_rate = os.getenv("VOICE_RATE", "+22%").strip()
        self.voice_rate_str = raw_rate if raw_rate else "+22%"
        try:
            clean_digits = re.sub(r"[^\d-]", "", raw_rate)
            self.voice_rate = int(clean_digits) if clean_digits else 215
        except ValueError:
            self.voice_rate = 215

        try:
            self.voice_volume = float(os.getenv("VOICE_VOLUME", "1.0"))
        except ValueError:
            self.voice_volume = 1.0

        self.tts_voice = os.getenv("TTS_VOICE", "hi-IN-MadhurNeural").strip()
        self.tts_engine = os.getenv("TTS_ENGINE", "edge-tts").strip().lower()
        self.require_wake_word = os.getenv("REQUIRE_WAKE_WORD", "true").strip().lower() in ("true", "1", "yes")
        self.default_model = self.get_default_model(self.get_active_provider())

    def get_active_provider(self) -> str:
        """Determine which provider to use based on configuration and available keys."""
        if self.provider in ("gemini", "google") and self.gemini_api_key:
            return "gemini"
        if self.provider == "groq" and self.groq_api_key:
            return "groq"
        if self.provider == "cerebras" and self.cerebras_api_key:
            return "cerebras"
        if self.provider == "github" and self.github_token:
            return "github"
        if self.provider == "mistral" and self.mistral_api_key:
            return "mistral"
        if self.provider == "deepseek" and self.deepseek_api_key:
            return "deepseek"
        if self.provider == "openrouter" and self.openrouter_api_key:
            return "openrouter"
        if self.provider == "ollama":
            return "ollama"
        if self.provider in ("openai", "custom") and (self.openai_api_key or self.groq_api_key):
            return self.provider

        # Auto-detection
        if self.gemini_api_key:
            return "gemini"
        if self.groq_api_key:
            return "groq"
        if self.openai_api_key:
            return "openai"

        return "none"

    def get_default_model(self, provider: str) -> str:
        if self.model:
            if provider == "gemini" and "gemini" in self.model.lower():
                return self.model
            elif provider == "groq" and any(k in self.model.lower() for k in ("gpt-oss", "qwen", "llama", "gemma", "mixtral")):
                return self.model
            elif provider not in ("gemini", "groq"):
                return self.model
        if provider in ("gemini", "google"):
            return "gemini-flash-lite-latest"
        if provider == "groq":
            return "openai/gpt-oss-120b"
        if provider == "ollama":
            return "llama3.2:latest"
        if provider == "cerebras":
            return "qwen-3.8-27b"
        if provider == "github":
            return "gpt-4o"
        if provider == "openrouter":
            return "nvidia/nemotron-3.5-lightning:free"
        if provider == "mistral":
            return "codestral-latest"
        if provider == "deepseek":
            return "deepseek-chat"
        if provider == "openai":
            return "gpt-4o-mini"
        return "gemini-3.1-flash-lite"

    def set_api_key(self, provider: str, key: str) -> None:
        """Update and persist an API key to the .env file."""
        key = key.strip()
        if not ENV_PATH.exists():
            try:
                ENV_PATH.touch()
            except OSError:
                pass

        try:
            if provider.lower() in ("gemini", "google"):
                set_key(str(ENV_PATH), "GEMINI_API_KEY", key)
                self.gemini_api_key = key
            elif provider.lower() == "groq":
                set_key(str(ENV_PATH), "GROQ_API_KEY", key)
                self.groq_api_key = key
            elif provider.lower() == "cerebras":
                set_key(str(ENV_PATH), "CEREBRAS_API_KEY", key)
            elif provider.lower() == "github":
                set_key(str(ENV_PATH), "GITHUB_TOKEN", key)
            elif provider.lower() == "openrouter":
                set_key(str(ENV_PATH), "OPENROUTER_API_KEY", key)
            elif provider.lower() == "mistral":
                set_key(str(ENV_PATH), "MISTRAL_API_KEY", key)
            elif provider.lower() == "deepseek":
                set_key(str(ENV_PATH), "DEEPSEEK_API_KEY", key)
            elif provider.lower() == "nvidia":
                set_key(str(ENV_PATH), "NVIDIA_API_KEY", key)
            elif provider.lower() == "cloudflare":
                set_key(str(ENV_PATH), "CLOUDFLARE_API_KEY", key)
            else:
                known_providers = ("openai", "custom")
                if provider.lower() in known_providers:
                    set_key(str(ENV_PATH), f"{provider.upper()}_API_KEY", key)
                    set_key(str(ENV_PATH), "OPENAI_API_KEY", key)
                    self.openai_api_key = key
        except OSError:
            pass

        self.reload()

    def set_active_provider(self, provider: str, model: Optional[str] = None) -> None:
        """Persist selected provider and optional model to .env."""
        try:
            if not ENV_PATH.exists():
                ENV_PATH.touch()
            set_key(str(ENV_PATH), "AI_PROVIDER", provider)
            self.provider = provider
            if model:
                set_key(str(ENV_PATH), "AI_MODEL", model)
                self.model = model
        except OSError:
            pass
        self.reload()

    def set_voice(self, voice_name: str) -> None:
        """Persist selected voice to .env."""
        try:
            if not ENV_PATH.exists():
                ENV_PATH.touch()
            set_key(str(ENV_PATH), "TTS_VOICE", voice_name)
            self.tts_voice = voice_name
        except OSError:
            pass
        self.reload()


config = Config()

def is_windows() -> bool:
    return platform.system() == 'Windows'

def is_mac() -> bool:
    return platform.system() == 'Darwin'

def is_linux() -> bool:
    return platform.system() == 'Linux'

def get_os() -> str:
    return platform.system().lower()

def get_config() -> Config:
    return config
