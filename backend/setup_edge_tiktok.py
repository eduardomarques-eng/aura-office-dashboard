# -*- coding: utf-8 -*-
"""
setup_edge_tiktok.py — Abre Edge para Eduardo fazer login TikTok (executar 1x)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cria o perfil Edge dedicado para automação TikTok.
Edge funciona com Playwright mesmo com Chrome aberto (executáveis separados).

Uso: python setup_edge_tiktok.py
"""
import pathlib, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EDGE_PROFILE = str(pathlib.Path(__file__).parent / "tiktok-edge-profile")
TIKTOK_LOGIN = "https://www.tiktok.com/login"
TIKTOK_STUDIO = "https://www.tiktok.com/tiktokstudio/upload"


def setup():
    from playwright.sync_api import sync_playwright

    print("\n  🎵 Aura Decore — Setup TikTok Edge")
    print("  ====================================")
    print(f"  Perfil: {EDGE_PROFILE}")
    print("\n  Abrindo Microsoft Edge...")
    print("  👉 FAÇA LOGIN NO TIKTOK e aguarde a tela de upload aparecer.")
    print("  👉 Após ver 'Seleciona o vídeo a carregar', feche o Edge ou pressione Enter aqui.\n")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=EDGE_PROFILE,
            channel="msedge",
            headless=False,
            args=["--no-sandbox"],
            timeout=30000,
        )
        page = ctx.new_page()
        page.goto(TIKTOK_LOGIN, wait_until="domcontentloaded", timeout=20000)

        print("  Edge aberto em tiktok.com/login. Faça login manualmente.")
        print("  Pressione Enter quando tiver concluído o login...")
        input()

        # Verificar se está logado navegando para o Studio
        try:
            page.goto(TIKTOK_STUDIO, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)
            content = page.inner_text("body")
            if "Seleciona" in content or "arrasta" in content or "carregar" in content:
                print("\n  ✅ Login TikTok confirmado! Upload page acessível.")
                print(f"  Perfil salvo em: {EDGE_PROFILE}")
                print("\n  Agora pode usar:")
                print("  python social_agent.py --tiktok-video video.mp4")
            else:
                print("\n  ⚠️  Página de upload não detectada. Verifique se o login foi concluído.")
        except Exception as e:
            print(f"\n  ⚠️  Erro ao verificar: {e}")

        ctx.close()


if __name__ == "__main__":
    setup()
