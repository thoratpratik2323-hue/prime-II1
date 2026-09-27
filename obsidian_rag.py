"""
Obsidian RAG & Knowledge Base Engine for Prime AI.
Allows Prime to semantically search, read, write, and index notes in the local Obsidian Vault.
Includes BM25 ranking, recursive directory traversal, chunking, and automated decision logging.
"""

from __future__ import annotations

import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VAULT_DIR = Path(__file__).resolve().parent / "Obsidian_Vault"


def get_vault_path() -> Path:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    return VAULT_DIR


def list_notes(recursive: bool = True) -> List[str]:
    """List all markdown notes in the Obsidian Vault."""
    vault = get_vault_path()
    glob_func = vault.rglob if recursive else vault.glob
    notes = []
    for f in glob_func("*.md"):
        if ".obsidian" not in f.parts:
            # Relative path from vault root
            notes.append(str(f.relative_to(vault)).replace("\\", "/"))
    return sorted(notes)


def _tokenize(text: str) -> List[str]:
    """Lowercase and extract alphanumeric word tokens."""
    return re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())


class ObsidianChunk:
    def __init__(self, filename: str, rel_path: str, heading: str, content: str):
        self.filename = filename
        self.rel_path = rel_path
        self.heading = heading
        self.content = content.strip()
        self.tokens = _tokenize(f"{filename} {heading} {self.content}")
        self.length = len(self.tokens)


def _chunk_markdown(rel_path: str, text: str) -> List[ObsidianChunk]:
    """Chunk a markdown document by headings (H1, H2, H3) or double newlines."""
    lines = text.splitlines()
    chunks: List[ObsidianChunk] = []
    curr_heading = Path(rel_path).stem
    curr_lines: List[str] = []

    for line in lines:
        if line.startswith(("# ", "## ", "### ", "#### ")):
            if curr_lines:
                chunk_body = "\n".join(curr_lines).strip()
                if chunk_body:
                    chunks.append(ObsidianChunk(Path(rel_path).name, rel_path, curr_heading, chunk_body))
                curr_lines = []
            curr_heading = line.lstrip("#").strip()
        else:
            curr_lines.append(line)

    if curr_lines:
        chunk_body = "\n".join(curr_lines).strip()
        if chunk_body:
            chunks.append(ObsidianChunk(Path(rel_path).name, rel_path, curr_heading, chunk_body))

    # If document had no headings, treat whole document as one chunk
    if not chunks and text.strip():
        chunks.append(ObsidianChunk(Path(rel_path).name, rel_path, Path(rel_path).stem, text.strip()))

    return chunks


def _load_all_chunks() -> List[ObsidianChunk]:
    """Load and chunk all notes across the vault."""
    vault = get_vault_path()
    all_chunks: List[ObsidianChunk] = []
    for file_path in vault.rglob("*.md"):
        if ".obsidian" in file_path.parts:
            continue
        try:
            rel = str(file_path.relative_to(vault)).replace("\\", "/")
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            all_chunks.extend(_chunk_markdown(rel, content))
        except Exception:
            continue
    return all_chunks


