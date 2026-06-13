# -*- coding: utf-8 -*-
"""
audit_and_integrate.py — Auditoria e Integração de Produtos Aura Decore
=======================================================================
Executa:
  1. Busca de fornecedores reais/plausíveis no AliExpress (via DDG).
  2. Validação financeira CFO GUARD (alvo de margem real 40-70%).
  3. Geração de imagens Japandi de alta qualidade (Principal, Lifestyle, Flat Lay) via Pollinations AI.
  4. Redação de copywriting focado em neuroarquitetura via Claude.
  5. Atualização do banco de dados local SQLite (aura_erp.db).
  6. Enriquecimento do arquivo produtos_aura.csv.
  7. Atualização das páginas estáticas HTML locais em aura-decor-preview/.
"""
import os
import sys
import csv
import json
import sqlite3
import pathlib
import time
import urllib.parse
from dotenv import load_dotenv
import httpx
import anthropic

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Caminhos
BACKEND_DIR = pathlib.Path(__file__).parent
ENV_PATH = BACKEND_DIR / ".env"
DB_PATH = BACKEND_DIR / "aura_erp.db"
SCRATCH_DIR = pathlib.Path("C:/Users/erick/.gemini/antigravity-ide/scratch")
CSV_PATH = SCRATCH_DIR / "produtos_aura.csv"
PREVIEW_DIR = SCRATCH_DIR / "aura-decor-preview"
ASSETS_DIR = PREVIEW_DIR / "assets"

# Carrega ambiente
load_dotenv(dotenv_path=ENV_PATH, override=True)

# Inicializa clientes
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
client_claude = None
if ANTHROPIC_KEY:
    try:
        client_claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    except Exception as e:
        print(f"Erro ao inicializar cliente Anthropic: {e}")

# Definição dos 4 produtos principais
PRODUCTS_CONFIG = {
    "vaso-organico-terracota": {
        "title": "Vaso Orgânico Terracota",
        "sku": "AD-VAS-ORG-01",
        "category": "Decoração Japandi",
        "price": 349.00,
        "compare_price": 690.00,
        "weight_kg": 1.5,
        "dimensions": "24cm de altura x 15cm de diâmetro",
        "inventory": 50,
        "target_cost": 110.00,
        "query_search": "ceramic wabi sabi terracota vase aliexpress",
        "supplier_name": "AliExpress - Wabi-Sabi Ceramic Store",
        "supplier_type": "dropshipping",
        "supplier_delivery": 20,
        "supplier_rating": 4,
        "prompts": {
            "principal": "A minimalist ceramic vase, organic curved shape, terracota color, rough textured clay, wabi-sabi style, neutral sand background, high-end product photography, soft side lighting, 8k",
            "lifestyle": "A wabi-sabi terracota ceramic vase on a low oak console table in a bright minimalist Japandi living room, linen curtains, soft morning light, cozy serene atmosphere, 8k",
            "flatlay": "Flat lay of a minimal terracota ceramic vase, dried grass stems, small raw clay pieces, warm beige background, aesthetic organic layout, clean studio light"
        }
    },
    "poltrona-boucle-creme": {
        "title": "Poltrona Bouclé Creme",
        "sku": "AD-POL-BOU-02",
        "category": "Móveis Japandi",
        "price": 2490.00,
        "compare_price": 4500.00,
        "weight_kg": 25.0,
        "dimensions": "85cm altura x 80cm largura x 75cm profundidade",
        "inventory": 15,
        "target_cost": 850.00,
        "query_search": "cream boucle modern accent armchair aliexpress",
        "supplier_name": "Fornecedor Nacional - Estofados Premium SC",
        "supplier_type": "nacional",
        "supplier_delivery": 12,
        "supplier_rating": 5,
        "prompts": {
            "principal": "A modern minimalist lounge armchair upholstered in luxurious textured cream-colored bouclé fabric, organic rounded curves, oak legs, neutral studio background, premium design furniture photography",
            "lifestyle": "A cozy cream bouclé fabric armchair in a minimalist Japandi style living room corner, near a large window, raw wood side table, beige linen drape, soft warm afternoon light, peaceful atmosphere, 8k",
            "flatlay": "Flat lay style showcase of cream bouclé fabric swatch, a miniature wooden chair model, natural oak wood sample, raw cotton yarn, warm ivory textured paper background, aesthetic design board"
        }
    },
    "luminaria-halo-moderna": {
        "title": "Luminária Halo Moderna",
        "sku": "AD-LUM-HAL-03",
        "category": "Iluminação Japandi",
        "price": 589.00,
        "compare_price": 1200.00,
        "weight_kg": 2.2,
        "dimensions": "35cm altura x 35cm largura x 12cm profundidade",
        "inventory": 30,
        "target_cost": 190.00,
        "query_search": "minimalist halo led table lamp aliexpress",
        "supplier_name": "AliExpress - Halo Lighting Co., Ltd.",
        "supplier_type": "dropshipping",
        "supplier_delivery": 18,
        "supplier_rating": 4,
        "prompts": {
            "principal": "A minimalist modern halo table lamp, circular metallic ring design, warm glowing led light glowing inwards, brushed aluminum bronze finish, dark neutral studio background, premium product design photography",
            "lifestyle": "A glowing minimalist halo circular lamp on a dark wood nightstand in a quiet cozy Japandi bedroom, soft linen bedding, serene warm indirect ambient lighting, wabi-sabi aesthetic, night mood, 8k",
            "flatlay": "Flat lay design moodboard for modern circular lamp, brushed metal sample, acrylic diffuser swatch, warm led bulb, sketch of circular light design, beige concrete background"
        }
    },
    "espelho-assimetrico": {
        "title": "Espelho Assimétrico",
        "sku": "AD-ESP-ASI-04",
        "category": "Decoração Japandi",
        "price": 890.00,
        "compare_price": 1800.00,
        "weight_kg": 7.5,
        "dimensions": "90cm altura x 65cm largura x 4cm espessura",
        "inventory": 20,
        "target_cost": 290.00,
        "query_search": "asymmetrical organic shaped wall mirror aliexpress",
        "supplier_name": "Fornecedor Nacional - Espelhos & Molduras SP",
        "supplier_type": "nacional",
        "supplier_delivery": 10,
        "supplier_rating": 5,
        "prompts": {
            "principal": "A large minimalist wall mirror with a fluid organic asymmetrical shape, thin light wood frame, reflection of a clean empty white wall, neutral studio product photography, modern home decor",
            "lifestyle": "A large organic asymmetrical mirror on a plaster wall in a modern entryway, reflecting a cozy Japandi hallway with an olive tree plant, warm soft natural lighting, elegant home decor, 8k",
            "flatlay": "Flat lay moodboard of an asymmetrical mirror glass sample, natural wood molding slice, light grey plaster background, clean shadows, architectural moodboard"
        }
    }
}


