# -*- coding: utf-8 -*-
"""
creative_agent.py — Pipeline Criativo Completo — Aura Decore
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Geradores suportados (em ordem de prioridade):
  1. Higgsfield AI   — imagem (Soul/Seedream) + vídeo (Kling/Seedance)  → HIGGSFIELD_API_KEY
  2. Together AI     — imagem FLUX.1 schnell (gratuito)                 → TOGETHER_API_KEY
  3. Stability AI    — imagem SDXL (plano gratuito)                     → STABILITY_API_KEY
  4. Google Veo/Imagen — vídeo/imagem premium                           → VERTEX_AI_KEY (Vertex AI)
  5. Gemini 2.0      — captions, roteiros, direção criativa             → GOOGLE_AI_KEY ✅

Uso:
  python creative_agent.py --theme "Quinta Aromática" --product "Vela Artesanal"
  python creative_agent.py --today          # usa tema do dia
  python creative_agent.py --video          # gera vídeo também
  python creative_agent.py --status         # mostra providers configurados
"""
import os, sys, json, time, base64, pathlib, argparse, urllib.parse
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
GOOGLE_AI_KEY      = os.getenv("GOOGLE_AI_KEY", "")
HIGGSFIELD_KEY     = os.getenv("HIGGSFIELD_API_KEY", "")
TOGETHER_KEY       = os.getenv("TOGETHER_API_KEY", "")
STABILITY_KEY      = os.getenv("STABILITY_API_KEY", "")
VERTEX_KEY         = os.getenv("VERTEX_AI_KEY", "")
FB_PAGE_TOKEN      = os.getenv("FB_PAGE_TOKEN", "")
META_ACCESS_TOKEN  = os.getenv("META_ACCESS_TOKEN") or FB_PAGE_TOKEN
IG_USER_ID         = os.getenv("IG_USER_ID", "17841442799060573")
FB_PAGE_ID         = os.getenv("FB_PAGE_ID", "1111100822090245")

GEMINI_URL         = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GRAPH_BASE         = "https://graph.facebook.com/v20.0"
STORE_URL          = "https://auradecore.com.br"
ASSETS_DIR         = pathlib.Path(__file__).parent / "social_posts" / "images"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURAÇÃO DE PROVEDORES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def status_provedores():
    """Mostra status de todos os provedores."""
    print("\n  📊 PROVEDORES DE CRIATIVO:")
    providers = [
        ("Gemini 2.0 Flash (texto)", bool(GOOGLE_AI_KEY), "GOOGLE_AI_KEY",
         "Já configurado ✅"),
        ("Higgsfield (imagem+vídeo premium)", bool(HIGGSFIELD_KEY), "HIGGSFIELD_API_KEY",
         "higgsfield.ai → Sign Up → API Keys"),
        ("Together AI (imagem Flux, grátis)", bool(TOGETHER_KEY), "TOGETHER_API_KEY",
         "api.together.ai → Account → API Keys (free tier)"),
        ("Stability AI (imagem SDXL)", bool(STABILITY_KEY), "STABILITY_API_KEY",
         "platform.stability.ai → Account → API Keys"),
        ("Google Veo/Imagen (vídeo premium)", bool(VERTEX_KEY), "VERTEX_AI_KEY",
         "console.cloud.google.com → Vertex AI → API Key"),
        ("Meta Graph API (posting)", bool(FB_PAGE_TOKEN), "FB_PAGE_TOKEN",
         "python get_fb_token.py"),
    ]
    for name, ok, key, guide in providers:
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name}")
        if not ok:
            print(f"     → .env: {key}=...")
            print(f"     → Como: {guide}")
    print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GERAÇÃO DE IMAGEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BRAND_STYLE = (
    "professional product photography, japandi minimalist aesthetic, "
    "wabi-sabi natural beauty, warm off-white background #F5F0EB, "
    "soft natural diffused light, premium luxury home decor brand, "
    "artisan handmade, terracotta and natural earth tones, "
    "high resolution 1080p, clean minimal composition, square format"
)

