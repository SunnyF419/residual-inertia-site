'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(require('node:path').join(__dirname, '../assets/site-motion.js'), 'utf8');

function boot({reduced = false, global = false, supported = true} = {}) {
  const events = {}, mediaEvents = {}, documentEvents = {}, frames = new Map();
  let observer, requested = 0, width = '720', cancelled = 0;
  const body = {classList: {contains: cls => global && cls === 'global-page', toggle() {}}};
  const clip = {setAttribute(name, value) {if (name === 'width') width = value;}};
  const preference = {matches: reduced, addEventListener(name, cb) {mediaEvents[name] = cb;}};
  const element = {animate() {return {finished: new Promise(() => {}), cancel() {cancelled++;}, pause() {}, play() {}};}};
  class Observer {
    constructor(cb) {this.cb = cb; this.items = []; observer = this;}
    observe(element) {this.items.push(element);}
    unobserve() {}
    disconnect() {this.disconnected = true;}
  }
  const document = {body, hidden: false, querySelector: () => ({offsetHeight: 400}), getElementById: () => clip,
    querySelectorAll: () => [element], addEventListener(name, cb) {documentEvents[name] = cb;}};
  const window = {scrollY: 0, matchMedia: () => preference, IntersectionObserver: supported ? Observer : undefined,
    requestAnimationFrame(cb) {frames.set(++requested, cb); return requested;}, cancelAnimationFrame(id) {frames.delete(id);},
    addEventListener(name, cb) {events[name] = cb;}};
  vm.runInNewContext(source, {window, document, IntersectionObserver: Observer, WeakSet, Set});
  return {events, preference, mediaEvents, frames, window, documentEvents, document,
    get observer() {return observer;}, get width() {return width;}, get cancelled() {return cancelled;}};
}

// Reduced motion leaves the entire decorative motif visible and schedules nothing.
let state = boot({reduced: true});
assert.equal(state.width, '720');
assert.equal(state.observer, undefined);
state.events.scroll();
assert.equal(state.frames.size, 0);

// Scroll progresses from half to full width, with one frame even under a burst.
state = boot();
assert.equal(state.width, '360');
state.window.scrollY = 400;
state.events.scroll(); state.events.scroll();
assert.equal(state.frames.size, 1);
for (const cb of state.frames.values()) cb();
state.frames.clear();
assert.equal(state.width, '720');
state.observer.cb([{isIntersecting: true, target: state.observer.items[0]}]);
state.preference.matches = true;
state.mediaEvents.change();
assert.equal(state.width, '720');
assert.equal(state.cancelled, 1);
assert.equal(state.observer.disconnected, true);

// Browsers without observers still have usable content and the scroll motif.
state = boot({supported: false});
assert.equal(state.width, '360');
assert.equal(state.observer, undefined);

// The map workspace receives no gesture handlers or animations from this script.
state = boot({global: true});
assert.deepEqual(Object.keys(state.events), []);
assert.equal(state.width, '720');
console.log('PASS: reduced motion, live preference change, batched scroll, observer fallback, map workspace isolation.');
