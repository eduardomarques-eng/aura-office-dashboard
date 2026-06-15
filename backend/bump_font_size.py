"""
bump_font_size.py — Aumenta a escala da fonte do corpo no tema LIVE da Aura Decore.
Edita config/settings_data.json (current.body_scale) via Admin API.
Salva o original antes de alterar (backup pontual).
Tema live: "Aura Decore - Cursor Dinamico" (160266387561).
"""
import os, json, datetime, pathlib, requests
from dotenv import load_dotenv

load_dotenv()
DOMAIN = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")
TOKEN  = os.getenv("SHOPIFY_ADMIN_TOKEN") or os.getenv("SHOPIFY_ADMIN_API_TOKEN", "")
THEME  = (os.getenv("SHOPIFY_LIVE_THEME_ID", "160266387561") or "160266387561").split("/")[-1]
API    = "2025-01"
H = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
BASE = f"https://{DOMAIN}/admin/api/{API}/themes/{THEME}/assets.json"

NEW_BODY_SCALE = 110     # era 100
KEY = "config/settings_data.json"

# 1) GET atual
r = requests.get(BASE, params={"asset[key]": KEY}, headers=H, timeout=60)
r.raise_for_status()
raw = r.json()["asset"]["value"]
data = json.loads(raw)

# 2) Backup pontual do original
ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
bdir = pathlib.Path(__file__).parent / "theme-backups"
bdir.mkdir(exist_ok=True)
bfile = bdir / f"settings_data_BEFORE_fontbump_{ts}.json"
bfile.write_text(raw, encoding="utf-8")
print(f"Backup do original salvo em: {bfile}")

# 3) Alterar current.body_scale
cur = data.get("current")
if not isinstance(cur, dict):
    print(f"[ERRO] 'current' nao e objeto (e '{cur}'). Abortado para nao quebrar settings.")
    raise SystemExit(1)

old_body = cur.get("body_scale")
old_head = cur.get("heading_scale")
cur["body_scale"] = NEW_BODY_SCALE
print(f"body_scale: {old_body} -> {cur['body_scale']}  (heading_scale mantido em {old_head})")

# 4) PUT de volta no tema live
payload = {"asset": {"key": KEY, "value": json.dumps(data, ensure_ascii=False)}}
r2 = requests.put(BASE, headers=H, json=payload, timeout=60)
if r2.status_code in (200, 201):
    print("PUT OK:", r2.json().get("asset", {}).get("updated_at", ""))
else:
    print("PUT FALHOU:", r2.status_code, r2.text[:400])
    raise SystemExit(1)

# 5) Verificar
rv = requests.get(BASE, params={"asset[key]": KEY}, headers=H, timeout=60)
chk = json.loads(rv.json()["asset"]["value"]).get("current", {}).get("body_scale")
print(f"Verificacao: current.body_scale agora = {chk}")
