'use strict';
(() => {
  const PAGE_SIZE = 6;
  function normalize(value) {
    return String(value).normalize('NFKC').toLocaleLowerCase().replace(/(\d)[./](?=\d)/g, '$1-').trim();
  }
  function filterRecords(records, query) {
    const words = normalize(query).split(/\s+/).filter(Boolean);
    return records.filter(record => words.every(word => normalize(record.text).includes(word)));
  }
  function pageRecords(records, page) {
    const pages = Math.max(1, Math.ceil(records.length / PAGE_SIZE));
    const current = Math.min(pages, Math.max(1, page));
    return {items: records.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE), page: current, pages};
  }
  if (typeof module !== 'undefined') module.exports = {filterRecords, pageRecords};
  if (typeof document === 'undefined') return;

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const label = (template, values) => template.replace(/\{(\w+)\}/g, (_, key) => String(values[key]));

  document.querySelectorAll('[data-research-search]').forEach(root => {
    let records;
    try {records = JSON.parse(root.querySelector('[data-search-data]').textContent);} catch {return;}
    const input = root.querySelector('[data-search-input]');
    const clear = root.querySelector('[data-search-clear]');
    const original = root.querySelector('[data-search-default]');
    const results = root.querySelector('[data-search-results]');
    const grid = root.querySelector('[data-search-grid]');
    const status = root.querySelector('[data-search-status]');
    const empty = root.querySelector('[data-search-empty]');
    const pager = root.querySelector('[data-search-pagination]');
    const previous = root.querySelector('[data-search-previous]');
    const next = root.querySelector('[data-search-next]');
    const pageLabel = root.querySelector('[data-search-page]');
    const links = Array.from(document.querySelectorAll('.research-filter a,.lang-toggle'), element => ({element, href: element.getAttribute('href')}));
    let page = 1;
    let composing = false;

    function render(updateURL = true) {
      const query = input.value.trim();
      clear.hidden = !input.value;
      original.hidden = Boolean(query);
      results.hidden = !query;
      grid.replaceChildren();
      if (query) {
        const matches = filterRecords(records, query);
        const slice = pageRecords(matches, page);
        page = slice.page;
        const fragment = document.createDocumentFragment();
        slice.items.forEach(record => {
          // Markup is escaped and generated from the same published cards at build time.
          // Never interpolate the user's query into HTML.
          const template = document.createElement('template');
          template.innerHTML = record.html;
          fragment.append(...template.content.querySelector('.research-grid').children);
        });
        grid.append(fragment);
        status.textContent = label(status.dataset.countLabel, {count: matches.length});
        empty.hidden = matches.length !== 0;
        pager.hidden = slice.pages <= 1;
        previous.disabled = page === 1;
        next.disabled = page === slice.pages;
        pageLabel.textContent = label(pageLabel.dataset.pageLabel, {page, pages: slice.pages});
      }
      links.forEach(({element, href}) => {
        const target = new URL(href, location.href);
        if (query) target.searchParams.set('q', query); else target.searchParams.delete('q');
        element.href = target.pathname + target.search + target.hash;
      });
      if (updateURL) {
        const address = new URL(location.href);
        if (query) address.searchParams.set('q', query); else address.searchParams.delete('q');
        history.replaceState(history.state, '', address.pathname + address.search + address.hash);
      }
    }
    input.addEventListener('compositionstart', () => {composing = true;});
    input.addEventListener('compositionend', () => {composing = false; page = 1; render();});
    input.addEventListener('input', () => {if (!composing) {page = 1; render();}});
    clear.addEventListener('click', () => {input.value = ''; page = 1; render(); input.focus();});
    function turn(delta) {
      page += delta;
      render();
      results.scrollIntoView({behavior: reduced.matches ? 'instant' : 'smooth', block: 'start'});
    }
    previous.addEventListener('click', () => turn(-1));
    next.addEventListener('click', () => turn(1));
    window.addEventListener('popstate', () => {input.value = new URL(location.href).searchParams.get('q') || ''; page = 1; render(false);});
    input.value = new URL(location.href).searchParams.get('q') || '';
    root.querySelector('[data-search-controls]').hidden = false;
    render(false);
  });

  document.querySelectorAll('[data-snapshot-archive]').forEach(root => {
    const dialog = root.querySelector('[data-archive-dialog]');
    if (typeof dialog.showModal !== 'function') return;
    const trigger = root.querySelector('[data-archive-open]');
    const fallback = root.querySelector('[data-archive-fallback]');
    const list = fallback.querySelector('.snapshot-list');
    const scroll = dialog.querySelector('[data-archive-scroll]');
    const input = dialog.querySelector('[data-search-input]');
    const clear = dialog.querySelector('[data-search-clear]');
    const empty = dialog.querySelector('[data-search-empty]');
    const status = dialog.querySelector('[data-search-status]');
    const rows = Array.from(list.children, element => ({element, text: element.textContent}));
    scroll.prepend(list);
    trigger.hidden = false;
    fallback.hidden = true;
    let closing = false;
    let composing = false;
    let savedY = 0;
    let previousOverflow = '';
    let previousPadding = '';

    function filter() {
      const matches = new Set(filterRecords(rows, input.value));
      rows.forEach(row => {row.element.hidden = !matches.has(row);});
      clear.hidden = !input.value;
      empty.hidden = matches.size !== 0;
      status.textContent = label(status.dataset.countLabel, {count: matches.size});
      scroll.scrollTop = 0;
    }
    function close() {
      if (!dialog.open || closing) return;
      closing = true;
      if (reduced.matches || typeof dialog.animate !== 'function') {dialog.close(); return;}
      const animation = dialog.animate([{opacity: 1, transform: 'translateY(0)'}, {opacity: 0, transform: 'translateY(12px)'}], {duration: 160, easing: 'ease-in', fill: 'forwards'});
      animation.finished.then(() => {dialog.close(); animation.cancel();}, () => dialog.close());
    }
    trigger.addEventListener('click', () => {
      if (dialog.open) return;
      savedY = window.scrollY;
      previousOverflow = document.body.style.overflow;
      previousPadding = document.body.style.paddingRight;
      const scrollbar = window.innerWidth - document.documentElement.clientWidth;
      const padding = parseFloat(getComputedStyle(document.body).paddingRight) || 0;
      document.body.style.paddingRight = `${padding + scrollbar}px`;
      document.body.style.overflow = 'hidden';
      input.value = '';
      filter();
      closing = false;
      dialog.showModal();
      input.focus({preventScroll: true});
    });
    dialog.querySelector('[data-archive-close]').addEventListener('click', close);
    dialog.addEventListener('cancel', event => {event.preventDefault(); close();});
    dialog.addEventListener('keydown', event => {
      if (event.key !== 'Tab') return;
      const controls = Array.from(dialog.querySelectorAll('button:not(:disabled),input:not(:disabled),a[href]'))
        .filter(element => element.getClientRects().length > 0);
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    });
    dialog.addEventListener('click', event => {
      const rect = dialog.getBoundingClientRect();
      if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) close();
    });
    dialog.addEventListener('close', () => {
      document.body.style.overflow = previousOverflow;
      document.body.style.paddingRight = previousPadding;
      trigger.focus({preventScroll: true});
      window.scrollTo({top: savedY, behavior: 'instant'});
      closing = false;
    });
    input.addEventListener('compositionstart', () => {composing = true;});
    input.addEventListener('compositionend', () => {composing = false; filter();});
    input.addEventListener('input', () => {if (!composing) filter();});
    clear.addEventListener('click', () => {input.value = ''; filter(); input.focus();});
  });
})();
