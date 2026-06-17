# -*- coding: utf-8 -*-
"""
social_agent.py — Motor de Conteúdo Social 5 Canais — Aura Decore
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Gera conteúdo editorial de alto nível: reels com script 30s, carrosséis de 8 slides,
fotos lifestyle. Publica em 5 canais simultâneos:
  1. Instagram @auradecore        — Meta Graph API
  2. Facebook Comercial @auradecore — Meta Graph API
  3. Facebook Pessoal @auras.decore — Chrome automation (Playwright)
  4. Pinterest @auradecoracao     — Pinterest API v5 (quando PINTEREST_API_READY=true)
  5. TikTok @decore.aura          — Chrome automation (Playwright, requer --tiktok-video)

Filosofia: 40% lifestyle · 30% produto em cena · 15% educação · 10% bastidores · 5% prova
NÃO é catálogo de produto — é editorial de marca aspiracional. Todo conteúdo em PT-BR.

Uso:
  python social_agent.py               # Gera e posta em todos os canais
  python social_agent.py --dry-run     # Preview sem postar
  python social_agent.py --date 2026-06-17  # Gera conteúdo para data específica
  python social_agent.py --tiktok-video video.mp4  # Inclui TikTok
"""
import os, sys, json, time, pathlib, argparse, subprocess, urllib.parse
from datetime import datetime, timedelta
import httpx
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ENV = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV, override=True)

GOOGLE_AI_KEY   = os.getenv("GOOGLE_AI_KEY", "")
ANTHROPIC_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
FB_PAGE_ID      = os.getenv("FB_PAGE_ID", "1111100822090245")
IG_USER_ID      = os.getenv("IG_USER_ID", "17841442799060573")
FB_PAGE_TOKEN   = os.getenv("FB_PAGE_TOKEN", "")
STORE_URL       = "https://auradecore.com.br"
GRAPH_BASE      = "https://graph.facebook.com/v21.0"
GEMINI_URL      = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

TIKTOK_CHROME_ENABLED    = os.getenv("TIKTOK_CHROME_ENABLED", "true").lower() == "true"
FB_PESSOAL_CHROME_ENABLED = os.getenv("FB_PESSOAL_CHROME_ENABLED", "true").lower() == "true"
PINTEREST_API_READY      = os.getenv("PINTEREST_API_READY", "false").lower() == "true"
PINTEREST_ACCESS_TOKEN   = os.getenv("PINTEREST_ACCESS_TOKEN", "")
PINTEREST_BOARD_ID       = os.getenv("PINTEREST_BOARD_ID", "")

POSTS_DIR = pathlib.Path(__file__).parent / "social_posts"
POSTS_DIR.mkdir(exist_ok=True)

# Weekday alvo — sobrescrito por main() quando --date é passado
_TARGET_WEEKDAY: int = datetime.now().weekday()

# ── Voz da marca ─────────────────────────────────────────────────────────────
BRAND_VOICE = (
    "Tom: sereno, poético, sofisticado, acolhedor. "
    "Linguagem calma e minimalista — evite exclamações excessivas, emojis em excesso "
    "e linguagem de vendas agressiva. "
    "Exemplos de frases da marca: "
    "'Um espaço que respira calma.' "
    "'Menos coisas. Mais presença.' "
    "'O detalhe que transforma um ambiente em lar.' "
    "O produto NUNCA é o protagonista — ele é parte do ambiente, da sensação."
)

# ── Calendário editorial semanal — Aura Decore ───────────────────────────────
# Programação real aprovada 2026-06-17 | Postiz postingTimes: 540/600/1080/1140
# Tipos: reel · carrossel · foto · story
# hora_segundo: dias com 2 posts (Seg + Qua). n8n WF08 dispara social_agent.py
# novamente às 19:00 nesses dias via --second-post flag.
WEEKLY_CALENDAR = {
    0: {"tipo": "reel",      "pilar": "educacao",   "hora": "09:00",
        "hora_segundo": "19:00", "tipo_segundo": "foto", "pilar_segundo": "lifestyle",
        "tema": "Como transformar qualquer cantinho em um espaço Japandi em 3 passos",
        "tema_segundo": "Silêncio visual: o detalhe que transforma um ambiente em lar"},
    1: {"tipo": "carrossel", "pilar": "produto",    "hora": "18:00",
        "tema": "5 peças que elevam a decoração da sua casa sem gastar muito"},
    2: {"tipo": "reel",      "pilar": "lifestyle",  "hora": "09:00",
        "hora_segundo": "19:00", "tipo_segundo": "foto", "pilar_segundo": "lifestyle",
        "tema": "A arte de montar uma bancada Japandi — do zero ao perfeito",
        "tema_segundo": "Ambiente decorado: o produto que faz toda a diferença"},
    3: {"tipo": "foto",      "pilar": "lifestyle",  "hora": "18:00",
        "tema": "Silêncio visual: o segredo dos ambientes mais bonitos do mundo"},
    4: {"tipo": "carrossel", "pilar": "lifestyle",  "hora": "18:00",
        "tema": "Lookbook: 7 ambientes Japandi que vão mudar sua forma de decorar"},
    5: {"tipo": "reel",      "pilar": "lifestyle",  "hora": "10:00",
        "tema": "ASMR de uma manhã Japandi — o ritual que você vai querer ter"},
    6: {"tipo": "carrossel", "pilar": "educacao",   "hora": "10:00",
        "tema": "Wabi-Sabi: a filosofia japonesa que aceita a imperfeição como beleza"},
}

# ── Coleção de produtos por pilar/dia ─────────────────────────────────────────
# shopify_img: CDN Shopify (sempre acessível pelo Meta). Usado como imagem primária.
# Fallback para Pollinations.ai apenas se shopify_img não disponível.
PRODUTOS = {
    0: {"name": "Incensário Ripple",           "price": "R$ 89,90",  "handle": "incensario-de-ceramica-ripple",
        "categoria": "ritual",
        "shopify_img": "https://cdn.shopify.com/s/files/1/0685/7064/4585/files/0001-5676166915954052063_aec8f558-aa01-404a-af28-fe5ffeca3c99.png"},
    1: {"name": "Vaso Wabi Bege Natural",       "price": "R$ 129,90", "handle": "vaso-ceramica-wabi-bege-natural",
        "categoria": "vaso",
        "shopify_img": "https://cdn.shopify.com/s/files/1/0685/7064/4585/files/0001-5676166915954052063_ae0f4e11-791f-4491-876e-3c0293245f36.png"},
    2: {"name": "Eucalipto Preservado",         "price": "R$ 79,90",  "handle": "eucalipto-preservado-buque-seco-natural",
        "categoria": "botanica",
        "shopify_img": "https://cdn.shopify.com/s/files/1/0685/7064/4585/files/0001-6048839783845039403_a649d883-76d4-49e4-9114-c313299fddbc.png"},
    3: {"name": "Vela de Soja Bambu & Cedro",   "price": "R$ 69,90",  "handle": "vela-artesanal-de-soja-bambu-cedro",
        "categoria": "aroma",
        "shopify_img": "https://cdn.shopify.com/s/files/1/0685/7064/4585/files/0001-5727958312850494609_dafae35e-eca2-4d13-b863-54946738b6d5.png"},
    4: {"name": "Bandeja Mármore & Madeira",    "price": "R$ 149,90", "handle": "bandeja-marmore-e-madeira-oval",
        "categoria": "organizacao",
        "shopify_img": "https://cdn.shopify.com/s/files/1/0685/7064/4585/files/0001-2988643836488738398_c6bab2e4-9ecf-4429-8d50-195d688d7121.png"},
    5: {"name": "Set Bowl Cerâmica 3 Peças",    "price": "R$ 189,90", "handle": "conjunto-bowl-ceramica-set-3-pecas",
        "categoria": "ceramica",
        "shopify_img": "https://cdn.shopify.com/s/files/1/0685/7064/4585/files/conjunto-bowl-ceramica.png"},
    6: {"name": "Kit Ritual Matinal Aura Zen",  "price": "R$ 229,90", "handle": "kit-ritual-matinal-aura-zen",
        "categoria": "kit",
        "shopify_img": "https://cdn.shopify.com/s/files/1/0685/7064/4585/files/0001-2447085992274919075_4029cb90-464a-469e-a016-815db12e6d10.png"},
}

