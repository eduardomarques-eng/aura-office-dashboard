# notion_tools.py — Integração Notion API com Aura Decore CRM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import os
import json
import httpx
from datetime import datetime

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")
NOTION_VERSION = "2022-06-28"

def _notion_headers() -> dict:
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }

async def sync_lead_to_notion(lead_data: dict) -> dict:
    """
    Sincroniza um lead do CRM (SQLite) para uma base de dados no Notion.
    lead_data deve conter: nome, telefone, estagio, interesse, dores, objecoes, nivel_engajamento.
    """
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        print("[WARN] Notion API não configurada (.env). Ignorando sincronização Notion.")
        return {"status": "skipped", "reason": "credentials_missing"}
        
    url = "https://api.notion.com/v1/pages"
    
    # Prepara propriedades do Notion
    properties = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": lead_data.get("nome", "Lead Sem Nome")
                    }
                }
            ]
        },
        "Telefone": {
            "rich_text": [
                {
                    "text": {
                        "content": lead_data.get("telefone", "")
                    }
                }
            ]
        },
        "Estágio": {
            "select": {
                "name": lead_data.get("estagio", "frio")
            }
        },
        "Interesse": {
            "rich_text": [
                {
                    "text": {
                        "content": lead_data.get("interesse", "desconhecido")
                    }
                }
            ]
        },
        "Dores": {
            "rich_text": [
                {
                    "text": {
                        "content": lead_data.get("dores", "nenhuma")
                    }
                }
            ]
        },
        "Objeções": {
            "rich_text": [
                {
                    "text": {
                        "content": lead_data.get("objecoes", "nenhuma")
                    }
                }
            ]
        },
        "Engajamento": {
            "select": {
                "name": lead_data.get("nivel_engajamento", "baixo")
            }
        },
        "Sincronizado": {
            "date": {
                "start": datetime.now().isoformat()
            }
        }
    }
    
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties
    }
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=payload, headers=_notion_headers())
            if r.status_code in (200, 201):
                data = r.json()
                print(f"[Notion] Lead sincronizado com sucesso: {data.get('id')}")
                return {"status": "success", "page_id": data.get("id")}
            else:
                print(f"[WARN] Erro Notion API ({r.status_code}): {r.text}")
                return {"status": "error", "code": r.status_code, "detail": r.text}
    except Exception as e:
        print(f"[WARN] Falha na requisição Notion: {e}")
        return {"status": "error", "detail": str(e)}

def sync_lead_to_notion_sync(lead_data: dict) -> dict:
    """
    Sincroniza um lead do CRM (SQLite) para uma base de dados no Notion de forma síncrona.
    """
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        print("[WARN] Notion API não configurada (.env). Ignorando sincronização Notion.")
        return {"status": "skipped", "reason": "credentials_missing"}
        
    url = "https://api.notion.com/v1/pages"
    properties = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": lead_data.get("nome", "Lead Sem Nome")
                    }
                }
            ]
        },
        "Telefone": {
            "rich_text": [
                {
                    "text": {
                        "content": lead_data.get("telefone", "")
                    }
                }
            ]
        },
        "Estágio": {
            "select": {
                "name": lead_data.get("estagio", "frio")
            }
        },
        "Interesse": {
            "rich_text": [
                {
                    "text": {
                        "content": lead_data.get("interesse", "desconhecido")
                    }
                }
            ]
        },
        "Dores": {
            "rich_text": [
                {
                    "text": {
                        "content": lead_data.get("dores", "nenhuma")
                    }
                }
            ]
        },
        "Objeções": {
            "rich_text": [
                {
                    "text": {
                        "content": lead_data.get("objecoes", "nenhuma")
                    }
                }
            ]
        },
        "Engajamento": {
            "select": {
                "name": lead_data.get("nivel_engajamento", "baixo")
            }
        },
        "Sincronizado": {
            "date": {
                "start": datetime.now().isoformat()
            }
        }
    }
    
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties
    }
    
    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(url, json=payload, headers=_notion_headers())
            if r.status_code in (200, 201):
                data = r.json()
                print(f"[Notion] Lead sincronizado com sucesso: {data.get('id')}")
                return {"status": "success", "page_id": data.get("id")}
            else:
                print(f"[WARN] Erro Notion API ({r.status_code}): {r.text}")
                return {"status": "error", "code": r.status_code, "detail": r.text}
    except Exception as e:
        print(f"[WARN] Falha na requisição Notion: {e}")
        return {"status": "error", "detail": str(e)}

from crewai.tools import BaseTool

class NotionSyncLeadTool(BaseTool):
    name: str = "NotionSyncLead"
    description: str = (
        "Sincroniza metadados e informações do lead para o banco de dados do Notion CRM. "
        "Input JSON: {\"nome\": \"Nome\", \"telefone\": \"Telefone\", \"estagio\": \"quente|morno|frio|cliente_ativo\", \"interesse\": \"Interesses\", \"dores\": \"Dores\", \"objecoes\": \"Objeções\", \"nivel_engajamento\": \"alto|medio|baixo\"} "
        "Output: status de sucesso ou erro em JSON."
    )

    def _run(self, input_str: str) -> str:
        try:
            data = json.loads(input_str)
        except Exception:
            return "Erro: Input deve ser um JSON válido."
        res = sync_lead_to_notion_sync(data)
        return json.dumps(res)

notion_sync = NotionSyncLeadTool()
NOTION_TOOLS = [notion_sync]

