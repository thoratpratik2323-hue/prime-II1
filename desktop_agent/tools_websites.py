"""
Website control: open named sites or arbitrary URLs in the default browser.

Uses the OS default-browser handler so the user's real Chrome/Edge/Firefox
opens at the requested destination (independent of the Playwright automation
browser and the in-app holographic BrowserAgent).
"""

from __future__ import annotations

import re
import subprocess
import sys
import webbrowser
from typing import Any, Dict
from urllib.parse import quote

from .registry import ToolError, register

# Named shortcuts the model can request by friendly name.
SITE_URLS: Dict[str, str] = {
    "youtube": "https://www.youtube.com",
    "spotify": "https://open.spotify.com",
    "music": "https://open.spotify.com",
    "songs": "https://open.spotify.com",
    "whatsapp": "https://web.whatsapp.com",
    "telegram": "https://web.telegram.org",
    "discord": "https://discord.com/app",
    "chatgpt": "https://chatgpt.com",
    "openai": "https://chat.openai.com",
    "gemini": "https://gemini.google.com",
    "gmail": "https://mail.google.com",
    "email": "https://mail.google.com",
    "mail": "https://mail.google.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "wikipedia": "https://www.wikipedia.org",
    "reddit": "https://www.reddit.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "linkedin": "https://www.linkedin.com",
    "maps": "https://maps.google.com",
    "translate": "https://translate.google.com",
    "drive": "https://drive.google.com",
    "calendar": "https://calendar.google.com",
    "docs": "https://docs.google.com",
    "google docs": "https://docs.google.com",
    "sheets": "https://sheets.google.com",
    "google sheets": "https://sheets.google.com",
    "excel": "https://sheets.google.com",
    "word": "https://docs.google.com",
    "powerpoint": "https://slides.google.com",
    "slides": "https://slides.google.com",
    "amazon": "https://www.amazon.com",
    "flipkart": "https://www.flipkart.com",
    "netflix": "https://www.netflix.com",
    "prime video": "https://www.primevideo.com",
    "primevideo": "https://www.primevideo.com",
    "hotstar": "https://www.hotstar.com",
    "jiocinema": "https://www.jiocinema.com",
    "jio cinema": "https://www.jiocinema.com",
    "notion": "https://www.notion.so",
    "canva": "https://www.canva.com",
    "slack": "https://app.slack.com",
    "zoom": "https://app.zoom.us/wc",
    "steam": "https://store.steampowered.com",
    "chess": "https://www.chess.com",
    "tradingview": "https://www.tradingview.com",
    "pinterest": "https://www.pinterest.com",
    "twitch": "https://www.twitch.tv",
    "figma": "https://www.figma.com",
    "stack overflow": "https://stackoverflow.com",
    "stackoverflow": "https://stackoverflow.com",
    "huggingface": "https://huggingface.co",
}


def _normalize_url(raw: str) -> str:
    # Strip rogue HTML tags (e.g. <span>.</span>) that models sometimes hallucinate
    url = re.sub(r"<[^>]+>", "", str(raw)).strip()
    if not url:
        raise ToolError("Empty URL.")
    if "://" not in url:
        url = "https://" + url
    return url


def open_url(url: str) -> str:
    """Open a URL in the default browser; returns the resolved URL."""
    url = _normalize_url(url)
    if sys.platform == "win32":
        try:
            subprocess.Popen(f'start "" "{url}"', shell=True)
            return url
        except Exception:
            pass
    ok = webbrowser.open(url, new=2)
    if not ok:
        raise ToolError(f"Failed to open default browser for {url}.")
    return url


@register("openWebsite")
def open_website(args: Dict[str, Any]) -> Dict[str, Any]:
    name = args.get("name")
    url = args.get("url")
    target = str(url or name or "").strip()
    if not target:
        raise ToolError("Provide 'name' (e.g. 'youtube') or 'url'.")

    # Clean out filler words
    cleaned = re.sub(r'\b(open|launch|start|kholo|khol|chalao|karo|website|site|please|the)\b', '', target, flags=re.IGNORECASE).strip()
    if cleaned:
        target = cleaned

    key = target.lower()

    # If it's actually an application, delegate to open_application
    try:
        from .tools_applications import APP_COMMANDS, open_application
        if key in APP_COMMANDS and key not in SITE_URLS and not any(key.endswith(ext) for ext in (".com", ".org", ".net", ".io", ".ai", ".in")):
            return open_application({"name": key})
    except Exception:
        pass

    if key in SITE_URLS:
        final_url = SITE_URLS[key]
    elif "://" in target or target.startswith("www."):
        final_url = target
    elif any(key.endswith(ext) for ext in (".com", ".org", ".net", ".io", ".ai", ".in", ".co", ".app", ".dev", ".edu", ".gov")):
        final_url = target
    else:
        # Check if known prefix
        final_url = f"https://www.{key}.com"

    resolved = open_url(final_url)
    return {"result": f"Opened {resolved} in the default browser."}


# Expose for sibling modules (tools_search).
def _build_search_url(engine: str, query: str) -> str:
    q = quote(query)
    base = {
        "google": f"https://www.google.com/search?q={q}",
        "youtube": f"https://www.youtube.com/results?search_query={q}",
        "github": f"https://github.com/search?q={q}&type=repositories",
        "chatgpt": f"https://www.google.com/search?q={q}",  # no search API
        "duckduckgo": f"https://duckduckgo.com/?q={q}",
        "bing": f"https://www.bing.com/search?q={q}",
        "amazon": f"https://www.amazon.com/s?k={q}",
        "wikipedia": f"https://en.wikipedia.org/w/index.php?search={q}",
    }
    if engine not in base:
        raise ToolError(
            f"Unsupported search engine '{engine}'. Choose from "
            f"{', '.join(sorted(base))}."
        )
    return base[engine]


__all__ = ["open_website", "open_url", "SITE_URLS", "_build_search_url"]
