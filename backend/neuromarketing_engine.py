# neuromarketing_engine.py — Aura Decore
# Motor de copy neuromarketing: desejo, dor, oferta e sequências de lead nurturing
# Agentes: NEURO (copy estratégico) + PROMO (disparos promocionais)

import os
import json
import random
from datetime import datetime, timedelta
from typing import Optional

# ── 6 Desejos Nucleares da Ana Clara (ICP Aura Decore) ──────────────────────────
DESIRE_MAP = {
    "status":        "Ser reconhecida como alguém com bom gosto e estilo próprio.",
    "pertencimento": "Fazer parte de uma comunidade que valoriza beleza intencional.",
    "seguranca":     "Sentir que seu lar é um refúgio seguro e organizado.",
    "conforto":      "Ter um espaço que abraça, não que estresa.",
    "beleza":        "Viver rodeada de objetos que ela mesma escolheu com cuidado.",
    "controle":      "Sentir que tem domínio sobre como o lar se apresenta ao mundo.",
}

# ── 5 Dores Emocionais Primárias ─────────────────────────────────────────────────
PAIN_MAP = {
    "caos":       "Lar bagunçado que drena energia e aumenta ansiedade.",
    "generico":   "Decoração impessoal que não reflete quem ela é.",
    "estresse":   "Ambiente que não desacelera — chega em casa e não descansa.",
    "vergonha":   "Envergonha de receber visitas por não ter 'um lar bonito'.",
    "paralisia":  "Não sabe por onde começar a decorar — muitas opções, pouco resultado.",
}

# ── Frameworks de Copy Neuromarketing ────────────────────────────────────────────
COPY_FRAMEWORKS = {

    "PAS": {
        "name": "Problem → Agitate → Solve",
        "desc": "Nomeia o problema, amplia a dor, apresenta a solução.",
        "template": (
            "[PROBLEMA] {problema}\n"
            "[AMPLIFICA] {amplifica}\n"
            "[SOLUÇÃO] {solucao}"
        ),
    },

    "AIDA": {
        "name": "Attention → Interest → Desire → Action",
        "desc": "Hook poderoso, desperta interesse, acende desejo, convida à ação.",
        "template": (
            "[HOOK] {hook}\n"
            "[INTERESSE] {interesse}\n"
            "[DESEJO] {desejo}\n"
            "[AÇÃO] {acao}"
        ),
    },

    "BAB": {
        "name": "Before → After → Bridge",
        "desc": "Contraste entre estado atual (dor) e estado desejado (sonho).",
        "template": (
            "[ANTES] {antes}\n"
            "[DEPOIS] {depois}\n"
            "[PONTE] {ponte}"
        ),
    },

    "SBO": {
        "name": "Story → Bridge → Offer",
        "desc": "História identificável, conexão emocional, oferta natural.",
        "template": (
            "[HISTÓRIA] {historia}\n"
            "[CONEXÃO] {conexao}\n"
            "[OFERTA] {oferta}"
        ),
    },

    "PROVA_SOCIAL": {
        "name": "Social Proof → Desire → Nudge",
        "desc": "Prova de outras pessoas, acende inveja saudável, convida suavemente.",
        "template": (
            "[PROVA] {prova}\n"
            "[IDENTIFICAÇÃO] {identificacao}\n"
            "[NUDGE] {nudge}"
        ),
    },
}

# ── Gatilhos Neurológicos ─────────────────────────────────────────────────────────
NEURO_TRIGGERS = {
    "escassez":      "Últimas {n} unidades disponíveis.",
    "urgencia":      "Oferta válida só até {data}.",
    "perda":         "Cada dia sem isso é um dia a mais de {dor}.",
    "autoridade":    "Curado por especialistas em Neuroarquitetura e Design Japandi.",
    "reciprocidade": "Um presente especial para você: {beneficio}.",
    "identidade":    "Para quem escolhe viver com intenção e beleza.",
    "novidade":      "Recém chegou — e já está na lista de favoritos de quem ama design.",
    "prova_social":  "{n} pessoas adoram esse produto — veja os comentários.",
}