HASHTAGS = {
    "lifestyle":  "#Japandi #EstiloJapandi #CasaMinimalista #DecorBrasil #InterioresJapandi #MinimalismoNatural #LarAconchegante #AmbienteSereno #CasaComAlma #HomeInspo",
    "produto":    "#AuraDecore #DecorMinimalista #VasoCeramica #CasaDecorada #DetalhesQueImportam #DecorPremium #PecasArtesanais #HomeDecorBrasil #DecoracaoNatural #ProdutoJapandi",
    "educacao":   "#WabiSabi #DicasDeDecoracao #DesignDeInteriores #DecorInspiracao #MinimalismoConsciente #ArquiteturaDeInteriores #EstiloDeVida #DesignMinimalista #DecorConsciente #InterioresMinimalistas",
    "lifestyle2": "#DecoracaoJapandi #JapandiStyle #NordicInterior #JapandiHome #MinimalistHome #WabiSabiHome #NaturalDecor #SlowLiving #ZenHome #CalmHome",
}


# ── LLM: Gemini ou Claude ─────────────────────────────────────────────────────
def _llm(system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> str:
    """Chama Gemini 2.0 Flash (com retry) ou Claude como fallback."""
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    if GOOGLE_AI_KEY:
        for attempt in range(3):
            try:
                r = httpx.post(
                    f"{GEMINI_URL}?key={GOOGLE_AI_KEY}",
                    json={
                        "contents": [{"parts": [{"text": full_prompt}]}],
                        "generationConfig": {"temperature": 0.85, "maxOutputTokens": max_tokens}
                    },
                    timeout=45
                )
                if r.status_code == 200:
                    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                if r.status_code == 429:
                    wait = 20 * (attempt + 1)
                    print(f"   ⏳ Gemini rate limit — aguardando {wait}s (tentativa {attempt+1}/3)...")
                    time.sleep(wait)
                    continue
                print(f"   ⚠️  Gemini HTTP {r.status_code}")
                break
            except Exception as e:
                print(f"   ⚠️  Gemini erro: {e}")
                break

    if ANTHROPIC_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": full_prompt}]
            )
            return msg.content[0].text.strip()
        except Exception as e:
            print(f"   ⚠️  Claude erro: {e}")

    return ""


# ── Geração de conteúdo por tipo ──────────────────────────────────────────────

def gerar_reel(tema: str, pilar: str, produto: dict) -> dict:
    """Gera script de Reel 30s + legenda + hashtags."""
    hashtags = HASHTAGS.get(pilar, HASHTAGS["lifestyle"]) + " " + HASHTAGS["lifestyle2"]

    system = (
        "Você é NOX, diretor criativo da Aura Decore. Criamos reels cinematic e aspiracionais — "
        "jamais parecemos catálogo de produto. "
        f"{BRAND_VOICE} "
        "Crie um script de Reel de 30 segundos para Instagram/TikTok no seguinte formato JSON exato."
    )

    user = f"""Tema do Reel: {tema}
Produto em cena (sutilmente): {produto['name']} — {produto['price']}
Pilar: {pilar}

Retorne APENAS este JSON (sem markdown, sem explicação):
{{
  "hook": "Cena de abertura 0-3s — pergunta que para o scroll ou afirmação surpreendente",
  "cena_1": "3-10s — primeira cena visual com narração/texto em tela",
  "cena_2": "10-18s — segunda cena que aprofunda o tema",
  "cena_3": "18-25s — terceira cena com transformação ou revelação",
  "cta": "25-30s — chamada para ação sutil, sem urgência artificial",
  "musica": "Sugestão de estilo de música/som (ex: lo-fi japonês, sons naturais ASMR, piano minimalista)",
  "legenda_ig": "Caption completo para Instagram (80-120 palavras, poético, com emojis estratégicos 3-4)",
  "legenda_tiktok": "Caption TikTok (30-50 palavras, mais direto, hook forte)",
  "legenda_fb": "Caption Facebook (50-70 palavras, acolhedor, com link do produto)",
  "alt_text": "Descrição da imagem para acessibilidade (20 palavras)"
}}"""

    raw = _llm(system, user, max_tokens=1200)
    return _parse_json(raw) or _fallback_reel(tema, produto, hashtags)


def gerar_carrossel(tema: str, pilar: str, produto: dict) -> dict:
    """Gera carrossel de 8 slides + legenda + hashtags."""
    hashtags = HASHTAGS.get(pilar, HASHTAGS["lifestyle"]) + " " + HASHTAGS["lifestyle2"]

    system = (
        "Você é VERA, creative director da Aura Decore. "
        "Criamos carrosséis editoriais irresistíveis — cada slide tem um design limpo e minimalista. "
        f"{BRAND_VOICE} "
        "Crie um carrossel de 8 slides que as pessoas vão salvar e compartilhar."
    )

    user = f"""Tema do Carrossel: {tema}
Produto contextual: {produto['name']} — {produto['price']} — {STORE_URL}/products/{produto['handle']}
Pilar: {pilar}

Retorne APENAS este JSON:
{{
  "capa": {{
    "titulo": "Título impactante (máx 6 palavras)",
    "subtitulo": "Gancho de curiosidade (1 linha)"
  }},
  "slides": [
    {{"numero": 2, "titulo": "Slide 2 — título", "texto": "1-2 frases do conteúdo"}},
    {{"numero": 3, "titulo": "Slide 3 — título", "texto": "1-2 frases do conteúdo"}},
    {{"numero": 4, "titulo": "Slide 4 — título", "texto": "1-2 frases do conteúdo"}},
    {{"numero": 5, "titulo": "Slide 5 — título", "texto": "1-2 frases do conteúdo"}},
    {{"numero": 6, "titulo": "Slide 6 — título", "texto": "1-2 frases do conteúdo"}},
    {{"numero": 7, "titulo": "Slide 7 — título", "texto": "1-2 frases do conteúdo"}}
  ],
  "cta_slide": "Slide 8 — CTA sutil convidando para auradecore.com.br",
  "legenda_ig": "Caption Instagram para o carrossel (70-100 palavras, que instiga a ver os slides)",
  "legenda_fb": "Caption Facebook (50-70 palavras, com link do produto)",
  "legenda_tiktok": "Caption TikTok para vídeo do carrossel (30-40 palavras)"
}}"""

    raw = _llm(system, user, max_tokens=1400)
    return _parse_json(raw) or _fallback_carrossel(tema, produto, hashtags)


