"""
Ferramentas de mineração real para NEXUS — AliExpress, Dropi, Tendências.
Usa DuckDuckGo (sem chave) + httpx para scraping básico.
"""
from __future__ import annotations
import json
import re
import time
from typing import Optional
import httpx
from crewai.tools import BaseTool
from pydantic import Field


def _ddg_search(query: str, max_results: int = 8) -> list[dict]:
    """Busca no DuckDuckGo. Retorna lista de {title, href, body}."""
    try:
        # Tenta nova API (ddgs) primeiro, fallback para duckduckgo_search
        try:
            from ddgs import DDGS
            with DDGS() as d:
                return list(d.text(query, max_results=max_results))
        except ImportError:
            from duckduckgo_search import DDGS
            return list(DDGS().text(query, max_results=max_results))
    except Exception as e:
        return [{"title": "Erro DDG", "href": "", "body": str(e)}]


def _extract_aliexpress_price(text: str) -> str:
    """Extrai preço USD/BRL de texto (best-effort)."""
    m = re.search(r"(?:US\s?\$|R\$|USD\s?)[\s]?([\d.,]+)", text, re.IGNORECASE)
    if m:
        return m.group(0).strip()
    # fallback: qualquer número que pareça preço
    m = re.search(r"\b(\d{1,3}[.,]\d{2})\b", text)
    if m:
        return m.group(0)
    return "—"


class AliExpressSearchTool(BaseTool):
    name: str = "AliExpressSearch"
    description: str = (
        "Busca produtos no AliExpress. "
        "Input: query em inglês (ex: 'japandi ceramic vase home decor'). "
        "Output: lista de produtos encontrados com título, URL, preço e avaliação."
    )

    def _run(self, query: str) -> str:
        queries = [
            f"{query} aliexpress buy price",
            f"{query} aliexpress wholesale dropship",
        ]
        all_results = []
        for q in queries:
            all_results.extend(_ddg_search(q, max_results=6))
            time.sleep(0.5)

        seen = set()
        products = []
        for r in all_results:
            href = r.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            price = _extract_aliexpress_price(r.get("body", ""))
            is_ali = "aliexpress.com" in href
            products.append({
                "titulo": r.get("title", "").strip()[:120],
                "url": href,
                "preco_estimado": price,
                "descricao": r.get("body", "").strip()[:200],
                "fonte": "AliExpress" if is_ali else "Outro",
            })
            if len(products) >= 10:
                break

        if not products:
            return f"Nenhum produto encontrado para: {query}"

        lines = [f"## AliExpress Search — {query}\n"]
        for i, p in enumerate(products, 1):
            lines.append(f"**{i}. {p['titulo']}** [{p['fonte']}]")
            lines.append(f"   Preço: {p['preco_estimado']}")
            lines.append(f"   URL: {p['url']}")
            lines.append(f"   Desc: {p['descricao']}\n")
        return "\n".join(lines)


class TrendSearchTool(BaseTool):
    name: str = "TrendSearch"
    description: str = (
        "Pesquisa tendências de produtos para decoração Japandi/wabi-sabi no mercado brasileiro. "
        "Input: categoria ou palavra-chave (ex: 'vasos ceramica japandi 2025'). "
        "Output: tendências, produtos em alta, preços e contexto de mercado."
    )

    def _run(self, query: str) -> str:
        searches = [
            f"{query} tendencia brasil 2025 decoração",
            f"{query} japandi wabi-sabi dropshipping margem",
            f"site:pinterest.com/pin {query} home decor",
        ]
        all_results = []
        for q in searches:
            all_results.extend(_ddg_search(q, max_results=5))
            time.sleep(0.4)

        if not all_results:
            return f"Sem resultados de tendência para: {query}"

        lines = [f"## Tendências — {query}\n"]
        seen = set()
        count = 0
        for r in all_results:
            href = r.get("href", "")
            if href in seen:
                continue
            seen.add(href)
            lines.append(f"**{r.get('title','').strip()[:100]}**")
            lines.append(f"   {r.get('body','').strip()[:250]}")
            lines.append(f"   Fonte: {href}\n")
            count += 1
            if count >= 8:
                break
        return "\n".join(lines)


