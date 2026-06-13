# -*- coding: utf-8 -*-
"""
canva_tools.py — Integração Canva Pro pessoal com Aura Decore
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Funcionalidades:
1. CanvaExportTool    — exporta designs do Canva via API Connect
2. CanvaUploadShopify — exporta do Canva e faz upload direto ao Shopify
3. CanvaListDesigns   — lista seus designs recentes por palavra-chave
4. CanvaBrandKit      — sincroniza brand kit Canva → variáveis CSS Shopify

Uso pelos agentes:
  LUNA: usa CanvaListDesigns + CanvaExportTool para buscar e exportar assets
  ARTE: usa CanvaExportTool para adicionar ao pipeline de imagens
  THEO/DEV: usa CanvaUploadShopify para publicar imagens direto na loja

Configuração necessária (.env):
  CANVA_API_TOKEN=eyJ... (gerado em canva.com/developers)
"""
from __future__ import annotations
import os
import re
import json
import time
import httpx
from crewai.tools import BaseTool

CANVA_API_TOKEN = os.getenv("CANVA_API_TOKEN", "")
CANVA_API_BASE  = "https://api.canva.com/rest/v1"

SHOPIFY_DOMAIN = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")
SHOPIFY_TOKEN  = os.getenv("SHOPIFY_ADMIN_TOKEN", "") or os.getenv("SHOPIFY_ADMIN_API_TOKEN", "")

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "generated_images", "canva")
os.makedirs(IMAGES_DIR, exist_ok=True)


def _canva_headers() -> dict:
    return {
        "Authorization": f"Bearer {CANVA_API_TOKEN}",
        "Content-Type": "application/json",
    }


def _shopify_headers() -> dict:
    return {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json",
    }


# ── Tool 1: Listar designs do Canva ──────────────────────────────────────────

class CanvaListDesignsTool(BaseTool):
    name: str = "CanvaListDesigns"
    description: str = (
        "Lista designs recentes do Canva Pro pessoal. "
        "Input: palavra-chave de busca (ex: 'banner aura', 'produto vaso', 'hero'). "
        "Output: lista de designs com ID, nome, URL de preview e data."
    )

    def _run(self, query: str) -> str:
        if not CANVA_API_TOKEN:
            return (
                "⚠️ CANVA_API_TOKEN não configurado.\n"
                "Acesse: canva.com/developers → 'Canva Connect' → gere seu token\n"
                "Adicione ao .env: CANVA_API_TOKEN=seu_token_aqui"
            )
        try:
            with httpx.Client(timeout=15) as hc:
                r = hc.get(
                    f"{CANVA_API_BASE}/designs",
                    headers=_canva_headers(),
                    params={"query": query, "limit": 20}
                )
            data = r.json()
            if r.status_code != 200:
                return f"Erro Canva API ({r.status_code}): {data}"

            designs = data.get("items", [])
            if not designs:
                return f"Nenhum design encontrado para '{query}'."

            lines = [f"🎨 Designs Canva para '{query}':"]
            for d in designs:
                name      = d.get("title", "Sem título")
                design_id = d.get("id", "")
                created   = d.get("created_at", "")[:10]
                lines.append(f"  • [{design_id}] {name} — {created}")
            return "\n".join(lines)
        except Exception as e:
            return f"Erro ao listar designs: {e}"


# ── Tool 2: Exportar design do Canva ─────────────────────────────────────────

