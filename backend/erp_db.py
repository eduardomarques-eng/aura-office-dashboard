"""
ERP/CRM Aura Decore — Camada de dados (SQLite)
================================================
Banco local persistente para os módulos:
  • CRM         — clientes, leads, funil de vendas, interações
  • Pedidos     — pedidos sincronizados do Shopify + itens
  • Estoque     — produtos, níveis de inventário, movimentações
  • Financeiro  — receitas, despesas, monitor MEI
  • Fornecedores— cadastro, pedidos de compra, custos

SQLite escolhido por: zero-config, arquivo único, transacional,
suficiente para o volume de um MEI. Migração para Postgres/Supabase
é trivial depois (mesmo SQL ANSI).
"""
import sqlite3
import pathlib
import threading
from datetime import datetime
from contextlib import contextmanager

_DB_PATH = pathlib.Path(__file__).parent / "aura_erp.db"
_LOCK = threading.Lock()


@contextmanager
def get_conn():
    """Conexão thread-safe com row_factory dict-like."""
    conn = sqlite3.connect(str(_DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def query(sql: str, params: tuple = ()) -> list[dict]:
    with _LOCK, get_conn() as conn:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()) -> int:
    """Executa INSERT/UPDATE/DELETE. Retorna lastrowid (ou rowcount em updates)."""
    with _LOCK, get_conn() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid or cur.rowcount


def execute_many(sql: str, seq: list[tuple]) -> int:
    with _LOCK, get_conn() as conn:
        cur = conn.executemany(sql, seq)
        return cur.rowcount


SCHEMA = """
-- ════════════════════════ CRM ════════════════════════
CREATE TABLE IF NOT EXISTS clientes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    shopify_id      TEXT UNIQUE,
    nome            TEXT NOT NULL,
    email           TEXT,
    telefone        TEXT,
    cidade          TEXT,
    estado          TEXT,
    estagio         TEXT DEFAULT 'lead',      -- lead | contato | cliente | recorrente | inativo
    origem          TEXT DEFAULT 'manual',    -- shopify | instagram | indicacao | manual
    tags            TEXT DEFAULT '',          -- csv
    total_gasto     REAL DEFAULT 0,
    qtd_pedidos     INTEGER DEFAULT 0,
    ultimo_pedido   TEXT,
    aceita_mkt      INTEGER DEFAULT 1,
    notas           TEXT DEFAULT '',
    interesse       TEXT,
    dores           TEXT,
    produtos_visualizados TEXT,
    objecoes        TEXT,
    nivel_engajamento TEXT,
    criado_em       TEXT DEFAULT (datetime('now','localtime')),
    atualizado_em   TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS interacoes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id  INTEGER REFERENCES clientes(id) ON DELETE CASCADE,
    tipo        TEXT,        -- nota | email | whatsapp | dm | ligacao | venda
    canal       TEXT,
    resumo      TEXT,
    agente      TEXT,        -- qual agente IA registrou (LENA, ZARA...)
    criado_em   TEXT DEFAULT (datetime('now','localtime'))
);

-- ════════════════════════ ESTOQUE / PRODUTOS ════════════════════════
CREATE TABLE IF NOT EXISTS produtos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    shopify_id      TEXT UNIQUE,
    titulo          TEXT NOT NULL,
    sku             TEXT,
    categoria       TEXT,                     -- entrada | medio | premium
    preco           REAL DEFAULT 0,
    custo           REAL DEFAULT 0,           -- custo do fornecedor
    estoque         INTEGER DEFAULT 0,
    estoque_minimo  INTEGER DEFAULT 5,
    fornecedor_id   INTEGER REFERENCES fornecedores(id),
    status          TEXT DEFAULT 'ativo',
    atualizado_em   TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id  INTEGER REFERENCES produtos(id) ON DELETE CASCADE,
    tipo        TEXT,        -- entrada | saida | ajuste | venda
    quantidade  INTEGER,
    motivo      TEXT,
    criado_em   TEXT DEFAULT (datetime('now','localtime'))
);

-- ════════════════════════ PEDIDOS ════════════════════════
CREATE TABLE IF NOT EXISTS pedidos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    shopify_id      TEXT UNIQUE,
    numero          TEXT,
    cliente_id      INTEGER REFERENCES clientes(id),
    cliente_nome    TEXT,
    total           REAL DEFAULT 0,
    subtotal        REAL DEFAULT 0,
    frete           REAL DEFAULT 0,
    desconto        REAL DEFAULT 0,
    status          TEXT,        -- pago | pendente | enviado | entregue | cancelado
    status_envio    TEXT,
    itens_json      TEXT,        -- snapshot dos itens
    criado_em       TEXT,
    sincronizado_em TEXT DEFAULT (datetime('now','localtime'))
);

-- ════════════════════════ FORNECEDORES / COMPRAS ════════════════════════
CREATE TABLE IF NOT EXISTS fornecedores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT NOT NULL,
    tipo            TEXT,        -- nacional | internacional | dropshipping
    contato         TEXT,
    email           TEXT,
    telefone        TEXT,
    prazo_entrega   INTEGER,     -- dias
    avaliacao       INTEGER DEFAULT 0,  -- 0-5
    notas           TEXT DEFAULT '',
    criado_em       TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS compras (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fornecedor_id   INTEGER REFERENCES fornecedores(id),
    fornecedor_nome TEXT,
    descricao       TEXT,
    valor_total     REAL DEFAULT 0,
    status          TEXT DEFAULT 'pedido',   -- pedido | pago | recebido | cancelado
    data_pedido     TEXT DEFAULT (datetime('now','localtime')),
    data_prevista   TEXT,
    criado_em       TEXT DEFAULT (datetime('now','localtime'))
);

-- ════════════════════════ FINANCEIRO ════════════════════════
CREATE TABLE IF NOT EXISTS financeiro (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo        TEXT NOT NULL,   -- receita | despesa
    categoria   TEXT,            -- venda | frete | fornecedor | marketing | taxa | das_mei | outro
    descricao   TEXT,
    valor       REAL NOT NULL,
    pedido_id   INTEGER REFERENCES pedidos(id),
    data        TEXT DEFAULT (datetime('now','localtime')),
    criado_em   TEXT DEFAULT (datetime('now','localtime'))
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_clientes_estagio ON clientes(estagio);
CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos(status);
CREATE INDEX IF NOT EXISTS idx_produtos_status ON produtos(status);
CREATE INDEX IF NOT EXISTS idx_financeiro_tipo ON financeiro(tipo);
CREATE INDEX IF NOT EXISTS idx_financeiro_data ON financeiro(data);
"""


def init_db():
    """Cria todas as tabelas se não existirem. Idempotente."""
    with _LOCK, get_conn() as conn:
        conn.executescript(SCHEMA)
    return {"status": "ok", "db": str(_DB_PATH), "initialized_at": datetime.now().isoformat()}


if __name__ == "__main__":
    print(init_db())
