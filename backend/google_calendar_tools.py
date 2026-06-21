# -*- coding: utf-8 -*-
"""
Google Calendar Tools — Integração Google Calendar para os agentes.
Permite listar compromissos e agendar consultas ou reuniões.
"""
from __future__ import annotations
import os
import json
import httpx
from datetime import datetime
from crewai.tools import BaseTool

GOOGLE_CALENDAR_CLIENT_ID = os.getenv("GOOGLE_CALENDAR_CLIENT_ID", "")
GOOGLE_CALENDAR_CLIENT_SECRET = os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET", "")
GOOGLE_CALENDAR_REFRESH_TOKEN = os.getenv("GOOGLE_CALENDAR_REFRESH_TOKEN", "")
GOOGLE_CALENDAR_ACCESS_TOKEN = os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN", "")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

def _get_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def _refresh_access_token() -> str:
    """Obtém ou renova o access token do Google OAuth2 de forma síncrona."""
    if GOOGLE_CALENDAR_ACCESS_TOKEN:
        return GOOGLE_CALENDAR_ACCESS_TOKEN
    
    if GOOGLE_CALENDAR_REFRESH_TOKEN and GOOGLE_CALENDAR_CLIENT_ID and GOOGLE_CALENDAR_CLIENT_SECRET:
        url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": GOOGLE_CALENDAR_CLIENT_ID,
            "client_secret": GOOGLE_CALENDAR_CLIENT_SECRET,
            "refresh_token": GOOGLE_CALENDAR_REFRESH_TOKEN,
            "grant_type": "refresh_token"
        }
        try:
            with httpx.Client(timeout=10) as client:
                r = client.post(url, data=payload)
                if r.status_code == 200:
                    return r.json().get("access_token", "")
        except Exception as e:
            print(f"[WARN] Erro ao renovar token Google Calendar: {e}")
    return ""

class GoogleCalendarListEventsTool(BaseTool):
    name: str = "GoogleCalendarListEvents"
    description: str = (
        "Lista os próximos eventos da agenda do Google Calendar. "
        "Input opcional: número máximo de resultados (default 10). "
        "Output: lista de eventos ou aviso de falta de credenciais."
    )

    def _run(self, max_results_str: str = "10") -> str:
        token = _refresh_access_token()
        if not token:
            return (
                "Google Calendar não configurado no .env. "
                "Para ativar, configure GOOGLE_CALENDAR_REFRESH_TOKEN, "
                "GOOGLE_CALENDAR_CLIENT_ID e GOOGLE_CALENDAR_CLIENT_SECRET."
            )
            
        try:
            max_results = int(max_results_str)
        except Exception:
            max_results = 10
            
        url = f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events"
        params = {
            "maxResults": max_results,
            "timeMin": datetime.utcnow().isoformat() + "Z",
            "singleEvents": "true",
            "orderBy": "startTime"
        }
        try:
            with httpx.Client(timeout=15) as client:
                r = client.get(url, headers=_get_headers(token), params=params)
                if r.status_code == 200:
                    events = r.json().get("items", [])
                    if not events:
                        return "Nenhum compromisso encontrado na agenda."
                    lines = ["Agenda — Próximos Compromissos:"]
                    for ev in events:
                        start = ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date", ""))
                        summary = ev.get("summary", "Sem título")
                        lines.append(f"- [{start}] {summary}")
                    return "\n".join(lines)
                else:
                    return f"Erro Google Calendar API ({r.status_code}): {r.text}"
        except Exception as e:
            return f"Erro ao acessar Google Calendar: {e}"

class GoogleCalendarCreateEventTool(BaseTool):
    name: str = "GoogleCalendarCreateEvent"
    description: str = (
        "Agenda um novo evento no Google Calendar. "
        "Input JSON: {\"summary\": \"Título\", \"description\": \"Descrição\", \"start_time\": \"2026-06-20T10:00:00-03:00\", \"end_time\": \"2026-06-20T11:00:00-03:00\", \"attendee_email\": \"email@cliente.com\"} "
        "Output: link do evento agendado ou erro."
    )

    def _run(self, input_str: str) -> str:
        token = _refresh_access_token()
        if not token:
            return (
                "Google Calendar não configurado no .env. "
                "Para ativar, configure GOOGLE_CALENDAR_REFRESH_TOKEN, "
                "GOOGLE_CALENDAR_CLIENT_ID e GOOGLE_CALENDAR_CLIENT_SECRET."
            )
            
        try:
            data = json.loads(input_str)
        except Exception:
            return "Erro: Input deve ser um JSON válido contendo summary, start_time, end_time."
            
        summary = data.get("summary", "Consulta Aura Decore")
        description = data.get("description", "Atendimento consultivo personalizado")
        start_time = data.get("start_time", "")
        end_time = data.get("end_time", "")
        attendee_email = data.get("attendee_email")
        
        if not start_time or not end_time:
            return "Erro: start_time e end_time são obrigatórios no formato ISO (ex: 2026-06-20T10:00:00-03:00)."
            
        url = f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events"
        event = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time},
        }
        if attendee_email:
            event["attendees"] = [{"email": attendee_email}]
            
        try:
            with httpx.Client(timeout=15) as client:
                r = client.post(url, json=event, headers=_get_headers(token))
                if r.status_code in (200, 201):
                    res_data = r.json()
                    return f"Evento agendado com sucesso! Link: {res_data.get('htmlLink')}"
                else:
                    return f"Erro Google Calendar API ({r.status_code}): {r.text}"
        except Exception as e:
            return f"Erro ao criar evento: {e}"

# Instâncias prontas para importar
calendar_list = GoogleCalendarListEventsTool()
calendar_create = GoogleCalendarCreateEventTool()
CALENDAR_TOOLS = [calendar_list, calendar_create]
