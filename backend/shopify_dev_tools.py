# -*- coding: utf-8 -*-
"""
Ferramentas de desenvolvimento Shopify para o agente DEV.
Permite ao DEV agente ler/escrever assets de tema, settings, colecoes,
paginas e executar sprints de melhoria autonomos.

APIs usadas: Shopify Admin REST 2025-01
"""
from __future__ import annotations
import os
import json
import re
import datetime
import httpx
from crewai.tools import BaseTool

SHOPIFY_DOMAIN = os.getenv("SHOPIFY_DOMAIN", "")
SHOPIFY_TOKEN  = os.getenv("SHOPIFY_ADMIN_TOKEN", "")
LIVE_THEME_ID  = os.getenv("SHOPIFY_LIVE_THEME_ID", "").split("/")[-1]
STAGING_ID     = os.getenv("SHOPIFY_STAGING_THEME_ID", "").split("/")[-1]

BASE_URL = f"https://{SHOPIFY_DOMAIN}/admin/api/2025-01" if SHOPIFY_DOMAIN else ""
HEADERS  = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}

# ── Calendário sazonal japandi para mercado brasileiro ───────────────────────

SEASONAL_CALENDAR: dict[tuple, dict] = {
    (1, 2): {
        "slug": "comeco_de_ano",
        "nome": "Começo de Ano — Detox e Intenção",
        "paleta_accent": "#8B9E8E",       # verde-cinza menta
        "hero_headline": "Comece o ano com leveza.",
        "hero_subheadline": "Organize, respire e crie o seu espaço de calma.",
        "announcement": "Novo ano, nova casa. Frete grátis acima R$199.",
        "colecao_destaque": "Organização & Detox",
        "produtos_foco": ["bandeja", "vaso", "difusor", "linho"],
        "prompt_hero": "minimalist japandi living room new year intention setting, "
                        "fresh green plants, natural light, clean white surfaces, "
                        "morning calm atmosphere, ceramic vase, wabi-sabi",
        "css_accent": "#8B9E8E",
        "tags_sazonais": ["novo-ano", "detox", "organizacao"],
    },
    (3, 4): {
        "slug": "outono_japandi",
        "nome": "Outono — Cores da Terra",
        "paleta_accent": "#B8793A",
        "hero_headline": "O outono mora em cada detalhe.",
        "hero_subheadline": "Tons quentes, texturas naturais e a calma da mudança.",
        "announcement": "Outono na sua casa. Vasos e plantas secas com frete grátis.",
        "colecao_destaque": "Outono Japandi",
        "produtos_foco": ["vaso", "pampas", "vela", "bambu"],
        "prompt_hero": "japandi autumn living room, dried pampas grass, terracotta ceramic vase, "
                        "warm amber light, wooden surface, fall leaves, cozy minimal atmosphere",
        "css_accent": "#B8793A",
        "tags_sazonais": ["outono", "cores-terra", "sazonalidade"],
    },
    (5, 6): {
        "slug": "inverno_aconchego",
        "nome": "Inverno — Aconchego e Ritual",
        "paleta_accent": "#6B7280",
        "hero_headline": "O frio pede um lar mais bonito.",
        "hero_subheadline": "Velas, difusores e texturas que aquecem qualquer ambiente.",
        "announcement": "Inverno em casa: kit vela + difusor com 10% OFF.",
        "colecao_destaque": "Inverno & Aconchego",
        "produtos_foco": ["vela", "difusor", "almofada", "manta"],
        "prompt_hero": "cozy japandi winter interior, burning candle soft light, "
                        "linen cushions, reed diffuser, warm minimal atmosphere, "
                        "wooden textures, wabi-sabi calm",
        "css_accent": "#5C6B73",
        "tags_sazonais": ["inverno", "aconchego", "ritual"],
    },
    (7, 8): {
        "slug": "renovacao_lar",
        "nome": "Renovação — Novo Ciclo",
        "paleta_accent": "#A67B5B",
        "hero_headline": "Renove seu espaço. Renove você.",
        "hero_subheadline": "Cada objeto com significado. Cada detalhe com intenção.",
        "announcement": "Semana da renovação: 15% OFF em itens selecionados.",
        "colecao_destaque": "Renovação & Estilo",
        "produtos_foco": ["vaso", "linho", "bandeja", "pedra"],
        "prompt_hero": "japandi home renovation refresh, new interior decoration, "
                        "ceramic vases, linen textiles, natural stone, bright morning light, "
                        "minimal clean space ready for new chapter",
        "css_accent": "#A67B5B",
        "tags_sazonais": ["renovacao", "novo-ciclo", "decoracao"],
    },
    (9, 10): {
        "slug": "primavera_bloom",
        "nome": "Primavera — Florescer Natural",
        "paleta_accent": "#9DB88A",
        "hero_headline": "A primavera entra pela porta.",
        "hero_subheadline": "Flores, cerâmica e a leveza do que está vivo.",
        "announcement": "Primavera: kits florais e cerâmicas com frete grátis.",
        "colecao_destaque": "Primavera Japandi",
        "produtos_foco": ["vaso", "flores", "ceramica", "verde"],
        "prompt_hero": "japandi spring interior, cherry blossom branch in ceramic vase, "
                        "soft green plants, natural light, fresh minimal atmosphere, "
                        "wabi-sabi spring bloom, earthy tones",
        "css_accent": "#9DB88A",
        "tags_sazonais": ["primavera", "bloom", "flores"],
    },
    (11, 12): {
        "slug": "natal_japandi",
        "nome": "Fim de Ano — Presentes com Alma",
        "paleta_accent": "#8B6F5C",
        "hero_headline": "Presentes que ficam. Momentos que importam.",
        "hero_subheadline": "Kits exclusivos para quem você ama — com a alma do Japandi.",
        "announcement": "Natal Japandi: kits presente com embalagem especial. Frete grátis.",
        "colecao_destaque": "Presentes Japandi",
        "produtos_foco": ["kit", "vela", "difusor", "ceramica"],
        "prompt_hero": "japandi christmas gift set, minimal festive decoration, "
                        "ceramic vessels, linen wrapping, pine branches, "
                        "warm candlelight, gift boxes natural materials, cozy premium",
        "css_accent": "#8B6F5C",
        "tags_sazonais": ["natal", "presentes", "fim-de-ano"],
    },
}

