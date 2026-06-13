# -*- coding: utf-8 -*-
"""
shopify_oauth_token.py — Gerador de Token Shopify Admin API via OAuth
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fluxo OAuth 2.0 completo para obter token permanente (offline).
Roda em http://localhost:8766
"""
import os, sys, time, pathlib, threading, webbrowser, urllib.parse, secrets, json, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ── Instalar dependencias ────────────────────────────────────────────────────
try:
    import httpx
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "-q"])
    import httpx

try:
    from dotenv import load_dotenv
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv", "-q"])
    from dotenv import load_dotenv

# ── Configuração ─────────────────────────────────────────────────────────────
HERE = pathlib.Path(__file__).parent
ENV_PATH = HERE / ".env"
load_dotenv(ENV_PATH, override=True)

SHOP = os.getenv("SHOPIFY_DOMAIN", "10ei3t-sf.myshopify.com")
API_KEY = os.getenv("SHOPIFY_API_KEY", "")
API_SECRET = os.getenv("SHOPIFY_API_SECRET", "")
PORT = 8766
NONCE = secrets.token_hex(16)
REDIRECT_URI = f"http://localhost:{PORT}/callback"

captured = {"done": False, "token": None, "error": None}

SCOPES = ",".join([
    "write_products", "read_products",
    "write_themes", "read_themes",
    "write_orders", "read_orders",
    "write_publications", "read_publications",
    "write_inventory", "read_inventory",
    "read_customers", "read_checkouts",
    "read_analytics",
    "read_shipping", "write_shipping",
    "read_fulfillments", "write_fulfillments"
])


def save_token_to_env(token: str, domain: str):
    """Salva o token em TODAS as variáveis relevantes do .env."""
    text = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.exists() else ""
    keys_to_update = {
        "SHOPIFY_DOMAIN": domain,
        "SHOPIFY_ADMIN_TOKEN": token,
        "SHOPIFY_ADMIN_API_TOKEN": token
    }
    seen = set()
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        matched = False
        for k, v in keys_to_update.items():
            if stripped.startswith(f"{k}="):
                lines.append(f"{k}={v}")
                seen.add(k)
                matched = True
                break
        if not matched:
            lines.append(line)
    for k, v in keys_to_update.items():
        if k not in seen:
            lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n  [SALVO] Token gravado no .env")
    print(f"    SHOPIFY_DOMAIN={domain}")
    print(f"    SHOPIFY_ADMIN_TOKEN={token[:25]}...")
    print(f"    SHOPIFY_ADMIN_API_TOKEN={token[:25]}...")


def test_token(token: str, domain: str) -> dict:
    """Testa o token contra múltiplos endpoints."""
    results = {"valid": False, "shop_name": "", "plan": "", "details": ""}
    
    # REST API
    for ver in ["2025-01", "2024-10", "2024-07"]:
        try:
            r = httpx.get(
                f"https://{domain}/admin/api/{ver}/shop.json",
                headers={"X-Shopify-Access-Token": token},
                timeout=15
            )
            if r.status_code == 200:
                shop = r.json().get("shop", {})
                results["valid"] = True
                results["shop_name"] = shop.get("name", "?")
                results["plan"] = shop.get("plan_name", "?")
                results["email"] = shop.get("email", "?")
                results["details"] = f"REST API {ver} OK"
                return results
        except Exception:
            continue
    
    # GraphQL
    try:
        r = httpx.post(
            f"https://{domain}/admin/api/2024-10/graphql.json",
            headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
            json={"query": "{ shop { name plan { displayName } } }"},
            timeout=15
        )
        if r.status_code == 200:
            data = r.json().get("data", {}).get("shop", {})
            if data:
                results["valid"] = True
                results["shop_name"] = data.get("name", "?")
                results["plan"] = data.get("plan", {}).get("displayName", "?")
                results["details"] = "GraphQL OK"
                return results
    except Exception:
        pass
    
    # Capturar erro
    try:
        r = httpx.get(
            f"https://{domain}/admin/api/2024-10/shop.json",
            headers={"X-Shopify-Access-Token": token},
            timeout=10
        )
        results["details"] = f"HTTP {r.status_code}: {r.text[:300]}"
    except Exception as e:
        results["details"] = str(e)
    return results