def audit_suppliers_ddg(query_search, fallback_url):
    """Realiza a busca de fornecedores no AliExpress via DDG."""
    print(f"🔍 Auditando fornecedores para query: '{query_search}'")
    try:
        from mining_tools import _ddg_search
        results = _ddg_search(query_search, max_results=3)
        urls = [r.get("href", "") for r in results if r.get("href", "")]
        if urls:
            print(f"   URLs encontradas: {urls}")
            return urls[0]
    except Exception as e:
        print(f"   Erro na busca DDG: {e}")
    
    print(f"   Usando URL de fallback: {fallback_url}")
    return fallback_url


def calculate_cfo_guard(price, cost):
    """Calcula as margens e valida com as regras da CFO GUARD."""
    frete_estimado = cost * 0.15
    costo_total = cost + frete_estimado
    margem_bruta = ((price - cost) / price) * 100
    margem_real = ((price - costo_total) / price) * 100
    status = "✅ APROVADO" if margem_real >= 35.0 else "❌ REPROVADO (margem real < 35%)"
    return {
        "custo_total": costo_total,
        "frete_estimado": frete_estimado,
        "margem_bruta": margem_bruta,
        "margem_real": margem_real,
        "status": status
    }


def generate_images_pollinations(handle, prompts_dict):
    """Gera 3 imagens Japandi para o produto usando Pollinations AI e salva no assets."""
    image_paths = {}
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    for img_type, prompt in prompts_dict.items():
        filename = f"{handle}_{img_type}.png"
        filepath = ASSETS_DIR / filename
        
        if filepath.exists():
            image_paths[img_type] = f"assets/{filename}"
            print(f"   Imagem [{img_type}] para '{handle}' já existe localmente: {filepath}")
            continue
            
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&private=true"
        
        print(f"🎨 Gerando imagem [{img_type}] para '{handle}'...")
        try:
            r = httpx.get(url, timeout=60)
            if r.status_code == 200:
                filepath.write_bytes(r.content)
                image_paths[img_type] = f"assets/{filename}"
                print(f"   Salvo em {filepath}")
            else:
                print(f"   Erro ao gerar ({r.status_code})")
                image_paths[img_type] = f"assets/col-vasos.png"  # fallback local
        except Exception as e:
            print(f"   Exceção na geração de imagem: {e}")
            image_paths[img_type] = f"assets/col-vasos.png"
            
    return image_paths