def get_current_season() -> dict:
    """Retorna a config sazonal do mes atual."""
    month = datetime.datetime.now().month
    for (m1, m2), config in SEASONAL_CALENDAR.items():
        if m1 <= month <= m2:
            return config
    return SEASONAL_CALENDAR[(11, 12)]  # fallback

def get_season_by_slug(slug: str) -> dict | None:
    for config in SEASONAL_CALENDAR.values():
        if config["slug"] == slug:
            return config
    return None


def _shopify_ok() -> bool:
    return bool(SHOPIFY_DOMAIN and SHOPIFY_TOKEN)


def _get(path: str, params: dict | None = None) -> dict:
    with httpx.Client(timeout=20) as hc:
        r = hc.get(f"{BASE_URL}{path}", headers=HEADERS, params=params)
        return r.json()


def _put(path: str, payload: dict) -> dict:
    with httpx.Client(timeout=30) as hc:
        r = hc.put(f"{BASE_URL}{path}", headers=HEADERS, json=payload)
        return r.json()


def _post(path: str, payload: dict) -> dict:
    with httpx.Client(timeout=30) as hc:
        r = hc.post(f"{BASE_URL}{path}", headers=HEADERS, json=payload)
        return r.json()


# ── Ferramenta 1: Ler/escrever assets do tema ─────────────────────────────────

