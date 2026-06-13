import os, requests, json
from dotenv import load_dotenv

load_dotenv()

DOMAIN = os.getenv("SHOPIFY_DOMAIN")
TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN")

headers = {
    'X-Shopify-Access-Token': TOKEN,
    'Content-Type': 'application/json'
}

print("=== DUPLICATING MAIN THEME ===")

# Get current main theme
r = requests.get(f'https://{DOMAIN}/admin/api/2025-01/themes.json', headers=headers)
if r.status_code != 200:
    print(f"Error fetching themes: {r.status_code} | {r.text}")
    exit(1)
    
themes = r.json().get('themes', [])
main_theme = None
for t in themes:
    if t['role'] == 'main':
        main_theme = t
        break

if not main_theme:
    print("Main theme not found.")
    exit(1)

print(f"Main theme found: {main_theme['name']} (ID: {main_theme['id']})")

# Create duplicate
payload = {
    "theme": {
        "name": "Backup-Antigravity",
        "role": "unpublished"
    }
}

# The Shopify API allows duplicating a theme by copying asset by asset or using a src, but the most reliable way 
# using the API is to create a new theme and then copy assets, or simply duplicating from the admin panel.
# Let's check if there is an endpoint to create a theme and import from an existing theme ID or URL.
# Under Shopify Admin API: POST /admin/api/2025-01/themes.json with src (URL of the theme JSON) duplicates it.
# Let's try duplicating using the src parameter.
payload["theme"]["src"] = f"https://{DOMAIN}/admin/api/2025-01/themes/{main_theme['id']}.json"

r2 = requests.post(f'https://{DOMAIN}/admin/api/2025-01/themes.json', headers=headers, json=payload)
if r2.status_code == 201:
    new_theme = r2.json().get('theme', {})
    print(f"SUCCESS! Created theme backup copy: '{new_theme['name']}' (ID: {new_theme['id']})")
else:
    print(f"Failed to duplicate theme using src: {r2.status_code} | {r2.text}")
    print("Attempting to create a new theme skeleton named 'Backup - Aura Decore'...")
    payload_fallback = {
        "theme": {
            "name": "Backup-Skeleton",
            "role": "unpublished"
        }
    }
    r3 = requests.post(f'https://{DOMAIN}/admin/api/2025-01/themes.json', headers=headers, json=payload_fallback)
    if r3.status_code == 201:
        print(f"SUCCESS! Created theme backup skeleton (ID: {r3.json()['theme']['id']})")
    else:
        print(f"Failed fallback: {r3.status_code} | {r3.text}")
