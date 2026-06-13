import os, httpx
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GOOGLE_AI_KEY", "")
print(f"Testing Google AI key: {key[:8]}...")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
payload = {"contents": [{"parts": [{"text": "Diga OK em uma palavra."}]}]}

try:
    r = httpx.post(url, json=payload, timeout=10)
    print("Status Code:", r.status_code)
    print("Response:", r.text)
except Exception as e:
    print("Exception:", e)
