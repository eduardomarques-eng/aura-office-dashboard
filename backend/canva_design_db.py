# -*- coding: utf-8 -*-
"""
canva_design_db.py — Banco de Dados de Designs Canva + Calendário de Publicação
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Catálogo de todos os designs Canva em PT-BR gerados para a Aura Decore.
Gerencia o calendário de recorrência de publicações com espaçamento neurológico.

Uso:
  python canva_design_db.py init       # Cria/recria o banco com todos os designs
  python canva_design_db.py calendar   # Gera calendário de publicação 90 dias
  python canva_design_db.py status     # Mostra status de publicações
  python canva_design_db.py next       # Próximos posts agendados (hoje)
  python canva_design_db.py list       # Lista todos os designs PT-BR
"""
import os, sys, json, sqlite3, pathlib
from datetime import datetime, date, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DB_PATH = pathlib.Path(__file__).parent / "canva_designs.db"

# ── Catálogo completo de designs PT-BR (excluindo inglês) ────────────────────
# Formato: (design_id, titulo, tipo, categoria, canal_primario, serie, episodio)
DESIGNS_PTBR = [
    # ── SÉRIE: Cantos que Curam ──────────────────────────────────────────────
    ("DAHMraPTz60", "Seu cantinho merece cuidado", "instagram_post", "serie", "instagram", "cantos_que_curam", 5),
    ("DAHMrUX15cM", "O canto que cura", "instagram_post", "serie", "instagram", "cantos_que_curam", 6),
    ("DAHMrJTfxdg", "Sua casa tem um canto que te abraça?", "instagram_post", "serie", "instagram", "cantos_que_curam", 1),

    # ── SÉRIE: Meu Refúgio ───────────────────────────────────────────────────
    ("DAHMrSVXbgI", "Este espaço foi feito para você respirar", "instagram_post", "serie", "instagram", "meu_refugio", 5),
    ("DAHMrYTKHb8", "Você merece um espaço que te devolva", "instagram_post", "serie", "instagram", "meu_refugio", 6),
    ("DAHMrLLNpbY", "Meu Refúgio: Você entra em casa...", "instagram_post", "serie", "instagram", "meu_refugio", 1),
    ("DAHMrEdgi38", "Elementos naturais", "instagram_post", "serie", "instagram", "meu_refugio", 2),
    ("DAHMrMRP4ak", "Seu espaço", "instagram_post", "serie", "instagram", "meu_refugio", 3),

    # ── SÉRIE: Biofilia em Casa ───────────────────────────────────────────────
    ("DAHMrcGA9AY", "Natureza dentro de casa: a ciência do bem-estar", "instagram_post", "serie", "instagram", "biofilia_em_casa", 5),
    ("DAHMrWe7buU", "Seu corpo sabe quando está num ambiente natural", "facebook_post", "serie", "facebook", "biofilia_em_casa", 6),
    ("DAHMrUBmX68", "Biofilia", "instagram_post", "serie", "instagram", "biofilia_em_casa", 2),
    ("DAHLw1DS-Qw", "Post Instagram: Biofilia Aura Decore", "instagram_post", "serie", "instagram", "biofilia_em_casa", 1),
    ("DAHLw6Farsc", "Story Instagram: Biofilia (Aura Decore)", "story", "serie", "instagram_story", "biofilia_em_casa", 3),

    # ── SÉRIE: Neuroarquitetura na Prática ────────────────────────────────────
    ("DAHMrZlh6Ks", "Como a Luz Natural Muda o Humor", "instagram_post", "serie", "instagram", "neuroarquitetura", 5),
    ("DAHMrOpEIFg", "Luz natural", "instagram_post", "serie", "instagram", "neuroarquitetura", 1),
    ("DAHMrKMOPQ0", "Casa Acolhe", "instagram_post", "serie", "instagram", "neuroarquitetura", 2),

    # ── SÉRIE: Ambientes que Abraçam ─────────────────────────────────────────
    ("DAHMrcWL_Fo", "Um lar que abraça de volta", "pinterest_pin", "serie", "pinterest", "ambientes_que_abracam", 5),
    ("DAHMrCwVjCY", "Sala Japandi", "pinterest_pin", "serie", "pinterest", "ambientes_que_abracam", 1),
    ("DAHMrYHHcGw", "Uma peça. Uma mudança.", "instagram_post", "serie", "instagram", "ambientes_que_abracam", 2),

    # ── PRODUTO: Vaso Cerâmica Wabi-Sabi ────────────────────────────────────
    ("DAHMrbgt65g", "Feito à mão. Pensado para durar. R$89,90", "instagram_post", "produto", "instagram", "vaso_wabi_sabi", None),
    ("DAHMrWCnpIE", "Cerâmica artesanal que ancora", "pinterest_pin", "produto", "pinterest", "vaso_wabi_sabi", None),
    ("DAHMrTV02k8", "O detalhe que faz toda a diferença", "facebook_post", "produto", "facebook", "vaso_wabi_sabi", None),
    ("DAHMrU4oj10", "Feito com as mãos. Sentido com a alma.", "instagram_post", "produto", "instagram", "vaso_wabi_sabi", None),
    ("DAHLujj94Ro", "Carrossel Vaso Cerâmico Wabi-Sabi", "instagram_post", "produto", "instagram", "vaso_wabi_sabi", None),
    ("DAHJnWXnljo", "Vaso Artesanal Terracota", "instagram_post", "produto", "instagram", "vaso_terracota", None),
    ("DAHJnfB3XK0", "Vaso Fosco Bege Areia", "instagram_post", "produto", "instagram", "vaso_bege", None),

    # ── PRODUTO: Vela Âmbar Natural ──────────────────────────────────────────
    ("DAHMrc38hcU", "Vela Âmbar", "instagram_post", "produto", "instagram", "vela_ambar", None),
    ("DAHMrStahgE", "Âmbar Natural (Pin)", "pinterest_pin", "produto", "pinterest", "vela_ambar", None),
    ("DAHMrfHX-8Q", "Noites que você vai querer repetir", "facebook_post", "produto", "facebook", "vela_ambar", None),
    ("DAHMraxAoGA", "Aromas que transformam", "instagram_post", "produto", "instagram", "vela_ambar", None),
    ("DAHJbBgnrbg", "Vela Âmbar Serenity", "instagram_post", "produto", "instagram", "vela_ambar", None),
    ("DAHJnUWLHsU", "Vela Aromática Âmbar Sândalo", "instagram_post", "produto", "instagram", "vela_sandalo", None),
    ("DAHMrIG2XIQ", "Vela Âmbar Natural (Pin)", "pinterest_pin", "produto", "pinterest", "vela_ambar", None),
    ("DAHMg0ZEB88", "Velas de cera de coco em duo", "instagram_post", "produto", "instagram", "vela_ambar", None),
    ("DAHMrCKx44A", "Acenda.", "instagram_post", "produto", "instagram", "vela_ambar", None),

    # ── PRODUTO: Almofada Linho Natural ──────────────────────────────────────
    ("DAHMra9c_jQ", "A textura que transforma", "instagram_post", "produto", "instagram", "almofada_linho", None),
    ("DAHMrdq6fss", "Almofada Linho Natural (Pin)", "pinterest_pin", "produto", "pinterest", "almofada_linho", None),
    ("DAHMrdTkjkc", "Conforto que você vê e sente", "facebook_post", "produto", "facebook", "almofada_linho", None),
    ("DAHMrJAooCs", "Aura Decore: A textura que transforma", "instagram_post", "produto", "instagram", "almofada_linho", None),

    # ── PRODUTO: Pampa Seco Premium ──────────────────────────────────────────
    ("DAHMrW5kbxA", "Natureza que fica. Para sempre.", "instagram_post", "produto", "instagram", "pampa_seco", None),
    ("DAHMrSxZP-8", "Pampa Seco (Pin)", "pinterest_pin", "produto", "pinterest", "pampa_seco", None),
    ("DAHMrQnIdsE", "Boho-japandi: o estilo que chegou para ficar", "facebook_post", "produto", "facebook", "pampa_seco", None),

    # ── PRODUTO: Bandeja Madeira ─────────────────────────────────────────────
    ("DAHJnTxG-q8", "Bandeja Minimalista Madeira Natural", "instagram_post", "produto", "instagram", "bandeja_madeira", None),

    # ── LIFESTYLE / EDITORIAL ────────────────────────────────────────────────
    ("DAHMrCkbQkA", "Editar é decorar.", "instagram_post", "lifestyle", "instagram", None, None),
    ("DAHMq4FJPmg", "Wabi-Sabi — a arte de encontrar", "instagram_post", "lifestyle", "instagram", None, None),
    ("DAHMq3U2ByE", "5 peças que elevam a decoração", "instagram_post", "lifestyle", "instagram", None, None),
    ("DAHMrHYx42Q", "Arranjo de Algodão Seco — Inauguração", "instagram_post", "lifestyle", "instagram", None, None),
    ("DAHMWE2Y63A", "Espaço Sereno", "instagram_post", "lifestyle", "instagram", None, None),
    ("DAHMh5teqNY", "Seu lar. Sua essência.", "instagram_post", "lifestyle", "instagram", None, None),
    ("DAHMrMEo7Mo", "3 passos para uma decoração Japandi", "instagram_post", "lifestyle", "instagram", None, None),
    ("DAHMrCkmjJ0", "5 objetos que mudam um ambiente", "instagram_post", "lifestyle", "instagram", None, None),
    ("DAHMg-uXEvs", "Sementes de Bambu", "instagram_post", "lifestyle", "instagram", None, None),

    # ── EDUCACIONAL ──────────────────────────────────────────────────────────
    ("DAHMrBY8x9I", "Decoração Wabi-Sabi (Pin)", "pinterest_pin", "educacional", "pinterest", None, None),
    ("DAHMrCzbHI0", "5 Elementos Transformadores (Pin)", "pinterest_pin", "educacional", "pinterest", None, None),
    ("DAHMrfZYQMg", "Como criar um canto Japandi (Pin)", "pinterest_pin", "educacional", "pinterest", None, None),
    ("DAHMrHeQ-lQ", "A imperfeição (Pin)", "pinterest_pin", "educacional", "pinterest", None, None),
    ("DAHMrIVL0bA", "Como usar difusor de varetas em casa (Pin)", "pinterest_pin", "educacional", "pinterest", None, None),

    # ── STORY / STORIES ──────────────────────────────────────────────────────
    ("DAHLwpvQfXg", "Aura Decore (Story)", "story", "lifestyle", "instagram_story", None, None),
    ("DAHLkTTiKi0", "Story Japandi Decoração", "story", "lifestyle", "instagram_story", None, None),
    ("DAHLka8m1kQ", "Story Promo Coleção Inverno 2026", "story", "lifestyle", "instagram_story", None, None),
    ("DAHLkViUzZs", "Post Feed Japandi 1080x1080", "instagram_post", "lifestyle", "instagram", None, None),
    ("DAHLkUoPFEY", "Story Busca Decoração Japandi", "story", "lifestyle", "instagram_story", None, None),
    ("DAHLw3vXNZA", "Post Instagram com decoração Japandi", "instagram_post", "lifestyle", "instagram", None, None),
]