def gerar_foto(tema: str, pilar: str, produto: dict) -> dict:
    """Gera caption poético para post de foto lifestyle."""
    hashtags = HASHTAGS.get(pilar, HASHTAGS["lifestyle"]) + " " + HASHTAGS["lifestyle2"]

    system = (
        "Você é VERA, copywriter da Aura Decore. "
        f"{BRAND_VOICE} "
        "Crie captions para foto lifestyle — não é post de produto, é editorial de estilo de vida."
    )

    user = f"""Tema da Foto: {tema}
Produto em cena: {produto['name']}
Pilar: {pilar}

Retorne APENAS este JSON:
{{
  "legenda_ig": "Caption poético para Instagram (60-90 palavras, 3-4 emojis, CTA sutil no final)",
  "legenda_fb": "Caption Facebook (40-60 palavras, com link do produto no final)",
  "legenda_tiktok": "Caption TikTok (20-35 palavras, direto ao ponto)",
  "stories_text": "Texto para Stories (máx 8 palavras — impactante e simples)",
  "alt_text": "Descrição acessível da imagem (20 palavras)"
}}"""

    raw = _llm(system, user, max_tokens=700)
    return _parse_json(raw) or _fallback_foto(tema, produto, hashtags)


# ── Geração de imagem via Pollinations.ai ────────────────────────────────────

# Prompts de imagem pré-definidos por categoria — sem chamada LLM extra
_IMG_PROMPTS = {
    "ritual":     "handmade ripple ceramic incense holder, minimalist japandi lifestyle, dried sage bundle, soft morning light, cream linen background, earth tones amber and warm white, wabi-sabi aesthetic, premium home decor photography, clean minimal composition, 1080x1080",
    "vaso":       "wabi-sabi ceramic vase bege natural, dried pampas grass and eucalyptus stems, japandi minimalist interior, warm natural light from window, linen texture surface, terracotta and cream palette, professional lifestyle photography, negative space composition",
    "botanica":   "preserved dried eucalyptus bouquet in handmade ceramic vase, japandi aesthetic, soft diffused light, warm cream background, dried botanical arrangement, minimal composition, premium home decor brand photography, earth tones",
    "aroma":      "artisan soy candle bamboo cedar, japandi minimalist setting, soft candlelight glow, handmade ceramic tray, linen texture, dried botanicals background, warm amber and cream tones, professional lifestyle photography, cozy minimalist atmosphere",
    "organizacao":"marble wood oval tray styled with candle ceramic bowl and dried flower, japandi home styling, natural light overhead, cream and warm wood tones, minimal flat lay, premium lifestyle photography, negative space",
    "ceramica":   "set of 3 handmade ceramic bowls wabi-sabi, japandi minimal kitchen counter, soft natural light, cream and terracotta tones, linen napkin, dried botanical accent, professional product lifestyle photography",
    "kit":        "japandi morning ritual flat lay, handmade ceramic set incense candle bowl, linen background, dried sage, warm natural light, cream and amber palette, slow living aesthetic, premium lifestyle photography, minimal composition",
}

def gerar_prompt_imagem(tipo: str, pilar: str, tema: str, produto: dict) -> str:
    """Retorna prompt de imagem pré-definido por categoria (sem chamada LLM)."""
    categoria = produto.get("categoria", "ritual")
    base = _IMG_PROMPTS.get(categoria, _IMG_PROMPTS["ritual"])
    # Ajuste sutil por tipo de post
    if tipo == "reel":
        base += ", vertical 9:16 composition, cinematic atmosphere"
    elif tipo == "carrossel":
        base += ", editorial style, text space left side, clean background"
    return base


def gerar_imagem_pollinations(prompt: str, width: int = 1080, height: int = 1080) -> dict:
    """Gera imagem via Pollinations.ai (gratuito, sem API key)."""
    seed = abs(hash(prompt)) % 99999
    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={width}&height={height}&model=flux&nologo=true&enhance=true&seed={seed}"
    )

    # Tenta baixar para validar que a imagem existe
    try:
        r = httpx.get(url, timeout=60, follow_redirects=True)
        if r.status_code == 200 and len(r.content) > 5000:
            # Salva localmente
            img_dir = pathlib.Path(__file__).parent / "generated_images"
            img_dir.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            img_path = img_dir / f"social_post_{ts}.jpg"
            img_path.write_bytes(r.content)
            return {"ok": True, "url": url, "path": str(img_path), "provider": "pollinations"}
    except Exception as e:
        print(f"   ⚠️  Pollinations erro: {e}")

    return {"ok": False, "url": url, "path": None, "provider": "pollinations_url_only"}


# ── Parsers e fallbacks ───────────────────────────────────────────────────────

def _parse_json(text: str) -> dict | None:
    if not text:
        return None
    # Remove markdown code blocks (```json ... ```)
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except Exception:
            pass
    return None


