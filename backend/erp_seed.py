"""
ERP seed — popula produtos reais da Aura Decore (snapshot Shopify 2026-05-30).
Idempotente: usa shopify_id como chave única (UPSERT).
Usado enquanto o token Admin REST do .env não está válido; quando estiver,
o endpoint /erp/sync/shopify mantém tudo atualizado automaticamente.
"""
import erp_db as db

# (shopify_id, titulo, sku, preco, estoque)
PRODUTOS = [
    ("7785846440041", "Vaso Cerâmica Wabi — Bege Natural | Decor Japandi", "AURA-VAS-001-BG-M", 89.90, 0),
    ("7785846505577", "Vela Âmbar Natural — Cera de Coco 100% Pura", "AURA-VEL-001-AB", 64.90, 0),
    ("7785846571113", "Almofada Linho Natural — Minimalista Japandi", "AURA-ALM-001-BA-45", 79.90, 0),
    ("7785846603881", "Pampa Seco Premium — Natural & Branco | Decor Boho Japandi", "AURA-PAM-001-BN-1", 47.90, 0),
    ("7785846669417", "Diffuser Premium — Cedro & Sândalo | 200ml", "AURA-DIF-001-CS", 129.90, 0),
    ("7786418045033", "Vaso de Cerâmica Minimalista — Branco", "AURA-VCM-007-PEQ", 129.90, 0),
    ("7786418110569", "Vaso de Cerâmica Artesanal — Terracota", "AURA-VCT-008-PEQ", 139.90, 0),
    ("7786418143337", "Vela Aromática Natural — Âmbar & Sândalo", "AURA-VAS-009-AB", 89.90, 0),
    ("7786418176105", "Almofada de Linho Natural — 45x45cm", "AURA-ALN-010-OW", 119.90, 0),
    ("7786418208873", "Pampas Naturais Secos — Buquê Decorativo", "AURA-PAM-011-NA", 79.90, 0),
    ("7786418241641", "Diffuser de Ambiente — Varetas Aromáticas", "AURA-DIF-012-BCV", 109.90, 0),
    ("7786418274409", "Bandeja Minimalista de Madeira Natural", "AURA-BAN-013-NA", 99.90, 0),
    ("7786418307177", "Vaso de Cerâmica Fosco — Bege Areia", "AURA-VCF-014-PEQ", 134.90, 0),
    ("7786642440297", "Vaso de Cerâmica Japandi", "AURA-VCJ-001-BRW", 129.90, 0),
    ("7786642473065", "Vela Aromática Natural — Coleção Aura", "AURA-VAN-002-AMB", 89.90, 0),
    ("7786642538601", "Almofada de Linho Natural 45x45", "AURA-ALN-003-CRU", 159.90, 0),
    ("7786642636905", "Arranjo de Pampas & Plantas Secas", "AURA-PPS-004-MED", 79.90, 0),
    ("7786642702441", "Diffuser de Varetas — Blend Exclusivo 200ml", "AURA-DVR-005-SAN", 119.90, 0),
    ("7786642800745", "Bandeja Minimalista em Madeira de Acácia", "AURA-BMA-006-PEQ", 89.90, 50),
    ("7792646258793", "Candeeiro de Bambu — Velas de Cera de Coco", "AURA-CAN-001-BB", 95.00, 50),
    ("7792646291561", "Kit de Jardinagem de Ervas Aromáticas", "AURA-KIT-001-ERV", 85.00, 50),
    ("7792661168233", "Painel de Madeira com Moss Preservado e Luz LED", "AURA-PNL-001-MOSS", 125.00, 50),
    ("7792661299305", "Conjunto de 4 Potes de Terracota para Plantas", "AURA-POT-001-TERRA", 68.00, 50),
    ("7795242270825", "Vaso Cerâmica Wabi-Sabi — Textura Natural", "AD-VASO-WS-001", 129.90, 50),
    ("7795242303593", "Bandeja de Bambu Zen — Organização com Alma", "AD-BAND-ZEN-P", 79.90, 50),
    ("7795242401897", "Arranjo de Pampas e Trigo Seco — Composição Botânica", "AD-BOT-PAMP-N", 89.90, 50),
    ("7795242500201", "Difusor de Ambiente Aura — Bambu & Aromas Naturais", "AD-DIF-AMB-001", 119.90, 50),
    ("7795242598505", "Porta-Objetos Madeira Clara — Minimalismo Funcional", "AD-PORT-MAD-N", 94.90, 0),
    ("7795259015273", "Vaso Cerâmica Oval Minimalista", "", 149.00, 50),
    ("7795259080809", "Vela Artesanal de Soja — Bambu & Cedro", "", 89.00, 50),
    ("7795259146345", "Eucalipto Preservado — Buquê Seco Natural", "", 79.00, 50),
    ("7795259179113", "Suporte de Livros em Madeira Natural — Minimalista", "", 129.00, 50),
    ("7795259211881", "Difusor de Varas — Lavanda & Musk Branco", "", 109.00, 50),
    ("7795259277417", "Incensário de Cerâmica — Ripple", "", 69.00, 50),
    ("7795259310185", "Cesta de Rattan Organizadora — Oval", "", 119.00, 0),
    ("7795259342953", "Vela Pilar de Cera Natural — Tom Argila", "", 59.00, 50),
    ("7795259408489", "Porta-Incenso em Bambu — Natural", "", 49.00, 50),
    ("7795259441257", "Arranjo de Ramos de Algodão Seco", "", 89.00, 50),
    ("7796713750633", "Kit de Incenso Japonês — 20 Varetas Artesanais", "AD-INC-KIT-001", 29.90, 50),
    ("7796713783401", "Pedras Decorativas Suiseki — Trio Natural", "AD-PED-SUI-001", 24.90, 50),
    ("7796713816169", "Sachê Aromático de Linho — Lavanda & Cedro", "AD-SAC-LAV-001", 19.90, 50),
    ("7796713848937", "Palo Santo Natural — Pack com 3 Palitos", "AD-PAL-NAT-001", 24.90, 50),
    ("7796713881705", "Mini Vaso Cerâmica Pocket — Wabi-Sabi", "AD-MINI-VAS-001", 39.90, 50),
    ("7796713914473", "Marcadores de Página em Bambu — Set 3 Peças", "AD-MAR-BAM-001", 22.90, 50),
    ("7796713947241", "Porta-Incenso Minimal em Madeira — Plano", "AD-POR-INC-001", 29.90, 50),
    ("7796713980009", "Mini Kit Zen — Starter Aura Decore", "AD-KIT-ZEN-001", 49.90, 50),
    ("7797722218601", "Sachê de Ervas Brasileiras — Sakura", "AD-SAC-BR-LAV", 29.90, 50),
    ("7797722251369", "Vela de Cera de Abelha Artesanal — Hana", "AD-VEL-AB-P", 24.90, 50),
    ("7797722284137", "Pedra Sabão Decorativa — Sabi", "AD-PED-SAB-001", 24.90, 50),
    ("7797722316905", "Pedra Semipreciosa Mini — Kit Trio MG", "AD-PED-SEMI-001", 34.90, 50),
    ("7797722349673", "Macramê Decorativo Mini — Nó", "AD-MAC-MIN-001", 19.90, 50),
    ("7797722382441", "Flores Secas Always-Viva — Buquê Brasileiro", "AD-BOT-ALW-001", 22.90, 50),
    ("7797722415209", "Algodão Crudo Decorativo — Kumo", "AD-BOT-ALG-001", 19.90, 50),
    ("7797722447977", "Kit Zen Nacional — Presente Brasileiro", "AD-KIT-BR-001", 59.90, 50),
]

