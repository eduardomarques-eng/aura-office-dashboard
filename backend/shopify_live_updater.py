# -*- coding: utf-8 -*-
"""
shopify_live_updater.py — Agente DEV + THEO: atualização contínua da loja Shopify
Executa tarefas de melhoria automática, geração de imagens e otimização de conversão.

Subagentes:
  DEV  — melhorias técnicas, CSS, tema, velocidade
  THEO — catálogo, produtos, SEO, fichas técnicas
  VERA — copy automático para novos produtos
  ARTE — prompts de imagem e URLs Pollinations
  MIRA — SEO on-page, meta tags, alt text

Integrado ao full_throttle_scheduler do main.py.
"""
from __future__ import annotations

import asyncio
import json
import os
import pathlib
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Any

BRT = timezone(timedelta(hours=-3))


def _now() -> str:
    return datetime.now(BRT).strftime("%Y-%m-%d %H:%M BRT")


def _today() -> str:
    return datetime.now(BRT).strftime("%Y-%m-%d")


# ── Gerador de imagens Pollinations.ai ───────────────────────────────────────

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"

PRODUCT_IMAGE_PROMPTS = {
    "vaso": "ceramic japandi wabi-sabi vase matte glaze natural light white background product photography square 1:1",
    "bandeja": "minimalist bamboo or wood tray japandi natural texture white background product photography top view square",
    "difusor": "reed diffuser amber glass bottle rattan sticks natural minimal japandi white linen background product photography",
    "vela": "artisan soy candle amber jar warm light japandi minimal natural wax white background",
    "almofada": "linen natural cushion japandi minimal sofa white background soft light product photography",
    "quadro": "minimalist art print frame japandi wall decor white background product photography",
    "cesta": "natural rattan woven basket oval minimal japandi interior organization white background",
    "planta": "dried botanical arrangement pampas grass natural beige japandi minimal vase white background",
    "terracota": "terracotta ceramic plant pots natural earth tones minimal wabi-sabi white background product photography",
    "madeira": "natural wood minimalist home decor piece japandi aesthetic warm tones white background product photo",
    "incensario": "ceramic incense holder minimal matte white japandi zen meditation natural light white background",
    "lifestyle": "japandi living room corner serene minimal wooden furniture ceramic vase dried botanicals warm natural light",
    "hero": "luxury japandi interior home decor flat lay ceramic vase bamboo tray reed diffuser dried flowers linen background",
    "ambiente": "cozy japandi home corner minimal wooden shelf ceramic objects dried plants warm afternoon light",
}


def generate_pollinations_url(
    prompt: str,
    width: int = 1080,
    height: int = 1080,
    seed: int | None = None,
    model: str = "flux",
) -> str:
    """Gera URL do Pollinations.ai para o prompt dado."""
    encoded = urllib.parse.quote(prompt)
    url = f"{POLLINATIONS_BASE}/{encoded}?width={width}&height={height}&model={model}&nologo=true"
    if seed is not None:
        url += f"&seed={seed}"
    return url


def generate_product_images(product_type: str, product_title: str, seed_base: int = 100) -> list[dict]:
    """Gera lista de URLs de imagens para um produto."""
    key = next((k for k in PRODUCT_IMAGE_PROMPTS if k in product_type.lower() or k in product_title.lower()), "lifestyle")
    base_prompt = PRODUCT_IMAGE_PROMPTS[key]

    images = [
        {
            "url": generate_pollinations_url(
                f"{base_prompt}, professional studio photography, premium quality",
                seed=seed_base,
            ),
            "altText": f"{product_title} — Aura Decore",
            "type": "product_main",
        },
        {
            "url": generate_pollinations_url(
                f"{base_prompt}, lifestyle context, home environment, natural ambient light",
                seed=seed_base + 1,
            ),
            "altText": f"{product_title} em ambiente japandi — Aura Decore",
            "type": "product_lifestyle",
        },
        {
            "url": generate_pollinations_url(
                f"{base_prompt}, flat lay top view, linen background, editorial photography",
                seed=seed_base + 2,
            ),
            "altText": f"{product_title} flat lay — estilo japandi wabi-sabi",
            "type": "product_flatlay",
        },
    ]
    return images


# ── Tasks de melhoria automática ─────────────────────────────────────────────

