"""
core/intent_router.py — Smart AI Intent Router for IP Prime.

Analyzes user queries to classify if they are coding-related, using a lightweight
classifier to improve accuracy.
"""

from __future__ import annotations

import logging
from typing import Optional

# Initialize structured logger
from core.logging_config import setup_logging
logger = setup_logging("ip_prime.intent_router")

# Fast-path keywords for instant classification (<1ms)
CODING_KEYWORDS = (
    "write a function", "write code", "code this", "debug", "python", "javascript",
    "typescript", "react", "html", "css", "c++", "c#", "java", "sql query",
    "traceback", "syntax error", "refactor", "algorithm", "loop not working",
    "fix this bug", "implement", "unit test", "git commit", "api endpoint"
)

GENERAL_KEYWORDS = (
    "hello", "hi", "how are you", "what is the weather", "good morning",
    "good evening", "open whatsapp", "set a reminder", "play music", "who are you"
)

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
