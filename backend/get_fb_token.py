# -*- coding: utf-8 -*-
"""
Servidor local para capturar FB Page Token via OAuth.
Roda em http://localhost:8765
Eduardo abre o link, autoriza no Facebook, token e salvo automaticamente no .env
"""
import os, sys, json, time, pathlib, threading, urllib.parse, webbrowser
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
import httpx

ENV_PATH = pathlib.Path(__file__).parent / ".env"

# ─── Carrega variaveis do .env ─────────────────────────────────────────────────
def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def save_token_to_env(token: str):
    """Salva o token em FB_PAGE_TOKEN E META_ACCESS_TOKEN (mesmo valor)."""
    text = ENV_PATH.read_text(encoding="utf-8")
    lines = []
    found_fb = found_meta = False
    for line in text.splitlines():
        if line.startswith("FB_PAGE_TOKEN="):
            lines.append(f"FB_PAGE_TOKEN={token}")
            found_fb = True
        elif line.startswith("META_ACCESS_TOKEN="):
            lines.append(f"META_ACCESS_TOKEN={token}")
            found_meta = True
        else:
            lines.append(line)
    if not found_fb:
        lines.append(f"FB_PAGE_TOKEN={token}")
    if not found_meta:
        lines.append(f"META_ACCESS_TOKEN={token}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n✅ FB_PAGE_TOKEN + META_ACCESS_TOKEN salvos no .env!")

# ─── Handler HTTP ──────────────────────────────────────────────────────────────
captured_token = {"value": None, "done": False}

