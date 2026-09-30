"""
tests/test_os1_suite.py
Comprehensive unit test suite for OS 1 Conversational Operating System Suite in Prime AI:
1. Generative Ephemeral UI Fragments Engine (Disk, Git, Media, System)
2. HER-Inspired Warm Companion & Breathing Coral Ring Aura
3. On-Device PII Privacy Guard & Prompt Sanitizer
4. Autonomous Proactive Daily & System Briefing Engine
5. Tool Catalog Registration & Dispatch Integration
"""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from actions.os1_fragments import OS1FragmentsEngine, generate_fragment, dismiss_fragment, list_active_fragments
from actions.her_companion import HERCompanionEngine, set_her_companion_mode, get_her_visualizer_state
from actions.os1_privacy_guard import OS1PrivacyGuard, sanitize_text, get_privacy_audit
from actions.os1_briefing import OS1BriefingEngine, generate_os1_briefing
import tool_definitions


class TestOS1Fragments(unittest.TestCase):
    """Test Suite for Generative Ephemeral UI Fragments."""

    def setUp(self):
        self.test_storage = Path(__file__).resolve().parent / "tmp_os1_fragments.json"
        self.engine = OS1FragmentsEngine(storage_path=self.test_storage)

    def tearDown(self):
        if self.test_storage.exists():
            try:
                self.test_storage.unlink()
            except Exception:
                pass

    def test_generate_disk_fragment(self):
        res = self.engine.generate_fragment("disk_cleaner")
        self.assertTrue(res["ok"])
        frag = res["fragment"]
        self.assertEqual(frag["type"], "disk_cleaner")
        self.assertIn("drives", frag["content"])
        self.assertIn("temp_cache_mb", frag["content"])
        self.assertIn(res["fragment_id"], self.engine.active_fragments)

    def test_generate_git_and_media_fragment(self):
        git_res = self.engine.generate_fragment("git_card")
        self.assertTrue(git_res["ok"])
        self.assertIn("branch", git_res["fragment"]["content"])

        media_res = self.engine.generate_fragment("media_controller", {"track": "Midnight City", "artist": "M83"})
        self.assertTrue(media_res["ok"])
        self.assertEqual(media_res["fragment"]["content"]["track"], "Midnight City")

    def test_dismiss_and_list_fragments(self):
        res1 = self.engine.generate_fragment("system_status")
        res2 = self.engine.generate_fragment("media_controller")
        fid1 = res1["fragment_id"]
        fid2 = res2["fragment_id"]

        listing = self.engine.list_active_fragments()
        self.assertEqual(listing["count"], 2)

        # Dismiss one
        d_res = self.engine.dismiss_fragment(fid1)
        self.assertTrue(d_res["ok"])
        self.assertNotIn(fid1, self.engine.active_fragments)
        self.assertIn(fid2, self.engine.active_fragments)

        # Dismiss all
        d_all = self.engine.dismiss_fragment("all")
        self.assertTrue(d_all["ok"])
        self.assertEqual(len(self.engine.active_fragments), 0)


class TestHERCompanion(unittest.TestCase):
    """Test Suite for HER Companion Persona & Coral Breathing Visualizer."""

    def setUp(self):
        self.test_state = Path(__file__).resolve().parent / "tmp_her_state.json"
        self.her = HERCompanionEngine(state_file=self.test_state)

    def tearDown(self):
        if self.test_state.exists():
            try:
                self.test_state.unlink()
            except Exception:
                pass

    def test_toggle_companion_mode(self):
        res = self.her.set_companion_mode(True, warmth_level="warm", palette="amber")
        self.assertTrue(res["ok"])
        self.assertTrue(res["enabled"])
        self.assertEqual(res["warmth_level"], "warm")
        self.assertEqual(res["palette"], "amber")

        addon = self.her.get_companion_prompt_addon()
        self.assertIn("Samantha", addon)

    def test_visualizer_states_and_frames(self):
        for mode in ["idle", "listening", "thinking", "speaking"]:
            self.her.set_visualizer_state(mode)
            frame = self.her.get_visualizer_frame(t_offset=1.5)
            self.assertTrue(frame["ok"])
            self.assertEqual(frame["mode"], mode)
            params = frame["render_params"]
            self.assertGreater(params["scale"], 0.8)
            self.assertGreater(params["opacity"], 0.5)
            self.assertIn("glow_color", params)