# Fornecedores iniciais (estrutura base — Eduardo completa contatos depois)
FORNECEDORES = [
    ("Fornecedor Nacional — Artesanato MG", "nacional", "", "", "", 7, 4, "Velas, pedra sabão, sachês nacionais"),
    ("Importação Dropshipping — Cerâmica/Decor", "dropshipping", "", "", "", 20, 3, "Vasos, difusores, almofadas premium"),
    ("Fornecedor Nacional — Botânicos Secos", "nacional", "", "", "", 5, 4, "Pampas, eucalipto, algodão, flores secas"),
]


def seed():
    for sid, titulo, sku, preco, estoque in PRODUTOS:
        cat = "entrada" if preco <= 50 else ("medio" if preco <= 129 else "premium")
        # custo estimado: dropshipping ~40% do preço (margem ~60%); usado só como baseline editável
        custo = round(preco * 0.40, 2)
        db.execute(
            """INSERT INTO produtos (shopify_id,titulo,sku,categoria,preco,custo,estoque,status)
               VALUES (?,?,?,?,?,?,?,'ativo')
               ON CONFLICT(shopify_id) DO UPDATE SET
                 titulo=excluded.titulo, sku=excluded.sku, categoria=excluded.categoria,
                 preco=excluded.preco, estoque=excluded.estoque,
                 atualizado_em=datetime('now','localtime')""",
            (sid, titulo, sku, cat, preco, custo, estoque))

    for nome, tipo, contato, email, tel, prazo, aval, notas in FORNECEDORES:
        existe = db.query_one("SELECT id FROM fornecedores WHERE nome=?", (nome,))
        if not existe:
            db.execute(
                """INSERT INTO fornecedores (nome,tipo,contato,email,telefone,prazo_entrega,avaliacao,notas)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (nome, tipo, contato, email, tel, prazo, aval, notas))

    total_p = db.query_one("SELECT COUNT(*) c FROM produtos")["c"]
    total_f = db.query_one("SELECT COUNT(*) c FROM fornecedores")["c"]
    return {"produtos": total_p, "fornecedores": total_f}


if __name__ == "__main__":
    db.init_db()
    print(seed())
