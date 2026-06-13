import httpx
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

domain = "aura-decor-17.myshopify.com"
token = os.environ.get("SHOPIFY_ADMIN_TOKEN", "")

print(f"Testing shpat_ token on {domain}...")
try:
    r = httpx.get(
        f"https://{domain}/admin/api/2024-10/themes.json",
        headers={"X-Shopify-Access-Token": token},
        timeout=10
    )
    print(f"Themes.json status: {r.status_code}")
    if r.status_code == 200:
        print("SUCCESS! Token is valid with shpat_ prefix!")
        print("Themes:", r.json())
except Exception as e:
    print(f"Error: {e}")
