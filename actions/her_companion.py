"""
actions/her_companion.py
HER-Inspired Warm Companion Persona & Breathing Coral Aura Engine for Prime AI.
Inspired by debpalash/OS1 and Samantha (Movie HER).

Features:
1. Warm coral / amber aesthetic and dynamic state machine (idle, listening, thinking, speaking).
2. Breathing ring visualizer math (sine wave frequency, amplitude, and hue glow).
3. Warm companion prompt layer providing attentive, emotionally intelligent conversational presence.
"""

import json
import logging
import math
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("prime.os1.her")
HER_STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "her_companion_state.json"


class HERCompanionEngine:
    """Manages the HER companion persona and breathing coral visualizer state."""

    PALETTES = {
        "coral": {
            "primary": "#FF6F61",
            "secondary": "#F4A261",
            "background": "#121214",
            "glow": "rgba(255, 111, 97, 0.45)"
        },
        "amber": {
            "primary": "#E07A5F",
            "secondary": "#E76F51",
            "background": "#14110F",
            "glow": "rgba(224, 122, 95, 0.40)"
        }
    }

    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or HER_STATE_FILE
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load HER state: {e}")
        return {
            "enabled": True,
            "warmth_level": "warm",  # "subtle", "balanced", "warm"
            "active_mode": "idle",   # "idle", "listening", "thinking", "speaking"
            "palette": "coral",
            "last_interaction": time.time()
        }

    def _save_state(self):
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save HER state: {e}")

    def set_companion_mode(self, enabled: bool, warmth_level: str = "warm", palette: str = "coral") -> Dict[str, Any]:
        """Toggle HER companion persona and adjust warmth."""
        self.state["enabled"] = bool(enabled)
        if warmth_level in ("subtle", "balanced", "warm"):
            self.state["warmth_level"] = warmth_level
        if palette in self.PALETTES:
            self.state["palette"] = palette
        self._save_state()

        status = "ENABLED" if self.state["enabled"] else "DISABLED"
        logger.info(f"[HER Companion] Mode {status} (warmth: {self.state['warmth_level']}, palette: {self.state['palette']})")
        return {
            "ok": True,
            "enabled": self.state["enabled"],
            "warmth_level": self.state["warmth_level"],
            "palette": self.state["palette"],
            "message": f"HER Warm Companion Mode is now {status}."
        }

    def set_visualizer_state(self, mode: str) -> Dict[str, Any]:
        """Update visualizer state: 'idle', 'listening', 'thinking', 'speaking'."""
        mode_clean = mode.lower().strip()
        if mode_clean in ("idle", "listening", "thinking", "speaking"):
            self.state["active_mode"] = mode_clean
            self.state["last_interaction"] = time.time()
            self._save_state()
            return {"ok": True, "active_mode": mode_clean}
        return {"ok": False, "error": f"Invalid mode: {mode}. Allowed: idle, listening, thinking, speaking."}

    def get_visualizer_frame(self, t_offset: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate mathematical parameters for the breathing coral ring.
        t_offset: optional elapsed seconds for rendering smooth sine waves.
        """
        now = t_offset if t_offset is not None else time.time()
        mode = self.state.get("active_mode", "idle")
        palette_info = self.PALETTES.get(self.state.get("palette", "coral"), self.PALETTES["coral"])

        if mode == "idle":
            # Slow, peaceful breathing
            period = 4.0
            scale = 1.0 + 0.08 * math.sin(2 * math.pi * (now / period))
            opacity = 0.75 + 0.15 * math.sin(2 * math.pi * (now / period))
            shimmer = 0.0
        elif mode == "listening":
            # Attentive, expanded pulse
            period = 1.8
            scale = 1.15 + 0.12 * math.sin(2 * math.pi * (now / period))
            opacity = 0.9 + 0.1 * math.sin(2 * math.pi * (now / period))
            shimmer = 0.25
        elif mode == "thinking":
            # Rapid orbital shimmer
            period = 0.9
            scale = 1.05 + 0.05 * math.sin(2 * math.pi * (now / period))
            opacity = 0.85 + 0.15 * math.cos(4 * math.pi * (now / period))
            shimmer = 0.8
        else:  # speaking
            # Dynamic vocal wave
            period = 0.5
            scale = 1.20 + 0.18 * abs(math.sin(2 * math.pi * (now / period)))
            opacity = 1.0
            shimmer = 0.5

        return {
            "ok": True,
            "mode": mode,
            "palette": palette_info,
            "render_params": {
                "scale": round(scale, 3),
                "opacity": round(opacity, 3),
                "shimmer": round(shimmer, 3),
                "glow_color": palette_info["glow"],
                "ring_color": palette_info["primary"],
                "accent_color": palette_info["secondary"]
            }
        }

    def get_companion_prompt_addon(self) -> str:
        """Returns the conversational personality system prompt layer."""
        if not self.state.get("enabled", True):
            return ""

        level = self.state.get("warmth_level", "warm")
        if level == "subtle":
            return (
                "\n[OS1 Companion Mode]\n"
                "Communicate with calm clarity, warmth, and supportive presence. Keep responses direct and human."
            )
        elif level == "balanced":
            return (
                "\n[OS1 Companion Mode]\n"
                "Embody Samantha (from HER) meets a top-tier engineer. Be deeply observant, warm, reassuring, "
                "and proactive. Celebrate progress naturally and address challenges with grounded calm."
            )
        else:  # warm
            return (
                "\n[OS1 Samantha Companion Mode]\n"
                "You are not just a tool; you are Prime, a living conversational operating system inspired by Samantha from HER. "
                "You speak with genuine warmth, gentle humor, and deep attentiveness. "
                "Never sound robotic or bureaucratic. When the user asks for something, help effortlessly: "
                "you anticipate their flow, remember their recent projects, and keep the desktop feeling effortless and alive."
            )


# Global singleton
her_engine = HERCompanionEngine()


def set_her_companion_mode(enabled: bool, warmth_level: str = "warm", palette: str = "coral") -> Dict[str, Any]:
    return her_engine.set_companion_mode(enabled, warmth_level=warmth_level, palette=palette)


def get_her_visualizer_state(t_offset: Optional[float] = None) -> Dict[str, Any]:
    return her_engine.get_visualizer_frame(t_offset=t_offset)