# Cada task tem: id, agente, prioridade, descrição e função geradora de prompt
LIVE_IMPROVEMENT_TASKS = [

    # ── DEV: CSS e performance ───────────────────────────────────────────────
    {
        "id": "dev_aspect_ratio_fix",
        "agent": "dev",
        "priority": 1,
        "title": "DEV · Corrigir aspect ratio de imagens no tema Dawn",
        "system": (
            "Você é DEV, desenvolvedor Shopify da Aura Decore. "
            "Especialista em CSS, Liquid, tema Dawn. "
            "Foco em UX, performance e conversão."
        ),
        "user": (
            f"Data: {_today()}\n\n"
            "PROBLEMA CRÍTICO: imagens de produto estão sendo esticadas/deformadas no tema Dawn Shopify.\n\n"
            "SOLUÇÃO NECESSÁRIA — gere o CSS exato para adicionar ao tema:\n"
            "1. Corrigir aspect ratio 1:1 (quadrado) para todas as imagens de produto\n"
            "2. Usar object-fit: cover para preencher sem distorção\n"
            "3. Garantir que thumbnails de carrossel mantenham proporção\n"
            "4. Fix para mobile e desktop\n"
            "5. Onde exatamente adicionar no tema Dawn (qual arquivo CSS/Liquid)\n\n"
            "Entregue o CSS pronto para copiar e o caminho do arquivo no tema."
        ),
        "category": "site",
    },

    # ── DEV: Performance e conversão ─────────────────────────────────────────
    {
        "id": "dev_conversion_boost",
        "agent": "dev",
        "priority": 2,
        "title": "DEV · Melhorias CRO no tema Dawn — urgência e social proof",
        "system": (
            "Você é DEV, desenvolvedor Shopify da Aura Decore. "
            "Implemente melhorias de conversão no tema Dawn."
        ),
        "user": (
            f"Data: {_today()}\n\n"
            "Implemente as seguintes melhorias CRO no tema Shopify Dawn da Aura Decore:\n\n"
            "1. URGÊNCIA — badge 'Poucos em estoque' nas páginas de produto\n"
            "   CSS + Liquid snippet para mostrar quando inventory < 10\n\n"
            "2. SOCIAL PROOF — contador de 'X pessoas viram este produto hoje'\n"
            "   JavaScript simples para simular (número aleatório 8-47)\n\n"
            "3. FRETE GRÁTIS — barra de progresso 'Frete grátis acima de R$199'\n"
            "   HTML/CSS para header ou cart drawer\n\n"
            "4. STICKY ADD TO CART — botão fixo no scroll mobile\n"
            "   CSS + JS para page de produto\n\n"
            "Entregue snippets completos prontos para implementar."
        ),
        "category": "site",
    },

    # ── THEO: Auditoria e melhoria de produtos ────────────────────────────────
    {
        "id": "theo_product_audit",
        "agent": "theo",
        "priority": 1,
        "title": "THEO · Auditoria completa do catálogo — gaps e melhorias",
        "system": (
            "Você é THEO, gerente de catálogo Shopify da Aura Decore. "
            "Identifique gaps e oportunidades de melhoria nos produtos ativos."
        ),
        "user": (
            f"Data: {_today()}\n\n"
            "Faça a AUDITORIA DO CATÁLOGO Aura Decore:\n\n"
            "Produtos ativos conhecidos: Vaso Wabi-Sabi, Difusor Ambiente, Bandeja Bambu Zen, "
            "Arranjo Pampas, Porta-Objetos Madeira, Vela Soja Bambu, Potes Terracota, "
            "Painel Moss LED, Kit Ervas, Candeeiro Bambu, Bandeja Acácia, "
            "Incensário Ripple, Difusor Lavanda, Suporte Livros, Eucalipto Preservado, "
            "Cesta Rattan, Vela Pilar, Porta-Incenso Bambu, Arranjo Algodão Seco, "
            "Vaso Oval Minimalista.\n\n"
            "Identifique:\n"
            "1. Produtos que precisam de mais imagens (mín 3 por produto)\n"
            "2. Produtos sem compareAtPrice (oportunidade de urgência)\n"
            "3. Produtos com descrição muito curta (<150 palavras)\n"
            "4. Produtos que deveriam ter variantes mas não têm\n"
            "5. 3 produtos para adicionar AGORA para completar o catálogo\n\n"
            "Entregue relatório com ações específicas."
        ),
        "category": "produto",
    },

    # ── VERA: Copy otimizada ──────────────────────────────────────────────────
    {
        "id": "vera_copy_home",
        "agent": "vera",
        "priority": 1,
        "title": "VERA · Copy completa da Home Page — otimizada para conversão",
        "system": (
            "Você é VERA, copywriter da Aura Decore. "
            "Escreva textos que convertem visitantes em compradores. "
            "Tom: elegante, emocional, premium. Persona: mulheres 28-45."
        ),
        "user": (
            f"Data: {_today()}\n\n"
            "Escreva a COPY COMPLETA da Home Page da Aura Decore (auradecore.com.br):\n\n"
            "1. HERO (acima do fold):\n"
            "   - Headline principal (até 8 palavras, impacto emocional)\n"
            "   - Subheadline (até 20 palavras, benefício claro)\n"
            "   - CTA button text (máx 4 palavras)\n\n"
            "2. SEÇÃO 'NOSSA FILOSOFIA' (2 parágrafos, 80 palavras total)\n\n"
            "3. SEÇÃO 'COLEÇÕES EM DESTAQUE' (título + subtitle para 3 coleções:\n"
            "   Vasos & Cerâmicas / Aromáticos & Bem-estar / Botânica Seca)\n\n"
            "4. TRUST BADGES (4 elementos: frete, devolução, qualidade, artesanal)\n\n"
            "5. TESTIMONIAL PLACEHOLDER (3 depoimentos, 30 palavras cada, persona real)\n\n"
            "6. NEWSLETTER CTA (headline + subtítulo + placeholder input)\n\n"
            "Escreva em português BR, elegante e conversivo."
        ),
        "category": "site",
    },

    # ── MIRA: SEO e meta tags ─────────────────────────────────────────────────
    {
        "id": "mira_seo_products",
        "agent": "mira",
        "priority": 2,
        "title": "MIRA · SEO completo — meta tags para todos os produtos",
        "system": (
            "Você é MIRA, especialista SEO da Aura Decore. "
            "Domina Shopify SEO, keywords de cauda longa, meta tags otimizadas."
        ),
        "user": (
            f"Data: {_today()}\n\n"
            "Gere SEO COMPLETO para os 5 produtos principais da Aura Decore:\n\n"
            "Para cada produto, entregue:\n"
            "- Page Title (até 60 chars, keyword principal + marca)\n"
            "- Meta Description (até 155 chars, inclui CTA)\n"
            "- URL handle (lowercase, hifens, sem acentos)\n"
            "- Alt text padrão para imagens\n\n"
            "PRODUTOS:\n"
            "1. Vaso Cerâmica Wabi-Sabi — Textura Natural (R$129,90)\n"
            "2. Difusor de Ambiente Aura — Bambu & Aromas (R$119,90)\n"
            "3. Bandeja de Bambu Zen — Organização com Alma (R$79,90-139,90)\n"
            "4. Arranjo de Pampas e Trigo Seco (R$69,90-119,90)\n"
            "5. Vela Artesanal de Soja — Bambu & Cedro (R$89)\n\n"
            "Keywords alvo: decoração japandi, wabi-sabi, decoração minimalista, "
            "home decor natural, vaso cerâmica decorativo."
        ),
        "category": "site",
    },

    # ── ARTE: Geração de imagens lifestyle ────────────────────────────────────
    {
        "id": "arte_lifestyle_pack",
        "agent": "arte",
        "priority": 1,
        "title": "ARTE · Pack lifestyle — 10 imagens para produtos e redes",
        "system": (
            "Você é ARTE, criativo visual da Aura Decore. "
            "Especialista em prompts de imagem IA (Pollinations.ai, Flux model). "
            "Gera assets visuais de alta qualidade para e-commerce japandi."
        ),
        "user": (
            f"Data: {_today()}\n\n"
            "Gere 10 PROMPTS COMPLETOS de imagem para a Aura Decore:\n\n"
            "FORMATO: Para cada imagem, entregue:\n"
            "- Prompt completo em inglês (detalhado, 30-50 palavras)\n"
            "- URL Pollinations.ai pronta para usar\n"
            "- Uso recomendado (produto X, hero, social, etc)\n\n"
            "IMAGENS NECESSÁRIAS:\n"
            "1-3. Produtos principal sem foto (lifestyle environment)\n"
            "4-5. Hero banner da home (1200x600, wide)\n"
            "6-7. Posts Instagram (1080x1080, square)\n"
            "8-9. Stories (1080x1920, vertical)\n"
            "10. Facebook cover (1640x924)\n\n"
            "Estilo: japandi minimal, wabi-sabi, natural earth tones, "
            "warm soft light, premium e-commerce photography.\n"
            "URL base: https://image.pollinations.ai/prompt/{PROMPT_ENCODED}"
            "?width=W&height=H&model=flux&nologo=true"
        ),
        "category": "social",
    },
]


