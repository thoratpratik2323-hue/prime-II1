"""
core/intent_router.py — Smart AI Intent Router & Accuracy Engine for IP Prime.

Analyzes user queries to classify intent categories:
- CODING_TASK
- WHATSAPP_ACTION
- SYSTEM_CONTROL
- BROWSER_ACTION
- MEDIA_CONTROL
- OBSIDIAN_KNOWLEDGE
- GENERAL_CONVERSATION

Provides precision accuracy directives and fast-path routing to eliminate
tool hallucinations and parameter mismatch.
"""

from __future__ import annotations

import logging
import re
from typing import Optional, Dict

from core.logging_config import setup_logging
logger = setup_logging("ip_prime.intent_router")

# Intent Categories
INTENT_CODING = "CODING_TASK"
INTENT_WHATSAPP = "WHATSAPP_ACTION"
INTENT_SYSTEM = "SYSTEM_CONTROL"
INTENT_BROWSER = "BROWSER_ACTION"
INTENT_MEDIA = "MEDIA_CONTROL"
INTENT_OBSIDIAN = "OBSIDIAN_KNOWLEDGE"
INTENT_CONVERSATION = "GENERAL_CONVERSATION"

# Fast-path keywords for instant classification (<1ms)
CODING_KEYWORDS = (
    "write a function", "write code", "code this", "debug", "python", "javascript",
    "typescript", "react", "html", "css", "c++", "c#", "java", "sql query",
    "traceback", "syntax error", "refactor", "algorithm", "loop not working",
    "fix this bug", "implement", "unit test", "git commit", "api endpoint",
    "compile", "pull request", "merge conflict", "patch file", "unittest"
)

WHATSAPP_KEYWORDS = (
    "whatsapp", "msg on whatsapp", "message on whatsapp", "send whatsapp",
    "open whatsapp", "call on whatsapp", "whatsapp call", "whatsapp message",
    "read whatsapp", "whatsapp chat"
)

SYSTEM_KEYWORDS = (
    "volume up", "volume down", "mute", "unmute", "set volume", "system info",
    "shutdown", "restart pc", "restart computer", "sleep pc", "lock screen", "lock pc",
    "take screenshot", "save screenshot", "kill process", "close process",
    "cpu usage", "ram usage", "battery status", "hardware health", "power profile"
)

BROWSER_KEYWORDS = (
    "search google", "google search", "search youtube", "open youtube",
    "youtube search", "browse to", "open website", "open url", "search web",
    "search the web", "open chrome", "search online"
)

MEDIA_KEYWORDS = (
    "play music", "pause music", "stop music", "resume music", "next track",
    "previous track", "next song", "previous song", "spotify play", "spotify pause",
    "media control", "volume boost"
)

OBSIDIAN_KEYWORDS = (
    "obsidian", "second brain", "take a note", "save note", "quick note",
    "search notes", "read note", "write note", "knowledge base", "vault"
)

GENERAL_KEYWORDS = (
    "hello", "hi", "how are you", "what is the weather", "good morning",
    "good evening", "good night", "who are you", "tell me a joke", "thank you",
    "what can you do", "introduce yourself"
)

ACCURACY_DIRECTIVES: Dict[str, str] = {
    INTENT_WHATSAPP: (
        "[ACCURACY DIRECTIVE - WHATSAPP]\n"
        "- Prioritize tools: 'sendWhatsAppMessage', 'openWhatsAppChat', 'makeWhatsAppCall', 'listWhatsAppContacts'.\n"
        "- For opening a conversation without sending text, use 'openWhatsAppChat' with 'recipient'.\n"
        "- Clean conversational filler ('ko', 'la', 'to') from contact names. Never invent phone numbers."
    ),
    INTENT_SYSTEM: (
        "[ACCURACY DIRECTIVE - SYSTEM CONTROL]\n"
        "- Prioritize native tools: 'volumeUp', 'volumeDown', 'setVolume', 'muteAudio', 'systemInfo', 'saveScreenshot', 'lockScreen', 'runTerminalCommand'.\n"
        "- Ensure volume amounts are scaled correctly (0 to 100 or 0.0 to 1.0) and avoid destructive commands without intent."
    ),
    INTENT_BROWSER: (
        "[ACCURACY DIRECTIVE - BROWSER & SEARCH]\n"
        "- Prioritize tools: 'searchGoogle', 'searchYouTube', 'openWebsite', 'openApplication'.\n"
        "- When given a direct URL or domain (e.g. github.com, youtube.com), call 'openWebsite' with clean 'url'.\n"
        "- For queries, call 'searchGoogle' or 'searchYouTube' with clean 'query'."
    ),
    INTENT_CODING: (
        "[ACCURACY DIRECTIVE - CODING & DEV]\n"
        "- Prioritize tools: 'createFile', 'readFile', 'patchCodeFile', 'runTerminalCommand', 'runUnitTests', 'gitAutomate'.\n"
        "- Ensure code syntax is valid, file paths exist or are canonical, and verify AST before patching."
    ),
    INTENT_MEDIA: (
        "[ACCURACY DIRECTIVE - MEDIA PLAYBACK]\n"
        "- Prioritize tools: 'mediaControl', 'spotifyControl'.\n"
        "- Valid actions: 'play', 'pause', 'play_pause', 'next', 'previous', 'stop'."
    ),
    INTENT_OBSIDIAN: (
        "[ACCURACY DIRECTIVE - SECOND BRAIN / OBSIDIAN]\n"
        "- Prioritize tools: 'searchObsidianNotes', 'readObsidianNote', 'writeObsidianNote', 'quickNote'.\n"
        "- Keep note titles alphanumeric and concise."
    ),
}

