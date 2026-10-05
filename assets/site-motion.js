'use strict';
(() => {
  // A fixed map workspace keeps all gestures and scrolling inside its panels.
  if (document.body.classList.contains('global-page')) return;
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  const cover = document.querySelector('.brand-cover');
  const clip = document.getElementById('kline-clip-rect');
  const seen = new WeakSet();
  const animations = new Set();
  const surfaces = new Set(document.querySelectorAll('.report-card,.reading-card'));
  const pointers = [];
  let observer;
  let frame = 0;

  function resetPointer(pointer) {
    if (pointer.frame) window.cancelAnimationFrame(pointer.frame);
    pointer.frame = 0;
    pointer.cover.style.removeProperty('--art-x');
    pointer.cover.style.removeProperty('--art-y');
  }
  document.querySelectorAll('.report-card').forEach(card => {
    const artwork = card.querySelector('.report-cover');
    if (!artwork) return;
    const pointer = {cover: artwork, frame: 0};
    pointers.push(pointer);
    card.addEventListener('pointermove', event => {
      if (preference.matches || !finePointer.matches || document.hidden || event.pointerType === 'touch') return;
      pointer.x = event.clientX;
      pointer.y = event.clientY;
      if (pointer.frame) return;
      pointer.frame = window.requestAnimationFrame(() => {
        pointer.frame = 0;
        const rect = card.getBoundingClientRect();
        if (!rect.width || !rect.height) return;
        artwork.style.setProperty('--art-x', ((pointer.x - rect.left) / rect.width - .5) * 12 + 'px');
        artwork.style.setProperty('--art-y', ((pointer.y - rect.top) / rect.height - .5) * 8 + 'px');
      });
    }, {passive: true});
    card.addEventListener('pointerleave', () => resetPointer(pointer));
    card.addEventListener('pointercancel', () => resetPointer(pointer));
  });
  finePointer.addEventListener('change', () => pointers.forEach(resetPointer));

  function updateKline() {
    frame = 0;
    if (!cover || !clip || preference.matches || document.hidden) return;
    const progress = Math.min(1, Math.max(0, window.scrollY / Math.max(280, cover.offsetHeight)));
    clip.setAttribute('width', String(360 + progress * 360));
  }
  function scheduleKline() {
    if (!frame && cover && clip && !preference.matches && !document.hidden) {
      frame = window.requestAnimationFrame(updateKline);
    }
  }
  function start() {
    if (preference.matches) return;
    updateKline();
    if (!window.IntersectionObserver) return;
    observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (surfaces.has(entry.target)) entry.target.classList.toggle('card-motion-visible', entry.isIntersecting && !preference.matches && !document.hidden);
        if (preference.matches || document.hidden) return;
        if (!entry.isIntersecting || seen.has(entry.target)) return;
        const element = entry.target;
        seen.add(element);
        // Decorative layers remain observed so off-screen motion stops.
        if (!surfaces.has(element)) observer.unobserve(element);
        // Content is always readable without JavaScript or animation support.
        if (typeof element.animate !== 'function') return;
        const animation = element.animate([
          {opacity: 0, transform: 'translateY(18px)'},
          {opacity: 1, transform: 'translateY(0)'}
        ], {duration: 600, easing: 'cubic-bezier(.22,1,.36,1)'});
        animations.add(animation);
        animation.finished.then(() => animations.delete(animation), () => animations.delete(animation));
      });
    }, {threshold: .08});
    document.querySelectorAll('.editorial-heading,.research-card,.reading-card,.home-updates,.overview-current,.overview-trend,.principle-grid>article').forEach(element => {
      if (!seen.has(element) || surfaces.has(element)) observer.observe(element);
    });
  }
  function stop() {
    if (observer) observer.disconnect();
    observer = undefined;
    if (frame) window.cancelAnimationFrame(frame);
    frame = 0;
    animations.forEach(animation => animation.cancel());
    animations.clear();
    surfaces.forEach(element => element.classList.remove('card-motion-visible'));
    pointers.forEach(resetPointer);
    if (clip) clip.setAttribute('width', '720');
  }
  window.addEventListener('scroll', scheduleKline, {passive: true});
  window.addEventListener('resize', scheduleKline, {passive: true});
  preference.addEventListener('change', () => {stop(); start();});
  document.addEventListener('visibilitychange', () => {
    document.body.classList.toggle('motion-paused', document.hidden);
    animations.forEach(animation => document.hidden ? animation.pause() : animation.play());
    if (document.hidden && frame) {window.cancelAnimationFrame(frame); frame = 0;}
    if (document.hidden) pointers.forEach(resetPointer);
    if (!document.hidden) {
      scheduleKline();
      // Re-evaluate visibility after a background tab returns without scrolling.
      if (observer) surfaces.forEach(element => {observer.unobserve(element); observer.observe(element);});
    }
  });
  start();
})();
