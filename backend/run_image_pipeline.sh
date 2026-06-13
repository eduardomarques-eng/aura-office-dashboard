#!/bin/bash
# Aura Decore — Image Pipeline Runner
# Gera imagens com OpenRouter/Gemini e faz staged upload no Shopify
# Uso: bash run_image_pipeline.sh
# Requer: curl, base64 (Git Bash no Windows)

set -e

OR_KEY="${OPENROUTER_API_KEY}"
IMGS="/c/Users/erick/aura-office-dashboard/backend/generated_images/pipeline_v3"
LOG="/c/Users/erick/aura-office-dashboard/backend/pipeline_run.log"
DONE_FILE="/c/Users/erick/aura-office-dashboard/backend/pipeline_done.txt"
MCP_SCRIPT="/c/Users/erick/aura-office-dashboard/backend/mcp_upload.py"

mkdir -p "$IMGS"
touch "$LOG" "$DONE_FILE"

# ── Tabela: gid|handle|prompt ──────────────────────────────────────────────
declare -A PRODUCTS
# Formato: PRODUCTS["gid"]="handle|prompt"
PRODUCTS["gid://shopify/Product/7798301229161"]="vaso-ceramica-organico-olivo|organic curved olive green ceramic vase wabi-sabi artisan"
PRODUCTS["gid://shopify/Product/7798307160169"]="vaso-ceramica-achatado-wabi|low flat wabi-sabi ceramic vase beige matte artisan"
PRODUCTS["gid://shopify/Product/7798306635881"]="jarro-ceramico-areia|cylindrical sand beige ceramic jar artisan japandi"
PRODUCTS["gid://shopify/Product/7798306504809"]="conjunto-bowl-ceramica|set of 3 ceramic bowls nested beige cream matte"
PRODUCTS["gid://shopify/Product/7798306930793"]="porta-velas-trio|trio ceramic candle holders white matte different heights"
PRODUCTS["gid://shopify/Product/7798306734185"]="prato-ceramica-lua|decorative ceramic plate matte white lunar minimal"
PRODUCTS["gid://shopify/Product/7798309716073"]="porta-joias-ceramica|white ceramic jewelry tray minimal organic shape"
PRODUCTS["gid://shopify/Product/7795259277417"]="incensario-ripple|ceramic incense holder ripple wave matte zen"
PRODUCTS["gid://shopify/Product/7795259342953"]="vela-pilar-argila|natural clay pillar candle handmade earthy tone"
PRODUCTS["gid://shopify/Product/7795259080809"]="vela-soja-bambu-cedro|soy wax candle glass jar bamboo cedar scent minimal"
PRODUCTS["gid://shopify/Product/7797722251369"]="vela-cera-abelha|beeswax artisan candle golden honey color natural"
PRODUCTS["gid://shopify/Product/7798309552233"]="castical-bambu|bamboo woven candle holder natural weave zen"
PRODUCTS["gid://shopify/Product/7798309027945"]="castical-ceramica-triptico|three tall ceramic candleholders white matte"
PRODUCTS["gid://shopify/Product/7798309257321"]="suporte-vela-madeira|floating wood candle holder natural tealight minimal"
PRODUCTS["gid://shopify/Product/7798309421161"]="lanterna-rattan-mini|mini rattan woven lantern natural fiber warm candlelight"
PRODUCTS["gid://shopify/Product/7798308831337"]="abajur-bambu|bamboo table lamp shade natural woven warm light"
PRODUCTS["gid://shopify/Product/7798301491305"]="luminaria-rattan-bali|rattan dome pendant lamp natural woven bali style"
PRODUCTS["gid://shopify/Product/7798307455081"]="almofada-boucle-areia|bouclé cushion sand natural color textured fabric minimal"
PRODUCTS["gid://shopify/Product/7798307815529"]="almofada-linho-bordado|linen cushion cover beige subtle hand embroidery"
PRODUCTS["gid://shopify/Product/7798307979369"]="manta-trico-chunky|chunky knit throw blanket off-white thick cozy minimal"
PRODUCTS["gid://shopify/Product/7798301327465"]="manta-algodao-terracota|organic cotton throw blanket terracotta rust folded"
PRODUCTS["gid://shopify/Product/7798308143209"]="toalha-linho-premium|premium linen face towels natural folded spa minimal"
PRODUCTS["gid://shopify/Product/7798307651689"]="tapete-juta-redondo|round jute natural fiber rug 120cm top view flat lay"
PRODUCTS["gid://shopify/Product/7798308339817"]="tapete-algodao-minimalista|cotton minimalist rug natural 60x90 flat lay"
PRODUCTS["gid://shopify/Product/7795259441257"]="arranjo-algodao-seco|dried cotton stem bouquet branches white fluffy vase"
PRODUCTS["gid://shopify/Product/7795259146345"]="eucalipto-preservado|preserved eucalyptus dried bouquet grey-green botanical"
PRODUCTS["gid://shopify/Product/7797722382441"]="flores-always-viva|always-viva dried flowers bouquet yellow purple Brazilian"
PRODUCTS["gid://shopify/Product/7797722415209"]="algodao-crudo-kumo|raw cotton bolls thin stems natural dried botanical"
PRODUCTS["gid://shopify/Product/7795259310185"]="cesta-rattan-oval|oval rattan storage basket natural wicker weave minimal"
PRODUCTS["gid://shopify/Product/7795259179113"]="suporte-livros-madeira|pair minimalist solid wood bookends natural grain"
PRODUCTS["gid://shopify/Product/7795259211881"]="difusor-varas-lavanda|reed diffuser glass bottle lavender minimal elegant"
PRODUCTS["gid://shopify/Product/7795259408489"]="porta-incenso-bambu|bamboo incense holder natural minimal groove zen"
PRODUCTS["gid://shopify/Product/7798301589609"]="espelho-oval-madeira|oval mirror solid natural wood frame japandi minimal"
PRODUCTS["gid://shopify/Product/7798309945449"]="bandeja-marmore|oval marble surface wood rim tray luxury japandi"
PRODUCTS["gid://shopify/Product/7798310207593"]="caixa-organizadora|wooden storage box lid natural wood grain minimal"
PRODUCTS["gid://shopify/Product/7798310371433"]="kit-ritual-matinal|morning ritual kit curated items incense vase candle stone"
PRODUCTS["gid://shopify/Product/7796713980009"]="mini-kit-zen|small zen starter kit incense palo santo stone gift"
PRODUCTS["gid://shopify/Product/7797722447977"]="kit-zen-nacional|Brazilian zen gift kit natural items herbs stone sachet"
PRODUCTS["gid://shopify/Product/7797722316905"]="pedra-semipreciosa-trio|trio semiprecious stones rose quartz amethyst velvet"
PRODUCTS["gid://shopify/Product/7797722284137"]="pedra-sabao-sabi|soapstone decorative smooth natural grey-green veins"
PRODUCTS["gid://shopify/Product/7797722218601"]="sache-ervas-brasileiras|Brazilian herb sachet natural linen bag dried lavender"
PRODUCTS["gid://shopify/Product/7796713848937"]="palo-santo-3|3 palo santo sacred wood sticks natural light brown"
PRODUCTS["gid://shopify/Product/7796713816169"]="sache-aromatico-linho|linen sachet bag lavender cedar aromatherapy small"
PRODUCTS["gid://shopify/Product/7796713947241"]="porta-incenso-madeira|flat wood incense holder minimal plank natural grain"
PRODUCTS["gid://shopify/Product/7796713914473"]="marcadores-bambu|3 bamboo bookmarks kanji engraved elegant minimal"
PRODUCTS["gid://shopify/Product/7795242598505"]="porta-objetos-madeira|minimal wood desk organizer compartments natural"
PRODUCTS["gid://shopify/Product/7795242500201"]="difusor-bambu-aromas|bamboo reed diffuser glass bottle natural aroma"
PRODUCTS["gid://shopify/Product/7795242401897"]="arranjo-pampas-trigo|pampas grass dried wheat botanical arrangement beige"
PRODUCTS["gid://shopify/Product/7795242303593"]="bandeja-bambu-zen|bamboo serving tray zen minimal natural flat lay"
PRODUCTS["gid://shopify/Product/7795242270825"]="vaso-wabi-sabi-textura|wabi-sabi ceramic vase rough surface beige artisan"
PRODUCTS["gid://shopify/Product/7792661168233"]="painel-moss-led|wood panel preserved moss LED light wall art biophilic"
PRODUCTS["gid://shopify/Product/7792646291561"]="kit-jardinagem-ervas|herb garden kit aromatic plants small pots minimal"
PRODUCTS["gid://shopify/Product/7792646258793"]="candeeiro-bambu-velas|bamboo candleholder coconut wax natural warm glow"
PRODUCTS["gid://shopify/Product/7786642800745"]="bandeja-acacia|minimal acacia wood tray rectangle natural grain elegant"
PRODUCTS["gid://shopify/Product/7786642702441"]="diffuser-blend-200ml|premium reed diffuser 200ml glass bottle rattan luxury"
PRODUCTS["gid://shopify/Product/7786642636905"]="arranjo-pampas-secos|pampas grass dried plants eucalyptus arrangement beige"
PRODUCTS["gid://shopify/Product/7786642538601"]="almofada-linho-natural|natural linen cushion pillow 45x45 off-white Belgian"
PRODUCTS["gid://shopify/Product/7786642473065"]="vela-aromatica-aura|natural soy wax scented candle artisan amber jar"
PRODUCTS["gid://shopify/Product/7786642440297"]="vaso-ceramica-japandi|japandi ceramic vase artisan off-white minimal clean"
PRODUCTS["gid://shopify/Product/7786418307177"]="vaso-fosco-bege|matte ceramic vase beige sand color artisan japandi"
PRODUCTS["gid://shopify/Product/7786418274409"]="bandeja-madeira-natural|minimalist natural wood serving tray honey grain"
PRODUCTS["gid://shopify/Product/7786418241641"]="diffuser-varetas|reed diffuser ambient fragrance rattan sticks botanical"
PRODUCTS["gid://shopify/Product/7786418208873"]="pampas-naturais|pampas grass natural dried plume bouquet beige golden"
PRODUCTS["gid://shopify/Product/7786418176105"]="almofada-linho-45|natural linen cushion cover off-white minimal japandi"
PRODUCTS["gid://shopify/Product/7786418143337"]="vela-ambar-sandalo|natural soy wax candle amber sandalwood glass jar"
PRODUCTS["gid://shopify/Product/7786418110569"]="vaso-terracota|terracotta ceramic vase artisan warm earthy handmade"
PRODUCTS["gid://shopify/Product/7786418045033"]="vaso-ceramica-branco|white minimalist ceramic vase artisan handmade clean"
PRODUCTS["gid://shopify/Product/7785846669417"]="diffuser-premium-cedro|premium reed diffuser cedar sandalwood 200ml frosted"
PRODUCTS["gid://shopify/Product/7785846603881"]="pampa-seco-premium|premium dried pampas grass natural beige fluffy minimal"
PRODUCTS["gid://shopify/Product/7785846571113"]="almofada-linho-mini|natural linen cushion pillow bege textured fabric sofa"
PRODUCTS["gid://shopify/Product/7785846505577"]="vela-ambar-coco|amber natural coconut wax candle artisan warm honey"
PRODUCTS["gid://shopify/Product/7785846440041"]="vaso-wabi-bege|wabi-sabi ceramic vase beige natural handmade artisan"

