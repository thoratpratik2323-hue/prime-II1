"""
tests/test_autonomous_upgrades.py
Comprehensive unit test suite for the 5 Autonomous Pillars:
1. Ultra-Low Voice Latency & Streaming Sentence Chunking
2. WhatsApp Autonomous Background Agent & Focus Mode
3. Active Desktop Vision & Grounded UI Clicking
4. Deep Obsidian RAG & Persistent Long-Term Memory
5. Self-Healing Autonomous Terminal & Coding Repair Loop
"""

import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import obsidian_rag
import tool_definitions
import whatsapp_manager
from claw_developer import autonomous_code_repair_loop, patch_file, run_terminal_command


class TestObsidianRAGDeep(unittest.TestCase):
    def setUp(self):
        self.vault = obsidian_rag.get_vault_path()

    def test_list_notes_recursive(self):
        notes = obsidian_rag.list_notes(recursive=True)
        self.assertIsInstance(notes, list)
        self.assertGreater(len(notes), 0)
        # Should include markdown files
        self.assertTrue(any(n.endswith(".md") for n in notes))

    def test_sync_vault(self):
        stats = obsidian_rag.sync_vault()
        self.assertTrue(stats.get("ok"))
        self.assertGreater(stats.get("total_notes", 0), 0)
        self.assertGreater(stats.get("total_indexed_chunks", 0), 0)

    def test_query_knowledge_base(self):
        res = obsidian_rag.query_knowledge_base("tools and actions", top_k=3)
        self.assertTrue(res.get("ok"))
        self.assertIn("context", res)
        self.assertIsInstance(res.get("results"), list)

    def test_write_and_read_note_and_append(self):
        test_note = "DevLogs/UnitTest_Note.md"
        content1 = "# Heading 1\nInitial content for testing."
        obsidian_rag.write_note(test_note, content1, mode="write")

        read1 = obsidian_rag.read_note(test_note)
        self.assertIn("Initial content for testing", read1)

        # Append
        content2 = "Additional appended line."
        obsidian_rag.write_note(test_note, content2, mode="append")
        read2 = obsidian_rag.read_note(test_note)
        self.assertIn("Initial content for testing", read2)
        self.assertIn("Additional appended line", read2)

        # Cleanup
        target = self.vault / test_note
        if target.exists():
            target.unlink()

    def test_auto_record_decision(self):
        msg = obsidian_rag.auto_record_session_decision("Test Architecture", "Adopted 5 Pillars", "Verified by unit test")
        self.assertIn("Decision recorded", msg)
        decisions_file = self.vault / "DevLogs" / "Decisions.md"
        self.assertTrue(decisions_file.exists())
        content = decisions_file.read_text(encoding="utf-8")
        self.assertIn("Test Architecture", content)
        self.assertIn("Adopted 5 Pillars", content)


class TestWhatsAppAutonomousAgent(unittest.TestCase):
    def test_focus_mode_toggle(self):
        res_on = whatsapp_manager.set_whatsapp_focus_mode(True, "Working on Prime AI")
        self.assertTrue(res_on.get("ok"))
        self.assertTrue(res_on.get("enabled"))
        self.assertEqual(res_on.get("reply_template"), "Working on Prime AI")

        status = whatsapp_manager.get_whatsapp_focus_mode()
        self.assertTrue(status.get("enabled"))

        res_off = whatsapp_manager.set_whatsapp_focus_mode(False)
        self.assertTrue(res_off.get("ok"))
        self.assertFalse(res_off.get("enabled"))

    def test_check_unread_messages(self):
        res = whatsapp_manager.check_unread_whatsapp_messages()
        self.assertTrue(res.get("ok"))
        self.assertIn("has_unread", res)
        self.assertIn("unread_count", res)

    def test_draft_and_confirm_workflow(self):
        draft_res = whatsapp_manager.draft_whatsapp_with_confirmation("9860998497", "Testing automated draft")
        self.assertTrue(draft_res.get("ok"))
        self.assertTrue(draft_res.get("awaiting_confirmation"))
        draft_id = draft_res.get("draft_id")
        self.assertIsNotNone(draft_id)

        # Mock send_whatsapp to avoid sending real message in test
        with patch.object(whatsapp_manager, "send_whatsapp", return_value={"ok": True, "message": "Sent"}) as mock_send:
            confirm_res = whatsapp_manager.confirm_and_send_draft(draft_id)
            self.assertTrue(confirm_res.get("ok"))
            mock_send.assert_called_once_with("9860998497", "Testing automated draft")

    def test_watcher_start_stop(self):
        res_start = whatsapp_manager.start_whatsapp_unread_watcher()
        self.assertTrue(res_start.get("ok"))
        res_stop = whatsapp_manager.stop_whatsapp_unread_watcher()
        self.assertTrue(res_stop.get("ok"))


class TestActiveDesktopVision(unittest.TestCase):
    def test_locate_and_click_ui_registered(self):
        from desktop_agent.registry import get_tool
        tool = get_tool("locateAndClickUI")
        self.assertIsNotNone(tool)

    def test_locate_and_click_ui_missing_element(self):
        from desktop_agent.tools_screenshot import locate_and_click_ui
        res = locate_and_click_ui({})
        self.assertFalse(res.get("ok"))
        self.assertIn("Missing 'element'", res.get("error"))

    def test_dispatch_tool_locate_ui(self):
        res = tool_definitions.execute_tool("locateAndClickUI", {})
        self.assertFalse(res.get("ok"))


class TestClawAutonomousSelfHealing(unittest.TestCase):
    def test_patch_file_surgical(self):
        test_file = Path("tests/test_scratch_patch.tmp")
        try:
            test_file.write_text("def hello():\n    return 'old'\n", encoding="utf-8")
            res = patch_file(str(test_file), "return 'old'", "return 'new'")
            self.assertTrue(res.get("ok"))
            content = test_file.read_text(encoding="utf-8")
            self.assertIn("return 'new'", content)
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_autonomous_repair_loop_already_passing(self):
        # A command that passes immediately should exit cleanly on attempt 1
        res = autonomous_code_repair_loop("python -c \"print('success')\"", max_attempts=2)
        self.assertTrue(res.get("ok"))
        self.assertTrue(res.get("passed"))
        self.assertEqual(res.get("attempt"), 1)


class TestVoiceEngineLowLatency(unittest.TestCase):
    def test_voice_engine_sentence_splitting(self):
        from voice_engine import VoiceEngine
        ve = VoiceEngine()
        # Mock tts_queue to inspect enqueued sentences
        ve._tts_enabled = True
        ve.tts_queue = MagicMock()

        sample_text = "Good morning Sir! All systems are operational. WhatsApp watcher is active."
        ve.speak(sample_text)

        # Should have split into 3 distinct sentences for streaming playback
        self.assertEqual(ve.tts_queue.put.call_count, 3)
        calls = [c[0][0] for c in ve.tts_queue.put.call_args_list]
        self.assertIn("Good morning Sir!", calls[0])
        self.assertIn("All systems are operational.", calls[1])
        self.assertIn("WhatsApp watcher is active.", calls[2])


if __name__ == "__main__":
    unittest.main()
