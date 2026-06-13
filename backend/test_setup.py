import os
from dotenv import load_dotenv
import anthropic
import httpx
import sys

load_dotenv()

print("API Keys:")
print("ANTHROPIC_API_KEY is present:", bool(os.getenv("ANTHROPIC_API_KEY")))

try:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=100,
        messages=[
            {"role": "user", "content": "Diga OK em uma palavra."}
        ]
    )
    print("Anthropic Response:", message.content[0].text)
except Exception as e:
    print("Anthropic Error:", str(e))

try:
    from mining_tools import _ddg_search
    results = _ddg_search("vaso wabi sabi aliexpress", max_results=2)
    print("DDG Results count:", len(results))
    print("First result:", results[0] if results else "None")
except Exception as e:
    print("DDG Error:", str(e))
