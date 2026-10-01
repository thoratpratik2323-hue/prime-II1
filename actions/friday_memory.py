"""
actions/friday_memory.py
Explicit User Preference & Memory Ledger for Prime AI (Inspired by debpalash/friday).

Allows users to explicitly store, recall, and delete personal preferences, working rules,
facts, and corrections that persist across sessions and power intelligent personalization.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("prime.friday.memory")
MEMORY_FILE = Path(__file__).resolve().parent.parent / "data" / "friday_user_memory.json"


class FridayMemoryLedger:
    """Explicit, user-controlled memory ledger."""

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

    def _sync_to_brain(self, key: str, value: str = "", category: str = "", action: str = "store"):
        """Synchronize memory fact into SQLite brain graph layer."""
        try:
            from memory.brain import store_fact, delete_fact
            if action == "store":
                store_fact(
                    subject="User",
                    predicate=key,
                    obj=value,
                    confidence=1.0,
                    source=f"friday_memory:{category}"
                )
            elif action == "delete":
                delete_fact(subject="User", predicate=key)
        except Exception as e:
            logger.warning(f"Failed to sync fact to brain: {e}")

    def _sync_to_obsidian(self):
        """Synchronize all memories into Obsidian Vault Profile/Preferences.md."""
        try:
            from obsidian_rag import write_note
            lines = [
                "# User Profile & Preferences (Synchronized Second Brain)",
                "",
                f"> Automatically synchronized with Prime Friday Memory Ledger. Total records: {len(self.memories)}.",
                f"> Last sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "| Preference / Rule | Value | Category | Last Updated |",
                "|---|---|---|---|",
            ]
            for k, item in sorted(self.memories.items()):
                val = str(item.get("value", "")).replace("|", "\\|")
                cat = item.get("category", "preferences")
                ts = item.get("updated_at", "")[:19].replace("T", " ")
                lines.append(f"| `{k}` | {val} | `{cat}` | {ts} |")

            write_note("Profile/Preferences.md", "\n".join(lines), mode="write")
        except Exception as e:
            logger.warning(f"Failed to sync to Obsidian Vault: {e}")

    def remember(self, key: str, value: str, category: str = "preferences") -> Dict[str, Any]:
        """Store or update a user memory."""
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
        self._sync_to_brain(k_clean, value.strip(), cat_clean, action="store")
        self._sync_to_obsidian()
        logger.info(f"[Friday Memory] Saved {cat_clean} '{k_clean}': '{value}'")
        return {
            "ok": True,
            "message": f"Remembered {cat_clean} for '{key}': {value} (synced to Second Brain & Obsidian Vault)",
            "memory": entry,
            "synced_obsidian": True,
            "synced_brain": True
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
        """Explicitly delete a stored memory."""
        k_clean = key.strip().lower()
        if k_clean in self.memories:
            removed = self.memories.pop(k_clean)
            self._save_memory()
            self._sync_to_brain(k_clean, action="delete")
            self._sync_to_obsidian()
            logger.info(f"[Friday Memory] Forgot '{k_clean}'")
            return {
                "ok": True,
                "message": f"Successfully deleted memory '{key}' (synced across Second Brain & Obsidian Vault).",
                "removed": removed,
                "synced_obsidian": True,
                "synced_brain": True
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
