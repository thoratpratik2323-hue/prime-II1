"""
tests/test_system_upgrades.py
Comprehensive test suite validating the 4 major architectural upgrades:
1. Sentence-Streaming TTS Pipeline & token iterator handling.
2. Automatic Safety Interceptor & Cryptographic Pre-State Receipts.
3. Tri-Directional Memory Synchronization (Friday JSON <-> Obsidian Vault <-> SQLite Brain Graph).
4. Live Visual HUD Telemetry and SSE streaming endpoints.
"""

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from actions.friday_memory import (
    remember_user_preference,
    recall_user_preferences,
    forget_user_preference,
    memory_ledger,
)
from actions.friday_policy import check_action_policy
from actions.friday_receipts import get_execution_receipts, receipt_ledger
from actions.friday_tasks import create_durable_task_plan, get_active_task_plan, task_manager
from actions.her_companion import get_her_visualizer_state, her_engine
from memory.brain import query_facts, delete_fact
from mobile_room_server import app
from voice_engine import voice


class TestSystemUpgrades(unittest.TestCase):
    """Test suite for the 4 architectural upgrades."""

    # ── 1. Voice Streaming & Sentence Pipelining ──────────────────────────
    def test_voice_speak_polymorphic_streaming(self):
        """Verify voice.speak accepts generator/iterable and dispatches clauses to queue."""
        voice.tts_enabled = True
        sample_tokens = ["Hello, ", "Sir. ", "Systems ", "are fully operational."]

        def token_gen():
            for tok in sample_tokens:
                yield tok

        # Test speak with generator
        result = voice.speak(token_gen())
        self.assertIn("Systems are fully operational.", result)
        # Drain the tts_queue or check dispatched history if consumed by worker thread
        items = []
        while not voice.tts_queue.empty():
            items.append(voice.tts_queue.get_nowait())
        all_items = items + list(getattr(voice, "_dispatched_history", []))
        self.assertTrue(len(all_items) >= 1)
        self.assertTrue(any("hello" in s.lower() or "systems" in s.lower() for s in all_items))

    # ── 2. Automatic Safety Policy Interceptor & Receipts ─────────────────
    def test_safety_interceptor_gating_destructive_command(self):
        """Verify safety policy gates destructive actions without an approval token."""
        from ai_agent import AIAgent

        agent = AIAgent.__new__(AIAgent)
        # Call _intercept_and_execute_tool with destructive rm -rf command
        res = agent._intercept_and_execute_tool(
            "runTerminalCommand",
            {"command": "rm -rf /critical/system/path"}
        )
        self.assertFalse(res.get("ok"))
        self.assertTrue(res.get("gated"))
        self.assertIn("approval_token", res)
        self.assertIn("GATED by Safety Policy", res.get("error", ""))

    def test_safety_interceptor_records_receipt(self):
        """Verify non-destructive safe tool creates execution receipt."""
        from ai_agent import AIAgent

        agent = AIAgent.__new__(AIAgent)
        # Execute safe echo command through interceptor
        res = agent._intercept_and_execute_tool(
            "runTerminalCommand",
            {"command": "echo Prime Safety Test"}
        )
        self.assertTrue(res.get("ok"))
        # Check recent receipts
        rec_data = get_execution_receipts(limit=5)
        self.assertTrue(rec_data.get("ok"))
        receipts = rec_data.get("receipts", [])
        self.assertTrue(any(r.get("tool_name") == "runTerminalCommand" for r in receipts))

    # ── 3. Tri-Directional Memory Sync ────────────────────────────────────
    def test_tri_directional_memory_sync_and_forget(self):
        """Verify remember & forget syncs Friday JSON, Obsidian Vault, and SQLite Brain."""
        test_key = "test_favorite_editor"
        test_val = "neovim_ide"

        # 1. Store
        save_res = remember_user_preference(test_key, test_val, category="preferences")
        self.assertTrue(save_res.get("ok"))
        # Master Brain returns synced_layers list; verify actual sync occurred via downstream checks
        synced = save_res.get("synced_layers", [])
        if synced:
            self.assertIn("obsidian_vault", synced)
            self.assertIn("sqlite_graph", synced)
        else:
            # Legacy format fallback
            self.assertTrue(save_res.get("synced_obsidian"))
            self.assertTrue(save_res.get("synced_brain"))

        # Check JSON memory ledger
        recalled = recall_user_preferences(test_key)
        self.assertEqual(recalled.get("count"), 1)
        self.assertEqual(recalled["memories"][0]["value"], test_val)

        # Check Obsidian Profile/Preferences.md
        obsidian_file = Path("Obsidian_Vault/Profile/Preferences.md")
        self.assertTrue(obsidian_file.exists())
        obsidian_content = obsidian_file.read_text(encoding="utf-8")
        self.assertIn(test_key, obsidian_content)
        self.assertIn(test_val, obsidian_content)

        # Check SQLite Brain facts
        facts = query_facts(subject="User", predicate=test_key)
        self.assertTrue(len(facts) >= 1)
        self.assertEqual(facts[0]["object"], test_val)

        # 2. Forget
        forget_res = forget_user_preference(test_key)
        self.assertTrue(forget_res.get("ok"))
        # Master Brain returns deleted_from list
        deleted = forget_res.get("deleted_from", [])
        if deleted:
            self.assertIn("obsidian_vault", deleted)
            self.assertIn("sqlite_graph", deleted)
        else:
            self.assertTrue(forget_res.get("synced_obsidian"))
            self.assertTrue(forget_res.get("synced_brain"))

        # Verify removal across all 3
        self.assertEqual(recall_user_preferences(test_key).get("count"), 0)
        obsidian_after = obsidian_file.read_text(encoding="utf-8")
        self.assertNotIn(f"`{test_key}`", obsidian_after)
        facts_after = query_facts(subject="User", predicate=test_key)
        self.assertEqual(len(facts_after), 0)

    # ── 4. Mobile HUD State & SSE Stream ──────────────────────────────────
    def test_mobile_hud_state_endpoint(self):
        """Verify /api/hud/state returns complete telemetry structure."""
        client = app.test_client()
        resp = client.get("/api/hud/state")
        self.assertEqual(resp.status_code, 200)

        data = resp.get_json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("status"), "online")
        self.assertIn("hardware", data)
        self.assertIn("cpu_percent", data["hardware"])
        self.assertIn("ram_percent", data["hardware"])
        self.assertIn("ai", data)
        self.assertIn("active_provider", data["ai"])
        self.assertIn("visualizer", data)
        self.assertIn("render_params", data["visualizer"])
        self.assertIn("ring_color", data["visualizer"]["render_params"])

    def test_mobile_hud_stream_tick(self):
        """Verify /api/hud/stream returns SSE events."""
        client = app.test_client()
        resp = client.get("/api/hud/stream")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, "text/event-stream")


if __name__ == "__main__":
    unittest.main()
