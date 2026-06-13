import os, httpx, json
from dotenv import load_dotenv

load_dotenv()

DOMAIN = os.getenv("SHOPIFY_DOMAIN", "aura-decor-17.myshopify.com")
TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "")
THEME_ID = "160138428521"

print(f"Listing assets for theme {THEME_ID} on {DOMAIN}...")

url = f"https://{DOMAIN}/admin/api/2025-01/themes/{THEME_ID}/assets.json"
headers = {"X-Shopify-Access-Token": TOKEN}

try:
    r = httpx.get(url, headers=headers, timeout=20)
    print(f"Status Code: {r.status_code}")
    if r.status_code == 200:
        assets = r.json().get("assets", [])
        print(f"Total assets in theme: {len(assets)}")
        
        # Save asset keys to file
        keys = [a["key"] for a in assets]
        with open("backend/theme_assets_list.json", "w", encoding="utf-8") as f:
            json.dump(keys, f, indent=2)
        print("Saved keys to backend/theme_assets_list.json")
        
        # Print first 50 keys
        for k in sorted(keys)[:60]:
            print(f"  - {k}")
    else:
        print(f"Error response: {r.text}")
except Exception as e:
    print(f"Exception: {e}")