# ── Templates de Mensagens WhatsApp por Estágio do Lead ─────────────────────────
WA_TEMPLATES = {

    # FRIO — primeira interação, sem histórico de compra
    "frio_interesse": [
        (
            "Oi, {nome}! 🌿 Que bom ter você por aqui.\n\n"
            "A Aura Decore nasceu de uma ideia simples: seu lar deve ser o lugar onde você respira fundo e sorri.\n\n"
            "Nossos produtos unem a elegância do Japandi com a calma da natureza — cada peça escolhida para transformar o espaço em algo seu de verdade.\n\n"
            "Dá uma olhada: auradecore.com.br ✨\n"
            "E se tiver alguma dúvida, pode me chamar — sou a Lena, estou aqui!"
        ),
        (
            "Oi {nome} 🌸 Bem-vinda!\n\n"
            "Sabia que o ambiente onde você vive afeta diretamente como você se sente? Não é clichê — é ciência.\n\n"
            "Na Aura, cuidamos de cada detalhe para que cada objeto que entra na sua casa seja intencional, bonito e com propósito.\n\n"
            "Aqui está um cupom especial de boas-vindas: **AURA10** (10% OFF na primeira compra) 💛\n"
            "auradecore.com.br"
        ),
    ],

    # MORNO — mostrou interesse, visitou produto, não comprou
    "morno_produto": [
        (
            "Oi {nome}! Você deu uma olhada em {produto} outro dia... 👀\n\n"
            "Às vezes a gente para porque tem uma dúvida — tamanho, material, como combina com o que já tem em casa.\n\n"
            "Me conta! Posso te ajudar a visualizar exatamente como ficaria no seu espaço. 🌿"
        ),
        (
            "{nome}, ainda pensando em {produto}? ✨\n\n"
            "Entendo — uma compra intencional merece reflexão. Mas deixa eu te contar:\n"
            "Esse produto específico foi curado porque combina com 3 estilos diferentes de decoração, "
            "dura anos e transforma qualquer ambiente em questão de minutos.\n\n"
            "Se quiser, te mando fotos de clientes que já têm em casa 🏡"
        ),
    ],

    # MORNO — carrinho abandonado com copy emocional
    "morno_carrinho": [
        (
            "{nome}, seu carrinho ainda está te esperando 🛒\n\n"
            "Olhando de fora, parece que você está montando algo bonito. E eu entendo — "
            "cada peça importa quando o objetivo é um lar que representa quem você é.\n\n"
            "Que tal usar **AURA10** para finalizar hoje? (10% OFF 🎁)\n"
            "→ auradecore.com.br/cart"
        ),
        (
            "Oi {nome}! Uma coisa rápida 🌸\n\n"
            "Você foi a única a salvar {produto} no carrinho essa semana — e nosso estoque é pequeno por escolha, "
            "porque trabalhamos com curadoria, não com volume.\n\n"
            "Se sumir, vai demorar para voltar. Se quiser garantir: **AURA10** (10% OFF, válido hoje) 💛"
        ),
    ],

    # QUENTE — já comprou, nutrição pós-compra + upsell
    "quente_upsell": [
        (
            "{nome}! 🎉 Seu {produto} chegou?\n\n"
            "Adoro imaginar a transformação que aquela peça está fazendo no seu canto. 🌿\n\n"
            "Aliás — clientes que amaram {produto} geralmente completam o ambiente com {produto_complementar}. "
            "Quer ver? Tenho algo especial para você como cliente Aura: **AURAVIP15** (15% OFF) 💛\n"
            "auradecore.com.br"
        ),
    ],

    # REATIVAÇÃO — inativo 60+ dias (win-back emocional)
    "win_back": [
        (
            "{nome}, faz um tempo... e senti sua falta! 🌸\n\n"
            "A Aura evoluiu muito. Novos produtos, nova coleção — coisas que eu sei que você vai amar.\n\n"
            "Guardei algo especial para você voltar:\n"
            "🎁 **AURAVIP15** — 15% OFF (válido 72h)\n\n"
            "Seu lar merece essa atenção. auradecore.com.br"
        ),
        (
            "Oi {nome} 💛 Aqui é a Lena, da Aura Decore.\n\n"
            "Sei que a vida fica corrida e a decoração vai ficando para depois... mas foi pensando exatamente nisso "
            "que trouxemos peças que transformam o ambiente em minutos — sem reforma, sem complicação.\n\n"
            "Tem uma oferta exclusiva esperando por você: **AURAVIP15** (15% OFF, expira em 3 dias)\n"
            "→ auradecore.com.br"
        ),
    ],

    # FLASH SALE — promoção relâmpago
    "flash_sale": [
        (
            "⚡ OFERTA RELÂMPAGO — só hoje!\n\n"
            "{nome}, selecionamos {n_produtos} produtos da coleção {colecao} com {desconto}% OFF.\n"
            "Frete grátis acima de R$299.\n\n"
            "⏰ Válido até {hora_fim} de hoje.\n"
            "→ auradecore.com.br | Cupom: **{cupom}**\n\n"
            "Estoque limitado — curadoria, não volume. 🌿"
        ),
    ],

    # LANÇAMENTO — novo produto
    "lancamento": [
        (
            "✨ Chegou, {nome}!\n\n"
            "Acabamos de adicionar {produto} à loja — e ele já está na lista de favoritos de quem ama "
            "design intencional.\n\n"
            "{descricao_emocional}\n\n"
            "Como cliente especial, você tem acesso antes de todo mundo: **AURA10** (10% OFF)\n"
            "→ auradecore.com.br"
        ),
    ],

    # DOR RESOLVIDA — conteúdo educativo que resolve uma dor e oferece produto
    "conteudo_dor": [
        (
            "{nome}, você já teve essa sensação de chegar em casa e não conseguir relaxar?\n\n"
            "Não é frescura — é neuroarquitetura. O ambiente caótico literalmente impede o cérebro de "
            "entrar no modo descanso.\n\n"
            "A solução não é reforma. É intenção. Três objetos certos transformam qualquer ambiente.\n\n"
            "Posso te mostrar o que nossa curadoria selecionou para isso? 🌿"
        ),
    ],
}