def gerar_prompt_imagem(produto: str, tema: str) -> str:
    """Usa Gemini para criar o prompt visual ideal para o produto."""
    if not GOOGLE_AI_KEY:
        return f"{produto}, {BRAND_STYLE}"

    try:
        r = httpx.post(
            f"{GEMINI_URL}?key={GOOGLE_AI_KEY}",
            json={"contents": [{"parts": [{"text":
                f"""Crie um prompt de imagem para geração de IA (Stable Diffusion/Flux) para:
Produto: {produto}
Tema: {tema}
Estilo da marca: Japandi, Wabi-sabi, minimalista brasileiro, tons terrosos naturais

O prompt deve ser em inglês, descritivo, específico para fotografia de produto premium.
Máximo 80 palavras. Retorne APENAS o prompt, sem explicação."""}]}]},
            timeout=15
        )
        if r.status_code == 200:
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return f"{text}, {BRAND_STYLE}"
    except Exception:
        pass
    return f"{produto.lower()} artisan minimal japandi, {BRAND_STYLE}"


def gerar_imagem_higgsfield(prompt: str, produto: str, date_str: str) -> dict:
    """Gera imagem via Higgsfield Seedream API."""
    if not HIGGSFIELD_KEY:
        return {"ok": False, "provider": "higgsfield", "msg": "HIGGSFIELD_API_KEY não configurado"}

    try:
        r = httpx.post(
            "https://platform.higgsfield.ai/api/v1/seedream/generate",
            headers={"hf-api-key": HIGGSFIELD_KEY, "Content-Type": "application/json"},
            json={"prompt": prompt, "aspect_ratio": "1:1", "resolution": "1080p"},
            timeout=60
        )
        if r.status_code == 200:
            data = r.json()
            request_id = data.get("request_id") or data.get("id")

            # Poll até completar (máx 2 min)
            for _ in range(24):
                time.sleep(5)
                poll_r = httpx.get(
                    f"https://platform.higgsfield.ai/api/v1/request/{request_id}",
                    headers={"hf-api-key": HIGGSFIELD_KEY},
                    timeout=15
                )
                if poll_r.status_code == 200:
                    result = poll_r.json()
                    status = result.get("status", "")
                    if status == "completed":
                        url = result.get("output", [{}])[0].get("url") or result.get("url")
                        if url:
                            img_path = ASSETS_DIR / f"{date_str}-{produto.replace(' ','-')[:20]}-hf.jpg"
                            img_r = httpx.get(url, timeout=30)
                            img_path.write_bytes(img_r.content)
                            return {"ok": True, "provider": "higgsfield", "url": url, "path": str(img_path)}
                    elif status == "failed":
                        break
        return {"ok": False, "provider": "higgsfield", "msg": f"Higgsfield erro: {r.status_code}"}
    except Exception as e:
        return {"ok": False, "provider": "higgsfield", "msg": str(e)}


