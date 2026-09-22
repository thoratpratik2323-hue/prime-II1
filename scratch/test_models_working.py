import os
import sys
sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv
load_dotenv()
from google import genai
from google.genai import types

key = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=key)

for m in ["gemini-flash-lite-latest", "gemini-3.1-flash-lite-preview", "gemini-3-flash-preview"]:
    try:
        chat = client.chats.create(
            model=m,
            config=types.GenerateContentConfig(
                system_instruction="You are Prime.",
                temperature=0.7,
            ),
        )
        resp = chat.send_message("Respond with OK")
        print(f"{m}: SUCCESS -> {resp.text.strip()}")
    except Exception as e:
        print(f"{m}: FAILED -> {e}")