# Copy editorial pré-escrito por tema (fallback de alta qualidade)
_EDITORIAL = {
    0: {  # Segunda — Reel educação Japandi
        "hook": "Por que alguns ambientes parecem pesados e outros respiram calma? A resposta é simples.",
        "cena_1": "Japandi não é um estilo de decoração — é uma filosofia. Menos coisas. Mais intenção.",
        "cena_2": "Três elementos mudam tudo: uma textura natural, uma planta ou ramo seco, e um item artesanal com alma.",
        "cena_3": "O incensário que queima devagar. O vaso que guarda silêncio. O ramo que traz a natureza para dentro.",
        "cta": "Explore nossa coleção em auradecore.com.br — link na bio.",
        "musica": "Sons de natureza suaves ou piano minimalista japonês",
        "legenda_ig": "✨ Três passos para um espaço que respira calma.\n\nNão é sobre ter mais — é sobre escolher melhor.\n\nUm ramo seco numa jarra de cerâmica. Uma vela acesa. O silêncio que só os espaços certos têm.\n\nEsse é o Japandi.\n\n🌿 Explore nossa coleção — link na bio.\n\n",
        "legenda_tiktok": "Como fazer seu apartamento parecer uma casa de revista sem reformar nada 🌿 #Japandi #DecorTikTok #AuraDecore #CasaMinimalista",
        "legenda_fb": "🌿 Três passos simples para transformar qualquer cantinho num espaço Japandi.\n\nNão é sobre o estilo — é sobre como você quer se sentir em casa.\n\nConheça nossa coleção: auradecore.com.br",
        "alt_text": "Cantinho Japandi com incensário de cerâmica, ramo seco e tecido de linho em tons terrosos",
    },
    1: {  # Terça — Carrossel produto
        "capa": {"titulo": "5 peças. Uma casa diferente.", "subtitulo": "Cada uma com um propósito."},
        "slides": [
            {"numero": 2, "titulo": "01. O vaso que ancora", "texto": "Cerâmica artesanal com textura imperfeita — bonita exatamente por isso. Wabi-sabi em forma de objeto."},
            {"numero": 3, "titulo": "02. O ramo que vive para sempre", "texto": "Eucalipto preservado. Natureza que fica — sem água, sem cuidado, com toda a presença."},
            {"numero": 4, "titulo": "03. A vela que transforma o ar", "texto": "Bambu e cedro. Quando acende, muda o clima do ambiente inteiro. Aromaterapia sem esforço."},
            {"numero": 5, "titulo": "04. A bandeja que organiza", "texto": "Mármore e madeira. Coloque sobre ela tudo que importa — vela, incenso, flor — e o caos vira composição."},
            {"numero": 6, "titulo": "05. O incensário que ritualiza", "texto": "Cerâmica Ripple. Não é só decoração — é o objeto que marca o início e o fim de cada momento do seu dia."},
            {"numero": 7, "titulo": "Uma peça muda o cantinho.", "texto": "Cinco peças mudam a forma como você sente sua casa."},
        ],
        "cta_slide": "Explore todas as peças em auradecore.com.br — cada uma escolhida com cuidado para o seu lar.",
        "legenda_ig": "Salve este carrossel. 📌\n\nCinco peças que transformam qualquer espaço sem precisar de reforma — só de intenção.\n\nO detalhe certo muda tudo. 🌿\n\n👉 Veja nossa coleção completa — link na bio.\n\n",
        "legenda_fb": "🌿 Cinco peças artesanais que elevam a decoração da sua casa.\n\nCada uma escolhida para trazer calma, textura e beleza natural ao seu lar.\n\nConheça: auradecore.com.br",
        "legenda_tiktok": "5 objetos que vão fazer seu apê parecer de revista 😌🌿 #AuraDecore #Japandi #DecorTikTok #CasaBonitaGastouPouco",
    },
    2: {  # Quarta — Reel lifestyle bancada
        "hook": "Sua bancada está pedindo socorro. Deixa eu te mostrar o que fazer.",
        "cena_1": "Comece com uma base vazia. Respira. Nada começa com acúmulo.",
        "cena_2": "Um elemento alto: ramo ou planta seca. Um elemento médio: vela ou difusor. Um elemento baixo: bandeja ou bowl.",
        "cena_3": "Eucalipto preservado. Bandeja de mármore. Vela acesa. Três elementos — uma bancada perfeita.",
        "cta": "Todos os elementos na nossa loja — link na bio. auradecore.com.br",
        "musica": "ASMR de objetos de cerâmica ou lo-fi calm",
        "legenda_ig": "A regra da bancada Japandi: nunca mais de três alturas diferentes. 🌿\n\nAlto. Médio. Baixo.\nPlanta. Vela. Bandeja.\n\nEssa tríade funciona em qualquer espaço, qualquer tamanho, qualquer orçamento.\n\n👉 Encontre cada peça — link na bio.\n\n",
        "legenda_tiktok": "A regra dos 3 objetos que salva qualquer bancada bagunçada ✨ #Japandi #DecorTikTok #AuraDecore #Organização",
        "legenda_fb": "🌿 Do zero ao perfeito: como montar uma bancada Japandi com apenas 3 elementos.\n\nAlto (planta ou ramo) + Médio (vela ou difusor) + Baixo (bandeja).\n\nVeja as peças: auradecore.com.br/products/eucalipto-preservado-buque-seco-natural",
        "alt_text": "Bancada Japandi com eucalipto preservado, vela artesanal e bandeja de mármore em ambiente claro minimalista",
    },
    3: {  # Quinta — Foto lifestyle silêncio visual
        "legenda_ig": "Silêncio visual.\n\nNão é vazio — é escolha.\nCada superfície livre é uma respiro.\nCada objeto que fica foi decidido com cuidado.\n\nAmbientes bonitos não acumulam. Eles selecionam. 🌿\n\n👉 Link na bio — curadoria de peças para o seu lar.\n\n",
        "legenda_fb": "🌿 O segredo dos ambientes mais bonitos do mundo?\n\nNão é o que eles têm — é o que eles não têm.\n\nVela de Soja Bambu & Cedro — R$ 69,90\nauradecore.com.br/products/vela-artesanal-de-soja-bambu-cedro",
        "legenda_tiktok": "O ambiente mais bonito que você já viu tinha uma coisa em comum: espaço vazio 🤍 #Japandi #Minimalismo #AuraDecore",
        "stories_text": "Menos coisas. Mais presença.",
        "alt_text": "Ambiente minimalista com vela artesanal de cerâmica, linho bege e luz natural lateral suave",
    },
    4: {  # Sexta — Carrossel lookbook
        "capa": {"titulo": "7 ambientes Japandi", "subtitulo": "Que vão mudar sua forma de decorar"},
        "slides": [
            {"numero": 2, "titulo": "Sala de estar — respiro total", "texto": "Um sofá de linho, um vaso de cerâmica no chão, uma planta seca alta no canto. Isso é tudo."},
            {"numero": 3, "titulo": "Quarto — santuário pessoal", "texto": "Roupa de cama em tons naturais, mesinha com apenas três objetos: livro, vela, copo d'água."},
            {"numero": 4, "titulo": "Bancada da cozinha", "texto": "Bowl de cerâmica com frutas, uma planta em vaso simples, óleo em garrafa de vidro âmbar."},
            {"numero": 5, "titulo": "Cantinho de leitura", "texto": "Uma poltrona, uma luminária discreta, uma bandeja com chá e incenso. O refúgio mais simples do mundo."},
            {"numero": 6, "titulo": "Home office com alma", "texto": "Mesa limpa, um ramo seco num vaso ao lado, um difusor ligado. Produtividade começa no ambiente."},
            {"numero": 7, "titulo": "Banheiro — spa particular", "texto": "Porta-shampoo de bambu, vela, toalha de linho. Três mudanças que transformam o banheiro inteiro."},
        ],
        "cta_slide": "Cada peça desses ambientes existe na Aura Decore. Veja em auradecore.com.br",
        "legenda_ig": "Salve para o Pinterest da sua cabeça. 📌\n\n7 ambientes Japandi que você pode recriar na sua casa — sem reforma, sem muito dinheiro.\n\nO segredo é a curadoria. Menos peças, mais certas. 🌿\n\n👉 Link na bio.\n\n",
        "legenda_fb": "🌿 Sete referências de ambientes Japandi que provam: beleza não precisa de acúmulo.\n\nVeja nossa coleção completa de peças artesanais: auradecore.com.br",
        "legenda_tiktok": "7 ambientes que vão mudar como você decora sua casa para sempre 😍 #Japandi #LookbookDecor #AuraDecore #CasaMinimalista",
    },
    5: {  # Sábado — Reel ASMR manhã
        "hook": "06h30. A casa ainda dorme. É quando a manhã pertence só a você.",
        "cena_1": "Água quente no coador de vidro. O café descendo devagar. Silêncio com cheiro.",
        "cena_2": "Incenso aceso. O ritual que prepara o espaço antes do dia começar.",
        "cena_3": "Bowl de cerâmica. Xícara. Uma vela. A mesa como altar de presença.",
        "cta": "Encontre os objetos do seu ritual — auradecore.com.br",
        "musica": "ASMR sons de natureza — água, vento suave, pássaros distantes",
        "legenda_ig": "O ritual que ninguém te contou: fazer o ambiente antes de fazer o dia. 🌿\n\nAntes da lista de tarefas. Antes do celular.\nUm incenso. Uma vela. O café.\n\nO ambiente certo muda tudo que vem depois.\n\n👉 Link na bio — objetos para o seu ritual matinal.\n\n",
        "legenda_tiktok": "Uma manhã Japandi completa: o ritual que mudou meu dia inteiro ☀️ #AuraDecore #ManhãJapandi #SlowLiving #ASMR #DecorTikTok",
        "legenda_fb": "🌿 Sábado de manhã como deveria ser: devagar, com intenção e cheiro bom.\n\nSet Bowl Cerâmica — R$ 189,90\nauradecore.com.br/products/conjunto-bowl-ceramica-set-3-pecas",
        "alt_text": "Mesa posta para café da manhã Japandi com bowl de cerâmica, vela acesa e incensário em ambiente claro",
    },
    6: {  # Domingo — Carrossel Wabi-Sabi
        "capa": {"titulo": "Wabi-Sabi", "subtitulo": "A filosofia que aceita a imperfeição como beleza"},
        "slides": [
            {"numero": 2, "titulo": "O que é Wabi-Sabi?", "texto": "Uma filosofia japonesa milenar que enxerga beleza no transitório, no imperfeito, no incompleto."},
            {"numero": 3, "titulo": "Wabi = Imperfeição humilde", "texto": "A craqueladura na cerâmica não é um defeito — é a assinatura do tempo. Cada peça é única porque viveu."},
            {"numero": 4, "titulo": "Sabi = Beleza que envelhece", "texto": "A patina da madeira, a textura áspera da argila, o ramo seco que dança mesmo sem vento."},
            {"numero": 5, "titulo": "Wabi-Sabi na sua casa", "texto": "Escolha peças feitas à mão. Prefira materiais naturais. Aceite as marcas do uso — elas são a história do objeto."},
            {"numero": 6, "titulo": "O que NÃO é Wabi-Sabi", "texto": "Perfeição industrial. Superfícies sem história. Objetos que nunca foram tocados. Beleza que não respira."},
            {"numero": 7, "titulo": "A pergunta que muda tudo", "texto": "Cada objeto na sua casa te diz algo? Se não, talvez não precise estar lá."},
        ],
        "cta_slide": "Curadoria de peças artesanais com alma — cada uma imperfeita do jeito certo. auradecore.com.br",
        "legenda_ig": "Wabi-Sabi não é estética — é uma forma de ver o mundo. 🌿\n\nA cerâmica com imperfeição é mais bonita. O ramo seco tem mais poesia que a flor artificial.\n\nA beleza que envelhece bem é a única que vale.\n\nSalve esse carrossel. 📌\n\n",
        "legenda_fb": "🌿 Wabi-Sabi: a filosofia japonesa que vai mudar como você olha para a decoração.\n\nKit Ritual Matinal Aura Zen — R$ 229,90\nauradecore.com.br/products/kit-ritual-matinal-aura-zen",
        "legenda_tiktok": "Wabi-Sabi: por que a imperfeição é o maior luxo do mundo 🤍 #WabiSabi #Japandi #AuraDecore #Filosofia #DecorTikTok",
    },
}


