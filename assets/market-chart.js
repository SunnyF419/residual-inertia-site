'use strict';
// Calendar windows and raw scores are shared by rendering and regression checks.
(function () {
  const day = value => Date.parse(value + 'T00:00:00Z');
  function tone(score) {
    if (score < 35) return 'constructive';
    if (score < 50) return 'neutral';
    if (score < 65) return 'caution';
    if (score < 80) return 'defensive';
    return 'stress';
  }
  function windowStart(end, months) {
    const d = new Date(day(end));
    const target = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() - months, 1));
    const last = new Date(Date.UTC(target.getUTCFullYear(), target.getUTCMonth() + 1, 0)).getUTCDate();
    target.setUTCDate(Math.min(d.getUTCDate(), last));
    return target.toISOString().slice(0, 10);
  }
  function select(data, months) {
    const start = months === 60 ? data.windowStart : windowStart(data.windowEnd, months);
    return {start, end: data.windowEnd, points: data.points.filter(p => p.date >= start && p.date <= data.windowEnd)};
  }
  function nearest(points, time) {
    let lo = 0, hi = points.length - 1;
    while (lo < hi) {
      const mid = Math.floor((lo + hi) / 2);
      if (day(points[mid].date) < time) lo = mid + 1;
      else hi = mid;
    }
    return lo > 0 && time - day(points[lo - 1].date) <= day(points[lo].date) - time ? lo - 1 : lo;
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {tone, windowStart, select, nearest};
  if (typeof document === 'undefined') return;
  const ns = 'http://www.w3.org/2000/svg';
  function node(tag, attrs, text) {
    const el = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
    if (text !== undefined) el.textContent = text;
    return el;
  }
  document.querySelectorAll('[data-market-chart]').forEach(panel => {
    const data = JSON.parse(panel.querySelector('[data-chart-data]').textContent);
    if (!data.points.length) return;
    const plot = panel.querySelector('.market-plot');
    const svg = panel.querySelector('.market-svg');
    const slider = panel.querySelector('[data-chart-slider]');
    const tooltip = panel.querySelector('[data-chart-tooltip]');
    const cursor = panel.querySelector('[data-chart-cursor]');
    const readout = panel.querySelector('[data-chart-readout]');
    const ranges = [...panel.querySelectorAll('[data-chart-range]')];
    let months = 60, view = select(data, months), geometry, selected = null;
    function hide() { tooltip.hidden = true; cursor.setAttribute('hidden', ''); selected = null; }
    function describe(p) { return `${p.date} · ${p.score.toFixed(1)} / 100 · ${p.label}`; }
    function show(index, announce = false) {
      const p = view.points[index];
      selected = index;
      const x = geometry.x(p.date), y = geometry.y(p.score);
      cursor.removeAttribute('hidden');
      const line = cursor.querySelector('line'), circle = cursor.querySelector('circle');
      for (const [key, value] of Object.entries({x1:x, x2:x, y1:geometry.top, y2:geometry.bottom})) line.setAttribute(key, value);
      circle.setAttribute('cx', x); circle.setAttribute('cy', y);
      circle.setAttribute('class', 'market-hover-point tone-' + tone(p.score));
      tooltip.textContent = describe(p);
      tooltip.className = 'market-tooltip tone-' + tone(p.score);
      tooltip.hidden = false;
      tooltip.style.left = Math.max(4, Math.min(x - 110, geometry.width - tooltip.offsetWidth - 4)) + 'px';
      tooltip.style.top = Math.max(4, Math.min(y - 48, geometry.height - tooltip.offsetHeight - 4)) + 'px';
      if (announce) {
        readout.textContent = describe(p);
        readout.className = 'score-value tone-' + tone(p.score);
        slider.setAttribute('aria-valuetext', describe(p));
      }
    }
    function render() {
      const width = Math.max(240, plot.getBoundingClientRect().width);
      const height = plot.getBoundingClientRect().height || 300;
      const left = 34, right = width - 14, top = 18, bottom = height - 32;
      const start = day(view.start), duration = Math.max(day(view.end) - start, 1);
      geometry = {width, height, top, bottom,
        x: date => left + (day(date) - start) / duration * (right - left),
        y: score => bottom - score / 100 * (bottom - top)};
      svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
      const {x, y} = geometry;
      const bands = [[0,35,'constructive'],[35,50,'neutral'],[50,65,'caution'],[65,80,'defensive'],[80,100,'stress']];
      panel.querySelector('[data-chart-bands]').replaceChildren(...bands.map(([lo,hi,color]) => node('rect', {
        x:left, y:y(hi), width:right-left, height:y(lo)-y(hi), class:'market-band tone-' + color})));
      const grid = [];
      for (const score of [0,35,50,65,80,100]) {
        grid.push(node('line', {x1:left,x2:right,y1:y(score),y2:y(score)}));
        grid.push(node('text', {x:left-8,y:y(score)+4,'text-anchor':'end'}, score));
      }
      panel.querySelector('[data-chart-grid]').replaceChildren(...grid);
      panel.querySelector('[data-chart-series]').setAttribute('points', view.points.map(p => `${x(p.date).toFixed(2)},${y(p.score).toFixed(2)}`).join(' '));
      const tickCount = width < 500 ? 3 : 6;
      const ticks = [];
      for (let i = 0; i < tickCount; i++) {
        const time = start + duration * i / (tickCount - 1);
        const date = new Date(time).toISOString().slice(0,10);
        const label = months === 60 ? date.slice(0,7) : date.slice(5);
        ticks.push(node('text', {x:left+(right-left)*i/(tickCount-1),y:height-9,'text-anchor':i===0?'start':i===tickCount-1?'end':'middle'}, label));
      }
      panel.querySelector('[data-chart-ticks]').replaceChildren(...ticks);
      const last = view.points[view.points.length-1];
      const marker = panel.querySelector('[data-chart-endpoint]');
      marker.setAttribute('cx', x(last.date)); marker.setAttribute('cy', y(last.score));
      panel.querySelector('#history-desc').textContent = `${view.start} — ${view.end} · ${view.points.length} ${data.countLabel}`;
      panel.querySelector('[data-chart-window]').textContent = `${data.rangeLabel}: ${view.start} — ${view.end} · ${view.points.length} ${data.countLabel}`;
      if (selected !== null) show(selected);
    }
    function resetBrowse() {
      slider.max = view.points.length - 1; slider.value = slider.max;
      const last = view.points[view.points.length-1];
      readout.textContent = describe(last);
      readout.className = 'score-value tone-' + tone(last.score);
      slider.setAttribute('aria-valuetext', describe(last));
    }
    render(); resetBrowse();
    panel.querySelectorAll('[data-chart-controls]').forEach(el => {el.hidden = false;});
    ranges.forEach(button => button.addEventListener('click', () => {
      months = Number(button.dataset.chartRange); view = select(data, months); hide();
      ranges.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      render(); resetBrowse();
    }));
    plot.addEventListener('pointermove', event => {
      const rect = plot.getBoundingClientRect();
      const position = Math.max(0, Math.min(1, (event.clientX - rect.left - 34) / (geometry.width - 48)));
      show(nearest(view.points, day(view.start) + position * (day(view.end) - day(view.start))));
    });
    plot.addEventListener('pointerleave', hide);
    slider.addEventListener('input', () => show(Number(slider.value), true));
    slider.addEventListener('focus', () => show(Number(slider.value)));
    slider.addEventListener('blur', hide);
    if (typeof ResizeObserver !== 'undefined') new ResizeObserver(render).observe(plot);
    else window.addEventListener('resize', render, {passive:true});
  });
})();
