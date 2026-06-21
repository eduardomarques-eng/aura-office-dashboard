"""
watchdog_aura.py — Guardião 24/7 dos serviços Aura Decore
Monitora e reinicia automaticamente: Backend FastAPI (8000) + WPPConnect (21465)
Execute: python watchdog_aura.py
"""
import subprocess
import sys
import os
import time
import socket
import pathlib
import signal
import threading
import datetime
import logging

# Fix Windows terminal encoding for unicode logs
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── Configuração de logging ────────────────────────────────────────────────────
LOG_FILE = pathlib.Path(__file__).parent / "backend" / "watchdog.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("watchdog")

# ── Caminhos ───────────────────────────────────────────────────────────────────
BASE_DIR    = pathlib.Path(__file__).parent
BACKEND_DIR = BASE_DIR / "backend"
WPP_DIR     = pathlib.Path("C:/Users/erick/wppconnect-server")
VENV_PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"
SYS_PYTHON  = pathlib.Path(r"C:\Users\erick\AppData\Local\Programs\Python\Python312\python.exe")

PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else str(SYS_PYTHON)

# ── Carrega .env para detectar URLs remotas ───────────────────────────────────
_env_file = BACKEND_DIR / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=_env_file, override=False)
    except ImportError:
        pass

# ── Serviços monitorados ───────────────────────────────────────────────────────
wpp_url = os.getenv("WPPCONNECT_URL", "")
n8n_url = os.getenv("N8N_BASE_URL", "")

is_wpp_local = "localhost" in wpp_url or "127.0.0.1" in wpp_url or not wpp_url
is_n8n_local = "localhost" in n8n_url or "127.0.0.1" in n8n_url or not n8n_url

