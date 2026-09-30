"""
actions/opal_ai_copilot.py
On-Device AI Media Copilot & Mood Matcher for Prime AI (Inspired by debpalash/Opal).

Translates natural language mood, vibe, or intent into actionable media:
- "play something chill for coding" -> Lofi Girl / Synthwave
- "breaking news" -> NDTV / BBC News
- "space launch" -> NASA TV Live
- "movies like Interstellar" -> Curated sci-fi recommendation list with plot hook
"""

import logging
import re
from typing import Any, Dict, List, Optional
from actions.opal_iptv import iptv_catalog

logger = logging.getLogger("prime.opal.copilot")

MOOD_VIBE_MAPPINGS = [
    {
        "keywords": ["lofi", "chill", "relax", "study", "homework", "peaceful", "calm", "reading"],
        "channel_id": "lofi_girl",
        "vibe": "Chill Study & Relaxation"
    },
    {
        "keywords": ["coding", "synthwave", "cyberpunk", "hacker", "developer", "night drive", "focus", "programming", "deep work"],
        "channel_id": "synthwave_radio",
        "vibe": "High-Energy Cyberpunk Focus"
    },
    {
        "keywords": ["jazz", "chillhop", "mellow", "groove", "coffee shop"],
        "channel_id": "chillhop_radio",
        "vibe": "Smooth Jazzhop & Mellow Beats"
    },
    {
        "keywords": ["classical", "mozart", "bach", "symphony", "instrumental focus"],
        "channel_id": "classical_focus",
        "vibe": "Classical Cognitive Flow"
    },
    {
        "keywords": ["news", "headlines", "current affairs", "india news", "world news", "politics"],
        "channel_id": "ndtv_news",
        "vibe": "Live Breaking News"
    },
    {
        "keywords": ["space", "nasa", "astronomy", "rocket", "iss", "cosmos"],
        "channel_id": "nasa_tv",
        "vibe": "Outer Space & Science"
    },
    {
        "keywords": ["rain", "thunder", "nature", "forest", "ambient rain", "sleep"],
        "channel_id": "nature_forest_rain",
        "vibe": "Nature & Ambient Rainfall"
    }
]

SIMILAR_MOVIES = {
    "interstellar": [
        {"title": "Arrival (2016)", "reason": "Deep, emotional first-contact sci-fi exploring time and communication."},
        {"title": "Contact (1997)", "reason": "Hard sci-fi about listening to signals from deep space."},
        {"title": "Ad Astra (2019)", "reason": "Visually stunning journey across the solar system with father-son themes."}
    ],
    "inception": [
        {"title": "Shutter Island (2010)", "reason": "Psychological thriller filled with reality-bending twists."},
        {"title": "The Matrix (1999)", "reason": "Philosophical sci-fi questioning simulated realities and consciousness."},
        {"title": "Tenet (2020)", "reason": "Nolan's complex exploration of temporal entropy and time inversion."}
    ]
}


class OpalMediaCopilot:
    """Intelligent media assistant mapping natural prompts to audio/video streams."""

    def __init__(self):
        pass

    def match_media_intent(self, user_prompt: str) -> Dict[str, Any]:
        """Analyze user query and return matched stream, movie recommendation, or YouTube query."""
        prompt = user_prompt.strip().lower()

        # 1. Check for movie recommendation queries ("movies like X", "similar to Y")
        movie_match = re.search(r'(?:movies?|films?|shows?)\s+(?:like|similar to)\s+([a-zA-Z0-9\s]+)', prompt)
        if movie_match:
            target_movie = movie_match.group(1).strip().lower()
            for key, recs in SIMILAR_MOVIES.items():
                if key in target_movie:
                    return {
                        "ok": True,
                        "type": "movie_recommendations",
                        "target": key.title(),
                        "recommendations": recs,
                        "spoken_summary": f"If you loved {key.title()}, here are 3 great films: {recs[0]['title']} and {recs[1]['title']}."
                    }

        # 2. Check curated mood/vibe stream catalog
        for mapping in MOOD_VIBE_MAPPINGS:
            if any(kw in prompt for kw in mapping["keywords"]):
                channel = iptv_catalog.get_channel(mapping["channel_id"])
                if channel:
                    return {
                        "ok": True,
                        "type": "live_stream",
                        "vibe": mapping["vibe"],
                        "matched_channel": channel,
                        "stream_url": channel["url"],
                        "title": channel["name"],
                        "spoken_summary": f"Tuning into {channel['name']} for your {mapping['vibe']} session."
                    }

        # 3. Fallback: Search YouTube video or stream directly
        search_query = prompt
        # Strip common action prefixes
        for prefix in ["play ", "put on ", "stream ", "watch ", "listen to "]:
            if search_query.startswith(prefix):
                search_query = search_query[len(prefix):].strip()

        yt_url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}"
        return {
            "ok": True,
            "type": "youtube_search",
            "vibe": "Custom Search",
            "query": search_query,
            "stream_url": yt_url,
            "title": f"Search: {search_query}",
            "spoken_summary": f"Searching YouTube for '{search_query}'."
        }


# Global singleton
media_copilot = OpalMediaCopilot()


def match_mood_media(vibe_or_prompt: str) -> Dict[str, Any]:
    return media_copilot.match_media_intent(vibe_or_prompt)
