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
        # When split_sentences=True is requested
        ve.speak(sample_text, split_sentences=True)

        # Should have split into 3 distinct sentences for streaming playback
        self.assertEqual(ve.tts_queue.put.call_count, 3)
        calls = [c[0][0] for c in ve.tts_queue.put.call_args_list]
        self.assertIn("Good morning Sir!", calls[0])
        self.assertIn("All systems are operational.", calls[1])
        self.assertIn("WhatsApp watcher is active.", calls[2])

        # Test continuous mode (default) delivers intact utterance without pauses
        ve.tts_queue.reset_mock()
        ve.speak(sample_text)
        self.assertEqual(ve.tts_queue.put.call_count, 1)
        self.assertIn("All systems are operational.", ve.tts_queue.put.call_args[0][0])

    def test_sagar_tamang_ultron_and_friday_voice_routing(self):
        from voice_engine import voice
        orig_voice = voice.current_voice
        orig_filter = voice.stark_filter_enabled
        try:
            # Test Ultron voice activation & automatic Stark DSP filter
            res_ultron = voice.set_voice("ultron")
            self.assertEqual(res_ultron, "ultron")
            self.assertTrue(voice.stark_filter_enabled)
            self.assertAlmostEqual(voice.stark_filter_intensity, 0.75)

            # Test Friday voice activation
            res_friday = voice.set_voice("friday")
            self.assertEqual(res_friday, "friday")

            # Test Onyx alias
            res_onyx = voice.set_voice("onyx")
            self.assertEqual(res_onyx, "ultron")
            self.assertTrue(voice.stark_filter_enabled)

            # Test Nova alias
            res_nova = voice.set_voice("nova")
            self.assertEqual(res_nova, "friday")
        finally:
            voice.set_voice(orig_voice)
            voice.stark_filter_enabled = orig_filter


class TestStarkIntercomAudioDSP(unittest.TestCase):
    """Feature 6: Cinematic Intercom / Stark Radio Audio DSP Filter Tests."""

    def test_stark_filter_toggle_and_intensity(self):
        from voice_engine import voice
        orig_state = voice.stark_filter_enabled
        orig_intensity = voice.stark_filter_intensity
        try:
            res = voice.set_stark_filter(True, 0.85)
            self.assertTrue(voice.stark_filter_enabled)
            self.assertAlmostEqual(voice.stark_filter_intensity, 0.85)
            self.assertTrue(res)

            res_off = voice.set_stark_filter(False)
            self.assertFalse(voice.stark_filter_enabled)
            self.assertFalse(res_off)
        finally:
            voice.stark_filter_enabled = orig_state
            voice.stark_filter_intensity = orig_intensity

    def test_stark_filter_dsp_pipeline(self):
        import numpy as np
        from voice_engine import apply_stark_intercom_filter

        sample_rate = 24000
        # 0.5s of test tone (440 Hz sine wave)
        t = np.linspace(0, 0.5, int(sample_rate * 0.5), endpoint=False)
        mono_signal = (np.sin(2 * np.pi * 440 * t) * 0.8).astype(np.float32)

        filtered = apply_stark_intercom_filter(mono_signal, sample_rate, intensity=0.7)
        self.assertEqual(filtered.shape, mono_signal.shape)
        self.assertFalse(np.isnan(filtered).any())
        self.assertFalse(np.isinf(filtered).any())
        # Soft saturation should keep bounds within [-1.0, 1.0]
        self.assertTrue(np.all(filtered >= -1.05))
        self.assertTrue(np.all(filtered <= 1.05))

    def test_stark_filter_tool_execution(self):
        res = tool_definitions.execute_tool("toggleStarkAudioFilter", {"enabled": True, "intensity": 0.75})
        self.assertTrue(res.get("ok"))
        self.assertIn("Stark Intercom Audio Filter", res.get("message"))


