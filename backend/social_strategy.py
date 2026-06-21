# social_strategy.py — Aura Decore · Motor de Redes Sociais
# Plano Avançado: 5 pilares, calendário semanal, geração + publicação automática

import asyncio
import os
import json
import pathlib
from datetime import datetime, timedelta
from typing import Optional

import httpx
from dotenv import load_dotenv

_ENV = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV, override=True)

FB_PAGE_ID    = os.getenv("FB_PAGE_ID", "")
FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN", "")
IG_USER_ID    = os.getenv("IG_USER_ID", "")
GROQ_KEY      = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

STORE_URL = "https://auradecore.com.br"
IG_HANDLE = "@auras.decore"
BRAND_VOICE = (
    "Use linguagem calma, poética e minimalista. "
    "Exemplo: 'Um canto que respira.\nMenos coisas. Mais presença.\nAura Decore.' "
    "Nunca use exclamações excessivas, emojis em excesso ou linguagem de vendas agressiva. "
    "Tom: sereno, sofisticado, acolhedor, aspiracional."
)

# ── 5 Pilares de Conteúdo ─────────────────────────────────────────────────────
CONTENT_PILLARS = {
    "lifestyle":  {"pct": 40, "desc": "Ambientes, harmonia, calmaria, espaços Japandi"},
    "produto":    {"pct": 30, "desc": "Fotos e vídeos premium dos produtos em cena"},
    "educacao":   {"pct": 15, "desc": "Dicas de decoração, significado Japandi, wabi-sabi"},
    "bastidores": {"pct": 10, "desc": "Valores da marca, processo, cuidados com o produto"},
    "prova":      {"pct":  5, "desc": "Depoimentos, antes/depois, clientes reais (UGC)"},
}

# ── Calendário Semanal ────────────────────────────────────────────────────────
# weekday: 0=seg, 1=ter, 2=qua, 3=qui, 4=sex, 5=sab, 6=dom
WEEKLY_CALENDAR = {
    0: [  # Segunda
        {"hora": "09:00", "tipo": "reel",     "pilar": "educacao",   "tema": "dica Japandi ou transformação de ambiente", "plataformas": ["instagram", "facebook"]},
        {"hora": "20:00", "tipo": "story",    "pilar": "bastidores", "tema": "série bastidores da semana",                "plataformas": ["instagram"]},
    ],
    1: [  # Terça
        {"hora": "18:00", "tipo": "carrossel","pilar": "produto",    "tema": "produto em foco + benefícios + CTA",        "plataformas": ["instagram", "facebook"]},
    ],
    2: [  # Quarta
        {"hora": "09:00", "tipo": "reel",     "pilar": "produto",    "tema": "ASMR montagem elegante ou unboxing",        "plataformas": ["instagram", "facebook"]},
        {"hora": "20:00", "tipo": "story",    "pilar": "lifestyle",  "tema": "poll: qual ambiente você quer ver?",        "plataformas": ["instagram"]},
    ],
    3: [  # Quinta
        {"hora": "18:00", "tipo": "foto",     "pilar": "lifestyle",  "tema": "foto única + texto inspirador minimalista", "plataformas": ["instagram", "facebook"]},
    ],
    4: [  # Sexta
        {"hora": "18:00", "tipo": "carrossel","pilar": "lifestyle",  "tema": "lookbook ou ambiente completo Japandi",     "plataformas": ["instagram", "facebook"]},
    ],
    5: [  # Sábado
        {"hora": "10:00", "tipo": "reel",     "pilar": "lifestyle",  "tema": "vídeo lifestyle calmo e aspiracional",      "plataformas": ["instagram", "facebook"]},
        {"hora": "20:00", "tipo": "story",    "pilar": "prova",      "tema": "depoimento de cliente",                     "plataformas": ["instagram"]},
    ],
    6: [  # Domingo
        {"hora": "10:00", "tipo": "foto",     "pilar": "educacao",   "tema": "post reflexivo + copy poético",             "plataformas": ["instagram", "facebook"]},
        {"hora": "19:00", "tipo": "carrossel","pilar": "lifestyle",  "tema": "carrossel de inspiração Japandi",           "plataformas": ["instagram", "facebook"]},
        {"hora": "21:00", "tipo": "story",    "pilar": "bastidores", "tema": "recap da semana + prévia do conteúdo",      "plataformas": ["instagram"]},
    ],
}

