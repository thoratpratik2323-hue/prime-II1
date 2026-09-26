"""
test_feature_matrix.py — Comprehensive Unit & Integration Test Matrix for Prime AI.
Verifies all capabilities one by one:
  - System Telemetry & Built-in OS Dominion Tools
  - File System Automation & Safety Checks
  - Confirmation Tokens & Sensitive Action Gating
  - Application & Website Directory Registries
  - WhatsApp Voice/Video Calling, Natural Time Parsing & Call Scheduling
  - Spoken Voice Bilingual Routing & Text Sanitization
  - Safe AST Code Execution Sandbox & Security Protections
  - Multi-Language Coding Intent Router
  - Obsidian RAG Second Brain Read/Write/Search
  - Agency Roster & Specialist Personas
  - Self-Healing Diagnostic Engine
  - Neural Mesh Bridge & Pairing Tokens
  - Predictive Context Engine
  - Telemetry Traces Logger
  - AI Agent History & Compatibility Parity
"""

from __future__ import annotations

import os
import sys
import time
import json
import unittest
from pathlib import Path

# Ensure root path is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import tool_definitions
from tool_definitions import execute_tool
from desktop_agent.registry import TOOLS, load_all
import whatsapp_manager
from voice_engine import voice, is_hindi_or_hinglish, check_barge_in_phrase, BARGE_IN_KEYWORDS
from core.safe_exec import validate_ast, UnsafeCodeError
from core.intent_router import is_coding_task
import obsidian_rag
import agency_roster
import self_healing_engine
from neural_mesh_bridge import mesh_bridge
from predictive_context_engine import predictive_engine
from prime_traces import trace_logger
from ai_agent import agent
import core.vector_memory as vector_memory
import core.terminal_sentinel as terminal_sentinel
import remote_bridge
import core.whatsapp_voicemail as whatsapp_voicemail
import core.clipboard_sentinel as clipboard_sentinel
import core.git_sentinel as git_sentinel
import core.standup_engine as standup_engine
import core.thermal_guard as thermal_guard


class TestPrimeFeatureMatrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_all()

    # =========================================================================
    # 1. System Telemetry & Built-in OS Dominion Tools
    # =========================================================================
    def test_01_tool_getCurrentTime(self):
        """Feature 1: Real-time system clock formatted for human interaction."""
        res = execute_tool("getCurrentTime", {})
        self.assertTrue(res.get("ok"))
        self.assertIn("Current system time is", str(res.get("result", "")))

    def test_02_tool_systemInfo(self):
        """Feature 2: Real-time CPU, RAM, and Disk telemetry."""
        res = execute_tool("systemInfo", {})
        self.assertTrue(res.get("ok"))
        data = res.get("result", {})
        self.assertIn("cpu", data)
        self.assertIn("ram", data)
        self.assertIn("disks", data)

    def test_03_tool_gpuInfo(self):
        """Feature 3: GPU metrics with graceful degradation if no NVIDIA card."""
        res = execute_tool("gpuInfo", {})
        self.assertIsInstance(res, dict)
        self.assertTrue("ok" in res or "gpus" in res.get("result", {}))

    def test_04_tool_temperatureInfo(self):
        """Feature 4: Hardware thermal sensors reporting."""
        res = execute_tool("temperatureInfo", {})
        self.assertIsInstance(res, dict)
        self.assertIn("ok", res)

    def test_05_tool_listDrives(self):
        """Feature 5: Drive mount points and storage volumes enumeration."""
        res = execute_tool("listDrives", {})
        self.assertTrue(res.get("ok"))
        drives = res.get("result", {}).get("drives", [])
        self.assertIsInstance(drives, list)
        self.assertGreater(len(drives), 0)

    def test_06_tool_getCursorPosition(self):
        """Feature 6: Active mouse cursor coordinates on primary display."""
        res = execute_tool("getCursorPosition", {})
        self.assertTrue(res.get("ok"))
        data = res.get("result", {})
        self.assertIn("x", data)
        self.assertIn("y", data)

    # =========================================================================
    # 2. Application & Website Directory Registries
    # =========================================================================
    def test_07_website_directory_lookup(self):
        """Feature 7: Standard web platform domain resolvers."""
        from desktop_agent.tools_websites import SITE_URLS
        self.assertIn("google", SITE_URLS)
        self.assertIn("youtube", SITE_URLS)
        self.assertIn("github", SITE_URLS)
        self.assertIn("whatsapp", SITE_URLS)
        self.assertIn("reddit", SITE_URLS)
        self.assertTrue(SITE_URLS["google"].startswith("https://"))

    def test_08_app_commands_registry(self):
        """Feature 8: Standard native Windows application registry."""
        from desktop_agent.tools_applications import APP_COMMANDS
        self.assertIn("notepad", APP_COMMANDS)
        self.assertIn("calc", APP_COMMANDS)
        self.assertIn("calculator", APP_COMMANDS)
        self.assertIn("vscode", APP_COMMANDS)

    # =========================================================================
    # 3. File System Automation & Safety Sandbox
    # =========================================================================
    def test_09_create_read_delete_file_lifecycle(self):
        """Feature 9: File lifecycle — create, read, and delete temporary test file."""
        test_file = BASE_DIR / "temp_feature_test.txt"
        test_content = "Prime AI Feature Matrix Verification Payload"

        # Create
        res_create = execute_tool("createFile", {
            "path": str(test_file),
            "content": test_content,
            "overwrite": True
        })
        self.assertTrue(res_create.get("ok"))

        # Read
        res_read = execute_tool("readFile", {"path": str(test_file)})
        self.assertTrue(res_read.get("ok"))
        self.assertIn(test_content, str(res_read.get("result", {}).get("result", "")))

        # Cleanup via recycling / safe unlink
        if test_file.exists():
            test_file.unlink()

    def test_10_list_files_and_search_files(self):
        """Feature 10: Filesystem listing and pattern matching search."""
        res_list = execute_tool("listFiles", {"path": str(BASE_DIR), "max_items": 10})
        self.assertTrue(res_list.get("ok"))
        items = res_list.get("result", {}).get("items", [])
        self.assertIsInstance(items, list)

        res_search = execute_tool("searchFiles", {
            "root_path": str(BASE_DIR),
            "query": "README",
            "max_results": 5
        })
        self.assertTrue(res_search.get("ok"))
        matches = res_search.get("result", {}).get("matches", [])
        self.assertTrue(any("README.md" in str(m) for m in matches))

    # =========================================================================
    # 4. Confirmation Tokens & Sensitive Action Gating
    # =========================================================================
    def test_11_confirmation_token_lifecycle(self):
        """Feature 11: Single-use cryptographic confirmation token issuance & validation."""
        from desktop_agent.tools_confirmation import (
            request_power_action,
            consume_token,
        )
        from desktop_agent.registry import ToolError

        res = request_power_action({"action": "lock"})
        self.assertTrue(res.get("requires_confirmation"))
        token = res.get("token")
        self.assertIsInstance(token, str)

        # Reject invalid token
        with self.assertRaises(ToolError):
            consume_token("lock", "WRONGTOK")

        # Accept valid token (consumes token)
        consume_token("lock", token)

        # Replay attempt must be rejected (single-use constraint)
        with self.assertRaises(ToolError):
            consume_token("lock", token)

    def test_12_autostart_status(self):
        """Feature 12: Windows registry run key startup query."""
        res = execute_tool("getAutoStartStatus", {})
        self.assertTrue(res.get("ok"))
        self.assertIn("enabled", res.get("result", {}))

    # =========================================================================
    # 5. WhatsApp Voice/Video Calling & Natural Time Parser
    # =========================================================================
    def test_13_whatsapp_phone_normalization_matrix(self):
        """Feature 13: Phone number normalization across various formats."""
        # 10 digit Indian number
        self.assertEqual(whatsapp_manager.normalize_phone_number("9876543210"), "+919876543210")
        # With spaces and dashes
        self.assertEqual(whatsapp_manager.normalize_phone_number("98765 43210"), "+919876543210")
        self.assertEqual(whatsapp_manager.normalize_phone_number("+91 98765-43210"), "+919876543210")
        # International number
        self.assertEqual(whatsapp_manager.normalize_phone_number("+1 (555) 234-5678"), "+15552345678")

    def test_14_whatsapp_resolve_recipient(self):
        """Feature 14: Recipient directory fuzzy matching vs raw phone numbers."""
        phone, name = whatsapp_manager.resolve_recipient("Rohit")
        self.assertIsNotNone(name)
        # Raw number direct pass-through
        phone_raw, name_raw = whatsapp_manager.resolve_recipient("+919999988888")
        self.assertEqual(phone_raw, "+919999988888")

    def test_15_whatsapp_parse_schedule_time_relative(self):
        """Feature 15: Relative time expressions parsing."""
        t1 = whatsapp_manager.parse_schedule_time("in 10 minutes")
        self.assertIsNotNone(t1)
        t2 = whatsapp_manager.parse_schedule_time("15 mins")
        self.assertIsNotNone(t2)
        t3 = whatsapp_manager.parse_schedule_time("in 2 hours")
        self.assertIsNotNone(t3)

    def test_16_whatsapp_parse_schedule_time_hinglish(self):
        """Feature 16: Hinglish conversational time parsing."""
        t1 = whatsapp_manager.parse_schedule_time("aadha ghanta baad")
        self.assertIsNotNone(t1)
        t2 = whatsapp_manager.parse_schedule_time("ek ghanta baad")
        self.assertIsNotNone(t2)
        t3 = whatsapp_manager.parse_schedule_time("6 baje")
        self.assertIsNotNone(t3)
        t4 = whatsapp_manager.parse_schedule_time("sham 7 baje")
        self.assertIsNotNone(t4)

    def test_17_whatsapp_schedule_and_cancel_lifecycle(self):
        """Feature 17: Scheduled call queuing, retrieval, and cancellation."""
        sched_res = whatsapp_manager.schedule_whatsapp_call(
            recipient="MatrixTestContact",
            time_str="in 50 minutes",
            call_type="video",
            note="Feature verification test call"
        )
        self.assertTrue(sched_res.get("ok"))
        call_id = sched_res.get("call_id")

        # List scheduled calls
        list_res = whatsapp_manager.list_scheduled_calls()
        self.assertTrue(list_res.get("ok"))
        self.assertTrue(any(c.get("id") == call_id for c in list_res.get("scheduled_calls", [])))

        # Cancel call
        cancel_res = whatsapp_manager.cancel_scheduled_call(call_id)
        self.assertTrue(cancel_res.get("ok"))

        # Verify not pending anymore
        list_res_after = whatsapp_manager.list_scheduled_calls()
        self.assertFalse(any(c.get("id") == call_id for c in list_res_after.get("scheduled_calls", [])))

    # =========================================================================
    # 6. Spoken Voice Bilingual Routing & Text Sanitization
    # =========================================================================
    def test_18_spoken_voice_hindi_hinglish_detector(self):
        """Feature 18: Linguistic routing — Hindi/Hinglish vs English."""
        # Devanagari Hindi
        self.assertTrue(is_hindi_or_hinglish("नमस्ते, आप कैसे हैं?"))
        # Hinglish speech patterns
        self.assertTrue(is_hindi_or_hinglish("bhai Rohit ko message bhej de"))
        self.assertTrue(is_hindi_or_hinglish("kya chal raha hai bhai"))
        self.assertTrue(is_hindi_or_hinglish("call disconnect kar do"))
        # Pure English technical commands
        self.assertFalse(is_hindi_or_hinglish("Run git status and show git commits"))
        self.assertFalse(is_hindi_or_hinglish("What is the current system CPU load?"))

    def test_19_voice_engine_text_sanitizer(self):
        """Feature 19: TTS cleaner — strips markdown links, backticks, emojis."""
        raw = "Check [Google](https://google.com) and run `npm test`! 🚀 **Great!**"
        clean = voice._sanitize_for_tts(raw)
        self.assertNotIn("https://", clean)
        self.assertNotIn("`", clean)
        self.assertNotIn("**", clean)
        self.assertIn("Google", clean)

    def test_20_voice_engine_rate_calculation(self):
        """Feature 20: Edge-TTS speech rate calculation (+22% speed boost)."""
        rate_str = voice._get_edge_rate()
        self.assertIn("%", rate_str)
        self.assertTrue(rate_str.startswith("+") or rate_str == "+0%")

    # =========================================================================
    # 7. Safe AST Code Execution Sandbox & Security Protections
    # =========================================================================
    def test_21_safe_exec_benign_expressions(self):
        """Feature 21: Safe Python evaluation of benign code."""
        code = "result = 2 + 3 * 4"
        # Should validate without raising UnsafeCodeError
        validate_ast(code, allowed_names={"result"}, allowed_attrs={})

    def test_22_safe_exec_blocks_subprocess(self):
        """Feature 22: Safe exec rejects subprocess injection."""
        code = "import subprocess; subprocess.run(['calc'])"
        with self.assertRaises(UnsafeCodeError):
            validate_ast(code, allowed_names=set(), allowed_attrs={})

    def test_23_safe_exec_blocks_os_module(self):
        """Feature 23: Safe exec rejects os system calls."""
        code = "import os; os.system('calc')"
        with self.assertRaises(UnsafeCodeError):
            validate_ast(code, allowed_names=set(), allowed_attrs={})

    def test_24_safe_exec_blocks_dunder_traversal(self):
        """Feature 24: Safe exec rejects dunder sandbox escape chains."""
        code = "x = ().__class__.__bases__[0].__subclasses__()"
        with self.assertRaises(UnsafeCodeError):
            validate_ast(code, allowed_names=set(), allowed_attrs={})

    # =========================================================================
    # 8. Cognitive Intent Router & Multi-Language Code Classification
    # =========================================================================
    def test_25_intent_router_multilingual_code_detection(self):
        """Feature 25: Intent router detects code tasks across languages."""
        self.assertTrue(is_coding_task("write a Python decorator for caching"))
        self.assertTrue(is_coding_task("how to implement quicksort in Rust"))
        self.assertTrue(is_coding_task("fix this JavaScript promise rejection"))
        self.assertTrue(is_coding_task("write an SQL query to select active users"))
        self.assertTrue(is_coding_task("create a C++ class with virtual destructor"))

    def test_26_intent_router_conversational_queries(self):
        """Feature 26: Intent router filters non-coding chit-chat."""
        self.assertFalse(is_coding_task("What is the capital of India?"))
        self.assertFalse(is_coding_task("Tell me a funny joke"))
        self.assertFalse(is_coding_task("How is the weather today?"))
        self.assertFalse(is_coding_task("Good morning Prime, how are you?"))

    # =========================================================================
    # 9. Second Brain (Obsidian RAG Vault)
    # =========================================================================
    def test_27_obsidian_rag_note_lifecycle(self):
        """Feature 27: Obsidian RAG note creation, search, and safe deletion."""
        vault = obsidian_rag.get_vault_path()
        self.assertTrue(vault.exists())

        title = "matrix_test_second_brain"
        content = "Obsidian Second Brain integration verified for Prime AI."
        write_res = obsidian_rag.write_note(title, content)
        self.assertIn("Successfully saved", write_res)

        # Search for it
        results = obsidian_rag.search_notes("matrix_test_second_brain")
        self.assertTrue(any(r["title"] == title for r in results))

        # Cleanup
        f = vault / f"{title}.md"
        if f.exists():
            f.unlink()

    # =========================================================================
    # 10. Agency Agent Roster & Specialist Personas
    # =========================================================================
    def test_28_agency_roster_loaded_divisions(self):
        """Feature 28: Agency Roster has coverage across all 6 core disciplines."""
        agents = agency_roster.load_all_agency_agents()
        self.assertGreaterEqual(len(agents), 270)
        # Check core disciplines
        self.assertIn("backend-architect", agents)
        self.assertIn("penetration-tester", agents)
        self.assertIn("web-gis-developer", agents)
        self.assertIn("growth-hacker", agents)
        self.assertIn("ui-designer", agents)
        self.assertIn("test-automation-engineer", agents)

    def test_29_agency_roster_instructions_retrieval(self):
        """Feature 29: Specialist agent instructions parser."""
        agent_data = agency_roster.get_agent_by_name("penetration-tester")
        self.assertIsNotNone(agent_data)
        instr = agency_roster.get_agent_instructions(agent_data)
        self.assertIn("security", instr.lower())

    # =========================================================================
    # 11. Self-Healing & Diagnostics Engine
    # =========================================================================
    def test_30_self_healing_engine_audit(self):
        """Feature 30: Self-healing full-system diagnostic audit."""
        report = self_healing_engine.self_healer.run_full_system_audit()
        self.assertEqual(report["overall_status"], "HEALTHY")
        self.assertEqual(report["passed_tests"], report["total_tests"])
        self.assertGreater(report["total_tests"], 0)

    # =========================================================================
    # 12. Neural Mesh Bridge & Mobile Room Server
    # =========================================================================
    def test_31_neural_mesh_pairing_token(self):
        """Feature 31: Neural Mesh Bridge pairing token lifecycle."""
        token = mesh_bridge.auth_token
        self.assertIsInstance(token, str)
        self.assertEqual(len(token), 8)
        self.assertTrue(mesh_bridge.verify_token(token))
        self.assertFalse(mesh_bridge.verify_token("INVALID0"))

    # =========================================================================
    # 13. Predictive Context Engine & Stack Detection
    # =========================================================================
    def test_32_predictive_context_stack_detection(self):
        """Feature 32: Tech stack inference from workspace signatures."""
        predictive_engine._prefetch_codebase_context("Prime")
        stack = predictive_engine._cached_project_context.get("stack", [])
        self.assertIn("Python", stack)

    # =========================================================================
    # 14. Prime Telemetry Traces Logger
    # =========================================================================
    def test_33_prime_traces_execution_logging(self):
        """Feature 33: Structured telemetry traces lifecycle."""
        trace = trace_logger.start_trace("Test Feature Matrix Trace")
        self.assertIsNotNone(trace)
        trace_logger.record_tool_call(trace, "testTool", {"arg": 1}, {"result": "ok"})
        trace_logger.end_trace(trace, response="Trace completed successfully")
        self.assertEqual(trace.get("status"), "success")
        self.assertEqual(len(trace.get("tools_called", [])), 1)

    # =========================================================================
    # 15. AI Agent Persona Management & Parity
    # =========================================================================
    def test_34_agent_persona_activation_lifecycle(self):
        """Feature 34: Dynamic persona morphing and reset."""
        # Activate persona
        activated = agent.activate_persona("code-reviewer")
        self.assertEqual(activated, "Code Reviewer")
        self.assertIsNotNone(agent.active_persona)

        # Deactivate
        agent.deactivate_persona()
        self.assertIsNone(agent.active_persona)

    def test_35_agent_process_input_and_message_parity(self):
        """Feature 35: Method parity between process_input and process_message."""
        self.assertTrue(hasattr(agent, "process_input"))
        self.assertTrue(hasattr(agent, "process_message"))
        self.assertEqual(agent.process_input.__name__, agent.process_message.__name__)

    # =========================================================================
    # 16. Full-Duplex Barge-In Sentinel & Speech Interruption
    # =========================================================================
    def test_36_barge_in_detection_and_interruption(self):
        """Feature 36: Speech interruption keyword detection and barge_in API."""
        self.assertTrue(check_barge_in_phrase("stop please"))
        self.assertTrue(check_barge_in_phrase("ruko ek second"))
        self.assertTrue(check_barge_in_phrase("wait"))
        self.assertTrue(check_barge_in_phrase("chup ho jao"))
        self.assertFalse(check_barge_in_phrase("open chrome and play song"))

        # Test barge_in method returns boolean and terminates speech cleanly
        interrupted = voice.barge_in()
        self.assertIsInstance(interrupted, bool)

    # =========================================================================
    # 17. Recurring WhatsApp Call Scheduler & Voice Note Transcriber
    # =========================================================================
    def test_37_recurring_whatsapp_call_scheduling(self):
        """Feature 37: Recurring daily/weekly WhatsApp call scheduling."""
        res = whatsapp_manager.schedule_whatsapp_call(
            recipient="Papa",
            time_str="5:00 PM",
            call_type="voice",
            recurring="daily"
        )
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("recurring"), "daily")
        self.assertIn("recurring: daily", res.get("message", ""))

        # Cancel test schedule to keep clean state
        call_id = res.get("call_id")
        if call_id:
            cancel_res = whatsapp_manager.cancel_scheduled_call(call_id)
            self.assertTrue(cancel_res.get("ok"))

    def test_38_whatsapp_audio_transcription_fallback(self):
        """Feature 38: WhatsApp voice note audio transcriber fallback gracefully on missing file."""
        res = whatsapp_manager.transcribe_whatsapp_audio("non_existent_audio_sample.ogg")
        self.assertFalse(res.get("ok"))
        self.assertIn("Audio file not found", res.get("error", ""))

    # =========================================================================
    # 18. Semantic Vector Memory & Dev Log Crystallizer
    # =========================================================================
    def test_39_vector_memory_and_dev_log_crystallizer(self):
        """Feature 39: TF-IDF & Cosine Similarity search and Obsidian dev log crystallizer."""
        index = vector_memory.VectorMemoryIndex()
        index.add_document("doc1", "Python async event loop audio voice streaming architecture")
        index.add_document("doc2", "WhatsApp automation pyautogui chrome web calling and chats")

        results = index.search("voice audio stream", top_k=2)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["id"], "doc1")

        # Test Dev Log Crystallizer
        res = vector_memory.crystallize_dev_log(
            summary="Unit Test Dev Log",
            details="Verifying automated dev log crystallization into Obsidian.",
            tags=["test", "crystallize"]
        )
        self.assertTrue(res.get("ok"))
        self.assertTrue(Path(res["path"]).exists())
        # Clean up test note
        try:
            os.remove(res["path"])
        except Exception:
            pass

    # =========================================================================
    # 19. Proactive Terminal Error Sentinel & Auto-Fix Interceptor
    # =========================================================================
    def test_40_terminal_sentinel_diagnosis_and_auto_heal(self):
        """Feature 40: Error traceback parsing and auto-fix resolution."""
        sentinel = terminal_sentinel.get_terminal_sentinel()
        
        # Test missing python module with mapping (e.g. cv2 -> opencv-python)
        py_err = "Traceback (most recent call last):\nModuleNotFoundError: No module named 'cv2'"
        diag = sentinel.intercept_error("python script.py", py_err)
        self.assertTrue(diag.get("detected"))
        self.assertEqual(diag.get("error_type"), "missing_python_module")
        self.assertEqual(diag.get("auto_heal_command"), "pip install opencv-python")

        # Test port in use
        port_err = "Error: listen EADDRINUSE: address already in use :::8080"
        diag_port = sentinel.intercept_error("npm start", port_err)
        self.assertTrue(diag_port.get("detected"))
        self.assertEqual(diag_port.get("error_type"), "port_in_use")
        self.assertIn("8080", diag_port.get("auto_heal_command", ""))

    # =========================================================================
    # 20. Remote Bridge & Out-of-Home Link
    # =========================================================================
    def test_41_remote_bridge_alerts_and_commands(self):
        """Feature 41: Remote alert buffering and authenticated command execution."""
        bridge = remote_bridge.get_remote_bridge()

        # Alert dispatch
        alert_res = bridge.send_remote_alert("Test Notification", "Testing out-of-home bridge", level="info")
        self.assertTrue(alert_res.get("ok"))
        self.assertEqual(alert_res["alert"]["title"], "Test Notification")

        # Remote command /status
        status_res = bridge.execute_remote_command("/status")
        self.assertTrue(status_res.get("ok"))
        self.assertIn("PRIME STATUS REPORT", status_res.get("output", ""))

        # Remote command /help
        help_res = bridge.execute_remote_command("/help")
        self.assertTrue(help_res.get("ok"))
        self.assertIn("/status", help_res.get("output", ""))

    # =========================================================================
    # 21. Tool Registry Dispatch for New Capabilities
    # =========================================================================
    def test_42_new_tools_dispatch_integration(self):
        """Feature 42: Verification of execute_tool dispatch for all 5 new modules."""
        # 1. searchSecondBrainSemantic
        res_sem = execute_tool("searchSecondBrainSemantic", {"query": "voice"})
        self.assertTrue(res_sem.get("ok"))

        # 2. interceptTerminalError
        res_sent = execute_tool("interceptTerminalError", {
            "command": "python test.py",
            "stderr": "ModuleNotFoundError: No module named 'yaml'"
        })
        self.assertTrue(res_sent.get("ok"))
        self.assertEqual(res_sent.get("diagnosis", {}).get("target"), "pyyaml")

        # 3. sendRemoteAlert
        res_alert = execute_tool("sendRemoteAlert", {"title": "Test", "message": "Test Message"})
        self.assertTrue(res_alert.get("ok"))

        # 4. transcribeWhatsAppAudio
        res_audio = execute_tool("transcribeWhatsAppAudio", {"audio_path": "non_existent.ogg"})
        self.assertFalse(res_audio.get("ok"))

    # =========================================================================
    # 22. WhatsApp Voicemail & Auto-Responder Sentinel
    # =========================================================================
    def test_43_whatsapp_voicemail_and_dnd_lifecycle(self):
        """Feature 43: DND focus mode toggle and automated voicemail call interception."""
        # Enable DND
        set_res = whatsapp_voicemail.set_dnd_mode(True, reason="Deep coding sprint")
        self.assertTrue(set_res.get("ok"))
        self.assertTrue(set_res.get("dnd_enabled"))

        # Incoming call during DND -> auto_responded (test mode: don't dispatch live message)
        call_res = whatsapp_voicemail.handle_voicemail_event("Rohan", call_type="voice", dispatch_message=False)
        self.assertTrue(call_res.get("ok"))
        self.assertEqual(call_res.get("action"), "auto_responded")
        self.assertIn("Deep coding sprint", call_res.get("voicemail_text", ""))

        # Retrieve call logs
        logs_res = whatsapp_voicemail.get_call_logs(limit=5)
        self.assertTrue(logs_res.get("ok"))
        self.assertTrue(len(logs_res.get("calls", [])) > 0)

        # Disable DND
        dis_res = whatsapp_voicemail.set_dnd_mode(False)
        self.assertTrue(dis_res.get("ok"))
        self.assertFalse(dis_res.get("dnd_enabled"))

    # =========================================================================
    # 23. Intelligent Clipboard Memory & Auto-Explainer
    # =========================================================================
    def test_44_clipboard_sentinel_classification_and_explanation(self):
        """Feature 44: Clipboard classification and instant explanation."""
        sentinel = clipboard_sentinel.get_clipboard_sentinel()

        # Test Classification
        self.assertEqual(sentinel.classify_snippet("Traceback (most recent call last):\nValueError: bad"), "traceback")
        self.assertEqual(sentinel.classify_snippet('{"key": "value", "count": 42}'), "json")
        self.assertEqual(sentinel.classify_snippet("def add(a, b):\n    return a + b"), "python")
        self.assertEqual(sentinel.classify_snippet("https://github.com"), "url")

        # Test Explanation
        explain_tb = sentinel.explain_snippet("Traceback (most recent call last):\nKeyError: 'user_id'")
        self.assertTrue(explain_tb.get("ok"))
        self.assertEqual(explain_tb.get("type"), "traceback")
        self.assertEqual(explain_tb.get("error_name"), "KeyError")

        # Test Format JSON
        format_res = sentinel.format_json_clip('{"name":"Prime","status":"active"}')
        self.assertTrue(format_res.get("ok"))

    # =========================================================================
    # 24. Autonomous Git Sentinel & Pre-Commit Quality Gate
    # =========================================================================
    def test_45_git_sentinel_pre_commit_audit(self):
        """Feature 45: Pre-commit syntax, secret, and conflict checks."""
        sentinel = git_sentinel.get_git_sentinel()

        audit = sentinel.audit_pre_commit()
        self.assertTrue(audit.get("ok"))
        self.assertIsInstance(audit.get("passed"), bool)

        # Test Smart Commit Message generator
        msg = sentinel.generate_smart_commit_message(["core/test_module.py", "tests/test_feature.py"])
        self.assertIn("feat:", msg)

        # Test PR summary generator
        pr = sentinel.generate_pr_summary(base_branch="main")
        self.assertTrue(pr.get("ok"))
        self.assertIn("Pull Request", pr.get("summary_markdown", ""))

    # =========================================================================
    # 25. Autonomous Standup & Evening Debrief Engine
    # =========================================================================
    def test_46_standup_and_debrief_engine(self):
        """Feature 46: Morning standup voice synthesis and evening wrap-up debriefs."""
        # Morning Standup
        standup = standup_engine.generate_morning_standup()
        self.assertTrue(standup.get("ok"))
        self.assertIn("Good morning Sir!", standup.get("speech_script", ""))
        self.assertIn("standup", standup)

        # Evening Debrief
        debrief = standup_engine.generate_evening_debrief()
        self.assertTrue(debrief.get("ok"))
        self.assertIn("Good evening Sir!", debrief.get("speech_script", ""))
        self.assertIn("debrief", debrief)

    # =========================================================================
    # 26. Smart Hardware Thermal & Battery Power Guardian
    # =========================================================================
    def test_47_thermal_guard_audit_and_power_profile(self):
        """Feature 47: System hardware telemetry audit and power profile switching."""
        guard = thermal_guard.get_thermal_guard()

        # Audit
        audit = guard.get_health_audit()
        self.assertTrue(audit.get("ok"))
        self.assertIn(audit.get("status"), ["OPTIMAL", "WARNING", "CRITICAL"])
        self.assertIn("metrics", audit)

        # Power profile switching
        eco_res = guard.set_power_profile("eco")
        self.assertTrue(eco_res.get("ok"))
        self.assertEqual(eco_res.get("profile"), "eco")

        bal_res = guard.set_power_profile("balanced")
        self.assertTrue(bal_res.get("ok"))
        self.assertEqual(bal_res.get("profile"), "balanced")

    # =========================================================================
    # 27. Tool Dispatch Integration for All 5 New Upgrades
    # =========================================================================
    def test_48_upgrades_tools_dispatch_integration(self):
        """Feature 48: Verification of execute_tool dispatch for all 5 new modules."""
        # 1. DND
        dnd_on = execute_tool("enableDNDMode", {"reason": "Test Session"})
        self.assertTrue(dnd_on.get("ok"))
        dnd_off = execute_tool("disableDNDMode", {})
        self.assertTrue(dnd_off.get("ok"))

        # 2. Call logs
        call_logs = execute_tool("getWhatsAppCallLogs", {"limit": 3})
        self.assertTrue(call_logs.get("ok"))

        # 3. Clipboard tools
        clip_explain = execute_tool("explainClipboardSnippet", {"text": "def compute(): pass"})
        self.assertTrue(clip_explain.get("ok"))

        # 4. Git Sentinel
        git_audit = execute_tool("gitPreCommitAudit", {})
        self.assertTrue(git_audit.get("ok"))

        # 5. Standup & Debrief
        m_standup = execute_tool("generateMorningStandup", {})
        self.assertTrue(m_standup.get("ok"))
        e_debrief = execute_tool("generateEveningDebrief", {})
        self.assertTrue(e_debrief.get("ok"))

        # 6. Thermal Guard
        health = execute_tool("getHardwareHealthAudit", {})
        self.assertTrue(health.get("ok"))
        prof = execute_tool("setPowerProfile", {"profile": "performance"})
        self.assertTrue(prof.get("ok"))


if __name__ == "__main__":
    unittest.main()


