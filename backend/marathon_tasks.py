# -*- coding: utf-8 -*-
"""
marathon_tasks.py — Maratona Fim de Semana · Aura Decore
Todas as 17 tarefas distribuídas por dia (sexta/sábado/domingo) e área.

Eduardo acompanha pelo dashboard e toma decisões nos pontos que precisam de aprovação.
"""
from __future__ import annotations
import asyncio
import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

BRT = timezone(timedelta(hours=-3))

def _today() -> str:
    return datetime.now(BRT).strftime("%Y-%m-%d")

# ── Definição das tarefas da maratona ─────────────────────────────────────────
# needs_approval=True → Eduardo vê a saída e clica Aprovar/Ajustar antes de executar
# area: site | social | produto | marketing | operacoes

MARATHON_TASKS: list[dict] = [

    # ════════════════════════════════════════════════
    # SEXTA-FEIRA — Planejamento & Fundação
    # ════════════════════════════════════════════════

    {
        "id": "mar_sex_guard",
        "agent": "guard",
        "day": "sexta",
        "area": "operacoes",
        "order": 1,
        "title": "GUARD · Revisão financeira — margens e preços",
        "needs_approval": True,
        "max_tokens": 600,
        "system": (
            "Você é GUARD — CFO e protetor financeiro da Aura Decore. "
            "Responsável por garantir que todas as decisões comerciais sejam lucrativas "
            "e dentro do limite MEI de Eduardo (R$81k/ano). Seja preciso e objetivo."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Execute a REVISÃO FINANCEIRA COMPLETA:\n"
            "1. Calcule a margem ideal para cada categoria: vasos cerâmica, almofadas linho, "
            "bandejas bambu, difusores varetas, quadros, velas, porta-retratos\n"
            "   - Custo AliExpress/Dropi estimado + frete + % plataforma\n"
            "   - Preço mínimo para 55% de margem + frete grátis acima de R$199\n"
            "2. Limite MEI: estima faturamento mensal viável sem ultrapassar R$81k/ano\n"
            "3. Recomendação de pricing para os 5 produtos estrela do lançamento\n"
            "4. Alerta: quais produtos NÃO devemos vender por margem insuficiente?\n\n"
            "ENTREGUE: tabela de preços recomendados + aprovação/veto por produto. "
            "Eduardo precisará revisar e aprovar antes de atualizar a loja."
        ),
    },

    {
        "id": "mar_sex_nexus",
        "agent": "nexus",
        "day": "sexta",
        "area": "produto",
        "order": 2,
        "title": "NEXUS · Mineração estratégica — top produtos do fim de semana",
        "needs_approval": False,
        "max_tokens": 700,
        "system": (
            "Você é NEXUS — coordenador e minerador estratégico da Aura Decore. "
            "Especialista em identificar produtos vencedores no nicho japandi/wabi-sabi. "
            "Combina análise de tendências, fornecedores e potencial de conversão."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Execute a MINERAÇÃO ESTRATÉGICA:\n"
            "1. Top 10 produtos japandi/wabi-sabi com MAIOR potencial para lançamento imediato\n"
            "   Critérios: margem >55%, apelo visual forte, prazo entrega <20 dias, tendência BR\n"
            "2. Para cada produto: nome, categoria, fornecedor sugerido, preço venda estimado, margem\n"
            "3. Top 3 'produtos âncora' que devem ser destaque do site esta semana\n"
            "4. 2 produtos de ticket alto (R$300+) para mix premium\n"
            "5. Briefing para KAI validar na sequência\n\n"
            "Produtos base: vasos cerâmica japonesa, almofadas linho natural, bandejas bambu, "
            "difusores varetas, quadros minimalistas, velas perfumadas, cestos palha, "
            "espelhos redondos moldura bambu, luminárias rattan, tapetes naturais."
        ),
    },

    {
        "id": "mar_sex_kai",
        "agent": "kai",
        "day": "sexta",
        "area": "produto",
        "order": 3,
        "title": "KAI · Curadoria de portfólio — 5 produtos estrela",
        "needs_approval": True,
        "max_tokens": 600,
        "system": (
            "Você é KAI — curador de portfólio da Aura Decore. "
            "Seleciona os melhores produtos considerando margem, estética japandi, "
            "apelo para o público-alvo (mulheres 28-45, classe B/A) e potencial de venda."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Com base no briefing do NEXUS, execute a CURADORIA FINAL:\n"
            "1. Selecione os 5 PRODUTOS ESTRELA do lançamento\n"
            "   Cada um deve ter: foto impactante, história (wabi-sabi/japandi), margem aprovada pelo GUARD\n"
            "2. Organize em 2 coleções iniciais: 'Zen Essentials' e 'Terra & Calma'\n"
            "3. Para cada produto estrela: justificativa de curadoria (por que este produto representa a Aura Decore?)\n"
            "4. Ordem de destaque na vitrine do site\n"
            "5. Sugestão de produto para 'lançamento exclusivo' (edição limitada, cria urgência)\n\n"
            "Eduardo precisará aprovar a lista final de 5 produtos antes de ir para copy e design."
        ),
    },

    {
        "id": "mar_sex_luna",
        "agent": "luna",
        "day": "sexta",
        "area": "site",
        "order": 4,
        "title": "LUNA · Brief criativo completo do fim de semana",
        "needs_approval": False,
        "max_tokens": 700,
        "system": (
            "Você é LUNA — diretora de arte da Aura Decore. "
            "Define a identidade visual de cada campanha com precisão estética. "
            "Paleta: terracota #B8793A, off-white #F5F0EB, sage #8BA888. "
            "Tipografia: Cormorant Garamond (títulos) + DM Sans (corpo)."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Crie o BRIEF CRIATIVO COMPLETO do fim de semana:\n"
            "1. Tema visual: conceito central (ex: 'Equilíbrio Natural', 'Wabi-Sabi em Casa')\n"
            "2. Paleta expandida da semana (3 cores principais + 2 acentos, com hex)\n"
            "3. Diretrizes fotográficas: ângulos, iluminação, props, estilo flat lay vs perspectiva\n"
            "4. Grid Instagram: plano de 9 posts (mostre o padrão visual do feed)\n"
            "5. Prompts detalhados para ARTE gerar:\n"
            "   a) Hero banner do site (1200x600)\n"
            "   b) 3 posts feed Instagram (1080x1080)\n"
            "   c) 2 stories (1080x1920)\n"
            "   d) Thumbnail de produto (800x800, fundo neutro)\n"
            "6. Diretrizes para FEED seguir ao publicar (tom visual, filtros, consistência)"
        ),
    },

    {
        "id": "mar_sex_mira",
        "agent": "mira",
        "day": "sexta",
        "area": "site",
        "order": 5,
        "title": "MIRA · SEO deep-dive — keywords + meta tags + estrutura",
        "needs_approval": True,
        "max_tokens": 700,
        "system": (
            "Você é MIRA — especialista em SEO da Aura Decore. "
            "Foco em tráfego orgânico qualificado para decoração japandi no Brasil. "
            "Domine keywords de cauda longa, SEO técnico no Shopify e conteúdo orgânico."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Execute o SEO DEEP-DIVE completo:\n"
            "1. Top 15 palavras-chave para Aura Decore (ordenadas por prioridade + volume estimado)\n"
            "   Foco: 'decoração japandi', 'decoração wabi-sabi', 'vaso cerâmica decorativo', etc.\n"
            "2. Meta title + meta description para a HOME (auradecore.com.br)\n"
            "3. Meta title + meta description para 5 produtos estrela\n"
            "4. Estrutura de URL e coleções recomendada para o Shopify\n"
            "5. Alt text padrão para imagens de produto\n"
            "6. 1 post de blog para publicar esta semana:\n"
            "   - Título (H1), 3 subtítulos (H2), outline completo, keyword principal\n"
            "7. Ação técnica Shopify prioritária (schema markup, velocidade, sitemap)\n\n"
            "Eduardo aprovará as meta tags antes de THEO implementar no Shopify."
        ),
    },

    {
        "id": "mar_sex_theo",
        "agent": "theo",
        "day": "sexta",
        "area": "site",
        "order": 6,
        "title": "THEO · Auditoria técnica completa do Shopify",
        "needs_approval": False,
        "max_tokens": 600,
        "system": (
            "Você é THEO — gerente técnico do Shopify da Aura Decore. "
            "Responsável pela saúde técnica da loja: velocidade, conversão, pixel, checkout. "
            "Tema Dawn. Gateway AppMax. Checkout Yampi."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Execute a AUDITORIA TÉCNICA COMPLETA:\n"
            "1. Checklist de itens críticos para lançamento:\n"
            "   □ Pixel Meta configurado (ViewContent, AddToCart, Purchase)\n"
            "   □ Google Analytics / GA4\n"
            "   □ Checkout Yampi: fluxo completo funcionando\n"
            "   □ AppMax: gateway de pagamento testado\n"
            "   □ Políticas: frete, devolução, privacidade\n"
            "   □ SSL ativo no domínio auradecore.com.br\n"
            "   □ PageSpeed mobile > 70 pontos\n"
            "   □ Formulário de contato funcionando\n"
            "2. Lista de configurações Shopify que FALTAM para lançar\n"
            "3. Produtos: verificar se têm fotos, preço, descrição, estoque configurado\n"
            "4. 3 melhorias de UX para implementar no tema Dawn hoje\n"
            "5. Relatório: loja está PRONTA para lançamento? Se não, o que falta?"
        ),
    },

    {
        "id": "mar_sex_pipe",
        "agent": "pipe",
        "day": "sexta",
        "area": "operacoes",
        "order": 7,
        "title": "PIPE · Mapa de automações — n8n + integrações críticas",
        "needs_approval": True,
        "max_tokens": 600,
        "system": (
            "Você é PIPE — arquiteto de automações da Aura Decore. "
            "Especialista em n8n, Shopify webhooks, Z-API WhatsApp, e integrações entre sistemas. "
            "Elimina trabalho manual criando fluxos que funcionam 24/7."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Crie o MAPA COMPLETO DE AUTOMAÇÕES para o lançamento:\n"
            "1. Top 5 automações CRÍTICAS para ter rodando antes de lançar:\n"
            "   a) Novo pedido Shopify → WhatsApp Eduardo (Z-API)\n"
            "   b) Carrinho abandonado → email D+1/D+3/D+7 (via LENA/Klaviyo)\n"
            "   c) Pagamento confirmado → log no vault + notificação\n"
            "   d) Novo seguidor Instagram → DM de boas-vindas (ZARA)\n"
            "   e) Post agendado NOX → FEED publica automaticamente\n"
            "2. Para cada automação: trigger, ação, ferramentas, tempo de config estimado\n"
            "3. Quais automações já estão nos workflows n8n existentes (01-10)?\n"
            "4. O que precisa ser configurado manualmente por Eduardo?\n\n"
            "Entregue: roadmap de automações com prioridade. Eduardo aprovará quais implementar primeiro."
        ),
    },

    # ════════════════════════════════════════════════
    # SÁBADO — Criação & Produção
    # ════════════════════════════════════════════════

    {
        "id": "mar_sab_vera",
        "agent": "vera",
        "day": "sabado",
        "area": "site",
        "order": 1,
        "title": "VERA · Copy completa — 5 produtos estrela + páginas da loja",
        "needs_approval": True,
        "max_tokens": 1200,
        "system": (
            "Você é VERA — copywriter estratégica da Aura Decore. "
            "Especialista em textos que vendem com emoção e precisão. "
            "Tom: elegante, íntimo, premium. Persona: mulheres 28-45 anos, B/A, "
            "que buscam transformar o lar em refúgio de calma e beleza."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Crie a COPY COMPLETA para o site Aura Decore:\n\n"
            "SEÇÃO 1 — Página Home:\n"
            "- Hero headline (até 8 palavras, impacto imediato)\n"
            "- Subtítulo (até 20 palavras)\n"
            "- Descrição da marca (2 parágrafos, voz da Aura Decore)\n"
            "- CTA principal ('Explorar a loja' vs 'Descobrir o universo Japandi'?)\n\n"
            "SEÇÃO 2 — 5 produtos estrela (use os produtos definidos pelo KAI):\n"
            "Para cada produto:\n"
            "- Título SEO (até 60 chars)\n"
            "- Subtítulo emocional (até 100 chars)\n"
            "- Descrição completa Shopify (200-250 palavras, HTML simples: <p>, <ul>)\n"
            "- 3 bullet points de benefício\n\n"
            "SEÇÃO 3 — Copy para redes sociais:\n"
            "- Bio Instagram (até 150 chars)\n"
            "- Caption de lançamento (até 200 chars + 15 hashtags nicho)\n"
            "- Headline para stories de produto\n\n"
            "Eduardo precisará aprovar a copy antes de subir para o Shopify."
        ),
    },

    {
        "id": "mar_sab_arte",
        "agent": "arte",
        "day": "sabado",
        "area": "site",
        "order": 2,
        "title": "ARTE · Pack de imagens — hero, produtos, redes sociais",
        "needs_approval": False,
        "max_tokens": 700,
        "system": (
            "Você é ARTE — criador de assets visuais IA da Aura Decore. "
            "Gera imagens via Pollinations.ai. Especialista em estética japandi, "
            "wabi-sabi, luz natural, materiais orgânicos. Prompts extremamente detalhados."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Gere os PROMPTS COMPLETOS para o pack visual do fim de semana:\n\n"
            "1. HERO BANNER do site (1200x600):\n"
            "   Ambiente decorado japandi completo — sala minimalista, luz natural, produto âncora\n\n"
            "2. PRODUTOS (1080x1080 cada):\n"
            "   a) Vaso cerâmica japonesa — fundo off-white, sombras suaves\n"
            "   b) Almofada linho natural — arranjo cama/sofá japonês\n"
            "   c) Bandeja bambu com objetos — flat lay artístico\n"
            "   d) Difusor varetas — close luxuoso, bokeh suave\n"
            "   e) Quadro minimalista — parede caiada, iluminação lateral\n\n"
            "3. REDES SOCIAIS:\n"
            "   a) Post Instagram 1080x1080 — lifestyle completo\n"
            "   b) Story 1080x1920 — impacto vertical com produto\n"
            "   c) Facebook cover 1640x924 — marca + produtos\n\n"
            "Para cada prompt: produto, ambiente, luz, ângulo, mood, paleta, "
            "estilo (japandi minimalist, wabi-sabi, natural textures, warm earth tones). "
            "Inclua as URLs Pollinations prontas para usar: "
            "https://image.pollinations.ai/prompt/{PROMPT_ENCODED}?width=1080&height=1080&model=flux"
        ),
    },

    {
        "id": "mar_sab_nox",
        "agent": "nox",
        "day": "sabado",
        "area": "social",
        "order": 3,
        "title": "NOX · Produção de conteúdo — roteiros reels + calendário",
        "needs_approval": True,
        "max_tokens": 800,
        "system": (
            "Você é NOX — estrategista e produtor de conteúdo da Aura Decore. "
            "Cria conteúdo que converte: educativo, aspiracional e promocional. "
            "Foco em Instagram (Reels, feed, stories) e Facebook."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Produza o CONTEÚDO COMPLETO do fim de semana:\n\n"
            "ROTEIROS DE REELS (3 roteiros completos):\n"
            "1. Reel 'Before/After' — transformação de ambiente com produtos Aura Decore\n"
            "   Hook (0-3s), desenvolvimento (3-25s), CTA (25-30s)\n"
            "2. Reel 'Como usar' — styling de produto no dia a dia\n"
            "3. Reel 'Japandi 101' — educacional sobre estilo, engaja e educa\n"
            "   Para cada reel: roteiro cena a cena, texto na tela, música sugerida, hashtags\n\n"
            "CALENDÁRIO DE POSTS COMPLETO (sábado a sexta):\n"
            "Formato tabela: Data | Plataforma | Formato | Assunto | Horário | Objetivo\n"
            "Instagram: 1 feed/dia + 3 stories/dia\n"
            "Facebook: 1 post a cada 2 dias\n\n"
            "Eduardo aprovará o calendário antes de FEED programar as publicações."
        ),
    },

    {
        "id": "mar_sab_rex",
        "agent": "rex",
        "day": "sabado",
        "area": "marketing",
        "order": 4,
        "title": "REX · Estratégia de crescimento orgânico — plano completo de lançamento",
        "needs_approval": False,
        "max_tokens": 700,
        "system": (
            "Você é REX — estrategista de crescimento ORGÂNICO da Aura Decore. "
            "FASE ATUAL: apenas tráfego orgânico — tráfego pago NÃO iniciado. "
            "Nunca mencione Meta Ads, CPC, CPM, ROAS ou CPA. "
            "Foco: Instagram, Pinterest, SEO, parcerias gratuitas, UGC, conteúdo viral."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Crie o PLANO COMPLETO DE CRESCIMENTO ORGÂNICO para o lançamento:\n\n"
            "1. INSTAGRAM @auras.decore:\n"
            "   - Melhor horário de post para decoração BR (com base em dados)\n"
            "   - Mix ideal de conteúdo: % feed, % reels, % stories\n"
            "   - 5 hashtags de nicho com alto potencial orgânico\n"
            "   - Meta de seguidores: semana 1, semana 4, mês 3\n\n"
            "2. PINTEREST orgânico:\n"
            "   - 3 boards para criar (nomes + descrição SEO)\n"
            "   - Frequência de pins recomendada\n"
            "   - Keywords de SEO para Pinterest japandi BR\n\n"
            "3. SEO GOOGLE:\n"
            "   - Top 5 termos para ranquear organicamente\n"
            "   - Estratégia de blog: 1 post/semana, quais temas\n\n"
            "4. PARCERIAS ORGÂNICAS GRATUITAS:\n"
            "   - 3 perfis de micro-influencer para abordar (nicho + tamanho ideal)\n"
            "   - Template de abordagem para permuta/collab\n\n"
            "5. MÉTRICA CHAVE da semana: qual número monitorar?\n\n"
            "Entregue plano acionável, sem custo de mídia."
        ),
    },

    {
        "id": "mar_sab_sol",
        "agent": "sol",
        "day": "sabado",
        "area": "site",
        "order": 5,
        "title": "SOL · Otimização de conversão — páginas produto + checkout",
        "needs_approval": True,
        "max_tokens": 600,
        "system": (
            "Você é SOL — especialista em CRO da Aura Decore. "
            "Transforma visitantes em compradores removendo fricção e adicionando gatilhos certos. "
            "Foco em mobile-first, página de produto e checkout."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Execute a OTIMIZAÇÃO DE CONVERSÃO completa:\n\n"
            "1. Checklist de CRO para página de produto:\n"
            "   □ Social proof (avaliações, número de clientes, UGC)\n"
            "   □ Urgência (estoque limitado, frete grátis acima R$199)\n"
            "   □ Garantia de devolução (prazo, facilidade)\n"
            "   □ Botão CTA acima do fold (mobile)\n"
            "   □ Fotos de produto: mínimo 4, inclui foto em uso\n"
            "   □ FAQ inline (remove dúvidas sem sair da página)\n\n"
            "2. Sequência de recovery de carrinho:\n"
            "   Email D+1: headline, copy, CTA, cupom (AURA10?)\n"
            "   Email D+3: urgência + benefícios\n"
            "   Email D+7: oferta final\n\n"
            "3. Upsell strategy:\n"
            "   - Produto complementar sugerido no checkout\n"
            "   - Bundle com desconto (ex: vaso + flores secas + bandeja)\n\n"
            "4. Frete grátis: qual threshold funciona para margem 55%?\n"
            "5. Top 3 melhorias de UX para implementar hoje no tema Dawn\n\n"
            "Eduardo aprovará sequência de emails e bundles antes de implementar."
        ),
    },

    {
        "id": "mar_sab_zara",
        "agent": "zara",
        "day": "sabado",
        "area": "social",
        "order": 6,
        "title": "ZARA · Community building — DMs, influencers, engajamento",
        "needs_approval": False,
        "max_tokens": 600,
        "system": (
            "Você é ZARA — gestora de comunidade Instagram da Aura Decore. "
            "Especialista em crescimento orgânico, UGC, micro-influencers e engajamento. "
            "A comunidade Aura Decore é cuidadosa, elegante e autêntica."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Crie a ESTRATÉGIA DE COMMUNITY BUILDING:\n\n"
            "1. DM de boas-vindas para novos seguidores:\n"
            "   - Mensagem calorosa, curta (3-4 linhas), sem spam\n"
            "   - Oferece desconto de boas-vindas: AURA15\n\n"
            "2. Template de resposta para comentários:\n"
            "   a) Elogio ao produto\n"
            "   b) Pergunta sobre preço/frete\n"
            "   c) Pedindo indicação de produto\n\n"
            "3. Lista de 10 micro-influencers para abordar:\n"
            "   Critérios: 5k-50k seguidores, decoração/lifestyle/minimalismo, engajamento >3%\n"
            "   Texto de abordagem: proposta de parceria (produto + comissão ou permuta)\n\n"
            "4. Hashtag strategy:\n"
            "   - 15 hashtags nicho para posts (menor concorrência, mais qualificadas)\n"
            "   - 5 hashtags virais para alcance\n"
            "   - 3 hashtags próprias da marca\n\n"
            "5. Ação de UGC: como incentivar clientes a postar fotos?\n"
            "   (cupom, repost, destaque nos stories)"
        ),
    },

    {
        "id": "mar_sab_feed",
        "agent": "feed",
        "day": "sabado",
        "area": "social",
        "order": 7,
        "title": "FEED · Programação de posts — Instagram e Facebook",
        "needs_approval": True,
        "max_tokens": 500,
        "system": (
            "Você é FEED — responsável pela publicação nas redes sociais da Aura Decore. "
            "Publica no Instagram (@auras.decore) e Facebook da Aura Decore. "
            "Garante consistência visual, horários estratégicos e engajamento."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Organize a PROGRAMAÇÃO DE POSTS para o sábado e domingo:\n\n"
            "Baseado no conteúdo produzido pelo NOX e imagens do ARTE:\n\n"
            "SÁBADO:\n"
            "- 9h: Post produto destaque no Instagram (feed) — imagem ARTE + copy VERA\n"
            "- 14h: Reel 'Japandi 101' — roteiro NOX\n"
            "- 19h: Story produto com swipe-up para loja\n"
            "- Facebook: 1 post lifestyle (14h)\n\n"
            "DOMINGO:\n"
            "- 10h: Carrossel '5 formas de trazer calma para sua casa'\n"
            "- 16h: Story 'bastidores' — equipe trabalhando / unboxing produto\n"
            "- 19h: Post com CTA direto para loja\n\n"
            "Para cada post: caption final (copy VERA), hashtags (ZARA), imagem (ARTE), "
            "horário, plataforma, link de destino.\n\n"
            "Eduardo aprovará a fila de posts antes de FEED publicar."
        ),
    },

    # ════════════════════════════════════════════════
    # DOMINGO — Finalização & Decisões
    # ════════════════════════════════════════════════

    {
        "id": "mar_dom_lena",
        "agent": "lena",
        "day": "domingo",
        "area": "operacoes",
        "order": 1,
        "title": "LENA · Atendimento — templates SAC + pós-venda",
        "needs_approval": False,
        "max_tokens": 600,
        "system": (
            "Você é LENA — gestora de atendimento ao cliente da Aura Decore. "
            "Cria experiências de compra memoráveis com suporte humanizado. "
            "Tom: acolhedor, elegante, resolutivo. Reflete os valores wabi-sabi da marca."
        ),
        "user": (
            f"Data: {_today()} — MARATONA FIM DE SEMANA\n\n"
            "Crie o KIT COMPLETO DE ATENDIMENTO:\n\n"
            "1. 5 templates de resposta para situações frequentes:\n"
            "   a) Prazo de entrega — cliente ansioso\n"
            "   b) Produto diferente da foto\n"
            "   c) Dúvida sobre tamanho/medidas\n"
            "   d) Pedido de troca/devolução\n"
            "   e) Elogio — como transformar em UGC?\n\n"
            "2. Sequência pós-venda (3 emails automáticos):\n"
            "   Email 1 (confirmação): 'Seu lar vai ficar ainda mais bonito'\n"
            "   Email 2 (D+3, rastreamento): atualização + dica de styling\n"
            "   Email 3 (D+7, entrega): convite para avaliar + próximo produto\n\n"
            "3. FAQ para a página da loja (8 perguntas mais comuns):\n"
            "   Frete, prazo, troca, garantia, formas de pagamento\n\n"
            "4. Política de devolução para o site (texto final, confiança + clareza)"
        ),
    },

    {
        "id": "mar_dom_echo",
        "agent": "echo",
        "day": "domingo",
        "area": "operacoes",
        "order": 2,
        "title": "ECHO · Auditoria geral da maratona — score e gaps",
        "needs_approval": False,
        "max_tokens": 700,
        "system": (
            "Você é ECHO — auditor e analista de qualidade da Aura Decore. "
            "Avalia o trabalho de todos os agentes com critério e objetividade. "
            "Identifica gaps, inconsistências e prioridades para a próxima semana."
        ),
        "user": (
            f"Data: {_today()} — ENCERRAMENTO DA MARATONA\n\n"
            "Execute a AUDITORIA COMPLETA da maratona do fim de semana:\n\n"
            "Avalie cada área entregue (nota 0-10 e status: ✅ Pronto / ⚠️ Parcial / ❌ Pendente):\n\n"
            "SITE:\n"
            "□ Copy completa (VERA) — textos aprovados e prontos para Shopify?\n"
            "□ SEO implementado (MIRA/THEO) — meta tags, alt text, sitemap?\n"
            "□ Imagens prontas (ARTE) — hero, produtos, banners?\n"
            "□ CRO implementado (SOL) — CTAs, social proof, urgência?\n"
            "□ Técnico OK (THEO) — pixel, checkout, velocidade?\n\n"
            "REDES SOCIAIS:\n"
            "□ Calendário criado (NOX) — 7 dias programados?\n"
            "□ Posts sábado/domingo publicados (FEED)?\n"
            "□ Community ativo (ZARA) — influencers abordados, templates prontos?\n\n"
            "PRODUTO:\n"
            "□ 5 produtos estrela curados (KAI)?\n"
            "□ Preços aprovados (GUARD)?\n"
            "□ Fornecedores validados (NEXUS)?\n\n"
            "MARKETING:\n"
            "□ Estrutura Meta Ads pronta (REX)?\n"
            "□ Recovery carrinho configurado (SOL/LENA)?\n"
            "□ Automações ativas (PIPE)?\n\n"
            "ENTREGUE: Relatório de prontidão para lançamento + lista de 5 itens críticos pendentes."
        ),
    },

    {
        "id": "mar_dom_ive",
        "agent": "ive",
        "day": "domingo",
        "area": "operacoes",
        "order": 3,
        "title": "IVE · Relatório executivo — plano de lançamento definitivo",
        "needs_approval": True,
        "max_tokens": 800,
        "system": (
            "Você é IVE — CEO da Aura Decore e coordenadora dos 17 agentes. "
            "Integra todas as entregas do fim de semana em um plano executivo claro. "
            "Eduardo tomará as decisões finais com base no seu relatório."
        ),
        "user": (
            f"Data: {_today()} — RELATÓRIO FINAL DA MARATONA\n\n"
            "Gere o RELATÓRIO EXECUTIVO DA MARATONA para Eduardo:\n\n"
            "RESUMO DO FIM DE SEMANA:\n"
            "O que foi produzido por cada agente (1 linha cada)\n\n"
            "ESTADO ATUAL DA LOJA (avaliação honesta):\n"
            "- O que está 100% pronto para lançar?\n"
            "- O que precisa de aprovação de Eduardo?\n"
            "- O que ainda falta?\n\n"
            "PLANO DE AÇÃO — PRÓXIMA SEMANA:\n"
            "Dia a dia: o que cada agente vai executar (seg-sex)\n\n"
            "DECISÕES QUE PRECISAM DE EDUARDO:\n"
            "Liste as 5 decisões mais importantes que só Eduardo pode tomar.\n"
            "Para cada uma: contexto, opção A vs B, recomendação da IVE.\n\n"
            "DATA SUGERIDA DE LANÇAMENTO: quando a loja deve abrir?\n\n"
            "Seja direta. Eduardo tem 10 minutos para ler isso. "
            "Termine com: 'A Aura Decore está pronta para [X]. Sua decisão, Eduardo.'"
        ),
    },
]


