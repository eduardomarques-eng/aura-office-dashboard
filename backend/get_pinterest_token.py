# -*- coding: utf-8 -*-
"""
get_pinterest_token.py — OAuth 2.0 Pinterest API v5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Servidor local que completa o flow OAuth e salva PINTEREST_ACCESS_TOKEN no .env

Pré-requisito:
  1. Criar app em developers.pinterest.com/apps/connect/
  2. Copiar App ID e App Secret
  3. Adicionar Redirect URI: http://localhost:8766/callback
  4. Executar: python get_pinterest_token.py --app-id SEU_ID --app-secret SEU_SECRET
     OU: setar PINTEREST_APP_ID e PINTEREST_APP_SECRET no .env e rodar sem args

Escopos gerados: pins:read, pins:write, boards:read, boards:write, user_accounts:read
"""
import os, sys, json, time, pathlib, threading, urllib.parse, base64, hashlib, secrets, argparse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import httpx

ENV_PATH = pathlib.Path(__file__).parent / ".env"
PORT = 8766
SCOPES = "pins:read,pins:write,boards:read,boards:write,user_accounts:read"
REDIRECT_URI = f"http://localhost:{PORT}/callback"


def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def save_token_to_env(token: str, refresh_token: str = ""):
    text = ENV_PATH.read_text(encoding="utf-8")
    lines = []
    found_access = found_refresh = False
    for line in text.splitlines():
        if line.startswith("PINTEREST_ACCESS_TOKEN="):
            lines.append(f"PINTEREST_ACCESS_TOKEN={token}")
            found_access = True
        elif line.startswith("PINTEREST_REFRESH_TOKEN="):
            lines.append(f"PINTEREST_REFRESH_TOKEN={refresh_token}")
            found_refresh = True
        else:
            lines.append(line)
    if not found_access:
        lines.append(f"PINTEREST_ACCESS_TOKEN={token}")
    if not found_refresh and refresh_token:
        lines.append(f"PINTEREST_REFRESH_TOKEN={refresh_token}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n✅ PINTEREST_ACCESS_TOKEN salvo no .env!")


state_store = {"state": "", "verifier": "", "token": None, "done": False}


def generate_pkce():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


