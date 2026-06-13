import erp_db as db

print("=== PRODUCTS IN ERP ===")
prods = db.query("SELECT * FROM produtos")
for p in prods:
    print(f"ID: {p['id']} | Shopify ID: {p['shopify_id']} | Title: {p['titulo']} | Price: {p['preco']} | Cost: {p['custo']} | Stock: {p['estoque']} | Supplier ID: {p['fornecedor_id']}")

print("\n=== SUPPLIERS IN ERP ===")
supps = db.query("SELECT * FROM fornecedores")
for s in supps:
    print(f"ID: {s['id']} | Name: {s['nome']} | Type: {s['tipo']} | Rating: {s['avaliacao']} | Delivery Time: {s['prazo_entrega']} days")