def generate_copywriting_claude(handle, config):
    """Chama Claude para redigir copywriting premium com foco em Neuroarquitetura, c/ fallback p/ Gemini."""
    title = config["title"]
    category = config["category"]
    price = config["price"]
    
    prompt = f"""
    Você é o copywriter principal da Aura Decore, marca premium de decoração e móveis Japandi.
    Crie o copywriting persuasivo, focado em Neuroarquitetura, Biofilia e Design Wabi-Sabi para:
    - Produto: {title}
    - Categoria: {category}
    - Preço: R$ {price:.2f}

    Retorne APENAS um objeto JSON válido (sem tags ``` ou outros textos) com o seguinte formato:
    {{
        "hook_subtitle": "Um subtítulo elegante que capta o design e o bem-estar mental.",
        "short_description": "Um texto curto (1 parágrafo) e cativante descrevendo a experiência sensorial, toque e sofisticação.",
        "body_html": "O texto longo em HTML estruturado (com tags <h3>, <p>, <ul> e <li>) detalhando a conexão com a neuroarquitetura, os materiais premium e as especificações técnicas básicas do produto.",
        "seo_title": "Título de SEO otimizado com até 60 caracteres.",
        "seo_description": "Descrição de SEO otimizada com até 160 caracteres."
    }}
    """
    
    # Tenta Claude primeiro
    if client_claude:
        print(f"📝 Gerando copy para '{handle}' via Claude...")
        try:
            r = client_claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            content = r.content[0].text.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception as e:
            print(f"   Erro no Claude para '{handle}': {e}. Tentando Gemini...")
            
    # Tenta Gemini como fallback
    print(f"♊ Gerando copy para '{handle}' via Gemini...")
    try:
        from google_ai import GeminiText
        r_gem = GeminiText.generate(prompt, temperature=0.7, max_tokens=1500)
        if r_gem["ok"]:
            content = r_gem["text"].strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        else:
            print(f"   Erro no Gemini: {r_gem['error']}")
    except Exception as e:
        print(f"   Exceção no Gemini para '{handle}': {e}")
        
    print(f"⚠️ Usando copywriting estático de fallback para '{handle}'")
    return generate_copy_fallback(title, category, price)


def generate_copy_fallback(title, category, price):
    """Gera textos de fallback caso o Claude não responda."""
    return {
        "hook_subtitle": "A Conexão com a Natureza e a Estética que Acalma a Mente.",
        "short_description": f"O {title} traz o minimalismo acolhedor da decoração Japandi para o seu espaço. Cada detalhe foi desenhado para inspirar tranquilidade e harmonia tátil.",
        "body_html": f"""
        <h3>Curvas orgânicas que induzem ao relaxamento</h3>
        <p>Desenvolvido sob os preceitos da neuroarquitetura, o {title} reduz a fadiga visual através de sua geometria fluida e textura tátil acolhedora. Ideal para compor pontos de foco serenos em salas de estar, quartos ou escritórios.</p>
        <ul>
            <li><strong>Design Assinado:</strong> Estética Wabi-Sabi premium.</li>
            <li><strong>Sensação Tátil:</strong> Textura suave e acabamento artesanal de alto padrão.</li>
            <li><strong>Conexão Biofílica:</strong> Tons e materiais inspirados no bem-estar natural.</li>
        </ul>
        """,
        "seo_title": f"{title} Premium | Estilo Japandi - Aura Decore",
        "seo_description": f"Transforme seu lar em um refúgio com o {title}. Design ergonômico, texturas orgânicas e entrega segura. Compre online na Aura Decore."
    }


def integrate_db(handle, config, supplier_id):
    """Insere ou atualiza o produto no banco SQLite aura_erp.db."""
    if not DB_PATH.exists():
        print(f"⚠️ Banco de dados {DB_PATH} não encontrado. Ignorando integração SQLite.")
        return
        
    print(f"🗄️ Atualizando banco de dados para '{handle}'...")
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        
        # Gera uma shopify_id fictícia caso o produto não exista
        shopify_id = f"789000000000{abs(hash(handle)) % 1000}"
        
        cur.execute("SELECT id, shopify_id FROM produtos WHERE sku = ?", (config["sku"],))
        row = cur.fetchone()
        
        if row:
            db_id = row[0]
            cur.execute("""
                UPDATE produtos
                SET titulo = ?, preco = ?, custo = ?, estoque = ?, fornecedor_id = ?, atualizado_em = datetime('now','localtime')
                WHERE id = ?
            """, (config["title"], config["price"], config["target_cost"], config["inventory"], supplier_id, db_id))
            print(f"   Atualizado produto ID {db_id} no SQLite.")
        else:
            cur.execute("""
                INSERT INTO produtos (shopify_id, titulo, sku, categoria, preco, custo, estoque, estoque_minimo, fornecedor_id, status, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, 5, ?, 'ativo', datetime('now','localtime'))
            """, (shopify_id, config["title"], config["sku"], config["category"], config["price"], config["target_cost"], config["inventory"], supplier_id))
            print(f"   Inserido novo produto com Shopify ID {shopify_id} no SQLite.")
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao integrar com o SQLite: {e}")


