/**
 * Aura Decore — Comprehensive Theme Upload Script
 * Uploads all modified assets, templates, layouts, and snippets to Shopify active theme
 */
const fs = require('fs');
const path = require('path');
const https = require('https');

const dir = __dirname;

// Load env from parent .env file
try {
  const envPath = path.join(dir, '..', 'backend', '.env');
  if (fs.existsSync(envPath)) {
    fs.readFileSync(envPath, 'utf8').split('\n').forEach(function(line) {
      line = line.trim();
      var m = line.match(/^([A-Z_0-9]+)=(.+)$/);
      if (m) process.env[m[1]] = m[2].trim().replace(/^["']|["']$/g, '');
    });
  }
} catch(e) {}

var THEME_ID = process.env.SHOPIFY_STAGING_THEME_ID || '160138428521';
if (!THEME_ID.startsWith('gid://')) {
  THEME_ID = 'gid://shopify/OnlineStoreTheme/' + THEME_ID;
}

var TOKEN = process.env.SHOPIFY_ADMIN_TOKEN || process.env.SHOPIFY_ACCESS_TOKEN || '';
var STORE = process.env.SHOPIFY_DOMAIN || 'aura-decor-17.myshopify.com';

if (!TOKEN) {
  console.error('ERROR: SHOPIFY_ADMIN_TOKEN not set');
  process.exit(1);
}

// List of files to upload
const filesToUpload = [
  { filename: 'layout/theme.liquid', localPath: 'layout/theme.liquid' },
  { filename: 'assets/aura-animations.css', localPath: 'aura-animations.css' },
  { filename: 'assets/aura-animations.js', localPath: 'aura-animations.js' },
  { filename: 'assets/aura-motion.css', localPath: 'assets/aura-motion.css' },
  { filename: 'assets/aura-motion.js', localPath: 'assets/aura-motion.js' },
  { filename: 'assets/aura-conversao.css', localPath: 'assets/aura-conversao.css' },
  { filename: 'assets/aura-conversao.js', localPath: 'assets/aura-conversao.js' },
  { filename: 'assets/aura-dcorada-clone.css', localPath: 'assets/aura-dcorada-clone.css' },
  { filename: 'assets/aura-decor-custom.css', localPath: 'assets/aura-decor-custom.css' },
  { filename: 'snippets/aura-urgency-badge.liquid', localPath: 'snippets/aura-urgency-badge.liquid' },
  { filename: 'snippets/aura-shipping-bar.liquid', localPath: 'snippets/aura-shipping-bar.liquid' },
  { filename: 'snippets/aura-sticky-cart.liquid', localPath: 'snippets/aura-sticky-cart.liquid' },
  { filename: 'snippets/aura-social-proof.liquid', localPath: 'snippets/aura-social-proof.liquid' },
  { filename: 'sections/header-group.json', localPath: 'sections/header-group.json' },
  { filename: 'sections/footer-group.json', localPath: 'sections/footer-group.json' },
  { filename: 'sections/aura-barra-social.liquid', localPath: 'sections/aura-barra-social.liquid' },
  { filename: 'sections/aura-whatsapp-float.liquid', localPath: 'sections/aura-whatsapp-float.liquid' },
  { filename: 'assets/aura-social.js', localPath: 'assets/aura-social.js' },
  { filename: 'sections/aura-banner-slider.liquid', localPath: 'sections/aura-banner-slider.liquid' },
  { filename: 'sections/aura-hero.liquid', localPath: 'sections/aura-hero.liquid' },
  { filename: 'sections/image-banner.liquid', localPath: 'sections/image-banner.liquid' },
  { filename: 'templates/index.json', localPath: 'templates/index.json' }
];

var MUTATION = `
  mutation themeFilesUpsert($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
    themeFilesUpsert(themeId: $themeId, files: $files) {
      upsertedThemeFiles { filename }
      userErrors { message field }
    }
  }
`;

function shopifyRequest(variables, label, cb) {
  var body = JSON.stringify({ query: MUTATION, variables: variables });
  var options = {
    hostname: STORE.replace(/^https?:\/\//, ''),
    path: '/admin/api/2025-01/graphql.json',
    method: 'POST',
    headers: {
      'Content-Type':  'application/json',
      'Content-Length': Buffer.byteLength(body),
      'X-Shopify-Access-Token': TOKEN,
    }
  };
  var req = https.request(options, function(res) {
    var data = '';
    res.on('data', function(c) { data += c; });
    res.on('end', function() {
      try {
        var json = JSON.parse(data);
        var result = (json.data || {}).themeFilesUpsert || {};
        var errors = result.userErrors || [];
        if (errors.length) {
          console.error(label, '❌ userErrors:', JSON.stringify(errors));
          cb(new Error(errors[0].message));
        } else {
          var upserted = (result.upsertedThemeFiles || []).map(function(f){ return f.filename; });
          console.log(label, '✅ uploaded:', upserted.join(', '));
          cb(null);
        }
      } catch(e) {
        console.error(label, '❌ parse error:', e.message, data.slice(0,200));
        cb(e);
      }
    });
  });
  req.on('error', function(e) { console.error(label, '❌ request error:', e.message); cb(e); });
  req.write(body);
  req.end();
}

// Upload sequentially
function uploadNext(index) {
  if (index >= filesToUpload.length) {
    console.log('\n🚀 ALL FILES UPLOADED SUCCESSFULLY TO THEME ID:', THEME_ID);
    return;
  }
  const item = filesToUpload[index];
  const fullLocalPath = path.join(dir, item.localPath);
  if (!fs.existsSync(fullLocalPath)) {
    console.error(`Local file not found: ${fullLocalPath}`);
    uploadNext(index + 1);
    return;
  }
  
  const content = fs.readFileSync(fullLocalPath, 'utf8');
  console.log(`Uploading ${item.filename} (${(content.length/1024).toFixed(1)} KB)...`);
  
  shopifyRequest({
    themeId: THEME_ID,
    files: [{ filename: item.filename, body: { type: 'TEXT', value: content } }]
  }, item.filename, function(err) {
    if (err) {
      console.error(`Failed to upload ${item.filename}`);
    }
    // Continue even on failure
    uploadNext(index + 1);
  });
}

console.log('🏪 Store:', STORE);
console.log('🎨 Theme ID:', THEME_ID);
console.log('Starting sequential upload...\n');
uploadNext(0);
