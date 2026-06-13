import os
import requests
import sys

# Ensure UTF-8 output to handle special characters in workflow names on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Find env file path
env_path = os.path.join(os.path.dirname(__file__), ".env")

# Basic env file parser
env_vars = {}
try:
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip()
except Exception as e:
    print(f"Error loading .env file: {e}")
    sys.exit(1)

n8n_key = env_vars.get("N8N_API_KEY")
if not n8n_key:
    print("Error: N8N_API_KEY not found in .env file.")
    sys.exit(1)

# n8n default local endpoint
url = "http://localhost:5678/api/v1/workflows"
headers = {"X-N8N-API-KEY": n8n_key}

print("Loading API key from backend/.env...")
print(f"API Key prefix: {n8n_key[:15]}...")
print("\nFetching workflows from n8n...")

try:
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        workflows = data.get("data", [])
        print(f"\nSUCCESS! Found {len(workflows)} workflows:")
        print(f"{'ID':<30} | {'Name':<50} | {'Active'}")
        print("-" * 95)
        for wf in workflows:
            print(f"{wf.get('id'):<30} | {wf.get('name'):<50} | {wf.get('active')}")
    else:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error occurred: {e}")
