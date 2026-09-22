import os
import sys
import traceback
sys.path.insert(0, os.path.abspath("."))

from dotenv import load_dotenv
load_dotenv()

results = {}

def run_test(name, fn):
    try:
        fn()
        results[name] = ("PASS", "OK")
        print(f"  [PASS] {name}")
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        results[name] = ("FAIL", err)
        print(f"  [FAIL] {name} -> {err}")

print("============================================================")
print("       PRIME AI — COMPREHENSIVE END-TO-END AUDIT           ")
print("============================================================")

# 1. Configuration & Platform
def test_config():
    from config import config, is_windows, get_os
    assert is_windows() is True
    assert get_os() == "windows"
    prov = config.get_active_provider()
    assert prov in ("gemini", "groq", "openai", "none")
    model = config.get_default_model(prov)
    assert bool(model)

run_test("1. Config & Platform Environment", test_config)

# 2. Voice Engine & Mark-LIV Voices
def test_voice():
    from voice_engine import voice, MARK_LIV_GEMINI_VOICES
    assert voice is not None
    assert "Charon" in MARK_LIV_GEMINI_VOICES.values()
    # Test TTS sanitization
    clean = voice._sanitize_for_tts("Hello **boss**, checking [code](url) & <tag>")
    assert "**" not in clean and "<tag>" not in clean

run_test("2. Voice Engine & Mark-LIV Synthesizer", test_voice)

# 3. AI Brain (Gemini Active Client & Function Calling)
def test_ai_brain():
    from ai_agent import AIAgent
    agent = AIAgent()
    assert agent._gemini_client is not None
    assert getattr(agent, "_current_gemini_model", None) is not None
    # Quick live generation
    resp = agent._gemini_chat.send_message("Say 1 in word")
    assert resp and len(resp.text or "") > 0

run_test("3. AI Brain (Gemini Real-time Inference)", test_ai_brain)

# 4. Tool Execution: System Info
def test_system_info():
    from tool_definitions import execute_tool
    res = execute_tool("systemInfo", {})
    assert res.get("ok") is True
    assert "CPU" in str(res) or "RAM" in str(res) or "System" in str(res)

run_test("4. Desktop Telemetry (systemInfo)", test_system_info)

# 5. Tool Execution: Browser-First Web Apps
def test_browser_apps():
    from tool_definitions import execute_tool
    res1 = execute_tool("openApplication", {"name": "whatsapp"})
    assert res1.get("ok") is True and "whatsapp.com" in str(res1)
    res2 = execute_tool("openApplication", {"name": "youtube"})
    assert res2.get("ok") is True and "youtube.com" in str(res2)
    res3 = execute_tool("openWebsite", {"url": "spotify"})
    assert res3.get("ok") is True and "spotify.com" in str(res3)

run_test("5. Browser-First Web Apps Routing", test_browser_apps)

# 6. Tool Execution: Volume & Media Controls
def test_media_volume():
    from tool_definitions import execute_tool
    res_vol = execute_tool("volumeUp", {"amount": 5})
    assert res_vol.get("ok") is True
    res_mute = execute_tool("muteToggle", {})
    assert res_mute.get("ok") is True
    # toggle back
    execute_tool("muteToggle", {})

run_test("6. Volume & Media Controls", test_media_volume)

# 7. Tool Execution: Time & Weather
def test_time_weather():
    from tool_definitions import execute_tool
    t_res = execute_tool("getCurrentTime", {})
    assert t_res.get("ok") is True and "Current system time" in str(t_res)
    w_res = execute_tool("getWeather", {"city": "Pune"})
    assert w_res.get("ok") is True

run_test("7. Time & Meteorological Reports", test_time_weather)

# 8. Tool Execution: Morning Briefing
def test_morning_briefing():
    from tool_definitions import execute_tool
    res = execute_tool("morningBriefing", {"action": "briefing"})
    assert res.get("ok") is True

run_test("8. Morning Briefing Action", test_morning_briefing)

# 9. Claw Code Developer: Terminal Execution
def test_claw_terminal():
    import claw_developer
    res = claw_developer.run_terminal_command("echo PRIME_ONLINE")
    assert res.get("ok") is True
    assert "PRIME_ONLINE" in res.get("stdout", "")

