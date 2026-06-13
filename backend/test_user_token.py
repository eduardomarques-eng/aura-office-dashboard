vicio desgraçado viu import httpx
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import os
domain = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")
token = os.getenv("SHOPIFY_ADMIN_TOKEN", "").strip()

print(f"Token length: {len(token)}")
print(f"Token prefix: {token[:10]}")

headers = {
    "X-Shopify-Access-Token": token,
    "Content-Type": "application/json"
}

# Test different API versions and endpoints
for endpoint in ["themes.json", "shop.json", "products.json"]:
    url = f"https://{domain}/admin/api/2024-10/{endpoint}"
    try:
        r = httpx.get(url, headers=headers, timeout=10)
        print(f"Endpoint {endpoint}: Status {r.status_code}")
        print(f"Response: {r.text[:200]}")
    except Exception as e:
        print(f"Error on {endpoint}: {e}")
