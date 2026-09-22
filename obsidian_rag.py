"""
Obsidian RAG & Knowledge Base Engine for Prime AI.
Allows Prime to semantically search, read, and write notes in the local Obsidian Vault.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

VAULT_DIR = Path(__file__).resolve().parent / "Obsidian_Vault"


def get_vault_path() -> Path:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    return VAULT_DIR


def list_notes() -> List[str]:
    """List all markdown notes in the Obsidian Vault."""
    vault = get_vault_path()
    return [f.name for f in vault.glob("*.md")]


def search_notes(query: str) -> List[Dict[str, Any]]:
    """Search for notes matching the query keywords in title or content."""
    vault = get_vault_path()
    query_lower = query.lower()
    results = []

    for file_path in vault.glob("*.md"):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            title_match = query_lower in file_path.stem.lower()
            content_match = query_lower in content.lower()

            if title_match or content_match:
                # Extract matching snippet
                snippet = ""
                if content_match:
                    idx = content.lower().find(query_lower)
                    start = max(0, idx - 80)
                    end = min(len(content), idx + 120)
                    snippet = "..." + content[start:end].replace("\n", " ") + "..."
                else:
                    snippet = content[:150].replace("\n", " ") + "..."

                results.append({
                    "filename": file_path.name,
                    "title": file_path.stem,
                    "snippet": snippet,
                    "path": str(file_path),
                })
        except Exception:
            continue

    return results


def read_note(note_name: str) -> str:
    """Read the full content of an Obsidian note."""
    vault = get_vault_path().resolve()
    safe_name = Path(note_name).name
    if not safe_name.endswith(".md"):
        safe_name += ".md"

    target_file = (vault / safe_name).resolve()
    if not str(target_file).startswith(str(vault)):
        return "Error: Path traversal attempt detected."

    if not target_file.exists():
        # Try finding case-insensitively
        for f in vault.glob("*.md"):
            if f.name.lower() == safe_name.lower() or f.stem.lower() == safe_name.lower().replace(".md", ""):
                target_file = f
                break

    if not target_file.exists():
        return f"Error: Note '{safe_name}' not found in Obsidian Vault."

    try:
        return target_file.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"Error reading note '{safe_name}': {e}"


def write_note(note_name: str, content: str) -> str:
    """Create or append content to a note in the Obsidian Vault."""
    vault = get_vault_path().resolve()
    safe_name = Path(note_name).name
    if not safe_name.endswith(".md"):
        safe_name += ".md"

    target_file = (vault / safe_name).resolve()
    if not str(target_file).startswith(str(vault)):
        return "Error: Path traversal attempt detected."

    try:
        target_file.write_text(content, encoding="utf-8")
        return f"Successfully saved note '{safe_name}' in Obsidian Vault."
    except Exception as e:
        return f"Error saving note '{safe_name}': {e}"
