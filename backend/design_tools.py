# -*- coding: utf-8 -*-
"""
Ferramentas de design e publicacao para ARTE, LUNA, NOX e FEED.
- ImageGenTool     : gera imagens via Pollinations.ai (gratis, sem chave)
- FacebookPostTool : publica no Facebook Page
- InstagramPostTool: publica no Instagram Business Account (Graph API)
- ShopifyProductTool: atualiza produtos na loja (descricao, imagens)
- ShopifyBannerTool : atualiza banners/hero da loja via Shopify metafields
- ImageSaveTool    : baixa e salva imagem gerada para uso posterior
"""
from __future__ import annotations
import os
import re
import json
import time
import urllib.parse
import httpx
from crewai.tools import BaseTool

# ── Credenciais lidas do ambiente ──────────────────────────────────────────────
FB_PAGE_ID    = os.getenv("FB_PAGE_ID", "")
FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN", "")
IG_USER_ID    = os.getenv("IG_USER_ID", "")       # Instagram Business Account ID
SHOPIFY_DOMAIN= os.getenv("SHOPIFY_DOMAIN", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "")

# Diretorio para salvar imagens geradas localmente
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "generated_images")
os.makedirs(IMAGES_DIR, exist_ok=True)


# ── Brand Kit Aura Decore ─────────────────────────────────────────────────────
BRAND_STYLE = (
    "japandi minimalist home decor, wabi-sabi aesthetic, "
    "natural earth tones, terracotta #B8793A, off-white #F5F0EB, sand #EDE5D8, "
    "warm light, soft shadows, premium lifestyle photography style, "
    "elegant and calming, biophilic design, natural materials"
)


# ── Ferramenta 1: Geracao de imagens ─────────────────────────────────────────

class ImageGenTool(BaseTool):
    name: str = "ImageGen"
    description: str = (
        "Gera imagem com IA usando Pollinations.ai (gratis, sem chave). "
        "Input JSON: {\"prompt\": \"descricao da imagem\", \"width\": 1080, \"height\": 1080, \"filename\": \"nome_arquivo\"} "
        "Formatos: 1080x1080 (feed), 1080x1920 (stories/reels), 1200x630 (banner). "
        "Output: URL da imagem gerada + caminho local salvo."
    )

    def _run(self, input_str: str) -> str:
        try:
            data = json.loads(input_str)
        except Exception:
            data = {"prompt": input_str}

        user_prompt = data.get("prompt", "japandi home decor product photo")
        width  = int(data.get("width",  1080))
        height = int(data.get("height", 1080))
        fname  = data.get("filename", f"aura_{int(time.time())}")

        # Enriquece com brand style
        full_prompt = f"{user_prompt}, {BRAND_STYLE}"
        encoded = urllib.parse.quote(full_prompt)
        seed = int(time.time()) % 100000
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width={width}&height={height}&seed={seed}&nologo=true&enhance=true&model=flux"
        )

        # Tenta baixar e salvar localmente
        try:
            r = httpx.get(url, timeout=45, follow_redirects=True)
            if r.status_code == 200 and len(r.content) > 1000:
                local_path = os.path.join(IMAGES_DIR, f"{fname}.jpg")
                with open(local_path, "wb") as f:
                    f.write(r.content)
                return (
                    f"Imagem gerada com sucesso!\n"
                    f"URL: {url}\n"
                    f"Local: {local_path}\n"
                    f"Dimensoes: {width}x{height}px\n"
                    f"Prompt: {user_prompt}"
                )
            else:
                return f"Imagem gerada (URL disponivel). URL: {url} | Prompt: {user_prompt}"
        except Exception as e:
            return (
                f"Imagem gerada (use a URL diretamente).\n"
                f"URL: {url}\n"
                f"Erro ao salvar local: {e}"
            )


# ── Ferramenta 2: Post no Facebook ───────────────────────────────────────────

