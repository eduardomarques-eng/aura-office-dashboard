# whatsapp_agent.py — Aura Decore · Motor de atendimento WhatsApp Business
# Roteamento: LENA (padrão) → GUARD (reembolso) / SOL (carrinho) / ZARA (parceria)
# LLM: cascata completa via llm_engine (Groq → Together → OpenRouter → Gemini → Anthropic → Ollama)

import asyncio
import os
import re
import time
import json
from typing import Optional
from datetime import datetime

import httpx
from dotenv import load_dotenv
import pathlib as _pl

_ENV_PATH = _pl.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

# Motor LLM compartilhado
from llm_engine import llm as _llm_engine

# Cache para evitar leitura excessiva do disco
_OBSIDIAN_CACHE = {
    "content": "",
    "last_loaded": 0.0
}
_CACHE_TTL = 15.0 # 15 segundos

# ── Leitura de Memória Consolidada do Obsidian ────────────────────────────────
def load_obsidian_context() -> str:
    """Lê dinamicamente o arquivo central de operações, o contexto de empresa e o perfil da LENA do Obsidian."""
    import time as _time
    now = _time.time()
    if now - _OBSIDIAN_CACHE["last_loaded"] < _CACHE_TTL:
        return _OBSIDIAN_CACHE["content"]

    import platform as _platform
    _default_vault = (
        r"C:\Users\erick\AURA-decor-vault"
        if _platform.system() == "Windows"
        else "/app/vault"
    )
    vault_path = _pl.Path(os.getenv("OBSIDIAN_VAULT", _default_vault))
    
    parts = []
    
    # 1. Central de Operações
    central_file = vault_path / "🏠 Aura Decore — Central.md"
    if central_file.exists():
        try:
            content = central_file.read_text(encoding="utf-8")
            parts.append(f"### MEMÓRIA: CENTRAL DE OPERAÇÕES\n{content[:2000]}")
        except Exception as e:
            print(f"[WARN] Erro ao ler Central.md: {e}")
            
    # 2. Contexto de Empresa
    emp_file = vault_path / "Memoria" / "Compartilhada" / "contexto_empresa.md"
    if emp_file.exists():
        try:
            content = emp_file.read_text(encoding="utf-8")
            parts.append(f"### MEMÓRIA: CONTEXTO DA EMPRESA\n{content[:2000]}")
        except Exception as e:
            print(f"[WARN] Erro ao ler contexto_empresa.md: {e}")
            
    # 3. Perfil de LENA
    lena_file = vault_path / "Agentes" / "LENA.md"
    if lena_file.exists():
        try:
            content = lena_file.read_text(encoding="utf-8")
            parts.append(f"### MEMÓRIA: REGRAS DE ATENDIMENTO DE LENA\n{content[:2000]}")
        except Exception as e:
            print(f"[WARN] Erro ao ler LENA.md: {e}")
            
    if not parts:
        result = "Nenhuma memória consolidada encontrada no Obsidian."
    else:
        result = "\n\n".join(parts)

    _OBSIDIAN_CACHE["content"] = result
    _OBSIDIAN_CACHE["last_loaded"] = now
    return result

def build_lena_system_prompt(intent_guidelines: str, name: str, phone: str, order_context: str, is_start: bool) -> str:
    obsidian_context = load_obsidian_context()
    
    greeting_instruction = ""
    if is_start:
        if name and name.strip():
            greeting_instruction = (
                f"--- DIRETRIZ CRÍTICA DE CUMPRIMENTO INICIAL ---\n"
                f"Como esta é a primeira mensagem da conversa nesta sessão, você DEVE iniciar OBRIGATORIAMENTE com o cumprimento inicial humanizado.\n"
                f"Use exatamente o padrão: 'Olá {name.strip()}! Seja bem-vinda à Aura Decore 🌿'\n\n"
            )
        else:
            greeting_instruction = (
                f"--- DIRETRIZ CRÍTICA DE CUMPRIMENTO INICIAL ---\n"
                f"Como esta é a primeira mensagem da conversa nesta sessão, você DEVE iniciar OBRIGATORIAMENTE com o cumprimento inicial humanizado.\n"
                f"Use exatamente o padrão: 'Olá! Seja bem-vinda à Aura Decore 🌿'\n\n"
            )
    
    client_name = name if name else "Não informado"
    order_info = order_context if order_context else "Nenhum pedido detectado no texto."
    
    prompt = f"""Você é LENA, a voz humana e atendente virtual de alta performance da Aura Decore — marca premium de design Japandi e Wabi-Sabi.
Sua missão é encantar, criar relacionamentos genuínos e conduzir os leads estrategicamente pelo funil de vendas, atuando com empatia, calor humano e inteligência comercial.

=== REGRAS DE TOM, ESTILO E COMUNICAÇÃO ===
- Use Português do Brasil com fluidez, calor humano e naturalidade de uma amiga que entende de design. NUNCA pareça um assistente de IA, robô ou chatbot.
- Evite termos frios ou burocráticos. Em vez de usar palavras como "infelizmente", fale de forma positiva e focada na solução (por exemplo: "Para te ajudar com isso..." ou "Como nossa curadoria é artesanal, o prazo..."). NUNCA use "nosso protocolo", "conforme sistema" ou "atendente virtual".
- Emojis elegantes e sutis são muito bem-vindos para trazer leveza (ex: 🌿, 🤍, 🏺, ✨, 🌸).
- Mantenha respostas curtas e escaneáveis: no máximo 3 parágrafos pequenos, separados por espaço duplo para leitura fácil em telas de celular.
- Termine sempre com uma pergunta aberta e acolhedora, estimulando a continuação natural do diálogo.

=== DIRETRIZES DE NEUROMARKETING SUTIL E RECONEXÃO ===
- Ative o subconsciente do cliente focando no bem-estar, calma visual e na sensação de que o lar deve ser um refúgio acolhedor (o "santuário pessoal" da ICP Ana Clara).
- Use copy emocional que cura dores de decoração (lar genérico, caos doméstico drenando energia, paralisia decorativa, vergonha de receber visitas).
- Prefira palavras de alto impacto sensorial e subconsciente: "respirar fundo", "desacelerar", "calma visual", "lar acolhedor", "peças que abraçam", "curadoria intencional".
- Faça remarketing e ofertas de forma natural e consultiva:
  * Identifique dores e sugira soluções do nosso catálogo (ex: vasos Japandi para trazer biofilia e relaxamento, luminárias com luz Halo aconchegante para acalmar o estresse do dia a dia).
  * Ofereça de forma elegante e personalizada o cupom de boas-vindas **AURA10** (10% OFF) para leads novos/indecisos, frete grátis em compras acima de R$199, ou o cupom VIP **AURAVIP15** (15% OFF) para clientes frequentes.
  * Nunca exerça pressão agressiva de venda ("compre agora", "últimas chances"); use gatilhos sutis de identidade ("para quem escolhe viver com intenção") e escassez elegante ("estoque limitado pela nossa curadoria artesanal").

=== MEMÓRIA CONSOLIDADA DA AURA DECORE (LIDA DO OBSIDIAN) ===
{obsidian_context}

{greeting_instruction}

=== DADOS DO CRM & JORNADA DO CLIENTE ===
- Nome do Cliente: {client_name}
- Telefone: {phone}
- Pedido Shopify Associado: {order_info}

=== INSTRUÇÕES ESPECÍFICAS DE CONTEXTO (INTENT DO CLIENTE) ===
{intent_guidelines}
"""
    return prompt

