import os
import sys
sys.path.insert(0, os.path.abspath("."))

from dotenv import load_dotenv
load_dotenv()

from tool_definitions import execute_tool
from ai_agent import AIAgent

print("=== Testing apps opening in browser ===")

apps_to_test = [
    ("youtube", "https://www.youtube.com"),
    ("spotify", "https://open.spotify.com"),
    ("whatsapp", "https://web.whatsapp.com"),
    ("discord", "https://discord.com/app"),
    ("telegram", "https://web.telegram.org"),
    ("chatgpt", "https://chatgpt.com"),
    ("hotstar", "https://www.hotstar.com"),
]

for app_name, expected_url in apps_to_test:
    res = execute_tool("openApplication", {"name": app_name})
    print(f"openApplication('{app_name}'): ok={res.get('ok')}, result={res.get('result')}")
    assert res.get("ok") is True, f"Failed for {app_name}: {res}"
    assert expected_url in str(res), f"Expected {expected_url} in result for {app_name}: {res}"

print("\n=== Testing AI Agent tool calling for 'open spotify' ===")
agent = AIAgent()
tool_calls = []
def mock_call(name, args):
    tool_calls.append((name, args))
    print(f"  [TOOL CALLED]: {name}({args})")

def mock_res(name, r):
    print(f"  [TOOL RESULT]: {name} -> {r}")

agent_reply = agent.process_message("open whatsapp", on_tool_call=mock_call, on_tool_result=mock_res)
print("Agent reply for 'open whatsapp':", agent_reply)
assert any(t[0] in ("openWebsite", "openApplication") for t in tool_calls), "No tool was called for 'open whatsapp'!"

print("\n=== ALL APPS SUCCESSFULLY OPEN IN BROWSER! ===")
