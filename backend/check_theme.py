import os, requests, json, sys
from dotenv import load_dotenv

load_dotenv()

DOMAIN = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")
TOKEN  = os.getenv("SHOPIFY_ADMIN_TOKEN", "")

headers = {
    'X-Shopify-Access-Token': TOKEN,
    'Content-Type': 'application/json'
}

# 1. Verificar temas
print("=== TEMAS ===")
r = requests.get(f'https://{DOMAIN}/admin/api/2024-01/themes.json', headers=headers)
themes = r.json().get('themes', [])
main_theme_id = None
for t in themes:
    role = t['role']
    print(f"  ID {t['id']} | {t['name']} | role={role}")
    if role == 'main':
        main_theme_id = t['id']

print(f"\n=== TEMA ATIVO: {main_theme_id} ===")

# 2. Verificar index.json
r2 = requests.get(
    f'https://{DOMAIN}/admin/api/2024-01/themes/{main_theme_id}/assets.json',
    params={'asset[key]': 'templates/index.json'},
    headers=headers
)
asset = r2.json().get('asset', {})
content = asset.get('value', '')
print("\n=== templates/index.json ===")
print(content[:3000])

# 3. Verificar secao hero (aura-hero ou sections/header)
print("\n=== Buscando secao hero ===")
for key in ['sections/aura-hero.liquid', 'sections/image-banner.liquid', 'sections/slideshow.liquid']:
    r3 = requests.get(
        f'https://{DOMAIN}/admin/api/2024-01/themes/{main_theme_id}/assets.json',
        params={'asset[key]': key},
        headers=headers
    )
    a = r3.json().get('asset', {})
    if a:
        print(f"  ENCONTRADO: {key} ({len(a.get('value',''))} chars)")
        # Mostra schema do banner para verificar configuracoes
        val = a.get('value', '')
        if '{% schema %}' in val:
            schema_start = val.find('{% schema %}')
            schema_end = val.find('{% endschema %}')
            print(val[schema_start:schema_end+15][:1500])
        break
    else:
        print(f"  nao encontrado: {key}")