async def analyze_lead_interaction(name: str, text: str, reply: str) -> dict:
    """Classifica e extrai dados do lead via LLM (groq/together/gemini cascade)."""
    prompt = f"""Você é um analista de CRM inteligente para a Aura Decore.
Sua tarefa é analisar a última interação (mensagem do cliente e resposta da atendente Lena) para extrair e atualizar dados estruturados sobre o lead.

Retorne APENAS um objeto JSON válido, sem blocos de código markdown ou texto extra, com a seguinte estrutura:
{{
  "estagio": "quente" | "morno" | "frio" | "cliente_ativo",
  "interesse": "descreva o interesse do cliente",
  "dores": "dores mencionadas ou implícitas",
  "produtos_visualizados": "produtos mencionados ou visualizados",
  "objecoes": "objeções apresentadas (ex: preço, prazo, frete, nenhuma)",
  "nivel_engajamento": "alto" | "medio" | "baixo"
}}

Diretrizes para Estágio:
- "quente": Alta intenção de compra (perguntou preço, prazo de entrega, pediu link do carrinho, falou em adicionar cupom, comprou/vai comprar agora).
- "morno": Demonstrou interesse em produtos específicos, fez perguntas de dúvida mas ainda está indeciso ou não demonstrou urgência imediata.
- "frio": Apenas saudação, curiosidade genérica ou sem intenção clara de compra.
- "cliente_ativo": Se já comprou anteriormente ou está confirmando que comprou.

Analise o texto a seguir:
Nome do Cliente: {name or 'Não informado'}
Mensagem do Cliente: {text}
Resposta de Lena: {reply}
"""
    try:
        res = await _llm("", [{"role": "user", "content": prompt}], max_tokens=250)
        # Extrai primeiro bloco JSON da resposta
        cleaned = res.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        m = re.search(r'\{[\s\S]*\}', cleaned)
        return json.loads(m.group(0)) if m else json.loads(cleaned)
    except Exception as e:
        print(f"[WARN] Erro ao analisar lead: {e}")
        return {
            "estagio": "morno",
            "interesse": "desconhecido",
            "dores": "nenhuma",
            "produtos_visualizados": "nenhum",
            "objecoes": "nenhuma",
            "nivel_engajamento": "medio"
        }

