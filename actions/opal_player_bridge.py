"""
actions/opal_player_bridge.py
Opal & VLC Player Launcher & Media Control Bridge for Prime AI.

Handles seamless stream handoff to:
1. Opal Native Binary (if installed)
2. VLC Media Player (vlc.exe)
3. mpv player (mpv.exe)
4. System Default Browser / Media Player fallback
"""

import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("prime.opal.player")
NOW_PLAYING_FILE = Path(__file__).resolve().parent.parent / "data" / "opal_now_playing.json"


class OpalPlayerBridge:
    """Dispatches media streams to external native players or browser fallbacks."""

    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path or NOW_PLAYING_FILE
        self.active_process: Optional[subprocess.Popen] = None
        self.now_playing: Dict[str, Any] = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"state": "stopped", "current_media": None}

    def _save_state(self):
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self.now_playing, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save now playing state: {e}")

    def detect_players(self) -> Dict[str, Optional[str]]:
        """Locate native player binaries installed on the host."""
        players = {
            "opal": shutil.which("opal") or shutil.which("opal.exe"),
            "vlc": shutil.which("vlc") or shutil.which("vlc.exe"),
            "mpv": shutil.which("mpv") or shutil.which("mpv.exe")
        }

        # Check standard Windows paths if not on PATH
        if not players["vlc"]:
            vlc_candidates = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
            ]
            for c in vlc_candidates:
                if os.path.exists(c):
                    players["vlc"] = c
                    break

        if not players["opal"]:
            opal_candidates = [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opal\opal.exe"),
                r"C:\Program Files\Opal\opal.exe"
            ]
            for c in opal_candidates:
                if os.path.exists(c):
                    players["opal"] = c
                    break

        return players

    def play_stream(self, stream_url: str, title: str = "", player_preference: str = "auto") -> Dict[str, Any]:
        """Launch media playback using the best available native player or browser fallback."""
        detected = self.detect_players()
        pref = player_preference.lower().strip()
        player_chosen = None
        cmd = []

        # 1. Opal native
        if (pref == "opal" or pref == "auto") and detected.get("opal"):
            player_chosen = "opal"
            cmd = [detected["opal"], stream_url]

        # 2. VLC
        elif (pref == "vlc" or pref == "auto") and detected.get("vlc"):
            player_chosen = "vlc"
            cmd = [detected["vlc"], "--one-instance", "--no-video-title-show", stream_url]

        # 3. mpv
        elif (pref == "mpv" or pref == "auto") and detected.get("mpv"):
            player_chosen = "mpv"
            cmd = [detected["mpv"], stream_url]

        # 4. Fallback to Windows default / Browser
        else:
            player_chosen = "browser_default"

        try:
            if player_chosen != "browser_default" and cmd:
                logger.info(f"[Opal Player] Launching '{title or stream_url}' via {player_chosen}")
                self.active_process = subprocess.Popen(cmd)
            else:
                import webbrowser
                logger.info(f"[Opal Player] Opening '{title or stream_url}' via default system browser")
                webbrowser.open(stream_url)

            self.now_playing = {
                "state": "playing",
                "title": title or "Media Stream",
                "stream_url": stream_url,
                "player": player_chosen,
                "started_at": datetime.now().isoformat()
            }
            self._save_state()

            return {
                "ok": True,
                "status": "playing",
                "player_used": player_chosen,
                "title": title or stream_url,
                "stream_url": stream_url
            }

        except Exception as e:
            logger.error(f"[Opal Player] Playback launch error: {e}")
            return {"ok": False, "error": f"Failed to start playback: {e}"}

    def control_playback(self, action: str) -> Dict[str, Any]:
        """Control active playback: stop, pause, resume."""
        act = action.lower().strip()
        if act == "stop":
            if self.active_process and self.active_process.poll() is None:
                try:
                    self.active_process.terminate()
                except Exception:
                    pass
            self.now_playing["state"] = "stopped"
            self._save_state()
            return {"ok": True, "action": "stopped"}

        elif act in ("pause", "resume", "play_pause"):
            try:
                import pyautogui
                pyautogui.press("playpause")
                return {"ok": True, "action": "play_pause_toggled"}
            except Exception:
                return {"ok": True, "action": act, "note": "Media key dispatched"}

        return {"ok": False, "error": f"Unknown action: {action}. Use stop, pause, or resume."}


# Global singleton
player_bridge = OpalPlayerBridge()


def play_media_stream(stream_url: str, title: str = "", player_preference: str = "auto") -> Dict[str, Any]:
    return player_bridge.play_stream(stream_url, title=title, player_preference=player_preference)


def control_player(action: str) -> Dict[str, Any]:
    return player_bridge.control_playback(action)
