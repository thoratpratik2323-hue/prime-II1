import os
import sys
sys.path.insert(0, os.path.abspath("."))

from dotenv import load_dotenv
load_dotenv()

from tool_definitions import execute_tool
from ai_agent import AIAgent

print("=== 1. Testing execute_tool openApplication('chrome') ===")
r1 = execute_tool("openApplication", {"name": "chrome"})
print("r1 (chrome):", r1)
assert r1["ok"] is True, f"Failed: {r1}"

print("\n=== 2. Testing execute_tool openApplication('youtube') (Routing to website) ===")
r2 = execute_tool("openApplication", {"name": "youtube"})
print("r2 (youtube via openApplication):", r2)
assert r2["ok"] is True, f"Failed: {r2}"

print("\n=== 3. Testing execute_tool openWebsite('calculator') (Routing to app) ===")
r3 = execute_tool("openWebsite", {"name": "calculator"})
print("r3 (calculator via openWebsite):", r3)
assert r3["ok"] is True, f"Failed: {r3}"

print("\n=== 4. Testing AI Agent with Gemini Brain ===")
agent = AIAgent()
print("Active Gemini Model:", getattr(agent, "_current_gemini_model", None))

tool_called = []
def mock_on_tool_call(name, args):
    tool_called.append((name, args))
    print(f"  [TOOL CALLED]: {name} with args {args}")

def mock_on_tool_result(name, res):
    print(f"  [TOOL RESULT]: {name} -> {res}")

res = agent.process_message("open chrome", on_tool_call=mock_on_tool_call, on_tool_result=mock_on_tool_result)
print("Agent response to 'open chrome':", res)
assert any(t[0] == "openApplication" for t in tool_called), "Tool openApplication was not called!"

print("\n=== 5. Testing AI Agent Local Fallback with Hinglish ===")
tool_called.clear()
fb_res1 = agent._process_local_fallback("chrome open karo", mock_on_tool_call, mock_on_tool_result)
print("Fallback response to 'chrome open karo':", fb_res1)

tool_called.clear()
fb_res2 = agent._process_local_fallback("app open karo notepad", mock_on_tool_call, mock_on_tool_result)
print("Fallback response to 'app open karo notepad':", fb_res2)

tool_called.clear()
fb_res3 = agent._process_local_fallback("open youtube", mock_on_tool_call, mock_on_tool_result)
print("Fallback response to 'open youtube':", fb_res3)

print("\n=== ALL APP/WEBSITE OPENING TESTS PASSED! ===")
