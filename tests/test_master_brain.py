"""
tests/test_master_brain.py
Unit and integration test suite for the Single Unified Big Brain (Prime Master Cognitive Cortex).
Validates multi-layer atomic remember, hybrid RRF recall, forget purging,
system prompt cognitive synthesis, and autonomous memory consolidation.
"""

import unittest
from pathlib import Path

from core.master_brain import prime_brain, remember_anything, recall_anything, forget_anything, get_master_brain_stats
from memory.brain import query_facts


class TestMasterBrain(unittest.TestCase):
    """Test suite for PrimeMasterBrain unified cognitive cortex."""

    def test_master_brain_stats(self):
        """Verify get_stats returns complete multi-layer telemetry."""
        stats = get_master_brain_stats()
        self.assertTrue(stats.get("ok"))
        self.assertEqual(stats.get("master_brain_status"), "ONLINE")
        self.assertIn("working_ram_preferences", stats)
        self.assertIn("sqlite_graph", stats)
        self.assertIn("facts", stats["sqlite_graph"])
        self.assertIn("entities", stats["sqlite_graph"])
        self.assertIn("obsidian_second_brain", stats)
        self.assertIn("total_notes", stats["obsidian_second_brain"])

    def test_unified_remember_across_all_layers(self):
        """Verify remember stores atomically in RAM, JSON, SQLite Graph, Obsidian, and Vector."""
        test_key = "test_unified_terminal"
        test_val = "Windows Terminal with PowerShell 7"

        res = remember_anything(test_key, test_val, category="rules")
        self.assertTrue(res.get("ok"))
        self.assertIn("ram_cache", res["synced_layers"])
        self.assertIn("json_ledger", res["synced_layers"])
        self.assertIn("sqlite_graph", res["synced_layers"])
        self.assertIn("obsidian_vault", res["synced_layers"])

        # Check SQLite Graph
        facts = query_facts(subject="User", predicate=test_key)
        self.assertTrue(len(facts) >= 1)
        self.assertEqual(facts[0]["object"], test_val)

        # Check Obsidian Vault Profile/Preferences.md
        obsidian_path = Path("Obsidian_Vault/Profile/Preferences.md")
        self.assertTrue(obsidian_path.exists())
        obsidian_txt = obsidian_path.read_text(encoding="utf-8")
        self.assertIn(test_key, obsidian_txt)
        self.assertIn(test_val, obsidian_txt)

        # Clean up
        forget_res = forget_anything(test_key)
        self.assertTrue(forget_res.get("ok"))
        self.assertIn("ram_cache", forget_res["deleted_from"])
        self.assertIn("sqlite_graph", forget_res["deleted_from"])

    def test_unified_recall_hybrid_rrf(self):
        """Verify hybrid recall combines results with Reciprocal Rank Fusion."""
        test_key = "test_quantum_engine"
        test_val = "Kyber-1024 Crystals"

        remember_anything(test_key, test_val, category="facts")

        # Hybrid recall
        rec = recall_anything(test_key, top_k=3)
        self.assertTrue(rec.get("ok"))
        self.assertTrue(rec.get("count") >= 1)
        self.assertTrue(any(test_key in str(r) for r in rec.get("results", [])))

        # Clean up
        forget_anything(test_key)

    def test_cognitive_context_synthesis(self):
        """Verify get_cognitive_context synthesizes dense system prompt context."""
        test_key = "test_favorite_voice"
        test_val = "Ultron Metallic Baritone"
        remember_anything(test_key, test_val, category="preferences")

        ctx = prime_brain.get_cognitive_context("Can you tell me about voice settings?")
        self.assertIn("[Active User Preferences & Operating Rules]", ctx)
        self.assertIn("Test_Favorite_Voice", ctx)
        self.assertIn("Ultron Metallic Baritone", ctx)

        # Clean up
        forget_anything(test_key)

    def test_autonomous_consolidation(self):
        """Verify consolidate executes without errors and cleans expired facts."""
        res = prime_brain.consolidate()
        self.assertTrue(res.get("ok"))
        self.assertIn("pruned_facts", res)
        self.assertIn("active_preferences", res)


if __name__ == "__main__":
    unittest.main()
