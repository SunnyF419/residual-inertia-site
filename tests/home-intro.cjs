/* Lifecycle regressions: an optional introduction must never trap a visitor. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../assets/home-intro.js'), 'utf8');
function boot(options = {}) {
  const frames = new Map(), timers = new Map(), storage = new Map(), events = {}, documentEvents = {}, mediaEvents = {}, pendingCloses = [];
  let sequence = 0, opened = 0, closed = 0, animation, scroll;
  if (options.seen) storage.set('ri-home-intro-seen', '1');
  const classList = () => {const values = new Set(); return {add: x => values.add(x), remove: x => values.delete(x), contains: x => values.has(x)};};
  const control = () => ({hidden: true, isConnected: true, events: {}, classList: classList(), addEventListener(name, cb) {this.events[name] = cb;}, focus() {document.activeElement = this;}});
  const skip = control(), replay = control(), main = control();
  main.setAttribute = () => {}; main.removeAttribute = () => {};
  const access = {dataset: {text: 'OBSERVE. RESEARCH. DECIDE.'}, textContent: ''};
  const status = {dataset: {text: 'INDEPENDENT RESEARCH'}, textContent: ''};
  const body = {classList: classList(), style: {overflow: 'auto', paddingRight: '2px'}};
  const dialogEvents = {};
  const dialog = {open: false, dataset: {}, classList: classList(), offsetWidth: 1000,
    querySelector: s => s.includes('skip') ? skip : s.includes('access') ? access : status,
    addEventListener: (name, cb) => {dialogEvents[name] = cb;},
    showModal() {if (options.showError) throw new Error('unsupported context'); this.open = true; opened++;},
    close() {this.open = false; closed++; if (options.asyncClose) pendingCloses.push(dialogEvents.close); else dialogEvents.close();},
    animate() {let resolve; const finished = new Promise(r => {resolve = r;}); animation = {finished, complete: resolve, cancel() {}}; return animation;}};
  if (options.unsupported) delete dialog.showModal;
  const reduced = {matches: !!options.reduced, addEventListener: (name, cb) => {mediaEvents[name] = cb;}};
  const document = {body, activeElement: body, hidden: !!options.hidden, documentElement: {clientWidth: 940},
    querySelector: s => s.includes('home-intro') ? (options.nonHome ? null : dialog) : replay,
    getElementById: () => main, addEventListener: (name, cb) => {documentEvents[name] = cb;}};
  const window = {innerWidth: 960, scrollY: options.scrollY || 0, location: {hash: options.hash || ''},
    matchMedia: () => reduced, getComputedStyle: () => ({paddingRight: '6px'}),
    performance: {now: () => 0, getEntriesByType: () => [{type: options.navigation || 'navigate'}]},
    sessionStorage: {getItem(key) {if (options.blockedStorage) throw new Error('blocked'); return storage.get(key);}, setItem: (k, v) => storage.set(k, v)},
    requestAnimationFrame: cb => {frames.set(++sequence, cb); return sequence;}, cancelAnimationFrame: id => frames.delete(id),
    setTimeout: (cb, delay) => {timers.set(++sequence, {cb, delay}); return sequence;}, clearTimeout: id => timers.delete(id),
    scrollTo: value => {scroll = value;}, addEventListener: (name, cb) => {events[name] = cb;}};
  vm.runInNewContext(source, {window, document, parseFloat});
  return {dialog, reduced, replay, skip, main, document, frames, timers, storage, documentEvents, mediaEvents, events, pendingCloses,
    get opened() {return opened;}, get closed() {return closed;}, get animation() {return animation;}, get scroll() {return scroll;},
    frame(now) {const [id, cb] = frames.entries().next().value; frames.delete(id); cb(now);},
    timer(delay) {const [id, timer] = [...timers].find(([, value]) => value.delay === delay); timers.delete(id); timer.cb();}};
}
(async () => {
  for (const options of [{reduced:true}, {seen:true}, {blockedStorage:true}, {hash:'#founder'}, {navigation:'back_forward'}, {navigation:'reload'}, {scrollY:400}, {hidden:true}, {unsupported:true}, {nonHome:true}]) {
    const s = boot(options); assert.equal(s.opened, 0); assert.equal(s.document.body.style.overflow, 'auto'); assert.equal(s.frames.size, 0);
  }
  let s = boot({showError:true}); assert.equal(s.dialog.open, false); assert.equal(s.document.body.style.overflow, 'auto'); assert.equal(s.document.body.style.paddingRight, '2px');
  s = boot(); assert.equal(s.opened, 1); assert.equal(s.storage.get('ri-home-intro-seen'), '1'); assert.equal(s.document.activeElement, s.skip);
  s.frame(1400); assert.equal(s.dialog.querySelector('[data-intro-access]').textContent, 'OBSERVE. RESEARCH. DECIDE.');
  s.frame(2100); assert.equal(s.dialog.dataset.phase, 'observe');
  s.frame(4800); assert.equal(s.dialog.dataset.phase, 'research');
  assert.equal(s.dialog.querySelector('[data-intro-status]').textContent, 'INDEPENDENT RESEARCH');
  s.frame(6300); assert.equal(s.dialog.dataset.phase, 'research');
  s.frame(7000); assert.equal(s.dialog.dataset.phase, 'decide');
  s.frame(9300); assert.equal(s.dialog.open, true); assert.equal(s.closed, 0);
  s.frame(9600); assert.equal(s.frames.size, 0); s.animation.complete(); await Promise.resolve();
  assert.equal(s.closed, 1); assert.equal(s.document.body.style.overflow, 'auto'); assert.equal(s.document.body.style.paddingRight, '2px'); assert.equal(s.document.activeElement, s.main); assert.equal(s.timers.size, 1);
  assert(s.main.classList.contains('intro-landing-focus'));
  s.main.events.blur(); assert(!s.main.classList.contains('intro-landing-focus'));
  s.timer(700); assert(!s.document.body.classList.contains('intro-revealing'));
  // Replay restores the original trigger, scroll position and styles.
  s.document.activeElement = s.replay; s.replay.events.click(); assert.equal(s.opened, 2);
  s.skip.events.click(); s.skip.events.click(); s.timer(750); assert.equal(s.closed, 2); assert.equal(s.document.activeElement, s.replay);
  assert.equal(s.scroll.top, 0); assert.equal(s.document.body.style.overflow, 'auto');
  // Motion preference and tab suspension release immediately, including during exit.
  s = boot(); s.reduced.matches = true; s.mediaEvents.change(); assert(!s.dialog.open); assert(s.replay.hidden); assert.equal(s.frames.size, 0);
  s = boot(); s.skip.events.click(); s.document.hidden = true; s.documentEvents.visibilitychange(); assert(!s.dialog.open); assert.equal(s.document.body.style.overflow, 'auto');
  s = boot(); s.timer(10600); assert(!s.dialog.open); assert.equal(s.frames.size, 0);
  s = boot(); s.events.pagehide(); assert(!s.dialog.open); assert.equal(s.document.body.style.paddingRight, '2px');
  // Native close events arrive later; old exit callbacks cannot close a new replay.
  s = boot({asyncClose:true}); s.skip.events.click(); const previousExit = s.animation;
  s.document.hidden = true; s.documentEvents.visibilitychange(); assert.equal(s.document.body.style.overflow, 'auto');
  s.document.hidden = false; s.document.activeElement = s.replay; s.replay.events.click();
  s.pendingCloses.shift()(); previousExit.complete(); await Promise.resolve();
  assert(s.dialog.open); assert.equal(s.document.body.style.overflow, 'hidden'); assert.equal(s.frames.size, 1);
  // Native unexpected closure also releases all scheduled work.
  s = boot(); s.dialog.close(); assert.equal(s.frames.size, 0); assert.equal(s.timers.size, 0);
  console.log('PASS: intro session policy, replay, focus/scroll restoration, safe failure, reduced motion, suspension and watchdog.');
})().catch(error => {console.error(error); process.exitCode = 1;});
