"""Gera os ícones PNG do PWA sem dependências externas."""
import struct, zlib, pathlib

def make_png(size: int) -> bytes:
    """Cria um PNG simples com fundo escuro e letra A dourada."""
    w = h = size
    # Cores
    bg   = (14, 12, 10)       # #0E0C0A
    card = (23, 20, 15)       # #17140F
    gold = (180, 148, 90)     # #B4945A
    bord = (46, 40, 32)       # #2E2820

    rows = []
    cx, cy = w // 2, h // 2

    # Raio do cartão arredondado
    r = size // 8
    pad = size // 16

    for y in range(h):
        row = []
        for x in range(w):
            # Dentro do card arredondado?
            lx, ly = x - pad, y - pad
            rw, rh = w - 2*pad, h - 2*pad
            in_card = (lx >= r and lx <= rw - r and 0 <= ly <= rh) or \
                      (ly >= r and ly <= rh - r and 0 <= lx <= rw) or \
                      ((lx-r)**2+(ly-r)**2 <= r**2) or \
                      ((lx-rw+r)**2+(ly-r)**2 <= r**2) or \
                      ((lx-r)**2+(ly-rh+r)**2 <= r**2) or \
                      ((lx-rw+r)**2+(ly-rh+r)**2 <= r**2)

            # Borda dourada do card
            border_w = max(2, size // 100)
            in_border = in_card
            lx2, ly2 = lx - border_w, ly - border_w
            rw2, rh2 = rw - 2*border_w, rh - 2*border_w
            r2 = max(r - border_w, 1)
            in_inner = (lx2 >= r2 and lx2 <= rw2 - r2 and 0 <= ly2 <= rh2) or \
                       (ly2 >= r2 and ly2 <= rh2 - r2 and 0 <= lx2 <= rw2) or \
                       ((lx2-r2)**2+(ly2-r2)**2 <= r2**2) or \
                       ((lx2-rw2+r2)**2+(ly2-r2)**2 <= r2**2) or \
                       ((lx2-r2)**2+(ly2-rh2+r2)**2 <= r2**2) or \
                       ((lx2-rw2+r2)**2+(ly2-rh2+r2)**2 <= r2**2)

            # Letra "A" — triângulo dourado centralizado
            fsize = size * 0.55
            ax1 = cx - fsize * 0.35
            ax2 = cx + fsize * 0.35
            ay1 = cy - fsize * 0.38
            ay2 = cy + fsize * 0.40
            stroke = max(2, size // 64)

            # Dois lados do A (linhas diagonais)
            # Lado esquerdo: (ax1,ay2) → (cx,ay1)
            def dist_to_seg(px,py,x1,y1,x2,y2):
                dx,dy=x2-x1,y2-y1
                t=max(0,min(1,((px-x1)*dx+(py-y1)*dy)/(dx*dx+dy*dy+1e-9)))
                return ((px-(x1+t*dx))**2+(py-(y1+t*dy))**2)**.5

            d_left  = dist_to_seg(x,y, ax1,ay2, cx,ay1)
            d_right = dist_to_seg(x,y, ax2,ay2, cx,ay1)
            # Barra horizontal do A
            bar_y = ay1 + fsize * 0.55
            bar_x1 = cx - fsize * 0.18
            bar_x2 = cx + fsize * 0.18
            in_bar = (abs(y - bar_y) <= stroke*0.8 and bar_x1 <= x <= bar_x2)
            in_letter = (d_left <= stroke or d_right <= stroke) or in_bar

            if in_letter and in_card:
                row += list(gold)
            elif in_border and not in_inner:
                row += list(bord)
            elif in_card:
                row += list(card)
            else:
                row += list(bg)

        rows.append(bytes([0] + row))  # filter byte = 0 (None)

    raw = b''.join(rows)
    compressed = zlib.compress(raw, 9)

    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        c += struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
        return c

    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)  # 8bit RGB
    png  = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', ihdr)
    png += chunk(b'IDAT', compressed)
    png += chunk(b'IEND', b'')
    return png

if __name__ == '__main__':
    root = pathlib.Path(__file__).parent
    for size, fname in [(192, 'pwa-icon-192.png'), (512, 'pwa-icon-512.png')]:
        data = make_png(size)
        (root / fname).write_bytes(data)
        print(f'✓ {fname} ({size}x{size}) — {len(data)} bytes')
    print('Icons gerados com sucesso.')
