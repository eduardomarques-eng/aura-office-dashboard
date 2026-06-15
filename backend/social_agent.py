# -*- coding: utf-8 -*-
"""
social_agent.py — Agente de Postagem Social Diária — Aura Decore
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Usa Gemini Pro (Google AI) para gerar conteúdo e Meta Graph API para publicar.
Posta diariamente no Instagram e Facebook da Aura Decore.

Uso:
  python social_agent.py               # Gera e posta agora
  python social_agent.py --dry-run     # Gera sem postar (preview)
  python social_agent.py --schedule    # Mostra config do agendador
"""
import os, sys, json, time, pathlib, argparse
from datetime import datetime
import httpx
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ENV = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV, override=True)

# ── Credenciais ────────────────────────────────────────────────
GOOGLE_AI_KEY   = os.getenv("GOOGLE_AI_KEY", "")
FB_PAGE_ID      = os.getenv("FB_PAGE_ID", "1111100822090245")
IG_USER_ID      = os.getenv("IG_USER_ID", "17841442799060573")
SHOPIFY_CDN     = "https://cdn.shopify.com/s/files/1/0685/7064/4585/files"
STORE_URL       = "https://auradecore.com.br"
GRAPH_BASE      = "https://graph.facebook.com/v20.0"
GEMINI_URL      = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ── Canais extras (Pinterest + TikTok) ────────────────────────
PINTEREST_URL         = os.getenv("PINTEREST_URL", "https://br.pinterest.com/auradecoracao/")
PINTEREST_ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN", "")  # OAuth via developers.pinterest.com
TIKTOK_URL            = os.getenv("TIKTOK_URL", "https://www.tiktok.com/@decore.aura")
TIKTOK_ACCESS_TOKEN   = os.getenv("TIKTOK_ACCESS_TOKEN", "")      # OAuth via business.tiktok.com
TIKTOK_CLIENT_KEY     = os.getenv("TIKTOK_CLIENT_KEY", "")        # app "Aura Decore Social" (7651513140559300629)
TIKTOK_CLIENT_SECRET  = os.getenv("TIKTOK_CLIENT_SECRET", "")
# Auto-publish só liga quando o app está aprovado pela plataforma E a publicação via API
# está implementada. Ter o token NÃO basta: Pinterest exige consumer type Business e
# TikTok exige Content Posting API + redirect URI configurados no portal. Até lá → manual.
PINTEREST_API_READY   = os.getenv("PINTEREST_API_READY", "false").lower() == "true"
TIKTOK_API_READY      = os.getenv("TIKTOK_API_READY", "false").lower() == "true"


def get_valid_token() -> str:
    """Retorna token valido. Se expirado, faz exchange automatico pelo user token."""
    # Recarrega .env para pegar token mais recente
    load_dotenv(dotenv_path=_ENV, override=True)
    token = os.getenv("FB_PAGE_TOKEN", "")
    if not token:
        return ""
    # Valida rapidamente
    try:
        r = httpx.get(
            f"{GRAPH_BASE}/{FB_PAGE_ID}",
            params={"fields": "id", "access_token": token},
            timeout=6
        )
        if "id" in r.json():
            return token
        # Token inválido — tenta exchange (se for user token salvo)
        r2 = httpx.get(
            f"{GRAPH_BASE}/{FB_PAGE_ID}",
            params={"fields": "access_token", "access_token": token},
            timeout=6
        )
        pg = r2.json().get("access_token", "")
        if pg:
            # Salva o novo page token
            env_text = pathlib.Path(_ENV).read_text(encoding="utf-8")
            lines = []
            for line in env_text.splitlines():
                if line.startswith("FB_PAGE_TOKEN=") or line.startswith("META_ACCESS_TOKEN="):
                    key = line.split("=")[0]
                    lines.append(f"{key}={pg}")
                else:
                    lines.append(line)
            pathlib.Path(_ENV).write_text("\n".join(lines) + "\n", encoding="utf-8")
            return pg
    except Exception:
        pass
    return token  # retorna o que tiver


