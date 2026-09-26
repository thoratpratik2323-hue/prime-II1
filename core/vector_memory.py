"""
Semantic Vector Memory and Dev Log Crystallizer for Prime AI.
Enables high-speed TF-IDF and cosine-similarity semantic retrieval over Obsidian Vault notes
and crystallizes structured dev logs directly into Obsidian with automatic vector indexing.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

log = logging.getLogger("prime.vector_memory")

VAULT_DIR = Path(__file__).resolve().parent.parent / "Obsidian_Vault"
CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "vector_memory_cache.json"

STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had",
    "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd",
    "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's",
    "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll",
    "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's",
    "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't",
    "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}


def tokenize(text: str) -> List[str]:
    """Tokenize and normalize text into clean stems/words."""
    if not text:
        return []
    words = re.findall(r"\b[a-zA-Z0-9_\-#]{2,}\b", text.lower())
    return [w for w in words if w not in STOPWORDS]


class VectorMemoryIndex:
    """In-memory Vector TF-IDF & Cosine Similarity search index."""

    def __init__(self, cache_file: Optional[Path] = None):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.doc_vectors: Dict[str, Dict[str, float]] = {}
        self.doc_norms: Dict[str, float] = {}
        self.idf: Dict[str, float] = {}
        self.cache_file = cache_file or CACHE_FILE
        self._load_cache()

    def add_document(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add or update a document in the index."""
        meta = metadata or {}
        tokens = tokenize(text)
        self.documents[doc_id] = {
            "id": doc_id,
            "text": text,
            "tokens": tokens,
            "metadata": meta,
            "updated_at": time.time()
        }
        self._recompute_index()

    def add_documents(self, docs: List[Dict[str, Any]]) -> None:
        """Add multiple documents in a batch."""
        for d in docs:
            doc_id = d.get("id") or str(d.get("path") or d.get("title") or time.time())
            text = d.get("text") or d.get("content") or ""
            meta = d.get("metadata") or {k: v for k, v in d.items() if k not in ("id", "text", "content")}
            tokens = tokenize(text)
            self.documents[doc_id] = {
                "id": doc_id,
                "text": text,
                "tokens": tokens,
                "metadata": meta,
                "updated_at": time.time()
            }
        self._recompute_index()

    def _recompute_index(self) -> None:
        """Compute IDFs and Document TF-IDF vectors."""
        n_docs = len(self.documents)
        if n_docs == 0:
            self.idf.clear()
            self.doc_vectors.clear()
            self.doc_norms.clear()
            return

        # 1. Document frequency (DF)
        df: Dict[str, int] = defaultdict(int)
        for doc in self.documents.values():
            unique_terms = set(doc["tokens"])
            for t in unique_terms:
                df[t] += 1

        # 2. IDF calculation: log((1 + N) / (1 + df)) + 1
        self.idf = {
            term: math.log((1.0 + n_docs) / (1.0 + freq)) + 1.0
            for term, freq in df.items()
        }

        # 3. TF-IDF vectors and norms
        self.doc_vectors.clear()
        self.doc_norms.clear()
        for doc_id, doc in self.documents.items():
            tokens = doc["tokens"]
            if not tokens:
                self.doc_vectors[doc_id] = {}
                self.doc_norms[doc_id] = 0.0
                continue

            tf = Counter(tokens)
            total = float(len(tokens))
            vec: Dict[str, float] = {}
            norm_sq = 0.0
            for term, count in tf.items():
                tfidf = (count / total) * self.idf.get(term, 1.0)
                vec[term] = tfidf
                norm_sq += tfidf * tfidf

            self.doc_vectors[doc_id] = vec
            self.doc_norms[doc_id] = math.sqrt(norm_sq)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic cosine-similarity search for a query string."""
        if not self.documents or not query.strip():
            return []

        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        # Build query TF-IDF vector
        q_tf = Counter(q_tokens)
        q_total = float(len(q_tokens))
        q_vec: Dict[str, float] = {}
        q_norm_sq = 0.0
        for term, count in q_tf.items():
            tfidf = (count / q_total) * self.idf.get(term, 1.0)
            q_vec[term] = tfidf
            q_norm_sq += tfidf * tfidf

        q_norm = math.sqrt(q_norm_sq)
        if q_norm == 0.0:
            return []

        scores: List[Tuple[str, float]] = []
        for doc_id, d_vec in self.doc_vectors.items():
            d_norm = self.doc_norms.get(doc_id, 0.0)
            if d_norm == 0.0:
                continue

            # Dot product
            dot = 0.0
            for term, q_val in q_vec.items():
                if term in d_vec:
                    dot += q_val * d_vec[term]

            score = dot / (q_norm * d_norm)
            if score > 0.001:
                scores.append((doc_id, score))

        # Sort descending by score
        scores.sort(key=lambda x: x[1], reverse=True)

        results: List[Dict[str, Any]] = []
        for doc_id, score in scores[:top_k]:
            doc = self.documents[doc_id]
            text = doc["text"]
            snippet = text[:200].replace("\n", " ") + ("..." if len(text) > 200 else "")
            results.append({
                "id": doc_id,
                "score": round(score, 4),
                "snippet": snippet,
                "metadata": doc.get("metadata", {}),
                "full_text": text
            })
        return results

    def save_cache(self) -> None:
        """Persist indexed docs to disk cache."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            export_data = {
                doc_id: {
                    "text": d["text"],
                    "metadata": d["metadata"],
                    "updated_at": d.get("updated_at", time.time())
                }
                for doc_id, d in self.documents.items()
            }
            self.cache_file.write_text(json.dumps(export_data, indent=2), encoding="utf-8")
        except Exception as e:
            log.warning("Failed to save vector memory cache: %s", e)

    def _load_cache(self) -> None:
        """Load indexed docs from disk cache if present."""
        if not self.cache_file.exists():
            return
        try:
            raw = json.loads(self.cache_file.read_text(encoding="utf-8"))
            docs_to_add = []
            for doc_id, item in raw.items():
                docs_to_add.append({
                    "id": doc_id,
                    "text": item.get("text", ""),
                    "metadata": item.get("metadata", {})
                })
            if docs_to_add:
                self.add_documents(docs_to_add)
        except Exception as e:
            log.warning("Failed to load vector memory cache: %s", e)


