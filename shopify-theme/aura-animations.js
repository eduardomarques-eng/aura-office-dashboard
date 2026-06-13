/* ════════════════════════════════════════════════════════════════
   Aura Decore — Premium Motion & Interactivity Engine v3.0 Pro Max
   THEO + LUNA · Aura Decore 2026
   ════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  function waitForGSAP(cb, tries) {
    tries = tries || 0;
    if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
      gsap.registerPlugin(ScrollTrigger);
      cb();
    } else if (tries < 80) {
      setTimeout(function () { waitForGSAP(cb, tries + 1); }, 100);
    }
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 1 — Custom Cursor + Trail de Partículas
  ══════════════════════════════════════════════════════════════ */
  var cursorDot, cursorRing;

  function initCursor() {
    if (window.matchMedia('(max-width: 749px)').matches) return;
    if (window.matchMedia('(pointer: coarse)').matches) return;

    cursorDot  = document.createElement('div');
    cursorRing = document.createElement('div');
    cursorDot.className  = 'aura-cursor';
    cursorRing.className = 'aura-cursor-ring';
    document.body.appendChild(cursorDot);
    document.body.appendChild(cursorRing);

    var mx = -100, my = -100, rx = -100, ry = -100;

    document.addEventListener('mousemove', function (e) {
      mx = e.clientX; my = e.clientY;
      gsap.set(cursorDot, { x: mx, y: my });
      spawnTrailParticle(mx, my);
    });

    gsap.ticker.add(function () {
      rx += (mx - rx) * 0.12; ry += (my - ry) * 0.12;
      gsap.set(cursorRing, { x: rx, y: ry });
    });

    /* Hover states */
    document.querySelectorAll('a, button, [role="button"], .card, input, textarea, select, label').forEach(function (el) {
      el.addEventListener('mouseenter', function () {
        cursorDot.classList.add('aura-cursor--hover');
        cursorRing.classList.add('aura-cursor-ring--hover');
      });
      el.addEventListener('mouseleave', function () {
        cursorDot.classList.remove('aura-cursor--hover');
        cursorRing.classList.remove('aura-cursor-ring--hover');
      });
    });

    /* Cursor grande sobre imagens de produto */
    document.querySelectorAll('.card__media img, .card-media img, .banner img, .hero img').forEach(function (img) {
      img.addEventListener('mouseenter', function () {
        cursorDot.classList.add('aura-cursor--image');
        cursorRing.classList.add('aura-cursor-ring--image');
      });
      img.addEventListener('mouseleave', function () {
        cursorDot.classList.remove('aura-cursor--image');
        cursorRing.classList.remove('aura-cursor-ring--image');
      });
    });

    document.addEventListener('mousedown', function () { cursorDot.classList.add('aura-cursor--click'); });
    document.addEventListener('mouseup',   function () { cursorDot.classList.remove('aura-cursor--click'); });
  }

  /* Trail de faíscas */
  var trailPool = [], trailIndex = 0, POOL_SIZE = 20;
  function buildTrailPool() {
    if (window.matchMedia('(max-width: 749px)').matches) return;
    if (window.matchMedia('(pointer: coarse)').matches) return;
    for (var i = 0; i < POOL_SIZE; i++) {
      var p = document.createElement('div');
      p.className = 'aura-trail-dot';
      document.body.appendChild(p);
      trailPool.push(p);
    }
  }
  var lastTrailTime = 0;
  function spawnTrailParticle(x, y) {
    if (!trailPool.length) return;
    var now = Date.now();
    if (now - lastTrailTime < 38) return;
    lastTrailTime = now;
    var p = trailPool[trailIndex % POOL_SIZE];
    trailIndex++;
    var size = 2.5 + Math.random() * 4;
    gsap.set(p, { x: x + (Math.random()-0.5)*8, y: y + (Math.random()-0.5)*8, width: size, height: size, opacity: 0.75, scale: 1 });
    gsap.to(p, { y: y - 18 - Math.random()*22, x: x + (Math.random()-0.5)*32, opacity: 0, scale: 0, duration: 0.65 + Math.random()*0.5, ease: 'power2.out' });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 2 — Scroll Progress Bar
  ══════════════════════════════════════════════════════════════ */
  function initScrollProgress() {
    var bar = document.createElement('div');
    bar.className = 'aura-scroll-progress';
    document.body.appendChild(bar);
    window.addEventListener('scroll', function () {
      var pct = window.scrollY / (document.documentElement.scrollHeight - window.innerHeight);
      bar.style.transform = 'scaleX(' + Math.min(pct, 1) + ')';
    }, { passive: true });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 3 — Floating CTA
  ══════════════════════════════════════════════════════════════ */
  function initFloatingCTA() {
    if (document.querySelector('.aura-float-cta')) return;

    var btn = document.createElement('a');
    btn.className = 'aura-float-cta';
    btn.href = '/collections/all';
    btn.setAttribute('aria-label', 'Explorar coleção');
    btn.innerHTML = '<span>Explorar coleção</span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>';
    document.body.appendChild(btn);

    /* Mostra após 30% scroll */
    window.addEventListener('scroll', function () {
      var pct = window.scrollY / (document.documentElement.scrollHeight - window.innerHeight);
      if (pct > 0.18) { btn.classList.add('aura-float-cta--visible'); }
      else             { btn.classList.remove('aura-float-cta--visible'); }
    }, { passive: true });

    /* Ripple no clique */
    btn.style.overflow = 'hidden';
    btn.addEventListener('click', function (e) {
      var rp = document.createElement('span'); rp.className = 'aura-ripple';
      var rect = btn.getBoundingClientRect(); var size = Math.max(rect.width, rect.height) * 2;
      rp.style.cssText = 'width:'+size+'px;height:'+size+'px;left:'+(e.clientX-rect.left-size/2)+'px;top:'+(e.clientY-rect.top-size/2)+'px;background:rgba(180,155,120,0.3);';
      btn.appendChild(rp); rp.addEventListener('animationend', function () { rp.remove(); });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 4 — Header Scroll + Magnetic Icons
  ══════════════════════════════════════════════════════════════ */
  function initHeader() {
    var header = document.querySelector('.header-wrapper, .site-header, header[role="banner"]');
    if (!header) return;

    window.addEventListener('scroll', function () {
      if (window.scrollY > 80) { header.classList.add('header--scrolled'); }
      else { header.classList.remove('header--scrolled'); }
    }, { passive: true });

    if (window.matchMedia('(max-width: 749px)').matches) return;
    header.querySelectorAll('.header__icon').forEach(function (icon) {
      icon.addEventListener('mousemove', function (e) {
        var rect = icon.getBoundingClientRect();
        gsap.to(icon, { x: (e.clientX-rect.left-rect.width/2)*0.38, y: (e.clientY-rect.top-rect.height/2)*0.38, duration: 0.3, ease: 'power2.out' });
      });
      icon.addEventListener('mouseleave', function () {
        gsap.to(icon, { x: 0, y: 0, duration: 0.5, ease: 'elastic.out(1, 0.5)' });
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 5 — Cart Badge Pulse
  ══════════════════════════════════════════════════════════════ */
  function initCartPulse() {
    var badge = document.querySelector('.cart-count-bubble, .header__cart-badge, .cart__icon-wrapper');
    if (!badge) return;

    /* Observa mudanças no DOM (item adicionado ao cart) */
    var lastCount = badge.textContent;
    new MutationObserver(function () {
      var newCount = badge.textContent;
      if (newCount !== lastCount && parseInt(newCount) > 0) {
        lastCount = newCount;
        badge.classList.remove('aura-cart-pulse');
        void badge.offsetWidth; /* reflow */
        badge.classList.add('aura-cart-pulse');
        setTimeout(function () { badge.classList.remove('aura-cart-pulse'); }, 3600);
      }
    }).observe(badge, { childList: true, characterData: true, subtree: true });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 6 — Hero: Zoom-in on Load + Parallax + Mouse
  ══════════════════════════════════════════════════════════════ */
  function initHeroParallax() {
    var hero = document.querySelector('.banner, .hero, [data-section-type="image-banner"], .slideshow, section.image-banner');
    if (!hero) return;

    hero.classList.add('hero-parallax-wrapper');
    var bg = hero.querySelector('img, .banner__media, .media, video');
    if (bg) {
      bg.classList.add('hero-parallax-bg');
      /* Zoom-in entrance */
      bg.classList.add('aura-hero-zoom');
      setTimeout(function () { bg.classList.add('aura-hero-zoom--ready'); }, 80);
    }

    gsap.to(bg, { yPercent: 28, ease: 'none', scrollTrigger: { trigger: hero, start: 'top top', end: 'bottom top', scrub: 1.2 } });

    var tX = 0, tY = 0, cX = 0, cY = 0;
    document.addEventListener('mousemove', function (e) {
      tX = (e.clientX / window.innerWidth  - 0.5) * 16;
      tY = (e.clientY / window.innerHeight - 0.5) * 16;
    });
    gsap.ticker.add(function () {
      cX += (tX-cX)*0.06; cY += (tY-cY)*0.06;
      if (bg) gsap.set(bg, { x: cX, y: cY });
      hero.querySelectorAll('.banner__content .field, .banner__box, .hero__text-group').forEach(function (el, i) {
        var d = (i%3+1)*0.4;
        gsap.set(el, { x: cX*d, y: cY*d*0.5 });
      });
    });

    var els = hero.querySelectorAll('.banner__heading, .banner__subheading, .hero__title, .hero__description, .banner__content a, .banner__buttons');
    els.forEach(function (el) { el.classList.add('hero-stagger-item'); });
    gsap.to(els, { opacity: 1, y: 0, duration: 1, stagger: 0.18, ease: 'power3.out', delay: 0.3 });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 7 — Text Scramble no Hero
  ══════════════════════════════════════════════════════════════ */
  var CHARS = 'アウラ•◆▲△AURA•·∙·◦○';
  function scrambleText(el, finalText, dur) {
    var start = Date.now(), len = finalText.length;
    var iv = setInterval(function () {
      var prog = Math.min((Date.now()-start)/dur, 1);
      var rev = Math.floor(prog*len), r = '';
      for (var i = 0; i < len; i++) {
        if (i < rev) r += finalText[i];
        else if (finalText[i] === ' ' || finalText[i] === '\n') r += finalText[i];
        else r += CHARS[Math.floor(Math.random()*CHARS.length)];
      }
      el.textContent = r;
      if (prog >= 1) { clearInterval(iv); el.textContent = finalText; }
    }, 45);
  }
  function initHeroScramble() {
    var h = document.querySelector('.banner__heading, .hero__title, .slideshow__slide-heading');
    if (!h) return;
    var orig = h.textContent.trim();
    if (!orig) return;
    setTimeout(function () { scrambleText(h, orig, 1400); }, 700);
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 8 — Split Text Reveal
  ══════════════════════════════════════════════════════════════ */
  function initSplitTextReveal() {
    document.querySelectorAll('.section-header h2, .collection__title, .rich-text h2, .title--primary, .featured-collection__title').forEach(function (el) {
      if (el.closest('.aura-mid-banner')) return;
      if (el.querySelector('.aura-word')) return; /* já processado */
      var words = el.innerHTML.trim().split(' ');
      el.innerHTML = words.map(function (w) { return '<span class="aura-word-wrap"><span class="aura-word">'+w+'</span></span>'; }).join(' ');
      var ws = el.querySelectorAll('.aura-word');
      ScrollTrigger.create({ trigger: el, start: 'top 85%', onEnter: function () {
        gsap.to(ws, { y: 0, opacity: 1, duration: 0.72, stagger: 0.065, ease: 'power4.out' });
      }, once: true });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 9 — Magnetic Buttons
  ══════════════════════════════════════════════════════════════ */
  function initMagneticButtons() {
    if (window.matchMedia('(max-width: 749px)').matches) return;
    document.querySelectorAll('button.button, a.button, .button--primary, .button--secondary, .aura-mid-banner__cta, .aura-float-cta, .aura-slide-btn').forEach(function (btn) {
      btn.addEventListener('mousemove', function (e) {
        var rect = btn.getBoundingClientRect();
        gsap.to(btn, { x: (e.clientX-rect.left-rect.width/2)*0.44, y: (e.clientY-rect.top-rect.height/2)*0.44, duration: 0.35, ease: 'power2.out' });
      });
      btn.addEventListener('mouseleave', function () {
        gsap.to(btn, { x: 0, y: 0, duration: 0.6, ease: 'elastic.out(1, 0.45)' });
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 10 — Middle Banner
  ══════════════════════════════════════════════════════════════ */
  function initMidBanner() {
    if (document.querySelector('.aura-mid-banner')) return;
    var sections = document.querySelectorAll('.shopify-section, section[class*="section"]');
    if (sections.length < 3) return;

    var heroImg = document.querySelector('.banner img, .hero img, .slideshow img');
    var bgUrl = heroImg ? heroImg.src.replace(/(\.[^.]+)$/, '_2048x$1').replace(/&width=\d+/, '&width=2048') : '';

    var banner = document.createElement('div');
    banner.className = 'shopify-section aura-mid-banner';
    banner.setAttribute('data-aura-mid', 'true');
    if (bgUrl) banner.style.setProperty('--mid-bg', 'url("'+bgUrl+'")');

    banner.innerHTML = '<div class="aura-mid-banner__bg" style="background-image: var(--mid-bg, linear-gradient(135deg, #2d1f14 0%, #4a3525 40%, #2d2318 100%));"></div><div class="aura-mid-banner__overlay"></div><div class="aura-mid-banner__noise"></div><div class="aura-mid-banner__content"><span class="aura-mid-banner__eyebrow">Aura Decore — Japandi Living</span><h2 class="aura-mid-banner__title">Um espaço que respira<br>intenção e beleza</h2><p class="aura-mid-banner__subtitle">Cada peça da nossa coleção foi escolhida para trazer equilíbrio,<br>calma e sofisticação ao seu lar.</p><a href="/collections/all" class="aura-mid-banner__cta"><span>Explorar coleção</span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg></a></div><div class="aura-particle" style="width:180px;height:180px;top:10%;left:5%;--duration:9s;--drift:-30px;--rot:15deg;opacity:0.06;"></div><div class="aura-particle" style="width:80px;height:80px;top:70%;right:8%;--duration:7s;--drift:-20px;--rot:-10deg;opacity:0.1;animation-delay:-3s;"></div><div class="aura-particle" style="width:260px;height:260px;bottom:-60px;right:-40px;--duration:12s;--drift:-15px;--rot:8deg;opacity:0.04;"></div>';

    sections[1].insertAdjacentElement('afterend', banner);

    ScrollTrigger.create({ trigger: banner, start: 'top 72%', onEnter: function () { banner.classList.add('aura-mid-banner--visible'); } });

    var midBg = banner.querySelector('.aura-mid-banner__bg');
    gsap.to(midBg, { yPercent: 18, ease: 'none', scrollTrigger: { trigger: banner, start: 'top bottom', end: 'bottom top', scrub: 1.5 } });

    var tmx = 0, tmy = 0, cmx = 0, cmy = 0;
    banner.addEventListener('mousemove', function (e) {
      var rect = banner.getBoundingClientRect();
      tmx = (e.clientX-rect.left)/rect.width - 0.5;
      tmy = (e.clientY-rect.top)/rect.height - 0.5;
      banner.style.setProperty('--spotlight-x', ((e.clientX-rect.left)/rect.width*100).toFixed(1)+'%');
      banner.style.setProperty('--spotlight-y', ((e.clientY-rect.top)/rect.height*100).toFixed(1)+'%');
    });
    banner.addEventListener('mouseleave', function () { tmx = 0; tmy = 0; });
    gsap.ticker.add(function () { cmx += (tmx-cmx)*0.07; cmy += (tmy-cmy)*0.07; gsap.set(midBg, { x: cmx*20, y: cmy*12 }); });

    var cta = banner.querySelector('.aura-mid-banner__cta');
    if (cta) {
      cta.style.overflow = 'hidden'; cta.style.position = 'relative';
      cta.addEventListener('click', function (e) {
        var rp = document.createElement('span'); rp.className = 'aura-ripple';
        var rect = cta.getBoundingClientRect(); var size = Math.max(rect.width, rect.height)*2;
        rp.style.cssText = 'width:'+size+'px;height:'+size+'px;left:'+(e.clientX-rect.left-size/2)+'px;top:'+(e.clientY-rect.top-size/2)+'px';
        cta.appendChild(rp); rp.addEventListener('animationend', function () { rp.remove(); });
      });
    }
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 11 — Card Reveal Overlay + 3D Tilt + Ambient Glow + Dynamic Shadow
  ══════════════════════════════════════════════════════════════ */
  function initCardInteractions() {
    var isMobile = window.matchMedia('(max-width: 749px)').matches;

    document.querySelectorAll('.card, .card--product, .product-card').forEach(function (card) {
      /* Overlay "Ver produto" */
      var media = card.querySelector('.card__media, .card-media, .product-card__image-wrapper');
      if (media && !media.querySelector('.aura-card-overlay')) {
        var overlay = document.createElement('div');
        overlay.className = 'aura-card-overlay';
        overlay.innerHTML = '<span class="aura-card-overlay__label">Ver produto</span>';
        media.style.position = 'relative';
        media.appendChild(overlay);
      }

      if (isMobile) return;

      /* 3D Tilt + Ambient Glow + Dynamic Shadow */
      card.addEventListener('mousemove', function (e) {
        var rect = card.getBoundingClientRect();
        var dx = (e.clientX-rect.left-rect.width/2)  / (rect.width/2);
        var dy = (e.clientY-rect.top -rect.height/2) / (rect.height/2);

        /* Tilt */
        gsap.to(card, { rotateX: -dy*9, rotateY: dx*9, transformPerspective: 900, ease: 'power2.out', duration: 0.4 });

        /* Ambient glow */
        var px = ((e.clientX-rect.left)/rect.width*100).toFixed(1);
        var py = ((e.clientY-rect.top)/rect.height*100).toFixed(1);
        card.style.setProperty('--glow-x', px+'%');
        card.style.setProperty('--glow-y', py+'%');
        card.classList.add('aura-card--glowing');

        /* Dynamic shadow (light source) */
        var sx = (dx * -18).toFixed(1) + 'px';
        var sy = (dy * -18 + 12).toFixed(1) + 'px';
        card.style.setProperty('--shadow-x', sx);
        card.style.setProperty('--shadow-y', sy);
      });

      card.addEventListener('mouseleave', function () {
        gsap.to(card, { rotateX: 0, rotateY: 0, ease: 'elastic.out(1, 0.5)', duration: 0.8 });
        card.classList.remove('aura-card--glowing');
        card.style.setProperty('--shadow-x', '0px');
        card.style.setProperty('--shadow-y', '8px');
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 12 — Scroll Reveal
  ══════════════════════════════════════════════════════════════ */
  function initScrollReveal() {
    var SEL = ['.collection-list__item','.product-grid > *','.grid--2-col > *','.grid--3-col > *','.grid--4-col > *','.featured-collection .card-wrapper','.section-header','.rich-text','.image-with-text__content','.image-with-text__media','.multicolumn-list__item','.blog-articles article','.footer__column','.footer__content-bottom'];
    var seen = new WeakSet();
    document.querySelectorAll(SEL.join(', ')).forEach(function (el, i) {
      if (seen.has(el)) return; seen.add(el); el.classList.add('aura-reveal');
      if (i%3===1) el.classList.add('aura-reveal--scale');
    });
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('aura-reveal--visible'); obs.unobserve(e.target); } });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    document.querySelectorAll('.aura-reveal').forEach(function (el) { obs.observe(el); });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 13 — Brand Marquee
  ══════════════════════════════════════════════════════════════ */
  function initMarquee() {
    if (document.querySelector('.aura-marquee')) return;
    var sections = document.querySelectorAll('.shopify-section');
    if (sections.length < 2) return;
    var ITEMS = ['✦ Design Japandi','✦ Qualidade Premium','✦ Minimalismo Intencional','✦ Entrega Segura','✦ Elegância Natural','✦ Materiais Sustentáveis'];
    var t = '<div class="aura-marquee-track">' + ITEMS.map(function (i) { return '<span class="aura-marquee-item">'+i+'</span>'; }).join('') + ITEMS.map(function (i) { return '<span class="aura-marquee-item" aria-hidden="true">'+i+'</span>'; }).join('') + '</div>';
    var m = document.createElement('div'); m.className = 'shopify-section aura-marquee-section';
    m.innerHTML = '<div class="aura-marquee" aria-hidden="true">'+t+'</div>';
    sections[0].insertAdjacentElement('afterend', m);
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 14 — Price Shimmer ao entrar no viewport
  ══════════════════════════════════════════════════════════════ */
  function initPriceHighlight() {
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('aura-price-lit');
          setTimeout(function () { entry.target.classList.remove('aura-price-lit'); }, 900);
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });

    document.querySelectorAll('.price, .price--regular, .price-item--regular').forEach(function (el) {
      obs.observe(el);
    });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 15 — Gradient Text em Headings principais
  ══════════════════════════════════════════════════════════════ */
  function initGradientHeadings() {
    document.querySelectorAll('.section-header h2, .collection__title, .featured-collection__title').forEach(function (el) {
      if (el.closest('.aura-mid-banner')) return;
      el.classList.add('aura-gradient-heading');
    });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 16 — Image Clip-Path Reveal on Scroll
  ══════════════════════════════════════════════════════════════ */
  function initImageReveal() {
    document.querySelectorAll('.image-with-text .image-with-text__media, .media-gallery__item').forEach(function (el) {
      el.classList.add('aura-img-reveal');
      ScrollTrigger.create({ trigger: el, start: 'top 80%', onEnter: function () { el.classList.add('aura-img-reveal--visible'); }, once: true });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 17 — Button Ripple
  ══════════════════════════════════════════════════════════════ */
  function initButtonRipple() {
    document.querySelectorAll('button.button, a.button, .button--primary, .button--secondary, .cart__checkout-button, form[action="/cart"] button, .aura-slide-btn').forEach(function (btn) {
      btn.style.overflow = 'hidden'; btn.style.position = 'relative';
      btn.addEventListener('click', function (e) {
        var rp = document.createElement('span'); rp.className = 'aura-ripple';
        var rect = btn.getBoundingClientRect(); var size = Math.max(rect.width, rect.height)*2.5;
        rp.style.cssText = 'width:'+size+'px;height:'+size+'px;left:'+(e.clientX-rect.left-size/2)+'px;top:'+(e.clientY-rect.top-size/2)+'px';
        btn.appendChild(rp); rp.addEventListener('animationend', function () { rp.remove(); });
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 18 — Page Entrance Animation (GSAP)
  ══════════════════════════════════════════════════════════════ */
  function initPageEntrance() {
    var hero = document.querySelector('.banner, .hero, [data-section-type="image-banner"], .slideshow');
    if (hero) {
      var sections = document.querySelectorAll('.shopify-section:not(:first-child)');
      gsap.from(sections, {
        opacity: 0, y: 50, stagger: 0.12, duration: 0.9, ease: 'power3.out', delay: 0.4,
        clearProps: 'all',
      });
    }
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 19 — Section Animations (GSAP ScrollTrigger)
  ══════════════════════════════════════════════════════════════ */
  function initSectionAnimations() {
    /* Grid products stagger */
    document.querySelectorAll('.featured-collection, .collection-list, .product-recommendations').forEach(function (sec) {
      var items = sec.querySelectorAll('.card-wrapper, .collection-list__item');
      if (!items.length) return;
      items.forEach(function (el) { el.classList.remove('aura-reveal'); });
      gsap.from(items, { opacity: 0, y: 50, scale: 0.95, duration: 0.82, stagger: 0.1, ease: 'power3.out', scrollTrigger: { trigger: sec, start: 'top 78%', toggleActions: 'play none none none' } });
    });

    /* Image-with-text split */
    document.querySelectorAll('.image-with-text').forEach(function (sec) {
      var med = sec.querySelector('.image-with-text__media');
      var con = sec.querySelector('.image-with-text__content');
      if (med) gsap.from(med, { opacity: 0, x: -64, duration: 1.1, ease: 'power3.out', scrollTrigger: { trigger: sec, start: 'top 80%', toggleActions: 'play none none none' } });
      if (con) gsap.from(con, { opacity: 0, x: 64, duration: 1.1, ease: 'power3.out', scrollTrigger: { trigger: sec, start: 'top 80%', toggleActions: 'play none none none' } });
    });

    /* Rich text / multicolumn */
    document.querySelectorAll('.rich-text__blocks > *, .multicolumn-list__item').forEach(function (el, i) {
      el.classList.remove('aura-reveal');
      gsap.from(el, { opacity: 0, y: 38, duration: 0.8, delay: i*0.09, ease: 'power3.out', scrollTrigger: { trigger: el, start: 'top 85%', toggleActions: 'play none none none' } });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 20 — Footer
  ══════════════════════════════════════════════════════════════ */
  function initFooter() {
    var footer = document.querySelector('.footer, .site-footer');
    if (!footer) return;
    var cols = footer.querySelectorAll('.footer__column, .footer-block, .site-footer__column');
    cols.forEach(function (c) { c.classList.remove('aura-reveal'); });
    gsap.from(cols, { opacity: 0, y: 32, stagger: 0.12, duration: 0.85, ease: 'power3.out', scrollTrigger: { trigger: footer, start: 'top 88%', toggleActions: 'play none none none' } });
    var bot = footer.querySelector('.footer__content-bottom');
    if (bot) { bot.classList.remove('aura-reveal'); gsap.from(bot, { opacity: 0, y: 18, duration: 0.7, ease: 'power3.out', scrollTrigger: { trigger: bot, start: 'top 95%', toggleActions: 'play none none none' } }); }
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 21 — Breathe
  ══════════════════════════════════════════════════════════════ */
  function initBreathe() {
    document.querySelectorAll('.trust-badges img, .icon-with-text__icon, .newsletter__icon, .announcement-bar__message').forEach(function (el) {
      el.classList.add('aura-breathe');
    });
  }

  /* ══════════════════════════════════════════════════════════════
     MÓDULO 22 — Counter Animado
  ══════════════════════════════════════════════════════════════ */
  function initCounters() {
    document.querySelectorAll('[data-aura-count]').forEach(function (el) {
      var target = parseInt(el.getAttribute('data-aura-count'), 10);
      if (isNaN(target)) return;
      ScrollTrigger.create({ trigger: el, start: 'top 85%', once: true, onEnter: function () {
        gsap.to({ val: 0 }, { val: target, duration: 2, ease: 'power2.out', onUpdate: function () { el.textContent = Math.round(this.targets()[0].val).toLocaleString('pt-BR'); } });
      }});
    });
  }

  /* ══════════════════════════════════════════════════════════════
     v4.0 ── MODULE 23 — Icon Echo Ring (viewport enter burst)
  ══════════════════════════════════════════════════════════════ */
  function initIconEcho() {
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        var el = e.target;
        el.classList.add('aura-icon-echo');
        setTimeout(function () {
          el.classList.add('aura-icon-echo--pulse');
          setTimeout(function () { el.classList.remove('aura-icon-echo--pulse'); }, 900);
        }, 180);
        obs.unobserve(el);
      });
    }, { threshold: 0.65 });
    document.querySelectorAll('.icon-with-text__icon, .trust-badges img, .newsletter__icon').forEach(function (el) {
      obs.observe(el);
    });
  }

  /* ══════════════════════════════════════════════════════════════
     v4.0 ── MODULE 24 — Icon Magnetic (hover pull + spin)
  ══════════════════════════════════════════════════════════════ */
  function initIconMagnetic() {
    if (window.matchMedia('(max-width: 749px)').matches) return;
    document.querySelectorAll('.icon-with-text__icon, .trust-badges img, .list-social__link').forEach(function (el) {
      el.addEventListener('mousemove', function (e) {
        var rect = el.getBoundingClientRect();
        var dx = (e.clientX - rect.left - rect.width / 2) * 0.45;
        var dy = (e.clientY - rect.top - rect.height / 2) * 0.45;
        gsap.to(el, { x: dx, y: dy, rotation: dx * 0.5, duration: 0.3, ease: 'power2.out' });
      });
      el.addEventListener('mouseleave', function () {
        gsap.to(el, { x: 0, y: 0, rotation: 0, duration: 0.65, ease: 'elastic.out(1, 0.45)' });
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     v4.0 ── MODULE 25 — Text + Icon Sync Entrance
  ══════════════════════════════════════════════════════════════ */
  function initTextIconSync() {
    document.querySelectorAll('.icon-with-text__item, .multicolumn-list__item').forEach(function (block) {
      var icon  = block.querySelector('.icon-with-text__icon, img, svg');
      var texts = block.querySelectorAll('.icon-with-text__heading, .icon-with-text__body, h3, h4, p');
      if (!icon && !texts.length) return;
      if (icon) { icon.style.opacity = '0'; icon.style.transform = 'translateY(22px) scale(0.78) rotate(-12deg)'; }
      texts.forEach(function (t) { t.style.opacity = '0'; t.style.transform = 'translateX(16px)'; });
      ScrollTrigger.create({
        trigger: block, start: 'top 83%', once: true,
        onEnter: function () {
          if (icon) gsap.to(icon, { opacity: 1, y: 0, scale: 1, rotation: 0, duration: 0.72, ease: 'back.out(2.2)' });
          texts.forEach(function (t, i) {
            gsap.to(t, { opacity: 1, x: 0, duration: 0.58, delay: 0.14 + i * 0.09, ease: 'power3.out' });
          });
        }
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     v4.0 ── MODULE 26 — Kinetic Headings (letter-wave hover)
  ══════════════════════════════════════════════════════════════ */
  function initKineticHeadings() {
    if (window.matchMedia('(max-width: 749px)').matches) return;
    document.querySelectorAll('.section-header h2, .rich-text h2').forEach(function (el) {
      if (el.classList.contains('aura-gradient-heading')) return;
      if (el.querySelector('.aura-kinetic-char')) return;
      var raw = el.textContent.trim();
      if (!raw || raw.length > 55) return;
      el.classList.add('aura-kinetic-heading');
      el.innerHTML = raw.split('').map(function (ch) {
        return ch === ' ' ? ' ' : '<span class="aura-kinetic-char">' + ch + '</span>';
      }).join('');
      el.addEventListener('mouseenter', function () {
        el.querySelectorAll('.aura-kinetic-char').forEach(function (span, i) {
          gsap.to(span, {
            y: -10, duration: 0.28, delay: i * 0.022, ease: 'power2.out',
            onComplete: function () { gsap.to(span, { y: 0, duration: 0.42, ease: 'elastic.out(1, 0.5)' }); }
          });
        });
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     v4.0 ── MODULE 27 — Magnetic Nav Links
  ══════════════════════════════════════════════════════════════ */
  function initMagneticNavLinks() {
    if (window.matchMedia('(max-width: 749px)').matches) return;
    document.querySelectorAll('.header__menu-item a, .list-menu__item--link > a').forEach(function (link) {
      link.addEventListener('mousemove', function (e) {
        var rect = link.getBoundingClientRect();
        gsap.to(link, {
          x: (e.clientX - rect.left - rect.width / 2) * 0.2,
          y: (e.clientY - rect.top - rect.height / 2) * 0.2,
          duration: 0.3, ease: 'power2.out'
        });
      });
      link.addEventListener('mouseleave', function () {
        gsap.to(link, { x: 0, y: 0, duration: 0.55, ease: 'elastic.out(1, 0.5)' });
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     v4.0 ── MODULE 28 — Section Spotlight (all content sections)
  ══════════════════════════════════════════════════════════════ */
  function initSectionSpotlight() {
    if (window.matchMedia('(max-width: 749px)').matches) return;
    var sels = '.featured-collection, .image-with-text, .rich-text, .multicolumn, .icon-with-text';
    document.querySelectorAll(sels).forEach(function (sec) {
      sec.classList.add('aura-section-spotlight');
      sec.addEventListener('mousemove', function (e) {
        var rect = sec.getBoundingClientRect();
        sec.style.setProperty('--sp-x', ((e.clientX - rect.left) / rect.width * 100).toFixed(1) + '%');
        sec.style.setProperty('--sp-y', ((e.clientY - rect.top) / rect.height * 100).toFixed(1) + '%');
      });
      sec.addEventListener('mouseleave', function () {
        sec.style.setProperty('--sp-x', '-300%');
        sec.style.setProperty('--sp-y', '-300%');
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     v4.0 ── MODULE 29 — All-Banner Interactions (tilt + spotlight)
  ══════════════════════════════════════════════════════════════ */
  function initAllBannerInteraction() {
    if (window.matchMedia('(max-width: 749px)').matches) return;
    var bannerSel = '.banner:not(.aura-mid-banner), .collection-hero, [data-section-type="image-banner"]';
    document.querySelectorAll(bannerSel).forEach(function (banner) {
      /* spotlight overlay */
      var sp = document.createElement('div');
      sp.className = 'aura-banner-spotlight';
      banner.style.position = 'relative';
      banner.appendChild(sp);
      /* text tilt target */
      var textEl = banner.querySelector('.banner__content, .banner__box, .collection__header, [class*="banner__text"]');
      banner.addEventListener('mousemove', function (e) {
        var rect = banner.getBoundingClientRect();
        var px = (e.clientX - rect.left) / rect.width * 100;
        var py = (e.clientY - rect.top) / rect.height * 100;
        sp.style.background = 'radial-gradient(circle 300px at ' + px.toFixed(1) + '% ' + py.toFixed(1) + '%, rgba(255,235,190,0.11) 0%, transparent 70%)';
        if (textEl) {
          var dx = (e.clientX - rect.left - rect.width / 2) / (rect.width / 2);
          var dy = (e.clientY - rect.top - rect.height / 2) / (rect.height / 2);
          gsap.to(textEl, { x: dx * 14, y: dy * 7, duration: 0.5, ease: 'power2.out' });
        }
      });
      banner.addEventListener('mouseleave', function () {
        sp.style.background = 'none';
        if (textEl) gsap.to(textEl, { x: 0, y: 0, duration: 0.85, ease: 'elastic.out(1, 0.4)' });
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     v4.0 ── MODULE 30 — Ambient Orbs on content sections
  ══════════════════════════════════════════════════════════════ */
  function initAmbientOrbs() {
    var ORB_CFG = [
      { w: 220, h: 220, top: '4%',  left: '1%',  dur: '12s', dx: '38px',  dy: '-24px', delay: '0s'  },
      { w: 140, h: 140, top: '62%', right: '3%', dur: '8.5s', dx: '-28px', dy: '18px',  delay: '-4s' },
    ];
    var sels = '.featured-collection, .rich-text, .image-with-text, .icon-with-text, .multicolumn';
    document.querySelectorAll(sels).forEach(function (sec) {
      if (sec.querySelector('.aura-ambient-orb')) return;
      var pos = getComputedStyle(sec).position;
      if (pos === 'static') sec.style.position = 'relative';
      sec.classList.add('aura-has-orbs');
      ORB_CFG.forEach(function (cfg) {
        var orb = document.createElement('div');
        orb.className = 'aura-ambient-orb';
        orb.style.cssText = [
          'width:' + cfg.w + 'px', 'height:' + cfg.h + 'px',
          cfg.left ? 'left:' + cfg.left : 'right:' + cfg.right,
          'top:' + cfg.top,
          '--orb-dur:' + cfg.dur, '--orb-dx:' + cfg.dx, '--orb-dy:' + cfg.dy,
          'animation-delay:' + cfg.delay
        ].join(';');
        sec.appendChild(orb);
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     v4.0 ── MODULE 31 — Collection / Card Enter Ripple
  ══════════════════════════════════════════════════════════════ */
  function initCollectionRipple() {
    if (window.matchMedia('(max-width: 749px)').matches) return;
    document.querySelectorAll('.collection-list__item, .card-wrapper').forEach(function (item) {
      item.style.position = 'relative';
      item.style.overflow = 'hidden';
      item.addEventListener('mouseenter', function (e) {
        var rect = item.getBoundingClientRect();
        var rip = document.createElement('div');
        rip.className = 'aura-col-ripple';
        rip.style.left = (e.clientX - rect.left) + 'px';
        rip.style.top  = (e.clientY - rect.top) + 'px';
        item.appendChild(rip);
        rip.addEventListener('animationend', function () { rip.remove(); });
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     v4.0 ── MODULE 32 — Announcement Bar Cycling
  ══════════════════════════════════════════════════════════════ */
  function initAnnouncementBar() {
    var bar = document.querySelector('.announcement-bar__message, .announcement-bar__content');
    if (!bar) return;
    var MSGS = [
      bar.textContent.trim(),
      '✦ Frete grátis acima de R$299',
      '✦ Design Japandi — Elegância Natural',
      '✦ Qualidade Premium em cada detalhe',
    ].filter(function (m) { return m && m.length > 2; });
    if (MSGS.length < 2) return;
    var idx = 0;
    setInterval(function () {
      bar.classList.add('aura-announcement--exit');
      setTimeout(function () {
        idx = (idx + 1) % MSGS.length;
        bar.textContent = MSGS[idx];
        bar.classList.remove('aura-announcement--exit');
        bar.classList.add('aura-announcement--enter');
        void bar.offsetWidth;
        bar.classList.remove('aura-announcement--enter');
      }, 420);
    }, 4800);
  }

  /* ══════════════════════════════════════════════════════════════
     v4.0 ── MODULE 33 — Word Hover Lift (rich text paragraphs)
  ══════════════════════════════════════════════════════════════ */
  function initWordHoverLift() {
    if (window.matchMedia('(max-width: 749px)').matches) return;
    document.querySelectorAll('.rich-text__text p, .image-with-text__text p, .icon-with-text__body').forEach(function (p) {
      if (p.textContent.length > 180 || p.querySelector('.aura-hover-word')) return;
      var parts = p.innerHTML.split(' ');
      p.innerHTML = parts.map(function (w) { return '<span class="aura-hover-word">' + w + '</span>'; }).join(' ');
      p.querySelectorAll('.aura-hover-word').forEach(function (w) {
        w.addEventListener('mouseenter', function () {
          gsap.to(w, { y: -5, color: 'rgba(120,95,65,1)', duration: 0.22, ease: 'power2.out' });
        });
        w.addEventListener('mouseleave', function () {
          gsap.to(w, { y: 0, color: '', duration: 0.38, ease: 'elastic.out(1, 0.5)' });
        });
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     v4.0 ── MODULE 34 — Heading Underline Reveal on Scroll
  ══════════════════════════════════════════════════════════════ */
  function initHeadingUnderline() {
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add('aura-heading-underline--visible');
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.5 });
    document.querySelectorAll('.section-header__title, .section-header h2, .featured-collection__title').forEach(function (el) {
      if (!el.classList.contains('aura-gradient-heading')) {
        el.classList.add('aura-heading-underline');
        obs.observe(el);
      }
    });
  }

  /* ══════════════════════════════════════════════════════════════
     v5.0 ── PREMIUM FONTS
  ══════════════════════════════════════════════════════════════ */
  function initPremiumFonts() {
    if (document.querySelector('[data-aura-fonts="v5"]')) return;
    var pc = document.createElement('link'); pc.rel = 'preconnect'; pc.href = 'https://fonts.googleapis.com';
    var pc2 = document.createElement('link'); pc2.rel = 'preconnect'; pc2.href = 'https://fonts.gstatic.com'; pc2.crossOrigin = 'anonymous';
    document.head.appendChild(pc); document.head.appendChild(pc2);
    var fl = document.createElement('link');
    fl.rel = 'stylesheet'; fl.setAttribute('data-aura-fonts', 'v5');
    fl.href = 'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&family=Jost:wght@300;400;500&display=swap';
    document.head.appendChild(fl);
  }

  /* ══════════════════════════════════════════════════════════════
     v5.0 ── HERO CINEMA (full-screen premium reveal)
  ══════════════════════════════════════════════════════════════ */
  function initHeroCinema() {
    var hero = document.querySelector('.banner, .hero, [data-section-type="image-banner"], .slideshow, section.image-banner');
    if (!hero) return;
    if (hero.classList.contains('aura-hero-cinema')) return; /* idempotent */

    hero.classList.add('aura-hero-cinema');

    /* Letterbox bars */
    var lbTop = document.createElement('div'); lbTop.className = 'aura-letterbox-top';
    var lbBot = document.createElement('div'); lbBot.className = 'aura-letterbox-bot';
    hero.appendChild(lbTop); hero.appendChild(lbBot);

    /* Atmosphere overlays */
    var grade   = document.createElement('div'); grade.className   = 'aura-hero-grade';
    var vignette = document.createElement('div'); vignette.className = 'aura-hero-vignette';
    var grain   = document.createElement('div'); grain.className   = 'aura-hero-grain';
    hero.appendChild(grade); hero.appendChild(vignette); hero.appendChild(grain);

    /* Live badge */
    var badge = document.createElement('div'); badge.className = 'aura-hero-badge';
    badge.innerHTML = 'Aura Ref&uacute;gio &mdash; Japandi Living';
    hero.appendChild(badge);

    /* Scroll indicator */
    var scrollInd = document.createElement('div'); scrollInd.className = 'aura-scroll-ind';
    scrollInd.innerHTML = '<div class="aura-scroll-ind__mouse"><div class="aura-scroll-ind__wheel"></div></div><span class="aura-scroll-ind__label">Scroll</span>';
    hero.appendChild(scrollInd);

    /* Holographic CTAs */
    hero.querySelectorAll('a.button, .button--primary, .banner__button, .hero__cta').forEach(function (btn) {
      btn.classList.add('aura-cta-holo');
    });

    /* ── Cinema reveal sequence ── */
    /* Phase 1: letterbox in (immediate) */
    setTimeout(function () {
      hero.classList.add('aura-hero-cinema--cinematic');

      /* Phase 2: image wipe up */
      setTimeout(function () {
        hero.classList.add('aura-hero-cinema--revealed');
      }, 220);

      /* Phase 3: letterbox out */
      setTimeout(function () {
        hero.classList.remove('aura-hero-cinema--cinematic');
      }, 2800);

      /* Phase 4: scroll indicator appears */
      setTimeout(function () {
        scrollInd.classList.add('aura-scroll-ind--visible');
      }, 2400);
    }, 80);

    /* ── Mouse-reactive color grade (pure rAF, no GSAP dep) ── */
    if (!window.matchMedia('(max-width: 749px)').matches && !window.matchMedia('(pointer: coarse)').matches) {
      var tgx = 50, tgy = 50, cgx = 50, cgy = 50;
      hero.addEventListener('mousemove', function (e) {
        var rect = hero.getBoundingClientRect();
        tgx = (e.clientX - rect.left) / rect.width * 100;
        tgy = (e.clientY - rect.top) / rect.height * 100;
      });
      (function gradeLoop() {
        cgx += (tgx - cgx) * 0.05;
        cgy += (tgy - cgy) * 0.05;
        grade.style.setProperty('--grade-x', cgx.toFixed(1) + '%');
        grade.style.setProperty('--grade-y', cgy.toFixed(1) + '%');
        requestAnimationFrame(gradeLoop);
      })();
    }

    /* ── Hide scroll indicator on scroll ── */
    var scrollHidden = false;
    window.addEventListener('scroll', function () {
      if (window.scrollY > 120 && !scrollHidden) {
        scrollHidden = true;
        scrollInd.style.opacity = '0';
      } else if (window.scrollY <= 40 && scrollHidden) {
        scrollHidden = false;
        scrollInd.style.opacity = '';
      }
    }, { passive: true });
  }

  /* ══════════════════════════════════════════════════════════════
     v4.0 ── MODULE 35 — Stagger Dawn Native Sections (ScrollTrigger)
  ══════════════════════════════════════════════════════════════ */
  function initDawnSectionStagger() {
    gsap.utils.toArray('.shopify-section').forEach(function (section) {
      if (
        section.querySelector('.aura-hero') || 
        section.querySelector('.footer') || 
        section.querySelector('.aura-announcement-bar') || 
        section.querySelector('.aura-mid-banner') || 
        section.classList.contains('shopify-section-group-header-group') || 
        section.classList.contains('shopify-section-group-footer-group')
      ) return;

      gsap.from(section, {
        opacity: 0,
        y: 40,
        duration: 0.9,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: section,
          start: 'top 85%',
          toggleActions: 'play none none none'
        }
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     v4.0 ── MODULE 36 — Rotating Section Dividers
  ══════════════════════════════════════════════════════════════ */
  function initRotatingDividers() {
    document.querySelectorAll('.aura-divider').forEach(function (div) {
      gsap.to(div, {
        rotation: 180,
        ease: 'none',
        scrollTrigger: {
          trigger: div,
          start: 'top bottom',
          end: 'bottom top',
          scrub: 1
        }
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     BOOT
  ══════════════════════════════════════════════════════════════ */
  function boot() {
    initPremiumFonts();
    initHeroCinema();
    buildTrailPool();
    initCursor();
    initScrollProgress();
    initFloatingCTA();
    initHeader();
    initCartPulse();
    initHeroScramble();
    initHeroParallax();
    initScrollReveal();
    initCardInteractions();
    initButtonRipple();
    initBreathe();
    initMarquee();
    initPriceHighlight();
    /* v4.0 — non-GSAP */
    initIconEcho();
    initAmbientOrbs();
    initCollectionRipple();
    initAnnouncementBar();
    initHeadingUnderline();

    waitForGSAP(function () {
      initMidBanner();
      initSplitTextReveal();
      initGradientHeadings();
      initMagneticButtons();
      initSectionAnimations();
      initFooter();
      initImageReveal();
      initCounters();
      // initPageEntrance(); // Disabled to avoid conflict with scroll-linked stagger
      initDawnSectionStagger();
      initRotatingDividers();
      /* v4.0 — GSAP */
      initIconMagnetic();
      initTextIconSync();
      initKineticHeadings();
      initMagneticNavLinks();
      initSectionSpotlight();
      initAllBannerInteraction();
      initWordHoverLift();

      setTimeout(function () { ScrollTrigger.refresh(); }, 700);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

})();
