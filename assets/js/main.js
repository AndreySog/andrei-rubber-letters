// main.js — switcher + scroll-spy + fullscreen toggle
// Pure vanilla JS. No dependencies.

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', () => {
    initFooter();
    initSwitcher();
    initFullscreen();
    initScrollSpy();
  });

  // -----------------------------------------------------------
  // footer: year, last-updated, deploy age, commit SHA
  // -----------------------------------------------------------

  function initFooter() {
    const year = document.getElementById('year');
    if (year) year.textContent = new Date().getFullYear();

    const last = document.getElementById('last-updated');
    if (last) {
      const d = new Date();
      last.textContent = d.toLocaleDateString('ru-RU', {
        year: 'numeric', month: 'long', day: 'numeric'
      });
      last.dateTime = d.toISOString();
    }

    const deployAge = document.getElementById('deploy-age');
    if (deployAge) {
      // ISO timestamp of first deploy (≈ msgId 905 era — 2026-07-18 09:28 EDT = 13:28 UTC)
      const deployed = new Date('2026-07-18T13:28:00Z');
      const minutes = Math.max(0, Math.floor((Date.now() - deployed.getTime()) / 60000));
      let label;
      if (minutes < 60)       label = minutes + ' min';
      else if (minutes < 1440) label = Math.floor(minutes / 60) + 'h';
      else                     label = Math.floor(minutes / 1440) + 'd';
      deployAge.textContent = label;
    }

    const sha = document.getElementById('commit-sha');
    if (sha) {
      // embedded at build time by the deploy script — fallback to short hash placeholder
      sha.textContent = (sha.textContent || '').trim() || 'latest';
    }
  }

  // -----------------------------------------------------------
  // bolt page switcher (нарисуй / начерти)
  // -----------------------------------------------------------

  function initSwitcher() {
    const switcher = document.querySelector('.switcher');
    if (!switcher) return;

    const buttons = Array.from(switcher.querySelectorAll('button'));
    const views = Array.from(document.querySelectorAll('.view'));

    function activate(targetId) {
      buttons.forEach(b => {
        b.classList.toggle('active', b.dataset.view === targetId);
      });
      views.forEach(v => v.classList.toggle('active', v.id === targetId));
    }

    buttons.forEach(btn => {
      btn.addEventListener('click', () => activate(btn.dataset.view));
    });

    // Keyboard: 1 / 2 keys (only on pages with a switcher)
    document.addEventListener('keydown', (e) => {
      // ignore if user is in an input
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const match = buttons.find(b => b.dataset.key === e.key);
      if (match) {
        activate(match.dataset.view);
        match.focus();
      }
    });
  }

  // -----------------------------------------------------------
  // fullscreen overlay for SVG stages
  // -----------------------------------------------------------

  function initFullscreen() {
    const overlay = createOverlay();
    document.body.appendChild(overlay.el);

    document.querySelectorAll('.stage').forEach(stage => {
      const expandBtn = stage.querySelector('.stage-expand');
      if (!expandBtn) return;

      expandBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const inner = stage.querySelector('svg, img');
        if (!inner) return;
        overlay.open(inner);
      });

      // also: double-click on the stage itself
      stage.addEventListener('dblclick', () => {
        const inner = stage.querySelector('svg, img');
        if (!inner) return;
        overlay.open(inner);
      });
    });
  }

  function createOverlay() {
    const el = document.createElement('div');
    el.className = 'fs-overlay';
    el.innerHTML = `
      <button class="fs-close" aria-label="Закрыть">✕ ESC</button>
      <div class="fs-content"></div>
    `;
    const content = el.querySelector('.fs-content');
    const closeBtn = el.querySelector('.fs-close');

    function open(srcEl) {
      content.innerHTML = '';
      const node = srcEl.cloneNode(true);
      node.removeAttribute('width');
      node.removeAttribute('height');
      node.style.maxWidth = '95vw';
      node.style.maxHeight = '92vh';
      content.appendChild(node);
      el.classList.add('is-open');
    }

    function close() {
      el.classList.remove('is-open');
      content.innerHTML = '';
    }

    closeBtn.addEventListener('click', close);
    el.addEventListener('click', (e) => { if (e.target === el) close(); });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && el.classList.contains('is-open')) close();
    });

    return { el, open, close };
  }

  // -----------------------------------------------------------
  // scroll-spy on quick-nav
  // -----------------------------------------------------------

  function initScrollSpy() {
    const navLinks = Array.from(document.querySelectorAll('.quick-nav a[href^="#"]'));
    if (navLinks.length === 0) return;

    const targets = navLinks
      .map(a => document.querySelector(a.getAttribute('href')))
      .filter(Boolean);
    if (targets.length === 0) return;

    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting && entry.intersectionRatio > 0.3) {
            const id = '#' + entry.target.id;
            navLinks.forEach(a => {
              a.classList.toggle('is-active', a.getAttribute('href') === id);
            });
          }
        });
      },
      { rootMargin: '-30% 0px -50% 0px', threshold: [0.3, 0.5, 0.7] }
    );
    targets.forEach(t => obs.observe(t));
  }

})();