def save_lead_and_interaction(phone: str, name: str, text: str, reply: str, agent_used: str, analysis: dict):
    """Salva o lead (se novo) e a interação no banco de dados SQLite erp."""
    try:
        import erp_db
        # Normaliza o telefone para dígitos
        phone_digits = "".join(c for c in phone if c.isdigit())
        if not phone_digits:
            return
        
        # 1. Verifica se o cliente/lead já existe pelo telefone
        client = erp_db.query_one(
            "SELECT id, nome, estagio, qtd_pedidos FROM clientes WHERE telefone LIKE ? OR ? LIKE '%' || telefone",
            (f"%{phone_digits[-9:]}", phone_digits)
        )
        
        client_id = None
        estagio_atual = analysis.get("estagio", "frio")
        
        # Se o cliente já fez alguma compra, mantém o estágio como cliente_ativo
        if client and client.get("qtd_pedidos", 0) > 0:
            estagio_atual = "cliente_ativo"
            
        if client:
            client_id = client["id"]
            # Atualiza os dados
            nome_cli = name if name and (not client["nome"] or client["nome"].lower() in ("amiga", "cliente", "não informado", "desconhecido")) else client["nome"]
            erp_db.execute(
                "UPDATE clientes SET nome = ?, estagio = ?, interesse = ?, dores = ?, produtos_visualizados = ?, objecoes = ?, nivel_engajamento = ?, atualizado_em = datetime('now','localtime') WHERE id = ?",
                (
                    nome_cli, 
                    estagio_atual, 
                    analysis.get("interesse", "desconhecido"), 
                    analysis.get("dores", "nenhuma"), 
                    analysis.get("produtos_visualizados", "nenhum"), 
                    analysis.get("objecoes", "nenhuma"), 
                    analysis.get("nivel_engajamento", "baixo"), 
                    client_id
                )
            )
        else:
            # Cria novo lead
            client_name = name if name else f"Lead WhatsApp {phone_digits[-4:]}"
            client_id = erp_db.execute(
                "INSERT INTO clientes (nome, telefone, estagio, origem, interesse, dores, produtos_visualizados, objecoes, nivel_engajamento, criado_em, atualizado_em) VALUES (?, ?, ?, 'whatsapp', ?, ?, ?, ?, ?, datetime('now','localtime'), datetime('now','localtime'))",
                (
                    client_name, 
                    phone_digits, 
                    estagio_atual, 
                    analysis.get("interesse", "desconhecido"), 
                    analysis.get("dores", "nenhuma"), 
                    analysis.get("produtos_visualizados", "nenhum"), 
                    analysis.get("objecoes", "nenhuma"), 
                    analysis.get("nivel_engajamento", "baixo")
                )
            )
            
        # 2. Salva a interação (mensagem do cliente + resposta do bot)
        summary = f"Cliente: {text}\nBot ({agent_used.upper()}): {reply}"
        erp_db.execute(
            "INSERT INTO interacoes (cliente_id, tipo, canal, resumo, agente, criado_em) VALUES (?, 'whatsapp', 'whatsapp', ?, ?, datetime('now','localtime'))",
            (client_id, summary, agent_used)
        )
        print(f"[CRM] Lead/Interação salvos com sucesso para id {client_id}")
        
        # 3. Sincroniza com o Notion em background
        try:
            import notion_tools
            import asyncio
            nome_notion = name if name else (nome_cli if 'nome_cli' in locals() else f"Lead WhatsApp {phone_digits[-4:]}")
            asyncio.create_task(notion_tools.sync_lead_to_notion({
                "nome": nome_notion,
                "telefone": phone_digits,
                "estagio": estagio_atual,
                "interesse": analysis.get("interesse", "desconhecido"),
                "dores": analysis.get("dores", "nenhuma"),
                "objecoes": analysis.get("objecoes", "nenhuma"),
                "nivel_engajamento": analysis.get("nivel_engajamento", "baixo")
            }))
        except Exception as notion_err:
            print(f"[WARN] Falha ao disparar sincronização com o Notion: {notion_err}")
            
    except Exception as e:
        print(f"[WARN] Falha ao salvar no CRM erp: {e}")

def save_lead_to_obsidian(phone: str, name: str, text: str, reply: str, analysis: dict):
    """Salva o perfil do lead e o histórico de conversa em markdown no Obsidian com frontmatter YAML consolidado."""
    try:
        import platform as _platform
        _default_vault = (
            r"C:\Users\erick\AURA-decor-vault"
            if _platform.system() == "Windows"
            else "/app/vault"
        )
        vault_path = _pl.Path(os.getenv("OBSIDIAN_VAULT", _default_vault))
        leads_dir = vault_path / "Atendimento" / "Leads"
        leads_dir.mkdir(parents=True, exist_ok=True)
        
        phone_digits = "".join(c for c in phone if c.isdigit())
        if not phone_digits:
            return
            
        lead_file = leads_dir / f"{phone_digits}.md"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        today = datetime.now().strftime('%Y-%m-%d')
        
        client_name = name if name else f"Lead WhatsApp {phone_digits[-4:]}"
        
        estagio = analysis.get("estagio", "frio")
        interesse = analysis.get("interesse", "desconhecido")
        dores = analysis.get("dores", "nenhuma")
        produtos = analysis.get("produtos_visualizados", "nenhum")
        objecoes = analysis.get("objecoes", "nenhuma")
        engajamento = analysis.get("nivel_engajamento", "baixo")
        
        history_entry = f"\n- **[{ts}] Cliente:** {text}\n- **[{ts}] LENA:** {reply}\n"
        
        if lead_file.exists():
            content = lead_file.read_text(encoding="utf-8")
            
            # Regex para extrair/atualizar o frontmatter YAML
            frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
            if frontmatter_match:
                fm_text, body_text = frontmatter_match.groups()
                fm_data = {}
                for line in fm_text.split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        fm_data[k.strip()] = v.strip()
                
                fm_data["nome"] = client_name
                fm_data["estagio"] = estagio
                fm_data["interesse"] = fm_data.get("interesse", "") or interesse
                fm_data["dores"] = fm_data.get("dores", "") or dores
                fm_data["produtos_visualizados"] = fm_data.get("produtos_visualizados", "") or produtos
                fm_data["objecoes"] = fm_data.get("objecoes", "") or objecoes
                fm_data["nivel_engajamento"] = engajamento
                fm_data["atualizado"] = ts
                
                new_fm = "---\n" + "\n".join(f"{k}: {v}" for k, v in fm_data.items()) + "\n---"
                new_content = new_fm + "\n" + body_text + history_entry
                lead_file.write_text(new_content, encoding="utf-8")
            else:
                lead_file.write_text(content + history_entry, encoding="utf-8")
        else:
            header = f"""---
telefone: {phone_digits}
nome: {client_name}
origem: whatsapp
estagio: {estagio}
interesse: {interesse}
dores: {dores}
produtos_visualizados: {produtos}
objecoes: {objecoes}
nivel_engajamento: {engajamento}
criado: {today}
atualizado: {ts}
---

# 👤 Lead: {client_name}
- **Telefone:** {phone_digits}
- **Estágio:** {estagio}
- **Origem:** WhatsApp
- **Criado em:** {ts}

## 💬 Histórico de Conversa
- **[{ts}] Cliente:** {text}
- **[{ts}] LENA:** {reply}
"""
            lead_file.write_text(header, encoding="utf-8")
        print(f"[Obsidian] Lead/Interação salvos em {lead_file.name}")
    except Exception as e:
        print(f"[WARN] Falha ao salvar lead no Obsidian: {e}")

