"""
ERP/CRM Aura Decore — Rotas FastAPI
====================================
Router montado em /erp no app principal. Módulos:
  /erp/dashboard            — visão geral (KPIs de todos os módulos)
  /erp/crm/...              — clientes, leads, funil, interações
  /erp/pedidos/...          — pedidos (sync Shopify)
  /erp/estoque/...          — produtos, inventário, alertas
  /erp/financeiro/...       — receitas, despesas, MEI
  /erp/fornecedores/...     — fornecedores e compras
  /erp/sync/shopify         — sincroniza clientes+pedidos+produtos reais
"""
import os
import json
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, Body, Query
from pydantic import BaseModel

import erp_db as db

router = APIRouter(prefix="/erp", tags=["ERP"])

_SHOPIFY_DOMAIN = os.getenv("SHOPIFY_DOMAIN", "")
_SHOPIFY_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "")
_API_VER = "2025-01"
MEI_LIMITE = float(os.getenv("MEI_LIMIT_ANUAL", "81000"))
MARGEM_MIN = float(os.getenv("MARGEM_MIN", "0.35"))


def _shopify_headers():
    return {"X-Shopify-Access-Token": _SHOPIFY_TOKEN, "Content-Type": "application/json"}


# ════════════════════════════════════════════════════════════════
# INICIALIZAÇÃO
# ════════════════════════════════════════════════════════════════
@router.on_event("startup")
def _startup():
    db.init_db()


@router.post("/init")
def init():
    """(Re)cria as tabelas do banco ERP."""
    return db.init_db()


# ════════════════════════════════════════════════════════════════
# DASHBOARD GERAL
# ════════════════════════════════════════════════════════════════
@router.get("/dashboard")
def dashboard():
    """KPIs consolidados de todos os módulos para a home do ERP."""
    ano = datetime.now().year

    # Financeiro
    receita_ano = db.query_one(
        "SELECT COALESCE(SUM(valor),0) v FROM financeiro WHERE tipo='receita' AND strftime('%Y',data)=?",
        (str(ano),))["v"]
    despesa_ano = db.query_one(
        "SELECT COALESCE(SUM(valor),0) v FROM financeiro WHERE tipo='despesa' AND strftime('%Y',data)=?",
        (str(ano),))["v"]
    receita_mes = db.query_one(
        "SELECT COALESCE(SUM(valor),0) v FROM financeiro WHERE tipo='receita' AND strftime('%Y-%m',data)=?",
        (datetime.now().strftime("%Y-%m"),))["v"]

    # CRM
    total_clientes = db.query_one("SELECT COUNT(*) c FROM clientes")["c"]
    funil = db.query("SELECT estagio, COUNT(*) qtd FROM clientes GROUP BY estagio")

    # Pedidos
    total_pedidos = db.query_one("SELECT COUNT(*) c FROM pedidos")["c"]
    pedidos_pendentes = db.query_one(
        "SELECT COUNT(*) c FROM pedidos WHERE status IN ('pendente','pago')")["c"]
    ticket = db.query_one("SELECT COALESCE(AVG(total),0) v FROM pedidos")["v"]

    # Estoque
    total_produtos = db.query_one("SELECT COUNT(*) c FROM produtos")["c"]
    estoque_baixo = db.query_one(
        "SELECT COUNT(*) c FROM produtos WHERE estoque <= estoque_minimo")["c"]

    return {
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "financeiro": {
            "receita_ano": round(receita_ano, 2),
            "despesa_ano": round(despesa_ano, 2),
            "lucro_ano": round(receita_ano - despesa_ano, 2),
            "receita_mes": round(receita_mes, 2),
            "mei": _mei_status(receita_ano),
        },
        "crm": {"total_clientes": total_clientes, "funil": {f["estagio"]: f["qtd"] for f in funil}},
        "pedidos": {
            "total": total_pedidos,
            "pendentes": pedidos_pendentes,
            "ticket_medio": round(ticket, 2),
        },
        "estoque": {"total_produtos": total_produtos, "alertas_estoque_baixo": estoque_baixo},
    }