class CanvaExportTool(BaseTool):
    name: str = "CanvaExport"
    description: str = (
        "Exporta um design do Canva Pro em alta resolução (JPG/PNG). "
        "Input JSON: {\"design_id\": \"ID_DO_DESIGN\", \"format\": \"jpg|png\", \"filename\": \"nome_arquivo\"} "
        "Output: caminho local do arquivo exportado e URL para uso no Shopify."
    )

    def _run(self, input_str: str) -> str:
        if not CANVA_API_TOKEN:
            return "⚠️ Configure CANVA_API_TOKEN no .env para exportar designs."
        try:
            data = json.loads(input_str)
        except Exception:
            data = {"design_id": input_str.strip()}

        design_id = data.get("design_id", "")
        fmt       = data.get("format", "jpg").lower()
        filename  = data.get("filename", f"canva_{int(time.time())}")

        if not design_id:
            return "design_id é obrigatório."

        try:
            with httpx.Client(timeout=60) as hc:
                # Criar job de exportação
                r = hc.post(
                    f"{CANVA_API_BASE}/exports",
                    headers=_canva_headers(),
                    json={
                        "design_id": design_id,
                        "format": {"type": fmt.upper()},
                    }
                )
                export_data = r.json()
                if r.status_code not in (200, 201):
                    return f"Erro ao criar export ({r.status_code}): {export_data}"

                job_id = export_data.get("job", {}).get("id", "")
                if not job_id:
                    return f"Sem job_id na resposta: {export_data}"

                # Aguardar conclusão do export (max 30s)
                for _ in range(15):
                    time.sleep(2)
                    rj = hc.get(f"{CANVA_API_BASE}/exports/{job_id}", headers=_canva_headers())
                    job = rj.json().get("job", {})
                    status = job.get("status", "")
                    if status == "success":
                        urls = job.get("urls", [])
                        if not urls:
                            return "Export concluído mas sem URLs disponíveis."
                        download_url = urls[0]

                        # Baixar e salvar localmente
                        rd = hc.get(download_url, follow_redirects=True, timeout=30)
                        ext = "png" if fmt == "png" else "jpg"
                        local_path = os.path.join(IMAGES_DIR, f"{filename}.{ext}")
                        with open(local_path, "wb") as f:
                            f.write(rd.content)

                        size_kb = len(rd.content) // 1024
                        return (
                            f"✅ Export Canva concluído!\n"
                            f"Design ID: {design_id}\n"
                            f"Local: {local_path}\n"
                            f"Tamanho: {size_kb}KB\n"
                            f"URL de download: {download_url}"
                        )
                    elif status == "failed":
                        return f"Export falhou: {job}"

                return "Timeout: export demorou mais de 30s."
        except Exception as e:
            return f"Erro ao exportar: {e}"


# ── Tool 3: Export direto Canva → Upload Shopify ─────────────────────────────

