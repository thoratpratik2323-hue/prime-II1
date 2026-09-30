"""
actions/opal_media_hub.py
Universal Media & Stream Hub for Prime AI (Inspired by debpalash/Opal).

Coordinates:
1. Multi-source search (IPTV channels, YouTube, Local media files)
2. Stream playback launching via OpalPlayerBridge
3. Persistent local watch/stream history in data/opal_history.json
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from actions.opal_iptv import iptv_catalog
from actions.opal_player_bridge import player_bridge
from actions.opal_ai_copilot import media_copilot

logger = logging.getLogger("prime.opal.hub")
HISTORY_FILE = Path(__file__).resolve().parent.parent / "data" / "opal_history.json"


class OpalMediaHub:
    """Universal media aggregator and playback dispatcher."""

    def __init__(self, history_path: Optional[Path] = None):
        self.history_path = history_path or HISTORY_FILE
        self.history: List[Dict[str, Any]] = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        if self.history_path.exists():
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _record_history(self, title: str, url: str, media_type: str, player: str):
        entry = {
            "title": title,
            "url": url,
            "type": media_type,
            "player": player,
            "played_at": datetime.now().isoformat()
        }
        self.history.append(entry)
        self.history = self.history[-150:]  # Retain last 150 items
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save playback history: {e}")

    def search_local_media(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search user's Videos and Music folders for matching media files."""
        results = []
        user_home = Path.home()
        media_dirs = [user_home / "Videos", user_home / "Music"]
        valid_extensions = {".mp4", ".mkv", ".avi", ".mp3", ".flac", ".wav", ".m4a"}

        q = query.lower().strip()
        for mdir in media_dirs:
            if not mdir.exists():
                continue
            try:
                for file_path in mdir.glob("*.*"):
                    if file_path.suffix.lower() in valid_extensions:
                        if not q or q in file_path.stem.lower():
                            results.append({
                                "title": file_path.name,
                                "path": str(file_path),
                                "url": f"file:///{file_path.as_posix()}",
                                "type": "local_file",
                                "extension": file_path.suffix.lower()
                            })
                            if len(results) >= limit:
                                return results
            except Exception:
                continue
        return results

    def universal_search(self, query: str) -> Dict[str, Any]:
        """Aggregate results across IPTV channels, local files, and YouTube."""
        iptv_matches = iptv_catalog.list_channels(query=query).get("channels", [])
        local_matches = self.search_local_media(query, limit=5)
        yt_search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"

        return {
            "ok": True,
            "query": query,
            "results": {
                "iptv_channels": iptv_matches[:5],
                "local_media": local_matches,
                "youtube_stream_url": yt_search_url
            }
        }

    def play_media(self, query_or_url: str, title: str = "", player_preference: str = "auto") -> Dict[str, Any]:
        """Intelligently resolve and launch media stream or file."""
        target_url = query_or_url.strip()
        media_title = title.strip()
        media_type = "stream"

        # Check if direct channel match in IPTV catalog
        channel = iptv_catalog.get_channel(target_url)
        if channel:
            target_url = channel["url"]
            media_title = channel["name"]
            media_type = "iptv_channel"

        # Check if natural language mood prompt
        elif not target_url.startswith(("http://", "https://", "file://", "rtmp://")) and not os.path.exists(target_url):
            matched = media_copilot.match_media_intent(target_url)
            if matched.get("stream_url"):
                target_url = matched["stream_url"]
                media_title = matched.get("title", media_title or query_or_url)
                media_type = matched.get("type", "copilot_match")

        # Launch via player bridge
        launch_res = player_bridge.play_stream(target_url, title=media_title, player_preference=player_preference)
        if launch_res.get("ok"):
            self._record_history(media_title or target_url, target_url, media_type, launch_res.get("player_used", "auto"))

        return {
            "ok": launch_res.get("ok", False),
            "media_title": media_title or target_url,
            "stream_url": target_url,
            "media_type": media_type,
            "player_info": launch_res
        }

    def get_history(self, limit: int = 20) -> Dict[str, Any]:
        """Retrieve recent playback history."""
        return {
            "ok": True,
            "count": len(self.history),
            "recent_plays": list(reversed(self.history[-limit:]))
        }


# Global singleton
media_hub = OpalMediaHub()


def search_universal_media(query: str) -> Dict[str, Any]:
    return media_hub.universal_search(query)


def play_universal_media(query_or_url: str, title: str = "", player_preference: str = "auto") -> Dict[str, Any]:
    return media_hub.play_media(query_or_url, title=title, player_preference=player_preference)


def get_media_playback_history(limit: int = 20) -> Dict[str, Any]:
    return media_hub.get_history(limit=limit)
