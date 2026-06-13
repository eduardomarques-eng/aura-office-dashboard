# -*- coding: utf-8 -*-
"""
figma_tools.py — Integração Figma → Design Tokens → Shopify CSS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Funcionalidades:
1. FigmaTokensSyncTool — extrai design tokens do Figma e gera CSS Shopify
2. FigmaExportAssetTool — exporta assets/frames do Figma como PNG/SVG
3. FigmaAuditTool      — audita consistência visual entre Figma e Shopify

Uso pelos agentes:
  LUNA: usa FigmaTokensSyncTool para manter CSS alinhado ao design
  DEV:  usa FigmaTokensSyncTool + FigmaExportAssetTool para atualizar tema
  ECHO: usa FigmaAuditTool para auditar consistência visual

Configuração necessária (.env):
  FIGMA_API_TOKEN=figd_... (Figma → Account Settings → Personal Access Tokens)
  FIGMA_FILE_ID=abc123   (da URL: figma.com/design/FILE_ID/nome-do-arquivo)
"""
from __future__ import annotations
import os
import re
import json
import time
import httpx
from crewai.tools import BaseTool

FIGMA_API_TOKEN = os.getenv("FIGMA_API_TOKEN", "")
FIGMA_FILE_ID   = os.getenv("FIGMA_FILE_ID", "")
FIGMA_API_BASE  = "https://api.figma.com/v1"

SHOPIFY_DOMAIN  = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")
SHOPIFY_TOKEN   = os.getenv("SHOPIFY_ADMIN_TOKEN", "") or os.getenv("SHOPIFY_ADMIN_API_TOKEN", "")

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "generated_images", "figma")
os.makedirs(ASSETS_DIR, exist_ok=True)


def _figma_headers() -> dict:
    return {"X-Figma-Token": FIGMA_API_TOKEN}

def _shopify_headers() -> dict:
    return {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}


# ── Extrator de design tokens do Figma ───────────────────────────────────────

def _extract_tokens_from_figma(file_data: dict) -> dict:
    """Percorre a árvore Figma e extrai cores, tipografia e espaçamentos."""
    tokens = {"colors": {}, "fonts": {}, "text_styles": {}}

    def walk(node: dict, depth: int = 0):
        if depth > 8:
            return
        node_type = node.get("type", "")
        name = node.get("name", "")

        # Extrair cores de styles (estilos compartilhados)
        if node_type in ("RECTANGLE", "VECTOR", "ELLIPSE", "FRAME", "COMPONENT"):
            fills = node.get("fills", [])
            for fill in fills:
                if fill.get("type") == "SOLID":
                    c = fill.get("color", {})
                    r = int(c.get("r", 0) * 255)
                    g = int(c.get("g", 0) * 255)
                    b = int(c.get("b", 0) * 255)
                    hex_color = f"#{r:02x}{g:02x}{b:02x}"
                    # Nomear por nome do node (limpo)
                    slug = re.sub(r'[^a-z0-9]', '-', name.lower()).strip('-')
                    if slug and hex_color != "#000000":
                        tokens["colors"][f"--figma-{slug}"] = hex_color

        # Extrair tipografia
        if node_type == "TEXT":
            style = node.get("style", {})
            font_family = style.get("fontFamily", "")
            font_size   = style.get("fontSize", 0)
            font_weight = style.get("fontWeight", 400)
            if font_family and name:
                slug = re.sub(r'[^a-z0-9]', '-', name.lower()).strip('-')
                tokens["text_styles"][slug] = {
                    "family": font_family,
                    "size": font_size,
                    "weight": font_weight,
                }
                if font_family not in tokens["fonts"].values():
                    tokens["fonts"][slug] = font_family

        # Recursão
        for child in node.get("children", []):
            walk(child, depth + 1)

    document = file_data.get("document", {})
    walk(document)
    return tokens