class ShopifyThemeAssetTool(BaseTool):
    name: str = "ShopifyThemeAsset"
    description: str = (
        "Le ou escreve um asset no tema Shopify (CSS, JS, Liquid, JSON). "
        "Input JSON: {\"action\": \"read|write\", \"theme\": \"live|staging\", "
        "\"key\": \"assets/custom.css\", \"value\": \"...conteudo...\"} "
        "Para 'read': retorna o conteudo atual do asset. "
        "Para 'write': atualiza o asset com o novo conteudo. "
        "Assets uteis: 'assets/base.css', 'config/settings_data.json', "
        "'sections/announcement-bar.liquid'"
    )

    def _run(self, input_str: str) -> str:
        if not _shopify_ok():
            return "Shopify nao configurado. Preencha SHOPIFY_DOMAIN e SHOPIFY_ADMIN_TOKEN no .env"
        try:
            data = json.loads(input_str)
        except Exception:
            return "Input invalido. Use JSON: {action, theme, key, value}"

        action = data.get("action", "read")
        theme  = data.get("theme", "staging")
        key    = data.get("key", "")
        value  = data.get("value", "")
        theme_id = STAGING_ID if theme == "staging" else LIVE_THEME_ID

        if not theme_id:
            return f"Theme ID nao configurado para '{theme}'. Verifique .env"

        try:
            if action == "read":
                result = _get(f"/themes/{theme_id}/assets.json", {"asset[key]": key})
                asset = result.get("asset", {})
                content = asset.get("value", asset.get("attachment", ""))
                return f"Asset '{key}' ({theme}):\n\n{content[:3000]}"
            else:
                payload = {"asset": {"key": key, "value": value}}
                result = _put(f"/themes/{theme_id}/assets.json", payload)
                if "asset" in result:
                    return f"Asset '{key}' atualizado no tema {theme}. Size: {result['asset'].get('size', '?')} bytes"
                return f"Erro: {result}"
        except Exception as e:
            return f"Erro ShopifyThemeAsset: {e}"


# ── Ferramenta 2: Atualizar settings do tema ─────────────────────────────────

class ShopifyThemeSettingsTool(BaseTool):
    name: str = "ShopifyThemeSettings"
    description: str = (
        "Le ou atualiza as configuracoes visuais do tema Shopify (settings_data.json). "
        "Input JSON: {\"action\": \"read|update\", \"theme\": \"staging\", "
        "\"updates\": {\"current\": {\"announcement_text\": \"...\"}}} "
        "Para 'read': retorna as settings atuais. "
        "Para 'update': mescla as updates com as settings existentes e salva. "
        "Use 'staging' para testar antes de publicar no live."
    )

    def _run(self, input_str: str) -> str:
        if not _shopify_ok():
            return "Shopify nao configurado."
        try:
            data = json.loads(input_str)
        except Exception:
            return "Input invalido."

        action   = data.get("action", "read")
        theme    = data.get("theme", "staging")
        updates  = data.get("updates", {})
        theme_id = STAGING_ID if theme == "staging" else LIVE_THEME_ID
        if not theme_id:
            return f"Theme ID nao configurado para '{theme}'."

        try:
            # Le settings atuais
            result = _get(f"/themes/{theme_id}/assets.json",
                          {"asset[key]": "config/settings_data.json"})
            raw = result.get("asset", {}).get("value", "{}")
            settings = json.loads(raw)

            if action == "read":
                # Retorna apenas o current (mais relevante)
                curr = settings.get("current", {})
                return f"Settings atuais ({theme}):\n{json.dumps(curr, indent=2, ensure_ascii=False)[:2000]}"

            # Mescla updates
            if "current" not in settings:
                settings["current"] = {}
            for k, v in updates.items():
                if isinstance(v, dict):
                    settings["current"].setdefault(k, {}).update(v)
                else:
                    settings["current"][k] = v

            new_value = json.dumps(settings, indent=2, ensure_ascii=False)
            save = _put(f"/themes/{theme_id}/assets.json",
                        {"asset": {"key": "config/settings_data.json", "value": new_value}})
            if "asset" in save:
                return f"Settings atualizadas no tema {theme}. Campos alterados: {list(updates.keys())}"
            return f"Erro ao salvar settings: {save}"
        except Exception as e:
            return f"Erro ShopifyThemeSettings: {e}"


# ── Ferramenta 3: Gerenciar colecoes ─────────────────────────────────────────