def gerar_imagem_together(prompt: str, produto: str, date_str: str) -> dict:
    """Gera imagem via Together AI (FLUX.1-schnell — gratuito)."""
    if not TOGETHER_KEY:
        return {"ok": False, "provider": "together", "msg": "TOGETHER_API_KEY não configurado"}

    try:
        r = httpx.post(
            "https://api.together.xyz/v1/images/generations",
            headers={"Authorization": f"Bearer {TOGETHER_KEY}", "Content-Type": "application/json"},
            json={
                "model": "black-forest-labs/FLUX.1-schnell-Free",
                "prompt": prompt,
                "width": 1024, "height": 1024,
                "steps": 4, "n": 1,
                "response_format": "b64_json"
            },
            timeout=60
        )
        if r.status_code == 200:
            b64 = r.json()["data"][0]["b64_json"]
            img_bytes = base64.b64decode(b64)
            img_path = ASSETS_DIR / f"{date_str}-{produto.replace(' ','-')[:20]}-together.jpg"
            img_path.write_bytes(img_bytes)
            return {"ok": True, "provider": "together", "path": str(img_path), "url": None}
        return {"ok": False, "provider": "together", "msg": f"Together erro: {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"ok": False, "provider": "together", "msg": str(e)}


def gerar_imagem_stability(prompt: str, produto: str, date_str: str) -> dict:
    """Gera imagem via Stability AI (SDXL)."""
    if not STABILITY_KEY:
        return {"ok": False, "provider": "stability", "msg": "STABILITY_API_KEY não configurado"}

    try:
        r = httpx.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
            headers={"Authorization": f"Bearer {STABILITY_KEY}", "Content-Type": "application/json"},
            json={
                "text_prompts": [{"text": prompt, "weight": 1}],
                "cfg_scale": 7, "height": 1024, "width": 1024, "samples": 1, "steps": 30
            },
            timeout=60
        )
        if r.status_code == 200:
            b64 = r.json()["artifacts"][0]["base64"]
            img_bytes = base64.b64decode(b64)
            img_path = ASSETS_DIR / f"{date_str}-{produto.replace(' ','-')[:20]}-stability.jpg"
            img_path.write_bytes(img_bytes)
            return {"ok": True, "provider": "stability", "path": str(img_path), "url": None}
        return {"ok": False, "provider": "stability", "msg": f"Stability erro: {r.status_code}"}
    except Exception as e:
        return {"ok": False, "provider": "stability", "msg": str(e)}


