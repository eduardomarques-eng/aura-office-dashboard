# -*- coding: utf-8 -*-
"""
Gerador diario de conteudo organico — Aura Decore (AUTONOMO)
Roda via Windows Task Scheduler todo dia 08h30.
- Gera 6 posts/dia (Reel, Story produto, Carrossel, 3 Stories) com tema rotativo
- Cria URL de imagem (Pollinations) + caption + hashtags
- Salva cada post formatado no vault Obsidian (pronto para publicar)
- Tenta publicar automaticamente via backend /social/post (funciona quando token FB valido)
- Loga tudo em organic_daily.log
"""
import os, sys, json, datetime, urllib.parse, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = "http://localhost:8000"
VAULT = r"C:\Users\erick\AURA-decor-vault\Redes Sociais\posts-prontos"
LOG = os.path.join(os.path.dirname(__file__), "organic_daily.log")
hoje = datetime.date.today()
doy = hoje.timetuple().tm_yday

def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] {msg}"
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def img(prompt, w, h, seed):
    enc = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{enc}?width={w}&height={h}&nologo=true&model=flux&seed={seed}"

REELS = [
    ("Como criar um canto zen com 3 objetos japandi", "cozy japandi corner shelf ceramic vase dried pampas candle minimal before after transformation"),
    ("5 erros de decoracao que deixam sua sala sem graca", "japandi living room common decor mistakes vs styled minimal editorial"),
    ("Antes e depois: prateleira comum vira curadoria", "shelf styling before after ceramic vase books candle plant japandi minimal"),
    ("O segredo das casas que parecem do Pinterest", "pinterest worthy japandi home interior natural light ceramic linen minimal"),
    ("Decoracao japandi para apartamento pequeno", "small apartment japandi decor compact minimal natural cozy"),
    ("Como combinar ceramica e botanica seca", "ceramic vase dried pampas botanical arrangement japandi styling minimal"),
    ("Tour pelo meu cantinho de leitura zen", "cozy reading nook japandi linen cushion wood shelf warm light minimal"),
]
PRODUTOS = [
    ("Vaso Ceramica Wabi-Sabi Bege Natural", "89,90", "wabi-sabi beige ceramic vase dried pampas minimal white background japandi"),
    ("Vela Aromatica Cera de Coco", "64,90", "coconut wax candle amber natural ceramic vessel warm minimal japandi"),
    ("Diffuser Premium Cedro & Sandalo 200ml", "129,90", "reed diffuser amber glass bottle rattan sticks minimal japandi white"),
    ("Pampa Seco Premium Natural", "47,90", "dried pampas grass bouquet natural beige minimal white background japandi"),
    ("Manta Trico Chunky Off White", "229,90", "chunky knit throw blanket off white cozy sofa minimal japandi"),
    ("Mini Kit Zen Starter", "49,90", "mini zen kit palo santo stones incense holder warm japandi cozy"),
    ("Luminaria Pendente Rattan Bali", "329,90", "rattan pendant lamp natural woven warm glow japandi minimal"),
]
DICAS = [
    ("A regra do impar: sempre 3 objetos na bandeja", "wooden tray three objects ceramic vase candle stone minimal japandi styled"),
    ("Como escolher o tamanho certo do vaso", "ceramic vases different sizes japandi proportion guide minimal"),
    ("Plantas secas duram anos e nao precisam de agua", "dried botanical pampas eucalyptus low maintenance japandi minimal"),
    ("O poder das texturas naturais na decoracao", "natural textures linen wood ceramic rattan japandi tactile minimal"),
    ("3 principios da decoracao japandi", "japandi design principles minimal natural neutral palette editorial"),
    ("Como criar camadas de luz aconchegante", "warm layered lighting candles lamp japandi cozy ambient minimal"),
    ("Paleta de cores neutras que sempre funciona", "neutral color palette beige terracotta sage japandi swatches minimal"),
]
BASTIDOR = [
    ("Como selecionamos cada peca da Aura", "behind scenes curating japandi home decor products selection flat lay warm light"),
    ("O cuidado na embalagem presente", "premium gift packaging wax seal tissue paper handwritten card japandi"),
    ("Conheca a filosofia wabi-sabi", "wabi-sabi imperfect ceramic handmade artisan japandi natural"),
    ("Por que escolhemos materiais sustentaveis", "sustainable natural materials bamboo linen ceramic rattan japandi eco"),
    ("Bastidor de um lancamento", "new product launch flat lay japandi decor selection editorial warm"),
]

def pick(lst):
    return lst[doy % len(lst)]