# Carrega token válido na inicialização
FB_PAGE_TOKEN     = get_valid_token()
META_ACCESS_TOKEN = FB_PAGE_TOKEN

# ── Templates de tema por dia da semana ────────────────────────
THEMES = {
    0: ("Segunda-feira Zen",   "mindfulness, início da semana, renovação, paz interior"),
    1: ("Terça Japandi",       "estética japandi, wabi-sabi, minimalismo japonês, natureza"),
    2: ("Quarta Botânica",     "plantas secas, flores preservadas, botânica, natureza em casa"),
    3: ("Quinta Aromática",    "velas, difusores, aromas, bem-estar sensorial, ritual"),
    4: ("Sexta do Lar",        "decoração, ambiente aconchegante, fim de semana, casa bonita"),
    5: ("Sábado Artesanal",    "cerâmica artesanal, mãos que fazem, processos manuais, exclusividade"),
    6: ("Domingo Ritual",      "ritual matinal, café, calma, presença, gratidão, domingo especial"),
}

# ── Produtos destaque por tema ─────────────────────────────────
FEATURED_PRODUCTS = {
    0: {"name": "Incensário de Cerâmica Ripple",        "price": "R$ 89,90",  "handle": "incensario-de-ceramica-ripple",            "url": f"{STORE_URL}/products/incensario-de-ceramica-ripple"},
    1: {"name": "Vaso Cerâmica Wabi — Bege Natural",    "price": "R$ 129,90", "handle": "vaso-ceramica-wabi-bege-natural",           "url": f"{STORE_URL}/products/vaso-ceramica-wabi-bege-natural"},
    2: {"name": "Eucalipto Preservado — Buquê Seco",    "price": "R$ 79,90",  "handle": "eucalipto-preservado-buque-seco-natural",   "url": f"{STORE_URL}/products/eucalipto-preservado-buque-seco-natural"},
    3: {"name": "Vela Artesanal de Soja — Bambu & Cedro","price": "R$ 69,90", "handle": "vela-artesanal-de-soja-bambu-cedro",        "url": f"{STORE_URL}/products/vela-artesanal-de-soja-bambu-cedro"},
    4: {"name": "Bandeja Mármore e Madeira — Oval",     "price": "R$ 149,90", "handle": "bandeja-marmore-e-madeira-oval",            "url": f"{STORE_URL}/products/bandeja-marmore-e-madeira-oval"},
    5: {"name": "Conjunto Bowl Cerâmica — Set 3 Peças", "price": "R$ 189,90", "handle": "conjunto-bowl-ceramica-set-3-pecas",        "url": f"{STORE_URL}/products/conjunto-bowl-ceramica-set-3-pecas"},
    6: {"name": "Kit Ritual Matinal — Aura Zen",        "price": "R$ 229,90", "handle": "kit-ritual-matinal-aura-zen",               "url": f"{STORE_URL}/products/kit-ritual-matinal-aura-zen"},
}

def get_product_image_url(handle: str) -> str:
    """Retorna URL da imagem do produto no Shopify CDN."""
    return f"{SHOPIFY_CDN}/{handle}.jpg?v=1780619025"

# ── Hashtags por tema ──────────────────────────────────────────
HASHTAG_SETS = {
    0: "#zen #mindfulness #decoracaozen #casazen #segundafeira #aurazen #japandi #decorminimalista",
    1: "#japandi #wabisabi #minimalismo #decoracaojapandesa #ceramica #natureza #homedesign",
    2: "#botanica #plantassecas #decoracaobotanica #florespreservadas #naturezaemcasa #dryflowers",
    3: "#velaartesanal #aromaterapia #difusor #bemestarsensorial #ritualdolar #homescents",
    4: "#decoracaodolar #homesweethome #casaconfortavel #homeinspo #weekendvibes #decorminimalista",
    5: "#ceramicaartesanal #artesanato #handmade #feitoamao #ceramica #arte #exclusivo",
    6: {"name": "#ritualdomar #domingo #calma #gratidao #presenca #selfcare #morningrituals #zen"},
}