def _mei_status(receita_ano: float) -> dict:
    pct = (receita_ano / MEI_LIMITE * 100) if MEI_LIMITE else 0
    if pct >= 100:
        farol = "🔴 ESTOUROU"
    elif pct >= 80:
        farol = "🟠 ATENÇÃO"
    else:
        farol = "🟢 SEGURO"
    return {
        "limite_anual": MEI_LIMITE,
        "faturado": round(receita_ano, 2),
        "disponivel": round(MEI_LIMITE - receita_ano, 2),
        "percentual": round(pct, 1),
        "farol": farol,
    }


# ════════════════════════════════════════════════════════════════
# CRM
# ════════════════════════════════════════════════════════════════
class ClienteIn(BaseModel):
    nome: str
    email: str = ""
    telefone: str = ""
    cidade: str = ""
    estado: str = ""
    estagio: str = "lead"
    origem: str = "manual"
    tags: str = ""
    notas: str = ""


@router.get("/crm/clientes")
def listar_clientes(estagio: str = "", busca: str = "", limit: int = 100):
    sql = "SELECT * FROM clientes WHERE 1=1"
    p = []
    if estagio:
        sql += " AND estagio=?"; p.append(estagio)
    if busca:
        sql += " AND (nome LIKE ? OR email LIKE ? OR telefone LIKE ?)"
        p += [f"%{busca}%"] * 3
    sql += " ORDER BY atualizado_em DESC LIMIT ?"; p.append(limit)
    return {"clientes": db.query(sql, tuple(p))}