# ── Lead Score — classifica temperatura do lead ──────────────────────────────────
def score_lead(customer: dict) -> str:
    """Retorna: 'frio', 'morno', 'quente', 'vip'"""
    orders = customer.get("orders_count", 0)
    spent = float(customer.get("total_spent", 0))
    last_order = customer.get("last_order_at")

    if orders == 0:
        return "frio"

    if orders >= 3 or spent >= 500:
        return "vip"

    if last_order:
        try:
            delta = datetime.now() - datetime.fromisoformat(last_order.replace("Z", ""))
            if delta.days > 60:
                return "frio"  # reativação necessária
        except Exception:
            pass

    if orders >= 1:
        return "quente"

    return "morno"


def get_template(stage: str, data: dict) -> str:
    """Pega template aleatório para o estágio e preenche com dados."""
    templates = WA_TEMPLATES.get(stage, WA_TEMPLATES["frio_interesse"])
    template = random.choice(templates)
    try:
        return template.format(**data)
    except KeyError:
        return template


def build_neuro_prompt(context: dict) -> str:
    """Constrói prompt enriquecido com neuromarketing para LENA/NEURO usar."""
    lead_score = score_lead(context.get("customer", {}))
    intent = context.get("intent", "geral")
    produto = context.get("produto", "")
    nome = context.get("customer", {}).get("first_name", "")

    desire_keys = list(DESIRE_MAP.keys())
    pain_keys   = list(PAIN_MAP.keys())

    # Seleciona desejo e dor mais relevantes para o contexto
    desejo = DESIRE_MAP.get("beleza") if "produto" in intent else DESIRE_MAP.get("conforto")
    dor    = PAIN_MAP.get("caos") if lead_score == "frio" else PAIN_MAP.get("paralisia")

    trigger = NEURO_TRIGGERS.get("identidade")
    if lead_score == "frio":
        trigger = NEURO_TRIGGERS.get("reciprocidade", "").format(beneficio="cupom AURA10 (10% OFF)")
    elif lead_score in ("morno",):
        trigger = NEURO_TRIGGERS.get("escassez", "").format(n="poucas")
    elif lead_score in ("quente", "vip"):
        trigger = NEURO_TRIGGERS.get("autoridade")

    return (
        f"CONTEXTO NEUROMARKETING:\n"
        f"- Lead score: {lead_score}\n"
        f"- Desejo nuclear ativado: {desejo}\n"
        f"- Dor emocional endereçada: {dor}\n"
        f"- Gatilho neurológico: {trigger}\n"
        f"- Framework recomendado: {'BAB' if lead_score == 'frio' else 'PAS' if lead_score == 'morno' else 'SBO'}\n"
        f"- Nome: {nome} | Produto de interesse: {produto}\n"
        f"\nUse esses elementos de forma SUTIL e NATURAL na sua resposta. "
        f"Nunca cite os frameworks explicitamente. Escreva como uma amiga, não como um vendedor."
    )