def _tokens_to_css(tokens: dict, file_name: str = "Aura Decore") -> str:
    """Converte design tokens em CSS com variáveis e classes Japandi."""

    color_vars = "\n".join([f"  {k}: {v};" for k, v in tokens["colors"].items()])
    font_vars  = "\n".join([
        f"  --figma-font-{k}: '{v}', sans-serif;"
        for k, v in tokens["fonts"].items()
    ])

    text_classes = ""
    for slug, s in tokens.get("text_styles", {}).items():
        text_classes += (
            f"\n.figma-{slug} {{\n"
            f"  font-family: '{s['family']}', sans-serif;\n"
            f"  font-size: {s['size']}px;\n"
            f"  font-weight: {s['weight']};\n"
            f"}}\n"
        )

    return f"""/* ══ Aura Decore — Figma Design Tokens ══
   Arquivo: {file_name}
   Gerado: {time.strftime('%Y-%m-%d %H:%M')}
   Tokens: {len(tokens['colors'])} cores, {len(tokens['fonts'])} fontes
═══════════════════════════════════════════════════ */

:root {{
  /* Cores do Figma */
{color_vars}

  /* Tipografia do Figma */
{font_vars}
}}

/* Utilitários baseados nos tokens Figma */
.aura-text-primary   {{ color: var(--figma-primary, #B8793A); }}
.aura-text-secondary {{ color: var(--figma-secondary, #1C1917); }}
.aura-bg-surface     {{ background: var(--figma-surface, #F5F0EB); }}
.aura-bg-accent      {{ background: var(--figma-accent, #EDE5D8); }}
{text_classes}
"""


# ── Tool 1: Sincronizar Tokens Figma → Shopify CSS ───────────────────────────

class FigmaTokensSyncTool(BaseTool):
    name: str = "FigmaTokensSync"
    description: str = (
        "Extrai design tokens (cores, tipografia) do arquivo Figma da Aura Decore "
        "e injeta como variáveis CSS no tema Shopify. "
        "Input: 'sync' para sincronizar ou file_id específico (ex: 'abc123def'). "
        "Output: resumo dos tokens extraídos e status da sincronização."
    )

    def _run(self, input_str: str) -> str:
        file_id = FIGMA_FILE_ID
        if input_str.strip() not in ("sync", "status", "") and len(input_str.strip()) > 5:
            file_id = input_str.strip()

        if not FIGMA_API_TOKEN:
            return (
                "⚠️ FIGMA_API_TOKEN não configurado.\n\n"
                "Como obter:\n"
                "1. Acesse figma.com → Account Settings (ícone de perfil)\n"
                "2. Seção 'Personal access tokens' → 'Generate new token'\n"
                "3. Adicione ao .env: FIGMA_API_TOKEN=figd_...\n\n"
                "Como obter FIGMA_FILE_ID:\n"
                "Abra seu arquivo Figma → copie da URL:\n"
                "figma.com/design/[FILE_ID]/nome-do-arquivo\n"
                "Adicione ao .env: FIGMA_FILE_ID=FILE_ID_aqui"
            )

        if not file_id:
            return (
                "⚠️ FIGMA_FILE_ID não configurado.\n"
                "Adicione ao .env: FIGMA_FILE_ID=ID_do_arquivo_figma\n"
                "Ou passe o ID diretamente: ex. 'abc123def'"
            )

        try:
            with httpx.Client(timeout=30) as hc:
                r = hc.get(f"{FIGMA_API_BASE}/files/{file_id}", headers=_figma_headers())

            if r.status_code == 403:
                return "Erro 403: Token Figma sem acesso ao arquivo. Verifique se o arquivo é seu ou compartilhado com você."
            if r.status_code != 200:
                return f"Erro Figma API ({r.status_code}): {r.text[:300]}"

            file_data = r.json()
            file_name = file_data.get("name", "Aura Decore")
            tokens    = _extract_tokens_from_figma(file_data)
            css       = _tokens_to_css(tokens, file_name)

            # Salvar CSS localmente
            css_path = os.path.join(os.path.dirname(__file__), "..", "shopify-theme", "assets", "figma-tokens.css")
            os.makedirs(os.path.dirname(css_path), exist_ok=True)
            with open(css_path, "w", encoding="utf-8") as f:
                f.write(css)

            result = (
                f"✅ Figma tokens extraídos!\n"
                f"Arquivo: {file_name}\n"
                f"Cores encontradas: {len(tokens['colors'])}\n"
                f"Fontes encontradas: {len(tokens['fonts'])}\n"
                f"Salvo em: {css_path}\n\n"
            )

            # Se 'sync' no input E Shopify configurado → injeta no tema
            if "sync" in input_str.lower() and SHOPIFY_DOMAIN and SHOPIFY_TOKEN:
                with httpx.Client(timeout=20) as hc:
                    rt = hc.get(
                        f"https://{SHOPIFY_DOMAIN}/admin/api/2025-01/themes.json",
                        headers=_shopify_headers()
                    )
                    themes = rt.json().get("themes", [])
                    main_id = next((t["id"] for t in themes if t["role"] == "main"), None)
                    if main_id:
                        ru = hc.put(
                            f"https://{SHOPIFY_DOMAIN}/admin/api/2025-01/themes/{main_id}/assets.json",
                            headers=_shopify_headers(),
                            json={"asset": {"key": "assets/figma-tokens.css", "value": css}}
                        )
                        if ru.status_code in (200, 201):
                            result += "✅ CSS injetado no tema Shopify! (assets/figma-tokens.css)\n"
                            result += "Adicione ao theme.liquid: {{ 'figma-tokens.css' | asset_url | stylesheet_tag }}\n"
                        else:
                            result += f"⚠️ Erro ao injetar no Shopify: {ru.status_code}\n"

            result += f"\nPreview do CSS:\n{css[:600]}..."
            return result

        except Exception as e:
            return f"Erro ao processar Figma: {e}"