class CanvaUploadShopifyTool(BaseTool):
    name: str = "CanvaUploadShopify"
    description: str = (
        "Exporta design do Canva e faz upload direto ao Shopify (produto ou arquivo). "
        "Input JSON: {\"design_id\": \"ID\", \"product_id\": \"ID_PRODUTO_OPCIONAL\", "
        "\"filename\": \"nome\", \"alt_text\": \"texto alternativo SEO\"} "
        "Se product_id fornecido: adiciona como imagem do produto. "
        "Sem product_id: faz upload para biblioteca de arquivos do Shopify. "
        "Output: URL final da imagem no Shopify."
    )

    def _run(self, input_str: str) -> str:
        if not CANVA_API_TOKEN:
            return "⚠️ Configure CANVA_API_TOKEN no .env."
        try:
            data = json.loads(input_str)
        except Exception:
            return "Input deve ser JSON: {\"design_id\": \"...\", \"product_id\": \"...\"}"

        design_id  = data.get("design_id", "")
        product_id = data.get("product_id", "")
        filename   = data.get("filename", f"aura_canva_{int(time.time())}")
        alt_text   = data.get("alt_text", "Aura Decore — Decoração Japandi")

        # 1. Exportar do Canva
        export_tool = CanvaExportTool()
        export_result = export_tool._run(json.dumps({
            "design_id": design_id,
            "format": "jpg",
            "filename": filename
        }))

        if "Erro" in export_result or "⚠️" in export_result:
            return export_result

        # Extrair path local
        local_path = None
        for line in export_result.split("\n"):
            if line.startswith("Local:"):
                local_path = line.replace("Local:", "").strip()
                break

        if not local_path or not os.path.exists(local_path):
            return f"Arquivo exportado não encontrado. Resultado: {export_result}"

        # 2. Upload ao Shopify
        if not SHOPIFY_DOMAIN or not SHOPIFY_TOKEN:
            return f"✅ Export OK: {local_path}\n⚠️ Shopify não configurado para upload automático."

        try:
            with open(local_path, "rb") as f:
                img_data = f.read()

            with httpx.Client(timeout=30) as hc:
                base = f"https://{SHOPIFY_DOMAIN}/admin/api/2025-01"
                import base64
                img_b64 = base64.b64encode(img_data).decode()

                if product_id:
                    # Upload como imagem de produto
                    r = hc.post(
                        f"{base}/products/{product_id}/images.json",
                        headers=_shopify_headers(),
                        json={"image": {
                            "attachment": img_b64,
                            "filename": f"{filename}.jpg",
                            "alt": alt_text,
                        }}
                    )
                    result = r.json()
                    img_url = result.get("image", {}).get("src", "")
                    if img_url:
                        return (
                            f"✅ Canva → Shopify Produto!\n"
                            f"Produto ID: {product_id}\n"
                            f"Imagem URL: {img_url}\n"
                            f"Alt text: {alt_text}"
                        )
                    return f"Erro upload produto Shopify: {result}"
                else:
                    # Upload para Files library (GraphQL)
                    gql = """
                    mutation fileCreate($files: [FileCreateInput!]!) {
                      fileCreate(files: $files) {
                        files { ... on MediaImage { image { url } } }
                        userErrors { field message }
                      }
                    }"""
                    r = hc.post(
                        f"https://{SHOPIFY_DOMAIN}/admin/api/2025-01/graphql.json",
                        headers=_shopify_headers(),
                        json={"query": gql, "variables": {
                            "files": [{"alt": alt_text, "contentType": "IMAGE",
                                       "originalSource": f"data:image/jpeg;base64,{img_b64}"}]
                        }}
                    )
                    result = r.json()
                    return f"✅ Upload Shopify Files: {result}"

        except Exception as e:
            return f"Erro ao fazer upload ao Shopify: {e}\nArquivo salvo em: {local_path}"


# ── Tool 4: Brand Kit Canva → CSS Shopify ────────────────────────────────────

