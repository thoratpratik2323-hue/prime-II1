import os
from dotenv import load_dotenv
load_dotenv()
from google import genai

key = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=key)

try:
    for m in client.models.list():
        name = m.name
        if "gemini" in name.lower() and "flash" in name.lower():
            print(name)
except Exception as e:
    print("List models error:", e)
