'use strict';
(() => {
  // A fixed map workspace keeps all gestures and scrolling inside its panels.
  if (document.body.classList.contains('global-page')) return;
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  const cover = document.querySelector('.brand-cover');
  const clip = document.getElementById('kline-clip-rect');
  const seen = new WeakSet();
  const animations = new Set();
  let observer;
  let frame = 0;

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
      if (preference.matches || document.hidden) return;
      entries.forEach(entry => {
        if (!entry.isIntersecting || seen.has(entry.target)) return;
        const element = entry.target;
        seen.add(element);
        observer.unobserve(element);
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
    document.querySelectorAll('.editorial-heading,.research-card,.home-updates,.overview-current,.overview-trend,.principle-grid>article').forEach(element => {
      if (!seen.has(element)) observer.observe(element);
    });
  }
  function stop() {
    if (observer) observer.disconnect();
    observer = undefined;
    if (frame) window.cancelAnimationFrame(frame);
    frame = 0;
    animations.forEach(animation => animation.cancel());
    animations.clear();
    if (clip) clip.setAttribute('width', '720');
  }
  window.addEventListener('scroll', scheduleKline, {passive: true});
  window.addEventListener('resize', scheduleKline, {passive: true});
  preference.addEventListener('change', () => {stop(); start();});
  document.addEventListener('visibilitychange', () => {
    document.body.classList.toggle('motion-paused', document.hidden);
    animations.forEach(animation => document.hidden ? animation.pause() : animation.play());
    if (document.hidden && frame) {window.cancelAnimationFrame(frame); frame = 0;}
    if (!document.hidden) scheduleKline();
  });
  start();
})();