def gerar_conteudo_gemini(tema: str, keywords: str, produto: dict) -> dict:
    """Usa Gemini Pro para gerar caption Instagram + Facebook."""
    hoje = datetime.now().strftime("%d/%m/%Y")
    weekday = datetime.now().weekday()
    hashtags = HASHTAG_SETS.get(weekday, "#decoracao #auradecore #japandi")
    if isinstance(hashtags, dict):
        hashtags = "#ritualdolar #domingo #calma #gratidao"

    prompt = f"""Você é o social media manager da Aura Decore, uma loja de decoração estilo Japandi/Wabi-sabi brasileira.

TEMA DO DIA: {tema}
PALAVRAS-CHAVE: {keywords}
PRODUTO EM DESTAQUE: {produto['name']} — {produto['price']}
DATA: {hoje}

Crie 2 versões de caption para redes sociais:

1. INSTAGRAM (máx 150 palavras):
- Tom: poético, sensorial, inspirador
- Emojis estratégicos (3-5 máximo)
- Mencione o produto sutilmente
- CTA suave: "link na bio" ou "explore nossa coleção"
- Termine com os hashtags: {hashtags} #auradecore #decoracaobrasileira

2. FACEBOOK (máx 100 palavras):
- Tom: mais direto e acolhedor
- Foco no benefício/sentimento
- CTA claro: link do produto
- 2-3 emojis no máximo

Responda em JSON:
{{
  "instagram": "caption completo aqui",
  "facebook": "caption completo aqui",
  "tema": "{tema}",
  "produto": "{produto['name']}"
}}"""

    if not GOOGLE_AI_KEY:
        # Fallback sem API key
        return _fallback_content(tema, produto, hashtags)

    try:
        r = httpx.post(
            f"{GEMINI_URL}?key={GOOGLE_AI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.8, "maxOutputTokens": 1024}},
            timeout=30
        )
        if r.status_code == 200:
            raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            # Extrai o JSON da resposta
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
    except Exception as e:
        print(f"   ⚠️  Gemini erro: {e} — usando fallback")

    return _fallback_content(tema, produto, hashtags)


def _fallback_content(tema: str, produto: dict, hashtags: str) -> dict:
    """Conteúdo padrão quando Gemini não está disponível."""
    hoje = datetime.now().strftime("%d/%m")
    return {
        "instagram": f"""✨ {tema} na Aura Decore

Cada detalhe do seu lar conta uma história. O {produto['name']} foi pensado para trazer harmonia, leveza e beleza natural para o seu espaço.

Porque um ambiente bonito começa com as escolhas certas. 🌿

👉 Link na bio para explorar nossa coleção completa.

{hashtags} #auradecore #decoracaobrasileira #japandi""",
        "facebook": f"""🌿 {tema} — {hoje}

{produto['name']} — {produto['price']}

Transforme seu espaço com a estética Japandi. Peças artesanais que trazem calma e beleza para o seu dia a dia.

🛍️ {produto['url']}""",
        "tema": tema,
        "produto": produto["name"]
    }


def postar_facebook(caption: str, dry_run: bool = False) -> dict:
    """Posta no Facebook Page."""
    if not FB_PAGE_TOKEN:
        return {"ok": False, "msg": "FB_PAGE_TOKEN não configurado"}

    if dry_run:
        print(f"\n  [DRY RUN] Facebook:\n  {caption[:200]}...")
        return {"ok": True, "msg": "dry-run", "id": "preview"}

    try:
        r = httpx.post(
            f"{GRAPH_BASE}/{FB_PAGE_ID}/feed",
            data={"message": caption, "access_token": FB_PAGE_TOKEN},
            timeout=20
        )
        data = r.json()
        if "id" in data:
            return {"ok": True, "id": data["id"]}
        return {"ok": False, "msg": data.get("error", {}).get("message", str(data))}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