class ShopifyCollectionTool(BaseTool):
    name: str = "ShopifyCollection"
    description: str = (
        "Cria ou atualiza colecoes na loja Shopify. "
        "Input JSON: {\"action\": \"list|create|update\", \"id\": \"123\", "
        "\"title\": \"Titulo\", \"body_html\": \"<p>Descricao</p>\", "
        "\"image_url\": \"...\", \"sort_order\": \"best-selling\"} "
        "Para 'list': lista todas as colecoes com IDs. "
        "Para 'create': cria nova colecao. "
        "Para 'update': atualiza colecao existente pelo ID."
    )

    def _run(self, input_str: str) -> str:
        if not _shopify_ok():
            return "Shopify nao configurado."
        try:
            data = json.loads(input_str)
        except Exception:
            data = {"action": "list"}

        action = data.get("action", "list")
        try:
            if action == "list":
                r = _get("/custom_collections.json", {"limit": 20, "fields": "id,title,handle"})
                cols = r.get("custom_collections", [])
                if not cols:
                    return "Nenhuma colecao encontrada."
                return "\n".join([f"ID {c['id']}: {c['title']} (/{c['handle']})" for c in cols])

            elif action == "create":
                payload: dict = {"custom_collection": {
                    "title": data.get("title", "Nova Colecao"),
                    "body_html": data.get("body_html", ""),
                    "sort_order": data.get("sort_order", "best-selling"),
                }}
                if "image_url" in data:
                    payload["custom_collection"]["image"] = {"src": data["image_url"]}
                r = _post("/custom_collections.json", payload)
                col = r.get("custom_collection", {})
                if "id" in col:
                    return f"Colecao criada! ID: {col['id']} | Titulo: {col['title']}"
                return f"Erro: {r}"

            elif action == "update":
                col_id = data.get("id", "")
                if not col_id:
                    return "ID da colecao necessario para update."
                payload = {"custom_collection": {}}
                for field in ("title", "body_html", "sort_order"):
                    if field in data:
                        payload["custom_collection"][field] = data[field]
                if "image_url" in data:
                    payload["custom_collection"]["image"] = {"src": data["image_url"]}
                r = _put(f"/custom_collections/{col_id}.json", payload)
                col = r.get("custom_collection", {})
                if "id" in col:
                    return f"Colecao {col_id} atualizada: {col.get('title', '')}"
                return f"Erro: {r}"
        except Exception as e:
            return f"Erro ShopifyCollection: {e}"


# ── Ferramenta 4: CSS customizado sazonal ─────────────────────────────────────

class ShopifyCustomCSSInjector(BaseTool):
    name: str = "ShopifyCustomCSS"
    description: str = (
        "Injeta CSS customizado sazonal no tema Shopify. "
        "Input JSON: {\"season_slug\": \"outono_japandi|primavera_bloom|...\", "
        "\"custom_css\": \"/* CSS adicional */\", \"theme\": \"staging|live\"} "
        "Se season_slug fornecido, gera CSS baseado na paleta sazonal. "
        "Sempre testa no staging antes de publicar no live. "
        "Slugs disponiveis: comeco_de_ano, outono_japandi, inverno_aconchego, "
        "renovacao_lar, primavera_bloom, natal_japandi"
    )

    def _run(self, input_str: str) -> str:
        if not _shopify_ok():
            return "Shopify nao configurado."
        try:
            data = json.loads(input_str)
        except Exception:
            return "Input invalido."

        theme      = data.get("theme", "staging")
        slug       = data.get("season_slug", "")
        extra_css  = data.get("custom_css", "")
        theme_id   = STAGING_ID if theme == "staging" else LIVE_THEME_ID

        # Gera CSS sazonal baseado na paleta
        season_css = ""
        if slug:
            season = get_season_by_slug(slug)
            if season:
                accent = season["css_accent"]
                season_css = f"""
/* === Aura Decore — Tema Sazonal: {season['nome']} === */
:root {{
  --color-accent-sazonal: {accent};
  --color-button-primary: {accent};
}}
.button--primary,
.shopify-challenge__button {{
  background-color: {accent} !important;
  border-color: {accent} !important;
}}
.announcement-bar {{
  background-color: {accent} !important;
  color: #F5F0EB !important;
}}
.price {{ color: {accent}; }}
.badge--sale {{ background-color: {accent}; }}
/* Hover states */
a:hover {{ color: {accent}; }}
.header__active-menu-item {{ color: {accent}; }}
"""

        final_css = season_css + "\n" + extra_css
        if not final_css.strip():
            return "Nenhum CSS fornecido. Use season_slug ou custom_css."

        asset_key = "assets/aura-sazonal.css"

        # Adiciona o include no theme.liquid se necessario
        try:
            # Salva CSS
            save = _put(f"/themes/{theme_id}/assets.json",
                        {"asset": {"key": asset_key, "value": final_css}})
            if "errors" in save:
                return f"Erro ao salvar CSS: {save}"

            return (
                f"CSS sazonal '{slug or 'customizado'}' injetado no tema {theme}!\n"
                f"Arquivo: {asset_key}\n"
                f"Tamanho: {len(final_css)} chars\n"
                f"Acento: {season.get('css_accent', 'custom') if slug else 'custom'}\n"
                f"IMPORTANTE: Adicione '{{{{ 'aura-sazonal.css' | asset_url | stylesheet_tag }}}}' "
                f"no theme.liquid para ativar."
            )
        except Exception as e:
            return f"Erro ShopifyCustomCSS: {e}"