def _fallback_reel(tema: str, produto: dict, hashtags: str) -> dict:
    ed = _EDITORIAL.get(_TARGET_WEEKDAY, {})
    h = HASHTAGS.get("lifestyle", "") + " " + HASHTAGS.get("lifestyle2", "")
    return {
        "hook":          ed.get("hook",   f"O espaço certo começa com uma escolha."),
        "cena_1":        ed.get("cena_1", f"Textura natural. Luz suave. Um objeto com alma."),
        "cena_2":        ed.get("cena_2", "Cada detalhe conta. Cada peça tem uma história."),
        "cena_3":        ed.get("cena_3", f"O {produto['name']} que transforma."),
        "cta":           ed.get("cta",    "Explore em auradecore.com.br — link na bio."),
        "musica":        ed.get("musica", "Lo-fi japonês, sons naturais ASMR"),
        "legenda_ig":    ed.get("legenda_ig",    f"✨ {tema}\n\n🌿 Link na bio.\n\n{h} #auradecore #decoracaobrasileira"),
        "legenda_tiktok":ed.get("legenda_tiktok",f"{tema} 🌿 #AuraDecore #Japandi #DecorTikTok #WabiSabi"),
        "legenda_fb":    ed.get("legenda_fb",    f"🌿 {produto['name']} — {produto['price']}\n{STORE_URL}/products/{produto['handle']}"),
        "alt_text":      ed.get("alt_text", f"Ambiente Japandi minimalista com {produto['name']}, luz natural suave, tons terrosos"),
    }


def _fallback_carrossel(tema: str, produto: dict, hashtags: str) -> dict:
    ed = _EDITORIAL.get(_TARGET_WEEKDAY, {})
    h = HASHTAGS.get("lifestyle", "") + " " + HASHTAGS.get("lifestyle2", "")
    return {
        "capa":          ed.get("capa",     {"titulo": tema[:35], "subtitulo": "Aura Decore — Japandi & Wabi-Sabi"}),
        "slides":        ed.get("slides",   [{"numero": i, "titulo": f"Slide {i}", "texto": "Conteúdo Aura Decore."} for i in range(2, 8)]),
        "cta_slide":     ed.get("cta_slide","Explore nossa coleção em auradecore.com.br"),
        "legenda_ig":    ed.get("legenda_ig",    f"📌 Salve este carrossel.\n\n{tema}\n\n🌿 Link na bio.\n\n{h} #auradecore"),
        "legenda_fb":    ed.get("legenda_fb",    f"🌿 {tema}\n\n{STORE_URL}"),
        "legenda_tiktok":ed.get("legenda_tiktok",f"{tema} 🌿 #AuraDecore #Japandi #DecorTikTok"),
    }


