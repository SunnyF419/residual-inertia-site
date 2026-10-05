'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(require('node:path').join(__dirname, '../assets/site-motion.js'), 'utf8');

function boot({reduced = false, global = false, supported = true, fine = true} = {}) {
  const events = {}, mediaEvents = {}, documentEvents = {}, frames = new Map();
  let observer, requested = 0, width = '720', cancelled = 0;
  const body = {classList: {contains: cls => global && cls === 'global-page', toggle() {}}};
  const clip = {setAttribute(name, value) {if (name === 'width') width = value;}};
  const preference = {matches: reduced, addEventListener(name, cb) {mediaEvents[name] = cb;}};
  const element = {animate() {return {finished: new Promise(() => {}), cancel() {cancelled++;}, pause() {}, play() {}};}};
  const cardEvents = {}, fineEvents = {}, artStyles = new Map(), cardClasses = new Set(), readingClasses = new Set();
  function classes(values) {return {toggle(name, active) {active ? values.add(name) : values.delete(name);}, remove(name) {values.delete(name);}};}
  const artwork = {style: {setProperty(name, value) {artStyles.set(name, value);}, removeProperty(name) {artStyles.delete(name);}}};
  const card = {classList: classes(cardClasses), querySelector() {return artwork;},
    addEventListener(name, callback) {cardEvents[name] = callback;}, getBoundingClientRect() {return {left: 0, top: 0, width: 600, height: 400};}};
  const reading = {classList: classes(readingClasses)};
  const finePointer = {matches: fine, addEventListener(name, callback) {fineEvents[name] = callback;}};
  class Observer {
    constructor(cb) {this.cb = cb; this.items = []; observer = this;}
    observe(element) {this.items.push(element);}
    unobserve() {}
    disconnect() {this.disconnected = true;}
  }
  const document = {body, hidden: false, querySelector: () => ({offsetHeight: 400}), getElementById: () => clip,
    querySelectorAll: selector => selector === '.report-card,.reading-card' ? [card, reading] : selector === '.report-card' ? [card] : [element, card, reading], addEventListener(name, cb) {documentEvents[name] = cb;}};
  const window = {scrollY: 0, matchMedia: query => query.includes('reduced-motion') ? preference : finePointer, IntersectionObserver: supported ? Observer : undefined,
    requestAnimationFrame(cb) {frames.set(++requested, cb); return requested;}, cancelAnimationFrame(id) {frames.delete(id);},
    addEventListener(name, cb) {events[name] = cb;}};
  vm.runInNewContext(source, {window, document, IntersectionObserver: Observer, WeakSet, Set});
  return {events, preference, mediaEvents, frames, window, documentEvents, document, card, reading, cardEvents, finePointer, fineEvents, artStyles, cardClasses, readingClasses,
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

// Continuous artwork motion only runs while its card is visible.
state = boot();
state.observer.cb([{isIntersecting:true,target:state.card}, {isIntersecting:true,target:state.reading}]);
assert(state.cardClasses.has('card-motion-visible'));
assert(state.readingClasses.has('card-motion-visible'));
state.observer.cb([{isIntersecting:false,target:state.card}]);
assert(!state.cardClasses.has('card-motion-visible'));

// Pointer bursts use the latest coordinates and share a single pending frame.
state.cardEvents.pointermove({clientX:100,clientY:100,pointerType:'mouse'});
state.cardEvents.pointermove({clientX:600,clientY:200,pointerType:'mouse'});
assert.equal(state.frames.size,1);
for(const cb of state.frames.values())cb();
state.frames.clear();
assert.equal(state.artStyles.get('--art-x'),'6px');
assert.equal(state.artStyles.get('--art-y'),'0px');
state.cardEvents.pointermove({clientX:200,clientY:100,pointerType:'mouse'});
state.cardEvents.pointerleave();
assert.equal(state.frames.size,0);
assert.equal(state.artStyles.size,0);

// Touch input, coarse pointers, reduced motion, and hidden tabs never schedule parallax.
for(const options of [{fine:false},{reduced:true},{}]){
  state=boot(options);
  state.cardEvents.pointermove({clientX:300,clientY:100,pointerType:options.fine===undefined&&!options.reduced?'touch':'mouse'});
  assert.equal(state.frames.size,0);
}
state=boot();state.document.hidden=true;
state.cardEvents.pointermove({clientX:400,clientY:100,pointerType:'mouse'});
assert.equal(state.frames.size,0);

// Preference changes cancel in-flight pointer work and reset decoration visibility.
state=boot();state.observer.cb([{isIntersecting:true,target:state.card}]);
state.cardEvents.pointermove({clientX:500,clientY:100,pointerType:'mouse'});
state.preference.matches=true;state.mediaEvents.change();
assert.equal(state.frames.size,0);assert.equal(state.artStyles.size,0);assert.equal(state.cardClasses.size,0);
state=boot();state.cardEvents.pointermove({clientX:500,clientY:100,pointerType:'mouse'});
state.finePointer.matches=false;state.fineEvents.change();
assert.equal(state.frames.size,0);
console.log('PASS: reduced motion, live preference change, batched scroll/parallax, visibility, touch fallback and map isolation.');