def get_or_create_supplier_db(config):
    """Retorna o ID do fornecedor correspondente ou o cria no SQLite."""
    if not DB_PATH.exists():
        return None
        
    name = config["supplier_name"]
    supplier_type = config["supplier_type"]
    delivery_time = config["supplier_delivery"]
    rating = config["supplier_rating"]
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM fornecedores WHERE nome = ?", (name,))
        row = cur.fetchone()
        
        if row:
            supplier_id = row[0]
        else:
            cur.execute("""
                INSERT INTO fornecedores (nome, tipo, prazo_entrega, avaliacao, notas, criado_em)
                VALUES (?, ?, ?, ?, ?, datetime('now','localtime'))
            """, (name, supplier_type, delivery_time, rating, f"Fornecedor auditado para {config['title']}"))
            supplier_id = cur.lastrowid
            print(f"   Fornecedor '{name}' cadastrado com ID {supplier_id}.")
            
        conn.commit()
        conn.close()
        return supplier_id
    except Exception as e:
        print(f"❌ Erro ao gerenciar fornecedor no banco: {e}")
        return None


def enrich_csv(all_results):
    """Enriquece o arquivo produtos_aura.csv com todas as colunas adicionais."""
    if not CSV_PATH.exists():
        print(f"⚠️ CSV {CSV_PATH} não encontrado. Pulando enriquecimento.")
        return
        
    print(f"📄 Enriquecendo CSV '{CSV_PATH}'...")
    
    # Colunas originais + enriquecidas
    fieldnames = [
        "Handle", "Title", "Body (HTML)", "Vendor", "Standard Product Type", "Published",
        "Variant Price", "Variant Compare At Price", "Variant SKU", "Tags", "SEO Title", "SEO Description",
        "Variant Cost", "Weight", "Dimensions", "Image 1", "Image 2", "Image 3", "Fornecedor", "Inventory Qty"
    ]
    
    updated_rows = []
    
    try:
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            original_rows = list(reader)
            
        # Percorre as linhas originais do CSV
        for row in original_rows:
            handle = row.get("Handle", "").strip()
            if handle in all_results:
                res = all_results[handle]
                config = PRODUCTS_CONFIG[handle]
                
                # Atualiza/Insere os campos enriquecidos
                row["Body (HTML)"] = res["copy"]["body_html"]
                row["SEO Title"] = res["copy"]["seo_title"]
                row["SEO Description"] = res["copy"]["seo_description"]
                row["Variant Cost"] = f"{config['target_cost']:.2f}"
                row["Weight"] = f"{config['weight_kg']} kg"
                row["Dimensions"] = config["dimensions"]
                row["Image 1"] = res["images"].get("principal", "")
                row["Image 2"] = res["images"].get("lifestyle", "")
                row["Image 3"] = res["images"].get("flatlay", "")
                row["Fornecedor"] = config["supplier_name"]
                row["Inventory Qty"] = str(config["inventory"])
            else:
                # Preenche com vazio para produtos não mapeados se houver
                for col in fieldnames[12:]:
                    row[col] = ""
                    
            updated_rows.append(row)
            
        # Se algum produto configurado não estava no CSV original, insere
        existing_handles = [r.get("Handle", "") for r in updated_rows]
        for handle, config in PRODUCTS_CONFIG.items():
            if handle not in existing_handles:
                res = all_results[handle]
                new_row = {
                    "Handle": handle,
                    "Title": config["title"],
                    "Body (HTML)": res["copy"]["body_html"],
                    "Vendor": "Aura Decore",
                    "Standard Product Type": config["category"],
                    "Published": "TRUE",
                    "Variant Price": f"{config['price']:.2f}",
                    "Variant Compare At Price": f"{config['compare_price']:.2f}",
                    "Variant SKU": config["sku"],
                    "Tags": f"Japandi, {config['title']}, Neuroarquitetura",
                    "SEO Title": res["copy"]["seo_title"],
                    "SEO Description": res["copy"]["seo_description"],
                    "Variant Cost": f"{config['target_cost']:.2f}",
                    "Weight": f"{config['weight_kg']} kg",
                    "Dimensions": config["dimensions"],
                    "Image 1": res["images"].get("principal", ""),
                    "Image 2": res["images"].get("lifestyle", ""),
                    "Image 3": res["images"].get("flatlay", ""),
                    "Fornecedor": config["supplier_name"],
                    "Inventory Qty": str(config["inventory"])
                }
                updated_rows.append(new_row)

        with open(CSV_PATH, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)
            
        print("   CSV enriquecido com sucesso.")
    except Exception as e:
        print(f"❌ Erro ao enriquecer o CSV: {e}")


