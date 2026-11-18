/* All catalogue and chart data are embedded at build time: no network or CDN required. */
(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('release-data').textContent);
  const $ = id => document.getElementById(id);
  const number = value => Number(value).toLocaleString('en-US');
  const themeButton = $('theme-toggle');
  const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
  let savedTheme = null;
  try { savedTheme = localStorage.getItem('geoai-release-theme'); } catch (_) { /* Storage is optional. */ }
  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    const label = `Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`;
    themeButton.setAttribute('aria-label', label);
    themeButton.title = label;
  }
  applyTheme(savedTheme || (systemTheme.matches ? 'dark' : 'light'));
  themeButton.addEventListener('click', () => {
    savedTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    applyTheme(savedTheme);
    try { localStorage.setItem('geoai-release-theme', savedTheme); } catch (_) { /* Storage is optional. */ }
  });
  systemTheme.addEventListener('change', event => { if (!savedTheme) applyTheme(event.matches ? 'dark' : 'light'); });

  const files = new Map(data.files.map(file => [file.path, file]));
  const rows = [...document.querySelectorAll('#file-list tr')];
  const search = $('file-search');
  const filters = [...document.querySelectorAll('[data-filter]')];
  let category = 'all';
  let expanded = false;
  const limit = 10;
  function renderCatalogue() {
    const query = search.value.trim().toLowerCase();
    const matches = rows.filter(row => {
      const file = files.get(row.dataset.path);
      return (category === 'all' || file.group === category) &&
        (!query || `${file.title} ${file.description} ${file.path} ${file.format}`.toLowerCase().includes(query));
    });
    const shown = expanded ? matches : matches.slice(0, limit);
    const visible = new Set(shown);
    rows.forEach(row => { row.hidden = !visible.has(row); });
    filters.forEach(button => {
      const selected = button.dataset.filter === category;
      button.classList.toggle('active', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
    $('empty-state').hidden = matches.length !== 0;
    $('catalogue-count').textContent = matches.length ?
      `Showing ${shown.length} of ${matches.length} ${matches.length === 1 ? 'file' : 'files'}${query || category !== 'all' ? ' matching your selection' : ' in this release'}` : '0 matching files';
    $('show-more').hidden = matches.length <= limit;
    $('show-more').textContent = expanded ? 'Show fewer files ↑' : `Show all ${matches.length} files ↓`;
  }
  search.addEventListener('input', () => { expanded = false; renderCatalogue(); });
  filters.forEach(button => button.addEventListener('click', () => {
    category = button.dataset.filter; expanded = false; renderCatalogue();
  }));
  $('show-more').addEventListener('click', () => {
    expanded = !expanded;
    renderCatalogue();
    if (!expanded) $('data').scrollIntoView({ block: 'start' });
  });
  $('reset-search').addEventListener('click', () => {
    category = 'all'; search.value = ''; expanded = false; renderCatalogue(); search.focus();
  });
  const catalogueDisclosure = $('catalogue-disclosure');
  function openCatalogueFromHash() {
    if (window.location.hash === '#data') catalogueDisclosure.open = true;
  }
  window.addEventListener('hashchange', openCatalogueFromHash);
  openCatalogueFromHash();
  document.querySelectorAll('a[href="#data"]').forEach(link => link.addEventListener('click', () => {
    catalogueDisclosure.open = true;
  }));
  document.querySelectorAll('[data-category-link]').forEach(link => link.addEventListener('click', () => {
    category = link.dataset.categoryLink; search.value = ''; expanded = false; renderCatalogue();
  }));
  renderCatalogue();

  const dialog = $('file-preview');
  let previewTrigger = null;
  function previewFile(path, trigger) {
    const file = files.get(path);
    if (!file) return;
    previewTrigger = trigger;
    $('preview-title').textContent = file.title;
    $('preview-description').textContent = file.description;
    $('preview-category').textContent = `${file.format} / FILE PREVIEW`;
    $('preview-meta').textContent = `${file.path} · ${file.size}${file.rows !== undefined ? ` · ${number(file.rows)} rows` : ''}`;
    $('preview-download').href = file.path;
    const body = $('preview-body');
    body.replaceChildren();
    if (file.columns) {
      const note = document.createElement('p');
      note.className = 'preview-sample-note';
      note.textContent = `First ${file.sample.length} rows · ${file.columns.length} columns. Scroll horizontally to inspect the table.`;
      const scroller = document.createElement('div');
      scroller.className = 'preview-data-scroll';
      scroller.tabIndex = 0;
      scroller.setAttribute('role', 'region');
      scroller.setAttribute('aria-label', 'Scrollable sample table');
      const table = document.createElement('table');
      const thead = table.createTHead();
      const header = thead.insertRow();
      file.columns.forEach(column => {
        const th = document.createElement('th'); th.scope = 'col'; th.textContent = column; header.append(th);
      });
      const tbody = table.createTBody();
      file.sample.forEach(values => {
        const row = tbody.insertRow();
        values.forEach(value => { row.insertCell().textContent = value || '—'; });
      });
      scroller.append(table); body.append(note, scroller);
    } else {
      const pre = document.createElement('pre');
      pre.className = 'preview-code'; pre.tabIndex = 0;
      pre.textContent = file.preview || 'Download this resource to inspect the full contents.';
      body.append(pre);
    }
    dialog.showModal();
    document.body.style.overflow = 'hidden';
  }
  document.querySelectorAll('[data-preview]').forEach(button => button.addEventListener('click', () => previewFile(button.dataset.preview, button)));
  $('close-preview').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    const r = dialog.getBoundingClientRect();
    if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();
  });
  dialog.addEventListener('close', () => {
    document.body.style.overflow = '';
    if (previewTrigger) previewTrigger.focus();
  });

  // Tabs expose one saved case at a time; arrow keys follow the tablist pattern.
  const caseTabs = [...document.querySelectorAll('[data-case]')];
  function selectCase(tab) {
    caseTabs.forEach(item => {
      const selected = item === tab;
      item.setAttribute('aria-selected', String(selected));
      item.tabIndex = selected ? 0 : -1;
      $(item.getAttribute('aria-controls')).hidden = !selected;
    });
  }
  caseTabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectCase(tab));
    tab.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % caseTabs.length;
      if (event.key === 'ArrowLeft') next = (index + caseTabs.length - 1) % caseTabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = caseTabs.length - 1;
      if (next === undefined) return;
      event.preventDefault(); selectCase(caseTabs[next]); caseTabs[next].focus();
    });
  });

  // Annual volumes use the released aggregate counts; 2026 is a partial year.
  const annual = data.annual.filter(row => Number(row.value) >= 2010);
  const svg = $('annual-chart');
  const NS = 'http://www.w3.org/2000/svg';
  const element = (tag, attributes, text) => {
    const node = document.createElementNS(NS, tag);
    Object.entries(attributes).forEach(([name, value]) => node.setAttribute(name, value));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  function drawChart(metric) {
    svg.replaceChildren();
    const isPaper = metric === 'n_papers';
    const noun = isPaper ? 'papers' : 'triples';
    svg.setAttribute('aria-label', `Annual ${noun} from 2010 to 2026. The 2026 volume is partial. Focus individual bars for counts.`);
    const title = element('title', {}, `Annual ${noun} in the audited corpus, 2010–2026`);
    svg.append(title);
    const max = Math.ceil(Math.max(...annual.map(row => Number(row[metric]))) / (isPaper ? 1000 : 5000)) * (isPaper ? 1000 : 5000);
    const left = 33, top = 13, bottom = 180, width = 460, height = bottom - top;
    [0, .5, 1].forEach(fraction => {
      const y = bottom - fraction * height;
      svg.append(element('line', { x1: left, y1: y, x2: 499, y2: y, class: 'chart-grid' }));
      svg.append(element('text', { x: left - 7, y: y + 3, 'text-anchor': 'end' }, fraction === 0 ? '0' : `${max * fraction / 1000}k`));
    });
    const gap = width / annual.length;
    const readout = row => { $('chart-readout').textContent = `${row.value}${row.value === '2026' ? '*' : ''} · ${number(row[metric])} ${noun}`; };
    annual.forEach((row, i) => {
      const count = Number(row[metric]);
      const barHeight = Math.max(1.5, count / max * height);
      const rect = element('rect', { x: left + i * gap + 3, y: bottom - barHeight, width: gap - 7, height: barHeight, class: `chart-bar${row.value === '2026' ? ' partial' : ''}`, tabindex: '0', role: 'img', 'aria-label': `${row.value}: ${number(count)} ${noun}${row.value === '2026' ? ', partial year' : ''}` });
      rect.append(element('title', {}, `${row.value}: ${number(count)} ${noun}`));
      rect.addEventListener('mouseenter', () => readout(row));
      rect.addEventListener('focus', () => readout(row));
      svg.append(rect);
      if (['2010', '2015', '2020', '2025', '2026'].includes(row.value)) {
        svg.append(element('text', { x: left + i * gap + gap / 2, y: 202, 'text-anchor': 'middle' }, row.value === '2026' ? '26*' : row.value));
      }
    });
    readout(annual.find(row => row.value === '2025') || annual[annual.length - 1]);
    $('chart-label').textContent = `${isPaper ? 'Papers' : 'Triples'} per year`;
    document.querySelectorAll('[data-metric]').forEach(button => {
      const selected = button.dataset.metric === metric;
      button.classList.toggle('selected', selected); button.setAttribute('aria-pressed', String(selected));
    });
  }
  document.querySelectorAll('[data-metric]').forEach(button => button.addEventListener('click', () => drawChart(button.dataset.metric)));
  if (svg) drawChart('n_papers');

  let toastTimer;
  function toast(message) {
    clearTimeout(toastTimer); $('toast').textContent = message; $('toast').hidden = false;
    toastTimer = setTimeout(() => { $('toast').hidden = true; }, 3500);
  }
  $('copy-citation')?.addEventListener('click', async () => {
    const citation = $('citation-text').textContent;
    try {
      if (!navigator.clipboard) throw new Error('Clipboard API unavailable');
      await navigator.clipboard.writeText(citation);
      toast('Citation copied to clipboard.');
    } catch (_) {
      const selection = window.getSelection();
      const range = document.createRange(); range.selectNodeContents($('citation-text'));
      selection.removeAllRanges(); selection.addRange(range);
      toast('Citation selected. Use your keyboard or context menu to copy.');
    }
  });
})();