# ── Sequência Automática de Nurturing ────────────────────────────────────────────
NURTURING_SEQUENCES = {
    "novo_lead": [
        {"dia": 0,  "stage": "frio_interesse",  "hora": "10:00"},
        {"dia": 2,  "stage": "conteudo_dor",     "hora": "14:00"},
        {"dia": 5,  "stage": "morno_produto",    "hora": "10:00"},
        {"dia": 7,  "stage": "morno_carrinho",   "hora": "16:00"},
        {"dia": 14, "stage": "flash_sale",       "hora": "10:00"},
    ],
    "pos_compra": [
        {"dia": 0,  "stage": "quente_upsell",   "hora": "imediato"},
        {"dia": 7,  "stage": "conteudo_dor",    "hora": "11:00"},
        {"dia": 14, "stage": "quente_upsell",   "hora": "10:00"},
    ],
    "win_back": [
        {"dia": 0,  "stage": "win_back",        "hora": "10:00"},
        {"dia": 3,  "stage": "conteudo_dor",    "hora": "14:00"},
        {"dia": 7,  "stage": "flash_sale",      "hora": "10:00"},
    ],
}


# ── API de consulta pública para o n8n ───────────────────────────────────────────
def get_sequence_for_event(event: str) -> list:
    """Retorna sequência de nurturing para um evento Shopify."""
    mapping = {
        "customers/create":  "novo_lead",
        "orders/paid":       "pos_compra",
        "checkouts/create":  "novo_lead",
        "win_back_trigger":  "win_back",
    }
    key = mapping.get(event, "novo_lead")
    return NURTURING_SEQUENCES.get(key, [])


def generate_promo_blast(
    colecao: str = "Japandi Premium",
    desconto: int = 15,
    cupom: str = "AURAVIP15",
    n_produtos: int = 5,
    hora_fim: str = "23h59",
) -> dict:
    """Gera dados de flash sale para disparo em massa via n8n."""
    return {
        "stage": "flash_sale",
        "data": {
            "colecao": colecao,
            "desconto": desconto,
            "cupom": cupom,
            "n_produtos": n_produtos,
            "hora_fim": hora_fim,
            "nome": "{nome}",  # será substituído por nome real no loop n8n
        },
        "template_preview": get_template("flash_sale", {
            "colecao": colecao,
            "desconto": desconto,
            "cupom": cupom,
            "n_produtos": n_produtos,
            "hora_fim": hora_fim,
            "nome": "cliente",
        }),
    }
