/* ==========================================================================
   Aura Decore — Social Integration
   WhatsApp Float + Facebook Pixel + Open Graph Helpers
   ========================================================================== */

(function() {
  'use strict';

  /* ============================================
     CONFIGURAÇÃO — atualize estes valores
  ============================================ */
  var CONFIG = {
    // WhatsApp: substitua pelo número real quando tiver
    whatsapp: '5585981957208', // formato: 55 + DDD + número
    whatsappMessage: 'Olá! Tenho interesse em um produto da Aura Decore 🌿',

    // Facebook Pixel ID — substitua pelo seu ID
    facebookPixelId: 'SEU_PIXEL_ID_AQUI',

    // Instagram
    instagram: 'auradecore',

    // Cor do botão WhatsApp
    whatsappColor: '#25D366'
  };

  /* ============================================
     1. WHATSAPP FLOATING BUTTON
     Aparece em todas as páginas, fácil de ver
  ============================================ */
  function initWhatsApp() {
    if (!CONFIG.whatsapp || CONFIG.whatsapp === '5511999999999') return;

    // Injeta CSS
    var style = document.createElement('style');
    style.textContent = [
      '.aura-whatsapp-btn {',
      '  position: fixed;',
      '  bottom: 2.4rem;',
      '  right: 2.4rem;',
      '  width: 6rem;',
      '  height: 6rem;',
      '  background: ' + CONFIG.whatsappColor + ';',
      '  border-radius: 50%;',
      '  display: flex;',
      '  align-items: center;',
      '  justify-content: center;',
      '  box-shadow: 0 4px 20px rgba(37,211,102,0.4);',
      '  z-index: 9998;',
      '  cursor: pointer;',
      '  text-decoration: none;',
      '  animation: waFloat 3s ease-in-out infinite;',
      '  transition: transform 0.3s ease, box-shadow 0.3s ease;',
      '}',
      '.aura-whatsapp-btn:hover {',
      '  transform: scale(1.12);',
      '  box-shadow: 0 8px 32px rgba(37,211,102,0.55);',
      '}',
      '.aura-whatsapp-btn svg { width: 3.2rem; height: 3.2rem; }',
      '.aura-whatsapp-tooltip {',
      '  position: absolute;',
      '  right: 7.6rem;',
      '  bottom: 50%;',
      '  transform: translateY(50%);',
      '  background: #2A2520;',
      '  color: white;',
      '  padding: 0.8rem 1.4rem;',
      '  border-radius: 4px;',
      '  font-size: 1.3rem;',
      '  white-space: nowrap;',
      '  opacity: 0;',
      '  pointer-events: none;',
      '  transition: opacity 0.3s ease;',
      '}',
      '.aura-whatsapp-btn:hover .aura-whatsapp-tooltip { opacity: 1; }',
      '@keyframes waFloat {',
      '  0%, 100% { transform: translateY(0); }',
      '  50% { transform: translateY(-6px); }',
      '}',
      '@media (max-width: 749px) {',
      '  .aura-whatsapp-btn { bottom: 1.6rem; right: 1.6rem; width: 5.6rem; height: 5.6rem; }',
      '}'
    ].join('');
    document.head.appendChild(style);

    // Cria botão
    var url = 'https://wa.me/' + CONFIG.whatsapp + '?text=' + encodeURIComponent(CONFIG.whatsappMessage);
    var btn = document.createElement('a');
    btn.href = url;
    btn.target = '_blank';
    btn.rel = 'noopener noreferrer';
    btn.className = 'aura-whatsapp-btn';
    btn.setAttribute('aria-label', 'Falar no WhatsApp');
    btn.innerHTML = [
      '<svg viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg">',
      '<path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>',
      '</svg>',
      '<span class="aura-whatsapp-tooltip">Fale conosco</span>'
    ].join('');

    document.body.appendChild(btn);

    // Track cliques
    btn.addEventListener('click', function() {
      if (typeof fbq !== 'undefined') fbq('track', 'Contact');
    });
  }

  /* ============================================
     2. FACEBOOK PIXEL
     PageView automático + eventos de produto
  ============================================ */
  function initFacebookPixel() {
    var pixelId = CONFIG.facebookPixelId;
    if (!pixelId || pixelId === 'SEU_PIXEL_ID_AQUI') return;

    // Carrega o pixel
    !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
    n.callMethod.apply(n,arguments):n.queue.push(arguments)};
    if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
    n.queue=[];t=b.createElement(e);t.async=!0;
    t.src=v;s=b.getElementsByTagName(e)[0];
    s.parentNode.insertBefore(t,s)}(window, document,'script',
    'https://connect.facebook.net/en_US/fbevents.js');

    fbq('init', pixelId);
    fbq('track', 'PageView');

    // Eventos de produto (se estiver em página de produto)
    var meta = document.querySelector('meta[property="og:type"]');
    if (meta && meta.content === 'product') {
      var price = document.querySelector('.price-item--regular');
      fbq('track', 'ViewContent', {
        content_type: 'product',
        currency: 'BRL',
        value: price ? parseFloat(price.textContent.replace(/[^0-9,]/g,'').replace(',','.')) : 0
      });
    }

    // Track Add to Cart
    document.addEventListener('click', function(e) {
      var btn = e.target.closest('[name="add"], .product-form__submit');
      if (btn) {
        fbq('track', 'AddToCart', { currency: 'BRL' });
      }
    });
  }

  /* ============================================
     3. SOCIAL SHARE BUTTONS nos artigos do blog
  ============================================ */
  function initBlogShare() {
    var shareContainer = document.querySelector('.article__share, .share');
    if (!shareContainer) return;

    var url = encodeURIComponent(window.location.href);
    var title = encodeURIComponent(document.title);

    var fbUrl = 'https://www.facebook.com/sharer/sharer.php?u=' + url;
    var waUrl = 'https://wa.me/?text=' + title + '%20' + url;

    var shareHtml = '<div class="aura-share-social" style="display:flex;gap:1.2rem;margin:2.4rem 0;">' +
      '<a href="' + fbUrl + '" target="_blank" rel="noopener" ' +
      'style="display:inline-flex;align-items:center;gap:0.8rem;background:#1877F2;color:white;' +
      'padding:0.8rem 1.6rem;text-decoration:none;font-size:1.3rem;font-weight:500;transition:opacity 0.2s"' +
      ' onmouseover="this.style.opacity=0.85" onmouseout="this.style.opacity=1">' +
      'Compartilhar no Facebook</a>' +
      '<a href="' + waUrl + '" target="_blank" rel="noopener" ' +
      'style="display:inline-flex;align-items:center;gap:0.8rem;background:#25D366;color:white;' +
      'padding:0.8rem 1.6rem;text-decoration:none;font-size:1.3rem;font-weight:500;transition:opacity 0.2s"' +
      ' onmouseover="this.style.opacity=0.85" onmouseout="this.style.opacity=1">' +
      'Enviar no WhatsApp</a>' +
      '</div>';

    shareContainer.insertAdjacentHTML('beforebegin', shareHtml);
  }

  /* ============================================
     4. OPEN GRAPH DYNAMIC — garante imagem correta
     no Facebook quando produto é compartilhado
  ============================================ */
  function ensureOGTags() {
    var ogImage = document.querySelector('meta[property="og:image"]');
    if (!ogImage) {
      // Pega a primeira imagem de produto visível
      var prodImg = document.querySelector('.product__media img, .card__media img');
      if (prodImg && prodImg.src) {
        var meta = document.createElement('meta');
        meta.setAttribute('property', 'og:image');
        meta.setAttribute('content', prodImg.src);
        document.head.appendChild(meta);
      }
    }

    // OG site name
    if (!document.querySelector('meta[property="og:site_name"]')) {
      var sn = document.createElement('meta');
      sn.setAttribute('property', 'og:site_name');
      sn.setAttribute('content', 'Aura Decore');
      document.head.appendChild(sn);
    }
  }

  /* ============================================
     INIT
  ============================================ */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      initWhatsApp();
      initFacebookPixel();
      initBlogShare();
      ensureOGTags();
    });
  } else {
    initWhatsApp();
    initFacebookPixel();
    initBlogShare();
    ensureOGTags();
  }

})();
