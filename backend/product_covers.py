# -*- coding: utf-8 -*-
"""
product_covers.py — Capas branded Japandi para produtos sem foto — Aura Decore
Gera imagem 2048x2048 elegante por produto. Zero credencial externa.
"""
import os, sys, json, pathlib, textwrap, hashlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SIZE = 2048
OUT = pathlib.Path(__file__).parent / "product_images"
OUT.mkdir(exist_ok=True)
FONTS = "C:/Windows/Fonts"

# Paleta Japandi por categoria (fundo, acento, texto)
PALETTES = {
    "ceramica":  ("#EDE6DC", "#B07A52", "#3A352F"),  # terracota
    "vela":      ("#F0E8DD", "#C8954F", "#3A352F"),  # ambar
    "aroma":     ("#F0E8DD", "#C8954F", "#3A352F"),
    "difusor":   ("#F0E8DD", "#C8954F", "#3A352F"),
    "botanica":  ("#E8EAE0", "#7E8B6A", "#343A30"),  # sage
    "pampa":     ("#E8EAE0", "#7E8B6A", "#343A30"),
    "eucalipto": ("#E8EAE0", "#7E8B6A", "#343A30"),
    "flores":    ("#E8EAE0", "#7E8B6A", "#343A30"),
    "algodao":   ("#E8EAE0", "#7E8B6A", "#343A30"),
    "almofada":  ("#EFE9E0", "#B89B74", "#3A352F"),  # texteis sand
    "manta":     ("#EFE9E0", "#B89B74", "#3A352F"),
    "tapete":    ("#EFE9E0", "#B89B74", "#3A352F"),
    "toalha":    ("#EFE9E0", "#B89B74", "#3A352F"),
    "capa":      ("#EFE9E0", "#B89B74", "#3A352F"),
    "luminaria": ("#EDE4D6", "#9C7B4F", "#352F28"),  # iluminacao
    "abajur":    ("#EDE4D6", "#9C7B4F", "#352F28"),
    "lanterna":  ("#EDE4D6", "#9C7B4F", "#352F28"),
    "candeeiro": ("#EDE4D6", "#9C7B4F", "#352F28"),
    "castical":  ("#EDE4D6", "#9C7B4F", "#352F28"),
    "incenso":   ("#ECE6DB", "#8A7B66", "#34302A"),  # rituais
    "incensario":("#ECE6DB", "#8A7B66", "#34302A"),
    "palo":      ("#ECE6DB", "#8A7B66", "#34302A"),
    "sache":     ("#ECE6DB", "#8A7B66", "#34302A"),
    "pedra":     ("#E9E6E0", "#8E8madeira"[:7], "#343230") if False else ("#E9E6E0", "#8E867A", "#343230"),
    "bandeja":   ("#EAE3D7", "#9A7E58", "#352F28"),  # madeira
    "espelho":   ("#EAE3D7", "#9A7E58", "#352F28"),
    "cesta":     ("#EAE3D7", "#9A7E58", "#352F28"),
    "suporte":   ("#EAE3D7", "#9A7E58", "#352F28"),
    "caixa":     ("#EAE3D7", "#9A7E58", "#352F28"),
    "marcador":  ("#EAE3D7", "#9A7E58", "#352F28"),
    "kit":       ("#EDE6DC", "#B07A52", "#3A352F"),
    "porta":     ("#EAE3D7", "#9A7E58", "#352F28"),
    "vaso":      ("#EDE6DC", "#B07A52", "#3A352F"),
    "jarro":     ("#EDE6DC", "#B07A52", "#3A352F"),
    "bowl":      ("#EDE6DC", "#B07A52", "#3A352F"),
    "prato":     ("#EDE6DC", "#B07A52", "#3A352F"),
}
DEFAULT_PAL = ("#EDE6DC", "#A8845E", "#3A352F")


def hx(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))


def pick_palette(title: str):
    t = title.lower()
    for key, pal in PALETTES.items():
        if key in t:
            return pal
    return DEFAULT_PAL


def font(name, size):
    try:
        return ImageFont.truetype(f"{FONTS}/{name}", size)
    except Exception:
        return ImageFont.load_default()


def make_cover(title: str, handle: str) -> str:
    bg, accent, ink = [hx(c) for c in pick_palette(title)]
    img = Image.new("RGB", (SIZE, SIZE), bg)
    d = ImageDraw.Draw(img)

    # Moldura fina
    m = 90
    d.rectangle([m, m, SIZE - m, SIZE - m], outline=accent, width=3)

    # Círculo wabi-sabi (enso) decorativo no topo
    cx, cy, r = SIZE // 2, 720, 240
    d.arc([cx - r, cy - r, cx + r, cy + r], start=20, end=340, fill=accent, width=10)

    # Wordmark topo
    wf = font("georgia.ttf", 46)
    wm = "A U R A   D E C O R E"
    w = d.textlength(wm, font=wf)
    d.text(((SIZE - w) / 2, 200), wm, font=wf, fill=accent)

    # Título do produto (centro-baixo), serif, quebrado
    clean = title.split("|")[0].split("—")[0].strip()
    tf = font("georgia.ttf", 92)
    lines = textwrap.wrap(clean, width=18)[:3]
    ty = 1180
    for ln in lines:
        w = d.textlength(ln, font=tf)
        d.text(((SIZE - w) / 2, ty), ln, font=tf, fill=ink)
        ty += 120

    # Subtítulo
    sf = font("georgia.ttf", 44)
    sub = "Decoração Japandi · Feito com alma"
    w = d.textlength(sub, font=sf)
    d.text(((SIZE - w) / 2, ty + 30), sub, font=sf, fill=accent)

    # Linha + site no rodapé
    d.line([cx - 120, SIZE - 240, cx + 120, SIZE - 240], fill=accent, width=2)
    uf = font("georgia.ttf", 38)
    url = "auradecore.com.br"
    w = d.textlength(url, font=uf)
    d.text(((SIZE - w) / 2, SIZE - 200), url, font=uf, fill=ink)

    path = OUT / f"{handle}.jpg"
    img.save(path, "JPEG", quality=92)
    return str(path)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--samples":
        for t, h in [("Vaso Cerâmica Wabi — Bege Natural", "sample-vaso"),
                     ("Vela Artesanal de Soja — Bambu & Cedro", "sample-vela"),
                     ("Eucalipto Preservado — Buquê Seco", "sample-euca")]:
            print("✓", make_cover(t, h))
    else:
        # Lê lista de produtos de products.json {handle,title}
        pj = pathlib.Path(__file__).parent / "products.json"
        if pj.exists():
            prods = json.loads(pj.read_text(encoding="utf-8"))
            for p in prods:
                print("✓", make_cover(p["title"], p["handle"]))
            print(f"\nTotal: {len(prods)} capas geradas em {OUT}")
        else:
            print("products.json não encontrado — rode --samples para testar")