_GLOBAL_VECTOR_INDEX: Optional[VectorMemoryIndex] = None


def get_default_vector_index() -> VectorMemoryIndex:
    """Singleton getter for the global vector memory index."""
    global _GLOBAL_VECTOR_INDEX
    if _GLOBAL_VECTOR_INDEX is None:
        _GLOBAL_VECTOR_INDEX = VectorMemoryIndex()
        # Auto-index vault if empty
        if not _GLOBAL_VECTOR_INDEX.documents:
            index_vault_notes()
    return _GLOBAL_VECTOR_INDEX


def index_vault_notes(vault_path: Optional[Path] = None) -> int:
    """Scan all markdown files in Obsidian vault and index them into vector memory."""
    v_path = vault_path or VAULT_DIR
    if not v_path.exists():
        v_path.mkdir(parents=True, exist_ok=True)
        return 0

    idx = get_default_vector_index()
    docs = []
    for md_file in v_path.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            docs.append({
                "id": str(md_file.relative_to(v_path)),
                "text": f"{md_file.stem}\n{content}",
                "metadata": {
                    "filename": md_file.name,
                    "title": md_file.stem,
                    "path": str(md_file),
                    "size": len(content)
                }
            })
        except Exception:
            continue

    if docs:
        idx.add_documents(docs)
        idx.save_cache()
    return len(docs)


def crystallize_dev_log(
    summary: str,
    details: str = "",
    tags: Optional[List[str]] = None,
    vault_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Crystallize a structured development activity log directly into Obsidian
    and immediately index it in semantic vector memory.
    """
    v_path = vault_path or VAULT_DIR
    dev_log_dir = v_path / "DevLogs"
    dev_log_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    timestamp_id = now.strftime("%Y%m%d_%H%M%S")

    tag_list = tags or ["dev", "ai_agent", "prime_log"]
    formatted_tags = " ".join(f"#{t.strip().lstrip('#')}" for t in tag_list)

    safe_title = re.sub(r"[^a-zA-Z0-9_\- ]", "", summary)[:50].strip().replace(" ", "_")
    if not safe_title:
        safe_title = "session_update"

    filename = f"{date_str}_{safe_title}_{timestamp_id[-4:]}.md"
    target_path = dev_log_dir / filename

    content = f"""---
title: "Dev Log: {summary}"
date: {date_str} {time_str}
tags: [{", ".join(tag_list)}]
type: dev_log
status: crystallized
---

# 🚀 Dev Log: {summary}
> **Recorded:** {date_str} at {time_str}  
> **Tags:** {formatted_tags}

## 📋 Summary
{summary}

## 🛠️ Details & Changes
{details or 'No additional details logged.'}

---
*Auto-crystallized by Prime Vector Memory Engine.*
"""

    try:
        target_path.write_text(content, encoding="utf-8")
        
        # Immediately index in vector memory
        idx = get_default_vector_index()
        rel_id = str(target_path.relative_to(v_path))
        idx.add_document(
            doc_id=rel_id,
            text=f"{summary}\n{details}\n{formatted_tags}",
            metadata={
                "filename": filename,
                "title": f"Dev Log: {summary}",
                "path": str(target_path),
                "tags": tag_list,
                "type": "dev_log"
            }
        )
        idx.save_cache()

        return {
            "ok": True,
            "message": f"Dev log crystallized and indexed in Obsidian: '{filename}'.",
            "filename": filename,
            "path": str(target_path),
            "tags": tag_list
        }
    except Exception as e:
        log.error("Failed to crystallize dev log: %s", e)
        return {"ok": False, "error": f"Failed to crystallize dev log: {e}"}


def search_vault_semantic(query: str, top_k: int = 5) -> Dict[str, Any]:
    """Semantic vector search across Obsidian vault notes."""
    idx = get_default_vector_index()
    results = idx.search(query, top_k=top_k)
    return {
        "ok": True,
        "query": query,
        "total_matches": len(results),
        "results": [
            {
                "title": r.get("metadata", {}).get("title") or r["id"],
                "path": r.get("metadata", {}).get("path") or r["id"],
                "score": r["score"],
                "snippet": r["snippet"]
            }
            for r in results
        ]
    }
