/* ===========================================
   AURA DECOR — Motion Design Engine
   Scroll reveals, parallax, cursor & interactions
   =========================================== */

(function() {
  'use strict';

  // ===== SCROLL REVEAL =====
  function initScrollReveal() {
    const revealElements = document.querySelectorAll(
      '.aura-reveal, .aura-stagger, .aura-slide-left, .aura-slide-right, .aura-scale, .aura-line, .aura-curtain, .aura-text-reveal'
    );
    if (!revealElements.length) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    revealElements.forEach(el => observer.observe(el));
  }

  // ===== AUTO-ADD REVEAL CLASSES =====
  function autoReveal() {
    // Add reveal to section headers
    document.querySelectorAll('.section-header, .title-wrapper').forEach(el => {
      if (!el.classList.contains('aura-reveal')) el.classList.add('aura-reveal');
    });

    // Add stagger to grids
    document.querySelectorAll('.grid--4-col-desktop, .grid--3-col-desktop, .multicolumn-list').forEach(el => {
      if (!el.classList.contains('aura-stagger')) el.classList.add('aura-stagger');
    });

    // Add scale to collection cards
    document.querySelectorAll('.collection-card-wrapper').forEach(el => {
      if (!el.classList.contains('aura-scale')) el.classList.add('aura-scale');
    });

    // Add reveal to rich text sections
    document.querySelectorAll('.rich-text__wrapper').forEach(el => {
      if (!el.classList.contains('aura-reveal')) el.classList.add('aura-reveal');
    });

    // Reveal image-with-text sections
    document.querySelectorAll('.image-with-text').forEach(el => {
      const img = el.querySelector('.image-with-text__media-item');
      const content = el.querySelector('.image-with-text__content');
      if (img && !img.classList.contains('aura-slide-left')) img.classList.add('aura-slide-left');
      if (content && !content.classList.contains('aura-slide-right')) content.classList.add('aura-slide-right');
    });

    // Add reveal to newsletter
    document.querySelectorAll('.newsletter').forEach(el => {
      if (!el.classList.contains('aura-reveal')) el.classList.add('aura-reveal');
    });

    // Aura custom sections
    document.querySelectorAll('.aura-collections__header, .aura-lookbook__header').forEach(el => {
      if (!el.classList.contains('aura-reveal')) el.classList.add('aura-reveal');
    });
    document.querySelectorAll('.aura-collections__grid').forEach(el => {
      if (!el.classList.contains('aura-stagger')) el.classList.add('aura-stagger');
    });
    document.querySelectorAll('.aura-lookbook__grid').forEach(el => {
      if (!el.classList.contains('aura-scale')) el.classList.add('aura-scale');
    });
  }

  // ===== PARALLAX =====
  function initParallax() {
    const parallaxImages = document.querySelectorAll('.aura-parallax-img');
    if (!parallaxImages.length) return;

    let ticking = false;
    function updateParallax() {
      parallaxImages.forEach(img => {
        const rect = img.parentElement.getBoundingClientRect();
        const speed = parseFloat(img.dataset.speed || 0.15);
        const yPos = (rect.top - window.innerHeight / 2) * speed;
        img.style.transform = 'translateY(' + yPos + 'px) scale(1.1)';
      });
      ticking = false;
    }

    window.addEventListener('scroll', () => {
      if (!ticking) { requestAnimationFrame(updateParallax); ticking = true; }
    }, { passive: true });
  }

  // ===== SMOOTH PARALLAX ON HERO =====
  function initHeroParallax() {
    const hero = document.querySelector('.aura-hero__bg-img');
    if (!hero) return;

    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const scrolled = window.scrollY;
          const rate = scrolled * 0.22;
          hero.style.transform = 'scale(1.08) translateY(' + rate + 'px)';
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }

  // ===== CURSOR DOT & RING (desktop) =====
  function initCursor() {
    if (window.innerWidth < 1024) return;

    const dot = document.createElement('div');
    dot.className = 'aura-cursor-dot';
    document.body.appendChild(dot);

    const ring = document.createElement('div');
    ring.className = 'aura-cursor-ring';
    document.body.appendChild(ring);

    let mouseX = 0, mouseY = 0;
    let dotX = 0, dotY = 0, ringX = 0, ringY = 0;

    document.addEventListener('mousemove', (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    });

    // Enlarge or change state on hover
    document.addEventListener('mouseover', (e) => {
      if (e.target.closest('a, button, input, select, .aura-magnetic, .aura-hero__btn-primary, .aura-hero__btn-secondary, .aura-hero__btn-ghost')) {
        ring.classList.add('active');
        dot.classList.add('active');
      }
      if (e.target.closest('.card-wrapper, .card, .product-card, .aura-col-card, .collection-card')) {
        ring.classList.add('card-active');
        dot.classList.add('card-active');
      }
    });

    document.addEventListener('mouseout', (e) => {
      if (e.target.closest('a, button, input, select, .aura-magnetic, .aura-hero__btn-primary, .aura-hero__btn-secondary, .aura-hero__btn-ghost')) {
        ring.classList.remove('active');
        dot.classList.remove('active');
      }
      if (e.target.closest('.card-wrapper, .card, .product-card, .aura-col-card, .collection-card')) {
        ring.classList.remove('card-active');
        dot.classList.remove('card-active');
      }
    });

    function animateCursor() {
      // Small central dot moves fast
      dotX += (mouseX - dotX) * 0.22;
      dotY += (mouseY - dotY) * 0.22;
      dot.style.left = dotX + 'px';
      dot.style.top = dotY + 'px';

      // Outer ring follows with a spring delay (elastic effect)
      ringX += (mouseX - ringX) * 0.12;
      ringY += (mouseY - ringY) * 0.12;
      ring.style.left = ringX + 'px';
      ring.style.top = ringY + 'px';

      requestAnimationFrame(animateCursor);
    }
    animateCursor();
  }

  // ===== MAGNETIC BUTTONS =====
  function initMagnetic() {
    const buttons = document.querySelectorAll('.aura-magnetic, .aura-hero__btn-primary, .aura-hero__btn-secondary, .aura-hero__btn-ghost, .product-form__submit, [name="add"]');
    buttons.forEach(btn => {
      btn.addEventListener('mousemove', (e) => {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        btn.style.transform = 'translate(' + (x * 0.25) + 'px, ' + (y * 0.25) + 'px)';
      });
      btn.addEventListener('mouseleave', () => {
        btn.style.transform = 'translate(0, 0)';
      });
    });
  }


  // ===== SMOOTH HEADER HIDE/SHOW =====
  function initHeaderAnimation() {
    const header = document.querySelector('.section-header, .shopify-section-header, header.header');
    if (!header) return;

    let lastScroll = 0;
    window.addEventListener('scroll', () => {
      const current = window.scrollY;
      if (current > 200) {
        if (current > lastScroll) {
          header.style.transform = 'translateY(-100%)';
          header.style.transition = 'transform 0.4s ease';
        } else {
          header.style.transform = 'translateY(0)';
          header.style.boxShadow = '0 2px 20px rgba(26,26,26,0.05)';
        }
      } else {
        header.style.transform = 'translateY(0)';
        header.style.boxShadow = 'none';
      }
      lastScroll = current;
    }, { passive: true });
  }

  // ===== NUMBER COUNTER ANIMATION =====
  function initCounters() {
    const counters = document.querySelectorAll('.aura-counter');
    if (!counters.length) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const target = parseInt(el.dataset.target || el.textContent);
          const duration = 2000;
          const start = Date.now();
          const timer = setInterval(() => {
            const elapsed = Date.now() - start;
            const progress = Math.min(elapsed / duration, 1);
            const ease = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.round(target * ease).toLocaleString('pt-BR');
            if (progress >= 1) clearInterval(timer);
          }, 16);
          observer.unobserve(el);
        }
      });
    }, { threshold: 0.5 });

    counters.forEach(c => observer.observe(c));
  }

  // ===== IMAGE TILT ON HOVER =====
  function initTilt() {
    document.querySelectorAll('.aura-collections__card').forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        card.style.transform = 'perspective(800px) rotateY(' + (x * 6) + 'deg) rotateX(' + (-y * 6) + 'deg) scale(1.02)';
      });
      card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(800px) rotateY(0deg) rotateX(0deg) scale(1)';
        card.style.transition = 'transform 0.5s ease';
      });
      card.addEventListener('mouseenter', () => {
        card.style.transition = 'none';
      });
    });
  }

  // ===== INIT =====
  function init() {
    autoReveal();
    initScrollReveal();
    initParallax();
    initHeroParallax();
    initCursor();
    initMagnetic();
    initCounters();
    initTilt();
    // Delayed header to avoid layout issues
    setTimeout(initHeaderAnimation, 1000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
