import os
import re

vault_path = r"C:\Users\erick\AURA-decor-vault"
print(f"Scanning Obsidian Vault at {vault_path}...")

token_pattern = re.compile(r"(shpat_[a-zA-Z0-9]{32}|atkn_[a-zA-Z0-9]{64}|shptka_[a-zA-Z0-9]{32})")
domain_pattern = re.compile(r"[a-zA-Z0-9\-]+\.myshopify\.com")

if not os.path.exists(vault_path):
    print("Vault path does not exist.")
else:
    for root, dirs, files in os.walk(vault_path):
        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        
                        # Find tokens
                        tokens = token_pattern.findall(content)
                        domains = domain_pattern.findall(content)
                        
                        if tokens or "shopify" in content.lower():
                            print(f"\nFOUND in {file}:")
                            if tokens:
                                print(f"  Tokens: {tokens}")
                            if domains:
                                print(f"  Domains: {domains}")
                            # Print lines with shopify
                            for line in content.splitlines():
                                if "shopify" in line.lower() or "shpat" in line.lower() or "token" in line.lower():
                                    print(f"    Line: {line.strip()[:100]}")
                except Exception as e:
                    pass

print("\nScan complete.")
