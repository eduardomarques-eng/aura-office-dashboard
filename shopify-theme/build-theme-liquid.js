const fs = require('fs');
const path = require('path');

// Read the original theme.liquid
const originalPath = path.join(__dirname, 'original-theme.liquid');

// We'll construct the modified version by replacing the injection point
// The original theme.liquid obtained from Shopify has \r\n line endings

const MOTION_SNIPPET = [
  '',
  "    <!-- ═══ Aura Decore Motion Layer ═══ -->",
  "    {{ 'aura-animations.css' | asset_url | stylesheet_tag }}",
  '    <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js" defer></script>',
  '    <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js" defer></script>',
  "    <script src=\"{{ 'aura-animations.js' | asset_url }}\" defer></script>",
  ''
].join('\r\n');

// Read if file exists, otherwise use the content we know
let original;
if (fs.existsSync(originalPath)) {
  original = fs.readFileSync(originalPath, 'utf8');
} else {
  // Fallback: read from the query result file we saved
  const queryResult = JSON.parse(fs.readFileSync(path.join(__dirname, 'theme-liquid-query.json'), 'utf8'));
  original = queryResult.content;
}

const CLOSE_HEAD = '\r\n  </head>';
const modified = original.replace(CLOSE_HEAD, MOTION_SNIPPET + CLOSE_HEAD);

const injected = modified.includes('aura-animations.css') && modified.includes('gsap');
const count = (modified.match(/aura-animations\.css/g) || []).length;

console.log('Original length:', original.length);
console.log('Modified length:', modified.length);
console.log('Injection present:', injected);
console.log('Injection count (should be 1):', count);

if (!injected || count !== 1) {
  console.error('INJECTION FAILED - aborting');
  process.exit(1);
}

// Save modified theme.liquid
fs.writeFileSync(path.join(__dirname, 'modified-theme.liquid'), modified, 'utf8');

// Save mutation payload
const payload = {
  themeId: 'gid://shopify/OnlineStoreTheme/142526644329',
  files: [{
    filename: 'layout/theme.liquid',
    body: { type: 'TEXT', value: modified }
  }]
};

fs.writeFileSync(path.join(__dirname, 'theme-liquid-vars.json'), JSON.stringify(payload), 'utf8');
console.log('Payload size (KB):', Math.round(JSON.stringify(payload).length / 1024));
console.log('SUCCESS');