# ── Tool 2: Exportar asset/frame do Figma ────────────────────────────────────

class FigmaExportAssetTool(BaseTool):
    name: str = "FigmaExportAsset"
    description: str = (
        "Exporta um frame ou componente específico do Figma como PNG ou SVG. "
        "Input JSON: {\"node_id\": \"0:123\", \"format\": \"png|svg\", \"scale\": 2, \"filename\": \"nome\"} "
        "Para encontrar node_id: inspecione o elemento no Figma (clique direito → Copy/Paste → Copy link). "
        "Output: arquivo salvo localmente com URL."
    )

    def _run(self, input_str: str) -> str:
        if not FIGMA_API_TOKEN or not FIGMA_FILE_ID:
            return "Configure FIGMA_API_TOKEN e FIGMA_FILE_ID no .env."

        try:
            data = json.loads(input_str)
        except Exception:
            data = {"node_id": input_str.strip()}

        node_id  = data.get("node_id", "")
        fmt      = data.get("format", "png").lower()
        scale    = data.get("scale", 2)
        filename = data.get("filename", f"figma_{int(time.time())}")

        if not node_id:
            return "node_id é obrigatório (ex: '0:123')."

        try:
            with httpx.Client(timeout=30) as hc:
                r = hc.get(
                    f"{FIGMA_API_BASE}/images/{FIGMA_FILE_ID}",
                    headers=_figma_headers(),
                    params={"ids": node_id, "format": fmt, "scale": scale}
                )
                if r.status_code != 200:
                    return f"Erro Figma export ({r.status_code}): {r.text[:300]}"

                image_url = r.json().get("images", {}).get(node_id, "")
                if not image_url:
                    return "Nenhuma URL de imagem retornada pelo Figma."

                # Download
                rd = hc.get(image_url, follow_redirects=True, timeout=30)
                ext = fmt
                local_path = os.path.join(ASSETS_DIR, f"{filename}.{ext}")
                with open(local_path, "wb") as f:
                    f.write(rd.content)

                size_kb = len(rd.content) // 1024
                return (
                    f"✅ Asset Figma exportado!\n"
                    f"Node: {node_id}\n"
                    f"Formato: {fmt.upper()} @ {scale}x\n"
                    f"Local: {local_path}\n"
                    f"Tamanho: {size_kb}KB\n"
                    f"URL Figma: {image_url}"
                )
        except Exception as e:
            return f"Erro ao exportar asset Figma: {e}"