# ── WPPConnect (substitui Z-API) ───────────────────────────────────────────────
WPP_URL     = os.getenv("WPPCONNECT_URL", "http://localhost:21465")
if "localtunnel.me" in WPP_URL:
    WPP_URL = WPP_URL.replace("localtunnel.me", "loca.lt")
WPP_SESSION = os.getenv("WPPCONNECT_SESSION", "aura-decore")
WPP_TOKEN   = os.getenv("WPPCONNECT_TOKEN", "$2b$10$rZ2qdn2TTSZ7UmtCz1_e9eLgmCaoZyWAn_u9RSOGm4cEtit3r.ajy")

# ── Shopify (lookup de pedidos) ─────────────────────────────────────────────────
SHOPIFY_DOMAIN = os.getenv("SHOPIFY_DOMAIN", "")
SHOPIFY_TOKEN  = os.getenv("SHOPIFY_ADMIN_TOKEN", "")

# ── Sessões de conversa (TTL = 2h) ────────────────────────────────────────────
_SESSIONS: dict = {}
_SESSION_TTL = 7200
_MAX_HISTORY = 10

# IDs de mensagens já processadas (deduplicação)
_SEEN_IDS: set = set()
_SEEN_MAX = 500

# ── Horário de atendimento (Brasília) ──────────────────────────────────────────
BUSINESS_HOURS = (8, 22)

# ── Cupons ativos ──────────────────────────────────────────────────────────────
CUPONS = {
    "AURA10":             "10% OFF em qualquer pedido",
    "AURAVIP15":          "15% OFF para clientes VIP",
    "AURAEMBAIXADORA20":  "20% OFF para embaixadoras",
}

