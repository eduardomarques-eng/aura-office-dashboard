import sqlite3
import json
import os
import sys
import uuid

sys.stdout.reconfigure(encoding='utf-8')

db_path = r"C:\Users\erick\.n8n\database.sqlite"
if not os.path.exists(db_path):
    print(f"n8n database not found at {db_path}!")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get existing project ID or use default
cursor.execute("SELECT projectId FROM shared_workflow LIMIT 1;")
row_p = cursor.fetchone()
project_id = row_p[0] if row_p else "XXapTvhXuM8jxt72"

print(f"Using projectId: {project_id}")

def import_workflow(wf_id, filepath):
    if not os.path.exists(filepath):
        print(f"File {filepath} not found. Skipping.")
        return
        
    with open(filepath, "r", encoding="utf-8-sig") as f:
        wf_data = json.load(f)
        
    name = wf_data["name"]
    nodes_str = json.dumps(wf_data["nodes"])
    connections_str = json.dumps(wf_data["connections"])
    settings_str = json.dumps(wf_data.get("settings", {}))
    
    version_id = str(uuid.uuid4())
    
    # Check if workflow exists by ID or name
    cursor.execute("SELECT id FROM workflow_entity WHERE id = ? OR name = ?", (str(wf_id), name))
    row = cursor.fetchone()
    
    if row:
        target_id = row[0]
        cursor.execute(
            "UPDATE workflow_entity SET name = ?, nodes = ?, connections = ?, settings = ?, active = 1, versionId = ?, activeVersionId = ?, updatedAt = datetime('now') WHERE id = ?",
            (name, nodes_str, connections_str, settings_str, version_id, version_id, target_id)
        )
        print(f"✓ Updated: '{name}' (ID: {target_id})")
        workflow_id_to_use = target_id
    else:
        cursor.execute(
            "INSERT INTO workflow_entity (id, name, nodes, connections, settings, active, versionId, activeVersionId, meta, isArchived, versionCounter, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?, 1, ?, ?, '{}', 0, 1, datetime('now'), datetime('now'))",
            (str(wf_id), name, nodes_str, connections_str, settings_str, version_id, version_id)
        )
        print(f"✓ Created: '{name}' (ID: {wf_id})")
        workflow_id_to_use = str(wf_id)
 
    # Clean up old history for this workflow
    cursor.execute("DELETE FROM workflow_history WHERE workflowId = ?", (workflow_id_to_use,))
    
    # Insert active version into history
    cursor.execute(
        "INSERT INTO workflow_history (versionId, workflowId, authors, createdAt, updatedAt, nodes, connections, name, autosaved, description) VALUES (?, ?, 'import', datetime('now'), datetime('now'), ?, ?, ?, 0, '')",
        (version_id, workflow_id_to_use, nodes_str, connections_str, name)
    )

    # Ensure there is an owner record in shared_workflow
    cursor.execute("SELECT workflowId FROM shared_workflow WHERE workflowId = ?", (workflow_id_to_use,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO shared_workflow (workflowId, projectId, role, createdAt, updatedAt) VALUES (?, ?, 'workflow:owner', datetime('now'), datetime('now'))",
            (workflow_id_to_use, project_id)
        )

# Mapping of ID to file name (mapping our workflows explicitly)
workflows_to_import = {
    "1": "01-novo-pedido-shopify.json",
    "2": "02-recuperacao-carrinho.json",
    "3": "03-whatsapp-lena.json",
    "4": "04-rastreamento-automatico.json", # New fulfillment tracking workflow
    "24": "WF24-neuro-nurturing.json",
    "25": "WF25-promo-blast.json",
    "26": "WF26-neuro-copy-inbound.json",
    "27": "WF27-whatsapp-remarketing-followup.json",
    "28": "WF28-canva-creative-dispatcher.json",
}

HERE = r"C:\Users\erick\aura-office-dashboard\n8n-workflows"
for wf_id, filename in workflows_to_import.items():
    filepath = os.path.join(HERE, filename)
    import_workflow(wf_id, filepath)

conn.commit()
conn.close()
print("All workflows successfully synchronized and activated in the n8n database!")