def _fallback_foto(tema: str, produto: dict, hashtags: str) -> dict:
    ed = _EDITORIAL.get(_TARGET_WEEKDAY, {})
    h = HASHTAGS.get("lifestyle", "") + " " + HASHTAGS.get("lifestyle2", "")
    return {
        "legenda_ig":     ed.get("legenda_ig",     f"✨ {tema}\n\n🌿 Link na bio.\n\n{h} #auradecore #decoracaobrasileira"),
        "legenda_fb":     ed.get("legenda_fb",     f"🌿 {produto['name']} — {produto['price']}\n{STORE_URL}/products/{produto['handle']}"),
        "legenda_tiktok": ed.get("legenda_tiktok", f"{tema} 🌿 #AuraDecore #Japandi #CasaMinimalista"),
        "stories_text":   ed.get("stories_text",   "Beleza que transforma."),
        "alt_text":       ed.get("alt_text",        f"Ambiente Japandi com {produto['name']}, luz natural e tons terrosos"),
    }


# ── Publicação ────────────────────────────────────────────────────────────────

def _get_token() -> str:
    load_dotenv(dotenv_path=_ENV, override=True)
    return os.getenv("FB_PAGE_TOKEN", "")


def postar_instagram(caption: str, image_url: str) -> dict:
    """Publica foto simples (1 imagem) no Instagram via Graph API."""
    token = _get_token()
    if not token or not image_url:
        return {"ok": False, "msg": "Token ou imagem ausente"}
    try:
        r1 = httpx.post(
            f"{GRAPH_BASE}/{IG_USER_ID}/media",
            data={"image_url": image_url, "caption": caption, "access_token": token},
            timeout=30
        )
        c = r1.json()
        if "id" not in c:
            return {"ok": False, "msg": f"Container: {c}"}
        time.sleep(5)
        r2 = httpx.post(
            f"{GRAPH_BASE}/{IG_USER_ID}/media_publish",
            data={"creation_id": c["id"], "access_token": token},
            timeout=20
        )
        d = r2.json()
        if "id" in d:
            return {"ok": True, "id": d["id"]}
        return {"ok": False, "msg": str(d)}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


def postar_instagram_carrossel(caption: str, image_urls: list[str]) -> dict:
    """Publica carrossel (2–10 imagens) no Instagram via Graph API.
    Requer mínimo 2 URLs válidas e acessíveis publicamente.
    """
    token = _get_token()
    valid_urls = [u for u in image_urls if u and u.startswith("http")]
    if not token:
        return {"ok": False, "msg": "FB_PAGE_TOKEN ausente"}
    if len(valid_urls) < 2:
        # Degradar para post simples se menos de 2 imagens
        if valid_urls:
            print("  ⚠️  Carrossel: menos de 2 imagens — degradando para post simples")
            return postar_instagram(caption, valid_urls[0])
        return {"ok": False, "msg": "Nenhuma imagem válida para carrossel"}

    child_ids = []
    for i, url in enumerate(valid_urls[:10]):  # IG permite até 10
        try:
            r = httpx.post(
                f"{GRAPH_BASE}/{IG_USER_ID}/media",
                data={"image_url": url, "is_carousel_item": "true", "access_token": token},
                timeout=30
            )
            d = r.json()
            if "id" in d:
                child_ids.append(d["id"])
                print(f"     Slide {i+1}/{len(valid_urls)}: container {d['id']}")
            else:
                print(f"     ⚠️  Slide {i+1} falhou: {d}")
        except Exception as e:
            print(f"     ⚠️  Slide {i+1} erro: {e}")

    if len(child_ids) < 2:
        return {"ok": False, "msg": f"Apenas {len(child_ids)} slides criados — mínimo 2 para carrossel"}

    time.sleep(3)
    try:
        r2 = httpx.post(
            f"{GRAPH_BASE}/{IG_USER_ID}/media",
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": caption,
                "access_token": token,
            },
            timeout=30
        )
        c2 = r2.json()
        if "id" not in c2:
            return {"ok": False, "msg": f"Carousel container: {c2}"}

        time.sleep(5)
        r3 = httpx.post(
            f"{GRAPH_BASE}/{IG_USER_ID}/media_publish",
            data={"creation_id": c2["id"], "access_token": token},
            timeout=20
        )
        d3 = r3.json()
        if "id" in d3:
            return {"ok": True, "id": d3["id"], "slides": len(child_ids)}
        return {"ok": False, "msg": str(d3)}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


def postar_facebook(caption: str, image_url: str = "") -> dict:
    token = _get_token()
    if not token:
        return {"ok": False, "msg": "FB_PAGE_TOKEN ausente"}
    try:
        if image_url:
            r = httpx.post(
                f"{GRAPH_BASE}/{FB_PAGE_ID}/photos",
                data={"url": image_url, "caption": caption, "access_token": token},
                timeout=20
            )
        else:
            r = httpx.post(
                f"{GRAPH_BASE}/{FB_PAGE_ID}/feed",
                data={"message": caption, "access_token": token},
                timeout=20
            )
        d = r.json()
        if "id" in d:
            return {"ok": True, "id": d["id"]}
        return {"ok": False, "msg": str(d)}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


