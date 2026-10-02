'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {tone, windowStart, select, nearest} = require('../assets/market-chart.js');
const data = JSON.parse(fs.readFileSync(path.join(__dirname, '../content/market/regime-history.json'), 'utf8'));
const original = JSON.stringify(data);
assert.equal(windowStart('2026-03-31', 1), '2026-02-28');
assert.equal(windowStart('2024-03-31', 1), '2024-02-29');
assert.equal(windowStart('2024-02-29', 12), '2023-02-28');
assert.equal(windowStart('2026-09-30', 6), '2026-03-30');
for (const months of [1,6,12,60]) {
  const view = select(data, months);
  assert.ok(view.points.length > 0);
  assert.ok(view.points.every(p => p.date >= view.start && p.date <= view.end));
  assert.equal(view.points.at(-1), data.points.at(-1));
  for (const [i,p] of view.points.entries()) assert.equal(nearest(view.points, Date.parse(p.date + 'T00:00:00Z')), i);
  assert.equal(nearest(view.points, 0), 0);
  assert.equal(nearest(view.points, Infinity), view.points.length - 1);
}
assert.deepEqual(select(data,60).points, data.points);
assert.equal(JSON.stringify(data), original);
for (const [score, expected] of [[34.99,'constructive'],[35,'neutral'],[49.99,'neutral'],[50,'caution'],[64.99,'caution'],[65,'defensive'],[79.99,'defensive'],[80,'stress']]) assert.equal(tone(score), expected);
for (const prefix of ['', 'en/']) {
  const html = fs.readFileSync(path.join(__dirname, '../dist/', prefix, 'overview/index.html'), 'utf8');
  const embedded = JSON.parse(html.match(/<script type="application\/json" data-chart-data>(.*?)<\/script>/s)[1]);
  assert.deepEqual(embedded.points.map(({date,score,state}) => ({date,score,state})), data.points);
  assert.ok(embedded.points.every(p => p.label));
  assert.equal((html.match(/data-chart-range="/g) || []).length, 4);
  assert.ok(html.includes('data-chart-range="60" aria-pressed="true"'));
  assert.ok(html.includes('data-chart-series points="'));
  assert.ok(html.includes('aria-live="polite"'));
  assert.ok(html.includes('/assets/market-chart.js?v='));
  const map = fs.readFileSync(path.join(__dirname, '../dist/', prefix, 'global/index.html'), 'utf8');
  assert.ok(!map.includes('/assets/market-chart.js'));
}
// Exercise actual UI callbacks, including calendar selection, resizing and keyboard browsing.
const vm = require('node:vm');
function element() {
  return {attrs:{}, events:{}, children:[], style:{}, hidden:false, offsetWidth:220, offsetHeight:32,
    setAttribute(k,v) {this.attrs[k] = String(v);}, removeAttribute(k) {delete this.attrs[k];},
    replaceChildren(...children) {this.children = children;},
    addEventListener(k,cb) {this.events[k] = cb;}};
}
const selectors = ['[data-chart-data]','.market-plot','.market-svg','[data-chart-slider]',
  '[data-chart-tooltip]','[data-chart-cursor]','[data-chart-readout]','[data-chart-bands]',
  '[data-chart-grid]','[data-chart-series]','[data-chart-ticks]','[data-chart-endpoint]',
  '#history-desc','[data-chart-window]'];
const ui = Object.fromEntries(selectors.map(s => [s,element()]));
const full = JSON.parse(fs.readFileSync(path.join(__dirname, '../dist/overview/index.html'), 'utf8').match(/<script type="application\/json" data-chart-data>(.*?)<\/script>/s)[1]);
ui['[data-chart-data]'].textContent = JSON.stringify(full);
let width = 1000;
ui['.market-plot'].getBoundingClientRect = () => ({width,height:300,left:0});
const line = element(), circle = element();
ui['[data-chart-cursor]'].querySelector = name => name === 'line' ? line : circle;
const controls = [element(),element()];
const buttons = [1,6,12,60].map(months => Object.assign(element(), {dataset:{chartRange:String(months)}}));
const panel = {querySelector:s => ui[s], querySelectorAll:s => s === '[data-chart-range]' ? buttons : controls};
let resize;
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../assets/market-chart.js'), 'utf8'), {
  document:{querySelectorAll:() => [panel], createElementNS:() => element()},
  ResizeObserver:class {constructor(cb) {resize = cb;} observe() {}},
  window:{addEventListener() {}}, Date, JSON, Math
});
const series = ui['[data-chart-series]'];
const pointCount = () => series.attrs.points.split(' ').length;
assert.equal(pointCount(), data.points.length);
assert.ok(controls.every(c => !c.hidden));
assert.equal(ui['[data-chart-bands]'].children.length, 5);
for (const [index,months] of [1,6,12,60].entries()) {
  buttons[index].events.click();
  assert.equal(pointCount(), select(data,months).points.length);
  assert.equal(buttons.filter(b => b.attrs['aria-pressed'] === 'true').length, 1);
}
buttons[0].events.click();
const view = select(data,1);
const slider = ui['[data-chart-slider]'];
slider.value = 0;
slider.events.input();
assert.ok(ui['[data-chart-readout]'].textContent.startsWith(view.points[0].date));
assert.ok(slider.attrs['aria-valuetext'].includes(view.points[0].score.toFixed(1)));
assert.equal(ui['[data-chart-tooltip]'].hidden, false);
assert.equal(circle.attrs.cx, String(34 + (Date.parse(view.points[0].date)-Date.parse(view.start))/(Date.parse(view.end)-Date.parse(view.start))*(width-48)));
width = 360; resize();
assert.equal(ui['.market-svg'].attrs.viewBox, '0 0 360 300');
assert.equal(ui['[data-chart-ticks]'].children.length, 3);
assert.equal(pointCount(), view.points.length);
ui['.market-plot'].events.pointermove({clientX:346});
assert.ok(ui['[data-chart-tooltip]'].textContent.startsWith(view.points.at(-1).date));
ui['.market-plot'].events.pointerleave();
assert.equal(ui['[data-chart-tooltip]'].hidden, true);
assert.ok('hidden' in ui['[data-chart-cursor]'].attrs);
console.log('PASS: calendar windows, raw thresholds, original data, range buttons, pointer and keyboard details, responsive coordinates, bilingual fallback and map isolation.');