class TokenHandler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass  # silencia logs

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        # Pagina inicial — mostra instrucoes
        if parsed.path == "/" or parsed.path == "":
            env = load_env()
            page_id = env.get("FB_PAGE_ID", "")
            html = f"""<!DOCTYPE html><html lang="pt-BR"><head>
            <meta charset="UTF-8"><title>Aura Decore — FB Token</title>
            <style>body{{font-family:sans-serif;max-width:600px;margin:60px auto;background:#F5F0EB;color:#333}}
            .box{{background:#fff;border-radius:12px;padding:32px;box-shadow:0 2px 20px rgba(0,0,0,.08)}}
            h1{{color:#B8793A}}a.btn{{display:inline-block;background:#1877F2;color:#fff;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:bold;margin-top:16px}}
            .note{{background:#fff8e6;border-left:4px solid #B8793A;padding:12px 16px;border-radius:4px;margin-top:16px;font-size:.9em}}
            </style></head><body><div class="box">
            <h1>🔑 Aura Decore — FB Page Token</h1>
            <p>Clique no botão abaixo para autorizar o acesso à página do Facebook.</p>
            <p>Após autorizar, o token será salvo automaticamente no backend.</p>
            <a class="btn" href="/start">Autorizar com Facebook →</a>
            <div class="note">⚠️ Certifique-se de estar logado no Facebook como <strong>administrador da página Aura Decore</strong> antes de clicar.</div>
            </div></body></html>"""
            self._send(html)

        # Inicia flow OAuth
        elif parsed.path == "/start":
            env = load_env()
            app_id = env.get("META_APP_ID", "").strip()
            page_id = env.get("FB_PAGE_ID", "1111100822090245")

            if not app_id:
                # Sem App ID — redireciona para Graph Explorer para copiar token manualmente
                html = """<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
                <title>Sem App ID</title>
                <style>body{font-family:sans-serif;max-width:600px;margin:60px auto;background:#F5F0EB}
                .box{background:#fff;border-radius:12px;padding:32px;box-shadow:0 2px 20px rgba(0,0,0,.08)}
                h2{color:#B8793A}input{width:100%;padding:10px;font-size:1em;border:2px solid #ddd;border-radius:6px;box-sizing:border-box;margin:8px 0}
                button{background:#B8793A;color:#fff;padding:12px 24px;border:none;border-radius:8px;font-size:1em;cursor:pointer;margin-top:8px}
                a{color:#1877F2}</style></head><body><div class="box">
                <h2>Cole o Page Token diretamente</h2>
                <p>Abra o <a href="https://developers.facebook.com/tools/explorer/" target="_blank">Graph API Explorer</a>, gere o token da página e cole abaixo:</p>
                <form action="/save" method="get">
                <input name="token" placeholder="EAAxxxxxxxxxxxxxxx..." required>
                <button type="submit">Salvar token →</button>
                </form>
                <hr>
                <p><strong>Como obter no Graph Explorer (passo a passo):</strong><br>
                1. Acesse <a href="https://developers.facebook.com/tools/explorer/" target="_blank">developers.facebook.com/tools/explorer</a><br>
                2. App: selecione <strong>Aura Decore</strong> (App ID: 2073471413233500)<br>
                3. User or Page: selecione <strong>Aura Decore (página)</strong><br>
                4. Permissões necessárias — adicione TODAS:<br>
                &nbsp;&nbsp;✅ pages_manage_posts<br>
                &nbsp;&nbsp;✅ pages_read_engagement<br>
                &nbsp;&nbsp;✅ instagram_basic<br>
                &nbsp;&nbsp;✅ instagram_content_publish<br>
                &nbsp;&nbsp;✅ instagram_manage_comments<br>
                &nbsp;&nbsp;✅ instagram_manage_insights<br>
                &nbsp;&nbsp;✅ business_management<br>
                5. Clique "Generate Access Token" e autorize<br>
                6. Execute: <code>GET /me/accounts</code><br>
                7. Copie o <strong>access_token</strong> da linha da página Aura Decore<br>
                8. Cole acima e clique Salvar</p>
                <p style="color:#B8793A;font-size:.85em">⚠️ Isso gera um token de curta duração (~1h). O backend o converte automaticamente em token permanente da página.</p>
                </div></body></html>"""
                self._send(html)
            else:
                SCOPES = ",".join([
                    "pages_manage_posts",
                    "pages_read_engagement",
                    "pages_show_list",
                    "pages_manage_metadata",
                    "instagram_basic",
                    "instagram_content_publish",
                    "instagram_manage_comments",
                    "business_management",
                    "ads_management",
                    "ads_read",
                    "public_profile",
                ])
                # Fluxo IMPLÍCITO (response_type=token) — não requer META_APP_SECRET.
                # O token vem no hash da URL e é capturado por JS em /callback.
                redirect = (
                    f"https://www.facebook.com/v20.0/dialog/oauth?"
                    f"client_id={app_id}&redirect_uri=http://localhost:8765/callback"
                    f"&scope={SCOPES}"
                    f"&response_type=token"
                )
                self._redirect(redirect)

        # Salvar token colado manualmente
        elif parsed.path == "/save":
            token = params.get("token", "").strip()
            if token and len(token) > 20:
                # Tenta exchangar para page token (se for user token)
                try:
                    env = load_env()
                    page_id = env.get("FB_PAGE_ID", "1111100822090245")
                    r_pg = httpx.get(f"https://graph.facebook.com/v20.0/{page_id}",
                        params={"fields": "access_token", "access_token": token}, timeout=15)
                    pg_token = r_pg.json().get("access_token", "")
                    if pg_token and len(pg_token) > 30:
                        token = pg_token  # usa page token
                except Exception:
                    pass  # fallback: salva token original
                save_token_to_env(token)
                captured_token["value"] = token
                captured_token["done"] = True
                html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Sucesso!</title>
                <style>body{{font-family:sans-serif;max-width:500px;margin:60px auto;background:#F5F0EB}}
                .box{{background:#fff;border-radius:12px;padding:32px;text-align:center}}
                h2{{color:#2e7d32}}p{{color:#555}}</style></head><body><div class="box">
                <h2>✅ Token salvo com sucesso!</h2>
                <p>FB_PAGE_TOKEN foi salvo no .env</p>
                <p>Token: <code>{token[:20]}...{token[-8:]}</code></p>
                <p>Reinicie o backend para ativar.</p>
                <p>Pode fechar esta janela.</p>
                </div></body></html>"""
                self._send(html)
            else:
                self._send("<h2>Token inválido. Volte e tente novamente.</h2>")

        # Callback OAuth — suporta fluxo implícito (token no hash) e explícito (code)
        elif parsed.path == "/callback":
            # Fluxo implícito: token vem no hash (#access_token=...) — JS lê e submete aqui
            token_direct = params.get("access_token", "")
            if token_direct and len(token_direct) > 20:
                # Tentar pegar page token via /me/accounts
                try:
                    r_acc = httpx.get("https://graph.facebook.com/v20.0/me/accounts",
                        params={"fields": "id,name,access_token", "access_token": token_direct}, timeout=15)
                    accounts = r_acc.json().get("data", [])
                    page_token = token_direct
                    if accounts:
                        page_token = accounts[0].get("access_token", token_direct)
                        page_id_found = accounts[0].get("id", "")
                        # Atualiza FB_PAGE_ID automaticamente
                        env_text = ENV_PATH.read_text(encoding="utf-8")
                        lines = []
                        for ln in env_text.splitlines():
                            if ln.startswith("FB_PAGE_ID="):
                                lines.append(f"FB_PAGE_ID={page_id_found}")
                            else:
                                lines.append(ln)
                        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    save_token_to_env(page_token)
                    captured_token["value"] = page_token
                    captured_token["done"] = True
                    self._send(f"<h2>✅ Token capturado e salvo!</h2><p>{page_token[:30]}...</p><p>Pode fechar esta janela.</p>")
                except Exception as e:
                    self._send(f"<h2>Erro ao buscar page token: {e}</h2>")
                return

            # Página HTML para fluxo implícito — lê hash e submete via JS
            if not params:
                html_implicit = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Capturando token...</title></head>
                <body><h2>⏳ Capturando token do Facebook...</h2>
                <script>
                var hash = window.location.hash.substring(1);
                var params = {};
                hash.split('&').forEach(function(p){ var kv=p.split('='); params[kv[0]]=decodeURIComponent(kv[1]||''); });
                if(params.access_token){
                    document.body.innerHTML='<h2>✅ Token capturado! Salvando...</h2>';
                    fetch('/callback?access_token='+encodeURIComponent(params.access_token))
                    .then(function(r){return r.text();})
                    .then(function(t){document.body.innerHTML=t;});
                } else {
                    document.body.innerHTML='<h2>❌ Token não encontrado no URL. Tente novamente.</h2><pre>'+hash+'</pre>';
                }
                </script></body></html>"""
                self._send(html_implicit)
                return

            code = params.get("code", "")
            env = load_env()
            app_id = env.get("META_APP_ID", "2073471413233500")
            app_secret = env.get("META_APP_SECRET", "")
            page_id = env.get("FB_PAGE_ID", "")

            if not code:
                self._send("<h2>Erro: código OAuth não recebido.</h2>")
                return
            try:
                # Troca code por user token
                r = httpx.get("https://graph.facebook.com/v20.0/oauth/access_token",
                    params={"client_id": app_id, "client_secret": app_secret,
                            "redirect_uri": "http://localhost:8765/callback", "code": code},
                    timeout=15)
                user_token = r.json().get("access_token", "")
                # Troca por long-lived user token
                r2 = httpx.get("https://graph.facebook.com/v20.0/oauth/access_token",
                    params={"grant_type": "fb_exchange_token", "client_id": app_id,
                            "client_secret": app_secret, "fb_exchange_token": user_token},
                    timeout=15)
                ll_token = r2.json().get("access_token", user_token)
                # Pega page token permanente
                r3 = httpx.get(f"https://graph.facebook.com/v20.0/{page_id}",
                    params={"fields": "access_token", "access_token": ll_token}, timeout=15)
                page_token = r3.json().get("access_token", "")
                if page_token:
                    save_token_to_env(page_token)
                    captured_token["value"] = page_token
                    captured_token["done"] = True
                    self._send(f"<h2>✅ Page Token permanente salvo!</h2><p>{page_token[:30]}...</p>")
                else:
                    # Fallback: salva user token
                    save_token_to_env(ll_token)
                    captured_token["value"] = ll_token
                    captured_token["done"] = True
                    self._send(f"<h2>✅ Token salvo (user token)</h2>")
            except Exception as e:
                self._send(f"<h2>Erro: {e}</h2>")
        else:
            self._send("<h2>404</h2>", 404)

    def _send(self, html, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

# ─── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    PORT = 8765
    # ThreadingHTTPServer = nao trava com conexoes pendentes do navegador
    server = ThreadingHTTPServer(("localhost", PORT), TokenHandler)
    server.daemon_threads = True
    print(f"[META TOKEN] Servidor (threaded) em http://localhost:{PORT}")

    # serve_forever em thread separada
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    def open_browser():
        time.sleep(1)
        webbrowser.open(f"http://localhost:{PORT}")
    threading.Thread(target=open_browser, daemon=True).start()

    # Aguarda token ser capturado (ate 15 min), depois mantem vivo +30s p/ pagina de sucesso
    try:
        deadline = time.time() + 900
        while not captured_token["done"] and time.time() < deadline:
            time.sleep(1)
        if captured_token["done"]:
            print(f"\n[OK] Token capturado: {captured_token['value'][:30]}...")
            time.sleep(30)
        else:
            print("\n[TIMEOUT] Nenhum token em 15 min.")
        server.shutdown()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
        server.shutdown()