# Hashtags por pilar
HASHTAG_BANKS = {
    "lifestyle":  "#Japandi #DecoracaoJapandi #CasaComAlma #LarAconchegante #EstiloJapandi #MinimalismoNatural #CasaMinimalista #InterioresJapandi #DecorBrasil #AmbienteSereno",
    "produto":    "#AuraDecore #DecorMinimalista #VasoCeramica #DifusorAromas #DecoracaoNatural #ProdutoJapandi #CasaDecorada #DetalhesQueImportam #DecorPremium #PresenteDeDecoracao",
    "educacao":   "#WabiSabi #DicasDeDecoracao #DesignDeInteriores #DecorInspiracao #EstiloDeVida #MinimalismoConsciente #DesignMinimalista #ArquiteturaDeInteriores #DecorConsciente #VidaSimples",
    "bastidores": "#BastidoresDaMarca #ProcessoCriativo #AuraDecore #MarcaBrasileira #FeitoComAmor #HistoriaDaMarca #ValoResDaMarca #TransparenciaMarca",
    "prova":      "#ClienteSatisfeito #DepoimentoReal #AntesEDepois #TransformacaoDeAmbiente #UGC #ComunidadeAura #ClienteAura #ResultadoReal",
}

# ── Geração de conteúdo via LLM ───────────────────────────────────────────────
async def _llm(system: str, user: str, max_tokens: int = 500) -> str:
    if GROQ_KEY:
        try:
            from groq import Groq
            g = Groq(api_key=GROQ_KEY, timeout=15)
            r = g.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=max_tokens, temperature=0.8,
            )
            return r.choices[0].message.content.strip()
        except Exception:
            pass
    if ANTHROPIC_KEY:
        try:
            from anthropic import Anthropic
            a = Anthropic(api_key=ANTHROPIC_KEY)
            r = a.messages.create(
                model="claude-3-5-sonnet-20240620", max_tokens=max_tokens,
                system=system, messages=[{"role": "user", "content": user}],
            )
            return r.content[0].text.strip()
        except Exception:
            pass
    return ""

async def gerar_copy(tipo: str, pilar: str, tema: str, produto: str = "") -> dict:
    """Gera copy completo: legenda + hashtags + roteiro (se reel)."""
    pilar_desc = CONTENT_PILLARS.get(pilar, {}).get("desc", "")
    hashtags   = HASHTAG_BANKS.get(pilar, "")

    if tipo == "reel":
        system = (
            "Você é NOX + VERA, dupla criativa da Aura Decore. "
            f"{BRAND_VOICE} "
            "Crie roteiro de Reel de 30s para Instagram: "
            "HOOK (0-3s — pergunta ou cena impactante), "
            "DESENVOLVIMENTO (3-25s — 3 cenas rápidas mostrando produto/ambiente), "
            "CTA (25-30s — convidar para visitar a loja). "
            "Depois do roteiro, escreva a LEGENDA completa (máx 150 palavras) e os HASHTAGS."
        )
        prompt = f"Tema do Reel: {tema}. Pilar: {pilar_desc}. Produto em destaque: {produto or 'escolha o mais adequado ao tema'}."
    elif tipo == "carrossel":
        system = (
            "Você é NOX + VERA, dupla criativa da Aura Decore. "
            f"{BRAND_VOICE} "
            "Crie um Carrossel de 8 slides para Instagram/Facebook: "
            "Slide 1: CAPA impactante com título. "
            "Slides 2-7: desenvolvimento do tema (1 ideia por slide, frase curta + descrição). "
            "Slide 8: CTA para auradecore.com.br. "
            "Depois, escreva a LEGENDA completa e HASHTAGS."
        )
        prompt = f"Tema do Carrossel: {tema}. Pilar: {pilar_desc}. Produto/foco: {produto or 'decoração Japandi em geral'}."
    else:  # foto / story
        system = (
            "Você é VERA, copywriter da Aura Decore. "
            f"{BRAND_VOICE} "
            "Crie uma legenda poética e minimalista (máx 80 palavras) para foto/story no Instagram. "
            "Inclua 1 CTA sutil no final e os HASHTAGS separados."
        )
        prompt = f"Tipo: {tipo}. Tema: {tema}. Pilar: {pilar_desc}. Produto: {produto or ''}."

    texto = await _llm(system, prompt, max_tokens=600)

    return {
        "tipo":      tipo,
        "pilar":     pilar,
        "tema":      tema,
        "texto":     texto,
        "hashtags":  hashtags,
        "gerado_em": datetime.now().isoformat(),
    }

async def gerar_imagem_prompt(tipo: str, pilar: str, tema: str) -> str:
    """Gera prompt de imagem IA para Pollinations via ARTE/LUNA."""
    system = (
        "Você é LUNA + ARTE, designers da Aura Decore. "
        "Gere um prompt de imagem IA (em inglês) para Pollinations.ai (modelo flux). "
        "Estilo obrigatório: japandi, wabi-sabi, minimal, natural light, earth tones (#B8793A, #F5F0EB), "
        "wood texture, linen, ceramic, calm atmosphere, professional product photography. "
        "Máximo 80 palavras. Apenas o prompt, sem explicações."
    )
    return await _llm(system, f"Tipo de post: {tipo}. Tema: {tema}. Pilar: {pilar}.", max_tokens=120)

