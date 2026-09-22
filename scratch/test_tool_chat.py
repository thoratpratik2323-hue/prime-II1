import os
import sys
sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv
load_dotenv()
from google import genai
from google.genai import types
from tool_definitions import get_gemini_tools

key = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=key)

try:
    chat = client.chats.create(
        model="gemini-flash-lite-latest",
        config=types.GenerateContentConfig(
            system_instruction="You are Prime AI. When user says open application or website, call the tool.",
            tools=get_gemini_tools(),
            temperature=0.3,
        ),
    )
    resp = chat.send_message("Open Chrome")
    print("Function calls:", resp.function_calls)
    print("Text:", getattr(resp, 'text', ''))
except Exception as e:
    print("Error:", type(e).__name__, e)