class TestOS1PrivacyGuard(unittest.TestCase):
    """Test Suite for On-Device PII and Credential Masking."""

    def setUp(self):
        self.test_audit = Path(__file__).resolve().parent / "tmp_privacy_audit.json"
        self.guard = OS1PrivacyGuard(audit_path=self.test_audit)

    def tearDown(self):
        if self.test_audit.exists():
            try:
                self.test_audit.unlink()
            except Exception:
                pass

    def test_redact_api_keys(self):
        sample = "Here is my key: sk-proj-1234567890abcdef1234567890abcdef12345678 and AIzaSyD9876543210zyxwvutsrqponmlkjihgfed"
        res = self.guard.sanitize(sample)
        self.assertTrue(res["ok"])
        self.assertFalse(res["clean"])
        self.assertGreaterEqual(res["redacted_count"], 2)
        self.assertIn("[REDACTED_OPENAI_KEY]", res["sanitized_text"])
        self.assertIn("[REDACTED_GOOGLE_API_KEY]", res["sanitized_text"])
        self.assertNotIn("sk-proj-", res["sanitized_text"])
        self.assertNotIn("AIzaSy", res["sanitized_text"])

    def test_redact_private_key_and_password(self):
        priv_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0\n-----END RSA PRIVATE KEY-----"
        sample = f"Config: password='SuperSecret123!' and token={priv_key}"
        res = self.guard.sanitize(sample)
        self.assertIn("[REDACTED_PASSWORD]", res["sanitized_text"])
        self.assertIn("[REDACTED_PRIVATE_KEY]", res["sanitized_text"])
        self.assertNotIn("SuperSecret123!", res["sanitized_text"])

    def test_clean_input_passthrough(self):
        clean_text = "What is the capital of France and how do I sort an array in Python?"
        res = self.guard.sanitize(clean_text)
        self.assertTrue(res["clean"])
        self.assertEqual(res["redacted_count"], 0)
        self.assertEqual(res["sanitized_text"], clean_text)


class TestOS1Briefing(unittest.TestCase):
    """Test Suite for Proactive System Briefing."""

    def setUp(self):
        self.engine = OS1BriefingEngine()

    @patch("actions.os1_briefing.OS1BriefingEngine._get_system_vitals")
    @patch("actions.os1_briefing.OS1BriefingEngine._get_git_summary")
    @patch("actions.os1_briefing.OS1BriefingEngine._get_whatsapp_summary")
    @patch("actions.os1_briefing.OS1BriefingEngine._get_obsidian_recent_note")
    def test_generate_briefing(self, mock_obsidian, mock_wa, mock_git, mock_vitals):
        mock_vitals.return_value = {
            "cpu_percent": 14.5,
            "ram_percent": 45.0,
            "free_disk_gb": 120.4,
            "battery_percent": 95
        }
        mock_git.return_value = {
            "repo": "Prime",
            "branch": "main",
            "uncommitted_changes": 2
        }
        mock_wa.return_value = {
            "unread_count": 3,
            "has_unread": True,
            "focus_mode": False
        }
        mock_obsidian.return_value = {
            "recent_note": "DevLogs/Decisions.md"
        }

        res = self.engine.generate_briefing()
        self.assertTrue(res["ok"])
        text = res["spoken_text"]
        self.assertIn("Prime is active", text)
        self.assertIn("14.5%", text)
        self.assertIn("2 uncommitted changes", text)
        self.assertIn("3 unread WhatsApp messages", text)
        self.assertIn("Decisions", text)


class TestToolDefinitionsOS1Integration(unittest.TestCase):
    """Test Suite for OS 1 Tool Specifications and Execution Dispatch."""

    def test_os1_specs_registered(self):
        names = [s["name"] for s in tool_definitions.TOOL_SPECS]
        self.assertIn("generateOS1Fragment", names)
        self.assertIn("dismissOS1Fragment", names)
        self.assertIn("listActiveFragments", names)
        self.assertIn("setHERCompanionMode", names)
        self.assertIn("getHERVisualizerState", names)
        self.assertIn("sanitizePromptPrivacy", names)
        self.assertIn("generateOS1Briefing", names)

    @patch("actions.os1_fragments.generate_fragment")
    def test_execute_generate_fragment(self, mock_gen):
        mock_gen.return_value = {"ok": True, "fragment_id": "frag_01"}
        res = tool_definitions.execute_tool("generateOS1Fragment", {"type": "disk_cleaner"})
        self.assertTrue(res["ok"])
        mock_gen.assert_called_with("disk_cleaner", custom_data=None)

    @patch("actions.os1_fragments.dismiss_fragment")
    def test_execute_dismiss_fragment(self, mock_dismiss):
        mock_dismiss.return_value = {"ok": True, "message": "Dismissed"}
        res = tool_definitions.execute_tool("dismissOS1Fragment", {"fragment_id": "frag_01"})
        self.assertTrue(res["ok"])
        mock_dismiss.assert_called_with("frag_01")

    @patch("actions.her_companion.set_her_companion_mode")
    def test_execute_set_her_companion(self, mock_set_her):
        mock_set_her.return_value = {"ok": True, "enabled": True}
        res = tool_definitions.execute_tool("setHERCompanionMode", {"enabled": True, "warmth_level": "warm"})
        self.assertTrue(res["ok"])
        mock_set_her.assert_called_with(True, warmth_level="warm", palette="coral")

    @patch("actions.os1_privacy_guard.sanitize_text")
    def test_execute_sanitize_privacy(self, mock_san):
        mock_san.return_value = {"ok": True, "sanitized_text": "clean"}
        res = tool_definitions.execute_tool("sanitizePromptPrivacy", {"prompt": "test with key sk-1234"})
        self.assertTrue(res["ok"])
        mock_san.assert_called_with("test with key sk-1234")

    @patch("actions.os1_briefing.generate_os1_briefing")
    def test_execute_generate_briefing(self, mock_briefing):
        mock_briefing.return_value = {"ok": True, "spoken_text": "Good morning"}
        res = tool_definitions.execute_tool("generateOS1Briefing", {})
        self.assertTrue(res["ok"])
        mock_briefing.assert_called_once()


if __name__ == "__main__":
    unittest.main()