run_test("9. Claw Code Terminal Execution", test_claw_terminal)

# 10. Claw Code Developer: File Patching
def test_claw_patching():
    import claw_developer
    test_file = "scratch/temp_patch_test.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("Line 1\nTarget Line to Replace\nLine 3\n")
    p_res = claw_developer.patch_file(test_file, "Target Line to Replace", "Replaced Successfully")
    assert p_res.get("ok") is True
    with open(test_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Replaced Successfully" in content
    if os.path.exists(test_file):
        os.remove(test_file)

run_test("10. Claw Code Surgical File Patcher", test_claw_patching)

# 11. Claw Code Developer: Git Automation
def test_claw_git():
    import claw_developer
    res = claw_developer.git_automate("status")
    assert res.get("ok") is True

run_test("11. Claw Code Git Automation", test_claw_git)

# 12. Claw Code Developer: Unit Test Runner
def test_claw_tests():
    import claw_developer
    res = claw_developer.run_unit_tests("pytest", path="tests/")
    assert isinstance(res, dict)

run_test("12. Claw Code Unit Test Runner", test_claw_tests)

# 13. Obsidian Knowledge Vault RAG
def test_obsidian():
    import obsidian_rag
    # write note
    w_res = obsidian_rag.write_note("audit_test", "# Audit Note\nPrime AI RAG test passed.")
    assert "Successfully saved" in w_res
    # read note
    r_res = obsidian_rag.read_note("audit_test")
    assert "Prime AI RAG test passed" in r_res
    # search note
    s_res = obsidian_rag.search_notes("Audit Note")
    assert len(s_res) > 0

run_test("13. Obsidian Knowledge Vault RAG", test_obsidian)

# 14. Project Exporter & Workspace Archiver
def test_project_exporter():
    import project_exporter
    res = project_exporter.export_project_starter("react_vite", destination_dir="scratch/exports")
    assert res.get("ok") is True
    zip_path = res.get("zip_path")
    assert os.path.exists(zip_path)

run_test("14. Project Starter Exporter", test_project_exporter)

# 15. Agency Specialists Roster (279 Personas)
def test_agency_roster():
    import agency_roster
    agents = agency_roster.get_all_agents()
    assert len(agents) >= 200
    p = agency_roster.get_agent_by_name("frontend-developer")
    assert p is not None
    instructions = agency_roster.get_agent_instructions(p)
    assert bool(instructions)

run_test("15. Agency Specialist Roster (279 Personas)", test_agency_roster)

# 16. Goal Tracking & Continual Learning
def test_goal_harness():
    from prime_goal_harness import goal_tracker, continual_harness
    g = goal_tracker.set_goal("Test Comprehensive Audit", subtasks=["Audit 1", "Audit 2"])
    assert g["objective"] == "Test Comprehensive Audit"
    goal_tracker.toggle_subtask(0)
    assert goal_tracker.get_active_goal()["progress_percent"] == 50.0
    l_res = continual_harness.record_lesson("Audit lesson", "All systems operational", context="Testing")
    assert isinstance(l_res.get("id"), int)

run_test("16. Goal Tracking & Continual Learning", test_goal_harness)

# 17. Hinglish Speech / Fallback Dispatcher
def test_hinglish_dispatch():
    from ai_agent import AIAgent
    agent = AIAgent()
    res1 = agent._process_local_fallback("chrome open karo", None, None)
    assert "Chrome" in res1 or "open" in res1.lower()
    res2 = agent._process_local_fallback("app open karo notepad", None, None)
    assert "Notepad" in res2 or "open" in res2.lower()
    res3 = agent._process_local_fallback("open youtube", None, None)
    assert "youtube" in res3.lower()

run_test("17. Hinglish Voice & Local Fallback Commands", test_hinglish_dispatch)

print("\n============================================================")
total_tests = len(results)
passed_tests = sum(1 for status, _ in results.values() if status == "PASS")
failed_tests = total_tests - passed_tests
print(f"  AUDIT SUMMARY: {passed_tests}/{total_tests} FEATURES OPERATIONAL ({passed_tests/total_tests*100:.1f}%)")
print("============================================================")

if failed_tests > 0:
    print("\nFailures:")
    for name, (status, detail) in results.items():
        if status == "FAIL":
            print(f"  - {name}: {detail}")