def gerar_imagem(prompt: str, produto: str, date_str: str) -> dict:
    """Tenta provedores em cascata até gerar uma imagem."""
    providers = [
        ("Higgsfield",  gerar_imagem_higgsfield),
        ("Together AI", gerar_imagem_together),
        ("Stability",   gerar_imagem_stability),
    ]
    for name, fn in providers:
        print(f"     Tentando {name}...")
        result = fn(prompt, produto, date_str)
        if result["ok"]:
            print(f"     ✅ Imagem gerada via {name}")
            return result
        else:
            print(f"     ⚠️  {name}: {result['msg']}")

    print("     ❌ Todos os provedores de imagem indisponíveis")
    print("     📋 Configure pelo menos um em .env:")
    print("        TOGETHER_API_KEY=... (gratuito em api.together.ai)")
    print("        HIGGSFIELD_API_KEY=... (higgsfield.ai)")
    return {"ok": False, "provider": "none", "path": None, "url": None}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GERAÇÃO DE VÍDEO (imagem → vídeo via Higgsfield Kling)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def gerar_video_kling(image_url: str, produto: str, date_str: str) -> dict:
    """Gera vídeo de produto via Higgsfield Kling (imagem → vídeo)."""
    if not HIGGSFIELD_KEY:
        return {"ok": False, "msg": "HIGGSFIELD_API_KEY necessário para vídeo"}
    if not image_url:
        return {"ok": False, "msg": "Imagem necessária para gerar vídeo"}

    motion_prompt = (
        "gentle slow zoom in, soft ambient light, product rotates slightly, "
        "candle flame flickers naturally, dreamy atmosphere, cinematic slow motion"
    )

    try:
        r = httpx.post(
            "https://platform.higgsfield.ai/api/v1/kling/generate",
            headers={"hf-api-key": HIGGSFIELD_KEY, "Content-Type": "application/json"},
            json={"image_url": image_url, "prompt": motion_prompt},
            timeout=30
        )
        if r.status_code == 200:
            request_id = r.json().get("request_id") or r.json().get("id")
            print(f"     🎬 Vídeo Kling em processamento (ID: {request_id})...")
            return {"ok": True, "request_id": request_id, "status": "processing",
                    "msg": f"Poll: GET /api/v1/request/{request_id}"}
        return {"ok": False, "msg": f"Kling erro: {r.status_code}"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# POSTAGEM NO INSTAGRAM COM IMAGEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def postar_instagram_com_imagem(image_url: str, caption: str) -> dict:
    """Posta no Instagram com imagem via Graph API."""
    token = META_ACCESS_TOKEN
    if not token:
        return {"ok": False, "msg": "META_ACCESS_TOKEN/FB_PAGE_TOKEN não configurado"}
    if not image_url:
        return {"ok": False, "msg": "image_url necessário para post com imagem"}

    try:
        # Cria container com imagem
        r1 = httpx.post(
            f"{GRAPH_BASE}/{IG_USER_ID}/media",
            data={"image_url": image_url, "caption": caption, "access_token": token},
            timeout=30
        )
        container = r1.json()
        if "id" not in container:
            return {"ok": False, "msg": f"Container erro: {container}"}

        time.sleep(3)

        # Publica
        r2 = httpx.post(
            f"{GRAPH_BASE}/{IG_USER_ID}/media_publish",
            data={"creation_id": container["id"], "access_token": token},
            timeout=30
        )
        data = r2.json()
        return {"ok": "id" in data, "id": data.get("id"), "msg": data.get("error", {}).get("message", "")}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


def postar_facebook_com_foto(image_path: str, caption: str) -> dict:
    """Posta foto no Facebook Page."""
    if not FB_PAGE_TOKEN:
        return {"ok": False, "msg": "FB_PAGE_TOKEN não configurado"}
    if not image_path or not pathlib.Path(image_path).exists():
        # Post de texto apenas
        try:
            r = httpx.post(f"{GRAPH_BASE}/{FB_PAGE_ID}/feed",
                           data={"message": caption, "access_token": FB_PAGE_TOKEN}, timeout=20)
            data = r.json()
            return {"ok": "id" in data, "id": data.get("id"), "type": "text"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    try:
        with open(image_path, "rb") as f:
            r = httpx.post(
                f"{GRAPH_BASE}/{FB_PAGE_ID}/photos",
                data={"caption": caption, "access_token": FB_PAGE_TOKEN},
                files={"source": ("photo.jpg", f, "image/jpeg")},
                timeout=60
            )
        data = r.json()
        return {"ok": "id" in data, "id": data.get("id"), "type": "photo"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GERAÇÃO DE CAPTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

THEMES = {
    0: ("Segunda-feira Zen",  "#zen #mindfulness #decoracaozen #auradecore #japandi"),
    1: ("Terça Japandi",      "#japandi #wabisabi #ceramica #natureza #auradecore"),
    2: ("Quarta Botânica",    "#botanica #plantassecas #florespreservadas #auradecore"),
    3: ("Quinta Aromática",   "#velaartesanal #aromaterapia #difusor #auradecore"),
    4: ("Sexta do Lar",       "#decoracaodolar #homeinspo #casaconfortavel #auradecore"),
    5: ("Sábado Artesanal",   "#ceramicaartesanal #handmade #feitoamao #auradecore"),
    6: ("Domingo Ritual",     "#ritualdolar #domingo #calma #selfcare #auradecore"),
}

def gerar_caption(tema: str, produto: str, preco: str, url_produto: str, hashtags: str) -> dict:
    if not GOOGLE_AI_KEY:
        return _caption_fallback(tema, produto, preco, url_produto, hashtags)

    prompt = f"""Social media manager da Aura Decore (decoração Japandi/Wabi-sabi brasileira).

TEMA: {tema} | PRODUTO: {produto} ({preco}) | URL: {url_produto}

Crie em JSON:
{{
  "instagram": "caption poético max 120 palavras, 3-5 emojis, CTA 'link na bio', hashtags: {hashtags} #decoracaobrasileira #casaminimalista",
  "facebook": "caption direto max 80 palavras, CTA com link: {url_produto}, 2-3 emojis",
  "stories_text": "frase curta impactante max 8 palavras para Stories (sem emojis)",
  "alt_text": "descrição acessível da imagem max 30 palavras"
}}"""

    try:
        r = httpx.post(
            f"{GEMINI_URL}?key={GOOGLE_AI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.85, "maxOutputTokens": 800}},
            timeout=20
        )
        if r.status_code == 200:
            raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            s, e = raw.find("{"), raw.rfind("}") + 1
            if s >= 0 and e > s:
                return json.loads(raw[s:e])
    except Exception as ex:
        print(f"     ⚠️  Gemini: {ex}")

    return _caption_fallback(tema, produto, preco, url_produto, hashtags)


def _caption_fallback(tema, produto, preco, url_produto, hashtags):
    return {
        "instagram": f"✨ {tema}\n\n{produto} — para quem valoriza a beleza das coisas simples. 🌿\n\nCada peça artesanal tem sua própria alma. Descubra a sua.\n\n👉 Link na bio\n\n{hashtags} #decoracaobrasileira #casaminimalista",
        "facebook": f"🌿 {tema} — {produto}\n\n{preco} | Peça artesanal com alma japandi.\n\nTransforme seu espaço com a beleza natural da Aura Decore.\n🛍️ {url_produto}",
        "stories_text": f"Beleza que transforma espaços.",
        "alt_text": f"Produto artesanal {produto} com estética japandi minimalista."
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRODUTOS_SEMANA = {
    0: {"name": "Incensário de Cerâmica Ripple",        "price": "R$ 89,90",  "slug": "incensario-de-ceramica-ripple"},
    1: {"name": "Vaso Cerâmica Wabi — Bege Natural",    "price": "R$ 129,90", "slug": "vaso-ceramica-oval-minimalista"},
    2: {"name": "Eucalipto Preservado — Buquê Seco",    "price": "R$ 79,90",  "slug": "eucalipto-preservado-buque-seco-natural"},
    3: {"name": "Vela Artesanal de Soja — Bambu & Cedro","price": "R$ 69,90", "slug": "vela-artesanal-de-soja-bambu-cedro"},
    4: {"name": "Bandeja Mármore e Madeira — Oval",     "price": "R$ 149,90", "slug": "bandeja-marmore-e-madeira-oval"},
    5: {"name": "Conjunto Bowl Cerâmica — Set 3 Peças", "price": "R$ 189,90", "slug": "conjunto-bowl-ceramica-set-3-pecas"},
    6: {"name": "Kit Ritual Matinal — Aura Zen",        "price": "R$ 229,90", "slug": "kit-ritual-matinal-aura-zen"},
}

def main(tema_override=None, produto_override=None, gerar_video=False, dry_run=False, show_status=False):
    print("=" * 62)
    print(f"  AURA DECORE — Creative Agent {'[DRY RUN]' if dry_run else ''}")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 62)

    if show_status:
        status_provedores()
        return

    wd = datetime.now().weekday()
    tema_nome, hashtags = THEMES[wd]
    produto_info = PRODUTOS_SEMANA[wd]

    if tema_override:
        tema_nome = tema_override
    if produto_override:
        produto_info = {"name": produto_override, "price": "Veja na loja",
                        "slug": produto_override.lower().replace(" ", "-")}

    produto_url = f"{STORE_URL}/products/{produto_info['slug']}"
    date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"\n  📅 Tema: {tema_nome}")
    print(f"  🛍️  Produto: {produto_info['name']} — {produto_info['price']}")

    # ── 1. Caption (Gemini) ──────────────────────────────────
    print("\n  [1/4] Gerando captions com Gemini 2.0 Flash...")
    captions = gerar_caption(tema_nome, produto_info["name"],
                             produto_info["price"], produto_url, hashtags)
    print("  ✅ Captions geradas")

    # ── 2. Prompt Visual (Gemini) ────────────────────────────
    print("\n  [2/4] Criando prompt visual com Gemini...")
    img_prompt = gerar_prompt_imagem(produto_info["name"], tema_nome)
    print(f"  ✅ Prompt: {img_prompt[:80]}...")

    # ── 3. Imagem ────────────────────────────────────────────
    img_result = {"ok": False, "path": None, "url": None}
    if not dry_run:
        print("\n  [3/4] Gerando imagem...")
        img_result = gerar_imagem(img_prompt, produto_info["name"], date_str)
    else:
        print("\n  [3/4] [DRY RUN] Pulando geração de imagem")

    # ── 4. Vídeo (opcional) ──────────────────────────────────
    video_result = {"ok": False}
    if gerar_video and img_result.get("url") and not dry_run:
        print("\n  [3.5/4] Gerando vídeo via Higgsfield Kling...")
        video_result = gerar_video_kling(img_result["url"], produto_info["name"], date_str)

    # ── Preview ──────────────────────────────────────────────
    print("\n  📸 INSTAGRAM:")
    for line in captions["instagram"].split("\n"):
        print(f"     {line}")
    print(f"\n  📘 FACEBOOK:")
    for line in captions["facebook"].split("\n"):
        print(f"     {line}")
    print(f"\n  📖 STORIES: {captions.get('stories_text','')}")

    # ── Salvar ───────────────────────────────────────────────
    posts_dir = pathlib.Path(__file__).parent / "social_posts"
    posts_dir.mkdir(exist_ok=True)
    save_path = posts_dir / f"{date_str}-creative.json"
    save_data = {
        "date": date_str,
        "tema": tema_nome,
        "produto": produto_info,
        "captions": captions,
        "image_prompt": img_prompt,
        "image": img_result,
        "video": video_result,
        "gerado_em": datetime.now().isoformat()
    }
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print(f"\n  ✅ Salvo: {save_path}")

    # ── Publicar ─────────────────────────────────────────────
    if not dry_run and (FB_PAGE_TOKEN or META_ACCESS_TOKEN):
        print("\n  [4/4] Publicando...")

        # Instagram com imagem (se gerada) ou apenas texto
        if img_result.get("url"):
            ig = postar_instagram_com_imagem(img_result["url"], captions["instagram"])
        else:
            print("  ⚠️  Sem imagem — postando texto no Instagram")
            ig = {"ok": False, "msg": "Sem imagem gerada"}

        if ig["ok"]:
            print(f"  ✅ Instagram publicado! ID: {ig.get('id')}")
        else:
            print(f"  ❌ Instagram: {ig['msg']}")

        # Facebook com foto local (se existir) ou texto
        fb = postar_facebook_com_foto(img_result.get("path", ""), captions["facebook"])
        if fb["ok"]:
            print(f"  ✅ Facebook publicado! ID: {fb.get('id')} ({fb.get('type','?')})")
        else:
            print(f"  ❌ Facebook: {fb['msg']}")
    elif not dry_run:
        print("\n  ⏳ Publicação pendente — configure FB_PAGE_TOKEN:")
        print("     python get_fb_token.py")

    print("\n" + "=" * 62)
    print("  CONCLUÍDO")
    if not any([bool(HIGGSFIELD_KEY), bool(TOGETHER_KEY), bool(STABILITY_KEY)]):
        print("\n  ⚡ ATIVE A GERAÇÃO DE IMAGEM (escolha um):")
        print("  • Together AI (GRÁTIS): api.together.ai → copie key → TOGETHER_API_KEY=...")
        print("  • Higgsfield: higgsfield.ai → Sign Up → HIGGSFIELD_API_KEY=...")
    print("=" * 62)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Aura Decore Creative Agent")
    p.add_argument("--today",    action="store_true", help="Usar tema do dia (padrão)")
    p.add_argument("--theme",    help="Tema personalizado")
    p.add_argument("--product",  help="Produto personalizado")
    p.add_argument("--video",    action="store_true", help="Gerar vídeo também (requer Higgsfield)")
    p.add_argument("--dry-run",  action="store_true", help="Preview sem gerar nem publicar")
    p.add_argument("--status",   action="store_true", help="Mostrar status dos provedores")
    args = p.parse_args()
    main(args.theme, args.product, args.video, args.dry_run, args.status)