# Designs em inglês — EXCLUÍDOS do calendário
DESIGNS_ENGLISH = [
    "DAHMWGPwevo",   # Serene Elegance
    "DAHMrD8cpRc",   # Elevate your space...
    "DAHMrHOdUc4",   # Aromas that Define Your Home
    "DAHMrNh-vus",   # Embrace your home
    "DAHMqxRaA0M",   # Japandi-Inspired Serenity for Your Home
    "DAHMrWcsCcU",   # Embrace Neutral Spaces
    "DAHMrI9kExc",   # Candle Collection (Pin)
    "DAHMrIJr8g0",   # Japandi Room Styling (Pin)
    "DAHMrJK1qek",   # Luxurious Gift Set (Pin)
    "DAHLul2nNMI",   # Cedar Sandalwood
    "DAHLunx52ms",   # Natural Comfort
    "DAHLuw9wayk",   # Minimalist Tray
    "DAHLujwh-rw",   # Embrace serene beauty at home
    "DAHLuwOlf-k",   # Find tranquility in the simple moments...
    "DAHMhws9fXI",   # Japandi Minimalist Decor (FB)
    "DAHLkfp_fR8",   # Brown Japandi Style Kitchen (Story)
    "DAHLkRQZVhg",   # Minimalist Japandi Visual Interior Design (Pin)
    "DAHMrAuaqNE",   # Ritual Kit
    "DAHMrVzHYp0",   # Serenity
    "DAHMrFC_YHU",   # Aura Decore Candle Collection
    "DAHMrE8T6Jg",   # Timeless Natural Beauty
    "DAHMrHbs6SQ",   # Aura Decore Presents: Cantos que Curam
    "DAHMrAZDvpA",   # Pampas Grass & Dried Plants
    "DAHMrAZDvpA",   # mixed
]


