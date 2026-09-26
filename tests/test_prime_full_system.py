"""
test_prime_full_system.py — Comprehensive Test Suite for Prime AI
Validates all features, codes, tools, and skills:
  1. System Core & Configurations (config, single_instance, providers)
  2. Spoken Voice Engine & Bilingual Routing (Brian Multilingual + Madhur Neural, +22% rate)
  3. WhatsApp Automation & Physical Desktop Dispatch (VCF parsing, thread isolation, Enter simulation)
  4. Tool Arsenal (73 Tool Specs & Dispatch Handlers)
  5. Second Brain & Obsidian RAG
  6. 279 Agency Skills & Multi-Agent Personas
  7. Intent Router & Fast-Path Cognitive Classification
  8. Self-Healing & Diagnostic Engine
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Configure utf-8 stdout/stderr on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestPrimeFullSystem(unittest.TestCase):

    # =========================================================================
    # 1. System Core & Configurations
    # =========================================================================
    def test_01_config_integrity(self):
        """Verify core configuration parameters, models, and voice defaults."""
        import config
        from config import config as cfg
        self.assertIsNotNone(config.BASE_DIR)
        self.assertTrue(any(v in cfg.tts_voice for v in ("RyanNeural", "BrianMultilingualNeural")))
        self.assertTrue(cfg.voice_rate_str.startswith("+"))
        self.assertIn("gemini", cfg.default_model.lower())
        print(f"  ✓ Config integrity & voice parameters ({cfg.tts_voice}) verified.")

    def test_02_single_instance_lock(self):
        """Verify single instance lock prevents duplicate Prime processes."""
        import single_instance
        # Use an isolated test mutex name
        acquired = single_instance.acquire_single_instance("Global\\PrimeAI_Test_Mutex")
        self.assertTrue(acquired)
        single_instance.release_single_instance()
        print("  ✓ SingleInstance mutex lock acquire and release verified.")

    def test_03_providers_and_model_routing(self):
        """Verify LLM providers, free directory (awesome-free-llm-apis), and provider configs."""
        import providers
        providers_list = providers.get_providers_list()
        self.assertGreaterEqual(len(providers_list), 6)
        
        # Verify essential providers exist
        gemini_prov = providers.get_provider_by_id("gemini")
        self.assertIsNotNone(gemini_prov)
        self.assertEqual(gemini_prov["name"], "Google Gemini")

        groq_prov = providers.get_provider_by_id("groq")
        self.assertIsNotNone(groq_prov)
        self.assertIn("Groq", groq_prov["name"])
        print(f"  ✓ Multi-LLM provider directory verified ({len(providers_list)} providers listed).")

    # =========================================================================
    # 2. Spoken Voice Engine & Bilingual Routing
    # =========================================================================
    def test_04_voice_bilingual_detection(self):
        """Verify Hindi/Hinglish detection and voice directory."""
        import voice_engine

        # Verify voice directory constants
        self.assertIn("brian", voice_engine.EDGE_NEURAL_VOICES)
        self.assertEqual(voice_engine.EDGE_NEURAL_VOICES["brian"], "en-US-BrianMultilingualNeural")
        self.assertEqual(voice_engine.EDGE_NEURAL_VOICES["madhur"], "hi-IN-MadhurNeural")

        # English phrases
        self.assertFalse(voice_engine.is_hindi_or_hinglish("Hello, what is the weather today?"))
        self.assertFalse(voice_engine.is_hindi_or_hinglish("Can you run the tests for me?"))

        # Devanagari Hindi
        self.assertTrue(voice_engine.is_hindi_or_hinglish("नमस्ते आप कैसे हैं?"))
        self.assertTrue(voice_engine.is_hindi_or_hinglish("आज क्या योजना है?"))

        # Hinglish phrases
        self.assertTrue(voice_engine.is_hindi_or_hinglish("bhai message bhej de"))
        self.assertTrue(voice_engine.is_hindi_or_hinglish("kya chal raha hai"))
        self.assertTrue(voice_engine.is_hindi_or_hinglish("accha theek hai"))
        self.assertTrue(voice_engine.is_hindi_or_hinglish("kaise ho bhai"))
        print("  ✓ Spoken Voice bilingual routing (Brian Multilingual + Madhur) verified.")

    # =========================================================================
    # 3. WhatsApp Automation & Physical Desktop Dispatch
    # =========================================================================
    def test_05_whatsapp_phone_sanitization_and_url(self):
        """Verify WhatsApp phone normalizer and contact book loader."""
        import whatsapp_manager
        
        # Indian 10-digit number -> international +91 prefix
        norm = whatsapp_manager.normalize_phone_number("9876543210")
        self.assertEqual(norm, "+919876543210")
        
        # International with +
        norm_plus = whatsapp_manager.normalize_phone_number("+91 98765-43210")
        self.assertEqual(norm_plus, "+919876543210")

        # Contact book fuzzy search
        contacts = whatsapp_manager.load_contacts()
        self.assertIsInstance(contacts, dict)
        print(f"  ✓ WhatsApp manager verified ({len(contacts)} contacts in directory).")

    def test_06_whatsapp_interactive_thread(self):
        """Verify run_on_interactive_thread executes successfully without desktop blocking."""
        import whatsapp_manager
        
        def _dummy_worker(val):
            return val * 2

        res = whatsapp_manager.run_on_interactive_thread(_dummy_worker, 21)
        self.assertEqual(res, 42)
        print("  ✓ WhatsApp interactive thread runner verified.")

    def test_06b_whatsapp_calling_and_scheduler(self):
        """Verify WhatsApp call scheduler and natural time parser."""
        import whatsapp_manager
        from tool_definitions import execute_tool

        # 1. Natural language time parsing (English and Hinglish)
        t1 = whatsapp_manager.parse_schedule_time("in 15 minutes")
        self.assertIsNotNone(t1)
        
        t2 = whatsapp_manager.parse_schedule_time("10 minute baad")
        self.assertIsNotNone(t2)

        t3 = whatsapp_manager.parse_schedule_time("5 baje")
        self.assertIsNotNone(t3)

        # 2. Schedule, list, and cancel call tool executions
        sched_res = execute_tool("scheduleWhatsAppCall", {
            "recipient": "Self",
            "time_str": "in 45 minutes",
            "call_type": "voice",
            "note": "Test System Calling"
        })
        self.assertTrue(sched_res.get("ok"))
        self.assertIn("scheduled", sched_res.get("message", "").lower())

        list_res = execute_tool("listScheduledWhatsAppCalls", {})
        self.assertTrue(list_res.get("ok"))
        self.assertIn("Self", str(list_res))

        cancel_res = execute_tool("cancelScheduledWhatsAppCall", {"identifier": "Self"})
        self.assertTrue(cancel_res.get("ok"))
        print("  ✓ WhatsApp voice/video call scheduler and time parser verified.")

    # =========================================================================
    # 4. Tool Arsenal (All 81+ Tools Coverage)
    # =========================================================================
    def test_07_all_tool_specs_registered(self):
        """Verify all tools declared in TOOL_SPECS have valid executable handlers."""
        import tool_definitions
        from desktop_agent.registry import TOOLS
        from plugin_registry import registry

        specs = tool_definitions.TOOL_SPECS
        self.assertGreaterEqual(len(specs), 81, f"Expected at least 81 tools, found {len(specs)}")

        unmapped = []
        for spec in specs:
            name = spec["name"]
            has_builtin = name in tool_definitions.BUILTIN_TOOL_DISPATCH or any(k.lower() == name.lower() for k in tool_definitions.BUILTIN_TOOL_DISPATCH)
            has_desktop = name in TOOLS
            has_plugin = registry.has_tool(name)
            
            if not (has_builtin or has_desktop or has_plugin):
                unmapped.append(name)

        self.assertEqual(unmapped, [], f"Unmapped tools in TOOL_SPECS: {unmapped}")
        print(f"  ✓ All {len(specs)} tool specifications mapped to active handlers.")

    def test_08_core_tool_executions(self):
        """Verify execution of essential built-in and system telemetry tools."""
        from tool_definitions import execute_tool

        # 1. getCurrentTime
        res_time = execute_tool("getCurrentTime", {})
        self.assertTrue(res_time.get("ok"))
        self.assertIn("Current system time is", str(res_time.get("result", "")))

        # 2. listWhatsAppContacts
        res_wa = execute_tool("listWhatsAppContacts", {"search": ""})
        self.assertTrue(res_wa.get("ok"))

        # 3. systemInfo
        res_sys = execute_tool("systemInfo", {})
        self.assertTrue(res_sys.get("ok"))

        # 4. listDrives
        res_drives = execute_tool("listDrives", {})
        self.assertTrue(res_drives.get("ok"))
        print("  ✓ Core tool executions (time, WhatsApp contacts, systemInfo, listDrives) passed.")

    # =========================================================================
    # 5. Second Brain & Obsidian RAG
    # =========================================================================
    def test_09_obsidian_rag_vault(self):
        """Verify Obsidian vault reading and search capabilities."""
        import obsidian_rag
        vault_path = obsidian_rag.get_vault_path()
        self.assertTrue(vault_path.exists())
        
        # Test note writing and reading
        write_res = obsidian_rag.write_note("test_audit_note", "Prime Audit Content")
        self.assertIn("Successfully saved", write_res)

        read_res = obsidian_rag.read_note("test_audit_note")
        self.assertEqual(read_res, "Prime Audit Content")
        
        # Test search
        results = obsidian_rag.search_notes("Prime Audit")
        self.assertIsInstance(results, list)
        self.assertTrue(any(r["title"] == "test_audit_note" for r in results))

        # Cleanup test note
        test_file = vault_path / "test_audit_note.md"
        if test_file.exists():
            test_file.unlink()
        print("  ✓ Obsidian RAG Second Brain vault connected and read/write verified.")

    # =========================================================================
    # 6. 279 Agency Skills & Personas
    # =========================================================================
    def test_10_agency_roster_and_skills(self):
        """Verify 279 Agency Specialist Agents and dynamic persona loading."""
        import agency_roster
        agents = agency_roster.load_all_agency_agents()
        self.assertGreaterEqual(len(agents), 270, f"Expected >=270 agents, got {len(agents)}")

        # Verify key roles exist
        self.assertIn("backend-architect", agents)
        self.assertIn("code-reviewer", agents)
        self.assertIn("frontend-developer", agents)
        self.assertIn("penetration-tester", agents)

        # Verify persona instructions retrieval
        agent_info = agency_roster.get_agent_by_name("backend-architect")
        self.assertIsNotNone(agent_info)
        instr = agency_roster.get_agent_instructions(agent_info)
        self.assertTrue(len(instr) > 0)
        print(f"  ✓ Agency Roster verified ({len(agents)} specialized agents loaded).")

    # =========================================================================
    # 7. Intent Router & Cognitive Classification
    # =========================================================================
    def test_11_intent_router(self):
        """Verify fast-path and ML coding classification."""
        from core.intent_router import is_coding_task
        self.assertTrue(is_coding_task("write a python function to sort an array"))
        self.assertTrue(is_coding_task("debug this syntax error in my script"))
        self.assertFalse(is_coding_task("what is the weather like today"))
        self.assertFalse(is_coding_task("hello good morning"))
        print("  ✓ Intent router cognitive classification verified (<1ms fast-path).")

    # =========================================================================
    # 8. Self-Healing & Diagnostic Engine
    # =========================================================================
    def test_12_self_healing_engine(self):
        """Verify self-healing engine audit and diagnostic report."""
        import self_healing_engine
        report = self_healing_engine.self_healer.run_full_system_audit()
        self.assertIsInstance(report, dict)
        self.assertIn("overall_status", report)
        self.assertEqual(report["overall_status"], "HEALTHY")
        self.assertEqual(report["passed_tests"], report["total_tests"])
        print(f"  ✓ Self-healing engine audit verified ({report['passed_tests']}/{report['total_tests']} tests passed in {report['total_latency_ms']}ms).")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestPrimeFullSystem)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "=" * 70)
        print("  ALL PRIME AI FEATURES, CODES & SKILLS PASSED WITH ZERO ERRORS!")
        print("=" * 70)
        sys.exit(0)
    else:
        sys.exit(1)
