'use strict';
(() => {
  const dialog = document.querySelector('[data-home-intro]');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const replay = document.querySelector('[data-intro-replay]');
  const skip = dialog.querySelector('[data-intro-skip]');
  const access = dialog.querySelector('[data-intro-access]');
  const status = dialog.querySelector('[data-intro-status]');
  const sessionKey = 'ri-home-intro-seen';
  let frame = 0, deadline = 0, revealTimer = 0, exitAnimation;
  let started = 0, closing = false, saved;

  function seen() {
    // Blocked storage should never become a reason to withhold the homepage.
    try { return window.sessionStorage.getItem(sessionKey) === '1'; }
    catch (_) { return true; }
  }
  function remember() {
    try { window.sessionStorage.setItem(sessionKey, '1'); } catch (_) {}
  }
  function cancelWork() {
    window.cancelAnimationFrame(frame);
    window.clearTimeout(deadline);
    frame = deadline = 0;
  }
  function cleanup() {
    cancelWork();
    if (exitAnimation) {exitAnimation.cancel(); exitAnimation = undefined;}
    dialog.classList.remove('intro-playing');
    document.body.classList.remove('intro-active');
    if (saved) {
      document.body.style.overflow = saved.overflow;
      document.body.style.paddingRight = saved.padding;
      window.scrollTo({top: saved.y, behavior: 'instant'});
      // Native dialog restores focus, but the initial page has no trigger.
      if (saved.focus && saved.focus !== document.body && saved.focus.isConnected) saved.focus.focus({preventScroll: true});
      else {
        const main = document.getElementById('main');
        main.setAttribute('tabindex', '-1');
        main.focus({preventScroll: true});
        main.addEventListener('blur', () => main.removeAttribute('tabindex'), {once: true});
      }
      saved = undefined;
    }
    closing = false;
  }
  function closeNow(immediate = false) {
    if (dialog.open) dialog.close();
    // The native close event is queued. Restore scroll now, even in a hidden tab.
    cleanup();
    if (immediate) {
      window.clearTimeout(revealTimer);
      document.body.classList.remove('intro-revealing');
    }
  }
  function finish(immediate = false) {
    if (!dialog.open) return;
    if (closing) {if (immediate) closeNow(true); return;}
    closing = true;
    cancelWork();
    remember();
    if (immediate || reduced.matches || typeof dialog.animate !== 'function') {closeNow(true); return;}
    document.body.classList.add('intro-revealing');
    window.clearTimeout(revealTimer);
    revealTimer = window.setTimeout(() => document.body.classList.remove('intro-revealing'), 700);
    const animation = exitAnimation = dialog.animate([{opacity: 1}, {opacity: 0}], {duration: 600, easing: 'cubic-bezier(.2,.7,.2,1)', fill: 'forwards'});
    const complete = () => {if (exitAnimation === animation) closeNow();};
    animation.finished.then(complete, complete);
    // Release even if animation completion is lost during tab suspension.
    deadline = window.setTimeout(complete, 750);
  }
  function write(node, count) {
    const value = node.dataset.text.slice(0, count);
    if (node.textContent !== value) node.textContent = value;
  }
  function tick(now) {
    const elapsed = now - started;
    const phase = elapsed < 1550 ? 'observe' : elapsed < 3050 ? 'research' : 'decide';
    if (dialog.dataset.phase !== phase) dialog.dataset.phase = phase;
    write(access, Math.floor(Math.max(0, elapsed - 120) / 23));
    write(status, Math.floor(Math.max(0, elapsed - 1550) / 30));
    if (elapsed >= 4400) {finish(); return;}
    frame = window.requestAnimationFrame(tick);
  }
  function play(manual = false) {
    if (dialog.open || reduced.matches || document.hidden) return;
    if (!manual) {
      const navigation = window.performance.getEntriesByType('navigation')[0];
      // Preserve deep links, reloads/back navigation and restored scroll position.
      if (seen() || window.location.hash || window.scrollY > 0 || (navigation && navigation.type !== 'navigate')) return;
    }
    saved = {overflow: document.body.style.overflow, padding: document.body.style.paddingRight, y: window.scrollY, focus: document.activeElement};
    const scrollbar = window.innerWidth - document.documentElement.clientWidth;
    const padding = parseFloat(window.getComputedStyle(document.body).paddingRight) || 0;
    document.body.style.overflow = 'hidden';
    document.body.style.paddingRight = `${padding + scrollbar}px`;
    try {dialog.showModal();} catch (_) {cleanup(); return;}
    remember();
    closing = false;
    dialog.classList.add('intro-resetting');
    access.textContent = status.textContent = '';
    dialog.dataset.phase = 'observe';
    document.body.classList.add('intro-active');
    dialog.classList.remove('intro-playing');
    // Reset the CSS timeline on an explicit replay.
    void dialog.offsetWidth;
    dialog.classList.remove('intro-resetting');
    dialog.classList.add('intro-playing');
    skip.focus({preventScroll: true});
    started = window.performance.now();
    frame = window.requestAnimationFrame(tick);
    deadline = window.setTimeout(() => finish(true), 5500);
  }
  skip.addEventListener('click', () => finish());
  dialog.addEventListener('cancel', event => {event.preventDefault(); finish();});
  dialog.addEventListener('keydown', event => {
    if (event.key === 'Escape' || event.key === 'Enter') {event.preventDefault(); finish();}
    if (event.key === 'Tab') {event.preventDefault(); skip.focus({preventScroll: true});}
  });
  dialog.addEventListener('close', () => {if (!dialog.open) cleanup();});
  reduced.addEventListener('change', () => {
    if (replay) replay.hidden = reduced.matches;
    if (reduced.matches) finish(true);
  });
  document.addEventListener('visibilitychange', () => {if (document.hidden) finish(true);});
  window.addEventListener('pagehide', () => finish(true));
  if (replay) {replay.hidden = reduced.matches; replay.addEventListener('click', () => play(true));}
  play();
})();