async def gerar_imagem_url(prompt: str, width: int = 1080, height: int = 1080) -> str:
    """Gera imagem via Pollinations.ai (gratuito, sem chave)."""
    import urllib.parse
    encoded = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&model=flux&nologo=true&seed={hash(prompt) % 99999}"

# ── Publicação Facebook ───────────────────────────────────────────────────────
async def publicar_facebook(mensagem: str, imagem_url: str = "") -> dict:
    if not FB_PAGE_TOKEN or not FB_PAGE_ID:
        return {"status": "not_configured", "plataforma": "facebook"}
    try:
        async with httpx.AsyncClient(timeout=20) as hc:
            if imagem_url:
                r = await hc.post(
                    f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos",
                    data={"url": imagem_url, "caption": mensagem, "access_token": FB_PAGE_TOKEN},
                )
            else:
                r = await hc.post(
                    f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/feed",
                    data={"message": mensagem, "access_token": FB_PAGE_TOKEN},
                )
            resp = r.json()
            if "id" in resp:
                return {"status": "publicado", "plataforma": "facebook", "post_id": resp["id"]}
            return {"status": "erro", "plataforma": "facebook", "detalhe": resp}
    except Exception as e:
        return {"status": "erro", "plataforma": "facebook", "detalhe": str(e)}

# ── Publicação Instagram (via Graph API) ─────────────────────────────────────
async def publicar_instagram(mensagem: str, imagem_url: str) -> dict:
    if not FB_PAGE_TOKEN or not IG_USER_ID or not imagem_url:
        return {"status": "not_configured", "plataforma": "instagram"}
    try:
        async with httpx.AsyncClient(timeout=30) as hc:
            # Etapa 1: criar container de mídia
            r1 = await hc.post(
                f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media",
                data={"image_url": imagem_url, "caption": mensagem, "access_token": FB_PAGE_TOKEN},
            )
            media = r1.json()
            if "id" not in media:
                return {"status": "erro", "plataforma": "instagram", "etapa": "media", "detalhe": media}
            # Etapa 2: publicar
            r2 = await hc.post(
                f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish",
                data={"creation_id": media["id"], "access_token": FB_PAGE_TOKEN},
            )
            pub = r2.json()
            if "id" in pub:
                return {"status": "publicado", "plataforma": "instagram", "post_id": pub["id"]}
            return {"status": "erro", "plataforma": "instagram", "etapa": "publish", "detalhe": pub}
    except Exception as e:
        return {"status": "erro", "plataforma": "instagram", "detalhe": str(e)}