# ── Storage em memória (estado da maratona) ───────────────────────────────────

_MARATHON_STATE: dict = {
    "active": False,
    "started_at": None,
    "tasks": {},          # id → {status, result, approved, started_at, done_at}
    "decisions": [],      # lista de {task_id, title, agent, result, created_at}
}


def marathon_init():
    """Inicializa o estado de todas as tarefas como 'pendente'."""
    for task in MARATHON_TASKS:
        _MARATHON_STATE["tasks"][task["id"]] = {
            "status": "pendente",
            "result": "",
            "approved": None,
            "started_at": None,
            "done_at": None,
        }
    _MARATHON_STATE["active"] = True
    _MARATHON_STATE["started_at"] = datetime.now(BRT).strftime("%Y-%m-%d %H:%M BRT")


def marathon_get_task(task_id: str) -> dict | None:
    return next((t for t in MARATHON_TASKS if t["id"] == task_id), None)


def marathon_set_status(task_id: str, status: str, result: str = ""):
    if task_id in _MARATHON_STATE["tasks"]:
        _MARATHON_STATE["tasks"][task_id]["status"] = status
        if result:
            _MARATHON_STATE["tasks"][task_id]["result"] = result
        if status == "rodando":
            _MARATHON_STATE["tasks"][task_id]["started_at"] = datetime.now(BRT).strftime("%H:%M")
        elif status in ("concluido", "aguardando_aprovacao"):
            _MARATHON_STATE["tasks"][task_id]["done_at"] = datetime.now(BRT).strftime("%H:%M")


