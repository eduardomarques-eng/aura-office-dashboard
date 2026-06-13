import httpx, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

pages = {
    "Homepage": "https://aura-decor-17.myshopify.com",
    "Collections": "https://aura-decor-17.myshopify.com/collections/all",
    "Product Abajur": "https://aura-decor-17.myshopify.com/products/abajur-de-bambu-natural-mesa",
}

print("=== CHECKING PAGES FOR LIQUID ERRORS ===")

for name, url in pages.items():
    try:
        r = httpx.get(url, params={"_fd": "0"}, timeout=15)
        print(f"\nPage: {name} ({url})")
        print(f"Status Code: {r.status_code}")
        
        html = r.text
        if "Liquid error" in html:
            print("[FAIL] Found Liquid errors on this page!")
            # Find the errors
            idx = 0
            while True:
                idx = html.find("Liquid error", idx)
                if idx == -1:
                    break
                # Print the context around the error
                context = html[max(0, idx - 100):min(len(html), idx + 200)]
                print(f"--- Context ---\n{context}\n---------------")
                idx += len("Liquid error")
        else:
            print("[OK] No Liquid errors found on this page!")
    except Exception as e:
        print(f"[FAIL] Exception fetching {name}: {e}")

print("\n=== VERIFICATION COMPLETE ===")
