# Aura Decore — Motion Layer: Guia de Implementação

**Responsável:** THEO (Shopify técnico) · Revisão visual: LUNA  
**Stack:** GSAP 3.12 + ScrollTrigger + CSS puro  
**Tema Shopify:** Dawn (compatível com qualquer versão)

---

## Arquivos entregues

| Arquivo | Destino no Shopify |
|---------|-------------------|
| `aura-animations.css` | `assets/aura-animations.css` |
| `aura-animations.js`  | `assets/aura-animations.js`  |
| `theme-liquid-snippet.html` | Conteúdo a colar em `layout/theme.liquid` |

---

## Passo a passo — 5 minutos

### 1. Upload dos arquivos CSS e JS

1. Shopify Admin → **Online Store → Themes**
2. Clique em **⋯ → Edit code** no tema ativo
3. Na barra lateral esquerda, clique em **Assets**
4. Clique em **Add a new asset** → upload `aura-animations.css`
5. Repita para `aura-animations.js`

---

### 2. Injetar na `theme.liquid`

1. Ainda em **Edit code**, abra `layout/theme.liquid`
2. Encontre a linha `</head>`
3. Cole o conteúdo de `theme-liquid-snippet.html` **imediatamente antes** de `</head>`

```html
  <!-- Cole aqui o conteúdo de theme-liquid-snippet.html -->
</head>
```

4. Clique em **Save**

---

### 3. Verificação rápida

Abra a loja em aba anônima e confirme:

- [ ] Cursor customizado visível no desktop (ponto âmbar + anel)
- [ ] Header encolhe e ganha blur ao rolar a página
- [ ] Cards de produto fazem tilt 3D ao hover
- [ ] Imagem do produto dá zoom suave ao hover
- [ ] Banner médio apareceu entre a 2ª e 3ª seção
- [ ] Seções animam ao entrar no viewport (fade + slide)
- [ ] Botões têm efeito ripple ao clicar
- [ ] No mobile: cursor desativado, animações leves apenas

---

## O que cada módulo faz

### Módulo 1 — Custom Cursor
Cursor customizado elegante com ponto âmbar e anel de tracking. Reage ao hover (expande) e ao click (encolhe). **Desativado em mobile/touchscreen automaticamente.**

### Módulo 2 — Header Scroll
Após 80px de scroll, o header ativa `header--scrolled` com:
- Padding reduzido
- `backdrop-filter: blur(18px)` (vidro fosco)
- Sombra suave

### Módulo 3 — Hero Parallax
- Imagem de fundo move 28% mais lento que o scroll (efeito profundidade)
- Mouse move a imagem ±14px nos eixos X/Y
- Textos do hero entram com stagger 0.18s cada

### Módulo 4 — Banner Médio Dinâmico
Inserido automaticamente entre a 2ª e 3ª seção da homepage. Contém:
- Parallax no background ao scroll
- Mouse parallax dentro do banner
- Texto animado ao entrar no viewport
- CTA com efeito curtain + ripple

**Para personalizar o texto:** edite as strings em `aura-animations.js` → `function initMidBanner()`:
- `aura-mid-banner__eyebrow` — sobretítulo
- `aura-mid-banner__title` — título principal
- `aura-mid-banner__subtitle` — subtítulo
- `href="/collections/all"` — link do botão

**Para trocar a imagem de fundo:** o script usa a imagem do hero automaticamente como fallback. Para forçar uma imagem específica, substitua o `bgUrl` em `initMidBanner()` por uma URL fixa.

### Módulo 5 — Scroll Reveal
`IntersectionObserver` adiciona `.aura-reveal--visible` quando elementos entram no viewport. Funciona em cards, grid, colunas, footer — sem JavaScript extra por elemento.

### Módulo 6 — Card 3D Hover
Mouse sobre o card cria inclinação 3D suave (máx. 8°). Ao sair, volta com efeito elástico.

### Módulo 7 — Button Ripple
Clique em qualquer botão cria ondas de luz partindo do ponto do click.

### Módulo 8 — Seções GSAP
ScrollTrigger controla:
- Headings de seção (fade-up)
- Grids de produto (stagger horizontal)
- Image-with-text (entrada split esquerda/direita)
- Rich text / multicolumn (stagger por item)

### Módulo 9 — Footer
Colunas do rodapé entram em stagger ao aparecer no viewport. Links têm sublinhado animado.

### Módulo 10 — Breathing
Ícones de confiança e badges têm animação de "respiração" orgânica contínua.

---

## Customizações comuns

### Alterar cores do cursor
Em `aura-animations.css`, seção `Custom Cursor`:
```css
.aura-cursor { background: rgba(180, 155, 120, 0.9); /* cor âmbar Aura */ }
.aura-cursor-ring { border: 1.5px solid rgba(180, 155, 120, 0.35); }
```

### Ajustar força do parallax do hero
Em `aura-animations.js` → `initHeroParallax()`:
```js
const STRENGTH = 14; // reduzir para efeito mais sutil
gsap.to(bg, { yPercent: 28, ... }); // reduzir 28 para parallax menos agressivo
```

### Desativar o cursor customizado
Em `aura-animations.css`, comente/remova:
```css
/* * { cursor: none !important; } */
```
E em `aura-animations.js`, remova a chamada `initCursor();`

### Adicionar classes manualmente a elementos
Para forçar animação em qualquer elemento:
```html
<div class="aura-reveal">Conteúdo aparece ao scroll</div>
<div class="aura-reveal aura-reveal--left">Vem da esquerda</div>
<div class="aura-breathe">Elemento que respira</div>
```

---

## Performance

| Técnica | Impacto |
|---------|---------|
| `will-change: transform` apenas onde necessário | ✅ Compositor GPU sem thrashing |
| `passive: true` em scroll listeners | ✅ Sem bloqueio de UI thread |
| `IntersectionObserver` em vez de scroll events para reveal | ✅ Zero custo fora do viewport |
| Animações CSS pesadas desativadas no mobile (`max-width: 749px`) | ✅ Mobile first |
| `prefers-reduced-motion` respeitado | ✅ Acessibilidade |
| GSAP com `defer` e CDN com cache longo | ✅ Não bloqueia LCP |
| `ScrollTrigger.refresh()` após boot | ✅ Evita posicionamento errado |

---

## Créditos

- **THEO** — arquitetura técnica, integração Shopify, GSAP
- **LUNA** — parâmetros de easing, timing, feeling da marca
- **GSAP** 3.12.5 by GreenSock (licença free para Shopify)