def bm25_search(query: str, chunks: List[ObsidianChunk], k1: float = 1.5, b: float = 0.75) -> List[Tuple[float, ObsidianChunk]]:
    """Compute BM25 scores for query tokens across all chunks."""
    query_tokens = _tokenize(query)
    if not query_tokens or not chunks:
        return []

    total_chunks = len(chunks)
    avg_len = sum(c.length for c in chunks) / max(1, total_chunks)

    # Document frequency
    df: Dict[str, int] = {}
    for c in chunks:
        seen = set(c.tokens)
        for t in query_tokens:
            if t in seen:
                df[t] = df.get(t, 0) + 1

    # IDF calculation
    idf: Dict[str, float] = {}
    for t in query_tokens:
        doc_count = df.get(t, 0)
        idf[t] = math.log(1.0 + (total_chunks - doc_count + 0.5) / (doc_count + 0.5))

    scored: List[Tuple[float, ObsidianChunk]] = []
    for c in chunks:
        score = 0.0
        # Term frequencies in chunk
        tf: Dict[str, int] = {}
        for tok in c.tokens:
            if tok in query_tokens:
                tf[tok] = tf.get(tok, 0) + 1

        for t in query_tokens:
            count = tf.get(t, 0)
            if count > 0:
                cur_idf = idf.get(t, 0.0)
                numerator = count * (k1 + 1.0)
                denominator = count + k1 * (1.0 - b + b * (c.length / max(1.0, avg_len)))
                score += cur_idf * (numerator / denominator)

        # Bonus for exact heading/filename match
        q_lower = query.lower()
        if q_lower in c.heading.lower():
            score += 2.5
        if q_lower in c.filename.lower():
            score += 3.0

        if score > 0.0:
            scored.append((round(score, 3), c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def search_notes(query: str) -> List[Dict[str, Any]]:
    """Search for notes matching the query keywords in title or content (backwards-compatible API)."""
    vault = get_vault_path()
    chunks = _load_all_chunks()
    scored = bm25_search(query, chunks)

    results = []
    seen_files = set()
    for score, chunk in scored:
        if chunk.rel_path in seen_files:
            continue
        seen_files.add(chunk.rel_path)

        snippet = chunk.content[:200].replace("\n", " ") + "..." if len(chunk.content) > 200 else chunk.content
        full_path = (vault / chunk.rel_path).resolve()
        results.append({
            "filename": chunk.filename,
            "title": chunk.heading or Path(chunk.filename).stem,
            "snippet": snippet,
            "path": str(full_path),
            "score": score,
        })
        if len(results) >= 10:
            break

    # Fallback to direct substring search if BM25 found nothing
    if not results:
        query_lower = query.lower()
        for file_path in vault.rglob("*.md"):
            if ".obsidian" in file_path.parts:
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if query_lower in file_path.stem.lower() or query_lower in content.lower():
                    results.append({
                        "filename": file_path.name,
                        "title": file_path.stem,
                        "snippet": content[:180].replace("\n", " ") + "...",
                        "path": str(file_path),
                        "score": 1.0,
                    })
            except Exception:
                continue

    return results[:10]


def query_knowledge_base(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Deep RAG query over the Obsidian Second Brain.
    Returns the most relevant chunks with contextual citations for LLM reasoning.
    """
    chunks = _load_all_chunks()
    scored = bm25_search(query, chunks)
    top_matches = scored[:top_k]

    if not top_matches:
        return {
            "ok": True,
            "query": query,
            "count": 0,
            "context": "No matching knowledge or notes found in the Obsidian Vault.",
            "results": []
        }

    formatted_chunks = []
    results_payload = []
    for score, c in top_matches:
        formatted_chunks.append(
            f"--- [Source: {c.rel_path} | Section: {c.heading} (Relevance: {score})] ---\n{c.content}\n"
        )
        results_payload.append({
            "path": c.rel_path,
            "heading": c.heading,
            "score": score,
            "content": c.content,
        })

    compiled_context = "\n".join(formatted_chunks)
    return {
        "ok": True,
        "query": query,
        "count": len(top_matches),
        "context": compiled_context,
        "results": results_payload
    }


def read_note(note_name: str) -> str:
    """Read the full content of an Obsidian note."""
    vault = get_vault_path().resolve()
    clean_name = note_name.strip().replace("\\", "/")
    if not clean_name.lower().endswith(".md"):
        clean_name += ".md"

    # 1. Try direct path relative to vault
    direct_path = (vault / clean_name).resolve()
    if str(direct_path).startswith(str(vault)) and direct_path.exists() and direct_path.is_file():
        try:
            return direct_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return f"Error reading note '{clean_name}': {e}"

    # 2. Try recursive lookup by stem or basename
    target_stem = Path(clean_name).stem.lower()
    for f in vault.rglob("*.md"):
        if ".obsidian" in f.parts:
            continue
        if f.stem.lower() == target_stem or f.name.lower() == Path(clean_name).name.lower():
            try:
                return f.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                return f"Error reading note '{f.name}': {e}"

    return f"Error: Note '{note_name}' not found in Obsidian Vault."


def write_note(note_name: str, content: str, mode: str = "write") -> str:
    """
    Create or append content to a note in the Obsidian Vault.
    Args:
        note_name: Relative note path (e.g. 'Daily_Notes/2026-09-27' or 'Project Plan')
        content: Markdown content to write
        mode: 'write' (overwrite) or 'append'
    """
    vault = get_vault_path().resolve()
    clean_name = note_name.strip().replace("\\", "/")
    if not clean_name.lower().endswith(".md"):
        clean_name += ".md"

    target_file = (vault / clean_name).resolve()
    if not str(target_file).startswith(str(vault)):
        return "Error: Path traversal attempt detected."

    target_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        if mode == "append" and target_file.exists():
            existing = target_file.read_text(encoding="utf-8", errors="ignore")
            target_file.write_text(existing + "\n\n" + content, encoding="utf-8")
            return f"Successfully appended to note '{target_file.name}' in Obsidian Vault."
        else:
            target_file.write_text(content, encoding="utf-8")
            return f"Successfully saved note '{target_file.name}' in Obsidian Vault."
    except Exception as e:
        return f"Error saving note '{clean_name}': {e}"


def auto_record_session_decision(topic: str, decision: str, details: str = "") -> str:
    """
    Autonomous Second Brain Logging:
    Persists key technical decisions, user preferences, and architectural choices
    into `Obsidian_Vault/DevLogs/Decisions.md`.
    """
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"### [{stamp}] {topic.strip()}\n- **Decision**: {decision.strip()}\n"
    if details:
        entry += f"- **Details**: {details.strip()}\n"

    res = write_note("DevLogs/Decisions.md", entry, mode="append")
    return f"Decision recorded in Second Brain: {res}"


def sync_vault() -> Dict[str, Any]:
    """Scan and return vault health & indexing stats."""
    vault = get_vault_path()
    all_files = list_notes(recursive=True)
    chunks = _load_all_chunks()
    return {
        "ok": True,
        "vault_path": str(vault),
        "total_notes": len(all_files),
        "total_indexed_chunks": len(chunks),
        "notes": all_files[:20],
    }
