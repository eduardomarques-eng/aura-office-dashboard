import os
import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

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
staging_theme_id = env_vars.get("SHOPIFY_STAGING_THEME_ID")

url = f"https://{domain}/admin/api/2025-01/themes/{staging_theme_id}/assets.json"
headers = {
    "X-Shopify-Access-Token": token,
    "Content-Type": "application/json"
}

r = requests.get(url, headers=headers, params={"asset[key]": "layout/theme.liquid"})
if r.status_code == 200:
    data = r.json()
    value = data.get("asset", {}).get("value", "")
    print("Fetched layout/theme.liquid from Staging Theme.")
    # Print the last 15 lines of theme.liquid
    lines = value.split("\n")
    print(f"Total lines: {len(lines)}")
    print("Last 15 lines of Staging theme's layout/theme.liquid:")
    for l in lines[-15:]:
        print(l)
else:
    print(f"Error fetching layout/theme.liquid: {r.status_code} - {r.text}")
