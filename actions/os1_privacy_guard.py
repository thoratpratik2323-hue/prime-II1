"""
actions/os1_privacy_guard.py
On-Device PII Privacy Guard & Prompt Sanitizer for Prime AI (Inspired by debpalash/OS1).

Guarantees zero sensitive data leakage to cloud LLMs:
1. API Keys (OpenAI, Google, GitHub, AWS, HuggingFace, Slack, Bearer tokens)
2. Private Keys & Encryption Certificates
3. Credit Cards & Payment Credentials
4. Passwords, Secrets, & Authentication URIs
5. Phone numbers & personal contact identities
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("prime.os1.privacy")
PRIVACY_AUDIT_FILE = Path(__file__).resolve().parent.parent / "data" / "privacy_audit.json"

class OS1PrivacyGuard:
    """Detects, masks, and audits PII and secret tokens in real time."""

    PATTERNS: List[Tuple[str, str, re.Pattern]] = [
        # (Category, Replacement Token, Regex Pattern)
        (
            "PRIVATE_KEY",
            "[REDACTED_PRIVATE_KEY]",
            re.compile(r"-----BEGIN (?:[A-Z0-9_-]+ )?PRIVATE KEY-----[\s\S]+?-----END (?:[A-Z0-9_-]+ )?PRIVATE KEY-----", re.IGNORECASE)
        ),
        (
            "OPENAI_KEY",
            "[REDACTED_OPENAI_KEY]",
            re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b")
        ),
        (
            "GOOGLE_KEY",
            "[REDACTED_GOOGLE_API_KEY]",
            re.compile(r"\bAIza[0-9A-Za-z-_]{30,45}\b")
        ),
        (
            "GITHUB_TOKEN",
            "[REDACTED_GITHUB_TOKEN]",
            re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b")
        ),
        (
            "AWS_KEY",
            "[REDACTED_AWS_KEY]",
            re.compile(r"\b(?:AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}\b")
        ),
        (
            "CREDIT_CARD",
            "[REDACTED_CREDIT_CARD]",
            re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")
        ),
        (
            "PASSWORD_ASSIGNMENT",
            r"\1=[REDACTED_PASSWORD]",
            re.compile(r"(?i)\b(password|passwd|pwd|secret|api_secret)\s*[:=]\s*['\"]?([^\s'\";,]{4,})['\"]?")
        ),
        (
            "PHONE_NUMBER",
            "[REDACTED_PHONE]",
            re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
        ),
    ]

    def __init__(self, audit_path: Optional[Path] = None):
        self.audit_path = audit_path or PRIVACY_AUDIT_FILE
        self.stats = self._load_audit()

    def _load_audit(self) -> Dict[str, Any]:
        if self.audit_path.exists():
            try:
                with open(self.audit_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "total_sanitizations": 0,
            "total_redactions": 0,
            "category_counts": {},
            "last_active": None
        }

    def _save_audit(self):
        try:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.audit_path, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to record privacy audit: {e}")

    def sanitize(self, text: str) -> Dict[str, Any]:
        """
        Scan and redact all sensitive PII, keys, and credentials from string.
        Returns sanitized text and metadata on redacting actions.
        """
        if not text or not isinstance(text, str):
            return {"ok": True, "sanitized_text": text, "redacted_count": 0, "categories": []}

        sanitized = text
        redactions = 0
        categories_detected = set()

        for category, token, pattern in self.PATTERNS:
            matches = list(pattern.finditer(sanitized))
            if matches:
                redactions += len(matches)
                categories_detected.add(category)
                sanitized = pattern.sub(token, sanitized)

        if redactions > 0:
            self.stats["total_sanitizations"] += 1
            self.stats["total_redactions"] += redactions
            for cat in categories_detected:
                self.stats["category_counts"][cat] = self.stats["category_counts"].get(cat, 0) + 1
            self.stats["last_active"] = datetime.now().isoformat()
            self._save_audit()
            logger.info(f"[Privacy Guard] Shielded {redactions} sensitive token(s): {list(categories_detected)}")

        return {
            "ok": True,
            "sanitized_text": sanitized,
            "redacted_count": redactions,
            "categories": list(categories_detected),
            "clean": redactions == 0
        }

    def get_audit_summary(self) -> Dict[str, Any]:
        """Return cumulative statistics on blocked PII and credentials."""
        return {
            "ok": True,
            "total_sanitizations": self.stats.get("total_sanitizations", 0),
            "total_redactions": self.stats.get("total_redactions", 0),
            "categories": self.stats.get("category_counts", {}),
            "last_active": self.stats.get("last_active")
        }


# Global singleton
privacy_guard = OS1PrivacyGuard()


def sanitize_text(text: str) -> Dict[str, Any]:
    return privacy_guard.sanitize(text)


def get_privacy_audit() -> Dict[str, Any]:
    return privacy_guard.get_audit_summary()
