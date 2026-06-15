# -*- coding: utf-8 -*-
"""
get_tiktok_token.py — OAuth 2.0 TikTok Content Posting API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Servidor local que completa o flow OAuth e salva TIKTOK_ACCESS_TOKEN no .env

Pré-requisito:
  1. Criar app em developers.tiktok.com
  2. Habilitar "Content Posting API" no app
  3. Copiar Client Key e Client Secret
  4. Adicionar Redirect URI: http://localhost:8767/callback
  5. Executar: python get_tiktok_token.py --client-key SEU_KEY --client-secret SEU_SECRET
     OU: setar TIKTOK_CLIENT_KEY e TIKTOK_CLIENT_SECRET no .env e rodar sem args

Escopos gerados: user.info.basic,video.publish,video.upload
"""
import os, sys, json, time, pathlib, threading, urllib.parse, base64, hashlib, secrets, argparse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import httpx

ENV_PATH = pathlib.Path(__file__).parent / ".env"
PORT = 8767
SCOPES = "user.info.basic,video.publish,video.upload"
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


def save_token_to_env(token: str, refresh_token: str = "", open_id: str = ""):
    text = ENV_PATH.read_text(encoding="utf-8")
    lines = []
    found_access = found_refresh = found_oid = False
    for line in text.splitlines():
        if line.startswith("TIKTOK_ACCESS_TOKEN="):
            lines.append(f"TIKTOK_ACCESS_TOKEN={token}"); found_access = True
        elif line.startswith("TIKTOK_REFRESH_TOKEN="):
            lines.append(f"TIKTOK_REFRESH_TOKEN={refresh_token}"); found_refresh = True
        elif line.startswith("TIKTOK_OPEN_ID="):
            lines.append(f"TIKTOK_OPEN_ID={open_id}"); found_oid = True
        else:
            lines.append(line)
    if not found_access:
        lines.append(f"TIKTOK_ACCESS_TOKEN={token}")
    if not found_refresh and refresh_token:
        lines.append(f"TIKTOK_REFRESH_TOKEN={refresh_token}")
    if not found_oid and open_id:
        lines.append(f"TIKTOK_OPEN_ID={open_id}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n✅ TIKTOK_ACCESS_TOKEN salvo no .env!")


state_store = {"state": "", "verifier": "", "token": None, "done": False}


def generate_pkce():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