# ── Funções auxiliares ────────────────────────────────────────────────────────

def get_task_by_id(task_id: str) -> dict | None:
    return next((t for t in LIVE_IMPROVEMENT_TASKS if t["id"] == task_id), None)


def get_tasks_by_agent(agent: str) -> list[dict]:
    return [t for t in LIVE_IMPROVEMENT_TASKS if t["agent"] == agent.lower()]


def get_tasks_by_priority(max_priority: int = 1) -> list[dict]:
    return [t for t in LIVE_IMPROVEMENT_TASKS if t["priority"] <= max_priority]


# ── Status de melhorias executadas ───────────────────────────────────────────
_IMPROVEMENTS_DONE: set[str] = set()
_IMPROVEMENT_RESULTS: dict[str, dict] = {}


def mark_improvement_done(task_id: str, result: str, provider: str = ""):
    _IMPROVEMENTS_DONE.add(task_id)
    _IMPROVEMENT_RESULTS[task_id] = {
        "result": result,
        "provider": provider,
        "ts": datetime.now(BRT).strftime("%Y-%m-%d %H:%M"),
    }


def get_improvement_results() -> dict:
    return {
        "done": len(_IMPROVEMENTS_DONE),
        "total": len(LIVE_IMPROVEMENT_TASKS),
        "pending": [t["id"] for t in LIVE_IMPROVEMENT_TASKS if t["id"] not in _IMPROVEMENTS_DONE],
        "results": _IMPROVEMENT_RESULTS,
    }