# ── Executor de post completo ─────────────────────────────────────────────────
async def executar_post(slot: dict, produto: str = "", salvar_vault: bool = True) -> dict:
    """
    Executa um slot do calendário semanal completo:
    gera copy → gera imagem → publica em todas as plataformas do slot.
    """
    tipo       = slot["tipo"]
    pilar      = slot["pilar"]
    tema       = slot["tema"]
    plataformas = slot.get("plataformas", ["instagram", "facebook"])

    # 1. Gera copy
    copy = await gerar_copy(tipo, pilar, tema, produto)
    legenda_completa = copy["texto"] + "\n\n" + copy["hashtags"]

    # 2. Gera imagem
    img_prompt = await gerar_imagem_prompt(tipo, pilar, tema)
    w, h = (1080, 1920) if tipo == "reel" else (1080, 1080)
    imagem_url = await gerar_imagem_url(img_prompt, w, h)

    resultados = []

    # 3. Publica nas plataformas
    for plat in plataformas:
        if tipo == "story":
            # Stories não publicamos via API automática — salva para publicação manual
            resultados.append({"status": "salvo_para_stories", "plataforma": plat})
            continue
        if plat == "facebook":
            r = await publicar_facebook(legenda_completa, imagem_url)
        elif plat == "instagram":
            r = await publicar_instagram(legenda_completa, imagem_url)
        else:
            r = {"status": "plataforma_desconhecida", "plataforma": plat}
        resultados.append(r)

    # 4. Salva no vault
    resultado_final = {
        "slot":       slot,
        "copy":       copy,
        "imagem_url": imagem_url,
        "img_prompt": img_prompt,
        "publicacoes": resultados,
        "executado_em": datetime.now().isoformat(),
    }

    if salvar_vault:
        _salvar_post_vault(resultado_final)

    # 5. Envia notificação automática via WhatsApp para Eduardo Marques
    try:
        from whatsapp_agent import send_whatsapp_message
        phone_raw = os.getenv("EDUARDO_PHONE", "")
        if phone_raw:
            phones = [p.strip() for p in phone_raw.split(",") if p.strip()]
            if phones:
                target_phone = phones[0]
                data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                status_geral = "✅ Sucesso"
                falhas = []
                status_plataformas = []

                for r in resultados:
                    plat_name = r.get("plataforma", "desconhecida").title()
                    status = r.get("status")
                    if status == "publicado":
                        status_plataformas.append(f"- {plat_name}: ✅ Sucesso (ID: {r.get('post_id')})")
                    elif status == "salvo_para_stories":
                        status_plataformas.append(f"- {plat_name}: 📲 Salvo para stories (publicação manual)")
                    else:
                        status_plataformas.append(f"- {plat_name}: ❌ Erro: {r.get('detalhe', 'Desconhecido')}")
                        falhas.append(f"{plat_name}: {r.get('detalhe', 'Desconhecido')}")
                        status_geral = "⚠️ Concluído com alertas/erros"

                legenda = copy.get("texto", "")
                resumo_legenda = legenda[:120] + "..." if len(legenda) > 120 else legenda
                erros_section = ""
                sugestao = "Tudo pronto e rodando perfeitamente! 🌿"
                if falhas:
                    erros_section = "\n⚠️ *Erros / Problemas:*\n" + "\n".join(f"• {f}" for f in falhas) + "\n"
                    sugestao = "Revisar logs do servidor para corrigir os erros nas plataformas com falha. 🛠️"

                report_msg = (
                    f"🌿 *Relatório de Publicação — Aura Decore* 🌿\n\n"
                    f"Status: {status_geral}\n"
                    f"📅 Horário: {data_hora}\n\n"
                    f"📱 *Plataformas:*\n"
                    + "\n".join(status_plataformas) + "\n"
                    f"{erros_section}\n"
                    f"📝 *Resumo do Conteúdo:*\n"
                    f"• Tipo: {tipo.upper()}\n"
                    f"• Pilar: {pilar}\n"
                    f"• Tema: {tema}\n"
                    f"• Produto: {produto or 'Geral'}\n"
                    f"• Legenda: \"{resumo_legenda}\"\n\n"
                    f"💡 *Sugestão de Ação:*\n{sugestao}"
                )

                # Cria uma task assíncrona para não travar o fluxo principal
                asyncio.create_task(send_whatsapp_message(target_phone, report_msg))
                print(f"[SOCIAL] Notificação WhatsApp enviada para Eduardo ({target_phone})")
    except Exception as e_notif:
        print(f"[WARN] Erro ao enviar notificação WhatsApp de post: {e_notif}")

    return resultado_final

def _salvar_post_vault(resultado: dict):
    """Salva post executado no vault Obsidian."""
    vault = os.getenv("OBSIDIAN_VAULT", r"C:\Users\erick\AURA-decor-vault")
    posts_dir = pathlib.Path(vault) / "Social" / "Posts"
    posts_dir.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d-%H%M")
    tipo = resultado["slot"].get("tipo", "post")
    pilar = resultado["slot"].get("pilar", "")
    fname = posts_dir / f"post-{ts}-{tipo}-{pilar}.json"
    fname.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")

# ── Gerador do próximo post do calendário ────────────────────────────────────
def proximo_slot() -> Optional[dict]:
    """Retorna o próximo slot do calendário baseado no dia/hora atual."""
    agora    = datetime.now()
    weekday  = agora.weekday()
    hora_str = agora.strftime("%H:%M")

    slots_hoje = WEEKLY_CALENDAR.get(weekday, [])
    for slot in slots_hoje:
        if slot["hora"] >= hora_str:
            return {**slot, "data": agora.strftime("%Y-%m-%d"), "dia": ["seg","ter","qua","qui","sex","sab","dom"][weekday]}

    # Próximo dia
    for delta in range(1, 8):
        prox = (weekday + delta) % 7
        slots = WEEKLY_CALENDAR.get(prox, [])
        if slots:
            data = (agora + timedelta(days=delta)).strftime("%Y-%m-%d")
            dia  = ["seg","ter","qua","qui","sex","sab","dom"][prox]
            return {**slots[0], "data": data, "dia": dia}
    return None

def slots_da_semana() -> list:
    """Retorna todos os slots da semana com dia e data calculada."""
    agora   = datetime.now()
    weekday = agora.weekday()
    todos   = []
    dias    = ["seg","ter","qua","qui","sex","sab","dom"]
    for delta in range(7):
        d = (weekday + delta) % 7
        data = (agora + timedelta(days=delta)).strftime("%Y-%m-%d")
        for slot in WEEKLY_CALENDAR.get(d, []):
            todos.append({**slot, "data": data, "dia": dias[d]})
    return todos
