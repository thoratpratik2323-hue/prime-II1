"""
actions/friday_memory.py
Explicit User Preference & Memory Ledger for Prime AI (Inspired by debpalash/friday).

Allows users to explicitly store, recall, and delete personal preferences, working rules,
facts, and corrections that persist across sessions and power intelligent personalization.

NOTE: This module is a thin proxy that delegates to the Prime Master Brain for
multi-layer atomic sync. The FridayMemoryLedger class remains as the durable JSON
persistence layer used internally by Master Brain.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("prime.friday.memory")
MEMORY_FILE = Path(__file__).resolve().parent.parent / "data" / "friday_user_memory.json"


class FridayMemoryLedger:
    """Durable JSON persistence layer for user preferences.
    Master Brain uses this internally for Layer 1 (JSON Ledger) storage."""

    VALID_CATEGORIES = {"preferences", "facts", "rules", "corrections"}

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or MEMORY_FILE
        self.memories: Dict[str, Dict[str, Any]] = self._load_memory()

    def _load_memory(self) -> Dict[str, Dict[str, Any]]:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load memory file: {e}")
        return {}

    def _save_memory(self):
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.memories, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to persist user memory: {e}")

    def remember(self, key: str, value: str, category: str = "preferences") -> Dict[str, Any]:
        """Store or update a user memory. Delegates to Master Brain for atomic multi-layer sync."""
        # Only delegate to Master Brain if this is the global singleton instance
        if self.storage_path == MEMORY_FILE:
            try:
                from core.master_brain import prime_brain
                return prime_brain.remember(key, value, category=category)
            except Exception:
                pass
        # Local-only persist (for test instances or if Master Brain unavailable)
        return self._remember_local(key, value, category)

    def _remember_local(self, key: str, value: str, category: str = "preferences") -> Dict[str, Any]:
        """Fallback: store locally without multi-layer sync."""
        k_clean = key.strip().lower()
        cat_clean = category.strip().lower()
        if cat_clean not in self.VALID_CATEGORIES:
            cat_clean = "preferences"

        entry = {
            "key": k_clean,
            "value": value.strip(),
            "category": cat_clean,
            "updated_at": datetime.now().isoformat()
        }

        self.memories[k_clean] = entry
        self._save_memory()
        logger.info(f"[Friday Memory] Saved {cat_clean} '{k_clean}': '{value}'")
        return {
            "ok": True,
            "message": f"Remembered {cat_clean} for '{key}': {value}",
            "memory": entry,
            "synced_obsidian": False,
            "synced_brain": False
        }

    def recall(self, query: str = "", category: str = "") -> Dict[str, Any]:
        """Search or list memories by query string or category."""
        q = query.strip().lower()
        cat = category.strip().lower()

        matched = []
        for k, item in self.memories.items():
            if cat and item.get("category") != cat:
                continue
            if q:
                search_space = f"{k} {item.get('value', '')} {item.get('category', '')}".lower()
                if q not in search_space:
                    continue
            matched.append(item)

        return {
            "ok": True,
            "count": len(matched),
            "memories": matched
        }

    def forget(self, key: str) -> Dict[str, Any]:
        """Delete a stored memory. Delegates to Master Brain for atomic multi-layer erasure."""
        # Only delegate to Master Brain if this is the global singleton instance
        if self.storage_path == MEMORY_FILE:
            try:
                from core.master_brain import prime_brain
                return prime_brain.forget(key)
            except Exception:
                pass
        # Local-only delete (for test instances or if Master Brain unavailable)
        return self._forget_local(key)

    def _forget_local(self, key: str) -> Dict[str, Any]:
        """Fallback: delete locally without multi-layer sync."""
        k_clean = key.strip().lower()
        if k_clean in self.memories:
            removed = self.memories.pop(k_clean)
            self._save_memory()
            logger.info(f"[Friday Memory] Forgot '{k_clean}'")
            return {
                "ok": True,
                "message": f"Successfully deleted memory '{key}'.",
                "removed": removed,
                "synced_obsidian": False,
                "synced_brain": False
            }
        return {"ok": False, "error": f"No memory found matching '{key}'."}

    def get_system_prompt_context(self) -> str:
        """Synthesize active preferences and rules for LLM prompt injection."""
        if not self.memories:
            return ""

        lines = ["[Active User Preferences & Rules]"]
        for k, v in self.memories.items():
            lines.append(f"- {k.title()}: {v['value']}")
        return "\n".join(lines)


# Global singleton
memory_ledger = FridayMemoryLedger()


def remember_user_preference(key: str, value: str, category: str = "preferences") -> Dict[str, Any]:
    return memory_ledger.remember(key, value, category=category)


def recall_user_preferences(query: str = "", category: str = "") -> Dict[str, Any]:
    return memory_ledger.recall(query=query, category=category)


def forget_user_preference(key: str) -> Dict[str, Any]:
    return memory_ledger.forget(key)