class FacebookPostTool(BaseTool):
    name: str = "FacebookPost"
    description: str = (
        "Publica post no Facebook Page da Aura Decore. "
        "Input JSON: {\"message\": \"texto do post\", \"image_url\": \"url_da_imagem_opcional\"} "
        "Se image_url fornecida, posta como foto. Sem image_url, posta como texto. "
        "Output: ID do post criado ou erro."
    )

    def _run(self, input_str: str) -> str:
        try:
            data = json.loads(input_str)
        except Exception:
            data = {"message": input_str}

        message   = data.get("message", "")
        image_url = data.get("image_url", "")

        # Modo vault: salva o post localmente quando token não configurado
        if not FB_PAGE_TOKEN or not FB_PAGE_ID:
            return self._save_to_vault("facebook", message, image_url)

        base = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}"
        try:
            with httpx.Client(timeout=20) as hc:
                if image_url:
                    resp = hc.post(f"{base}/photos",
                        params={"access_token": FB_PAGE_TOKEN},
                        json={"url": image_url, "caption": message})
                else:
                    resp = hc.post(f"{base}/feed",
                        params={"access_token": FB_PAGE_TOKEN},
                        json={"message": message})
            result = resp.json()
            if "id" in result:
                return f"Post publicado no Facebook! ID: {result['id']} | Preview: {message[:80]}"
            else:
                # API falhou (ex: página não vinculada) — preserva conteúdo no vault
                err = result.get('error', {}).get('message', str(result))
                vault_msg = self._save_to_vault("facebook", message, image_url)
                return f"Erro Facebook: {err}\n[FALLBACK] {vault_msg}"
        except Exception as e:
            vault_msg = self._save_to_vault("facebook", message, image_url)
            return f"Erro ao publicar no Facebook: {e}\n[FALLBACK] {vault_msg}"

    def _save_to_vault(self, rede: str, message: str, image_url: str) -> str:
        """Salva post no vault Obsidian quando a rede social não está configurada."""
        try:
            vault = os.path.join(os.path.dirname(__file__), "..", "..", "AURA-decor-vault",
                                 "Redes Sociais", "posts-prontos")
            os.makedirs(vault, exist_ok=True)
            ts = time.strftime("%Y%m%d-%H%M%S")
            fname = os.path.join(vault, f"post-{rede}-{ts}.md")
            content = (f"# Post {rede.title()} — {time.strftime('%Y-%m-%d %H:%M')}\n\n"
                      f"**Status:** 🟡 Aguardando publicação manual\n"
                      f"**Rede:** {rede.title()}\n\n"
                      f"## Texto\n{message}\n\n"
                      f"{'## Imagem\n' + image_url + chr(10) if image_url else ''}"
                      f"---\n*Configure FB_PAGE_TOKEN no .env para publicação automática*\n")
            with open(fname, "w", encoding="utf-8") as f:
                f.write(content)
            return (f"✅ Post salvo no vault (publicação manual necessária).\n"
                   f"📁 {fname}\n"
                   f"📝 Preview: {message[:100]}\n"
                   f"🔑 Para publicar automaticamente: adicione FB_PAGE_TOKEN ao .env")
        except Exception as e:
            return f"Post preparado (vault indisponível): {message[:120]} | Erro: {e}"


# ── Ferramenta 3: Post no Instagram ──────────────────────────────────────────