SERVICES = {
    "backend": {
        "port":        8000,
        "check_url":   "http://localhost:8000/health",
        "cmd":         [PYTHON, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"],
        "cwd":         str(BACKEND_DIR),
        "restart_max": 10,
        "cooldown":    8,
        "process":     None,
    }
}

if is_wpp_local:
    SERVICES["wppconnect"] = {
        "port":        21465,
        "check_url":   "http://localhost:21465",
        "cmd":         ["npm", "run", "start"],
        "cwd":         str(WPP_DIR) if WPP_DIR.exists() else None,
        "restart_max": 5,
        "cooldown":    12,
        "process":     None,
    }

if is_n8n_local:
    SERVICES["n8n"] = {
        "port":        5678,
        "check_url":   "http://localhost:5678/healthz",
        "cmd":         [r"C:\Users\erick\AppData\Roaming\npm\n8n.cmd", "start"],
        "cwd":         str(BASE_DIR),
        "restart_max": 5,
        "cooldown":    15,
        "process":     None,
    }

restart_counts = {k: 0 for k in SERVICES}
_stop_event = threading.Event()
_last_sync_day = -1  # controla sincronizacao diaria

# ── Utilitários ────────────────────────────────────────────────────────────────
def is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def kill_process(proc):
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

def start_service(name: str) -> bool:
    svc = SERVICES[name]
    if not svc["cwd"] or not pathlib.Path(svc["cwd"]).exists():
        log.warning(f"[{name}] Diretório não encontrado: {svc['cwd']} — ignorando.")
        return False

    if restart_counts[name] >= svc["restart_max"]:
        log.error(f"[{name}] Limite de {svc['restart_max']} reinicializações atingido! Intervenção manual necessária.")
        return False

    kill_process(svc["process"])

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["OTEL_SDK_DISABLED"]       = "true"
    env["CREWAI_TELEMETRY_OPT_OUT"] = "true"

    cmd = svc["cmd"]
    # No Windows, npm e n8n.cmd precisam de shell=True
    use_shell = name in ("wppconnect", "n8n") and sys.platform == "win32"

    log.info(f"[{name}] Iniciando: {' '.join(cmd)} (tentativa {restart_counts[name]+1})")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=svc["cwd"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=use_shell,
        )
        svc["process"] = proc
        restart_counts[name] += 1

        # Thread para capturar logs do processo filho
        def _log_output(p, label):
            try:
                for raw_line in p.stdout:
                    try:
                        line = raw_line.decode("utf-8", errors="replace").rstrip()
                        if line:
                            log.info(f"  [{label}] {line}")
                    except Exception:
                        pass
            except Exception:
                pass

        t = threading.Thread(target=_log_output, args=(proc, name), daemon=True)
        t.start()
        return True
    except Exception as e:
        log.error(f"[{name}] Falha ao iniciar: {e}")
        return False

def check_and_heal(name: str):
    svc = SERVICES[name]
    port = svc["port"]
    proc = svc["process"]

    # Processo morreu?
    proc_dead = proc is not None and proc.poll() is not None
    port_down  = not is_port_open(port)

    if proc_dead or (proc is None and port_down):
        reason = "processo morreu" if proc_dead else "porta fechada / serviço não iniciado"
        log.warning(f"[{name}] ⚠️  Serviço inativo ({reason}). Reiniciando em {svc['cooldown']}s...")
        time.sleep(svc["cooldown"])
        start_service(name)
    elif port_down and proc and proc.poll() is None:
        # Processo existe mas porta não responde → pode estar inicializando
        log.debug(f"[{name}] Processo vivo mas porta {port} ainda não responde (pode estar subindo)...")

# ── Loop principal ─────────────────────────────────────────────────────────────
def run_daily_sync():
    """Executa sync_full_system.py em background (sincronizacao diaria)."""
    sync_script = BASE_DIR / "sync_full_system.py"
    if not sync_script.exists():
        log.warning("sync_full_system.py nao encontrado — pulando sync diario")
        return
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["OTEL_SDK_DISABLED"] = "true"
        env["CREWAI_TELEMETRY_OPT_OUT"] = "true"
        proc = subprocess.Popen(
            [PYTHON, "-X", "utf8", str(sync_script)],
            cwd=str(BASE_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        out, _ = proc.communicate(timeout=120)
        log.info("[SYNC] Sincronizacao diaria concluida:")
        for line in out.decode("utf-8", errors="replace").split("\n"):
            if line.strip():
                log.info(f"  {line}")
    except Exception as e:
        log.error(f"[SYNC] Erro na sincronizacao diaria: {e}")

def watchdog_loop():
    log.info("=" * 60)
    log.info("  🛡️  Watchdog Aura Decore — iniciando")
    log.info(f"  Python: {PYTHON}")
    log.info(f"  Backend: {BACKEND_DIR}")
    log.info(f"  WPPConnect dir existe: {WPP_DIR.exists()}")
    log.info("=" * 60)

    # Inicialização imediata
    for name in SERVICES:
        if not is_port_open(SERVICES[name]["port"]):
            start_service(name)
            time.sleep(5)

    log.info("Monitoramento ativo. Verificando a cada 30s...")

    while not _stop_event.is_set():
        for name in SERVICES:
            if not _stop_event.is_set():
                check_and_heal(name)

        # Sincronizacao diaria automatica as 06:00
        global _last_sync_day
        now = datetime.datetime.now()
        if now.hour == 6 and now.day != _last_sync_day:
            _last_sync_day = now.day
            log.info("[SYNC] Iniciando sincronizacao diaria automatica (06:00)...")
            sync_thread = threading.Thread(target=run_daily_sync, daemon=True)
            sync_thread.start()

        _stop_event.wait(30)

    log.info("Watchdog encerrado.")

def graceful_stop(sig, frame):
    log.info(f"Sinal {sig} recebido. Encerrando watchdog...")
    _stop_event.set()
    for name, svc in SERVICES.items():
        kill_process(svc["process"])
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT,  graceful_stop)
    signal.signal(signal.SIGTERM, graceful_stop)
    try:
        watchdog_loop()
    except KeyboardInterrupt:
        graceful_stop(None, None)
