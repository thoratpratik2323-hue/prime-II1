import os
from dotenv import load_dotenv
load_dotenv()
from google import genai

key = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=key)

candidates = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
    "gemini-3.5-flash"
]

for model in candidates:
    try:
        res = client.models.generate_content(
            model=model,
            contents="hello"
        )
        print(f"SUCCESS: {model} -> {res.text.strip()}")
        break
    except Exception as e:
        print(f"FAILED: {model} -> {type(e).__name__}: {str(e)[:80]}")
