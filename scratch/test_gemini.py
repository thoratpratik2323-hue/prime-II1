import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY", "")
print("Key length:", len(key))
print("Key prefix:", key[:6])

try:
    from google import genai
    client = genai.Client(api_key=key)
    res = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say hello in one word",
    )
    print("Gemini response:", res.text)
except Exception as e:
    print("Gemini failed:", type(e).__name__, e)