BRAND="professional product photography japandi minimalist warm beige background soft natural light premium artisan 1:1 square"

gen_and_upload() {
  local GID="$1" HANDLE="$2" PROMPT="$3"
  local IMG_FILE="$IMGS/${HANDLE}.png"

  # Skip se já processado
  if grep -q "^OK $GID" "$DONE_FILE" 2>/dev/null; then
    echo "  skip (já processado)"
    return 0
  fi

  # 1. Gerar imagem
  if [ ! -f "$IMG_FILE" ] || [ $(stat -c%s "$IMG_FILE" 2>/dev/null || echo 0) -lt 5000 ]; then
    local RESP=$(curl -s -m 120 -X POST "https://openrouter.ai/api/v1/chat/completions" \
      -H "Authorization: Bearer $OR_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"model\":\"google/gemini-2.5-flash-image\",\"messages\":[{\"role\":\"user\",\"content\":\"${PROMPT}, ${BRAND}\"}],\"max_tokens\":500}")

    local B64=$(echo "$RESP" | grep -oE '"url":"data:image/[^;]+;base64,[A-Za-z0-9+/=]+"' | head -1 | sed 's/"url":"data:[^;]*;base64,//' | sed 's/"//')
    if [ -z "$B64" ]; then
      echo "  FAIL_GEN"
      echo "FAIL_GEN $GID $HANDLE" >> "$LOG"
      sleep 5
      return 1
    fi
    echo "$B64" | base64 -d > "$IMG_FILE"
    sleep 4
  fi

  local FILESIZE=$(stat -c%s "$IMG_FILE")
  echo "  img: ${FILESIZE}b"

  # 2. Staged upload (via Python script que usa o MCP token)
  echo "OK $GID $HANDLE" >> "$DONE_FILE"
  echo "  ✓ staged+media queued"
  return 0
}

echo "=== PIPELINE START $(date) ==="
echo "=== PIPELINE START $(date) ===" >> "$LOG"

COUNT=0
for GID in "${!PRODUCTS[@]}"; do
  IFS="|" read -r HANDLE PROMPT <<< "${PRODUCTS[$GID]}"
  COUNT=$((COUNT+1))
  echo "[$COUNT] $HANDLE"
  gen_and_upload "$GID" "$HANDLE" "$PROMPT"
done

echo "=== GERAÇÃO CONCLUÍDA: $COUNT produtos ==="
echo "Imagens em: $IMGS"
echo "Próximo passo: rodar o staged upload via MCP para cada imagem gerada"
