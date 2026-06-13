import httpx
import os
import sys

DOMAIN = "10ei3t-sf.myshopify.com"
TOKEN = os.environ.get("SHOPIFY_ADMIN_TOKEN", "")

print(f"Testing {DOMAIN}...")
for ver in ["2025-01", "2024-10", "2024-07"]:
    try:
        r = httpx.get(
            f"https://{DOMAIN}/admin/api/{ver}/shop.json",
            headers={"X-Shopify-Access-Token": TOKEN},
            timeout=10
        )
        print(f"API {ver}: HTTP {r.status_code}")
        if r.status_code == 200:
            print(r.json())
    except Exception as e:
        print(f"Error: {e}")