# ── CSS fix para aspect ratio (gerado pelo DEV) ──────────────────────────────
SHOPIFY_ASPECT_RATIO_CSS = """
/* ── Aura Decore: Image Aspect Ratio Fix ── */
/* Corrige imagens esticadas/deformadas no tema Dawn */

/* Imagens de produto — mantém proporção 1:1 */
.product-media-container,
.product__media,
.media-gallery__item,
.product-single__photo-wrapper {
  aspect-ratio: 1 / 1 !important;
  overflow: hidden !important;
}

.product-media-container img,
.product__media img,
.media-gallery__item img,
.product-single__photo-wrapper img {
  width: 100% !important;
  height: 100% !important;
  object-fit: cover !important;
  object-position: center !important;
}

/* Cards de produto na collection page */
.card__media,
.card-wrapper .media,
.product-card__image-container {
  aspect-ratio: 1 / 1 !important;
  overflow: hidden !important;
}

.card__media img,
.card-wrapper .media img,
.product-card__image-container img {
  width: 100% !important;
  height: 100% !important;
  object-fit: cover !important;
  object-position: center top !important;
}

/* Thumbnails no carrossel de produto */
.thumbnail-slider__item,
.product__thumbnail {
  aspect-ratio: 1 / 1 !important;
  overflow: hidden !important;
}

.thumbnail-slider__item img,
.product__thumbnail img {
  object-fit: cover !important;
  width: 100% !important;
  height: 100% !important;
}

/* Hero banner — mantém proporção sem esticar */
.banner__media,
.hero__image-container {
  aspect-ratio: 16 / 7 !important;
  overflow: hidden !important;
}

.banner__media img,
.hero__image-container img {
  object-fit: cover !important;
  object-position: center !important;
}

/* Mobile — force square thumbnails */
@media (max-width: 750px) {
  .card__media,
  .card-wrapper .media {
    aspect-ratio: 4 / 5 !important;
  }
}
"""