# ── Ferramenta 5: Atualizar announcement bar ─────────────────────────────────

class ShopifyAnnouncementTool(BaseTool):
    name: str = "ShopifyAnnouncement"
    description: str = (
        "Atualiza o banner de anuncio da loja (announcement bar) com texto sazonal. "
        "Input JSON: {\"text\": \"Texto do anuncio\", \"link\": \"/collections/all\", "
        "\"theme\": \"staging|live\"} "
        "Usa theme settings para atualizar o anuncio."
    )

    def _run(self, input_str: str) -> str:
        if not _shopify_ok():
            return "Shopify nao configurado."
        try:
            data = json.loads(input_str)
        except Exception:
            return "Input invalido."

        text     = data.get("text", "")
        link     = data.get("link", "/collections/all")
        theme    = data.get("theme", "staging")
        theme_id = STAGING_ID if theme == "staging" else LIVE_THEME_ID

        if not text:
            return "Texto do anuncio necessario."

        try:
            # Le settings atuais
            r = _get(f"/themes/{theme_id}/assets.json",
                     {"asset[key]": "config/settings_data.json"})
            raw  = r.get("asset", {}).get("value", "{}")
            sets = json.loads(raw)
            curr = sets.setdefault("current", {})

            # Atualiza announcement
            curr["announcement_text"] = text
            curr["announcement_link"] = link
            curr["show_announcement"] = True

            # Salva
            save = _put(f"/themes/{theme_id}/assets.json",
                        {"asset": {"key": "config/settings_data.json",
                                   "value": json.dumps(sets, ensure_ascii=False)}})
            if "asset" in save:
                return f"Announcement atualizado ({theme}): '{text[:80]}'"
            return f"Erro: {save}"
        except Exception as e:
            return f"Erro ShopifyAnnouncement: {e}"


# ── Ferramenta 6: Publicar tema staging → live ────────────────────────────────

class ShopifyPublishThemeTool(BaseTool):
    name: str = "ShopifyPublishTheme"
    description: str = (
        "Publica o tema staging como tema live da loja. "
        "Input JSON: {\"confirm\": true, \"reason\": \"motivo da publicacao\"} "
        "ATENCAO: Esta acao torna o staging o tema ativo para todos os visitantes. "
        "Sempre confirme que testou o staging antes de publicar. "
        "Requer {\"confirm\": true} explicitamente."
    )

    def _run(self, input_str: str) -> str:
        if not _shopify_ok():
            return "Shopify nao configurado."
        try:
            data = json.loads(input_str)
        except Exception:
            return "Input invalido."

        if not data.get("confirm", False):
            return (
                "CONFIRMACAO NECESSARIA. Passe {\"confirm\": true} para publicar o staging como live. "
                "Certifique-se de ter testado o staging_theme primeiro."
            )
        if not STAGING_ID:
            return "SHOPIFY_STAGING_THEME_ID nao configurado no .env"

        reason = data.get("reason", "atualizacao sazonal automatica")
        try:
            result = _put(f"/themes/{STAGING_ID}.json",
                          {"theme": {"id": STAGING_ID, "role": "main"}})
            if "theme" in result:
                return (
                    f"Tema staging publicado como live!\n"
                    f"Theme ID: {STAGING_ID}\n"
                    f"Motivo: {reason}\n"
                    f"Status: {result['theme'].get('role', '?')}"
                )
            return f"Erro ao publicar tema: {result}"
        except Exception as e:
            return f"Erro ShopifyPublishTheme: {e}"


# ── Ferramenta 7: Detector de sazonalidade ───────────────────────────────────

