import os, requests, json, time, sys
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

load_dotenv()

DOMAIN = os.getenv("SHOPIFY_DOMAIN")
TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN")

headers = {
    'X-Shopify-Access-Token': TOKEN,
    'Content-Type': 'application/json'
}

SRC_THEME_ID = "160138428521"
DEST_THEME_ID = "160247840873"

print(f"=== COPYING ASSETS FROM {SRC_THEME_ID} TO {DEST_THEME_ID} ===")

# Get src assets list
r = requests.get(f'https://{DOMAIN}/admin/api/2025-01/themes/{SRC_THEME_ID}/assets.json', headers=headers)
if r.status_code != 200:
    print(f"Error listing assets: {r.status_code} | {r.text}")
    exit(1)

assets = r.json().get('assets', [])
print(f"Found {len(assets)} assets in source theme.")

for i, asset in enumerate(assets):
    key = asset['key']
    print(f"[{i+1}/{len(assets)}] Copying {key}...")
    
    # Get asset value
    r_val = requests.get(f'https://{DOMAIN}/admin/api/2025-01/themes/{SRC_THEME_ID}/assets.json', params={'asset[key]': key}, headers=headers)
    if r_val.status_code != 200:
        print(f"  [ERROR] Error fetching {key}: {r_val.status_code}")
        continue
        
    asset_data = r_val.json().get('asset', {})
    
    # Prepare payload
    payload = {
        "asset": {
            "key": key
        }
    }
    if 'value' in asset_data:
        payload['asset']['value'] = asset_data['value']
    elif 'attachment' in asset_data:
        payload['asset']['attachment'] = asset_data['attachment']
        
    # Write asset to destination
    r_put = requests.put(f'https://{DOMAIN}/admin/api/2025-01/themes/{DEST_THEME_ID}/assets.json', headers=headers, json=payload)
    if r_put.status_code != 200:
        print(f"  [ERROR] Error writing {key}: {r_put.status_code} | {r_put.text}")
    else:
        print(f"  [OK]")
        
    # Small pause to respect API rate limits
    time.sleep(0.4)

print("\n=== THEME REPLICATION COMPLETE! ===")
