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
FB_PAGE_TOKEN   = os.getenv("FB_PAGE_TOKEN", "")
IG_USER_ID      = os.getenv("IG_USER_ID", "17841442799060573")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN") or FB_PAGE_TOKEN
STORE_URL       = "https://auradecore.com.br"
GRAPH_BASE      = "https://graph.facebook.com/v20.0"
GEMINI_URL      = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

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
    0: {"name": "Incensário de Cerâmica Ripple", "price": "R$ 89,90", "url": f"{STORE_URL}/products/incensario-de-ceramica-ripple"},
    1: {"name": "Vaso Cerâmica Wabi — Bege Natural", "price": "R$ 129,90", "url": f"{STORE_URL}/products/vaso-ceramica-oval-minimalista"},
    2: {"name": "Eucalipto Preservado — Buquê Seco", "price": "R$ 79,90", "url": f"{STORE_URL}/products/eucalipto-preservado-buque-seco-natural"},
    3: {"name": "Vela Artesanal de Soja — Bambu & Cedro", "price": "R$ 69,90", "url": f"{STORE_URL}/products/vela-artesanal-de-soja-bambu-cedro"},
    4: {"name": "Bandeja Mármore e Madeira — Oval", "price": "R$ 149,90", "url": f"{STORE_URL}/products/bandeja-marmore-e-madeira-oval"},
    5: {"name": "Conjunto Bowl Cerâmica — Set 3 Peças", "price": "R$ 189,90", "url": f"{STORE_URL}/products/conjunto-bowl-ceramica-set-3-pecas"},
    6: {"name": "Kit Ritual Matinal — Aura Zen", "price": "R$ 229,90", "url": f"{STORE_URL}/products/kit-ritual-matinal-aura-zen"},
}

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


def postar_instagram(caption: str, dry_run: bool = False) -> dict:
    """Posta no Instagram via Graph API (sem imagem = text post)."""
    token = META_ACCESS_TOKEN or FB_PAGE_TOKEN
    if not token:
        return {"ok": False, "msg": "META_ACCESS_TOKEN não configurado"}

    if dry_run:
        print(f"\n  [DRY RUN] Instagram:\n  {caption[:200]}...")
        return {"ok": True, "msg": "dry-run", "id": "preview"}

    try:
        # Cria container de mídia (apenas texto)
        r1 = httpx.post(
            f"{GRAPH_BASE}/{IG_USER_ID}/media",
            data={"caption": caption, "media_type": "REELS",
                  "access_token": token},
            timeout=20
        )
        container = r1.json()
        if "id" not in container:
            return {"ok": False, "msg": f"Container: {container}"}

        time.sleep(2)  # aguarda processamento

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


def salvar_post_arquivo(content: dict, produto: dict) -> str:
    """Salva o post gerado em arquivo JSON para revisão."""
    posts_dir = pathlib.Path(__file__).parent / "social_posts"
    posts_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = posts_dir / f"{today}.json"
    post_data = {
        "date": today,
        "tema": content.get("tema"),
        "produto": content.get("produto"),
        "produto_url": produto.get("url"),
        "produto_price": produto.get("price"),
        "instagram": content.get("instagram"),
        "facebook": content.get("facebook"),
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

    ig_result = postar_instagram(content["instagram"])
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
