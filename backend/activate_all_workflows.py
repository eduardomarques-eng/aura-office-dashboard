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

base_url = "http://localhost:5678/api/v1"
headers = {"X-N8N-API-KEY": n8n_key}

print("Fetching workflows...")
try:
    r = requests.get(f"{base_url}/workflows", headers=headers)
    if r.status_code != 200:
        print(f"Failed to fetch workflows: HTTP {r.status_code} - {r.text}")
        sys.exit(1)
        
    workflows = r.json().get("data", [])
    print(f"Found {len(workflows)} workflows.")
    
    activated_count = 0
    already_active_count = 0
    failed_count = 0
    
    for wf in workflows:
        wf_id = wf.get("id")
        wf_name = wf.get("name")
        is_active = wf.get("active")
        
        if is_active:
            print(f"[SKIP] '{wf_name}' (ID: {wf_id}) is already active.")
            already_active_count += 1
            continue
            
        print(f"[ACTIVATE] Activating '{wf_name}' (ID: {wf_id})...")
        activate_url = f"{base_url}/workflows/{wf_id}/activate"
        
        try:
            ar = requests.post(activate_url, headers=headers)
            if ar.status_code == 200:
                print(f"  -> Successfully activated!")
                activated_count += 1
            else:
                print(f"  -> Failed: HTTP {ar.status_code} - {ar.text}")
                failed_count += 1
        except Exception as ae:
            print(f"  -> Error: {ae}")
            failed_count += 1
            
    print("\n--- Activation Summary ---")
    print(f"Already Active: {already_active_count}")
    print(f"Newly Activated: {activated_count}")
    print(f"Failed: {failed_count}")
    
except Exception as e:
    print(f"Error occurred: {e}")