reel = pick(REELS); prod = pick(PRODUTOS); dica = pick(DICAS); bast = pick(BASTIDOR)
prod2 = PRODUTOS[(doy + 3) % len(PRODUTOS)]

posts = [
    {"tipo":"REEL", "hora":"09h", "rede":"Instagram Reel + Facebook",
     "img":img(reel[1], 1080, 1920, 80000+doy),
     "cap":f"{reel[0]}\n\nSem reformas. Sem gastanca. So intencao.\n\nLink na bio -> auradecore.com.br\n\n#JapandiDecor #WabiSabi #DecorMinimalista #CasaJapandi #AuraDecore #DecoracaoNatural #CantoZen #HomeInspo #CasaComAlma #DecorBoho #MinimalismoFuncional #InterioresNaturais #CasaMinimalista #DecoracaoConsciente #BemEstarEmCasa"},
    {"tipo":"STORY-PRODUTO", "hora":"12h", "rede":"Instagram Stories + Facebook",
     "img":img(prod[2], 1080, 1920, 81000+doy),
     "cap":f"Cada peca e unica. Como voce.\n\n{prod[0]}\nR$ {prod[1]}\nFrete gratis acima de R$ 299\n\nArrastar para cima -> auradecore.com.br"},
    {"tipo":"CARROSSEL", "hora":"14h", "rede":"Instagram Feed + Facebook",
     "img":img("japandi living room flat lay ceramic vase candle diffuser cushion wooden tray minimal editorial composition white background", 1080, 1080, 82000+doy),
     "cap":f"5 objetos que transformam qualquer sala\n\nSalve esse post para quando for decorar!\n\nTudo na Aura Decore -> auradecore.com.br\n\n#JapandiDecor #DecorMinimalista #CasaComAlma #WabiSabi #AuraDecore #HomeInspo #CasaJapandi #InterioresNaturais #MinimalismoFuncional #DecorNatural #InspireDeco #CasaMinimalista"},
    {"tipo":"STORY-DICA", "hora":"17h", "rede":"Instagram Stories",
     "img":img(dica[1], 1080, 1920, 83000+doy),
     "cap":f"{dica[0]}\n\nEsse truque de decorador funciona em qualquer estilo. Salve!"},
    {"tipo":"STORY-BASTIDOR", "hora":"19h", "rede":"Instagram Stories",
     "img":img(bast[1], 1080, 1920, 84000+doy),
     "cap":f"{bast[0]}\n\nResponde: qual o seu estilo?\nA) Japandi  B) Boho  C) Minimalista"},
    {"tipo":"STORY-CTA", "hora":"21h", "rede":"Instagram Stories + Facebook",
     "img":img(prod2[2] + " amber warm night cozy", 1080, 1920, 85000+doy),
     "cap":f"Ultima chance do dia!\n\n{prod2[0]}\nR$ {prod2[1]} — frete gratis hoje\n\nArrastar para cima -> auradecore.com.br"},
]

os.makedirs(VAULT, exist_ok=True)
log(f"=== Geracao diaria {hoje} (dia {doy}) ===")
salvos = 0
publicados = 0
for p in posts:
    nome = f"{hoje}-{p['tipo'].lower()}"
    conteudo = (
        f"# {p['tipo']} — {hoje}\n"
        f"**Horario:** {p['hora']} | **Rede:** {p['rede']}\n"
        f"**Status:** Pronto para publicar\n\n"
        f"## Imagem\n{p['img']}\n\n"
        f"## Caption\n{p['cap']}\n\n"
        f"---\n*Gerado automaticamente pelos agentes Aura Decore*\n"
    )
    try:
        with open(os.path.join(VAULT, nome + ".md"), "w", encoding="utf-8") as f:
            f.write(conteudo)
        salvos += 1
    except Exception as e:
        log(f"  ERRO ao salvar {nome}: {e}")
    try:
        data = json.dumps({"message": p["cap"], "image_url": p["img"],
                           "agent_id": "feed", "platform": "facebook"}).encode("utf-8")
        req = urllib.request.Request(f"{BASE}/social/post", data=data,
                                     headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=30)
        res = json.loads(resp.read().decode("utf-8"))
        if isinstance(res.get("result"), dict) and res["result"].get("id"):
            publicados += 1
            log(f"  PUBLICADO {p['tipo']}: {res['result']['id']}")
        else:
            log(f"  vault-only {p['tipo']} (token FB pendente)")
    except Exception as e:
        log(f"  vault-only {p['tipo']} (backend/token: {str(e)[:50]})")

log(f"=== {salvos}/6 salvos no vault | {publicados}/6 publicados nas redes ===")
print(f"\n{salvos} posts salvos | {publicados} publicados automaticamente")