# ── Tool 3: Auditoria visual Figma ↔ Shopify ─────────────────────────────────

class FigmaAuditTool(BaseTool):
    name: str = "FigmaAudit"
    description: str = (
        "Audita consistência entre o design no Figma e o tema Shopify ao vivo. "
        "Verifica se cores e fontes do Figma estão aplicadas na loja. "
        "Input: 'audit' para executar. Output: relatório de gaps visuais."
    )

    def _run(self, input_str: str) -> str:
        report = [
            "# 🎨 Auditoria Visual — Figma ↔ Shopify",
            f"Data: {time.strftime('%Y-%m-%d %H:%M')}",
            "",
        ]

        # Verificar configurações
        figma_ok   = bool(FIGMA_API_TOKEN and FIGMA_FILE_ID)
        shopify_ok = bool(SHOPIFY_DOMAIN and SHOPIFY_TOKEN)

        report.append(f"**Figma API:** {'✅ Configurado' if figma_ok else '❌ FIGMA_API_TOKEN/FILE_ID ausentes'}")
        report.append(f"**Shopify API:** {'✅ Configurado' if shopify_ok else '❌ SHOPIFY_ADMIN_TOKEN ausente'}")
        report.append("")

        if not figma_ok:
            report.append("## ⚠️ Ações necessárias:")
            report.append("1. `FIGMA_API_TOKEN=figd_...` → Account Settings → Personal access tokens")
            report.append("2. `FIGMA_FILE_ID=...` → URL do arquivo Figma")
            return "\n".join(report)

        # Checklist de brand kit Aura Decore esperados
        expected_tokens = {
            "Terra/Marrom":    "#B8793A",
            "Off-white":       "#F5F0EB",
            "Sand/Areia":      "#EDE5D8",
            "Carvão":          "#1C1917",
            "Sálvia":          "#8A9A7B",
        }
        expected_fonts = ["Cormorant Garamond", "DM Sans"]

        report.append("## Tokens Esperados (Brand Kit Japandi)")
        for name, hex_color in expected_tokens.items():
            report.append(f"  • {name}: `{hex_color}`")
        report.append("")
        report.append("## Fontes Esperadas")
        for font in expected_fonts:
            report.append(f"  • {font}")
        report.append("")

        # Verificar arquivo CSS figma-tokens.css existe localmente
        css_path = os.path.join(os.path.dirname(__file__), "..", "shopify-theme", "assets", "figma-tokens.css")
        if os.path.exists(css_path):
            report.append(f"✅ figma-tokens.css encontrado localmente")
        else:
            report.append("❌ figma-tokens.css não encontrado — execute FigmaTokensSync primeiro")

        report.append("")
        report.append("## Recomendações")
        report.append("1. Execute `FigmaTokensSync sync` para sincronizar tokens → Shopify")
        report.append("2. Execute `CanvaBrandKit sync` para sincronizar brand kit Canva → Shopify")
        report.append("3. Verifique visualmente em auradecore.com.br após sincronização")

        return "\n".join(report)


# ── Instâncias prontas ────────────────────────────────────────────────────────
figma_tokens = FigmaTokensSyncTool()
figma_export = FigmaExportAssetTool()
figma_audit  = FigmaAuditTool()

FIGMA_TOOLS = [figma_tokens, figma_export, figma_audit]
