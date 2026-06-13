/* ============================================================
   AURA DECORE — JS DE ALTA CONVERSÃO (CRO)
   auradecore.com.br
   ============================================================ */

(function () {
  'use strict';

  /* ----------------------------------------------------------
     1. INTERSECTION OBSERVER — Animações de entrada ao scroll
     ---------------------------------------------------------- */
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        var el = e.target;
        var delay = el.dataset.delay || 0;
        setTimeout(function () {
          el.classList.add('is-visible');
        }, Number(delay));
        io.unobserve(el);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -48px 0px' });

  document.querySelectorAll('.animate-on-scroll').forEach(function (el) {
    io.observe(el);
  });

  /* ----------------------------------------------------------
     2. SCROLL PROGRESS BAR
     ---------------------------------------------------------- */
  var scrollBar = document.createElement('div');
  scrollBar.className = 'aura-scroll-progress';
  document.body.prepend(scrollBar);

  window.addEventListener('scroll', function () {
    var scrolled = window.scrollY;
    var total = document.body.scrollHeight - window.innerHeight;
    var pct = total > 0 ? (scrolled / total) * 100 : 0;
    scrollBar.style.width = pct + '%';
  }, { passive: true });

  /* ----------------------------------------------------------
     3. VIEWERS COUNTER — Social proof (7-23 pessoas)
     ---------------------------------------------------------- */
  var viewers = Math.floor(Math.random() * 17) + 7;

  document.querySelectorAll('.aura-viewers-count').forEach(function (el) {
    el.textContent = viewers;
  });

  // Flutua levemente a cada 20-40s para parecer orgânico
  setInterval(function () {
    var delta = Math.floor(Math.random() * 5) - 2;
    viewers = Math.min(23, Math.max(7, viewers + delta));
    document.querySelectorAll('.aura-viewers-count').forEach(function (el) {
      el.textContent = viewers;
    });
  }, (Math.random() * 20000) + 20000);

  /* ----------------------------------------------------------
     4. URGÊNCIA — Alerta sutil quando estoque baixo
     ---------------------------------------------------------- */
  document.querySelectorAll('.aura-badge-urgencia').forEach(function (badge) {
    badge.style.opacity = '0';
    badge.style.transform = 'scale(0.8)';
    badge.style.transition = 'opacity 0.4s ease, transform 0.4s cubic-bezier(0.34,1.56,0.64,1)';
    setTimeout(function () {
      badge.style.opacity = '1';
      badge.style.transform = 'scale(1)';
    }, 800);
  });

  /* ----------------------------------------------------------
     5. PROGRESS BAR — Anima ao entrar na viewport
     ---------------------------------------------------------- */
  var progressIO = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        var fill = e.target.querySelector('.aura-progress-fill');
        if (fill) {
          var targetWidth = fill.dataset.width || '70%';
          setTimeout(function () {
            fill.style.width = targetWidth;
          }, 200);
        }
        progressIO.unobserve(e.target);
      }
    });
  }, { threshold: 0.5 });

  document.querySelectorAll('.aura-progress-bar').forEach(function (bar) {
    var fill = bar.querySelector('.aura-progress-fill');
    if (fill) fill.style.width = '0%';
    progressIO.observe(bar);
  });

})();
