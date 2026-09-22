"""
Verification test script for OpenJarvis inherited superpowers in Prime AI.
Tests:
1. Ollama Provider configuration & model mappings.
2. Proactive Autonomous Operator sentinels & lifecycle.
3. Execution Trace logging & latency calculation.
4. Model Context Protocol (MCP) server bridge & configuration.
5. Tool definitions dispatch for operatorControl.
"""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def test_ollama_provider():
    print("\n[1] Testing Ollama / Local LLM Provider...")
    import providers
    p = providers.get_provider_by_id("ollama")
    assert p is not None, "Ollama provider not found in providers directory!"
    assert p["base_url"] == "http://localhost:11434/v1"
    assert p["default_model"] == "llama3.2:latest"

    from config import config
    model = config.get_default_model("ollama")
    assert model == "llama3.2:latest"
    print("  ✓ Ollama provider registered with endpoint http://localhost:11434/v1 and default model llama3.2:latest")

def test_proactive_operator():
    print("\n[2] Testing Proactive Autonomous Background Operator...")
    from prime_operator import operator
    status = operator.get_status()
    assert "enabled" in status
    assert "ram_percent" in status
    assert "sentinels" in status
    assert len(status["sentinels"]) == 4
    print(f"  ✓ Proactive Operator active! Sentinels ({len(status['sentinels'])}): {status['sentinels']}")
    print(f"  ✓ Host RAM monitored: {status['ram_percent']}%, Battery: {status['battery']}")

def test_trace_logging():
    print("\n[3] Testing Trace-Based Execution & Reflection Logging...")
    from prime_traces import trace_logger
    t = trace_logger.start_trace("Prime what is the current time")
    assert t["user_input"] == "Prime what is the current time"
    assert "trace_id" in t
    
    trace_logger.record_tool_call(t, "getCurrentTime", {}, {"ok": True, "result": "2026-09-21 11:42:00"})
    assert len(t["tools_called"]) == 1

    ended = trace_logger.end_trace(t, response="The current time is 11:42 AM.")
    assert ended["status"] == "success"
    assert ended["duration_ms"] >= 0.0

    recent = trace_logger.get_recent_traces(limit=1)
    assert len(recent) > 0
    assert recent[0]["trace_id"] == t["trace_id"]
    print(f"  ✓ Trace successfully recorded: ID={t['trace_id']}, Latency={ended['duration_ms']}ms, Tools={len(t['tools_called'])}")

def test_mcp_bridge():
    print("\n[4] Testing Model Context Protocol (MCP) Bridge...")
    from mcp_bridge import mcp_bridge
    servers = mcp_bridge.get_server_list()
    assert len(servers) >= 3
    names = [s["name"] for s in servers]
    assert "filesystem" in names
    assert "github" in names
    assert "brave-search" in names
    print(f"  ✓ MCP bridge initialized with {len(servers)} default server templates: {names}")

def test_tool_dispatch():
    print("\n[5] Testing operatorControl Tool Dispatch...")
    from tool_definitions import execute_tool
    res = execute_tool("operatorControl", {"action": "status"})
    assert res.get("ok") is True
    assert "Operator running" in str(res.get("result"))
    print(f"  ✓ Tool operatorControl executed successfully: {res.get('result')}")

if __name__ == "__main__":
    print("=" * 65)
    print("TESTING OPENJARVIS ARCHITECTURE INHERITANCE IN PRIME AI")
    print("=" * 65)
    test_ollama_provider()
    test_proactive_operator()
    test_trace_logging()
    test_mcp_bridge()
    test_tool_dispatch()
    print("=" * 65)
    print("ALL 5 SUPERPOWERS VERIFIED AND 100% OPERATIONAL! 🚀")
    print("=" * 65)