class TestWirelessAndroidADBControl(unittest.TestCase):
    """Feature 4: Wireless Android ADB Control Tests."""

    def test_android_manager_init(self):
        from actions.android_manager import AndroidManager
        mgr = AndroidManager()
        self.assertIsNotNone(mgr)
        self.assertEqual(mgr.default_port, 5555)

    @patch("actions.android_manager.subprocess.run")
    def test_list_devices(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="List of devices attached\n192.168.1.50:5555\tdevice\nemulator-5554\tdevice\n"
        )
        from actions.android_manager import android_manager
        devices = android_manager.list_devices()
        self.assertTrue(devices.get("ok"))
        serials = [d["serial"] for d in devices.get("devices", [])]
        self.assertIn("192.168.1.50:5555", serials)
        self.assertIn("emulator-5554", serials)

    @patch("actions.android_manager.subprocess.run")
    def test_get_battery_status(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Current Battery Service state:\n  level: 85\n  status: 2\n  temperature: 300\n"
        )
        from actions.android_manager import android_manager
        status = android_manager.get_battery_status()
        self.assertTrue(status.get("ok"))
        self.assertEqual(status.get("level"), 85)
        self.assertEqual(status.get("status"), "Charging")

    @patch("actions.android_manager.subprocess.run")
    def test_wake_and_unlock(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        from actions.android_manager import android_manager
        res = android_manager.wake_and_unlock()
        self.assertTrue(res.get("ok"))
        self.assertIn("dismissed lock screen", res.get("message").lower())

    def test_android_tool_definitions_dispatch(self):
        with patch("actions.android_manager.AndroidManager.get_battery_status", return_value={"ok": True, "level": 92}):
            res = tool_definitions.execute_tool("androidBattery", {})
            self.assertTrue(res.get("ok"))
            self.assertEqual(res.get("level"), 92)


class TestMobileRoomGestureEndpoint(unittest.TestCase):
    """Feature 3: MediaPipe Gesture and Mobile Cockpit Endpoints."""

    def setUp(self):
        from mobile_room_server import app
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_gesture_open_palm_mute(self):
        resp = self.client.post("/api/gesture", json={"gesture": "open_palm"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("action"), "barge_in_and_mute")

    def test_gesture_thumbs_up_confirm(self):
        resp = self.client.post("/api/gesture", json={"gesture": "thumbs_up"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("action"), "confirm_draft")

    def test_api_command_execution(self):
        with patch("ai_agent.AIAgent.process_message", return_value="Command executed successfully, Sir."):
            resp = self.client.post("/api/command", json={"command": "system status"})
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data.get("ok"))
            self.assertIn("Command executed", data.get("reply"))


class TestVocalIsolationDSP(unittest.TestCase):
    """VoiceStudio Feature 4: Vocal Isolation & Noise Suppression DSP Tests."""

    def test_vocal_isolation_state_toggle(self):
        import actions.vocal_isolation as vi
        orig = vi.get_vocal_isolation_state()
        try:
            res_on = vi.set_vocal_isolation_state(True, 0.85)
            self.assertTrue(res_on.get("ok"))
            self.assertTrue(res_on.get("enabled"))
            self.assertAlmostEqual(res_on.get("sensitivity"), 0.85)

            res_off = vi.set_vocal_isolation_state(False)
            self.assertFalse(res_off.get("enabled"))
        finally:
            vi.set_vocal_isolation_state(orig.get("enabled", True), orig.get("sensitivity", 0.75))

    def test_vocal_isolation_filtering(self):
        import numpy as np
        from actions.vocal_isolation import apply_vocal_isolation

        sr = 16000
        t = np.linspace(0, 0.4, int(sr * 0.4), endpoint=False)
        # Low rumble (40Hz fan) + Speech tone (1000Hz) + High hiss (8000Hz)
        signal = (np.sin(2 * np.pi * 40 * t) * 0.3 + np.sin(2 * np.pi * 1000 * t) * 0.6 + np.sin(2 * np.pi * 8000 * t) * 0.2).astype(np.float32)

        isolated = apply_vocal_isolation(signal, sample_rate=sr, sensitivity=0.8)
        self.assertEqual(isolated.shape, signal.shape)
        self.assertFalse(np.isnan(isolated).any())
        self.assertFalse(np.isinf(isolated).any())

    def test_vocal_isolation_tool_dispatch(self):
        res = tool_definitions.execute_tool("toggleVocalNoiseIsolation", {"enabled": True, "sensitivity": 0.8})
        self.assertTrue(res.get("ok"))
        self.assertIn("Vocal Isolation", res.get("message"))


class TestSystemWideDictation(unittest.TestCase):
    """VoiceStudio Feature 3: System-Wide Dictation & Native App Typing Tests."""

    def test_dictation_status(self):
        from actions.dictation_manager import get_dictation_status
        status = get_dictation_status()
        self.assertTrue(status.get("ok"))
        self.assertIn("is_active", status)
        self.assertIn("active_window", status)

    @patch("actions.dictation_manager._simulate_paste")
    @patch("pyperclip.copy")
    @patch("pyperclip.paste", return_value="original_clipboard_data")
    def test_insert_text_clipboard_preservation(self, mock_paste, mock_copy, mock_sim):
        from actions.dictation_manager import insert_text_into_active_window
        res = insert_text_into_active_window("Hello World from Prime Dictation", restore_clipboard=True)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("characters_inserted"), len("Hello World from Prime Dictation"))
        mock_sim.assert_called_once()
        # Should have copied new text, then restored original clipboard data
        mock_copy.assert_any_call("Hello World from Prime Dictation")
        mock_copy.assert_any_call("original_clipboard_data")

    def test_dictate_tool_dispatch(self):
        with patch("actions.dictation_manager.insert_text_into_active_window", return_value={"ok": True, "target_window": "Test App", "message": "Success"}):
            res = tool_definitions.execute_tool("dictateToActiveWindow", {"text": "Unit Test Dictation"})
            self.assertTrue(res.get("ok"))
            self.assertEqual(res.get("target_window"), "Test App")


class TestVoiceStudioAndCloning(unittest.TestCase):
    """VoiceStudio Features 1 & 2: Local Voice Cloning, Voice Design, and Engine Adapter Tests."""

    def test_list_voice_profiles(self):
        from actions.voice_studio_manager import list_voice_profiles
        profiles = list_voice_profiles()
        self.assertTrue(profiles.get("ok"))
        self.assertIn("local_profiles", profiles)
        profile_ids = [p["id"] for p in profiles.get("local_profiles", [])]
        self.assertIn("ultron", profile_ids)
        self.assertIn("friday", profile_ids)

    def test_design_voice_persona(self):
        from actions.voice_studio_manager import design_voice
        res = design_voice("Deep resonant British butler with calm cadence", "Alfred")
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("name"), "Alfred")
        self.assertEqual(res.get("profile_id"), "designed_alfred")
        attrs = res.get("attributes", {})
        self.assertEqual(attrs.get("gender"), "male")
        self.assertEqual(attrs.get("pitch"), "low")
        self.assertEqual(attrs.get("accent"), "en-GB")

    def test_clone_voice_from_reference_file(self):
        import wave
        from pathlib import Path
        from actions.voice_studio_manager import clone_voice

        # Generate a small dummy reference WAV file
        test_wav = Path("tests/test_ref_voice.wav")
        try:
            with wave.open(str(test_wav), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                # 0.2s of 440Hz tone
                import numpy as np
                t = np.linspace(0, 0.2, int(16000 * 0.2), endpoint=False)
                tone = (np.sin(2 * np.pi * 440 * t) * 30000).astype(np.int16)
                wf.writeframes(tone.tobytes())

            res = clone_voice(str(test_wav), "Tony Stark")
            self.assertTrue(res.get("ok"))
            self.assertEqual(res.get("name"), "Tony Stark")
            self.assertEqual(res.get("profile_id"), "cloned_tony_stark")
        finally:
            if test_wav.exists():
                test_wav.unlink()
            cleaned = Path("tests/test_ref_voice_cleaned.wav")
            if cleaned.exists():
                cleaned.unlink()

    def test_voicestudio_tool_dispatch(self):
        res_list = tool_definitions.execute_tool("listVoiceProfiles", {})
        self.assertTrue(res_list.get("ok"))

        res_design = tool_definitions.execute_tool("designVoicePersona", {
            "description": "Warm cheerful female assistant",
            "profile_name": "Sunny"
        })
        self.assertTrue(res_design.get("ok"))
        self.assertEqual(res_design.get("name"), "Sunny")

        res_set = tool_definitions.execute_tool("setVoiceProfile", {"profile_id": "ultron"})
        self.assertTrue(res_set.get("ok"))


if __name__ == "__main__":
    unittest.main()


