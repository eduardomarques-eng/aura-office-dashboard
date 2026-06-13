import os, httpx, sys
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

load_dotenv()

DOMAIN = os.getenv("SHOPIFY_DOMAIN", "aura-decor-17.myshopify.com")
TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "")

url = f"https://{DOMAIN}/admin/api/2025-01/products.json"
headers = {"X-Shopify-Access-Token": TOKEN}

try:
    r = httpx.get(url, headers=headers, params={"limit": 50}, timeout=15)
    print(f"Status Code: {r.status_code}")
    if r.status_code == 200:
        products = r.json().get("products", [])
        print(f"Listed {len(products)} products:")
        for p in products:
            print(f"  - {p.get('title')} | Handle: {p.get('handle')} | Status: {p.get('status')}")
    else:
        print(f"Error: {r.text}")
except Exception as e:
    print(f"Exception: {e}")