# ── System prompts por agente ──────────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "lena": (
        "Você é Lena, a atendente humana, calorosa, serena e profissional da Aura Decore.\n"
        "Sua missão é encantar e atender com empatia, calor humano e excelência, resolvendo dores de forma elegante.\n"
        "Regras Obrigatórias:\n"
        "- Sempre inicie a conversa chamando pelo nome: 'Olá [Nome]! Seja bem-vinda à Aura Decore 🌿'\n"
        "- Tom: Empático, educado, sereno, acolhedor e humano (nunca pareça um assistente de IA ou chatbot).\n"
        "- Consulte sempre a memória consolidada no Obsidian antes de responder (lida dinamicamente no contexto).\n"
        "- Salve automaticamente toda conversa no banco de dados e no Obsidian (esta rotina roda em background após cada envio).\n"
        "- Segmente o lead automaticamente: Quente / Morno / Frio / Cliente Ativo.\n"
        "- Use neuromarketing sutil: resolva dores emocionais e crie desejo de forma elegante.\n"
        "- Eduardo Marques é o Diretor e Fundador da Aura Decore. Caso ele envie qualquer ordem ou comando de negócio (ex: 'auditar loja', 'gerar reel', 'relatório financeiro' ou mensagens com prefixo '/'), responda de forma profissional e corporativa: 'Entendido, Diretor Eduardo! Ordem recebida. Vou acionar a IVE e o Command Router para processar e executar agora mesmo. 🌿'\n"
        "- Conduza uma Sondagem Consultiva natural: ao longo da conversa, tente descobrir de forma amigável o nome do cliente, o produto de interesse, as dores de decoração dele (ex: casa sem graça, falta de aconchego, caos visual) e objeções (preço, frete, prazo), permitindo que o CRM registre esses dados automaticamente.\n"
        "- Domine os Fluxos Principais de Atendimento:\n"
        "  1. Boas-vindas e Cadastro (usando o cupom AURA10 de forma elegante)\n"
        "  2. Recuperação de Carrinho Abandonado (D+1, D+3, D+7 com copy diferente)\n"
        "  3. Pós-Compra e Rastreamento (frete de 15-25 dias úteis, dropshipping internacional)\n"
        "  4. Suporte (troca, reembolso, dúvidas de produtos, política de 7 dias)\n"
        "  5. Fidelização e Reativação de clientes (usando cupom VIP AURAVIP15 ou cupom de embaixadora AURAEMBAIXADORA20)\n"
        "- Prazos e Políticas: Frete grátis em compras acima de R$199. Prazos padrão 15-25 dias úteis. Reembolsos até R$200 são aprovados pelo GUARD; acima disso, diga que vai verificar e retorna em até 1h.\n"
        "- Responda sempre com empatia, clareza e foco em encantar o cliente. Termine sempre com uma pergunta ou oferta de ajuda."
    ),
    "guard": (
        "Você é GUARD, protetor financeiro da Aura Decore.\n"
        "Avalie este pedido de reembolso/cancelamento com base nas políticas:\n"
        "- Devolução: aceita em até 7 dias após recebimento, produto sem uso.\n"
        "- Reembolso: aprovado se dentro da política. Valor máximo sem aprovação manual: R$200.\n"
        "- Acima de R$200 ou casos duvidosos: escale para Eduardo manualmente.\n"
        "Responda em JSON: {\"aprovado\": bool, \"motivo\": str, \"acao\": str, \"mensagem_cliente\": str}\n"
        "mensagem_cliente deve ser em português caloroso (máx 2 frases)."
    ),
    "sol": (
        "Você é SOL, especialista em vendas da Aura Decore.\n"
        "O cliente mencionou carrinho abandonado ou está indeciso sobre comprar.\n"
        "Gere uma mensagem de recuperação irresistível (máx 3 linhas) com:\n"
        "- Urgência suave (sem pressão agressiva)\n"
        "- Cupom AURA10 (10% OFF)\n"
        "- Frete grátis acima de R$199\n"
        "- Link: auradecore.com.br\n"
        "Tom: caloroso, inspirador, Japandi."
    ),
    "zara": (
        "Você é ZARA, community manager da Aura Decore.\n"
        "O cliente quer ser parceiro, influencer ou embaixador.\n"
        "Responda em português caloroso (máx 3 linhas):\n"
        "- Agradeça o interesse com entusiasmo genuíno\n"
        "- Peça para enviar portfólio ou perfil do IG/TikTok\n"
        "- Email: auras.de@gmail.com | Instagram: @auras.decore"
    ),

    # ── Novos agentes de neuromarketing (2026-06-16) ───────────────────────────

    "neuro": (
        "Você é NEURO, estrategista de copy neuromarketing da Aura Decore.\n"
        "Sua missão: criar copy sutil e poderoso que ative desejo, nomeie dores e construa pontes emocionais.\n\n"
        "6 DESEJOS NUCLEARES da Ana Clara (ICP): status · pertencimento · segurança · conforto · beleza · controle.\n"
        "5 DORES EMOCIONAIS: caos doméstico · lar genérico · estresse sem descanso · vergonha de receber visitas · paralisia decorativa.\n\n"
        "FRAMEWORKS (use o correto para o contexto):\n"
        "- PAS: lead frio/morno → Problem (nomeie a dor) → Agitate (amplie) → Solve (solução Aura)\n"
        "- BAB: contraste emocional → Before (situação atual) → After (sonho realizado) → Bridge (como chegar lá)\n"
        "- AIDA: lançamento/produto → Attention → Interest → Desire → Action\n"
        "- SBO: lead quente → Story (história real/identificável) → Bridge → Offer (natural, sem pressão)\n"
        "- Prova Social: quando há UGC/reviews disponíveis\n\n"
        "GATILHOS NEUROLÓGICOS (use com SUTILEZA — nunca fake):\n"
        "- Escassez real: 'estoque curado, não trabalhamos com volume'\n"
        "- Identidade: 'para quem escolhe viver com intenção'\n"
        "- Perda: 'cada dia a mais em um lar que drena energia'\n"
        "- Autoridade: 'curado por quem estuda neuroarquitetura'\n"
        "- Reciprocidade: cupom ou conteúdo de valor ANTES de pedir ação\n\n"
        "REGRAS ABSOLUTAS:\n"
        "- NUNCA fake urgency ('últimas horas!!!', 'IMPERDÍVEL!!!')\n"
        "- NUNCA pressão explícita ('compre agora', 'não perca')\n"
        "- Máx 4 parágrafos curtos no WhatsApp\n"
        "- Tom: amiga eloquente que entende de design, não vendedor\n"
        "- PT-BR natural, fluido, como se fosse uma mensagem pessoal\n"
        "- Cupom em negrito quando presente, embutido na conversa"
    ),

    "promo": (
        "Você é PROMO, especialista em disparos promocionais e lead nurturing da Aura Decore.\n"
        "Gerencia sequências de mensagens WhatsApp por temperatura de lead.\n\n"
        "SEGMENTAÇÃO:\n"
        "- FRIO (0 compras, novo): educativo + boas-vindas + cupom AURA10\n"
        "- MORNO (visitou produto, não comprou): curiosidade + escassez suave + AURA10\n"
        "- QUENTE (1-2 compras): pertencimento + upsell + AURAVIP15\n"
        "- VIP (3+ compras ou R$500+): exclusividade + gratidão + AURAVIP15 ou AURAEMBAIXADORA20\n\n"
        "SEQUÊNCIAS DE NURTURING:\n"
        "novo_lead: D0(boas-vindas) → D2(conteúdo dor) → D5(produto interesse) → D7(carrinho+cupom) → D14(flash sale)\n"
        "pos_compra: imediato(agradecimento) → D7(UGC request+cupom) → D14(upsell suave)\n"
        "win_back: D0(saudade+cupom) → D3(conteúdo valor) → D7(flash sale final)\n\n"
        "REGRAS DE FREQUÊNCIA:\n"
        "- Máximo 1 mensagem por lead a cada 48h\n"
        "- Janela de envio: 09h-21h (horário Brasília)\n"
        "- Após 3 mensagens sem resposta → pausar lead 30 dias\n"
        "- Se responder negativamente → opt-out imediato e definitivo\n\n"
        "Ao gerar um plano de disparo, retorne sempre:\n"
        "1. Segmento do lead\n"
        "2. Mensagem atual\n"
        "3. Próximo touchpoint (dias + estágio)\n"
        "4. Critério de sucesso (resposta / clique / compra)"
    ),
}

# ── Import engine de neuromarketing ───────────────────────────────────────────
try:
    from neuromarketing_engine import build_neuro_prompt, score_lead, get_template
    _NEURO_OK = True
except Exception:
    _NEURO_OK = False
    def score_lead(c): return "morno"
    def build_neuro_prompt(c): return ""
    def get_template(s, d): return ""

