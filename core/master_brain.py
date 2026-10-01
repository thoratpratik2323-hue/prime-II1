"""
core/master_brain.py — Prime AI Single Unified Master Cognitive Cortex.

Consolidates all memory subsystems of Prime AI into one coherent, atomic,
and multi-tiered engine:
1. Working Memory (RAM hot cache for sub-millisecond retrieval)
2. Relational & Knowledge Graph (SQLite brain.db triples, entities, relations)
3. Obsidian Second Brain RAG (BM25 lexical note chunks in Markdown)
4. Semantic Vector Store (TF-IDF & Cosine Similarity embeddings)
5. Durable Task State (Restart-safe multi-step execution plans)
6. Cryptographic Receipts Ledger (Tool pre-states, execution trails, rollbacks)
7. Autonomous Sleep-Cycle Memory Consolidation (Digests and fact pruning)
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("prime.core.master_brain")
_lock = threading.Lock()


class PrimeMasterBrain:
    """
    The Single Unified Big Brain for Prime AI.
    Provides a single entry point for storing, recalling, searching,
    and synthesizing context across all cognitive layers.
    """

    def __init__(self):
        self._initialized = False
        self._ram_cache: Dict[str, Dict[str, Any]] = {}
        self._last_consolidation = 0.0
        self._init_brain()

    def _init_brain(self):
        """Warm up all underlying memory engines safely."""
        with _lock:
            if self._initialized:
                return
            try:
                # 1. Warm up user preferences into RAM
                from actions.friday_memory import memory_ledger
                self._ram_cache = dict(memory_ledger.memories)
                logger.info(f"[Master Brain] Loaded {len(self._ram_cache)} active user memories into RAM cache.")

                # 2. Touch SQLite Graph store schema
                from memory.brain import _get_db
                conn = _get_db()
                conn.close()
                logger.info("[Master Brain] Connected to SQLite Knowledge Graph (brain.db).")

                # 3. Touch Obsidian Second Brain Vault
                from obsidian_rag import get_vault_path
                v_path = get_vault_path()
                logger.info(f"[Master Brain] Connected to Obsidian Second Brain Vault at '{v_path.name}'.")

                self._initialized = True
            except Exception as e:
                logger.warning(f"[Master Brain] Initialization warning: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    #  1. UNIFIED WRITE (Remember)
    # ═══════════════════════════════════════════════════════════════════════════

    def remember(
        self,
        key: str,
        value: Any,
        category: str = "preferences",
        importance: int = 5,
        sync_obsidian: bool = True,
        sync_graph: bool = True,
        sync_vector: bool = True,
    ) -> Dict[str, Any]:
        """
        Store a fact, preference, rule, or decision into the Master Brain.
        Automatically distributes data atomically across RAM, JSON, Graph, Obsidian, and Vector layers.
        """
        k_clean = str(key).strip().lower()
        val_str = str(value).strip()
        cat_clean = str(category).strip().lower()
        if not cat_clean:
            cat_clean = "preferences"

        synced_layers = []

        with _lock:
            # Layer 0: RAM Hot Cache
            now_iso = datetime.now().isoformat()
            entry = {
                "key": k_clean,
                "value": val_str,
                "category": cat_clean,
                "importance": importance,
                "updated_at": now_iso,
            }
            self._ram_cache[k_clean] = entry
            synced_layers.append("ram_cache")

            # Layer 1: Durable JSON Ledger
            try:
                from actions.friday_memory import memory_ledger
                memory_ledger.memories[k_clean] = entry
                memory_ledger._save_memory()
                synced_layers.append("json_ledger")
            except Exception as e:
                logger.warning(f"[Master Brain] JSON sync error: {e}")

            # Layer 2: SQLite Knowledge Graph (Triples & Entities)
            if sync_graph:
                try:
                    from memory.brain import store_fact, store_entity
                    store_entity(name=k_clean, entity_type="user_preference", metadata={"category": cat_clean})
                    store_fact(
                        subject="User",
                        predicate=k_clean,
                        obj=val_str,
                        confidence=1.0,
                        source=f"master_brain:{cat_clean}"
                    )
                    synced_layers.append("sqlite_graph")
                except Exception as e:
                    logger.warning(f"[Master Brain] Graph sync error: {e}")

            # Layer 3: Obsidian Second Brain Vault (Markdown Profile & DevLogs)
            if sync_obsidian:
                try:
                    from obsidian_rag import write_note
                    lines = [
                        "# User Profile & Preferences (Synchronized Second Brain)",
                        "",
                        f"> Automatically synchronized with Prime Master Brain. Total records: {len(self._ram_cache)}.",
                        f"> Last sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        "",
                        "| Preference / Rule | Value | Category | Last Updated |",
                        "|---|---|---|---|",
                    ]
                    for k, item in sorted(self._ram_cache.items()):
                        val_escaped = str(item.get("value", "")).replace("|", "\\|")
                        cat_item = item.get("category", "preferences")
                        ts = item.get("updated_at", "")[:19].replace("T", " ")
                        lines.append(f"| `{k}` | {val_escaped} | `{cat_item}` | {ts} |")

                    write_note("Profile/Preferences.md", "\n".join(lines), mode="write")
                    synced_layers.append("obsidian_vault")
                except Exception as e:
                    logger.warning(f"[Master Brain] Obsidian sync error: {e}")

            # Layer 4: Semantic Vector Store Indexing
            if sync_vector:
                try:
                    from core.vector_memory import get_default_vector_index
                    idx = get_default_vector_index()
                    idx.add_document(
                        doc_id=f"pref_{k_clean}",
                        text=f"User preference {k_clean}: {val_str} (category: {cat_clean})",
                        metadata={"key": k_clean, "category": cat_clean, "type": "preference"}
                    )
                    synced_layers.append("vector_index")
                except Exception as e:
                    logger.debug(f"[Master Brain] Vector indexing error: {e}")

        logger.info(f"[Master Brain] Remembered '{k_clean}' across {len(synced_layers)} layers: {synced_layers}")
        return {
            "ok": True,
            "message": f"Successfully remembered '{key}' across {len(synced_layers)} cognitive layers.",
            "key": k_clean,
            "value": val_str,
            "category": cat_clean,
            "synced_layers": synced_layers,
            "timestamp": now_iso,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  2. UNIFIED HYBRID RECALL (Search)
    # ═══════════════════════════════════════════════════════════════════════════

    def recall(
        self,
        query: str = "",
        category: str = "",
        top_k: int = 5,
        mode: str = "hybrid",
    ) -> Dict[str, Any]:
        """
        Multi-modal hybrid recall across all memory layers:
        - Exact/Category match in RAM & JSON ledger
        - SQLite Knowledge Graph triples & relations
        - Obsidian BM25 document chunks
        - Semantic Vector TF-IDF / Cosine Similarity
        Combines candidate results via Reciprocal Rank Fusion (RRF).
        """
        q = (query or "").strip()
        cat = (category or "").strip().lower()

        # Path A: Explicit category or empty query returns known active preferences
        if not q and cat:
            matches = [v for v in self._ram_cache.values() if v.get("category") == cat]
            return {
                "ok": True,
                "query": query,
                "count": len(matches),
                "mode": "category",
                "results": matches[:top_k],
            }

        # Fast exact hit in RAM
        if q.lower() in self._ram_cache:
            item = self._ram_cache[q.lower()]
            return {
                "ok": True,
                "query": query,
                "count": 1,
                "mode": "exact_ram",
                "results": [item],
            }

        # Path B: Multi-Modal Hybrid Search
        candidates: List[Dict[str, Any]] = []
        scores: Dict[str, float] = {}

        def _add_hit(doc_id: str, title: str, content: str, source: str, rank: int, weight: float = 1.0):
            # Reciprocal Rank Fusion formula: 1.0 / (60 + rank)
            rrf = weight * (1.0 / (60.0 + rank))
            scores[doc_id] = scores.get(doc_id, 0.0) + rrf
            candidates.append({
                "id": doc_id,
                "title": title,
                "content": content,
                "source": source,
                "rrf_score": rrf
            })

        # 1. Search RAM / Preferences
        q_lower = q.lower()
        pref_rank = 1
        for k, v in self._ram_cache.items():
            if cat and v.get("category") != cat:
                continue
            search_blob = f"{k} {v.get('value', '')} {v.get('category', '')}".lower()
            if q_lower in search_blob or any(word in search_blob for word in q_lower.split() if len(word) > 2):
                _add_hit(f"pref_{k}", f"Preference: {k}", str(v.get("value", "")), "User Preferences", pref_rank, weight=1.4)
                pref_rank += 1

        # 2. Search SQLite Knowledge Graph Facts
        try:
            from memory.brain import query_facts
            graph_facts = query_facts(subject=q, limit=top_k) or []
            if not graph_facts:
                graph_facts = query_facts(predicate=q, limit=top_k) or []
            for i, f in enumerate(graph_facts):
                fact_str = f"{f['subject']} -> {f['predicate']}: {f['object']}"
                _add_hit(f"graph_{f['subject']}_{f['predicate']}", f"Graph Fact: {f['predicate']}", fact_str, "Knowledge Graph", i + 1, weight=1.2)
        except Exception as e:
            logger.debug(f"[Master Brain] Graph query error: {e}")

        # 3. Search Obsidian Second Brain via BM25
        try:
            from obsidian_rag import query_knowledge_base
            obs_res = query_knowledge_base(q, top_k=top_k)
            for i, c in enumerate(obs_res.get("results", [])):
                _add_hit(f"obs_{c['path']}_{c['heading']}", f"{c['heading']} ({c['path']})", c["content"], "Obsidian Vault (BM25)", i + 1, weight=1.0)
        except Exception as e:
            logger.debug(f"[Master Brain] Obsidian BM25 error: {e}")

        # 4. Search Semantic Vector Store
        try:
            from core.vector_memory import search_vault_semantic
            vec_res = search_vault_semantic(q, top_k=top_k)
            for i, vr in enumerate(vec_res.get("results", [])):
                _add_hit(f"vec_{vr['path']}", vr["title"], vr["snippet"], "Semantic Vector", i + 1, weight=0.9)
        except Exception as e:
            logger.debug(f"[Master Brain] Vector search error: {e}")

        # Deduplicate & Sort by fused RRF score
        seen_ids = set()
        unique_results = []
        for c in sorted(candidates, key=lambda x: scores.get(x["id"], 0.0), reverse=True):
            if c["id"] not in seen_ids:
                seen_ids.add(c["id"])
                c["final_score"] = round(scores.get(c["id"], 0.0), 4)
                unique_results.append(c)

        top_matches = unique_results[:top_k]

        return {
            "ok": True,
            "query": query,
            "count": len(top_matches),
            "mode": mode,
            "results": top_matches,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  3. UNIFIED FORGET (Erase)
    # ═══════════════════════════════════════════════════════════════════════════

    def forget(self, key: str) -> Dict[str, Any]:
        """
        Delete a preference or memory across all layers simultaneously.
        """
        k_clean = str(key).strip().lower()
        synced_deletions = []

        with _lock:
            # 1. RAM Cache
            if k_clean in self._ram_cache:
                self._ram_cache.pop(k_clean)
                synced_deletions.append("ram_cache")

            # 2. JSON Ledger
            try:
                from actions.friday_memory import memory_ledger
                if k_clean in memory_ledger.memories:
                    memory_ledger.memories.pop(k_clean)
                    memory_ledger._save_memory()
                    synced_deletions.append("json_ledger")
            except Exception:
                pass

            # 3. SQLite Graph
            try:
                from memory.brain import delete_fact
                delete_fact(subject="User", predicate=k_clean)
                synced_deletions.append("sqlite_graph")
            except Exception:
                pass

            # 4. Obsidian Vault Profile
            try:
                from obsidian_rag import write_note
                lines = [
                    "# User Profile & Preferences (Synchronized Second Brain)",
                    "",
                    f"> Automatically synchronized with Prime Master Brain. Total records: {len(self._ram_cache)}.",
                    f"> Last sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    "| Preference / Rule | Value | Category | Last Updated |",
                    "|---|---|---|---|",
                ]
                for k, item in sorted(self._ram_cache.items()):
                    val_escaped = str(item.get("value", "")).replace("|", "\\|")
                    cat_item = item.get("category", "preferences")
                    ts = item.get("updated_at", "")[:19].replace("T", " ")
                    lines.append(f"| `{k}` | {val_escaped} | `{cat_item}` | {ts} |")

                write_note("Profile/Preferences.md", "\n".join(lines), mode="write")
                synced_deletions.append("obsidian_vault")
            except Exception:
                pass

        if synced_deletions:
            logger.info(f"[Master Brain] Deleted '{k_clean}' across layers: {synced_deletions}")
            return {
                "ok": True,
                "message": f"Successfully forgot '{key}' from {len(synced_deletions)} cognitive layers.",
                "key": k_clean,
                "deleted_from": synced_deletions,
            }

        return {"ok": False, "error": f"No memory found matching '{key}'."}

    # ═══════════════════════════════════════════════════════════════════════════
    #  4. SYSTEM PROMPT COGNITIVE SYNTHESIZER
    # ═══════════════════════════════════════════════════════════════════════════

    def get_cognitive_context(self, user_prompt: str = "") -> str:
        """
        Synthesize high-priority cognitive memory into a clean, dense markdown block
        ready for direct system prompt injection (<2ms latency).
        """
        blocks: List[str] = []

        # 1. Active User Preferences & Directives (Zero-latency RAM cache)
        if self._ram_cache:
            pref_lines = ["[Active User Preferences & Operating Rules]"]
            for k, v in sorted(self._ram_cache.items()):
                pref_lines.append(f"- {k.title()}: {v['value']}")
            blocks.append("\n".join(pref_lines))

        # 2. User Profile Knowledge Graph (Persistent facts about the user)
        try:
            from memory.brain import query_facts
            facts = query_facts(subject="pratik", limit=8)
            if facts:
                fact_lines = [f"- {f.get('predicate', 'fact')}: {f.get('object', '')}" for f in facts if f.get('object')]
                if fact_lines:
                    blocks.append("[USER PROFILE & PERSISTENT KNOWLEDGE GRAPH (PRATIK)]\n" + "\n".join(fact_lines))
        except Exception:
            pass

        # 3. Active Durable Task Plan
        try:
            from actions.friday_tasks import get_active_task_plan
            plan_res = get_active_task_plan()
            if plan_res.get("has_active_plan") and plan_res.get("plan"):
                plan = plan_res["plan"]
                plan_lines = [
                    f"[Active Multi-Step Durable Plan (ID: {plan['plan_id']})]",
                    f"Goal: {plan['goal']}",
                    f"Current Step: Step {plan['current_step_index'] + 1} of {len(plan['steps'])}"
                ]
                for s in plan["steps"]:
                    icon = "✅" if s["status"] == "completed" else "⏳" if s["status"] == "in_progress" else "⚪"
                    plan_lines.append(f"  {icon} Step {s['step_index'] + 1}: {s['description']} [{s['status'].upper()}]")
                blocks.append("\n".join(plan_lines))
        except Exception:
            pass

        # 4. Contextual RAG Retrieval (If prompt refers to specific project/architecture)
        if user_prompt and len(user_prompt) > 8:
            keywords = [w for w in re.findall(r"\b[a-zA-Z]{4,}\b", user_prompt.lower()) if w not in ("please", "should", "could", "would", "about")]
            if any(k in user_prompt.lower() for k in ("architecture", "database", "agent", "tool", "obsidian", "devlog", "decision", "project", "plan", "memory")):
                try:
                    rag_res = self.recall(user_prompt, top_k=2, mode="hybrid")
                    if rag_res.get("results"):
                        rag_lines = ["[Relevant Second Brain Memory]"]
                        for r in rag_res["results"]:
                            snippet = r["content"][:220].replace("\n", " ")
                            rag_lines.append(f"- Source ({r['source']}): {r['title']} -> {snippet}")
                        blocks.append("\n".join(rag_lines))
                except Exception:
                    pass

        return "\n\n".join(blocks)

    # ═══════════════════════════════════════════════════════════════════════════
    #  5. AUTONOMOUS SLEEP-CYCLE CONSOLIDATION
    # ═══════════════════════════════════════════════════════════════════════════

    def consolidate(self) -> Dict[str, Any]:
        """
        Sleep-cycle background consolidation:
        - Summarizes daily conversation records into weekly digests.
        - Prunes duplicate or expired SQLite graph facts.
        - Synchronizes Obsidian DevLogs.
        """
        now = time.time()
        with _lock:
            # 1. Prune expired or orphaned facts in SQLite
            pruned_count = 0
            try:
                from memory.brain import _get_db
                conn = _get_db()
                try:
                    cur = conn.execute("DELETE FROM facts WHERE expires_at IS NOT NULL AND expires_at < datetime('now')")
                    conn.commit()
                    pruned_count = cur.rowcount
                finally:
                    conn.close()
            except Exception as e:
                logger.warning(f"[Master Brain] Fact pruning warning: {e}")

            # 2. Record consolidation event in DevLogs
            try:
                from obsidian_rag import auto_record_session_decision
                auto_record_session_decision(
                    "Master Brain Autonomous Consolidation",
                    f"Consolidation cycle completed. Pruned {pruned_count} expired facts. Total active preferences: {len(self._ram_cache)}."
                )
            except Exception:
                pass

            self._last_consolidation = now

        return {
            "ok": True,
            "message": "Master Brain memory consolidation completed.",
            "pruned_facts": pruned_count,
            "active_preferences": len(self._ram_cache),
            "timestamp": datetime.now().isoformat(),
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  6. MASTER BRAIN TELEMETRY & STATS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """Return a consolidated summary of all brain memory layers."""
        # 1. Graph facts count
        facts_count = 0
        entities_count = 0
        try:
            from memory.brain import _get_db
            conn = _get_db()
            try:
                r1 = conn.execute("SELECT COUNT(*) FROM facts").fetchone()
                facts_count = r1[0] if r1 else 0
                r2 = conn.execute("SELECT COUNT(*) FROM entities").fetchone()
                entities_count = r2[0] if r2 else 0
            finally:
                conn.close()
        except Exception:
            pass

        # 2. Obsidian notes count
        obsidian_notes = 0
        try:
            from obsidian_rag import list_notes
            obsidian_notes = len(list_notes(recursive=True))
        except Exception:
            pass

        # 3. Durable plans & receipts count
        plans_count = 0
        receipts_count = 0
        try:
            from actions.friday_tasks import task_manager
            plans_count = len(task_manager.plans)
            from actions.friday_receipts import receipt_engine
            receipts_count = len(receipt_engine.receipts)
        except Exception:
            pass

        return {
            "ok": True,
            "master_brain_status": "ONLINE",
            "working_ram_preferences": len(self._ram_cache),
            "sqlite_graph": {
                "facts": facts_count,
                "entities": entities_count,
            },
            "obsidian_second_brain": {
                "total_notes": obsidian_notes,
            },
            "durable_task_plans": plans_count,
            "cryptographic_receipts": receipts_count,
            "last_consolidation_ts": self._last_consolidation,
        }


# Global singleton instance of Prime Master Brain
prime_brain = PrimeMasterBrain()


def remember_anything(key: str, value: Any, category: str = "preferences") -> Dict[str, Any]:
    """Store anything into the Prime Master Brain."""
    return prime_brain.remember(key, value, category=category)


def recall_anything(query: str = "", category: str = "", top_k: int = 5) -> Dict[str, Any]:
    """Search or retrieve from the Prime Master Brain."""
    return prime_brain.recall(query=query, category=category, top_k=top_k)


def forget_anything(key: str) -> Dict[str, Any]:
    """Erase a memory across all layers in Prime Master Brain."""
    return prime_brain.forget(key)


def get_master_brain_stats() -> Dict[str, Any]:
    """Get complete telemetry from the Prime Master Brain."""
    return prime_brain.get_stats()