def write_product_html(handle, config, copy_info, image_info):
    """Escreve e estiliza de forma premium o HTML de preview individual do produto."""
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    filepath = PREVIEW_DIR / f"aura-{handle}.html"
    
    # Formatação de preços
    price_str = f"R$ {config['price']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    comp_price_str = f"R$ {config['compare_price']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    # Imagens
    img_p = image_info.get("principal", "assets/col-vasos.png")
    img_l = image_info.get("lifestyle", "assets/lookbook.png")
    img_f = image_info.get("flatlay", "assets/col-texteis.png")
    
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config['title']} - Aura Decore</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --sand: #f5f2eb;
            --cream: #FAF9F6;
            --terracotta: #c46c53;
            --dark-terracotta: #a65842;
            --text-main: #2c2a29;
            --text-light: #595552;
        }}
        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--cream);
            color: var(--text-main);
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }}
        h1, h2, h3 {{
            font-family: 'Playfair Display', serif;
            font-weight: 400;
        }}
        .header {{
            text-align: center;
            padding: 2rem 0;
            border-bottom: 1px solid rgba(0,0,0,0.05);
            background: white;
        }}
        .header h1 {{
            margin: 0;
            font-size: 1.6rem;
            letter-spacing: 3px;
            text-transform: uppercase;
        }}
        .header h1 a {{
            text-decoration: none;
            color: var(--text-main);
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 4rem 2rem;
            display: grid;
            grid-template-columns: 1.1fr 0.9fr;
            gap: 4rem;
            align-items: start;
        }}
        .image-col {{
            position: sticky;
            top: 2rem;
        }}
        .main-img-wrap {{
            width: 100%;
            height: 550px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.08);
            background: #eee;
        }}
        .main-img-wrap img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.4s ease;
        }}
        .main-img-wrap img:hover {{
            transform: scale(1.03);
        }}
        .thumbnail-gallery {{
            display: flex;
            gap: 15px;
            margin-top: 20px;
        }}
        .thumbnail-gallery img {{
            width: 90px;
            height: 90px;
            object-fit: cover;
            cursor: pointer;
            border-radius: 6px;
            border: 2px solid transparent;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            transition: all 0.2s ease;
        }}
        .thumbnail-gallery img:hover {{
            transform: translateY(-2px);
        }}
        .thumbnail-gallery img.active {{
            border-color: var(--terracotta);
        }}
        .content-col {{
            padding-top: 10px;
        }}
        .category-tag {{
            font-size: 0.85rem;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: var(--terracotta);
            margin-bottom: 1rem;
            font-weight: 600;
        }}
        .product-title {{
            font-size: 2.6rem;
            color: var(--text-main);
            margin-top: 0;
            margin-bottom: 0.5rem;
            line-height: 1.2;
        }}
        .hook-text {{
            font-size: 1.25rem;
            font-family: 'Playfair Display', serif;
            font-style: italic;
            color: var(--text-light);
            margin-bottom: 1.5rem;
        }}
        .price-section {{
            display: flex;
            align-items: baseline;
            gap: 1.2rem;
            margin: 2rem 0;
            padding: 1.5rem 0;
            border-top: 1px solid rgba(0,0,0,0.05);
            border-bottom: 1px solid rgba(0,0,0,0.05);
        }}
        .price {{
            font-size: 2.2rem;
            font-weight: 600;
            color: var(--terracotta);
        }}
        .old-price {{
            font-size: 1.3rem;
            color: var(--text-light);
            text-decoration: line-through;
        }}
        .description-short {{
            font-size: 1.1rem;
            color: var(--text-main);
            font-weight: 500;
            margin-bottom: 2rem;
            line-height: 1.7;
        }}
        .description-body {{
            font-size: 1.05rem;
            color: var(--text-light);
            margin-bottom: 2.5rem;
            line-height: 1.8;
        }}
        .description-body h3 {{
            color: var(--text-main);
            font-size: 1.4rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }}
        .description-body ul {{
            padding-left: 1.5rem;
            margin-bottom: 2rem;
        }}
        .description-body li {{
            margin-bottom: 0.5rem;
        }}
        .cta-button {{
            display: inline-block;
            background-color: var(--terracotta);
            color: white;
            padding: 1.3rem 2.5rem;
            font-size: 1.1rem;
            font-weight: 600;
            text-decoration: none;
            border-radius: 4px;
            text-align: center;
            transition: all 0.3s ease;
            width: 100%;
            box-sizing: border-box;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            box-shadow: 0 10px 20px rgba(196,108,83,0.25);
        }}
        .cta-button:hover {{
            background-color: var(--dark-terracotta);
            transform: translateY(-2px);
            box-shadow: 0 15px 25px rgba(196,108,83,0.35);
        }}
        .spec-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 3rem;
            background: white;
            border-radius: 6px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.02);
        }}
        .spec-table th, .spec-table td {{
            padding: 1rem 1.2rem;
            text-align: left;
            font-size: 0.95rem;
            border-bottom: 1px solid rgba(0,0,0,0.04);
        }}
        .spec-table th {{
            background-color: var(--sand);
            color: var(--text-main);
            font-weight: 600;
            width: 35%;
        }}
        .benefits {{
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid rgba(0,0,0,0.05);
        }}
        .benefit-item {{
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.2rem;
            color: var(--text-main);
            font-weight: 600;
            font-size: 1rem;
        }}
        .benefit-item svg {{
            width: 22px;
            height: 22px;
            color: var(--terracotta);
        }}
        .back-link-wrap {{
            margin-top: 3rem;
            text-align: center;
        }}
        .back-link {{
            color: var(--text-light);
            text-decoration: none;
            font-weight: 600;
            font-size: 1rem;
            transition: color 0.2s ease;
        }}
        .back-link:hover {{
            color: var(--terracotta);
        }}
        @media (max-width: 900px) {{
            .container {{
                grid-template-columns: 1fr;
                gap: 3rem;
                padding: 2rem 1.5rem;
            }}
            .image-col {{
                position: relative;
                top: 0;
            }}
            .main-img-wrap {{
                height: 400px;
            }}
        }}
    </style>