class PinterestOAuthHandler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        env = load_env()
        app_id = env.get("PINTEREST_APP_ID", "")
        app_secret = env.get("PINTEREST_APP_SECRET", "")

        if parsed.path in ("/", ""):
            if not app_id:
                html = self._missing_credentials_page()
            else:
                html = self._start_page(app_id)
            self._send(html)

        elif parsed.path == "/start":
            verifier, challenge = generate_pkce()
            state = secrets.token_urlsafe(16)
            state_store["state"] = state
            state_store["verifier"] = verifier

            auth_url = (
                f"https://www.pinterest.com/oauth/"
                f"?client_id={app_id}"
                f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
                f"&response_type=code"
                f"&scope={SCOPES}"
                f"&state={state}"
                f"&code_challenge={challenge}"
                f"&code_challenge_method=S256"
            )
            self._redirect(auth_url)

        elif parsed.path == "/callback":
            code = params.get("code", "")
            state_recv = params.get("state", "")

            if params.get("error"):
                self._send(f"<h2>❌ Erro: {params.get('error_description', params.get('error'))}</h2>")
                return

            if state_recv != state_store["state"]:
                self._send("<h2>❌ State inválido — possível CSRF</h2>")
                return

            if not code:
                self._send("<h2>❌ Código de autorização não recebido</h2>")
                return

            # Troca code por access_token
            try:
                creds = base64.b64encode(f"{app_id}:{app_secret}".encode()).decode()
                r = httpx.post(
                    "https://api.pinterest.com/v5/oauth/token",
                    headers={
                        "Authorization": f"Basic {creds}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": REDIRECT_URI,
                        "code_verifier": state_store["verifier"],
                    },
                    timeout=20,
                )
                data = r.json()
                access_token = data.get("access_token", "")
                refresh_token = data.get("refresh_token", "")
                expires_in = data.get("expires_in", 0)

                if not access_token:
                    self._send(f"<h2>❌ Erro ao obter token: {data}</h2>")
                    return

                save_token_to_env(access_token, refresh_token)
                state_store["token"] = access_token
                state_store["done"] = True

                html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>✅ Pinterest Token</title>
                <style>body{{font-family:sans-serif;max-width:500px;margin:60px auto;background:#F5F0EB}}
                .box{{background:#fff;border-radius:12px;padding:32px;text-align:center}}
                h2{{color:#2e7d32}}code{{background:#f5f5f5;padding:4px 8px;border-radius:4px}}</style></head>
                <body><div class="box">
                <h2>✅ Pinterest Access Token salvo!</h2>
                <p>Token: <code>{access_token[:20]}...{access_token[-8:]}</code></p>
                <p>Expira em: {int(expires_in/3600)}h</p>
                <p>PINTEREST_ACCESS_TOKEN atualizado no .env e Railway.</p>
                <p>Pode fechar esta janela.</p>
                </div></body></html>"""
                self._send(html)

                # Atualiza Railway automaticamente
                threading.Thread(target=self._update_railway, args=(access_token, refresh_token), daemon=True).start()

            except Exception as e:
                self._send(f"<h2>❌ Erro: {e}</h2>")

        elif parsed.path == "/save":
            token = params.get("token", "").strip()
            if token and len(token) > 20:
                save_token_to_env(token)
                state_store["token"] = token
                state_store["done"] = True
                self._send(f"<h2>✅ Token salvo manualmente!</h2><p>{token[:20]}...</p>")
            else:
                self._send("<h2>Token inválido</h2>")
        else:
            self._send("<h2>404</h2>", 404)

    def _update_railway(self, access_token, refresh_token):
        try:
            import subprocess
            subprocess.run(["railway", "service", "web"], cwd=str(ENV_PATH.parent.parent), capture_output=True)
            subprocess.run(["railway", "variables", "set", f"PINTEREST_ACCESS_TOKEN={access_token}"],
                           cwd=str(ENV_PATH.parent.parent), capture_output=True)
            if refresh_token:
                subprocess.run(["railway", "variables", "set", f"PINTEREST_REFRESH_TOKEN={refresh_token}"],
                               cwd=str(ENV_PATH.parent.parent), capture_output=True)
            print("[Railway] PINTEREST_ACCESS_TOKEN atualizado no Railway.")
        except Exception as e:
            print(f"[Railway] Erro ao atualizar: {e}")

    def _missing_credentials_page(self):
        return """<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
        <title>Pinterest OAuth — Sem credenciais</title>
        <style>body{font-family:sans-serif;max-width:600px;margin:60px auto;background:#F5F0EB}
        .box{background:#fff;border-radius:12px;padding:32px}h1{color:#B8793A}
        input{width:100%;padding:10px;border:2px solid #ddd;border-radius:6px;box-sizing:border-box;margin:6px 0}
        button{background:#B8793A;color:#fff;padding:12px 24px;border:none;border-radius:8px;cursor:pointer;margin-top:8px}
        a{color:#E60023}</style></head><body><div class="box">
        <h1>📌 Pinterest OAuth — Aura Decore</h1>
        <p>PINTEREST_APP_ID e PINTEREST_APP_SECRET não encontrados no .env</p>
        <p><strong>Passo 1:</strong> Crie o app em
        <a href="https://developers.pinterest.com/apps/connect/" target="_blank">developers.pinterest.com/apps/connect/</a></p>
        <p><strong>Passo 2:</strong> Copie o App ID e App Secret da página do app</p>
        <p><strong>Passo 3:</strong> Cole aqui para gerar o token:</p>
        <form action="/set-creds" method="get">
        <input name="app_id" placeholder="App ID (ex: 1234567)">
        <input name="app_secret" placeholder="App Secret (ex: abcdef123...)">
        <button type="submit">Iniciar OAuth →</button>
        </form>
        <hr>
        <p>Ou cole o access_token diretamente (se já tiver):</p>
        <form action="/save" method="get">
        <input name="token" placeholder="Token Pinterest...">
        <button type="submit">Salvar token →</button>
        </form>
        </div></body></html>"""

    def _start_page(self, app_id):
        return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
        <title>Pinterest OAuth — Aura Decore</title>
        <style>body{{font-family:sans-serif;max-width:600px;margin:60px auto;background:#F5F0EB}}
        .box{{background:#fff;border-radius:12px;padding:32px}}h1{{color:#E60023}}
        a.btn{{display:inline-block;background:#E60023;color:#fff;padding:14px 28px;
        border-radius:8px;text-decoration:none;font-weight:bold;margin-top:16px}}
        .note{{background:#fff8e6;border-left:4px solid #B8793A;padding:12px;margin-top:16px}}
        </style></head><body><div class="box">
        <h1>📌 Pinterest OAuth — Aura Decore</h1>
        <p>App ID: <strong>{app_id}</strong></p>
        <p>Clique para autorizar o acesso à conta @auradecoracao no Pinterest:</p>
        <a class="btn" href="/start">Autorizar com Pinterest →</a>
        <div class="note">
        <strong>Escopos:</strong> pins:read, pins:write, boards:read, boards:write, user_accounts:read<br>
        <strong>Redirect:</strong> {REDIRECT_URI}
        </div>
        </div></body></html>"""

    def _send(self, html, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-id", help="Pinterest App ID")
    parser.add_argument("--app-secret", help="Pinterest App Secret")
    args = parser.parse_args()

    # Salva credenciais no .env se passadas como args
    if args.app_id and args.app_secret:
        text = ENV_PATH.read_text(encoding="utf-8")
        lines = []
        found_id = found_secret = False
        for line in text.splitlines():
            if line.startswith("PINTEREST_APP_ID="):
                lines.append(f"PINTEREST_APP_ID={args.app_id}"); found_id = True
            elif line.startswith("PINTEREST_APP_SECRET="):
                lines.append(f"PINTEREST_APP_SECRET={args.app_secret}"); found_secret = True
            else:
                lines.append(line)
        if not found_id: lines.append(f"PINTEREST_APP_ID={args.app_id}")
        if not found_secret: lines.append(f"PINTEREST_APP_SECRET={args.app_secret}")
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[Pinterest] App ID e Secret salvos no .env")

    server = ThreadingHTTPServer(("localhost", PORT), PinterestOAuthHandler)
    server.daemon_threads = True
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    import webbrowser
    threading.Thread(target=lambda: (time.sleep(1), webbrowser.open(f"http://localhost:{PORT}")), daemon=True).start()

    print(f"[Pinterest OAuth] Servidor em http://localhost:{PORT}")
    print(f"[Pinterest OAuth] Após criar o app, cole App ID + Secret em http://localhost:{PORT}")

    try:
        deadline = time.time() + 900
        while not state_store["done"] and time.time() < deadline:
            time.sleep(1)
        if state_store["done"]:
            print(f"\n[OK] Pinterest token capturado!")
            time.sleep(30)
        else:
            print("\n[TIMEOUT] Nenhum token em 15 min.")
        server.shutdown()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
