import os
import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load env
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
live_theme_id = env_vars.get("SHOPIFY_LIVE_THEME_ID")
staging_theme_id = env_vars.get("SHOPIFY_STAGING_THEME_ID")

yampi_snippet_path = r"C:\Users\erick\aura-office-dashboard\shopify-theme\snippets\YampiSnippet.liquid"

if not os.path.exists(yampi_snippet_path):
    print(f"Error: YampiSnippet.liquid not found at {yampi_snippet_path}")
    sys.exit(1)

with open(yampi_snippet_path, 'r', encoding='utf-8') as f:
    yampi_snippet_content = f.read()

YAMPI_INCLUDE_TAG = """  <!-- Não remova. Checkout Yampi. -->
{% capture yampi_snippet_content %}{% include 'YampiSnippet' %}{% endcapture %} {% unless yampi_snippet_content contains 'Liquid error' %} {% include 'YampiSnippet' %} {% endunless %}
<!-- Não remova. Checkout Yampi. -->"""

def deploy_yampi_to_theme(theme_id, theme_name):
    print(f"\n--- Deploying Yampi to {theme_name} (Theme ID: {theme_id}) ---")
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }
    
    # 1. Upload YampiSnippet.liquid
    asset_url = f"https://{domain}/admin/api/2025-01/themes/{theme_id}/assets.json"
    payload = {
        "asset": {
            "key": "snippets/YampiSnippet.liquid",
            "value": yampi_snippet_content
        }
    }
    r = requests.put(asset_url, headers=headers, json=payload)
    if r.status_code == 200:
        print("✅ snippets/YampiSnippet.liquid uploaded successfully!")
    else:
        print(f"❌ Failed to upload snippets/YampiSnippet.liquid: {r.status_code} - {r.text}")
        return False

    # 2. Get layout/theme.liquid
    r_get = requests.get(asset_url, headers=headers, params={"asset[key]": "layout/theme.liquid"})
    if r_get.status_code != 200:
        print(f"❌ Failed to retrieve layout/theme.liquid: {r_get.status_code} - {r_get.text}")
        return False
        
    theme_liquid_content = r_get.json().get("asset", {}).get("value", "")
    
    if "YampiSnippet" in theme_liquid_content:
        print("ℹ️ layout/theme.liquid already contains Yampi integration. Skipping layout modification.")
        return True
    
    # Insert before </body>
    if "</body>" in theme_liquid_content:
        modified_content = theme_liquid_content.replace("</body>", f"{YAMPI_INCLUDE_TAG}\n</body>")
        print("Inserting Yampi include before </body> tag...")
    else:
        print("❌ Error: </body> tag not found in theme.liquid")
        return False
        
    # Upload layout/theme.liquid back
    payload_layout = {
        "asset": {
            "key": "layout/theme.liquid",
            "value": modified_content
        }
    }
    r_put = requests.put(asset_url, headers=headers, json=payload_layout)
    if r_put.status_code == 200:
        print("✅ layout/theme.liquid updated and uploaded successfully!")
        return True
    else:
        print(f"❌ Failed to upload updated layout/theme.liquid: {r_put.status_code} - {r_put.text}")
        return False

# Run deploy for both themes
deploy_yampi_to_theme(staging_theme_id, "Staging Theme")
deploy_yampi_to_theme(live_theme_id, "Live Theme")