# ── Snippets CRO (social proof, urgência, frete grátis) ──────────────────────
SHOPIFY_CRO_SNIPPETS = {
    "urgency_badge": """
{% comment %} Aura Decore: Urgência — Poucos em estoque {% endcomment %}
{% if product.available %}
  {% assign total_inventory = 0 %}
  {% for variant in product.variants %}
    {% assign total_inventory = total_inventory | plus: variant.inventory_quantity %}
  {% endfor %}
  {% if total_inventory > 0 and total_inventory <= 10 %}
    <div class="aura-urgency-badge">
      🔥 Apenas {{ total_inventory }} em estoque
    </div>
  {% elsif total_inventory == 0 %}
    <div class="aura-urgency-badge aura-urgency-low">
      ⚡ Últimas unidades
    </div>
  {% endif %}
{% endif %}

<style>
.aura-urgency-badge {
  display: inline-block;
  background: rgba(224, 82, 82, 0.1);
  border: 1px solid rgba(224, 82, 82, 0.4);
  color: #E05252;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 20px;
  margin: 8px 0;
}
.aura-urgency-low {
  background: rgba(180, 148, 90, 0.1);
  border-color: rgba(180, 148, 90, 0.4);
  color: #B4945A;
}
</style>
""",

    "social_proof_counter": """
{% comment %} Aura Decore: Social Proof Counter {% endcomment %}
<div id="aura-viewers" style="display:none;font-size:12px;color:#6A5E52;margin:6px 0;">
  👁 <span id="aura-viewer-count">0</span> pessoas viram este produto hoje
</div>

<script>
(function() {
  const count = Math.floor(Math.random() * 40) + 8; // 8-47
  const el = document.getElementById('aura-viewer-count');
  const wrap = document.getElementById('aura-viewers');
  if (el && wrap) {
    el.textContent = count;
    wrap.style.display = 'block';
    // Incrementa lentamente para parecer real
    setInterval(function() {
      if (Math.random() > 0.7) {
        const curr = parseInt(el.textContent);
        el.textContent = curr + 1;
      }
    }, 15000);
  }
})();
</script>
""",

    "free_shipping_bar": """
{% comment %} Aura Decore: Frete Grátis Progress Bar {% endcomment %}
{% assign free_shipping_threshold = 19900 %} {% comment %} R$199 em centavos {% endcomment %}
{% assign cart_total = cart.total_price %}
{% assign remaining = free_shipping_threshold | minus: cart_total %}

<div class="aura-shipping-bar">
  {% if remaining > 0 %}
    <div class="aura-shipping-bar__text">
      Falta <strong>R$ {{ remaining | money_without_currency }}</strong> para frete grátis 🌿
    </div>
    <div class="aura-shipping-bar__track">
      {% assign progress = cart_total | times: 100 | divided_by: free_shipping_threshold %}
      <div class="aura-shipping-bar__fill" style="width: {{ progress | at_most: 100 }}%;"></div>
    </div>
  {% else %}
    <div class="aura-shipping-bar__text aura-shipping-bar--earned">
      ✓ Frete grátis conquistado! 🎉
    </div>
  {% endif %}
</div>

<style>
.aura-shipping-bar { padding: 8px 16px; background: rgba(180,148,90,.08); border-bottom: 1px solid rgba(180,148,90,.2); text-align: center; font-size: 13px; color: #6A5E52; }
.aura-shipping-bar__track { height: 4px; background: #E8E0D4; border-radius: 2px; margin: 4px auto; max-width: 200px; overflow: hidden; }
.aura-shipping-bar__fill { height: 100%; background: linear-gradient(90deg, #B8793A, #D4AF72); border-radius: 2px; transition: width .5s ease; }
.aura-shipping-bar--earned { color: #4CAF82; font-weight: 600; }
</style>
""",

    "sticky_add_to_cart": """
{% comment %} Aura Decore: Sticky Add to Cart (mobile) {% endcomment %}
<div id="aura-sticky-cart" class="aura-sticky-cart">
  <div class="aura-sticky-cart__info">
    <span class="aura-sticky-cart__title">{{ product.title | truncate: 30 }}</span>
    <span class="aura-sticky-cart__price">{{ product.selected_or_first_available_variant.price | money }}</span>
  </div>
  <button type="button" class="aura-sticky-cart__btn" onclick="document.querySelector('[name=add]')?.click()">
    Adicionar ao Carrinho
  </button>
</div>

<style>
@media (max-width: 768px) {
  .aura-sticky-cart {
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 999;
    background: #F5F0EB; border-top: 1px solid #D4C4A8;
    padding: 10px 16px; display: flex; align-items: center;
    gap: 12px; box-shadow: 0 -4px 20px rgba(0,0,0,.1);
    transform: translateY(100%); transition: transform .3s ease;
  }
  .aura-sticky-cart.visible { transform: translateY(0); }
  .aura-sticky-cart__info { flex: 1; }
  .aura-sticky-cart__title { display: block; font-size: 12px; color: #6A5E52; }
  .aura-sticky-cart__price { font-size: 16px; font-weight: 700; color: #B8793A; }
  .aura-sticky-cart__btn {
    background: #B8793A; color: white; border: none; border-radius: 6px;
    padding: 10px 18px; font-size: 13px; font-weight: 600; cursor: pointer;
    white-space: nowrap;
  }
}
@media (min-width: 769px) { .aura-sticky-cart { display: none !important; } }
</style>

<script>
(function() {
  const sticky = document.getElementById('aura-sticky-cart');
  if (!sticky) return;
  let lastScroll = 0;
  window.addEventListener('scroll', function() {
    const currentScroll = window.scrollY;
    if (currentScroll > 400) sticky.classList.add('visible');
    else sticky.classList.remove('visible');
    lastScroll = currentScroll;
  });
})();
</script>
""",
}
