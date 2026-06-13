/**
 * Aura Decore — Motion Layer
 * GSAP + ScrollTrigger | Japandi × Minimalismo
 * "Movimento que respira. Animação que não grita."
 */

document.addEventListener('DOMContentLoaded', () => {
  if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') {
    setTimeout(initAuraMotion, 800);
  } else {
    initAuraMotion();
  }
});

function initAuraMotion() {
  if (typeof gsap === 'undefined') return;

  // Registrar plugin
  gsap.registerPlugin(ScrollTrigger);

  // ── 1. Hero Parallax ────────────────────────────────────
  const heroImg = document.querySelector('.aura-parallax-img');
  if (heroImg) {
    gsap.to(heroImg, {
      yPercent: 18,
      ease: 'none',
      scrollTrigger: {
        trigger: '.aura-hero',
        start: 'top top',
        end: 'bottom top',
        scrub: 1.2
      }
    });
  }

  // ── 2. Hero Content — entrada elegante ──────────────────
  const heroKicker = document.querySelector('.aura-hero__kicker');
  const heroTitle  = document.querySelector('.aura-hero__title');
  const heroDesc   = document.querySelector('.aura-hero__desc');
  const heroActions = document.querySelector('.aura-hero__actions');

  if (heroTitle) {
    const heroTl = gsap.timeline({ delay: 0.3 });
    if (heroKicker)  heroTl.from(heroKicker,  { opacity: 0, y: 20, duration: 0.7, ease: 'power2.out' });
    heroTl.from(heroTitle,   { opacity: 0, y: 40, duration: 1.0, ease: 'power3.out' }, '-=0.3');
    if (heroDesc)    heroTl.from(heroDesc,    { opacity: 0, y: 24, duration: 0.8, ease: 'power2.out' }, '-=0.5');
    if (heroActions) heroTl.from(heroActions, { opacity: 0, y: 16, duration: 0.6, ease: 'power2.out' }, '-=0.4');
  }

  // ── 3. Reveal on scroll — [data-aura-reveal] ─────────────
  document.querySelectorAll('[data-aura-reveal]').forEach((el) => {
    const delay = el.dataset.auraReveal ? parseInt(el.dataset.auraReveal) * 0.1 : 0;
    gsap.from(el, {
      opacity: 0,
      y: 32,
      duration: 0.85,
      delay: delay,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: el,
        start: 'top 88%',
        toggleActions: 'play none none none'
      }
    });
  });

  // ── 4. Stagger grid de produtos ──────────────────────────
  document.querySelectorAll('.aura-featured-col__grid').forEach((grid) => {
    const items = grid.querySelectorAll('.aura-featured-col__item');
    if (items.length === 0) return;
    gsap.from(items, {
      opacity: 0,
      y: 48,
      duration: 0.75,
      ease: 'power3.out',
      stagger: 0.12,
      scrollTrigger: {
        trigger: grid,
        start: 'top 82%',
        toggleActions: 'play none none none'
      }
    });
  });

  // ── 5. Stagger grade de coleções ─────────────────────────
  const cgCards = document.querySelectorAll('.aura-cg-card');
  if (cgCards.length > 0) {
    gsap.from(cgCards, {
      opacity: 0,
      y: 40,
      duration: 0.8,
      ease: 'power3.out',
      stagger: 0.08,
      scrollTrigger: {
        trigger: '.aura-cg-layout',
        start: 'top 85%',
        toggleActions: 'play none none none'
      }
    });
  }

  // ── 6. Editorial Banner parallax ─────────────────────────
  document.querySelectorAll('.aura-banner').forEach((banner) => {
    const img = banner.querySelector('.aura-banner__img');
    if (!img) return;
    gsap.to(img, {
      yPercent: 12,
      ease: 'none',
      scrollTrigger: {
        trigger: banner,
        start: 'top bottom',
        end: 'bottom top',
        scrub: 1.5
      }
    });
  });

  // ── 7. Seções de titulo com linha divisória ───────────────
  document.querySelectorAll('.aura-featured-col__header').forEach((header) => {
    const kicker = header.querySelector('.kicker');
    const title  = header.querySelector('.aura-featured-col__title');
    const desc   = header.querySelector('.aura-featured-col__desc');
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: header,
        start: 'top 85%',
        toggleActions: 'play none none none'
      }
    });
    if (kicker) tl.from(kicker, { opacity: 0, y: 16, duration: 0.6, ease: 'power2.out' });
    if (title)  tl.from(title,  { opacity: 0, y: 24, duration: 0.8, ease: 'power3.out' }, '-=0.3');
    if (desc)   tl.from(desc,   { opacity: 0, y: 16, duration: 0.6, ease: 'power2.out' }, '-=0.4');
  });

  // ── 8. Scroll progress indicator ─────────────────────────
  const progressBar = document.createElement('div');
  progressBar.style.cssText = 'position:fixed;top:0;left:0;height:2px;width:0%;background:var(--aura-terracota,#B8793A);z-index:9999;transition:width 0.1s linear;pointer-events:none;';
  document.body.appendChild(progressBar);
  ScrollTrigger.create({
    trigger: document.body,
    start: 'top top',
    end: 'bottom bottom',
    onUpdate: (self) => {
      progressBar.style.width = (self.progress * 100) + '%';
    }
  });

  // ── 9. Image hover zoom via CSS (reforço via JS) ──────────
  document.querySelectorAll('.aura-cg-card').forEach((card) => {
    const img = card.querySelector('.aura-cg-img');
    if (!img) return;
    card.addEventListener('mouseenter', () => {
      gsap.to(img, { scale: 1.06, duration: 0.6, ease: 'power2.out' });
    });
    card.addEventListener('mouseleave', () => {
      gsap.to(img, { scale: 1.0, duration: 0.5, ease: 'power2.inOut' });
    });
  });

  // ── 10. Footer stagger ───────────────────────────────────
  const footerBlocks = document.querySelectorAll('.footer-block');
  if (footerBlocks.length > 0) {
    gsap.from(footerBlocks, {
      opacity: 0,
      y: 24,
      duration: 0.7,
      ease: 'power2.out',
      stagger: 0.1,
      scrollTrigger: {
        trigger: '.footer',
        start: 'top 90%',
        toggleActions: 'play none none none'
      }
    });
  }

  console.log('[Aura Motion] GSAP inicializado — 10 animações ativas.');
}