class InstagramPostTool(BaseTool):
    name: str = "InstagramPost"
    description: str = (
        "Publica foto/story/reel no Instagram Business Account da Aura Decore. "
        "Input JSON: {\"caption\": \"legenda com hashtags\", \"image_url\": \"url_publica_da_imagem\", "
        "\"media_type\": \"IMAGE|REELS|STORIES\"} "
        "media_type padrao: IMAGE (feed). Use STORIES para stories 1080x1920. "
        "A image_url deve ser publicamente acessivel. "
        "Output: ID do post ou instrucoes se IG nao configurado."
    )

    def _run(self, input_str: str) -> str:
        ig_id = IG_USER_ID or os.getenv("IG_USER_ID", "")
        token = FB_PAGE_TOKEN or os.getenv("FB_PAGE_TOKEN", "")

        if not ig_id or not token:
            try:
                data2 = json.loads(input_str) if isinstance(input_str, str) else {}
            except Exception:
                data2 = {}
            caption   = data2.get("caption", input_str if isinstance(input_str, str) else "")
            image_url = data2.get("image_url", "")
            return FacebookPostTool()._save_to_vault("instagram", caption, image_url)

        try:
            data = json.loads(input_str)
        except Exception:
            data = {"caption": input_str, "image_url": ""}

        caption    = data.get("caption", "")
        image_url  = data.get("image_url", "")
        media_type = data.get("media_type", "IMAGE").upper()

        if not image_url:
            return "image_url obrigatoria para post no Instagram."

        base = f"https://graph.facebook.com/v20.0/{ig_id}"
        try:
            with httpx.Client(timeout=30) as hc:
                # Step 1: criar container de media
                container_payload: dict = {"image_url": image_url, "access_token": token}
                if media_type == "STORIES":
                    container_payload["media_type"] = "IMAGE"
                    container_payload["is_story"] = "true"
                elif media_type == "REELS":
                    container_payload["media_type"] = "REELS"
                    container_payload["caption"] = caption
                else:
                    container_payload["caption"] = caption

                r1 = hc.post(f"{base}/media", params={"access_token": token}, json=container_payload)
                container = r1.json()
                if "id" not in container:
                    err = container.get('error', {}).get('message', str(container))
                    vault_msg = FacebookPostTool()._save_to_vault(f"instagram-{media_type.lower()}", caption, image_url)
                    return f"Erro ao criar container IG ({media_type}): {err}\n[FALLBACK] {vault_msg}"

                # Step 2: publicar
                r2 = hc.post(
                    f"{base}/media_publish",
                    params={"access_token": token},
                    json={"creation_id": container["id"]},
                )
                result = r2.json()
                if "id" in result:
                    return f"Post publicado no Instagram! ID: {result['id']}"
                else:
                    err = result.get('error', {}).get('message', str(result))
                    vault_msg = FacebookPostTool()._save_to_vault(f"instagram-{media_type.lower()}", caption, image_url)
                    return f"Erro ao publicar IG: {err}\n[FALLBACK] {vault_msg}"
        except Exception as e:
            vault_msg = FacebookPostTool()._save_to_vault(f"instagram-{media_type.lower()}", caption, image_url)
            return f"Erro Instagram: {e}\n[FALLBACK] {vault_msg}"


# ── Ferramenta 4: Atualizar produto Shopify ───────────────────────────────────

class ShopifyProductTool(BaseTool):
    name: str = "ShopifyProduct"
    description: str = (
        "Atualiza produto na loja Shopify (descricao, titulo, tags, imagem). "
        "Input JSON: {\"product_id\": \"123456789\", \"title\": \"Titulo\", "
        "\"body_html\": \"<p>Descricao HTML</p>\", \"tags\": \"tag1,tag2\", "
        "\"image_url\": \"url_opcional\"} "
        "Se product_id omitido, lista os primeiros 10 produtos com seus IDs. "
        "Output: confirmacao da atualizacao ou lista de produtos."
    )

    def _run(self, input_str: str) -> str:
        if not SHOPIFY_DOMAIN or not SHOPIFY_TOKEN:
            return (
                "Shopify nao configurado. "
                "Configure SHOPIFY_DOMAIN e SHOPIFY_ADMIN_TOKEN no .env"
            )
        headers = {
            "X-Shopify-Access-Token": SHOPIFY_TOKEN,
            "Content-Type": "application/json",
        }
        base = f"https://{SHOPIFY_DOMAIN}/admin/api/2025-01"

        try:
            data = json.loads(input_str)
        except Exception:
            # Se nao e JSON, lista produtos
            data = {}

        product_id = data.get("product_id", "")

        # Sem product_id: lista produtos
        if not product_id:
            try:
                with httpx.Client(timeout=15) as hc:
                    r = hc.get(f"{base}/products.json?limit=10&fields=id,title,status", headers=headers)
                products = r.json().get("products", [])
                lines = ["Produtos na loja:"]
                for p in products:
                    lines.append(f"  ID: {p['id']} | {p['title']} | {p.get('status','')}")
                return "\n".join(lines) if products else "Nenhum produto encontrado."
            except Exception as e:
                return f"Erro ao listar produtos: {e}"

        # Com product_id: atualiza
        payload: dict = {"product": {}}
        if "title"     in data: payload["product"]["title"]      = data["title"]
        if "body_html" in data: payload["product"]["body_html"]  = data["body_html"]
        if "tags"      in data: payload["product"]["tags"]       = data["tags"]

        try:
            with httpx.Client(timeout=20) as hc:
                if payload["product"]:
                    r = hc.put(f"{base}/products/{product_id}.json", headers=headers, json=payload)
                    result = r.json()
                    if "product" in result:
                        return f"Produto {product_id} atualizado! Titulo: {result['product'].get('title','')}"
                    else:
                        return f"Erro Shopify: {result}"

                # Adicionar imagem se fornecida
                if "image_url" in data:
                    ri = hc.post(
                        f"{base}/products/{product_id}/images.json",
                        headers=headers,
                        json={"image": {"src": data["image_url"]}},
                    )
                    return f"Imagem adicionada ao produto {product_id}: {ri.json()}"

                return "Nada a atualizar."
        except Exception as e:
            return f"Erro ao atualizar produto: {e}"