class SeasonDetectorTool(BaseTool):
    name: str = "SeasonDetector"
    description: str = (
        "Detecta a estacao/epoca atual e retorna config completa para atualizacao da loja. "
        "Input: 'atual' para a estacao de agora, ou slug especifico como 'natal_japandi'. "
        "Output: paleta, headline, anuncio, colecao destaque, produtos foco e prompt de imagem."
    )

    def _run(self, input_str: str) -> str:
        query = input_str.strip().lower()
        if query in ("atual", "current", "now", ""):
            season = get_current_season()
        else:
            season = get_season_by_slug(query) or get_current_season()

        return json.dumps(season, ensure_ascii=False, indent=2)


# ── Ferramenta 8: Sprint dev report ──────────────────────────────────────────

class ShopifyDevReportTool(BaseTool):
    name: str = "ShopifyDevReport"
    description: str = (
        "Gera um relatorio de estado atual da loja Shopify para o sprint de desenvolvimento. "
        "Input: 'full' para relatorio completo, 'quick' para resumo. "
        "Output: lista de produtos, colecoes, temas, paginas e recomendacoes de melhoria."
    )

    def _run(self, input_str: str) -> str:
        if not _shopify_ok():
            return (
                "SHOPIFY_ADMIN_TOKEN nao configurado.\n"
                "Para ativar: adicione SHOPIFY_ADMIN_TOKEN no .env\n"
                "Como obter: Shopify Admin → Configuracoes → Apps e canais → Desenvolver apps → "
                "Criar app → permissoes read_products, write_products, read_themes, write_themes, "
                "read_content, write_content"
            )

        lines = ["# Relatorio de Estado — Shopify Aura Decore\n"]
        season = get_current_season()
        lines.append(f"**Estacao atual**: {season['nome']}")
        lines.append(f"**Colecao sugerida**: {season['colecao_destaque']}")
        lines.append(f"**Announcement sugerido**: {season['announcement']}\n")

        try:
            # Produtos
            r_prod = _get("/products.json", {"limit": 20, "fields": "id,title,status,variants"})
            products = r_prod.get("products", [])
            lines.append(f"**Produtos**: {len(products)} encontrados")
            sem_img = sum(1 for p in products if not p.get("images"))
            if sem_img:
                lines.append(f"  ⚠ {sem_img} produto(s) sem imagem — ARTE pode gerar")

            # Colecoes
            r_col = _get("/custom_collections.json", {"limit": 20, "fields": "id,title"})
            collections = r_col.get("custom_collections", [])
            lines.append(f"**Colecoes**: {len(collections)} criadas")

            # Temas
            r_themes = _get("/themes.json")
            themes = r_themes.get("themes", [])
            for t in themes:
                role = "LIVE" if t.get("role") == "main" else "staging"
                lines.append(f"  [{role}] {t['name']} (ID: {t['id']})")

            lines.append("\n**Recomendacoes para este sprint:**")
            lines.append(f"1. Atualizar announcement bar: '{season['announcement']}'")
            lines.append(f"2. Criar/atualizar colecao '{season['colecao_destaque']}'")
            lines.append(f"3. Injetar CSS sazonal para acento {season['css_accent']}")
            lines.append(f"4. Gerar hero image: '{season['hero_headline']}'")
            if sem_img:
                lines.append(f"5. Gerar fotos para {sem_img} produtos sem imagem (via ARTE)")
            lines.append("6. Testar staging antes de publicar live")

            return "\n".join(lines)
        except Exception as e:
            lines.append(f"\nErro ao buscar dados: {e}")
            lines.append("Verifique se SHOPIFY_ADMIN_TOKEN esta correto no .env")
            return "\n".join(lines)


# ── Instancias prontas ────────────────────────────────────────────────────────

theme_asset    = ShopifyThemeAssetTool()
theme_settings = ShopifyThemeSettingsTool()
collection_mgr = ShopifyCollectionTool()
custom_css     = ShopifyCustomCSSInjector()
announcement   = ShopifyAnnouncementTool()
publish_theme  = ShopifyPublishThemeTool()
season_detector= SeasonDetectorTool()
dev_report     = ShopifyDevReportTool()

DEV_TOOLS = [
    dev_report, season_detector, theme_asset, theme_settings,
    collection_mgr, custom_css, announcement, publish_theme,
]