@router.post("/crm/clientes")
def criar_cliente(c: ClienteIn):
    cid = db.execute(
        """INSERT INTO clientes (nome,email,telefone,cidade,estado,estagio,origem,tags,notas)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (c.nome, c.email, c.telefone, c.cidade, c.estado, c.estagio, c.origem, c.tags, c.notas))
    return {"status": "ok", "id": cid}


@router.put("/crm/clientes/{cid}/estagio")
def mover_funil(cid: int, estagio: str = Body(..., embed=True)):
    db.execute("UPDATE clientes SET estagio=?, atualizado_em=datetime('now','localtime') WHERE id=?",
               (estagio, cid))
    return {"status": "ok", "id": cid, "novo_estagio": estagio}


@router.get("/crm/clientes/{cid}")
def detalhe_cliente(cid: int):
    cliente = db.query_one("SELECT * FROM clientes WHERE id=?", (cid,))
    if not cliente:
        return {"erro": "Cliente não encontrado"}
    cliente["interacoes"] = db.query(
        "SELECT * FROM interacoes WHERE cliente_id=? ORDER BY criado_em DESC", (cid,))
    cliente["pedidos"] = db.query(
        "SELECT * FROM pedidos WHERE cliente_id=? ORDER BY criado_em DESC", (cid,))
    return cliente


@router.post("/crm/clientes/{cid}/interacao")
def add_interacao(cid: int, tipo: str = Body(...), resumo: str = Body(...),
                  canal: str = Body(""), agente: str = Body("")):
    iid = db.execute(
        "INSERT INTO interacoes (cliente_id,tipo,canal,resumo,agente) VALUES (?,?,?,?,?)",
        (cid, tipo, canal, resumo, agente))
    return {"status": "ok", "id": iid}


@router.get("/crm/funil")
def funil_vendas():
    estagios = ["lead", "contato", "cliente", "recorrente", "inativo"]
    out = []
    for e in estagios:
        rows = db.query("SELECT id,nome,email,total_gasto,ultimo_pedido FROM clientes WHERE estagio=? ORDER BY total_gasto DESC", (e,))
        out.append({"estagio": e, "qtd": len(rows), "clientes": rows})
    return {"funil": out}


# ════════════════════════════════════════════════════════════════
# ESTOQUE / PRODUTOS
# ════════════════════════════════════════════════════════════════
@router.get("/estoque/produtos")
def listar_produtos(status: str = "", alerta: bool = False, limit: int = 200):
    sql = "SELECT * FROM produtos WHERE 1=1"; p = []
    if status:
        sql += " AND status=?"; p.append(status)
    if alerta:
        sql += " AND estoque <= estoque_minimo"
    sql += " ORDER BY estoque ASC LIMIT ?"; p.append(limit)
    return {"produtos": db.query(sql, tuple(p))}


@router.get("/estoque/alertas")
def alertas_estoque():
    baixo = db.query("SELECT * FROM produtos WHERE estoque <= estoque_minimo ORDER BY estoque ASC")
    return {"qtd": len(baixo), "produtos": baixo}


class AjusteEstoque(BaseModel):
    quantidade: int
    tipo: str = "ajuste"   # entrada | saida | ajuste
    motivo: str = ""


@router.post("/estoque/produtos/{pid}/movimentar")
def movimentar_estoque(pid: int, m: AjusteEstoque):
    prod = db.query_one("SELECT * FROM produtos WHERE id=?", (pid,))
    if not prod:
        return {"erro": "Produto não encontrado"}
    delta = m.quantidade if m.tipo == "entrada" else (-m.quantidade if m.tipo == "saida" else m.quantidade - prod["estoque"])
    novo = max(0, prod["estoque"] + delta) if m.tipo != "ajuste" else max(0, m.quantidade)
    db.execute("UPDATE produtos SET estoque=?, atualizado_em=datetime('now','localtime') WHERE id=?", (novo, pid))
    db.execute("INSERT INTO movimentacoes_estoque (produto_id,tipo,quantidade,motivo) VALUES (?,?,?,?)",
               (pid, m.tipo, m.quantidade, m.motivo))
    return {"status": "ok", "estoque_anterior": prod["estoque"], "estoque_atual": novo}


# ════════════════════════════════════════════════════════════════
# PEDIDOS
# ════════════════════════════════════════════════════════════════
@router.get("/pedidos")
def listar_pedidos(status: str = "", limit: int = 100):
    sql = "SELECT * FROM pedidos WHERE 1=1"; p = []
    if status:
        sql += " AND status=?"; p.append(status)
    sql += " ORDER BY criado_em DESC LIMIT ?"; p.append(limit)
    return {"pedidos": db.query(sql, tuple(p))}


@router.get("/pedidos/{pid}")
def detalhe_pedido(pid: int):
    ped = db.query_one("SELECT * FROM pedidos WHERE id=?", (pid,))
    if ped and ped.get("itens_json"):
        try:
            ped["itens"] = json.loads(ped["itens_json"])
        except Exception:
            ped["itens"] = []
    return ped or {"erro": "Pedido não encontrado"}


# ════════════════════════════════════════════════════════════════
# FORNECEDORES / COMPRAS
# ════════════════════════════════════════════════════════════════
class FornecedorIn(BaseModel):
    nome: str
    tipo: str = "nacional"
    contato: str = ""
    email: str = ""
    telefone: str = ""
    prazo_entrega: int = 7
    avaliacao: int = 0
    notas: str = ""


@router.get("/fornecedores")
def listar_fornecedores():
    return {"fornecedores": db.query("SELECT * FROM fornecedores ORDER BY avaliacao DESC, nome")}


@router.post("/fornecedores")
def criar_fornecedor(f: FornecedorIn):
    fid = db.execute(
        """INSERT INTO fornecedores (nome,tipo,contato,email,telefone,prazo_entrega,avaliacao,notas)
           VALUES (?,?,?,?,?,?,?,?)""",
        (f.nome, f.tipo, f.contato, f.email, f.telefone, f.prazo_entrega, f.avaliacao, f.notas))
    return {"status": "ok", "id": fid}


class CompraIn(BaseModel):
    fornecedor_id: int
    fornecedor_nome: str = ""
    descricao: str
    valor_total: float
    status: str = "pedido"
    data_prevista: str = ""


@router.get("/compras")
def listar_compras(status: str = ""):
    sql = "SELECT * FROM compras WHERE 1=1"; p = []
    if status:
        sql += " AND status=?"; p.append(status)
    sql += " ORDER BY data_pedido DESC"
    return {"compras": db.query(sql, tuple(p))}


@router.post("/compras")
def criar_compra(c: CompraIn):
    cid = db.execute(
        """INSERT INTO compras (fornecedor_id,fornecedor_nome,descricao,valor_total,status,data_prevista)
           VALUES (?,?,?,?,?,?)""",
        (c.fornecedor_id, c.fornecedor_nome, c.descricao, c.valor_total, c.status, c.data_prevista))
    # Compra recebida/paga vira despesa no financeiro
    if c.status in ("pago", "recebido"):
        db.execute("INSERT INTO financeiro (tipo,categoria,descricao,valor) VALUES ('despesa','fornecedor',?,?)",
                   (f"Compra: {c.descricao}", c.valor_total))
    return {"status": "ok", "id": cid}


# ════════════════════════════════════════════════════════════════
# FINANCEIRO + MEI
# ════════════════════════════════════════════════════════════════
class LancamentoIn(BaseModel):
    tipo: str           # receita | despesa
    categoria: str = "outro"
    descricao: str = ""
    valor: float
    data: str = ""


@router.get("/financeiro")
def listar_financeiro(tipo: str = "", mes: str = "", limit: int = 200):
    sql = "SELECT * FROM financeiro WHERE 1=1"; p = []
    if tipo:
        sql += " AND tipo=?"; p.append(tipo)
    if mes:
        sql += " AND strftime('%Y-%m',data)=?"; p.append(mes)
    sql += " ORDER BY data DESC LIMIT ?"; p.append(limit)
    return {"lancamentos": db.query(sql, tuple(p))}


@router.post("/financeiro")
def lancar(l: LancamentoIn):
    if l.data:
        lid = db.execute("INSERT INTO financeiro (tipo,categoria,descricao,valor,data) VALUES (?,?,?,?,?)",
                         (l.tipo, l.categoria, l.descricao, l.valor, l.data))
    else:
        lid = db.execute("INSERT INTO financeiro (tipo,categoria,descricao,valor) VALUES (?,?,?,?)",
                         (l.tipo, l.categoria, l.descricao, l.valor))
    return {"status": "ok", "id": lid}


@router.get("/financeiro/mei")
def mei():
    ano = str(datetime.now().year)
    receita = db.query_one(
        "SELECT COALESCE(SUM(valor),0) v FROM financeiro WHERE tipo='receita' AND strftime('%Y',data)=?",
        (ano,))["v"]
    por_mes = db.query(
        """SELECT strftime('%Y-%m',data) mes, SUM(valor) total
           FROM financeiro WHERE tipo='receita' AND strftime('%Y',data)=?
           GROUP BY mes ORDER BY mes""", (ano,))
    return {"ano": ano, **_mei_status(receita), "por_mes": por_mes}


@router.get("/financeiro/dre")
def dre(mes: str = ""):
    """Demonstrativo de resultado simplificado (receita - despesas por categoria)."""
    filtro = "AND strftime('%Y-%m',data)=?" if mes else ""
    p = (mes,) if mes else ()
    receita = db.query_one(f"SELECT COALESCE(SUM(valor),0) v FROM financeiro WHERE tipo='receita' {filtro}", p)["v"]
    despesas = db.query(
        f"SELECT categoria, SUM(valor) total FROM financeiro WHERE tipo='despesa' {filtro} GROUP BY categoria", p)
    total_desp = sum(d["total"] for d in despesas)
    return {
        "periodo": mes or "acumulado",
        "receita_bruta": round(receita, 2),
        "despesas_por_categoria": despesas,
        "despesa_total": round(total_desp, 2),
        "lucro_liquido": round(receita - total_desp, 2),
        "margem": round((receita - total_desp) / receita * 100, 1) if receita else 0,
    }


# ════════════════════════════════════════════════════════════════
# SYNC SHOPIFY (clientes + pedidos + produtos reais)
# ════════════════════════════════════════════════════════════════
@router.post("/sync/shopify")
async def sync_shopify():
    if not _SHOPIFY_DOMAIN or not _SHOPIFY_TOKEN:
        return {"erro": "Shopify não configurado (SHOPIFY_DOMAIN / SHOPIFY_ADMIN_TOKEN)"}
    resultado = {"clientes": 0, "pedidos": 0, "produtos": 0, "receita_lancada": 0.0, "erros": []}
    base = f"https://{_SHOPIFY_DOMAIN}/admin/api/{_API_VER}"
    async with httpx.AsyncClient(timeout=30, headers=_shopify_headers()) as hc:
        # ── PRODUTOS ──
        try:
            r = await hc.get(f"{base}/products.json?limit=250&fields=id,title,variants,status")
            for prod in r.json().get("products", []):
                v = (prod.get("variants") or [{}])[0]
                sku = v.get("sku", "")
                preco = float(v.get("price", 0) or 0)
                estoque = int(v.get("inventory_quantity", 0) or 0)
                cat = "entrada" if preco <= 50 else ("medio" if preco <= 129 else "premium")
                db.execute(
                    """INSERT INTO produtos (shopify_id,titulo,sku,categoria,preco,estoque,status)
                       VALUES (?,?,?,?,?,?,?)
                       ON CONFLICT(shopify_id) DO UPDATE SET
                         titulo=excluded.titulo, preco=excluded.preco, estoque=excluded.estoque,
                         categoria=excluded.categoria, status=excluded.status,
                         atualizado_em=datetime('now','localtime')""",
                    (str(prod["id"]), prod.get("title", ""), sku, cat, preco, estoque, prod.get("status", "active")))
                resultado["produtos"] += 1
        except Exception as e:
            resultado["erros"].append(f"produtos: {e}")

        # ── CLIENTES ──
        try:
            r = await hc.get(f"{base}/customers.json?limit=250")
            for c in r.json().get("customers", []):
                nome = f"{c.get('first_name','')} {c.get('last_name','')}".strip() or c.get("email", "Sem nome")
                gasto = float(c.get("total_spent", 0) or 0)
                nped = int(c.get("orders_count", 0) or 0)
                estagio = "recorrente" if nped > 1 else ("cliente" if nped == 1 else "lead")
                addr = c.get("default_address") or {}
                db.execute(
                    """INSERT INTO clientes (shopify_id,nome,email,telefone,cidade,estado,estagio,origem,total_gasto,qtd_pedidos)
                       VALUES (?,?,?,?,?,?,?,'shopify',?,?)
                       ON CONFLICT(shopify_id) DO UPDATE SET
                         total_gasto=excluded.total_gasto, qtd_pedidos=excluded.qtd_pedidos,
                         estagio=excluded.estagio, atualizado_em=datetime('now','localtime')""",
                    (str(c["id"]), nome, c.get("email", ""), c.get("phone", "") or "",
                     addr.get("city", ""), addr.get("province", ""), estagio, gasto, nped))
                resultado["clientes"] += 1
        except Exception as e:
            resultado["erros"].append(f"clientes: {e}")

        # ── PEDIDOS (e lança receita no financeiro) ──
        try:
            r = await hc.get(f"{base}/orders.json?status=any&limit=250")
            for o in r.json().get("orders", []):
                shop_id = str(o["id"])
                ja_existe = db.query_one("SELECT id FROM pedidos WHERE shopify_id=?", (shop_id,))
                cliente = o.get("customer") or {}
                cli_nome = f"{cliente.get('first_name','')} {cliente.get('last_name','')}".strip()
                total = float(o.get("total_price", 0) or 0)
                itens = [{"titulo": li.get("title"), "qtd": li.get("quantity"), "preco": li.get("price")}
                         for li in o.get("line_items", [])]
                status = "pago" if o.get("financial_status") == "paid" else (o.get("financial_status") or "pendente")
                cli_local = db.query_one("SELECT id FROM clientes WHERE shopify_id=?", (str(cliente.get("id")),)) if cliente.get("id") else None
                db.execute(
                    """INSERT INTO pedidos (shopify_id,numero,cliente_id,cliente_nome,total,subtotal,frete,desconto,status,status_envio,itens_json,criado_em)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(shopify_id) DO UPDATE SET
                         status=excluded.status, status_envio=excluded.status_envio,
                         sincronizado_em=datetime('now','localtime')""",
                    (shop_id, o.get("name", ""), cli_local["id"] if cli_local else None, cli_nome,
                     total, float(o.get("subtotal_price", 0) or 0),
                     float((o.get("total_shipping_price_set", {}).get("shop_money", {}) or {}).get("amount", 0) or 0),
                     float(o.get("total_discounts", 0) or 0),
                     status, o.get("fulfillment_status") or "nao_enviado",
                     json.dumps(itens, ensure_ascii=False), o.get("created_at", "")))
                # lança receita só de pedidos pagos e ainda não registrados
                if not ja_existe and status == "pago":
                    db.execute(
                        "INSERT INTO financeiro (tipo,categoria,descricao,valor,data) VALUES ('receita','venda',?,?,?)",
                        (f"Pedido {o.get('name','')}", total, o.get("created_at", "")[:19].replace("T", " ")))
                    resultado["receita_lancada"] += total
                resultado["pedidos"] += 1
        except Exception as e:
            resultado["erros"].append(f"pedidos: {e}")

    resultado["sincronizado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    return resultado