def postar_tiktok_chrome(video_path: str, caption: str, dry_run: bool = False) -> dict:
    if not video_path or not pathlib.Path(video_path).exists():
        return {"ok": False, "msg": f"Vídeo não encontrado: {video_path}"}
    script = pathlib.Path(__file__).parent / "tiktok_chrome_post.py"
    cmd = [sys.executable, str(script), "--video", video_path, "--caption", caption]
    if dry_run:
        cmd.append("--dry-run")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding="utf-8")
        if result.returncode == 0:
            return {"ok": True, "msg": "Publicado via TikTok Studio Chrome"}
        return {"ok": False, "msg": result.stderr or result.stdout}
    except subprocess.TimeoutExpired:
        return {"ok": False, "msg": "Timeout: upload demorou > 5 min"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


def postar_facebook_pessoal(caption: str, image_url: str = "", dry_run: bool = False) -> dict:
    """Publica no perfil pessoal @auras.decore via Chrome (Playwright)."""
    script = pathlib.Path(__file__).parent / "fb_pessoal_chrome_post.py"
    if not script.exists():
        return {"ok": False, "msg": "fb_pessoal_chrome_post.py não encontrado"}
    cmd = [sys.executable, str(script), "--caption", caption]
    if image_url:
        cmd += ["--image-url", image_url]
    if dry_run:
        cmd.append("--dry-run")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding="utf-8")
        if result.returncode == 0:
            return {"ok": True, "msg": "Publicado no FB Pessoal @auras.decore via Chrome"}
        return {"ok": False, "msg": (result.stderr or result.stdout)[:300]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "msg": "Timeout: automação Chrome demorou > 5 min"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


def postar_pinterest(caption: str, image_url: str, link: str = "") -> dict:
    """Cria um Pin no Pinterest @auradecoracao via API v5."""
    if not PINTEREST_API_READY:
        return {"ok": False, "msg": "PINTEREST_API_READY=false — ative em .env quando aprovado"}
    if not PINTEREST_ACCESS_TOKEN:
        return {"ok": False, "msg": "PINTEREST_ACCESS_TOKEN ausente — execute get_pinterest_token.py"}
    if not PINTEREST_BOARD_ID:
        return {"ok": False, "msg": "PINTEREST_BOARD_ID ausente — adicione ao .env"}
    try:
        payload = {
            "board_id": PINTEREST_BOARD_ID,
            "title": caption[:100],
            "description": caption,
            "media_source": {"source_type": "image_url", "url": image_url},
        }
        if link:
            payload["link"] = link
        r = httpx.post(
            "https://api.pinterest.com/v5/pins",
            headers={
                "Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        d = r.json()
        if "id" in d:
            return {"ok": True, "id": d["id"]}
        return {"ok": False, "msg": str(d)}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


# ── Salvamento do post ────────────────────────────────────────────────────────

def salvar_post(data: dict, date_str: str) -> str:
    filepath = POSTS_DIR / f"{date_str}-creative.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(filepath)


# ── Integração banco Canva ────────────────────────────────────────────────────

def _canva_posts_hoje() -> list:
    """Retorna posts Canva agendados para hoje (do canva_design_db.py)."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "canva_design_db",
            pathlib.Path(__file__).parent / "canva_design_db.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        db = pathlib.Path(__file__).parent / "canva_designs.db"
        if not db.exists():
            mod.init_db()
            mod.gerar_calendario(dias=90)
        return mod.get_posts_hoje()
    except Exception as e:
        return []


def _marcar_canva_publicado(pub_id: int, post_id: str = "", erro: str = ""):
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "canva_design_db",
            pathlib.Path(__file__).parent / "canva_design_db.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.marcar_publicado(pub_id, post_id, erro)
    except Exception:
        pass


# ── Main ──────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False, date_str: str = "", tiktok_video: str = ""):
    global _TARGET_WEEKDAY
    alvo = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
    weekday = alvo.weekday()
    _TARGET_WEEKDAY = weekday
    today = alvo.strftime("%Y-%m-%d")

    slot    = WEEKLY_CALENDAR[weekday]
    produto = PRODUTOS[weekday]
    produto["url"] = f"{STORE_URL}/products/{produto['handle']}"
    produto["categoria"] = produto.get("categoria", "decor")

    tipo  = slot["tipo"]
    pilar = slot["pilar"]
    tema  = slot["tema"]
    dias  = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

    print("=" * 62)
    print(f"  AURA DECORE — Social Agent {'[DRY RUN]' if dry_run else ''}")
    print(f"  {alvo.strftime('%d/%m/%Y')} ({dias[weekday]}) — {slot['hora']}")
    print("=" * 62)

    # ── Calendário Canva do dia ───────────────────────────────────────────────
    canva_posts = _canva_posts_hoje()
    if canva_posts:
        print(f"\n  📅 CANVA HOJE ({len(canva_posts)} posts agendados):")
        for p in canva_posts:
            print(f"     {p['hora']} [{p['canal']:<18}] {p['titulo'][:40]}")
            print(f"           https://www.canva.com/design/{p['design_id']}/edit")
        print()
    print(f"\n  Tipo:    {tipo.upper()}")
    print(f"  Pilar:   {pilar} ({['lifestyle 40%','produto 30%','educacao 15%','bastidores 10%','prova 5%'][['lifestyle','produto','educacao','bastidores','prova'].index(pilar)] if pilar in ['lifestyle','produto','educacao','bastidores','prova'] else pilar})")
    print(f"  Tema:    {tema}")
    print(f"  Produto: {produto['name']} — {produto['price']}")

    # ── 1. Gerar conteúdo ──
    print(f"\n  [1/4] Gerando conteúdo {tipo} com IA...")
    if tipo == "reel":
        content = gerar_reel(tema, pilar, produto)
    elif tipo == "carrossel":
        content = gerar_carrossel(tema, pilar, produto)
    else:
        content = gerar_foto(tema, pilar, produto)

    llm_ok = bool(GOOGLE_AI_KEY or ANTHROPIC_KEY) and "hook" in content or "capa" in content or "legenda_ig" in content
    print(f"  {'✅ Conteúdo gerado' if llm_ok else '⚠️  Fallback (sem API key)'}")

    # ── 2. Imagem primária: Shopify CDN (sempre acessível pelo Meta)
    #       Secundária: Pollinations.ai (para slides extras em carrossel)
    print(f"\n  [2/4] Preparando imagem...")
    shopify_img_url = produto.get("shopify_img", "")
    img_prompt = gerar_prompt_imagem(tipo, pilar, tema, produto)
    w, h = (1080, 1920) if tipo == "reel" else (1080, 1080)

    if shopify_img_url:
        print(f"  ✅ Imagem primária: Shopify CDN ({shopify_img_url.split('/')[-1][:50]})")
        img = {"ok": True, "url": shopify_img_url, "path": None, "provider": "shopify_cdn"}
        # Para carrossel, gerar imagens extras via Pollinations como slides adicionais
        if tipo == "carrossel":
            print(f"     Gerando slides extras via Pollinations.ai...")
            extra_imgs = []
            for seed_offset in [0, 1, 2]:
                ep = gerar_imagem_pollinations(img_prompt + f" variation {seed_offset}", w, h)
                extra_imgs.append(ep.get("url", ""))
            carrossel_urls = [shopify_img_url] + [u for u in extra_imgs if u]
            print(f"     Total slides com URL válida: {len(carrossel_urls)}")
        else:
            carrossel_urls = [shopify_img_url]
    else:
        img = gerar_imagem_pollinations(img_prompt, w, h)
        carrossel_urls = [img.get("url", "")]
        if img["ok"]:
            print(f"  ✅ Imagem gerada via Pollinations: {pathlib.Path(img['path']).name}")
        else:
            print(f"  ⚠️  Imagem URL gerada (Pollinations pode demorar p/ ficar acessível)")
            print(f"     {img['url'][:80]}...")

    # ── 3. Preview ──
    legenda_ig = content.get("legenda_ig", "")
    legenda_fb = content.get("legenda_fb", "")
    legenda_fb_pessoal = content.get("legenda_fb_pessoal", legenda_fb)  # usa FB comercial como fallback
    legenda_tt = content.get("legenda_tiktok", "")
    legenda_pin = content.get("legenda_pinterest", legenda_ig)  # usa IG como fallback

    hashtags = HASHTAGS.get(pilar, HASHTAGS["lifestyle"]) + " " + HASHTAGS["lifestyle2"]
    if hashtags not in legenda_ig:
        legenda_ig = legenda_ig + f"\n\n{hashtags} #auradecore #decoracaobrasileira"

    print(f"\n  {'─'*56}")
    if tipo == "reel":
        print(f"  SCRIPT REEL 30s:")
        print(f"  HOOK:    {content.get('hook', '')[:80]}")
        print(f"  CENA 1:  {content.get('cena_1', '')[:70]}")
        print(f"  CENA 2:  {content.get('cena_2', '')[:70]}")
        print(f"  CENA 3:  {content.get('cena_3', '')[:70]}")
        print(f"  CTA:     {content.get('cta', '')[:60]}")
        print(f"  MÚSICA:  {content.get('musica', '')}")
    elif tipo == "carrossel":
        capa = content.get("capa", {})
        print(f"  CARROSSEL 8 SLIDES:")
        print(f"  CAPA:    {capa.get('titulo', '')} | {capa.get('subtitulo', '')}")
        for slide in content.get("slides", []):
            print(f"  Slide {slide.get('numero', '')}: {slide.get('titulo', '')} — {slide.get('texto', '')[:50]}")
        print(f"  Slide 8: {content.get('cta_slide', '')[:60]}")
    print(f"  {'─'*56}")
    print(f"\n  📸 INSTAGRAM:\n  {legenda_ig[:250]}...")
    print(f"\n  📘 FACEBOOK Comercial:\n  {legenda_fb[:200]}...")
    print(f"\n  👤 FACEBOOK Pessoal @auras.decore:\n  {legenda_fb_pessoal[:200]}...")
    print(f"\n  📌 PINTEREST @auradecoracao:\n  {legenda_pin[:150]}...")
    print(f"\n  🎵 TIKTOK @decore.aura:\n  {legenda_tt[:150]}")

    # ── 4. Salvar JSON ──
    post_data = {
        "date": today,
        "tipo": tipo,
        "pilar": pilar,
        "tema": tema,
        "produto": produto,
        "content": content,
        "captions": {
            "instagram":       legenda_ig,
            "facebook":        legenda_fb,
            "facebook_pessoal": legenda_fb_pessoal,
            "tiktok":          legenda_tt,
            "pinterest":       legenda_pin,
            "stories_text":    content.get("stories_text", ""),
        },
        "image": img,
        "image_prompt": img_prompt,
        "instagram":         legenda_ig,
        "facebook":          legenda_fb,
        "facebook_pessoal":  legenda_fb_pessoal,
        "tiktok":            legenda_tt,
        "pinterest":         legenda_pin,
        "gerado_em": datetime.now().isoformat(),
    }
    saved = salvar_post(post_data, today)
    print(f"\n  ✅ Salvo: {pathlib.Path(saved).name}")

    if dry_run:
        print(f"\n  [DRY RUN] Sem publicação.")
        print("=" * 62)
        return

    # ── 5. Publicar em todos os 5 canais ──
    print(f"\n  [4/4] Publicando em 5 canais...")
    image_url = img.get("url", "")
    produto_url = produto.get("url", STORE_URL)

    # Canal 1: Instagram @auradecore (Graph API)
    # Carrossel: mínimo 2 imagens obrigatório — usa Shopify CDN + Pollinations extras
    if tipo == "carrossel" and len(carrossel_urls) >= 2:
        print(f"  📸 Instagram: publicando CARROSSEL ({len(carrossel_urls)} slides)...")
        ig = postar_instagram_carrossel(legenda_ig, carrossel_urls)
        if ig["ok"]:
            print(f"  ✅ Instagram @auradecore — CARROSSEL {ig.get('slides')} slides — ID: {ig.get('id')}")
        else:
            print(f"  ❌ Instagram Carrossel: {ig['msg']}")
    else:
        ig = postar_instagram(legenda_ig, image_url)
        if ig["ok"]:
            print(f"  ✅ Instagram @auradecore — ID: {ig.get('id')}")
        else:
            print(f"  ❌ Instagram: {ig['msg']}")

    # Canal 2: Facebook Comercial @auradecore (Graph API)
    fb = postar_facebook(legenda_fb, image_url)
    if fb["ok"]:
        print(f"  ✅ Facebook Comercial @auradecore — ID: {fb.get('id')}")
    else:
        print(f"  ❌ Facebook Comercial: {fb['msg']}")

    # Canal 3: Facebook Pessoal @auras.decore (Chrome MCP)
    if FB_PESSOAL_CHROME_ENABLED:
        fbp = postar_facebook_pessoal(legenda_fb_pessoal, image_url)
        if fbp["ok"]:
            print(f"  ✅ Facebook Pessoal @auras.decore — {fbp['msg']}")
        else:
            print(f"  ❌ Facebook Pessoal: {fbp['msg']}")
    else:
        print(f"  ⏭️  Facebook Pessoal: desabilitado (FB_PESSOAL_CHROME_ENABLED=false)")

    # Canal 4: Pinterest @auradecoracao (API v5)
    pin = postar_pinterest(legenda_pin, image_url, link=produto_url)
    if pin["ok"]:
        print(f"  ✅ Pinterest @auradecoracao — Pin ID: {pin.get('id')}")
    else:
        print(f"  ⏭️  Pinterest: {pin['msg']}")

    # Canal 5: TikTok @decore.aura (Chrome MCP — requer vídeo)
    if TIKTOK_CHROME_ENABLED and tiktok_video:
        print(f"\n  🎵 TikTok Chrome — {pathlib.Path(tiktok_video).name}")
        tt = postar_tiktok_chrome(tiktok_video, legenda_tt)
        print(f"  {'✅' if tt['ok'] else '❌'} TikTok @decore.aura: {tt['msg']}")
    elif TIKTOK_CHROME_ENABLED:
        print(f"  ⏭️  TikTok: passe --tiktok-video para publicar automaticamente")
    else:
        print(f"  ⏭️  TikTok: desabilitado (TIKTOK_CHROME_ENABLED=false)")

    # ── Marcar posts Canva do dia como publicados ──
    if canva_posts:
        canal_ids = {
            "instagram":    ig.get("id", "") if ig["ok"] else "",
            "facebook":     fb.get("id", "") if fb["ok"] else "",
            "facebook_pessoal": "",
            "pinterest":    pin.get("id", "") if pin["ok"] else "",
        }
        for cp in canva_posts:
            pid = canal_ids.get(cp.get("canal", ""), "")
            _marcar_canva_publicado(cp["id"], post_id=pid)

    print("\n" + "=" * 62)
    print("  CONCLUÍDO — 5 CANAIS PROCESSADOS")
    print("=" * 62)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aura Decore Social Agent — Conteúdo Editorial")
    parser.add_argument("--dry-run",       action="store_true", help="Preview sem publicar")
    parser.add_argument("--date",          default="",          help="Data alvo YYYY-MM-DD (padrão: hoje)")
    parser.add_argument("--tiktok-video",  default="",          help="Vídeo .mp4 para TikTok")
    parser.add_argument("--schedule",      action="store_true", help="Mostrar config agendador")
    args = parser.parse_args()

    if args.schedule:
        print("""
Agendamento (Railway cron):
  [cron.social-post]
  schedule = "0 12 * * *"  # 12:00 UTC = 09:00 Brasília
  command = "python backend/social_agent.py"

Agendamento (Windows Task Scheduler):
  schtasks /create /tn "AuraDecore-Social" /tr "python C:\\...\\backend\\social_agent.py" /sc daily /st 09:00
""")
    else:
        main(dry_run=args.dry_run, date_str=args.date, tiktok_video=args.tiktok_video)