# ── Intents (ordem importa: mais específico primeiro) ─────────────────────────
_INTENT_ORDERED = [
    ("reembolso",    r"\b(reembolso|devolu[cç][aã]o|devolver|estornar|cancelar pedido|cancelamento|estorno|trocar|troca)\b"),
    ("reclamacao",   r"\b(errado|problema|defeito|quebrado|danificado|n[aã]o chegou|sumiu|atrasado|raiva|decepcionada)\b"),
    ("parceria",     r"\b(parceria|influencer|embaixadora|divulgar|publi|permuta|colabora[cç][aã]o|ugc)\b"),
    ("carrinho",     r"\b(carrinho|finalizar|comprar|desconto|cupom|frete|gr[aá]tis|oferta|promo[cç][aã]o)\b"),
    ("pedido",       r"\b(pedido|rastrear|rastreio|entrega|prazo|chegou|despachou|c[oó]digo|nfe|nota fiscal)\b"),
    ("produto",      r"\b(produto|pre[cç]o|dispon[ií]vel|vende|quanto custa|valor|estoque|foto|cor|tamanho)\b"),
    # Intents de neuromarketing (detectam oportunidade de nurturing)
    ("desejo",       r"\b(sonho|quero muito|adorei|perfeito|lindo|apaixonada|queria ter|meu lar|minha casa|ambiente)\b"),
    ("inspiracao",   r"\b(inspira[cç][aã]o|dica|ideia|como decorar|como organizar|combina|ficaria bem|estilo|japandi|minimalista)\b"),
    ("dor_decoracao",r"\b(bagun[cç]a|sem estilo|feio|n[aã]o gosto|cansa[cç]o|neutro demais|n[aã]o parece meu|n[aã]o sei decorar)\b"),
    ("saudacao",     r"\b(oi|ol[aá]|bom dia|boa tarde|boa noite|hey|hello|e a[ií]|salve)\b"),
]
_INTENT_PATTERNS = dict(_INTENT_ORDERED)

_ORDER_PATTERN = re.compile(r"#?(\d{4,6})")

def classify_intent(text: str) -> str:
    t = text.lower()
    for intent, pattern in _INTENT_ORDERED:
        if re.search(pattern, t):
            return intent
    return "geral"

def route_agent(intent: str) -> str:
    if intent == "reembolso":
        return "guard"
    if intent == "carrinho":
        return "sol"
    if intent in ("desejo", "inspiracao", "dor_decoracao"):
        return "neuro"
    if intent == "parceria":
        return "zara"
    return "lena"

def extract_order_number(text: str) -> Optional[str]:
    m = _ORDER_PATTERN.search(text)
    return m.group(1) if m else None

# ── Lookup real de pedido Shopify ──────────────────────────────────────────────
async def _shopify_order_info(order_number: str) -> Optional[str]:
    """Retorna resumo do pedido em texto para injetar no contexto da LENA."""
    if not SHOPIFY_DOMAIN or not SHOPIFY_TOKEN:
        return None
    try:
        url = f"https://{SHOPIFY_DOMAIN}/admin/api/2024-01/orders.json"
        headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
        params  = {"name": f"#{order_number}", "status": "any", "fields": "id,name,email,financial_status,fulfillment_status,created_at,line_items,shipping_lines,tracking_url"}
        async with httpx.AsyncClient(timeout=10) as hc:
            r = await hc.get(url, headers=headers, params=params)
            if r.status_code != 200:
                return None
            orders = r.json().get("orders", [])
            if not orders:
                return f"Pedido #{order_number} não encontrado no sistema."
            o = orders[0]
            items = ", ".join(i["title"] for i in o.get("line_items", []))
            fin   = o.get("financial_status", "—")
            ful   = o.get("fulfillment_status") or "pendente"
            track = o.get("tracking_url") or "link de rastreio não disponível ainda"
            date  = o.get("created_at", "")[:10]
            return (
                f"Pedido #{order_number} | Data: {date} | Itens: {items} | "
                f"Pagamento: {fin} | Entrega: {ful} | Rastreio: {track}"
            )
    except Exception:
        return None

# ── Sessões ────────────────────────────────────────────────────────────────────
def get_or_create_session(phone: str, name: str = "") -> dict:
    now = time.time()
    if phone in _SESSIONS:
        sess = _SESSIONS[phone]
        if now - sess["last_ts"] > _SESSION_TTL:
            _SESSIONS[phone] = {"history": [], "last_ts": now, "name": name or sess.get("name", ""), "state": "open"}
    else:
        _SESSIONS[phone] = {"history": [], "last_ts": now, "name": name, "state": "open"}
    _SESSIONS[phone]["last_ts"] = now
    return _SESSIONS[phone]

def add_to_history(phone: str, role: str, content: str):
    if phone not in _SESSIONS:
        return
    hist = _SESSIONS[phone]["history"]
    hist.append({"role": role, "content": content})
    if len(hist) > _MAX_HISTORY * 2:
        _SESSIONS[phone]["history"] = hist[-(_MAX_HISTORY * 2):]

def is_business_hours() -> bool:
    h = datetime.now().hour
    return BUSINESS_HOURS[0] <= h < BUSINESS_HOURS[1]

# ── Wrapper LLM (usa cascata completa do llm_engine) ─────────────────────────
async def _llm(system: str, messages: list, max_tokens: int = 350) -> str:
    text, _ = await _llm_engine(system, messages, max_tokens=max_tokens)
    return text

# ── Envio WPPConnect ───────────────────────────────────────────────────────────
def _wpp_headers() -> dict:
    return {"Authorization": f"Bearer {WPP_TOKEN}", "Content-Type": "application/json"}

