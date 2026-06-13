import os
import requests
import json
import sys
import time
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

sys.stdout.reconfigure(encoding='utf-8')

# Load .env
env_path = r"C:\Users\erick\aura-office-dashboard\backend\.env"
env_vars = {}
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env_vars[k.strip()] = v.strip().strip("'\"")

token = env_vars.get("SHOPIFY_ADMIN_TOKEN")
domain = env_vars.get("SHOPIFY_DOMAIN")
live_theme_id = env_vars.get("SHOPIFY_LIVE_THEME_ID")
staging_theme_id = env_vars.get("SHOPIFY_STAGING_THEME_ID")

print(f"Checking assets for Shopify store: {domain}")
print(f"Live theme ID: {live_theme_id}")
print(f"Staging theme ID: {staging_theme_id}")

def check_asset(theme_id, asset_key):
    if not token or not domain or not theme_id:
        print(f"Missing config for theme {theme_id}")
        return False
    url = f"https://{domain}/admin/api/2025-01/themes/{theme_id}/assets.json"
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }
    
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    for attempt in range(3):
        try:
            r = session.get(url, headers=headers, params={"asset[key]": asset_key}, timeout=15)
            if r.status_code == 200:
                print(f"[FOUND] Asset '{asset_key}' EXISTS in theme {theme_id}!")
                return True
            elif r.status_code == 404:
                print(f"[MISSING] Asset '{asset_key}' is MISSING in theme {theme_id}!")
                return False
            else:
                print(f"[ERROR] {r.status_code} checking theme {theme_id}: {r.text}")
                return False
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"[RETRY] Connection issue: {e}. Retrying {attempt+1}/3...")
            time.sleep(2)
        except Exception as e:
            print(f"[EXCEPTION] checking theme {theme_id}: {e}")
            return False
    return False

print("\n--- Live Theme Check ---")
check_asset(live_theme_id, "snippets/YampiSnippet.liquid")
check_asset(live_theme_id, "layout/theme.liquid")

print("\n--- Staging Theme Check ---")
check_asset(staging_theme_id, "snippets/YampiSnippet.liquid")
check_asset(staging_theme_id, "layout/theme.liquid")
