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
  function rankRecords(records, query) {
    const words = normalize(query).split(/\s+/).filter(Boolean);
    const rank = record => {
      const title = normalize(record.title || '');
      return title === normalize(query) ? 0 : words.every(word => title.includes(word)) ? 1 : 2;
    };
    return [...records].sort((a, b) => rank(a) - rank(b));
  }
  if (typeof module !== 'undefined') module.exports = {filterRecords, pageRecords, rankRecords};
  if (typeof document === 'undefined') return;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const label = (template, values) => template.replace(/\{(\w+)\}/g, (_, key) => String(values[key]));

  // Both searches share modal focus, scrolling and close behavior.
  function bindDialog(dialog, trigger, onOpen, siteSearch = false) {
    if (typeof dialog.showModal !== 'function') return null;
    let closing = false;
    let savedY = 0;
    let previousOverflow = '';
    let previousPadding = '';
    const header = document.querySelector('.masthead');
    function align() {
      if (siteSearch) dialog.style.setProperty('--search-top', `${window.innerWidth <= 600 ? 0 : header.getBoundingClientRect().height}px`);
    }
    function close() {
      if (!dialog.open || closing) return;
      closing = true;
      if (reduced.matches || typeof dialog.animate !== 'function') {dialog.close(); return;}
      const animation = dialog.animate([{opacity: 1, transform: 'translateY(0)'}, {opacity: 0, transform: 'translateY(12px)'}], {duration: 160, easing: 'ease-in', fill: 'forwards'});
      animation.finished.then(() => {dialog.close(); animation.cancel();}, () => dialog.close());
    }
    function open() {
      if (dialog.open) return;
      savedY = window.scrollY;
      previousOverflow = document.body.style.overflow;
      previousPadding = document.body.style.paddingRight;
      const scrollbar = window.innerWidth - document.documentElement.clientWidth;
      const padding = parseFloat(getComputedStyle(document.body).paddingRight) || 0;
      document.body.style.paddingRight = `${padding + scrollbar}px`;
      document.body.style.overflow = 'hidden';
      if (siteSearch) header.classList.remove('masthead--hidden');
      align();
      closing = false;
      dialog.showModal();
      trigger.setAttribute('aria-expanded', 'true');
      onOpen();
      dialog.querySelector('[data-search-input]').focus({preventScroll: true});
    }
    trigger.hidden = false;
    trigger.addEventListener('click', open);
    trigger.addEventListener('focus', () => {if (siteSearch) header.classList.remove('masthead--hidden');});
    dialog.querySelector('[data-dialog-close],[data-archive-close]').addEventListener('click', close);
    dialog.addEventListener('cancel', event => {event.preventDefault(); close();});
    dialog.addEventListener('keydown', event => {
      if (event.key === 'Escape') {event.preventDefault(); close(); return;}
      if (event.key !== 'Tab') return;
      const controls = Array.from(dialog.querySelectorAll('button:not(:disabled),input:not(:disabled),a[href]'))
        .filter(element => element.getClientRects().length > 0);
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {event.preventDefault(); last.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first.focus();}
    });
    dialog.addEventListener('click', event => {
      const rect = dialog.getBoundingClientRect();
      if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) close();
    });
    dialog.addEventListener('close', () => {
      document.body.style.overflow = previousOverflow;
      document.body.style.paddingRight = previousPadding;
      trigger.setAttribute('aria-expanded', 'false');
      trigger.focus({preventScroll: true});
      window.scrollTo({top: savedY, behavior: 'instant'});
      closing = false;
    });
    window.addEventListener('resize', () => {if (dialog.open) align();}, {passive: true});
    return {open, close};
  }

  const dialog = document.querySelector('[data-site-search]');
  const trigger = document.querySelector('[data-site-search-open]');
  if (dialog && trigger) {
    const input = dialog.querySelector('[data-search-input]');
    const clear = dialog.querySelector('[data-search-clear]');
    const results = dialog.querySelector('[data-site-search-results]');
    const status = dialog.querySelector('[data-search-status]');
    const empty = dialog.querySelector('[data-search-empty]');
    const retry = dialog.querySelector('[data-search-retry]');
    const scroll = dialog.querySelector('[data-site-search-scroll]');
    const pager = dialog.querySelector('[data-search-pagination]');
    const previous = dialog.querySelector('[data-search-previous]');
    const next = dialog.querySelector('[data-search-next]');
    const pageLabel = dialog.querySelector('[data-search-page]');
    const tabs = Array.from(dialog.querySelectorAll('[data-site-search-kind]'));
    let records;
    let loading;
    let scope = 'all';
    let page = 1;
    let composing = false;

    function render() {
      clear.hidden = !input.value;
      if (!records) return;
      const query = input.value.trim();
      const matches = rankRecords(filterRecords(records, query), query);
      tabs.forEach(tab => {
        const kind = tab.dataset.siteSearchKind;
        tab.setAttribute('aria-pressed', String(scope === kind));
        tab.querySelector('[data-site-search-count]').textContent = String(kind === 'all' ? matches.length : matches.filter(record => record.kind === kind).length);
      });
      const filtered = scope === 'all' ? matches : matches.filter(record => record.kind === scope);
      const slice = pageRecords(filtered, page);
      page = slice.page;
      results.replaceChildren();
      slice.items.forEach(record => {
        const row = document.createElement('li');
        const link = document.createElement('a');
        const target = new URL(record.url, location.origin);
        if (target.origin !== location.origin) return;
        link.href = target.pathname + target.hash;
        const meta = document.createElement('span'); meta.className = 'site-search-result-meta';
        meta.textContent = record.category + (record.date ? ' · ' + record.date : '');
        const title = document.createElement('span'); title.className = 'site-search-result-title'; title.textContent = record.title;
        const summary = document.createElement('p'); summary.textContent = record.description;
        const arrow = document.createElement('span'); arrow.className = 'site-search-result-arrow'; arrow.textContent = '›'; arrow.setAttribute('aria-hidden', 'true');
        link.append(meta, title, summary, arrow); row.append(link); results.append(row);
      });
      status.textContent = query ? label(status.dataset.countLabel, {count: filtered.length}) : status.dataset.explore;
      empty.hidden = filtered.length !== 0;
      retry.hidden = true;
      pager.hidden = slice.pages <= 1;
      previous.disabled = page === 1;
      next.disabled = page === slice.pages;
      pageLabel.textContent = label(pageLabel.dataset.pageLabel, {page, pages: slice.pages});
      scroll.scrollTop = 0;
    }
    async function load() {
      if (records) {render(); return;}
      status.textContent = status.dataset.loading;
      retry.hidden = true;
      if (!loading) {
        loading = fetch(dialog.dataset.source).then(response => {
          if (!response.ok) throw new Error('Search response failed');
          return response.json();
        }).then(data => {
          if (data.version !== 1 || !Array.isArray(data.records)) throw new Error('Invalid search index');
          records = data.records;
        });
      }
      try {await loading; render();}
      catch {loading = undefined; status.textContent = status.dataset.error; retry.hidden = false;}
    }
    const controller = bindDialog(dialog, trigger, () => {page = 1; load();}, true);
    function search() {
      page = 1;
      render();
      const address = new URL(location.href);
      if (input.value.trim()) address.searchParams.set('q', input.value.trim()); else address.searchParams.delete('q');
      history.replaceState(history.state, '', address.pathname + address.search + address.hash);
    }
    input.addEventListener('compositionstart', () => {composing = true;});
    input.addEventListener('compositionend', () => {composing = false; search();});
    input.addEventListener('input', () => {if (!composing) search();});
    clear.addEventListener('click', () => {input.value = ''; search(); input.focus();});
    retry.addEventListener('click', load);
    tabs.forEach(tab => tab.addEventListener('click', () => {scope = tab.dataset.siteSearchKind; page = 1; render();}));
    previous.addEventListener('click', () => {page--; render();});
    next.addEventListener('click', () => {page++; render();});
    dialog.addEventListener('close', () => {
      const address = new URL(location.href); address.searchParams.delete('q');
      history.replaceState(history.state, '', address.pathname + address.search + address.hash);
    });
    const query = new URL(location.href).searchParams.get('q');
    if (query && controller) {input.value = query; controller.open();}
  }

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
    let composing = false;
    scroll.prepend(list);
    fallback.hidden = true;
    function filter() {
      const matches = new Set(filterRecords(rows, input.value));
      rows.forEach(row => {row.element.hidden = !matches.has(row);});
      clear.hidden = !input.value;
      empty.hidden = matches.size !== 0;
      status.textContent = label(status.dataset.countLabel, {count: matches.size});
      scroll.scrollTop = 0;
    }
    bindDialog(dialog, trigger, () => {input.value = ''; filter();});
    input.addEventListener('compositionstart', () => {composing = true;});
    input.addEventListener('compositionend', () => {composing = false; filter();});
    input.addEventListener('input', () => {if (!composing) filter();});
    clear.addEventListener('click', () => {input.value = ''; filter(); input.focus();});
  });
})();