class CanvaBrandKitTool(BaseTool):
    name: str = "CanvaBrandKit"
    description: str = (
        "Lê o brand kit do Canva Pro e sincroniza cores/tipografia como variáveis CSS no Shopify. "
        "Input: 'sync' para sincronizar, ou 'status' para ver configuração atual. "
        "Output: CSS com variáveis geradas a partir do brand kit Canva."
    )

    def _run(self, input_str: str) -> str:
        # Brand kit Aura Decore (hardcoded + dinâmico via Canva API quando disponível)
        brand_kit = {
            "name": "Aura Decore — Japandi",
            "colors": {
                "--aura-terra":     "#B8793A",
                "--aura-offwhite":  "#F5F0EB",
                "--aura-sand":      "#EDE5D8",
                "--aura-charcoal":  "#1C1917",
                "--aura-sage":      "#8A9A7B",
                "--aura-cream":     "#FAF7F2",
                "--aura-mist":      "#D4C9B8",
                "--aura-warm-dark": "#2C2420",
            },
            "fonts": {
                "heading": "Cormorant Garamond",
                "body": "DM Sans",
                "accent": "Jost",
            }
        }

        # Tentar buscar brand kit via API Canva
        if CANVA_API_TOKEN and "status" not in input_str.lower():
            try:
                with httpx.Client(timeout=10) as hc:
                    r = hc.get(f"{CANVA_API_BASE}/brand-kits", headers=_canva_headers())
                    if r.status_code == 200:
                        kits = r.json().get("items", [])
                        if kits:
                            kit = kits[0]
                            # Extrair cores do brand kit real
                            for color in kit.get("colors", []):
                                hex_color = color.get("color", {}).get("hex", "")
                                name_slug = color.get("name", "").lower().replace(" ", "-")
                                if hex_color and name_slug:
                                    brand_kit["colors"][f"--canva-{name_slug}"] = f"#{hex_color}"
            except Exception:
                pass  # Usa brand kit hardcoded

        # Gerar CSS com as variáveis
        css_vars = "\n".join([f"  {k}: {v};" for k, v in brand_kit["colors"].items()])
        css = f"""/* ══ Aura Decore — Brand Kit CSS ══
   Gerado por CanvaBrandKit em {time.strftime('%Y-%m-%d %H:%M')}
   Sincronizado com Canva Pro: {brand_kit['name']}
═══════════════════════════════════════ */

:root {{
{css_vars}

  /* Tipografia */
  --font-heading: '{brand_kit['fonts']['heading']}', Georgia, serif;
  --font-body:    '{brand_kit['fonts']['body']}', system-ui, sans-serif;
  --font-accent:  '{brand_kit['fonts']['accent']}', sans-serif;

  /* Aplicações semânticas */
  --color-primary:    var(--aura-terra);
  --color-background: var(--aura-offwhite);
  --color-surface:    var(--aura-cream);
  --color-text:       var(--aura-charcoal);
  --color-text-muted: var(--aura-mist);
  --color-accent:     var(--aura-sage);
  --color-border:     var(--aura-sand);
}}

/* Componentes base Japandi */
.aura-btn-primary {{
  background: var(--aura-terra);
  color: var(--aura-offwhite);
  font-family: var(--font-body);
  border: none;
  padding: 12px 28px;
  border-radius: 2px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.25s ease, transform 0.15s ease;
}}
.aura-btn-primary:hover {{
  background: var(--aura-warm-dark);
  transform: translateY(-1px);
}}

.aura-section-title {{
  font-family: var(--font-heading);
  font-size: clamp(1.8rem, 4vw, 3rem);
  font-weight: 300;
  color: var(--aura-charcoal);
  letter-spacing: 0.04em;
  line-height: 1.2;
}}

.aura-badge {{
  background: var(--aura-sand);
  color: var(--aura-terra);
  font-family: var(--font-body);
  font-size: 0.7rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  padding: 4px 10px;
  border-radius: 1px;
}}
"""

        # Se Shopify configurado, injeta o CSS no tema
        if SHOPIFY_DOMAIN and SHOPIFY_TOKEN and "sync" in input_str.lower():
            try:
                with httpx.Client(timeout=20) as hc:
                    # Buscar tema principal
                    rt = hc.get(
                        f"https://{SHOPIFY_DOMAIN}/admin/api/2025-01/themes.json",
                        headers=_shopify_headers()
                    )
                    themes = rt.json().get("themes", [])
                    main_id = next((t["id"] for t in themes if t["role"] == "main"), None)
                    if main_id:
                        # Salvar como asset CSS
                        ru = hc.put(
                            f"https://{SHOPIFY_DOMAIN}/admin/api/2025-01/themes/{main_id}/assets.json",
                            headers=_shopify_headers(),
                            json={"asset": {
                                "key": "assets/aura-brand-kit.css",
                                "value": css
                            }}
                        )
                        if ru.status_code in (200, 201):
                            return (
                                f"✅ Brand Kit sincronizado com Shopify!\n"
                                f"Arquivo: assets/aura-brand-kit.css\n"
                                f"Cores: {len(brand_kit['colors'])} variáveis CSS\n"
                                f"Fontes: {', '.join(brand_kit['fonts'].values())}\n\n"
                                f"Adicione ao theme.liquid:\n"
                                f'{{ "aura-brand-kit.css" | asset_url | stylesheet_tag }}\n\n'
                                f"CSS gerado:\n{css[:500]}..."
                            )
            except Exception as e:
                return f"CSS gerado mas erro ao sincronizar Shopify: {e}\n\n{css}"

        return f"Brand Kit gerado (use 'sync' para aplicar no Shopify):\n{css}"


# ── Instâncias prontas ────────────────────────────────────────────────────────
canva_list     = CanvaListDesignsTool()
canva_export   = CanvaExportTool()
canva_upload   = CanvaUploadShopifyTool()
canva_brandkit = CanvaBrandKitTool()

CANVA_TOOLS = [canva_list, canva_export, canva_upload, canva_brandkit]