# ── CSS Premium ──────────────────────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
color:#e0e0e0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.c{width:100%;max-width:700px}
.box{background:rgba(255,255,255,0.06);backdrop-filter:blur(20px);border-radius:24px;padding:48px 40px;
border:1px solid rgba(255,255,255,0.1);box-shadow:0 25px 50px rgba(0,0,0,0.4)}
.box::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;
background:linear-gradient(90deg,#5cdb95,#05386b,#5cdb95);border-radius:24px 24px 0 0}
.box{position:relative;overflow:hidden}
h1{font-size:1.7em;font-weight:700;background:linear-gradient(135deg,#5cdb95,#8ee4af);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:6px}
.sub{color:#8892b0;font-size:.9em;margin-bottom:28px;line-height:1.5}
.section{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
border-radius:16px;padding:28px;margin-bottom:20px}
.section-title{font-weight:600;font-size:1em;color:#8ee4af;margin-bottom:4px;display:flex;align-items:center;gap:8px}
.section-desc{color:#8892b0;font-size:.82em;margin-bottom:16px}
label{display:block;font-weight:500;margin-bottom:5px;font-size:.88em;color:#ccd6f6}
input[type=text]{width:100%;padding:12px 16px;border:2px solid rgba(255,255,255,0.1);border-radius:10px;
font-size:.95em;background:rgba(255,255,255,0.05);color:#e6f1ff;transition:all .2s;font-family:'Inter',sans-serif}
input:focus{border-color:#5cdb95;outline:none;box-shadow:0 0 0 3px rgba(92,219,149,0.15)}
input::placeholder{color:#495670}
.btn{display:block;width:100%;background:linear-gradient(135deg,#5cdb95,#05386b);color:#fff;
padding:14px;border-radius:10px;border:none;font-weight:600;font-size:1em;cursor:pointer;
transition:all .25s;font-family:'Inter',sans-serif;letter-spacing:.02em;margin-top:12px}
.btn:hover{transform:translateY(-2px);box-shadow:0 8px 25px rgba(92,219,149,0.3)}
.btn:active{transform:translateY(0)}
.btn:disabled{opacity:.5;cursor:not-allowed;transform:none}
.btn-oauth{display:block;text-align:center;background:linear-gradient(135deg,#e94560,#c23052);
color:#fff;padding:14px;border-radius:10px;text-decoration:none;font-weight:600;font-size:1em;
transition:all .25s;margin-top:12px}
.btn-oauth:hover{transform:translateY(-2px);box-shadow:0 8px 25px rgba(233,69,96,0.3)}
.divider{display:flex;align-items:center;margin:24px 0;gap:16px}
.divider::before,.divider::after{content:'';flex:1;height:1px;background:rgba(255,255,255,0.1)}
.divider span{color:#8892b0;font-size:.8em;font-weight:500;white-space:nowrap}
.status{display:flex;align-items:center;gap:10px;padding:12px 16px;border-radius:10px;
font-size:.85em;margin-bottom:20px}
.status.warn{background:rgba(255,183,77,0.1);border:1px solid rgba(255,183,77,0.3);color:#ffb74d}
.status.ok{background:rgba(92,219,149,0.1);border:1px solid rgba(92,219,149,0.3);color:#5cdb95}
.status.err{background:rgba(233,69,96,0.1);border:1px solid rgba(233,69,96,0.3);color:#e94560}
.guide{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);
border-radius:14px;padding:20px 24px;margin-top:24px;font-size:.82em;color:#8892b0;line-height:1.7}
.guide h3{font-size:.92em;color:#8ee4af;margin-bottom:10px;font-weight:600}
.guide ol{padding-left:18px;margin:0}
.guide li{margin-bottom:4px}
.guide code{background:rgba(92,219,149,0.15);padding:2px 7px;border-radius:4px;font-size:.9em;color:#5cdb95}
.tag{display:inline-block;background:linear-gradient(135deg,rgba(92,219,149,0.2),rgba(92,219,149,0.1));
color:#5cdb95;font-size:.72em;font-weight:600;padding:4px 12px;border-radius:20px;
border:1px solid rgba(92,219,149,0.2);margin-bottom:16px}
.form-group{margin-bottom:16px}
.success-box{text-align:center;padding:40px 30px}
.success-icon{font-size:4em;margin-bottom:20px}
.success-detail{background:rgba(92,219,149,0.1);border:1px solid rgba(92,219,149,0.2);
padding:20px;border-radius:14px;margin:24px 0;text-align:left;font-size:.9em;line-height:1.7;color:#8ee4af}
.error-detail{background:rgba(233,69,96,0.1);border:1px solid rgba(233,69,96,0.2);
padding:20px;border-radius:14px;margin:24px 0;text-align:left;font-size:.88em;line-height:1.6;
color:#e94560;word-break:break-all}
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(p.query))

        if p.path in ("/", ""):
            self._home(q)
        elif p.path == "/start-oauth":
            self._start_oauth()
        elif p.path == "/callback":
            self._callback(q)
        elif p.path == "/save-manual":
            self._save_manual(q)
        else:
            self._html("<h2>404</h2>", 404)

    def _home(self, q):
        # Status atual
        current = os.getenv("SHOPIFY_ADMIN_TOKEN", "") or os.getenv("SHOPIFY_ADMIN_API_TOKEN", "")
        status_html = ""
        if current:
            res = test_token(current, SHOP)
            if res["valid"]:
                status_html = f'<div class="status ok">🟢 Token ativo — {res["shop_name"]} ({res["plan"]})</div>'
            else:
                status_html = f'<div class="status err">🔴 Token atual inválido: {res["details"][:100]}</div>'
        else:
            status_html = '<div class="status warn">⚠️ Nenhum token configurado.</div>'

        oauth_btn = ""
        if API_KEY and API_SECRET:
            oauth_btn = f"""
            <div class="divider"><span>OU VIA OAUTH AUTOMÁTICO</span></div>
            <a href="/start-oauth" class="btn-oauth">🔗 Autorizar App via OAuth (gera token permanente) →</a>
            <p style="text-align:center;font-size:.78em;color:#8892b0;margin-top:8px">
                Usa API Key: {API_KEY[:8]}... | Loja: {SHOP}
            </p>
            """
        else:
            oauth_btn = '<div class="status warn">⚠️ OAuth indisponível — SHOPIFY_API_KEY não configurada no .env</div>'

        html = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<title>Shopify Token — Aura Decore</title><style>{CSS}</style></head>
<body><div class="c"><div class="box">
    <div class="tag">SHOPIFY ADMIN API</div>
    <h1>🔑 Configuração de Token</h1>
    <div class="sub">Gere ou configure o token de acesso permanente para a API Admin da sua loja Shopify.</div>
    
    {status_html}
    
    <div class="section">
        <div class="section-title">📋 Método 1 — Colar Token Manualmente</div>
        <div class="section-desc">Cole um token gerado no painel Shopify (shpat_ ou atkn_).</div>
        <form id="f" action="/save-manual" method="GET">
            <div class="form-group">
                <label>Domínio da Loja</label>
                <input type="text" name="domain" value="{SHOP}" required>
            </div>
            <div class="form-group">
                <label>Token Admin API</label>
                <input type="text" name="token" placeholder="shpat_xxx... ou atkn_xxx..." required>
            </div>
            <button type="submit" class="btn" id="btn">Validar & Salvar →</button>
        </form>
    </div>
    
    <div class="section">
        <div class="section-title">⚡ Método 2 — OAuth Automático (Recomendado)</div>
        <div class="section-desc">Autorize o app na Shopify e o token será capturado automaticamente.</div>
        {oauth_btn}
    </div>
    
    <div class="guide">
        <h3>📋 Para gerar token no painel Shopify:</h3>
        <ol>
            <li>Acesse <b>admin.shopify.com</b> → Configurações → Apps</li>
            <li>Clique em <b>Desenvolver apps</b> → <b>Criar app</b></li>
            <li>Configure os <b>escopos da API Admin</b> → Salvar</li>
            <li>Clique em <b>Instalar app</b> → Copie o token</li>
            <li>Cole acima e clique <b>Validar & Salvar</b></li>
        </ol>
    </div>
</div></div>
<script>
document.getElementById('f').addEventListener('submit',function(){{
    var b=document.getElementById('btn');b.textContent='⏳ Validando...';b.disabled=true;
}});
</script></body></html>"""
        self._html(html)

    def _start_oauth(self):
        if not API_KEY:
            self._html(self._err_page("API Key não configurada", "Defina SHOPIFY_API_KEY no .env"))
            return
        url = (
            f"https://{SHOP}/admin/oauth/authorize"
            f"?client_id={API_KEY}"
            f"&scope={urllib.parse.quote(SCOPES)}"
            f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
            f"&state={NONCE}"
        )
        print(f"  [OAUTH] Redirecionando para: {url[:100]}...")
        self._redirect(url)

    def _callback(self, q):
        error = q.get("error", "")
        error_desc = q.get("error_description", "")
        code = q.get("code", "")
        state = q.get("state", "")

        if error:
            print(f"  [OAUTH ERRO] {error}: {error_desc}")
            self._html(self._err_page(
                f"Erro OAuth: {error}",
                f"{error_desc}<br><br>Possíveis causas:<br>"
                f"• O app não tem <code>http://localhost:{PORT}/callback</code> como Redirect URI<br>"
                f"• A API Key está incorreta<br>"
                f"• O app não está configurado como Custom/Public App no Partners Dashboard",
                back=True
            ))
            return

        if not code:
            self._html(self._err_page("Código não recebido", "Tente novamente.", back=True))
            return

        # Trocar código por token
        print(f"  [OAUTH] Trocando código por token...")
        try:
            r = httpx.post(
                f"https://{SHOP}/admin/oauth/access_token",
                data={
                    "client_id": API_KEY,
                    "client_secret": API_SECRET,
                    "code": code
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=20
            )
            print(f"  [OAUTH] Resposta: HTTP {r.status_code}")
            print(f"  [OAUTH] Body: {r.text[:300]}")
            
            if r.status_code != 200:
                self._html(self._err_page(
                    f"Shopify retornou HTTP {r.status_code}",
                    f"Resposta: {r.text[:500]}",
                    back=True
                ))
                return
            
            data = r.json()
            token = data.get("access_token", "")
            scope = data.get("scope", "")

            if not token:
                self._html(self._err_page("Token vazio na resposta", json.dumps(data, indent=2)[:500], back=True))
                return

            # Salvar e validar
            save_token_to_env(token, SHOP)
            res = test_token(token, SHOP)
            captured["token"] = token
            captured["done"] = True

            prefix = token[:5] + "..." if len(token) > 5 else token
            details = f"""
                <b>Prefixo:</b> {prefix}<br>
                <b>Escopos:</b> {scope[:200]}<br>
                <b>Loja:</b> {res.get('shop_name', '?')}<br>
                <b>Plano:</b> {res.get('plan', '?')}<br>
                <b>Validação:</b> {'✅ Token funcional!' if res['valid'] else '⚠️ ' + res['details'][:200]}
            """
            self._html(self._ok_page("Token OAuth Capturado!", details))

        except Exception as e:
            print(f"  [OAUTH ERRO] {e}")
            self._html(self._err_page("Erro ao trocar código", str(e), back=True))

    def _save_manual(self, q):
        token = q.get("token", "").strip()
        domain = q.get("domain", "").strip()

        if not token or not domain:
            self._html(self._err_page("Dados incompletos", "Token e domínio são obrigatórios.", back=True))
            return

        print(f"  [MANUAL] Validando token em {domain}...")
        res = test_token(token, domain)

        if res["valid"]:
            save_token_to_env(token, domain)
            captured["done"] = True
            captured["token"] = token
            details = f"""
                <b>Loja:</b> {res['shop_name']}<br>
                <b>Plano:</b> {res.get('plan', '?')}<br>
                <b>Email:</b> {res.get('email', '?')}<br>
                <b>API:</b> {res['details']}<br>
                <b>Prefixo:</b> {token[:5]}...
            """
            self._html(self._ok_page("Token Salvo com Sucesso!", details))
        else:
            self._html(self._err_page(
                "Validação Falhou",
                f"O token não foi aceito pela loja <b>{domain}</b>.<br><br>"
                f"<b>Erro:</b> {res['details']}<br><br>"
                f"<b>Verifique:</b><br>"
                f"• O token está completo (sem espaços extras)?<br>"
                f"• O domínio está correto?<br>"
                f"• O app está instalado na loja?<br>"
                f"• O token não foi revogado?",
                back=True
            ))

    def _ok_page(self, title, details):
        return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<title>Sucesso</title><style>{CSS}</style></head>
<body><div class="c"><div class="box success-box">
    <div class="success-icon">✅</div>
    <h1 style="color:#5cdb95;-webkit-text-fill-color:#5cdb95">{title}</h1>
    <div class="success-detail">{details}</div>
    <p style="color:#8ee4af;font-weight:600;font-size:1.1em;margin-top:30px">
        Prontinho! Pode fechar esta janela. 🎉
    </p>
</div></div></body></html>"""

    def _err_page(self, title, details, back=False):
        btn = '<a href="/" style="display:inline-block;background:linear-gradient(135deg,#5cdb95,#05386b);color:#fff;padding:12px 28px;border-radius:10px;text-decoration:none;font-weight:600;margin-top:20px">← Tentar Novamente</a>' if back else ''
        return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<title>Erro</title><style>{CSS}</style></head>
<body><div class="c"><div class="box" style="text-align:center">
    <div style="font-size:4em;margin-bottom:20px">❌</div>
    <h1 style="color:#e94560;-webkit-text-fill-color:#e94560">{title}</h1>
    <div class="error-detail">{details}</div>
    {btn}
</div></div></body></html>"""

    def _html(self, h, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(h.encode("utf-8"))

    def _redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()


if __name__ == "__main__":
    # Matar processo anterior na porta
    try:
        r = subprocess.run(
            ["powershell", "-Command",
             f"$c = Get-NetTCPConnection -LocalPort {PORT} -ErrorAction SilentlyContinue; "
             f"if($c) {{ $c | ForEach-Object {{ taskkill /F /PID $($_.OwningProcess) 2>$null }} }}"],
            capture_output=True, text=True, timeout=8
        )
    except Exception:
        pass

    time.sleep(1)

    server = ThreadingHTTPServer(("localhost", PORT), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()

    print()
    print("=" * 60)
    print("  SHOPIFY TOKEN GENERATOR — Aura Decore")
    print(f"  Servidor: http://localhost:{PORT}")
    print(f"  Loja:     {SHOP}")
    print(f"  API Key:  {API_KEY[:12]}..." if API_KEY else "  API Key:  (não configurada)")
    print("=" * 60)
    print()

    # Abrir Chrome
    def open_chrome():
        time.sleep(1.5)
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        for cp in chrome_paths:
            if os.path.exists(cp):
                try:
                    subprocess.Popen([cp, f"http://localhost:{PORT}"])
                    print(f"  [OK] Chrome aberto")
                    return
                except Exception:
                    pass
        webbrowser.open(f"http://localhost:{PORT}")
        print(f"  [OK] Navegador aberto")

    threading.Thread(target=open_chrome, daemon=True).start()

    try:
        deadline = time.time() + 1200
        while not captured["done"] and time.time() < deadline:
            time.sleep(1)
        if captured["done"]:
            token = captured["token"]
            print()
            print("=" * 60)
            print(f"  ✅ TOKEN CAPTURADO E SALVO!")
            print(f"  Prefixo: {token[:5]}...")
            print(f"  Tamanho: {len(token)} caracteres")
            print("=" * 60)
            time.sleep(3)
        else:
            print("\n  [TIMEOUT] 20 minutos sem token.")
        server.shutdown()
    except KeyboardInterrupt:
        print("\n  Encerrado.")
        server.shutdown()
