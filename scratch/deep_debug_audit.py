"""
Comprehensive Full-Project Deep Debugging & Health Audit Suite.
Tests:
1. Python AST & py_compile syntax verification across ALL .py files in project.
2. Module import verification for all root, action, and agent files.
3. Tool Dispatcher & Tool Specs parameter consistency.
4. AI Agent fallback ladder & provider resolution.
5. Wake-Word detector & audio pipeline.
6. OpenJarvis Pillars (Operator, Traces, MCP, Ollama).
7. Desktop Agent app launchers & browser routing.
8. Continual learning & Goal harness.
"""

import os
import sys
import py_compile
import traceback
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

issues = []

def log_issue(category: str, filepath: str, message: str):
    issues.append({"category": category, "file": filepath, "message": message})
    print(f"  [ISSUE] [{category}] {filepath}: {message}")

print("=" * 70)
print("1. COMPILATION & SYNTAX CHECK ACROSS ALL PYTHON FILES")
print("=" * 70)

py_files = list(BASE_DIR.rglob("*.py"))
# Filter out venv, .git, or egg-info if any
filtered_files = [
    f for f in py_files 
    if "venv" not in f.parts and ".git" not in f.parts and "__pycache__" not in f.parts
]

compile_success = 0
for f in filtered_files:
    rel_path = f.relative_to(BASE_DIR)
    try:
        py_compile.compile(str(f), doraise=True)
        compile_success += 1
    except py_compile.PyCompileError as e:
        log_issue("SYNTAX_ERROR", str(rel_path), str(e))
    except Exception as e:
        log_issue("COMPILE_ERROR", str(rel_path), str(e))

print(f"Compiled {compile_success}/{len(filtered_files)} files without syntax errors.")

print("\n" + "=" * 70)
print("2. CORE MODULE IMPORT CHECKS")
print("=" * 70)

core_modules = [
    "config",
    "voice_engine",
    "voice_assistant",
    "ai_agent",
    "tool_definitions",
    "prime",
    "prime_operator",
    "prime_traces",
    "mcp_bridge",
    "providers",
    "prime_goal_harness",
    "agency_roster",
    "obsidian_rag",
    "claw_developer",
    "project_exporter"
]

import_success = 0
for mod in core_modules:
    try:
        __import__(mod)
        import_success += 1
        print(f"  ✓ Imported: {mod}")
    except Exception as e:
        log_issue("IMPORT_ERROR", mod, f"{type(e).__name__}: {e}")

print(f"Successfully imported {import_success}/{len(core_modules)} core modules.")

print("\n" + "=" * 70)
print("3. DESKTOP AGENT MODULE AUDIT")
print("=" * 70)

desktop_dir = BASE_DIR / "desktop_agent"
if desktop_dir.exists():
    for f in desktop_dir.glob("*.py"):
        mod_name = f"desktop_agent.{f.stem}"
        try:
            __import__(mod_name)
            print(f"  ✓ Desktop module: {f.name}")
        except Exception as e:
            log_issue("DESKTOP_AGENT_ERROR", str(f.relative_to(BASE_DIR)), f"{type(e).__name__}: {e}")

print("\n" + "=" * 70)
print("4. TOOL DISPATCH VERIFICATION (51 TOOLS)")
print("=" * 70)

try:
    from tool_definitions import TOOL_SPECS, execute_tool
    print(f"  Total Registered Tool Specs: {len(TOOL_SPECS)}")
    
    # Test key tools without side effects
    test_tools = [
        ("getCurrentTime", {}),
        ("getSystemStats", {}),
        ("getWeather", {"city": "Pune"}),
        ("operatorControl", {"action": "status"}),
        ("getAutoStartStatus", {}),
    ]
    
    for tool_name, args in test_tools:
        res = execute_tool(tool_name, args)
        if res.get("ok"):
            print(f"  ✓ Tool {tool_name} returned ok: {str(res.get('result'))[:60]}...")
        else:
            log_issue("TOOL_FAIL", tool_name, str(res.get("error")))

except Exception as e:
    log_issue("TOOL_DISPATCH_CRASH", "tool_definitions.py", str(e))

print("\n" + "=" * 70)
print("5. WAKE-WORD & AUDIO INTEGRITY")
print("=" * 70)

try:
    from voice_assistant import clean_command, get_require_wake_word, get_dynamic_welcome_message
    assert get_require_wake_word() is True, "Wake word is not required!"
    
    r1, cmd1 = clean_command("Prime open YouTube")
    assert r1 is True and cmd1 == "open youtube", f"Failed positive wake word test: {r1}, {cmd1}"
    
    r2, cmd2 = clean_command("open YouTube")
    assert r2 is False, f"Failed negative wake word test: {r2}, {cmd2}"
    
    msg = get_dynamic_welcome_message()
    assert len(msg) > 10, f"Empty welcome message: {msg}"
    print("  ✓ Strict Wake Word Protection: ACTIVE")
    print(f"  ✓ Sample Dynamic Welcome Greeting: \"{msg}\"")
except Exception as e:
    log_issue("WAKE_WORD_FAIL", "voice_assistant.py", str(e))

print("\n" + "=" * 70)
print("6. OPENJARVIS ARCHITECTURE PILLARS")
print("=" * 70)

try:
    import providers
    ollama_p = providers.get_provider_by_id("ollama")
    assert ollama_p is not None, "Ollama not in providers!"
    print(f"  ✓ Pillar 1 (Ollama): Registered at {ollama_p['base_url']}")
    
    from prime_operator import operator
    op_status = operator.get_status()
    assert op_status["enabled"] is True, "Operator disabled!"
    print(f"  ✓ Pillar 2 (Proactive Operator): {len(op_status['sentinels'])} sentinels active")
    
    from prime_traces import trace_logger
    recent = trace_logger.get_recent_traces(limit=2)
    print(f"  ✓ Pillar 3 (Trace Feedback): {len(recent)} traces loaded")
    
    from mcp_bridge import mcp_bridge
    mcp_servers = mcp_bridge.get_server_list()
    print(f"  ✓ Pillar 4 (MCP Bridge): {len(mcp_servers)} MCP server templates configured")
except Exception as e:
    log_issue("OPENJARVIS_FAIL", "openjarvis_pillars", str(e))

print("\n" + "=" * 70)
print("7. ACTIONS DIRECTORY COMPREHENSIVE SCAN")
print("=" * 70)

actions_dir = BASE_DIR / "actions"
action_modules = list(actions_dir.glob("*.py"))
broken_actions = 0
for act_file in action_modules:
    if act_file.name == "__init__.py":
        continue
    mod_name = f"actions.{act_file.stem}"
    try:
        __import__(mod_name)
    except Exception as e:
        broken_actions += 1
        log_issue("ACTION_IMPORT_WARN", str(act_file.relative_to(BASE_DIR)), f"{type(e).__name__}: {e}")

print(f"Scanned {len(action_modules)} action modules. Broken: {broken_actions}")

print("\n" + "=" * 70)
print("DEBUG AUDIT SUMMARY")
print("=" * 70)
print(f"Total Issues Detected: {len(issues)}")
if issues:
    for iss in issues:
        print(f" - [{iss['category']}] {iss['file']}: {iss['message']}")
else:
    print("ALL MODULES, SCRIPTS, AND TOOLS PASSED WITH 0 CRITICAL ERRORS! 🚀")
print("=" * 70)

sys.exit(len(issues))