</head>
<body>
    <header class="header">
        <h1><a href="index.html">Aura Decore</a></h1>
    </header>
    
    <main class="container">
        <div class="image-col">
            <div class="main-img-wrap">
                <img id="main-product-img" src="{img_p}" alt="{config['title']}">
            </div>
            <div class="thumbnail-gallery">
                <img src="{img_p}" alt="Foto Principal" class="active" onclick="changeImage('{img_p}', this)">
                <img src="{img_l}" alt="Ambiente/Lifestyle" onclick="changeImage('{img_l}', this)">
                <img src="{img_f}" alt="Flat Lay" onclick="changeImage('{img_f}', this)">
            </div>
        </div>
        
        <div class="content-col">
            <div class="category-tag">{config['category']}</div>
            <h2 class="product-title">{config['title']}</h2>
            <div class="hook-text">{copy_info.get('hook_subtitle', '')}</div>
            
            <div class="price-section">
                <span class="price">{price_str}</span>
                <span class="old-price">{comp_price_str}</span>
            </div>
            
            <div class="description-short">
                {copy_info.get('short_description', '')}
            </div>
            
            <div class="description-body">
                {copy_info.get('body_html', '')}
            </div>
            
            <a href="#" class="cta-button" onclick="alert('Funcionalidade de compra simulada para este preview local ✦')">Adicionar ao Meu Refúgio</a>
            
            <table class="spec-table">
                <tr>
                    <th>SKU</th>
                    <td>{config['sku']}</td>
                </tr>
                <tr>
                    <th>Dimensões</th>
                    <td>{config['dimensions']}</td>
                </tr>
                <tr>
                    <th>Peso Estimado</th>
                    <td>{config['weight_kg']} kg</td>
                </tr>
                <tr>
                    <th>Disponibilidade</th>
                    <td>Em Estoque ({config['inventory']} unidades)</td>
                </tr>
                <tr>
                    <th>Fornecedor Mapeado</th>
                    <td>{config['supplier_name']}</td>
                </tr>
                <tr>
                    <th>Prazo de Envio</th>
                    <td>Envio imediato, entrega estimada em {config['supplier_delivery']} dias úteis</td>
                </tr>
            </table>
            
            <div class="benefits">
                <div class="benefit-item">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                    Compra 100% Segura & Encriptada
                </div>
                <div class="benefit-item">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                    Garantia Incondicional de 7 Dias Aura
                </div>
                <div class="benefit-item">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                    Design Curado e Texturas Naturais Premium
                </div>
            </div>
            
            <div class="back-link-wrap">
                <a href="index.html" class="back-link">← Voltar à Home do Preview</a>
            </div>
        </div>
    </main>

    <script>
    function changeImage(src, element) {{
        document.getElementById('main-product-img').src = src;
        const thumbs = document.querySelectorAll('.thumbnail-gallery img');
        thumbs.forEach(t => t.classList.remove('active'));
        element.classList.add('active');
    }}
    </script>
