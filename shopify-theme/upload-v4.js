/**
 * Aura Decore — v4.0 Upload Script
 * Uploads aura-animations.css and aura-animations.js to Shopify staging theme
 */
const fs   = require('fs');
const path = require('path');
const https = require('https');

const dir = __dirname;

// Load env from parent .env file if available
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

var THEME_ID = process.env.SHOPIFY_STAGING_THEME_ID || '142526644329';
if (!THEME_ID.startsWith('gid://')) {
  THEME_ID = 'gid://shopify/OnlineStoreTheme/' + THEME_ID;
}

var TOKEN = process.env.SHOPIFY_ADMIN_TOKEN || process.env.SHOPIFY_ACCESS_TOKEN || '';
var STORE = process.env.SHOPIFY_DOMAIN || 'aura-decor-17.myshopify.com';

if (!TOKEN) {
  console.error('ERROR: SHOPIFY_ADMIN_TOKEN not set');
  process.exit(1);
}

var CSS = fs.readFileSync(path.join(dir, 'aura-animations.css'), 'utf8');
var JS  = fs.readFileSync(path.join(dir, 'aura-animations.js'),  'utf8');
var LIQUID = fs.readFileSync(path.join(dir, 'sections', 'aura-banner-slider.liquid'), 'utf8');

console.log('CSS size:', (CSS.length/1024).toFixed(1)+'KB');
console.log('JS  size:', (JS.length/1024).toFixed(1)+'KB');
console.log('LIQUID size:', (LIQUID.length/1024).toFixed(1)+'KB');

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
          console.error(label, 'userErrors:', JSON.stringify(errors));
        } else {
          var upserted = (result.upsertedThemeFiles || []).map(function(f){ return f.filename; });
          console.log(label, '✅ uploaded:', upserted.join(', '));
        }
        cb(null);
      } catch(e) {
        console.error(label, 'parse error:', e.message, data.slice(0,200));
        cb(e);
      }
    });
  });
  req.on('error', function(e) { console.error(label, 'request error:', e.message); cb(e); });
  req.write(body);
  req.end();
}

// Upload CSS, JS, and LIQUID sequentially (avoid concurrent large requests)
shopifyRequest({
  themeId: THEME_ID,
  files: [{ filename: 'assets/aura-animations.css', body: { type: 'TEXT', value: CSS } }]
}, 'CSS', function() {
  shopifyRequest({
    themeId: THEME_ID,
    files: [{ filename: 'assets/aura-animations.js', body: { type: 'TEXT', value: JS } }]
  }, 'JS', function() {
    shopifyRequest({
      themeId: THEME_ID,
      files: [{ filename: 'sections/aura-banner-slider.liquid', body: { type: 'TEXT', value: LIQUID } }]
    }, 'LIQUID', function() {
      console.log('\n🚀 v4.0 upload complete — 34 modules + Banner Slider live on staging theme');
    });
  });
});
