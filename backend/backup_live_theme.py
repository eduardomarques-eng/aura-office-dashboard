"""
backup_live_theme.py — Backup completo do tema LIVE (MAIN) da Aura Decore.

Uso:
    python backup_live_theme.py            # backup do tema MAIN (live)
    python backup_live_theme.py 160266387561   # backup de um theme_id especifico

REGRA DA EQUIPE: rodar SEMPRE antes de qualquer alteracao no tema.
Tema valido atual: "Aura Decore - Cursor Dinamico" (160266387561).
Baixa todos os assets para theme-backups/<nome>-<timestamp>/ preservando a estrutura.
"""
import os, sys, time, json, base64, pathlib, datetime, requests
from dotenv import load_dotenv

load_dotenv()

DOMAIN = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")
TOKEN  = os.getenv("SHOPIFY_ADMIN_TOKEN") or os.getenv("SHOPIFY_ADMIN_API_TOKEN", "")
API    = "2025-01"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

if not TOKEN:
    print("[ERRO] SHOPIFY_ADMIN_TOKEN ausente no .env")
    sys.exit(1)


def _get(url, params=None, tries=4):
    """GET com retry simples para rate limit (429)."""
    for attempt in range(tries):
        r = requests.get(url, headers=HEADERS, params=params, timeout=60)
        if r.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        return r
    return r


def resolve_theme_id():
    if len(sys.argv) > 1:
        return sys.argv[1].split("/")[-1]
    r = _get(f"https://{DOMAIN}/admin/api/{API}/themes.json")
    for t in r.json().get("themes", []):
        if t.get("role") == "main":
            return str(t["id"]), t.get("name", "theme")
    print("[ERRO] Nenhum tema MAIN encontrado.")
    sys.exit(1)


def main():
    resolved = resolve_theme_id()
    if isinstance(resolved, tuple):
        theme_id, theme_name = resolved
    else:
        theme_id = resolved
        # busca o nome
        r = _get(f"https://{DOMAIN}/admin/api/{API}/themes/{theme_id}.json")
        theme_name = r.json().get("theme", {}).get("name", "theme")

    slug = "".join(c if c.isalnum() else "-" for c in theme_name).strip("-").lower()
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    out = pathlib.Path(__file__).parent / "theme-backups" / f"{slug}-{ts}"
    out.mkdir(parents=True, exist_ok=True)

    print(f"=== BACKUP: {theme_name} (ID {theme_id}) ===")
    print(f"Destino: {out}")

    r = _get(f"https://{DOMAIN}/admin/api/{API}/themes/{theme_id}/assets.json")
    assets = r.json().get("assets", [])
    print(f"Total de assets: {len(assets)}")

    ok, fail = 0, 0
    manifest = []
    for i, a in enumerate(assets, 1):
        key = a["key"]
        ra = _get(f"https://{DOMAIN}/admin/api/{API}/themes/{theme_id}/assets.json",
                  params={"asset[key]": key})
        asset = ra.json().get("asset", {})
        dest = out / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            if asset.get("value") is not None:
                dest.write_text(asset["value"], encoding="utf-8")
            elif asset.get("attachment"):
                dest.write_bytes(base64.b64decode(asset["attachment"]))
            else:
                fail += 1
                print(f"  [{i}/{len(assets)}] VAZIO: {key}")
                continue
            ok += 1
            manifest.append({"key": key, "size": asset.get("size")})
            if i % 20 == 0:
                print(f"  ... {i}/{len(assets)}")
        except Exception as e:
            fail += 1
            print(f"  [{i}/{len(assets)}] ERRO {key}: {e}")
        time.sleep(0.3)  # respeita rate limit REST (~2 req/s)

    (out / "_manifest.json").write_text(json.dumps({
        "theme_id": theme_id,
        "theme_name": theme_name,
        "domain": DOMAIN,
        "backup_at": ts,
        "assets_ok": ok,
        "assets_fail": fail,
        "assets": manifest,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n=== CONCLUIDO: {ok} ok, {fail} falhas ===")
    print(f"Backup salvo em: {out}")


if __name__ == "__main__":
    main()
