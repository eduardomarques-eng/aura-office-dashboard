import os, httpx, time, base64, sys
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

load_dotenv()

DOMAIN = os.getenv("SHOPIFY_DOMAIN", "aura-decor-17.myshopify.com")
TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "")
THEME_ID = "160138428521"

headers = {
    'X-Shopify-Access-Token': TOKEN,
    'Content-Type': 'application/json'
}

# 1. Fetch remote assets list from Shopify
print("Fetching remote assets list from Shopify...")
url = f"https://{DOMAIN}/admin/api/2025-01/themes/{THEME_ID}/assets.json"
try:
    r = httpx.get(url, headers=headers, timeout=20)
    if r.status_code != 200:
        print(f"Error fetching assets list: {r.status_code} | {r.text}")
        exit(1)
    remote_keys = {a["key"] for a in r.json().get("assets", [])}
    print(f"Total remote assets on Shopify: {len(remote_keys)}")
except Exception as e:
    print(f"Exception fetching assets list: {e}")
    exit(1)

# 2. Scan local theme directory
local_dir = os.path.join(os.path.dirname(__file__), "..", "shopify-theme")
valid_folders = ["assets", "config", "layout", "locales", "sections", "snippets", "templates"]

local_files = []
for folder in valid_folders:
    folder_path = os.path.join(local_dir, folder)
    if not os.path.exists(folder_path):
        continue
    for root, _, files in os.walk(folder_path):
        for file in files:
            full_path = os.path.join(root, file)
            # Get relative path for key
            rel_path = os.path.relpath(full_path, local_dir)
            key = rel_path.replace("\\", "/")
            local_files.append((key, full_path))

print(f"Total local files found: {len(local_files)}")

# 3. Identify missing files or files we want to upload
missing_files = []
for key, full_path in local_files:
    if key not in remote_keys:
        missing_files.append((key, full_path))

print(f"Total missing files to upload: {len(missing_files)}")

# 4. Upload missing files
for index, (key, filepath) in enumerate(missing_files):
    print(f"[{index + 1}/{len(missing_files)}] Uploading {key}...")
    
    is_binary = filepath.endswith(('.png', '.gif', '.jpg', '.jpeg', '.webp', '.ico', '.pdf', '.woff', '.woff2', '.ttf', '.eot'))
    
    payload = {
        "asset": {
            "key": key
        }
    }
    
    try:
        if is_binary:
            with open(filepath, 'rb') as f:
                content = f.read()
            payload["asset"]["attachment"] = base64.b64encode(content).decode('utf-8')
        else:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            payload["asset"]["value"] = content
            
        put_url = f"https://{DOMAIN}/admin/api/2025-01/themes/{THEME_ID}/assets.json"
        
        # Retry logic for uploading
        uploaded = False
        retries = 3
        while not uploaded and retries > 0:
            r_put = httpx.put(put_url, headers=headers, json=payload, timeout=30)
            if r_put.status_code == 200:
                print(f"  [OK] Uploaded {key} ({r_put.json().get('asset', {}).get('size', '?')} bytes)")
                uploaded = True
            elif r_put.status_code == 429:
                print("  [WAIT] Rate limit hit. Sleeping for 2 seconds...")
                time.sleep(2)
                retries -= 1
            else:
                print(f"  [ERROR] Error uploading {key}: {r_put.status_code} | {r_put.text[:200]}")
                retries -= 1
                
        time.sleep(0.35)  # Pause to respect rate limits
    except Exception as e:
        print(f"  [EXCEPT] Exception during upload of {key}: {e}")

print("Upload process completed!")
