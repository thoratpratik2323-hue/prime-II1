"""
actions/voice_studio_manager.py
VoiceStudio Local Integration & Voice Cloning / Voice Design Manager for Prime AI.
Interfaces with debpalash/VoiceStudio (port 3900) for fully-local ElevenLabs-quality
voice cloning, prompt-driven voice design, and offline profile management.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from actions.vocal_isolation import clean_audio_file
from config import BASE_DIR, config

log = logging.getLogger("prime.voice_studio")

VOICESTUDIO_HOST = os.getenv("VOICESTUDIO_HOST", "http://127.0.0.1:3900").rstrip("/")
PROFILES_DIR = BASE_DIR / "Obsidian_Vault" / "VoiceProfiles"
PROFILES_FILE = PROFILES_DIR / "profiles.json"


def _ensure_profiles_dir() -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    if not PROFILES_FILE.exists():
        initial = {
            "version": "1.0",
            "profiles": {
                "ultron": {
                    "id": "ultron",
                    "name": "Ultron (Sagar Tamang Baritone)",
                    "type": "preset",
                    "description": "Deep commanding metallic baritone with Stark Intercom DSP filter",
                    "filter_enabled": True,
                    "filter_intensity": 0.75,
                },
                "friday": {
                    "id": "friday",
                    "name": "F.R.I.D.A.Y. (Sagar Tamang Nova)",
                    "type": "preset",
                    "description": "Clear natural female AI assistant",
                    "filter_enabled": False,
                },
                "charon": {
                    "id": "charon",
                    "name": "Mark-LIV Charon",
                    "type": "preset",
                    "description": "Authoritative deep Gemini neural voice",
                    "filter_enabled": True,
                    "filter_intensity": 0.65,
                },
            },
        }
        PROFILES_FILE.write_text(json.dumps(initial, indent=2), encoding="utf-8")
    return PROFILES_FILE


def check_voicestudio_connection() -> Dict[str, Any]:
    """Check whether local VoiceStudio server is running on port 3900."""
    url = f"{VOICESTUDIO_HOST}/.well-known/voicestudio-speech"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = resp.read().decode("utf-8")
            return {
                "ok": True,
                "online": True,
                "host": VOICESTUDIO_HOST,
                "details": json.loads(data) if data.startswith("{") else data[:100],
            }
    except Exception as e:
        return {
            "ok": True,
            "online": False,
            "host": VOICESTUDIO_HOST,
            "message": f"VoiceStudio server is not running at {VOICESTUDIO_HOST}. Offline fallback active.",
        }


def list_voice_profiles() -> Dict[str, Any]:
    """Lists all available voice profiles: built-in presets, cloned voices, and designed personas."""
    _ensure_profiles_dir()
    try:
        data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
        profiles = data.get("profiles", {})
    except Exception as e:
        profiles = {}

    vs_status = check_voicestudio_connection()
    remote_voices = []

    if vs_status.get("online"):
        try:
            req = urllib.request.Request(f"{VOICESTUDIO_HOST}/v1/voices", method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                remote_data = json.loads(resp.read().decode("utf-8"))
                remote_voices = remote_data.get("voices", [])
        except Exception:
            pass

    return {
        "ok": True,
        "voicestudio_online": vs_status.get("online", False),
        "local_profiles": list(profiles.values()),
        "voicestudio_voices": remote_voices,
        "total": len(profiles) + len(remote_voices),
    }


def clone_voice(
    sample_path: str,
    profile_name: str,
    language: str = "en",
    clean_sample: bool = True,
) -> Dict[str, Any]:
    """
    Clones a voice from a reference audio file (.wav or .mp3).
    Pre-cleans the audio with vocal isolation to remove background hiss/fan noise,
    then registers the cloned voice with local VoiceStudio and saves the profile.
    """
    p = Path(sample_path)
    if not p.exists():
        return {"ok": False, "error": f"Reference audio file not found: {sample_path}"}

    processed_sample = str(p)
    if clean_sample:
        clean_res = clean_audio_file(str(p))
        if clean_res.get("ok"):
            processed_sample = clean_res.get("cleaned_path", str(p))

    profile_id = f"cloned_{profile_name.lower().replace(' ', '_')}"

    # Check VoiceStudio daemon
    vs_status = check_voicestudio_connection()
    remote_profile_id = None

    if vs_status.get("online"):
        try:
            with open(processed_sample, "rb") as af:
                b64_audio = base64.b64encode(af.read()).decode("utf-8")
            payload = {
                "name": profile_name,
                "audio_base64": b64_audio,
                "language": language,
            }
            req = urllib.request.Request(
                f"{VOICESTUDIO_HOST}/v1/voices/clone",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                remote_profile_id = res_data.get("profile_id") or res_data.get("id")
        except Exception as e:
            log.warning("VoiceStudio remote cloning call failed (%s), registering locally.", e)

    # Save to local profile registry
    _ensure_profiles_dir()
    try:
        data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
        profiles = data.get("profiles", {})
    except Exception:
        profiles = {}

    profile_entry = {
        "id": profile_id,
        "name": profile_name,
        "type": "cloned",
        "sample_path": processed_sample,
        "language": language,
        "remote_profile_id": remote_profile_id,
        "created_at": str(Path(sample_path).stat().st_mtime),
    }
    profiles[profile_id] = profile_entry
    PROFILES_FILE.write_text(json.dumps({"version": "1.0", "profiles": profiles}, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "profile_id": profile_id,
        "name": profile_name,
        "sample_path": processed_sample,
        "voicestudio_synced": bool(remote_profile_id),
        "message": f"Voice successfully cloned and registered as '{profile_name}' (ID: {profile_id}).",
    }


def design_voice(description: str, profile_name: str) -> Dict[str, Any]:
    """
    Designs a custom voice persona from a prompt description (e.g., 'Deep resonant British male butler').
    Maps attributes (pitch, age, gender, accent, style) and registers a new profile.
    """
    if not description or not profile_name:
        return {"ok": False, "error": "Description and profile_name are required."}

    profile_id = f"designed_{profile_name.lower().replace(' ', '_')}"
    desc_lower = description.lower()

    # Attribute mapping heuristics
    gender = "female" if any(w in desc_lower for w in ("female", "woman", "girl", "lady", "queen")) else "male"
    pitch = "low" if any(w in desc_lower for w in ("deep", "baritone", "bass", "low")) else "high" if "high" in desc_lower else "normal"
    accent = "en-GB" if any(w in desc_lower for w in ("british", "uk", "english", "butler", "jarvis")) else "en-US"
    style = "cinematic" if any(w in desc_lower for w in ("metallic", "robot", "ultron", "intercom", "armor")) else "natural"

    vs_status = check_voicestudio_connection()
    remote_profile_id = None

    if vs_status.get("online"):
        try:
            payload = {
                "name": profile_name,
                "description": description,
                "gender": gender,
                "pitch": pitch,
                "accent": accent,
            }
            req = urllib.request.Request(
                f"{VOICESTUDIO_HOST}/v1/voices/design",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20.0) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                remote_profile_id = res_data.get("profile_id") or res_data.get("id")
        except Exception as e:
            log.warning("VoiceStudio remote design call failed (%s), registering locally.", e)

    _ensure_profiles_dir()
    try:
        data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
        profiles = data.get("profiles", {})
    except Exception:
        profiles = {}

    profile_entry = {
        "id": profile_id,
        "name": profile_name,
        "type": "designed",
        "description": description,
        "attributes": {
            "gender": gender,
            "pitch": pitch,
            "accent": accent,
            "style": style,
        },
        "remote_profile_id": remote_profile_id,
    }
    profiles[profile_id] = profile_entry
    PROFILES_FILE.write_text(json.dumps({"version": "1.0", "profiles": profiles}, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "profile_id": profile_id,
        "name": profile_name,
        "description": description,
        "attributes": profile_entry["attributes"],
        "voicestudio_synced": bool(remote_profile_id),
        "message": f"Voice persona successfully designed and saved as '{profile_name}' (ID: {profile_id}).",
    }


def set_active_voice_profile(profile_id: str) -> Dict[str, Any]:
    """Switches Prime's active voice to the given voice profile ID or preset name."""
    try:
        from voice_engine import voice

        resolved = voice.set_voice(profile_id)
        return {
            "ok": True,
            "active_voice": resolved,
            "message": f"Prime voice profile successfully set to '{resolved}'.",
        }
    except Exception as e:
        return {"ok": False, "error": f"Failed to set voice profile: {e}"}