class TikTokOAuthHandler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        env = load_env()
        client_key = env.get("TIKTOK_CLIENT_KEY", "")
        client_secret = env.get("TIKTOK_CLIENT_SECRET", "")

        if parsed.path in ("/", ""):
            if not client_key:
                html = self._missing_credentials_page()
            else:
                html = self._start_page(client_key)
            self._send(html)

        elif parsed.path == "/start":
            verifier, challenge = generate_pkce()
            state = secrets.token_urlsafe(16)
            state_store["state"] = state
            state_store["verifier"] = verifier

            auth_url = (
                f"https://www.tiktok.com/v2/auth/authorize/"
                f"?client_key={client_key}"
                f"&response_type=code"
                f"&scope={urllib.parse.quote(SCOPES)}"
                f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
                f"&state={state}"
                f"&code_challenge={challenge}"
                f"&code_challenge_method=S256"
            )
            self._redirect(auth_url)

        elif parsed.path == "/callback":
            code = params.get("code", "")
            state_recv = params.get("state", "")

            if params.get("error"):
                desc = params.get("error_description", params.get("error"))
                self._send(f"<h2>❌ Erro: {desc}</h2>")
                return

            if state_recv != state_store["state"]:
                self._send("<h2>❌ State inválido — possível CSRF</h2>")
                return

            if not code:
                self._send("<h2>❌ Código de autorização não recebido</h2>")
                return

            try:
                r = httpx.post(
                    "https://open.tiktokapis.com/v2/oauth/token/",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data={
                        "client_key": client_key,
                        "client_secret": client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": REDIRECT_URI,
                        "code_verifier": state_store["verifier"],
                    },
                    timeout=20,
                )
                data = r.json()
                access_token = data.get("access_token", "")
                refresh_token = data.get("refresh_token", "")
                open_id = data.get("open_id", "")
                expires_in = data.get("expires_in", 0)

                if not access_token:
                    self._send(f"<h2>❌ Erro ao obter token: {data}</h2>")
                    return

                save_token_to_env(access_token, refresh_token, open_id)
                state_store["token"] = access_token
                state_store["done"] = True

                html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>✅ TikTok Token</title>
                <style>body{{font-family:sans-serif;max-width:500px;margin:60px auto;background:#f0f0f0}}
                .box{{background:#fff;border-radius:12px;padding:32px;text-align:center}}
                h2{{color:#2e7d32}}code{{background:#f5f5f5;padding:4px 8px;border-radius:4px}}</style></head>
                <body><div class="box">
                <h2>✅ TikTok Access Token salvo!</h2>
                <p>Token: <code>{access_token[:20]}...{access_token[-8:]}</code></p>
                <p>Open ID: <code>{open_id}</code></p>
                <p>Expira em: {int(expires_in/3600)}h</p>
                <p>TIKTOK_ACCESS_TOKEN atualizado no .env e Railway.</p>
                <p>Pode fechar esta janela.</p>
                </div></body></html>"""
                self._send(html)

                threading.Thread(target=self._update_railway, args=(access_token, refresh_token, open_id), daemon=True).start()

            except Exception as e:
                self._send(f"<h2>❌ Erro: {e}</h2>")

        elif parsed.path == "/save":
            token = params.get("token", "").strip()
            open_id = params.get("open_id", "").strip()
            if token and len(token) > 20:
                save_token_to_env(token, open_id=open_id)
                state_store["token"] = token
                state_store["done"] = True
                self._send(f"<h2>✅ Token salvo manualmente!</h2><p>{token[:20]}...</p>")
            else:
                self._send("<h2>Token inválido</h2>")
        else:
            self._send("<h2>404</h2>", 404)

    def _update_railway(self, access_token, refresh_token, open_id):
        try:
            import subprocess
            cwd = str(ENV_PATH.parent.parent)
            subprocess.run(["railway", "service", "web"], cwd=cwd, capture_output=True)
            subprocess.run(["railway", "variables", "set", f"TIKTOK_ACCESS_TOKEN={access_token}"],
                           cwd=cwd, capture_output=True)
            if refresh_token:
                subprocess.run(["railway", "variables", "set", f"TIKTOK_REFRESH_TOKEN={refresh_token}"],
                               cwd=cwd, capture_output=True)
            if open_id:
                subprocess.run(["railway", "variables", "set", f"TIKTOK_OPEN_ID={open_id}"],
                               cwd=cwd, capture_output=True)
            print("[Railway] TIKTOK_ACCESS_TOKEN atualizado no Railway.")
        except Exception as e:
            print(f"[Railway] Erro ao atualizar: {e}")

    def _missing_credentials_page(self):
        return """<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
        <title>TikTok OAuth — Sem credenciais</title>
        <style>body{font-family:sans-serif;max-width:600px;margin:60px auto;background:#f0f0f0}
        .box{background:#fff;border-radius:12px;padding:32px}h1{color:#000}
        input{width:100%;padding:10px;border:2px solid #ddd;border-radius:6px;box-sizing:border-box;margin:6px 0}
        button{background:#000;color:#fff;padding:12px 24px;border:none;border-radius:8px;cursor:pointer;margin-top:8px}
        a{color:#fe2c55}</style></head><body><div class="box">
        <h1>🎵 TikTok OAuth — Aura Decore</h1>
        <p>TIKTOK_CLIENT_KEY e TIKTOK_CLIENT_SECRET não encontrados no .env</p>
        <p><strong>Passo 1:</strong> Crie o app em
        <a href="https://developers.tiktok.com/" target="_blank">developers.tiktok.com</a></p>
        <p><strong>Passo 2:</strong> Habilite <strong>Content Posting API</strong> no app</p>
        <p><strong>Passo 3:</strong> Em "Manage Apps" → App → Settings → copie Client Key e Client Secret</p>
        <p><strong>Passo 4:</strong> Em Redirect URIs adicione: <code>http://localhost:8767/callback</code></p>
        <p><strong>Passo 5:</strong> Cole aqui para gerar o token:</p>
        <form action="/" method="get">
        <input name="client_key" placeholder="Client Key (ex: awxxxxxxxx)">
        <input name="client_secret" placeholder="Client Secret (ex: 7Gxxxxxxxx)">
        <button type="submit">Iniciar OAuth →</button>
        </form>
        <hr>
        <p>Ou cole o access_token diretamente:</p>
        <form action="/save" method="get">
        <input name="token" placeholder="Access Token TikTok...">
        <input name="open_id" placeholder="Open ID (opcional)">
        <button type="submit">Salvar token →</button>
        </form>
        </div></body></html>"""

    def _start_page(self, client_key):
        return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
        <title>TikTok OAuth — Aura Decore</title>
        <style>body{{font-family:sans-serif;max-width:600px;margin:60px auto;background:#f0f0f0}}
        .box{{background:#fff;border-radius:12px;padding:32px}}h1{{color:#000}}
        a.btn{{display:inline-block;background:#fe2c55;color:#fff;padding:14px 28px;
        border-radius:8px;text-decoration:none;font-weight:bold;margin-top:16px}}
        .note{{background:#fff0f2;border-left:4px solid #fe2c55;padding:12px;margin-top:16px}}
        </style></head><body><div class="box">
        <h1>🎵 TikTok OAuth — Aura Decore</h1>
        <p>Client Key: <strong>{client_key}</strong></p>
        <p>Clique para autorizar publicação de vídeos na conta @decore.aura:</p>
        <a class="btn" href="/start">Autorizar com TikTok →</a>
        <div class="note">
        <strong>Escopos:</strong> user.info.basic, video.publish, video.upload<br>
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
    parser.add_argument("--client-key", help="TikTok Client Key")
    parser.add_argument("--client-secret", help="TikTok Client Secret")
    args = parser.parse_args()

    if args.client_key and args.client_secret:
        text = ENV_PATH.read_text(encoding="utf-8")
        lines = []
        found_key = found_secret = False
        for line in text.splitlines():
            if line.startswith("TIKTOK_CLIENT_KEY="):
                lines.append(f"TIKTOK_CLIENT_KEY={args.client_key}"); found_key = True
            elif line.startswith("TIKTOK_CLIENT_SECRET="):
                lines.append(f"TIKTOK_CLIENT_SECRET={args.client_secret}"); found_secret = True
            else:
                lines.append(line)
        if not found_key: lines.append(f"TIKTOK_CLIENT_KEY={args.client_key}")
        if not found_secret: lines.append(f"TIKTOK_CLIENT_SECRET={args.client_secret}")
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[TikTok] Client Key e Secret salvos no .env")

    server = ThreadingHTTPServer(("localhost", PORT), TikTokOAuthHandler)
    server.daemon_threads = True
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    import webbrowser
    threading.Thread(target=lambda: (time.sleep(1), webbrowser.open(f"http://localhost:{PORT}")), daemon=True).start()

    print(f"[TikTok OAuth] Servidor em http://localhost:{PORT}")
    print(f"[TikTok OAuth] Siga as instruções no browser para criar o app e gerar o token")

    try:
        deadline = time.time() + 900
        while not state_store["done"] and time.time() < deadline:
            time.sleep(1)
        if state_store["done"]:
            print(f"\n[OK] TikTok token capturado!")
            time.sleep(30)
        else:
            print("\n[TIMEOUT] Nenhum token em 15 min.")
        server.shutdown()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