_vectorizer = None
_classifier = None

def _get_classifier():
    global _vectorizer, _classifier
    if _classifier is None:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression

            training_data = [
                ("write a function", 1), ("code this", 1), ("debug this error", 1),
                ("how do i loop", 1), ("python script", 1), ("sql query", 1),
                ("hello", 0), ("how are you", 0), ("what is the weather", 0),
                ("set a reminder", 0), ("open whatsapp", 0), ("good morning", 0)
            ]
            x_train = [text for text, label in training_data]
            y_train = [label for text, label in training_data]

            _vectorizer = TfidfVectorizer()
            x_feat = _vectorizer.fit_transform(x_train)
            _classifier = LogisticRegression()
            _classifier.fit(x_feat, y_train)
        except Exception as e:
            logger.debug("[Router] ML classifier initialization failed: %s", e)
    return _vectorizer, _classifier


def classify_intent(user_message: str) -> str:
    """
    Classify user message into a high-level intent category for accuracy optimization.
    """
    if not user_message:
        return INTENT_CONVERSATION

    msg_lower = user_message.lower().strip()

    # 1. WhatsApp Action
    if any(k in msg_lower for k in WHATSAPP_KEYWORDS) or re.search(r'\b(whatsapp|wa message|wa msg|wa call)\b', msg_lower):
        return INTENT_WHATSAPP

    # 2. System Control
    if any(k in msg_lower for k in SYSTEM_KEYWORDS) or re.search(r'\b(volume|mute|unmute|screenshot|shutdown|restart|battery|cpu|ram)\b', msg_lower):
        return INTENT_SYSTEM

    # 3. Media Control
    if any(k in msg_lower for k in MEDIA_KEYWORDS) or re.search(r'\b(play music|pause music|next song|spotify)\b', msg_lower):
        return INTENT_MEDIA

    # 4. Browser / Search
    if any(k in msg_lower for k in BROWSER_KEYWORDS) or re.search(r'\b(search google|google search|search youtube|search online|open website)\b', msg_lower):
        return INTENT_BROWSER

    # 5. Obsidian / Notes
    if any(k in msg_lower for k in OBSIDIAN_KEYWORDS) or re.search(r'\b(obsidian|second brain|save note|take note)\b', msg_lower):
        return INTENT_OBSIDIAN

    # 6. Coding
    if is_coding_task(user_message):
        return INTENT_CODING

    return INTENT_CONVERSATION


def get_accuracy_directive(intent: str) -> Optional[str]:
    """Return the precision directive for the given intent category, if available."""
    return ACCURACY_DIRECTIVES.get(intent)


def is_coding_task(user_message: str) -> bool:
    """
    Determines if a user query is coding-related using fast keyword heuristics
    and fallback ML classification.
    """
    if not user_message:
        return False

    msg_lower = user_message.lower().strip()

    # Fast-path checks
    if any(k in msg_lower for k in CODING_KEYWORDS):
        logger.info("[Router] Fast-path coding task detected for: '%s'", user_message[:30])
        return True

    if any(msg_lower.startswith(k) for k in GENERAL_KEYWORDS):
        logger.debug("[Router] Fast-path general task detected for: '%s'", user_message[:30])
        return False

    # ML Classifier fallback
    try:
        vect, clf = _get_classifier()
        if vect and clf:
            features = vect.transform([msg_lower])
            pred = clf.predict(features)[0]
            if pred == 1:
                logger.info("[Router] ML coding task detected for: '%s'", user_message[:30])
                return True
    except Exception as e:
        logger.debug("[Router] Classifier prediction failed: %s", e)

    logger.debug("[Router] General task detected for: '%s'", user_message[:30])
    return False