class MarginCalculatorTool(BaseTool):
    name: str = "MarginCalculator"
    description: str = (
        "Calcula margem de lucro e preço de venda sugerido para um produto dropshipping. "
        "Input JSON: {\"custo_usd\": 5.50, \"taxa_cambio\": 5.80, \"markup\": 2.5} "
        "— markup padrão 2.5x (margem ~60%). "
        "Output: preço de custo BRL, preço sugerido BRL, margem %, se passa no filtro >35%."
    )

    def _run(self, input_str: str) -> str:
        try:
            data = json.loads(input_str)
        except Exception:
            # tenta extrair números diretamente
            nums = re.findall(r"[\d.]+", input_str)
            if len(nums) < 1:
                return "Erro: forneça custo_usd no mínimo."
            data = {
                "custo_usd": float(nums[0]),
                "taxa_cambio": float(nums[1]) if len(nums) > 1 else 5.80,
                "markup": float(nums[2]) if len(nums) > 2 else 2.5,
            }

        custo_usd = float(data.get("custo_usd", 0))
        cambio = float(data.get("taxa_cambio", 5.80))
        markup = float(data.get("markup", 2.5))

        custo_brl = custo_usd * cambio
        preco_sugerido = custo_brl * markup
        margem = ((preco_sugerido - custo_brl) / preco_sugerido) * 100

        frete_estimado = custo_brl * 0.15  # ~15% do custo como frete médio
        custo_total = custo_brl + frete_estimado
        margem_real = ((preco_sugerido - custo_total) / preco_sugerido) * 100

        status = "✅ APROVADO" if margem_real >= 35 else "❌ REPROVADO (margem < 35%)"

        return (
            f"💰 Cálculo de Margem\n"
            f"Custo USD: ${custo_usd:.2f}\n"
            f"Câmbio: R${cambio:.2f}\n"
            f"Custo BRL: R${custo_brl:.2f}\n"
            f"Frete estimado: R${frete_estimado:.2f}\n"
            f"Custo total: R${custo_total:.2f}\n"
            f"Preço sugerido (markup {markup}x): R${preco_sugerido:.2f}\n"
            f"Margem bruta: {margem:.1f}%\n"
            f"Margem real (c/ frete): {margem_real:.1f}%\n"
            f"Resultado: {status}"
        )


class DropisSearchTool(BaseTool):
    name: str = "DropisSearch"
    description: str = (
        "Busca produtos no catálogo Dropi (dropshipping nacional). "
        "Input: categoria ou produto (ex: 'vaso ceramica'). "
        "Output: produtos disponíveis com preços e informações de fornecedor."
    )

    def _run(self, query: str) -> str:
        searches = [
            f"dropi.com.br {query} preco",
            f"dropi dropshipping {query} fornecedor brasil",
            f"habitoo dropshipping {query} decoracao casa",
        ]
        all_results = []
        for q in searches:
            all_results.extend(_ddg_search(q, max_results=5))
            time.sleep(0.4)

        if not all_results:
            return f"Sem resultados no Dropi/Habitoo para: {query}"

        lines = [f"## Dropi/Habitoo — {query}\n"]
        seen = set()
        count = 0
        for r in all_results:
            href = r.get("href", "")
            if href in seen:
                continue
            seen.add(href)
            price = _extract_aliexpress_price(r.get("body", ""))
            lines.append(f"**{r.get('title','').strip()[:100]}**")
            lines.append(f"   Preço: {price}")
            lines.append(f"   {r.get('body','').strip()[:200]}")
            lines.append(f"   Fonte: {href}\n")
            count += 1
            if count >= 6:
                break
        return "\n".join(lines)


# Instâncias prontas para importar no crew_agents.py
aliexpress_search = AliExpressSearchTool()
trend_search = TrendSearchTool()
margin_calculator = MarginCalculatorTool()
dropis_search = DropisSearchTool()

NEXUS_TOOLS = [aliexpress_search, trend_search, dropis_search]
KAI_TOOLS = [margin_calculator, dropis_search]