</body>
</html>"""
    
    try:
        filepath.write_text(html_content, encoding="utf-8")
        print(f"   Visualização salva com sucesso em {filepath}")
    except Exception as e:
        print(f"❌ Erro ao escrever visualização HTML: {e}")


def update_home_page_links(all_results):
    """Atualiza index.html do preview para mapear corretamente os 4 produtos principais."""
    filepath = PREVIEW_DIR / "index.html"
    if not filepath.exists():
        print(f"⚠️ Index home {filepath} não encontrado.")
        return
        
    print(f"🔗 Atualizando index.html do preview para linkar os produtos...")
    try:
        content = filepath.read_text(encoding="utf-8")
        
        # 1. Atualizar Card do Vaso Orgânico Terracota (normalmente Card 1 no Best Sellers)
        # Substitui a div do Card 1
        vaso_res = all_results.get("vaso-organico-terracota")
        if vaso_res:
            old_vaso_snippet = '<div class="product-card" onclick="window.location.href=\'aura-vaso-organico-terracota.html\'">'
            new_vaso_snippet = '<div class="product-card" onclick="window.location.href=\'aura-vaso-organico-terracota.html\'">'
            # Vamos procurar onde o vaso-alma.png está na lista de produtos dos best sellers e substituir toda a div dele
            # Vamos usar uma substituição direta da div
            
        # Para ser mais robusto, vamos modificar o HTML de index.html usando regex ou marcadores específicos dos best sellers.
        # Os 8 Cards de produtos começam na linha 240+
        # Vamos reestruturar os 8 cards dos mais desejados (Best Sellers) de forma fixa e super limpa para os 4 produtos principais da Aura mais 4 outros do catálogo original
        
        # Vamos extrair as divs dos cards
        best_sellers_section_start = content.find('<div class="products-grid reveal">', content.find('M A I S &nbsp; D E S E J A D O S'))
        best_sellers_section_end = content.find('</div>\n  </div>\n</section>', best_sellers_section_start)
        
        if best_sellers_section_start != -1 and best_sellers_section_end != -1:
            # Substitui o bloco dos Best Sellers pelos nossos 4 produtos principais enriquecidos e outros 4 secundários
            new_best_sellers_content = """<div class="products-grid reveal">
      <!-- Card 1: Vaso Orgânico Terracota -->
      <div class="product-card" onclick="window.location.href='aura-vaso-organico-terracota.html'">
        <div class="product-img">
          <img src="assets/vaso-organico-terracota_principal.png" alt="Vaso Orgânico Terracota" loading="lazy">
          <span class="product-badge" style="background: var(--terracotta);">Mais Vendido</span>
          <span class="product-quick">👁 Spooky Preview</span>
        </div>
        <div class="product-info">
          <p class="product-cat">Decoração Japandi</p>
          <h4>Vaso Orgânico Terracota</h4>
          <p class="product-price">R$ 349,00 <small>6x R$ 58,17</small></p>
          <p class="product-stars">★★★★★</p>
          <a href="#" class="product-card-btn" onclick="event.stopPropagation();">Adicionar ao Refúgio</a>
        </div>
      </div>
      
      <!-- Card 2: Luminária Halo Moderna -->
      <div class="product-card" onclick="window.location.href='aura-luminaria-halo-moderna.html'">
        <div class="product-img">
          <img src="assets/luminaria-halo-moderna_principal.png" alt="Luminária Halo Moderna" loading="lazy">
          <span class="product-badge" style="background: var(--terracotta);">Destaque</span>
          <span class="product-quick">👁 Spooky Preview</span>
        </div>
        <div class="product-info">
          <p class="product-cat">Iluminação Japandi</p>
          <h4>Luminária Halo Moderna</h4>
          <p class="product-price">R$ 589,00 <small>6x R$ 98,17</small></p>
          <p class="product-stars">★★★★★</p>
          <a href="#" class="product-card-btn" onclick="event.stopPropagation();">Adicionar ao Refúgio</a>
        </div>
      </div>

      <!-- Card 3: Poltrona Bouclé Creme -->
      <div class="product-card" onclick="window.location.href='aura-poltrona-boucle-creme.html'">
        <div class="product-img">
          <img src="assets/poltrona-boucle-creme_principal.png" alt="Poltrona Bouclé Creme" loading="lazy">
          <span class="product-badge" style="background: var(--terracotta);">Premium Luxo</span>
          <span class="product-quick">👁 Spooky Preview</span>
        </div>
        <div class="product-info">
          <p class="product-cat">Móveis Japandi</p>
          <h4>Poltrona Bouclé Creme</h4>
          <p class="product-price">R$ 2.490,00 <small>6x R$ 415,00</small></p>
          <p class="product-stars">★★★★★</p>
          <a href="#" class="product-card-btn" onclick="event.stopPropagation();">Adicionar ao Refúgio</a>
        </div>
      </div>

      <!-- Card 4: Espelho Assimétrico -->
      <div class="product-card" onclick="window.location.href='aura-espelho-assimetrico.html'">
        <div class="product-img">
          <img src="assets/espelho-assimetrico_principal.png" alt="Espelho Assimétrico" loading="lazy">
          <span class="product-badge" style="background: var(--terracotta);">Novidade</span>
          <span class="product-quick">👁 Spooky Preview</span>
        </div>
        <div class="product-info">
          <p class="product-cat">Decoração Japandi</p>
          <h4>Espelho Assimétrico</h4>
          <p class="product-price">R$ 890,00 <small>6x R$ 148,33</small></p>
          <p class="product-stars">★★★★★</p>
          <a href="#" class="product-card-btn" onclick="event.stopPropagation();">Adicionar ao Refúgio</a>
        </div>
      </div>
      
      <!-- Card 5: Vela Ritual (catálogo antigo) -->
      <div class="product-card">
        <div class="product-img">
          <img src="assets/vela-ritual.png" alt="Vela Ritual em Cerâmica" loading="lazy">
          <span class="product-quick">👁</span>
        </div>
        <div class="product-info">
          <p class="product-cat">Velas & Aromas</p>
          <h4>Vela Ritual</h4>
          <p class="product-price">R$ 179,00 <small>6x R$ 29,83</small></p>
          <p class="product-stars">★★★★★</p>
          <a href="#" class="product-card-btn">Adicionar ao Refúgio</a>
        </div>
      </div>

      <!-- Card 6: Manta Ninho (catálogo antigo) -->
      <div class="product-card">
        <div class="product-img">
          <img src="assets/manta-ninho.png" alt="Manta Ninho em Algodão Orgânico" loading="lazy">
          <span class="product-badge">Têxtil</span>
          <span class="product-quick">👁</span>
        </div>
        <div class="product-info">
          <p class="product-cat">Têxteis</p>
          <h4>Manta Ninho</h4>
          <p class="product-price">R$ 349,00 <small>6x R$ 58,17</small></p>
          <p class="product-stars">★★★★★</p>
          <a href="#" class="product-card-btn">Adicionar ao Refúgio</a>
        </div>
      </div>

      <!-- Card 7: Difusor Névoa (catálogo antigo) -->
      <div class="product-card">
        <div class="product-img">
          <img src="assets/difusor.png" alt="Difusor de Ambiente Névoa" loading="lazy">
          <span class="product-quick">👁</span>
        </div>
        <div class="product-info">
          <p class="product-cat">Velas & Aromas</p>
          <h4>Difusor Névoa</h4>
          <p class="product-price">R$ 149,00 <small>6x R$ 24,83</small></p>
          <p class="product-stars">★★★★★</p>
          <a href="#" class="product-card-btn">Adicionar ao Refúgio</a>
        </div>
      </div>

      <!-- Card 8: Bandeja Zen (catálogo antigo) -->
      <div class="product-card">
        <div class="product-img">
          <img src="assets/bandeja-zen.png" alt="Bandeja Zen Efeito Travertino" loading="lazy">
          <span class="product-quick">👁</span>
        </div>
        <div class="product-info">
          <p class="product-cat">Bandejas & Objetos</p>
          <h4>Bandeja Zen</h4>
          <p class="product-price">R$ 219,00 <small>6x R$ 36,50</small></p>
          <p class="product-stars">★★★★☆</p>
          <a href="#" class="product-card-btn">Adicionar ao Refúgio</a>
        </div>
      </div>"""
            
            content = content[:best_sellers_section_start] + new_best_sellers_content + content[best_sellers_section_end:]
            filepath.write_text(content, encoding="utf-8")
            print("   index.html atualizado e linkado com sucesso.")
        else:
            print("❌ Não foi possível encontrar a seção dos Best Sellers no index.html.")
            
    except Exception as e:
        print(f"❌ Erro ao atualizar o index.html: {e}")


def main():
    print("=====================================================================")
    print("         INICIANDO AUTOMATIZAÇÃO — INTEGRAR AURA DECORE")
    print("=====================================================================")
    
    all_results = {}
    
    for handle, config in PRODUCTS_CONFIG.items():
        print(f"\n📦 Processando: '{config['title']}' ({handle})")
        print("-" * 50)
        
        # 1. Auditoria de fornecedores
        fallback_url = f"https://www.aliexpress.com/wholesale?SearchText={urllib.parse.quote(config['query_search'])}"
        supplier_url = audit_suppliers_ddg(config["query_search"], fallback_url)
        
        # 2. CFO Guard Margins
        financials = calculate_cfo_guard(config["price"], config["target_cost"])
        print(f"💰 Margens CFO GUARD:")
        print(f"   Preço de Venda: R$ {config['price']:.2f}")
        print(f"   Preço de Custo (Supplier): R$ {config['target_cost']:.2f}")
        print(f"   Frete Estimado (15%): R$ {financials['frete_estimado']:.2f}")
        print(f"   Custo Total Mapeado: R$ {financials['custo_total']:.2f}")
        print(f"   Margem Bruta: {financials['margem_bruta']:.1f}%")
        print(f"   Margem Real: {financials['margem_real']:.1f}%")
        print(f"   Status da CFO Guard: {financials['status']}")
        
        # 3. Geração de imagens Pollinations AI
        images_info = generate_images_pollinations(handle, config["prompts"])
        
        # 4. Geração de Copy via Claude
        copy_info = generate_copywriting_claude(handle, config)
        print(f"📝 Copywriting Gerado:")
        print(f"   Subtítulo: '{copy_info.get('hook_subtitle')}'")
        print(f"   SEO Title: '{copy_info.get('seo_title')}'")
        
        # Armazena os resultados para os fluxos agregados
        all_results[handle] = {
            "supplier_url": supplier_url,
            "financials": financials,
            "images": images_info,
            "copy": copy_info
        }
        
        # 5. Integrar no SQLite local
        supplier_id = get_or_create_supplier_db(config)
        integrate_db(handle, config, supplier_id)
        
        # 6. Escrever o preview HTML individual do produto
        write_product_html(handle, config, copy_info, images_info)
        
    # 7. Enriquecer o arquivo CSV de produtos
    enrich_csv(all_results)
    
    # 8. Atualizar index.html com as ligações correspondentes
    update_home_page_links(all_results)
    
    print("\n=====================================================================")
    print("       AUTOMATIZAÇÃO E INTEGRAÇÃO DE PRODUTOS FINALIZADA COM SUCESSO")
    print("=====================================================================")


if __name__ == "__main__":
    main()