def postar_instagram(caption: str, image_url: str = "", dry_run: bool = False) -> dict:
    """Posta foto no Instagram via Graph API usando imagem do Shopify CDN."""
    token = META_ACCESS_TOKEN or FB_PAGE_TOKEN
    if not token:
        return {"ok": False, "msg": "META_ACCESS_TOKEN não configurado"}

    if dry_run:
        print(f"\n  [DRY RUN] Instagram (img: {image_url[:60]}...):\n  {caption[:200]}...")
        return {"ok": True, "msg": "dry-run", "id": "preview"}

    if not image_url:
        return {"ok": False, "msg": "image_url obrigatoria para posts no Instagram"}

    try:
        # Cria container de mídia com imagem
        r1 = httpx.post(
            f"{GRAPH_BASE}/{IG_USER_ID}/media",
            data={"image_url": image_url, "caption": caption, "access_token": token},
            timeout=30
        )
        container = r1.json()
        if "id" not in container:
            return {"ok": False, "msg": f"Container: {container}"}

        time.sleep(5)  # aguarda processamento da imagem

        # Publica o container
        r2 = httpx.post(
            f"{GRAPH_BASE}/{IG_USER_ID}/media_publish",
            data={"creation_id": container["id"], "access_token": token},
            timeout=20
        )
        data = r2.json()
        if "id" in data:
            return {"ok": True, "id": data["id"]}
        return {"ok": False, "msg": data.get("error", {}).get("message", str(data))}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


def _gerar_conteudo_pinterest(produto: dict, caption_ig: str) -> str:
    """Adapta caption IG para formato Pinterest pin (título SEO + descrição curta + link)."""
    nome = produto.get("name", "")
    preco = produto.get("price", "")
    url = produto.get("url", STORE_URL)
    return f"{nome} — {preco} | Decoração Japandi | Aura Decore\n\n" \
           f"{caption_ig[:200].strip()}...\n\n" \
           f"Compre em: {url}"


def _gerar_conteudo_tiktok(caption_ig: str) -> str:
    """Adapta caption IG para TikTok (mais curto, trending hooks, hashtags TikTok-friendly)."""
    linhas = [l for l in caption_ig.split("\n") if l.strip()]
    hook = linhas[0] if linhas else "Decoração que transforma."
    return f"{hook}\n\n#AuraDecore #Japandi #DecorTikTok #CasaMinimalista #WabiSabi #HomeDecorBrasil #DecorInspo"


def salvar_post_arquivo(content: dict, produto: dict) -> str:
    """Salva o post gerado em arquivo JSON para revisão."""
    posts_dir = pathlib.Path(__file__).parent / "social_posts"
    posts_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = posts_dir / f"{today}.json"
    ig_caption = content.get("instagram", "")
    post_data = {
        "date": today,
        "tema": content.get("tema"),
        "produto": content.get("produto"),
        "produto_url": produto.get("url"),
        "produto_price": produto.get("price"),
        "instagram": ig_caption,
        "facebook": content.get("facebook"),
        "pinterest": _gerar_conteudo_pinterest(produto, ig_caption),
        "tiktok": _gerar_conteudo_tiktok(ig_caption),
        "canais_auto": ["instagram", "facebook"]
                       + (["pinterest"] if PINTEREST_API_READY else [])
                       + (["tiktok"] if TIKTOK_API_READY else []),
        "canais_manual": ([] if PINTEREST_API_READY else ["pinterest"])
                       + ([] if TIKTOK_API_READY else ["tiktok"]),
        "gerado_em": datetime.now().isoformat()
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)
    return str(filepath)


