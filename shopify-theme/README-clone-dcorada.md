# 🪴 Aura Decore — Clone Estrutural Dcorada
> Layout 1:1 com a Dcorada · Identidade Japandi da Aura

---

## 📐 Estrutura de Páginas Criada

Replica **exatamente** a estrutura de páginas da Dcorada, mas com:
- **Paleta Japandi**: offwhite `#F0EAE0`, gold `#B8976A`, charcoal `#2D2D2D`
- **Tipografia**: Cormorant Garamond (headings) + Inter (UI/body)
- **Conceito**: Minimalismo luxuoso vs. Náutico colorido

---

## 🗂 Arquivos Criados

### Seções (`/sections/`)
| Arquivo | Equivalente na Dcorada | Descrição |
|---|---|---|
| `aura-barra-social.liquid` | `.barra-inicial` | Barra com redes sociais, fale conosco, telefone e WhatsApp |
| `aura-banner-slider.liquid` | `.flexslider` banner cheio | Slider de banners fullwidth com Splide.js |
| `aura-mini-banners.liquid` | `.banner.mini-banner` 3 col | 3 mini banners em grid abaixo do slider principal |
| `aura-vitrine-carrossel.liquid` | `.produtos-carrossel` | Vitrine de produtos em carrossel (4 cards/linha) |
| `aura-categorias-grid.liquid` | Menu visual por categoria | Grid de categorias com imagem circular |
| `aura-garantias.liquid` | Selos de confiança no rodapé | Barra horizontal com ícones de benefícios |
| `aura-instagram.liquid` | Widget SnapWidget | Feed do Instagram (SnapWidget ou grade manual) |

### Assets (`/assets/`)
| Arquivo | Descrição |
|---|---|
| `aura-dcorada-clone.css` | CSS global completo — todos os componentes estilizados na identidade Aura |

### Template
| Arquivo | Descrição |
|---|---|
| `templates/index.json` | Home page completa, ordem das seções definida |

---

## 📋 Ordem das Seções na Home Page

```
┌──────────────────────────────────────────────────┐
│  ANNOUNCEMENT BAR  "Pague 10% no Pix"            │ ← já no Shopify (configurar no admin)
├──────────────────────────────────────────────────┤
│  HEADER + MENU                                   │ ← tema Dawn (configurar nav)
├──────────────────────────────────────────────────┤
│  1. aura-barra-social   ← redes / fale / tel    │
├──────────────────────────────────────────────────┤
│  2. aura-garantias      ← frete | seguro | pix  │
├──────────────────────────────────────────────────┤
│  3. aura-banner-slider  ← slider fullwidth       │
├──────────────────────────────────────────────────┤
│  4. aura-mini-banners   ← 3 banners em grid      │
├──────────────────────────────────────────────────┤
│  5. aura-vitrine        ← "Lançamentos"          │
├──────────────────────────────────────────────────┤
│  6. aura-vitrine        ← "Mais Vendidos"        │
├──────────────────────────────────────────────────┤
│  7. aura-categorias-grid                         │
├──────────────────────────────────────────────────┤
│  8. aura-vitrine        ← "Coleção Japandi"      │
├──────────────────────────────────────────────────┤
│  9. Depoimentos (seção existente)                │
├──────────────────────────────────────────────────┤
│ 10. aura-instagram      ← "Siga-nos Instagram"  │
├──────────────────────────────────────────────────┤
│ 11. Newsletter          ← cupom 1ª compra        │
├──────────────────────────────────────────────────┤
│  FOOTER                                          │ ← tema Dawn
└──────────────────────────────────────────────────┘
```

---

## 🚀 Como Fazer o Upload no Shopify

### Opção A — Shopify CLI (recomendado)
```bash
cd C:\Users\erick\aura-office-dashboard\shopify-theme
shopify theme push --store auradecore.myshopify.com
```

### Opção B — Upload manual pelo Admin
1. Acesse **Admin Shopify → Online Store → Themes**
2. No tema ativo, clique em **"..." → Edit code**
3. Faça upload/edite cada arquivo:
   - `sections/` → cole cada `.liquid`
   - `assets/aura-dcorada-clone.css` → upload do CSS
   - `templates/index.json` → substitua o conteúdo

---

## 🎨 Configurações de Cores no Shopify Admin

Após upload, configure no **Customize → Theme settings**:

