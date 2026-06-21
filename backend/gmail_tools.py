# gmail_tools.py — Integração SMTP Gmail para Aura Decore
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "auras.de@gmail.com")
SMTP_PASS = os.getenv("SMTP_PASSWORD", "")  # Senha de app do Gmail do Eduardo

def send_email_smtp(to_email: str, subject: str, body_text: str, attachment_path: str = None) -> dict:
    """
    Envia um e-mail com ou sem anexo usando o SMTP do Gmail.
    """
    if not SMTP_PASS:
        print("[WARN] SMTP_PASSWORD não configurado no .env. Ignorando envio de e-mail.")
        return {"status": "skipped", "reason": "smtp_password_missing"}
        
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
    
    if attachment_path and os.path.exists(attachment_path):
        try:
            filename = os.path.basename(attachment_path)
            with open(attachment_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f"attachment; filename= {filename}",
                )
                msg.attach(part)
        except Exception as file_err:
            print(f"[WARN] Falha ao anexar arquivo {attachment_path}: {file_err}")
            
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()
        print(f"[Gmail] E-mail enviado com sucesso para {to_email}")
        return {"status": "success", "to": to_email}
    except Exception as e:
        print(f"[WARN] Falha ao enviar e-mail via SMTP: {e}")
        return {"status": "error", "detail": str(e)}

import json
from crewai.tools import BaseTool

class GmailSendEmailTool(BaseTool):
    name: str = "GmailSendEmail"
    description: str = (
        "Envia um e-mail com ou sem anexo usando o SMTP do Gmail (auras.de@gmail.com). "
        "Input JSON: {\"to_email\": \"destinatario@email.com\", \"subject\": \"Assunto\", \"body_text\": \"Corpo do e-mail\", \"attachment_path\": \"caminho_anexo_opcional\"} "
        "Output: status de sucesso ou erro em JSON."
    )

    def _run(self, input_str: str) -> str:
        try:
            data = json.loads(input_str)
        except Exception:
            return "Erro: Input deve ser um JSON válido contendo to_email, subject e body_text."
        
        to_email = data.get("to_email")
        subject = data.get("subject")
        body_text = data.get("body_text")
        attachment_path = data.get("attachment_path")
        
        if not to_email or not subject or not body_text:
            return "Erro: to_email, subject e body_text são obrigatórios."
            
        res = send_email_smtp(to_email, subject, body_text, attachment_path)
        return json.dumps(res)

gmail_send = GmailSendEmailTool()
GMAIL_TOOLS = [gmail_send]