async def _wpp_send(phone: str, message: str) -> bool:
    """Envia mensagem via WPPConnect. Retorna True se enviou com sucesso."""
    if not WPP_TOKEN:
        print("[WPPConnect] ERRO: WPPCONNECT_TOKEN não configurado!")
        return False
    if "localhost" in WPP_URL or "127.0.0.1" in WPP_URL:
        print(f"[WPPConnect] ERRO: WPPCONNECT_URL aponta para localhost ({WPP_URL}) — configure a URL do servidor!")
        return False

    url = f"{WPP_URL}/api/{WPP_SESSION}/send-message"
    phone_clean = phone.replace("@c.us", "").replace("@s.whatsapp.net", "")
    if not phone_clean.startswith("55"):
        phone_clean = f"55{phone_clean}"

    print(f"[WPPConnect] Enviando para {phone_clean} via {url}...")
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=15) as hc:
                r = await hc.post(
                    url,
                    json={"phone": phone_clean, "message": message, "isGroup": False},
                    headers=_wpp_headers(),
                )
                if r.status_code in (200, 201):
                    # WPP responde 200 mesmo em erro lógico (ex.: número inexistente,
                    # sessão desconectada). Validar o status do CORPO, não só o HTTP.
                    try:
                        body = r.json()
                    except Exception:
                        body = {}
                    body_status = str(body.get("status", "")).lower()
                    if body_status in ("error", "disconnected"):
                        print(f"[WPPConnect] ⚠️ Falha lógica para {phone_clean}: {body.get('message', r.text[:160])}")
                        # Erros lógicos (número não existe, sessão off) não se resolvem com retry
                        return False
                    print(f"[WPPConnect] ✅ Mensagem enviada para {phone_clean}")
                    return True
                else:
                    print(f"[WPPConnect] ⚠️ HTTP {r.status_code} para {phone_clean}: {r.text[:200]}")
                    if r.status_code == 401:
                        print("[WPPConnect] Token inválido! Verifique WPPCONNECT_TOKEN no .env")
                        return False
                    if r.status_code == 404:
                        print(f"[WPPConnect] Sessão '{WPP_SESSION}' não encontrada. Verifique WPPCONNECT_SESSION")
                        return False
        except httpx.ConnectError as e:
            print(f"[WPPConnect] ❌ Erro de conexão (tentativa {attempt+1}/3): {e}")
            if attempt < 2:
                await asyncio.sleep(2)
        except Exception as e:
            print(f"[WPPConnect] ❌ Erro inesperado (tentativa {attempt+1}/3): {type(e).__name__}: {e}")
            if attempt < 2:
                await asyncio.sleep(2)
    print(f"[WPPConnect] ❌ Falha definitiva ao enviar para {phone_clean} após 3 tentativas")
    return False

async def send_whatsapp_message(phone: str, message: str) -> bool:
    """Função pública para enviar mensagens de WhatsApp pelo WPPConnect.
    Retorna True se a entrega foi confirmada."""
    return await _wpp_send(phone, message)

async def send_whatsapp_image_base64(phone: str, file_path: str, caption: str = ""):
    """Envia imagem local via WPPConnect codificada em base64."""
    if not WPP_TOKEN or not os.path.exists(file_path):
        return
    import base64
    try:
        with open(file_path, "rb") as f:
            img_data = f.read()
        b64_data = base64.b64encode(img_data).decode("utf-8")
        filename = os.path.basename(file_path)
        mime_type = "image/png" if file_path.endswith(".png") else "image/jpeg"
        base64_str = f"data:{mime_type};base64,{b64_data}"
        
        url = f"{WPP_URL}/api/{WPP_SESSION}/send-file-base64"
        payload = {
            "phone": phone,
            "base64": base64_str,
            "filename": filename,
            "caption": caption
        }
        async with httpx.AsyncClient(timeout=30) as hc:
            await hc.post(url, json=payload, headers=_wpp_headers())
        print(f"[WPPConnect] Imagem {filename} enviada com sucesso para {phone}")
    except Exception as e:
        print(f"[WARN] Erro ao enviar imagem via WPPConnect: {e}")

async def _wpp_typing(phone: str):
    """Envia indicador de digitação via WPPConnect."""
    if not WPP_TOKEN:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as hc:
            await hc.post(f"{WPP_URL}/api/{WPP_SESSION}/chat-state", json={"phone": phone, "chatstate": "typing"}, headers=_wpp_headers())
        await asyncio.sleep(2)
        async with httpx.AsyncClient(timeout=5) as hc:
            await hc.post(f"{WPP_URL}/api/{WPP_SESSION}/chat-state", json={"phone": phone, "chatstate": "stopped"}, headers=_wpp_headers())
    except Exception:
        pass