| Configuração | Valor |
|---|---|
| Announcement bar background | `#B8976A` |
| Announcement bar text | `#FFFFFF` |
| Header background | `#FFFFFF` |
| Header text | `#1A1A1A` |
| Menu background | `#2D2D2D` |
| Button (primary) | `#B8976A` |
| Footer background | `#2D2D2D` |
| Footer text | `#F0EAE0` |

---

## 📝 Configurar Cada Seção (após subir)

### 1. Announcement Bar (já existe no Dawn)
- Texto: `"Pague com 10% de desconto no PIX"`
- Link: `/collections/all`

### 2. Aura Barra Social
- Adicionar URLs das redes sociais
- Telefone/WhatsApp da loja

### 3. Aura Banner Slider
- Adicionar 2-3 imagens **1920×600px**
- Dica: usar imagens da coleção Japandi com fundo neutro
- Vincular cada slide a uma coleção

### 4. Aura Mini Banners
- **3 imagens 600×400px** — uma por ambiente
- Sugestões: Sala / Almofadas & Têxteis / Vasos & Cerâmica

### 5. Aura Vitrines
- Selecionar a **coleção** em cada vitrine nas configurações
- Vitrine 1 → coleção "lancamentos"
- Vitrine 2 → coleção "mais-vendidos"
- Vitrine 3 → coleção "japandi" ou "all"

### 6. Aura Instagram
- **Opção A** (recomendada): Criar conta no [SnapWidget](https://snapwidget.com), colar token
- **Opção B**: Adicionar 6 fotos manualmente nos blocos

---

## 🗺 Outras Páginas (equivalentes ao Dcorada)

### Página de Coleção (`/collections/[handle]`)
O CSS `aura-dcorada-clone.css` já estiliza:
- Grid de produtos
- Filtros laterais
- Ordenação
- Cards com hover + badge desconto
- Preço com riscado + cor Pix

### Página de Produto (`/products/[handle]`)
Já estilizado no CSS:
- Título com Cormorant Garamond
- Preço em gold `#B8976A`
- Botão "Adicionar ao carrinho" em gold
- Seletor de variante com borda gold

### Carrinho (`/cart`)
Estilizado no CSS com:
- Header em Cormorant Garamond
- Total em gold
- Botão checkout em gold

### Conta / Login (`/account`)
Formulários com inputs minimalistas, labels uppercase

---

## 🔧 Configurações de Menu (equivalente às categorias da Dcorada)

Criar no Shopify Admin → **Navigation → Main menu**:

```
- Todos os Produtos → /collections/all
- Sala de Estar → /collections/sala
  - Vasos → /collections/vasos
  - Almofadas → /collections/almofadas
  - Espelhos → /collections/espelhos
  - Luminárias → /collections/luminarias
- Quarto → /collections/quarto
- Cozinha → /collections/cozinha
- Banheiro → /collections/banheiro
- Jardim → /collections/jardim
- Velas & Aromas → /collections/velas
- Escritório → /collections/escritorio
```

---

## 💡 Diferenças Intencionais vs. Dcorada

| Feature | Dcorada | Aura Decore |
|---|---|---|
| Cor primária | Azul petróleo `#084d6e` | Gold Japandi `#B8976A` |
| Fontes | Oswald | Cormorant Garamond + Inter |
| Tema barra menu | Azul escuro | Charcoal `#2D2D2D` |
| Conceito | Náutico/Praia | Japandi/Minimalista |
| Plataforma | Loja Integrada | Shopify Dawn |

O **layout estrutural** é idêntico — a identidade visual é 100% Aura Decore.

---

## ✅ Checklist de Implementação

- [ ] Upload do `aura-dcorada-clone.css` para Assets
- [ ] Upload das 7 seções `.liquid` para Sections
- [ ] Atualizar `templates/index.json`
- [ ] Verificar injeção do CSS no `theme.liquid` (linha já adicionada)
- [ ] Configurar Announcement Bar com texto do Pix
- [ ] Adicionar imagens nos banners principais
- [ ] Adicionar imagens nos mini banners (3)
- [ ] Vincular vitrines às coleções corretas
- [ ] Configurar menu de navegação
- [ ] Configurar Instagram (SnapWidget ou fotos manuais)
- [ ] Testar mobile (375px) e desktop (1440px)