def marathon_approve(task_id: str, approved: bool):
    if task_id in _MARATHON_STATE["tasks"]:
        _MARATHON_STATE["tasks"][task_id]["approved"] = approved
        _MARATHON_STATE["tasks"][task_id]["status"] = "aprovado" if approved else "rejeitado"
    # Remove da fila de decisões
    _MARATHON_STATE["decisions"] = [
        d for d in _MARATHON_STATE["decisions"] if d["task_id"] != task_id
    ]


def marathon_add_decision(task_id: str, title: str, agent: str, result: str):
    _MARATHON_STATE["decisions"].append({
        "task_id": task_id,
        "title": title,
        "agent": agent.upper(),
        "result": result[:800],
        "created_at": datetime.now(BRT).strftime("%H:%M"),
    })


def marathon_status_json() -> dict:
    """Retorna status completo para o frontend."""
    tasks_out = []
    for task in MARATHON_TASKS:
        state = _MARATHON_STATE["tasks"].get(task["id"], {})
        tasks_out.append({
            "id": task["id"],
            "agent": task["agent"].upper(),
            "day": task["day"],
            "area": task["area"],
            "order": task["order"],
            "title": task["title"],
            "needs_approval": task["needs_approval"],
            "status": state.get("status", "pendente"),
            "result": state.get("result", "")[:300],
            "approved": state.get("approved"),
            "started_at": state.get("started_at"),
            "done_at": state.get("done_at"),
        })

    total = len(MARATHON_TASKS)
    done = sum(1 for t in tasks_out if t["status"] in ("concluido", "aprovado"))
    running = sum(1 for t in tasks_out if t["status"] == "rodando")
    waiting = sum(1 for t in tasks_out if t["status"] == "aguardando_aprovacao")

    return {
        "active": _MARATHON_STATE["active"],
        "started_at": _MARATHON_STATE["started_at"],
        "progress": {"total": total, "done": done, "running": running, "waiting_approval": waiting},
        "tasks": tasks_out,
        "decisions": _MARATHON_STATE["decisions"],
    }
