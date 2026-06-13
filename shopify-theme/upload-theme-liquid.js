/**
 * Aura Decore — Upload theme.liquid com integração Yampi
 * Uso: node upload-theme-liquid.js [THEME_ID]
 * THEME_ID padrão: staging (142526644329)
 */
const fs   = require('fs');
const path = require('path');
const https = require('https');

// Carrega .env
try {
  const envPath = path.join(__dirname, '..', 'backend', '.env');
  if (fs.existsSync(envPath)) {
    fs.readFileSync(envPath, 'utf8').split('\n').forEach(function(line) {
      line = line.trim();
      const m = line.match(/^([A-Z_0-9]+)=(.+)$/);
      if (m) process.env[m[1]] = m[2].trim().replace(/^["']|["']$/g, '');
    });
  }
} catch(e) {}

const TOKEN    = process.env.SHOPIFY_ADMIN_TOKEN || '';
const STORE    = process.env.SHOPIFY_DOMAIN      || 'aura-decor-17.myshopify.com';
const ARG_ID   = process.argv[2];
let THEME_ID = ARG_ID || process.env.SHOPIFY_STAGING_THEME_ID
               || '142526644329';
if (!THEME_ID.startsWith('gid://')) {
  THEME_ID = 'gid://shopify/OnlineStoreTheme/' + THEME_ID;
}

if (!TOKEN) {
  console.error('\n❌  SHOPIFY_ADMIN_TOKEN está vazio no .env');
  console.error('   Adicione o token e rode novamente: node upload-theme-liquid.js\n');
  process.exit(1);
}

const CONTENT = fs.readFileSync(path.join(__dirname, 'original-theme.liquid'), 'utf8');
console.log(`📦 theme.liquid: ${(CONTENT.length/1024).toFixed(1)} KB`);
console.log(`🏪 Store : ${STORE}`);
console.log(`🎨 Theme : ${THEME_ID}`);

const MUTATION = `
  mutation themeFilesUpsert($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
    themeFilesUpsert(themeId: $themeId, files: $files) {
      upsertedThemeFiles { filename }
      userErrors { message field }
    }
  }
`;

const body = JSON.stringify({
  query: MUTATION,
  variables: {
    themeId: THEME_ID,
    files: [{ filename: 'layout/theme.liquid', body: { type: 'TEXT', value: CONTENT } }]
  }
});

const options = {
  hostname: STORE.replace(/^https?:\/\//, ''),
  path: '/admin/api/2025-01/graphql.json',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(body),
    'X-Shopify-Access-Token': TOKEN,
  }
};

console.log('\n⏳ Enviando para Shopify...');
const req = https.request(options, function(res) {
  let data = '';
  res.on('data', c => data += c);
  res.on('end', function() {
    try {
      const json = JSON.parse(data);
      if (res.statusCode === 200 && json.data?.themeFilesUpsert) {
        const result = json.data.themeFilesUpsert;
        const errors = result.userErrors || [];
        if (errors.length) {
          console.error('❌ Erros:', JSON.stringify(errors, null, 2));
        } else {
          const files = (result.upsertedThemeFiles || []).map(f => f.filename);
          console.log('✅ Upload concluído:', files.join(', '));
          console.log('\n🎉 Yampi Checkout integrado ao tema Shopify!');
          console.log('   URL de checkout: https://pay.yampi.com.br/aura-decor2/checkout');
        }
      } else {
        console.error('❌ Resposta inesperada HTTP', res.statusCode, data.slice(0,300));
      }
    } catch(e) {
      console.error('❌ Erro parse:', e.message, data.slice(0,300));
    }
  });
});
req.on('error', e => console.error('❌ Erro de rede:', e.message));
req.write(body);
req.end();