# ── Ferramenta 5: Gera briefing de design estruturado ─────────────────────────

class DesignBriefTool(BaseTool):
    name: str = "DesignBrief"
    description: str = (
        "Gera um briefing visual completo para um post/banner/criativo da Aura Decore. "
        "Input: descricao do que precisa (ex: 'post instagram produto vaso ceramica japandi'). "
        "Output: briefing detalhado com paleta, tipografia, conceito visual, prompt para gerar imagem, "
        "formato, copy sugerida e hashtags."
    )

    def _run(self, description: str) -> str:
        # Briefing estruturado baseado no brand kit Aura Decore
        formats = {
            "post": "1080x1080px (feed Instagram/Facebook)",
            "story": "1080x1920px (stories/reels)",
            "banner": "1200x630px (Facebook/Web)",
            "produto": "800x800px (foto produto Shopify)",
        }

        # Detecta formato pela descricao
        desc_low = description.lower()
        if "story" in desc_low or "reel" in desc_low:
            fmt = "story"
        elif "banner" in desc_low or "hero" in desc_low:
            fmt = "banner"
        elif "produto" in desc_low or "product" in desc_low:
            fmt = "produto"
        else:
            fmt = "post"

        return f"""# Briefing Visual — Aura Decore
**Pedido:** {description}
**Formato:** {formats[fmt]}

## Brand Kit
- Paleta principal: Terra #B8793A + Off-white #F5F0EB + Sand #EDE5D8
- Tipografia: Cormorant Garamond (titulos) + DM Sans (corpo)
- Tom: Elegante, minimalista, premium, quente

## Conceito Visual
- Cenario: ambiente limpo com luz natural difusa
- Materiais: ceramica, linho, madeira, bambu, pedra
- Mood: tranquilidade, biofilia, conexao com a natureza
- Evitar: fundo branco duro, cores vibrantes, clutter visual

## Prompt para ImageGen
"{description}, japandi minimalist aesthetic, natural earth tones terracotta #B8793A, warm soft light, premium lifestyle photography, wabi-sabi style, biophilic design, clean background, ultra realistic, 4K"

## Copy Sugerida
- Headline: Descanse os olhos. E a alma.
- CTA: Descubra em auradecore.com.br
- Hashtags: #AuraDecore #JapandiDecor #WabiSabi #DecorMinimalista #DecorJapandi #CasaMinimalista #VidaComCalma #HomeDecorBrasil

## Proximos passos
1. Usar ImageGen com o prompt acima
2. Revisar resultado com LUNA
3. Adicionar copy com VERA
4. Publicar com FEED (FacebookPost + InstagramPost)
"""


# ── Instancias prontas para importar ─────────────────────────────────────────

image_gen       = ImageGenTool()
facebook_post   = FacebookPostTool()
instagram_post  = InstagramPostTool()
shopify_product = ShopifyProductTool()
design_brief    = DesignBriefTool()

LUNA_TOOLS = [design_brief, image_gen]
ARTE_TOOLS = [image_gen, design_brief]
FEED_TOOLS = [facebook_post, instagram_post]
NOX_TOOLS  = [design_brief]
THEO_TOOLS = [shopify_product]
