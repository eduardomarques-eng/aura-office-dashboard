import erp_db as db

print("=== STARTING PRODUCT-SUPPLIER MAPPING ===")

# Define rules for mapping: (keyword list, supplier_id)
rules = [
    # 4: AliExpress - Wabi-Sabi Ceramic Store (dropshipping)
    (["vaso", "cerâmica", "potes", "prato", "copo", "xícara", "porta-joias"], 4),
    # 6: AliExpress - Halo Lighting Co., Ltd. (dropshipping)
    (["luminária", "abajur", "candeeiro", "luz led"], 6),
    # 5: Fornecedor Nacional - Estofados Premium SC (nacional)
    (["poltrona", "almofada", "manta", "tricô", "capa", "tapete", "juta", "toalha"], 5),
    # 3: Fornecedor Nacional – Botânicos Secos (nacional)
    (["pampas", "pampa", "eucalipto", "algodão", "ramos", "plantas secas", "flores secas", "always-viva"], 3),
    # 2: Importacao Dropshipping – Ceramica/Decor (dropshipping)
    (["difusor", "diffuser", "incenso", "incensário", "porta-incenso", "sachê", "palo santo"], 2),
    # 7: Fornecedor Nacional - Espelhos & Molduras SP (nacional)
    (["espelho"], 7),
    # 1: Fornecedor Nacional – Artesanato MG (nacional)
    (["suporte", "cesta", "porta-objetos", "bandeja", "caixa", "bambu", "madeira", "mármore", "kit ritual", "kit zen", "pedra", "pedras", "macramê"], 1)
]

# Fetch all products
prods = db.query("SELECT id, titulo, fornecedor_id FROM produtos")
updated_count = 0

for p in prods:
    title_lower = p["titulo"].lower()
    matched_supplier = None
    
    for keywords, supplier_id in rules:
        if any(kw in title_lower for kw in keywords):
            matched_supplier = supplier_id
            break
            
    if matched_supplier and p["fornecedor_id"] != matched_supplier:
        db.execute("UPDATE produtos SET fornecedor_id = ? WHERE id = ?", (matched_supplier, p["id"]))
        print(f"Linked: '{p['titulo']}' -> Supplier ID {matched_supplier}")
        updated_count += 1

print(f"\n=== MAPPING COMPLETE. Updated {updated_count} products ===")