def init_db():
    """Cria o banco de dados SQLite com todas as tabelas."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS designs (
            id TEXT PRIMARY KEY,
            titulo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            canal_primario TEXT NOT NULL,
            serie TEXT,
            episodio INTEGER,
            idioma TEXT DEFAULT 'pt-br',
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS publicacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            design_id TEXT NOT NULL,
            canal TEXT NOT NULL,
            data_agendada TEXT NOT NULL,
            hora TEXT DEFAULT '09:00',
            publicado INTEGER DEFAULT 0,
            publicado_em TEXT,
            post_id TEXT,
            erro TEXT,
            FOREIGN KEY (design_id) REFERENCES designs(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS recorrencia_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            design_id TEXT NOT NULL,
            canal TEXT NOT NULL,
            data_publicacao TEXT NOT NULL,
            exposicao_numero INTEGER DEFAULT 1,
            FOREIGN KEY (design_id) REFERENCES designs(id)
        )
    """)

    # Inserir designs
    for d in DESIGNS_PTBR:
        c.execute("""
            INSERT OR REPLACE INTO designs (id, titulo, tipo, categoria, canal_primario, serie, episodio)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, d)

    conn.commit()
    conn.close()
    print(f"✅ Banco criado: {DB_PATH}")
    print(f"   {len(DESIGNS_PTBR)} designs PT-BR cadastrados")
    print(f"   {len(DESIGNS_ENGLISH)} designs em inglês EXCLUÍDOS")


def gerar_calendario(dias: int = 90, inicio: date = None):
    """
    Gera calendário de publicação com espaçamento neurológico.
    Regras:
    - Mesmo design não aparece em <7 dias no mesmo canal
    - Séries em ordem de episódio com 5-7 dias de intervalo
    - Produtos rotacionam semanalmente
    - Pinterest: 3x/semana
    - Instagram/FB: 1x/dia cada
    """
    if inicio is None:
        inicio = date.today() + timedelta(days=1)

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Limpar agendamentos futuros não publicados
    c.execute("DELETE FROM publicacoes WHERE publicado=0 AND data_agendada >= ?", (inicio.isoformat(),))

    designs = c.execute("SELECT id, titulo, tipo, categoria, canal_primario, serie, episodio FROM designs").fetchall()

    # Separar por tipo
    series      = [d for d in designs if d[3] == "serie"]
    produtos    = [d for d in designs if d[3] == "produto"]
    lifestyle   = [d for d in designs if d[3] == "lifestyle"]
    educacional = [d for d in designs if d[3] == "educacional"]
    stories     = [d for d in designs if d[2] == "story"]
    pins        = [d for d in designs if d[4] == "pinterest"]

    agendamentos = []
    last_design_por_canal = {}  # design_id -> última data no canal

    def pode_agendar(design_id, canal, data_alvo):
        key = f"{design_id}:{canal}"
        last = last_design_por_canal.get(key)
        if last is None:
            return True
        return (data_alvo - last).days >= 7

    def agendar(design_id, canal, data_alvo, hora="09:00"):
        key = f"{design_id}:{canal}"
        if pode_agendar(design_id, canal, data_alvo):
            agendamentos.append((design_id, canal, data_alvo.isoformat(), hora))
            last_design_por_canal[key] = data_alvo
            return True
        return False

    # Índices rotativos
    idx_serie      = 0
    idx_produto    = 0
    idx_lifestyle  = 0
    idx_educacional = 0
    idx_story      = 0
    idx_pin        = 0

    for i in range(dias):
        data = inicio + timedelta(days=i)
        weekday = data.weekday()  # 0=Seg, 6=Dom

        # ── Instagram: 1 post/dia (alternando) ──────────────────────────────
        pool_ig = series + produtos + lifestyle + educacional
        pool_ig_filtered = [d for d in pool_ig if d[2] in ("instagram_post",)]
        if pool_ig_filtered:
            # Rotação baseada no dia
            idx = i % len(pool_ig_filtered)
            design = pool_ig_filtered[idx]
            hora_ig = "09:00" if weekday < 5 else "10:00"
            agendar(design[0], "instagram", data, hora_ig)

        # ── Facebook Comercial: 1 post/dia ───────────────────────────────────
        pool_fb = [d for d in designs if d[4] in ("facebook", "instagram") and d[2] in ("instagram_post", "facebook_post")]
        if pool_fb:
            idx = (i + 3) % len(pool_fb)  # offset para não ser o mesmo que IG
            design = pool_fb[idx]
            agendar(design[0], "facebook", data, "18:00")

        # ── Facebook Pessoal: 2x/semana (Ter, Sex) ───────────────────────────
        if weekday in (1, 4):
            pool_fbp = lifestyle + series
            pool_fbp_f = [d for d in pool_fbp if d[2] == "instagram_post"]
            if pool_fbp_f:
                idx = (i // 2) % len(pool_fbp_f)
                design = pool_fbp_f[idx]
                agendar(design[0], "facebook_pessoal", data, "19:00")

        # ── Pinterest: 3x/semana (Seg, Qua, Sab) ────────────────────────────
        if weekday in (0, 2, 5):
            pool_pin = [d for d in designs if d[4] == "pinterest" or d[2] == "pinterest_pin"]
            if pool_pin:
                idx = (i // 3) % len(pool_pin) if pool_pin else 0
                design = pool_pin[idx % len(pool_pin)]
                agendar(design[0], "pinterest", data, "14:00")

        # ── Stories: 3x/semana (Seg, Qua, Sex) ───────────────────────────────
        if weekday in (0, 2, 4) and stories:
            idx = (i // 3) % len(stories)
            design = stories[idx]
            agendar(design[0], "instagram_story", data, "08:00")

    # Inserir no banco
    c.executemany("""
        INSERT INTO publicacoes (design_id, canal, data_agendada, hora)
        VALUES (?, ?, ?, ?)
    """, agendamentos)

    conn.commit()
    total = len(agendamentos)
    conn.close()
    print(f"✅ Calendário gerado: {total} publicações agendadas")
    print(f"   Período: {inicio} → {inicio + timedelta(days=dias)}")
    print(f"   Média: {total/dias:.1f} posts/dia")


def status():
    """Mostra status do banco e próximas publicações."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    total_designs = c.execute("SELECT COUNT(*) FROM designs").fetchone()[0]
    total_agendados = c.execute("SELECT COUNT(*) FROM publicacoes WHERE publicado=0").fetchone()[0]
    total_publicados = c.execute("SELECT COUNT(*) FROM publicacoes WHERE publicado=1").fetchone()[0]

    print("=" * 60)
    print("  AURA DECORE — Calendário de Publicações Canva")
    print("=" * 60)
    print(f"  Designs PT-BR cadastrados: {total_designs}")
    print(f"  Posts agendados (pendentes): {total_agendados}")
    print(f"  Posts publicados: {total_publicados}")

    # Por canal
    print("\n  Por canal (agendados):")
    for row in c.execute("""
        SELECT canal, COUNT(*) as total FROM publicacoes
        WHERE publicado=0 GROUP BY canal ORDER BY total DESC
    """):
        print(f"    {row[0]:<20} {row[1]:>4} posts")

    # Próximos 7 dias
    hoje = date.today().isoformat()
    proxima = (date.today() + timedelta(days=7)).isoformat()
    print(f"\n  Próximos 7 dias ({hoje} → {proxima}):")
    for row in c.execute("""
        SELECT p.data_agendada, p.hora, p.canal, d.titulo
        FROM publicacoes p JOIN designs d ON p.design_id = d.id
        WHERE p.publicado=0 AND p.data_agendada BETWEEN ? AND ?
        ORDER BY p.data_agendada, p.hora
        LIMIT 20
    """, (hoje, proxima)):
        print(f"    {row[0]} {row[1]} [{row[2]:<18}] {row[3][:45]}")

    conn.close()


def get_posts_hoje() -> list:
    """Retorna publicações agendadas para hoje (usado pelo social_agent.py)."""
    hoje = date.today().isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    rows = c.execute("""
        SELECT p.id, p.design_id, p.canal, p.hora, d.titulo, d.tipo
        FROM publicacoes p JOIN designs d ON p.design_id = d.id
        WHERE p.data_agendada = ? AND p.publicado = 0
        ORDER BY p.hora
    """, (hoje,)).fetchall()
    conn.close()
    return [{"pub_id": r[0], "design_id": r[1], "canal": r[2], "hora": r[3],
             "titulo": r[4], "tipo": r[5]} for r in rows]


def marcar_publicado(pub_id: int, post_id: str = "", erro: str = ""):
    """Marca uma publicação como realizada."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    ok = 0 if erro else 1
    c.execute("""
        UPDATE publicacoes SET publicado=?, publicado_em=?, post_id=?, erro=?
        WHERE id=?
    """, (ok, datetime.now().isoformat(), post_id, erro, pub_id))
    conn.commit()
    conn.close()


def get_design_export_url(design_id: str) -> str:
    """Retorna a URL de edição do design no Canva."""
    return f"https://www.canva.com/design/{design_id}/edit"


def listar_designs():
    """Lista todos os designs cadastrados."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    print("=" * 70)
    print(f"  DESIGNS PT-BR AURA DECORE — {len(DESIGNS_PTBR)} total")
    print("=" * 70)
    for cat in ["serie", "produto", "lifestyle", "educacional"]:
        rows = c.execute(
            "SELECT id, titulo, tipo, canal_primario, serie FROM designs WHERE categoria=? ORDER BY serie, titulo",
            (cat,)
        ).fetchall()
        if rows:
            print(f"\n  [{cat.upper()}] {len(rows)} designs:")
            for r in rows:
                serie = f" [{r[4]}]" if r[4] else ""
                print(f"    {r[0]}  {r[2]:<16}  {r[1][:40]}{serie}")
    conn.close()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "status"
    if arg == "init":
        init_db()
    elif arg == "calendar":
        init_db()
        gerar_calendario(dias=90)
        status()
    elif arg == "status":
        if not DB_PATH.exists():
            print("⚠️  Banco não existe. Execute: python canva_design_db.py init")
        else:
            status()
    elif arg == "next":
        posts = get_posts_hoje()
        print(f"Posts de hoje ({date.today()}): {len(posts)}")
        for p in posts:
            print(f"  {p['hora']} [{p['canal']}] {p['titulo'][:50]}")
    elif arg == "list":
        if not DB_PATH.exists():
            init_db()
        listar_designs()
    else:
        print(f"Uso: python canva_design_db.py [init|calendar|status|next|list]")