def main(dry_run: bool = False):
    print("=" * 60)
    print(f"  AURA DECORE — Social Agent {'[DRY RUN]' if dry_run else ''}")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 60)

    weekday = datetime.now().weekday()
    tema_nome, tema_keys = THEMES[weekday]
    produto = FEATURED_PRODUCTS[weekday]

    print(f"\n  📅 Tema de hoje: {tema_nome}")
    print(f"  🛍️  Produto: {produto['name']} — {produto['price']}")

    # ── 1. Gerar conteúdo com Gemini ──
    print("\n  [1/3] Gerando conteúdo com Gemini Pro...")
    gemini_ok = bool(GOOGLE_AI_KEY)
    content = gerar_conteudo_gemini(tema_nome, tema_keys, produto)
    print(f"  {'✅ Gemini Pro' if gemini_ok else '⚠️  Fallback (sem GOOGLE_AI_KEY)'} — conteúdo gerado")

    # ── 2. Preview ──
    print("\n  📸 INSTAGRAM:")
    print("  " + "\n  ".join(content["instagram"].split("\n")))
    print("\n  📘 FACEBOOK:")
    print("  " + "\n  ".join(content["facebook"].split("\n")))

    # ── 3. Salvar ──
    saved_path = salvar_post_arquivo(content, produto)
    print(f"\n  ✅ Post salvo: {saved_path}")

    # ── Preview Pinterest + TikTok ──
    pinterest_content = _gerar_conteudo_pinterest(produto, content.get("instagram", ""))
    tiktok_content = _gerar_conteudo_tiktok(content.get("instagram", ""))
    print(f"\n  📌 PINTEREST (manual):\n  {pinterest_content[:150]}...")
    print(f"\n  🎵 TIKTOK (manual):\n  {tiktok_content[:150]}...")
    if not PINTEREST_API_READY:
        motivo = "app aguarda consumer type Business" if PINTEREST_ACCESS_TOKEN else "PINTEREST_ACCESS_TOKEN ausente"
        print(f"  ⚠️  Pinterest ({motivo}) — postar manualmente em {PINTEREST_URL}")
    if not TIKTOK_API_READY:
        motivo = "app aguarda Content Posting API + redirect URI" if TIKTOK_CLIENT_KEY else "TIKTOK_ACCESS_TOKEN ausente"
        print(f"  ⚠️  TikTok ({motivo}) — postar manualmente em {TIKTOK_URL}")

    # ── 4. Publicar ──
    if dry_run:
        print("\n  [DRY RUN] Posts não publicados — modo preview")
        return

    print("\n  [3/3] Publicando...")

    fb_result = postar_facebook(content["facebook"])
    if fb_result["ok"]:
        print(f"  ✅ Facebook publicado! ID: {fb_result.get('id')}")
    else:
        print(f"  ❌ Facebook: {fb_result['msg']}")
        if "FB_PAGE_TOKEN" in fb_result["msg"]:
            print("     → Configure FB_PAGE_TOKEN no .env")
            print("     → Execute: python get_fb_token.py")

    # Imagem do produto no Shopify CDN
    img_url = get_product_image_url(produto.get("handle", produto.get("name", "").lower().replace(" ", "-")))
    ig_result = postar_instagram(content["instagram"], image_url=img_url)
    if ig_result["ok"]:
        print(f"  ✅ Instagram publicado! ID: {ig_result.get('id')}")
    else:
        print(f"  ❌ Instagram: {ig_result['msg']}")
        if "não configurado" in ig_result.get("msg", ""):
            print("     → Configure META_ACCESS_TOKEN no .env (= FB_PAGE_TOKEN)")

    print("\n" + "=" * 60)
    print("  CONCLUÍDO")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aura Decore Social Agent")
    parser.add_argument("--dry-run", action="store_true", help="Preview sem publicar")
    parser.add_argument("--schedule", action="store_true", help="Mostrar config agendador")
    args = parser.parse_args()

    if args.schedule:
        print("""
Agendamento diário (Windows Task Scheduler):
  schtasks /create /tn "AuraDecore-SocialPost" /tr "python C:\\Users\\erick\\aura-office-dashboard\\backend\\social_agent.py" /sc daily /st 09:00

Agendamento diário (Railway cron via Procfile):
  Adicione em railway.toml:
  [cron.social-post]
  schedule = "0 12 * * *"  # 12:00 UTC = 09:00 Brasília
  command = "python backend/social_agent.py"
""")
    else:
        main(dry_run=args.dry_run)
