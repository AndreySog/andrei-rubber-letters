// lock.js — password gate for andrei-ideas-site
// Client-side gate. Stops casual viewers, not motivated scrapers.
// See README.md → "Password gate" for honest scope-limit note.

(function () {
  'use strict';

  var PASSWORD = 'qqq';
  var STORAGE_KEY = 'andrei-ideas-auth';

  // ---- session helpers ----
  function isAuthed() {
    try {
      // sessionStorage wins per-tab; localStorage persists for return visits
      return sessionStorage.getItem(STORAGE_KEY) === '1' ||
             localStorage.getItem(STORAGE_KEY) === '1';
    } catch (e) {
      // privacy mode etc — fall through to prompt
      return false;
    }
  }

  function rememberAuth() {
    try {
      sessionStorage.setItem(STORAGE_KEY, '1');
      localStorage.setItem(STORAGE_KEY, '1');
    } catch (e) { /* ignore */ }
  }

  function forgetAuth() {
    try {
      sessionStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) { /* ignore */ }
  }

  // expose a logout hook on window for power users / debugging
  // usage from devtools: lockOut()
  window.lockOut = forgetAuth;

  // ---- main ----
  document.addEventListener('DOMContentLoaded', function () {
    if (isAuthed()) return;     // nothing to do

    var root = document.documentElement;
    root.classList.add('is-locked');

    // build overlay
    var overlay = document.createElement('div');
    overlay.className = 'lock-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'lock-title');

    overlay.innerHTML =
      '<div class="lock-card" id="lock-card">' +
        '<div class="lock-corners"></div>' +
        '<div class="lock-icon" aria-hidden="true">' +
          '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
               'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            '<rect x="3" y="11" width="18" height="11" rx="2"/>' +
            '<path d="M7 11V7a5 5 0 0 1 10 0v4"/>' +
          '</svg>' +
        '</div>' +
        '<h1 id="lock-title" class="lock-title">// Доступ ограничен</h1>' +
        '<p class="lock-subtitle">Введите пароль, чтобы открыть сайт.</p>' +
        '<form class="lock-form" id="lock-form" autocomplete="off">' +
          '<input type="password" class="lock-input" id="lock-input" ' +
                 'name="p" placeholder="•••" inputmode="text" autocapitalize="off" ' +
                 'autocorrect="off" spellcheck="false" aria-label="Пароль"/>' +
          '<button type="submit" class="lock-submit">открыть</button>' +
          '<div class="lock-error" id="lock-error" aria-live="polite"></div>' +
        '</form>' +
        '<div class="lock-footer">' +
          'protected · client-side gate<br>' +
          '<span style="color: var(--text-mute);">andrei-ideas-site</span>' +
        '</div>' +
      '</div>';

    document.body.appendChild(overlay);

    var form    = document.getElementById('lock-form');
    var input   = document.getElementById('lock-input');
    var error   = document.getElementById('lock-error');
    var card    = document.getElementById('lock-card');

    // focus
    setTimeout(function () { input.focus(); }, 30);

    function showError(msg) {
      error.textContent = msg;
      error.classList.add('is-visible');
      input.classList.add('is-error');
      card.classList.remove('is-shaking');
      // re-trigger animation
      void card.offsetWidth;
      card.classList.add('is-shaking');
    }

    function clearError() {
      error.textContent = '';
      error.classList.remove('is-visible');
      input.classList.remove('is-error');
    }

    input.addEventListener('input', clearError);

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var v = (input.value || '').trim();
      if (v === PASSWORD) {
        rememberAuth();
        // small delay so the user sees the lock UI accept the input
        card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        card.style.opacity = '0';
        card.style.transform = 'translateY(-6px) scale(0.98)';
        setTimeout(function () {
          root.classList.remove('is-locked');
          overlay.remove();
        }, 280);
      } else {
        showError('неверный пароль');
        input.select();
      }
    });

    // Esc clears input on lock screen
    document.addEventListener('keydown', function (e) {
      if (root.classList.contains('is-locked') &&
          e.key === 'Escape' &&
          document.activeElement === input) {
        input.value = '';
        clearError();
      }
    });
  });
})();