# ── Processador principal ──────────────────────────────────────────────────────
async def process_message(phone: str, text: str, name: str = "", message_id: str = "") -> dict:
    """
    Processa mensagem recebida do WhatsApp.
    Retorna {"agent": str, "reply": str, "intent": str, "escalated": bool}
    """
    # Deduplicação
    if message_id:
        if message_id in _SEEN_IDS:
            return {"agent": "none", "reply": "", "intent": "duplicate", "escalated": False}
        _SEEN_IDS.add(message_id)
        if len(_SEEN_IDS) > _SEEN_MAX:
            _SEEN_IDS.clear()

    text = text.strip()
    if not text:
        return {"agent": "none", "reply": "", "intent": "empty", "escalated": False}

    sess   = get_or_create_session(phone, name)
    intent = classify_intent(text)
    primary_agent = route_agent(intent)
    escalated = False

    # Histórico de conversa (últimas 6 mensagens)
    history = sess["history"][-6:]

    # Identifica se é o início da conversa na sessão (sem respostas do assistente)
    is_start = not any(msg["role"] == "assistant" for msg in history)

    # ── Lookup de pedido Shopify ──────────────────────────────────────────────
    order_context = ""
    order_num = extract_order_number(text)
    if order_num and intent in ("pedido", "reclamacao", "reembolso"):
        info = await _shopify_order_info(order_num)
        if info:
            order_context = f"\n[DADOS DO PEDIDO NA LOJA]: {info}\n"

    guard_context = ""
    intent_guidelines = ""

    # ── GUARD — reembolso/cancelamento ────────────────────────────────────────
    if primary_agent == "guard":
        escalated = True
        guard_result = await _llm(
            SYSTEM_PROMPTS["guard"],
            [{"role": "user", "content": f"Cliente ({name or phone}) solicitou: {text}{order_context}"}],
            max_tokens=250,
        )
        try:
            g = json.loads(guard_result)
            base_reply = g.get("mensagem_cliente", "")
            guard_context = f"\n[GUARD: aprovado={g.get('aprovado')}, motivo={g.get('motivo')}, ação={g.get('acao')}]"
        except Exception:
            base_reply = guard_result
            guard_context = ""

        intent_guidelines = (
            f"O cliente solicitou reembolso/devolução ou cancelamento do pedido.\n"
            f"O assistente financeiro GUARD analisou a solicitação e gerou o seguinte parecer:\n"
            f"'{base_reply}'\n\n"
            f"Com base nesse parecer, formule a resposta final ao cliente usando o seu tom LENA (caloroso, empático, resolutivo, sem burocracia).\n"
            f"Se foi aprovado ou se foi escalado, explique com clareza o prazo e o próximo passo."
        )

    # ── SOL — recuperação de carrinho ─────────────────────────────────────────
    elif primary_agent == "sol":
        intent_guidelines = (
            "O cliente abandonou o carrinho ou está indeciso quanto à compra.\n"
            "Sua missão é atuar como especialista de vendas (SOL), gerando uma mensagem de recuperação irresistível e inspiradora:\n"
            "- Ofereça urgência suave, sem pressão agressiva.\n"
            "- Apresente o cupom AURA10 (10% OFF) ou frete grátis para compras acima de R$199.\n"
            "- Indique o site: auradecore.com.br"
        )

    # ── ZARA — parceria/influencer ────────────────────────────────────────────
    elif primary_agent == "zara":
        intent_guidelines = (
            "O cliente tem interesse em parcerias, divulgação, ser embaixador ou publis.\n"
            "Atue como community manager (ZARA) para responder com entusiasmo:\n"
            "- Agradeça pelo interesse em fazer parte da comunidade Aura Decore.\n"
            "- Solicite o portfólio ou os perfis das redes sociais (IG/TikTok).\n"
            "- Canal de contato: e-mail auras.de@gmail.com ou direct do Instagram @auras.decore."
        )

    # ── NEURO — desejo/inspiração/dor de decoração ────────────────────────────
    elif primary_agent == "neuro":
        customer_ctx = {"first_name": name, "orders_count": 0, "total_spent": 0}
        lead_score = score_lead(customer_ctx) if _NEURO_OK else "morno"
        neuro_ctx = build_neuro_prompt({
            "intent": intent,
            "customer": customer_ctx,
            "produto": "",
        }) if _NEURO_OK else ""

        intent_guidelines = (
            f"O cliente está buscando inspiração, expressando desejos para o lar, ou compartilhando dores de decoração.\n"
            f"Atue como estrategista de copy neuromarketing (NEURO):\n"
            f"- Use os frameworks PAS (Problem-Agitate-Solve) ou BAB (Before-After-Bridge) dependendo do contexto.\n"
            f"- Ative desejos nucleares da ICP Ana Clara (conforto, pertencimento, beleza, controle).\n"
            f"- Trate das dores comuns de decoração (lar genérico, caos doméstico, paralisia decorativa).\n"
            f"- Diretrizes neuromarketing extras: {neuro_ctx}"
        )

    # ── LENA — atendimento geral ──────────────────────────────────────────────
    else:
        intent_guidelines = (
            f"O cliente está fazendo perguntas gerais, tirando dúvidas de produtos ou saudando (intent={intent}).\n"
            f"Responda à dúvida de forma extremamente atenciosa, clara e simpática.\n"
            f"- Prazos de entrega padrão: 15-25 dias úteis (dropshipping internacional).\n"
            f"- Frete grátis em compras acima de R$199.\n"
            f"- Se for uma dúvida de produto, responda com precisão a partir da memória de produtos do Obsidian."
        )

    # Constrói o system prompt final e unificado da LENA
    system_prompt = build_lena_system_prompt(intent_guidelines, name, phone, order_context, is_start)

    # Executa a chamada do LLM usando o prompt unificado de LENA
    user_msg = f"Mensagem do cliente: {text}"
    msgs = history + [{"role": "user", "content": user_msg}]
    reply = await _llm(system_prompt, msgs, max_tokens=350)

    # Analisa e segmenta o lead
    analysis = await analyze_lead_interaction(name, text, reply)

    # Salva o lead e a interação no banco de dados SQLite (CRM) e no Obsidian (memória em markdown)
    save_lead_and_interaction(phone, name, text, reply, primary_agent, analysis)
    save_lead_to_obsidian(phone, name, text, reply, analysis)

    add_to_history(phone, "user", text)
    add_to_history(phone, "assistant", reply)

    return {
        "agent":     primary_agent,
        "reply":     reply,
        "intent":    intent,
        "escalated": escalated,
        "guard_log": guard_context if escalated else "",
    }


async def handle_incoming(phone: str, text: str, name: str = "", message_id: str = "") -> dict:
    """Função pública: processa + envia resposta via WPPConnect.
    O envio é AGUARDADO (não fire-and-forget) para garantir entrega.
    """
    # Indica digitação em background (não bloqueia processamento)
    asyncio.create_task(_wpp_typing(phone))
    await asyncio.sleep(1.5)

    result = await process_message(phone, text, name, message_id)

    if result.get("reply"):
        # Awaita o envio — não usa create_task para não perder erros
        sent = await _wpp_send(phone, result["reply"])
        result["sent"] = sent
        if not sent:
            print(f"[WA] ⚠️ Resposta gerada mas NÃO enviada para {phone}. Reply: {result['reply'][:80]}")
    else:
        result["sent"] = False

    return result
