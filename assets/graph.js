/* Knowledge graph explorer. Data: assets/graph_data.js (built by scripts/export_graph.py). */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const fail = msg => { const e = $('kg-error'); e.hidden = false; e.innerHTML = '<strong>Could not render the graph.</strong> ' + esc(msg); $('kg-loading').hidden = true; };

  /* ---- theme toggle (shared key with the main page) ---- */
  const themeButton = $('theme-toggle');
  let repaint = () => {};
  themeButton.addEventListener('click', () => {
    const t = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem('geoai-release-theme', t); } catch (_) { /* Storage is optional. */ }
    repaint();
  });

  if (typeof vis === 'undefined') return fail('assets/vendor/vis-network.min.js did not load.');
  if (!window.GRAPH_DATA) return fail('assets/graph_data.js did not load. Run python3 scripts/make_page.py.');
  const D = window.GRAPH_DATA;

  const TYPE = {
    TechnicalFeature: { v: '--kg-tf', label: 'Technical feature', desc: 'A reported method, model, data attribute or processing step: the starting point of a pathway.' },
    RiskMechanism: { v: '--kg-rm', label: 'Risk mechanism', desc: 'The process by which a feature can lead to harm.' },
    EthicalImpact: { v: '--kg-ei', label: 'Ethical impact', desc: 'A harm to people or society; each carries a harm family.' },
    Mitigation: { v: '--kg-mi', label: 'Mitigation', desc: 'A safeguard that inhibits a mechanism or impact.' },
    HarmCategory: { v: '--kg-hc', label: 'Harm category', desc: 'One of five harm-family hubs that ethical impacts roll up to via IS_A.' },
  };
  const REL = {
    PROMOTES: { v: '--kg-promotes', desc: 'The source makes the target more likely.' },
    INHIBITS: { v: '--kg-inhibits', desc: 'The source reduces or blocks the target.' },
    IS_A: { v: '--kg-isa', desc: 'Concept hierarchy: the source is a kind of the target.' },
  };
  const HARM_LABEL = { PrivacyViolation: 'Privacy violation', EqualRightsViolation: 'Equal-rights violation', PhysicalHarm: 'Physical harm', EconomicLoss: 'Economic loss', PsychologicalHarm: 'Psychological harm' };
  const harmLabel = k => HARM_LABEL[k] || k;
  const typeOf = t => TYPE[t] || { v: '--muted', label: t, desc: '' };
  const relOf = r => REL[r] || { v: '--muted', desc: '' };
  const wrap = (s, n) => { const out = []; let line = ''; for (const w of String(s).split(' ')) { if ((line + ' ' + w).trim().length > n) { if (line) out.push(line.trim()); line = w; } else line += ' ' + w; } if (line.trim()) out.push(line.trim()); return out.join('\n'); };

  const byId = new Map(D.nodes.map(n => [n.id, n]));
  const degMax = Math.max(1, ...D.nodes.map(n => n.degree));
  const wMax = Math.max(1, ...D.edges.map(e => e.weight));
  const LEVEL = { TechnicalFeature: 0, Mitigation: 1, RiskMechanism: 1, EthicalImpact: 2, HarmCategory: 3 };

  /* ---- state ---- */
  const shownTypes = new Set(Object.keys(TYPE));
  let showIsa = true, layered = false, physicsOn = false, focusSet = null, selected = null;

  function nodeStyle(n) {
    const merged = n.merged_from && n.merged_from.length;
    const c = css(typeOf(n.type).v), bg = css('--kg-canvas'), ink = css('--ink');
    const dim = focusSet && !focusSet.has(n.id);
    return {
      color: { background: c, border: merged ? css('--kg-merge') : bg, highlight: { background: c, border: ink }, hover: { background: c, border: ink } },
      opacity: dim ? 0.12 : 1,
      font: { color: dim ? 'rgba(0,0,0,0)' : ink, strokeColor: bg, strokeWidth: 4, size: 12, face: css('--font') || 'sans-serif' },
      hidden: !shownTypes.has(n.type) || (!showIsa && n.type === 'HarmCategory'),
    };
  }
  function edgeStyle(e) {
    const isa = e.relation === 'IS_A';
    const vis_ = !(focusSet && !(focusSet.has(e.from) && focusSet.has(e.to)));
    const a = byId.get(e.from), b = byId.get(e.to);
    return {
      color: { color: css(relOf(e.relation).v), highlight: css(relOf(e.relation).v), hover: css(relOf(e.relation).v), opacity: vis_ ? (isa ? 0.55 : 0.75) : 0.04 },
      hidden: (isa && !showIsa) || !shownTypes.has(a.type) || !shownTypes.has(b.type) || (!showIsa && (a.type === 'HarmCategory' || b.type === 'HarmCategory')),
    };
  }

  const nodes = new vis.DataSet(D.nodes.map(n => Object.assign({
    id: n.id, label: wrap(n.label, 22), level: LEVEL[n.type] ?? 1,
    shape: n.type === 'HarmCategory' ? 'square' : n.is_concept ? 'triangle' : 'dot',
    size: (n.type === 'HarmCategory' ? 14 : 7) + 20 * Math.sqrt(n.degree / degMax),
    borderWidth: n.merged_from ? 3 : 1.5, title: undefined,
  }, nodeStyle(n))));
  const edges = new vis.DataSet(D.edges.map((e, i) => Object.assign({
    id: 'e' + i, from: e.from, to: e.to,
    arrows: e.relation === 'IS_A' ? { to: false } : { to: { enabled: true, scaleFactor: 0.5 } },
    dashes: e.relation === 'IS_A' ? [3, 4] : false,
    width: e.relation === 'IS_A' ? 0.7 : 1 + 3 * (e.weight / wMax),
    smooth: { type: 'dynamic' },
  }, edgeStyle(e))));
  const edgeRaw = new Map(D.edges.map((e, i) => ['e' + i, e]));

  const FORCE = { enabled: true, solver: 'forceAtlas2Based', forceAtlas2Based: { gravitationalConstant: -45, centralGravity: 0.008, springLength: 120, springConstant: 0.06, damping: 0.5, avoidOverlap: 0.6 }, stabilization: { iterations: 260 }, minVelocity: 0.5 };
  const net = new vis.Network($('kg-net'), { nodes, edges }, {
    layout: { improvedLayout: false },
    physics: FORCE,
    interaction: { hover: true, keyboard: false, tooltipDelay: 200, zoomSpeed: 0.7 },
    edges: { selectionWidth: 1.5 },
  });

  function restyle() {
    nodes.update(D.nodes.map(n => Object.assign({ id: n.id }, nodeStyle(n))));
    edges.update(D.edges.map((e, i) => Object.assign({ id: 'e' + i }, edgeStyle(e))));
  }
  repaint = () => { restyle(); renderRail(); };

  /* ---- rail ---- */
  const nCausal = D.edges.filter(e => e.relation !== 'IS_A').length;
  $('s-nodes').textContent = D.stats.nodes;
  $('s-causal').textContent = nCausal;
  $('s-isa').textContent = D.edges.length - nCausal;
  $('kg-graph-link').href = D.graph;
  const list = $('kg-node-list');
  [...D.nodes].sort((a, b) => a.label.localeCompare(b.label)).forEach(n => { const o = document.createElement('option'); o.value = n.label; list.appendChild(o); });

  let harmActive = null;
  function renderRail() {
    const legend = $('kg-legend'); legend.innerHTML = '';
    Object.keys(TYPE).forEach(t => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'kg-row'; b.setAttribute('aria-pressed', String(shownTypes.has(t)));
      b.innerHTML = `<span class="kg-dot" style="background:${css(TYPE[t].v)}${t === 'HarmCategory' ? ';border-radius:2px' : ''}"></span><span>${TYPE[t].label}<small>${esc(TYPE[t].desc)}</small></span><span class="ct">${D.stats.by_type[t] || 0}</span>`;
      b.onclick = () => { shownTypes.has(t) ? shownTypes.delete(t) : shownTypes.add(t); restyle(); renderRail(); };
      legend.appendChild(b);
    });
    const rel = $('kg-relations'); rel.innerHTML = '';
    const tot = Object.values(D.stats.by_relation).reduce((a, b) => a + b, 0) || 1;
    Object.entries(D.stats.by_relation).sort((a, b) => b[1] - a[1]).forEach(([k, v]) => {
      const d = document.createElement('div'); d.className = 'kg-bar'; d.title = relOf(k).desc;
      d.innerHTML = `<div><b>${esc(k)}</b><span>${v}</span></div><i><i style="width:${(100 * v / tot).toFixed(1)}%;background:${css(relOf(k).v)}"></i></i>`;
      rel.appendChild(d);
    });
    const harms = $('kg-harms'); harms.innerHTML = '';
    Object.entries(D.stats.by_harm).sort((a, b) => b[1] - a[1]).forEach(([k, v]) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'kg-row' + (harmActive === k ? ' on' : '');
      b.setAttribute('aria-pressed', 'true');
      b.innerHTML = `<span class="kg-dot" style="background:${css('--kg-ei')}"></span><span>${harmLabel(k)}</span><span class="ct">${v} impacts</span>`;
      b.onclick = () => { if (harmActive === k) { harmActive = null; clearFocus(); } else { harmActive = k; focusHarm(k); } renderRail(); };
      harms.appendChild(b);
    });
  }
  renderRail();

  /* ---- focus + detail ---- */
  function neighbours(id) { const s = new Set([id]); D.edges.forEach(e => { if (e.from === id) s.add(e.to); if (e.to === id) s.add(e.from); }); return s; }
  function clearFocus() { focusSet = null; selected = null; restyle(); }
  function focusHarm(family) {
    const m = new Set();
    D.nodes.forEach(n => { if (n.type === 'HarmCategory' && n.id.toLowerCase().includes(family.toLowerCase())) m.add(n.id); if (n.harm_family === family && n.type === 'EthicalImpact') m.add(n.id); });
    D.edges.forEach(e => { if (e.relation === 'IS_A') return; if (m.has(e.to)) m.add(e.from); });           // direct drivers
    D.edges.forEach(e => { if (e.relation === 'IS_A') return; if (m.has(e.to) && byId.get(e.to).type === 'RiskMechanism') m.add(e.from); }); // features behind those mechanisms
    D.edges.forEach(e => { if (e.relation === 'IS_A' && m.has(e.from)) m.add(e.to); });
    focusSet = m; closeDetail(false); restyle();
    net.fit({ nodes: [...m].filter(id => !nodes.get(id).hidden), animation: { duration: 500 } });
  }
  function openDetail(badge, color, title, body) {
    const b = $('d-badge'); b.textContent = badge; b.style.background = color;
    $('d-title').textContent = title; $('d-body').innerHTML = body; $('kg-detail').hidden = false; document.querySelector('.kg-stage').classList.add('has-detail');
  }
  function closeDetail(reset = true) { $('kg-detail').hidden = true; document.querySelector('.kg-stage').classList.remove('has-detail'); net.unselectAll(); if (reset) { harmActive = null; clearFocus(); renderRail(); } }
  $('d-close').onclick = () => closeDetail();
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && !$('kg-detail').hidden) closeDetail(); });

  function linkButton(e, out) {
    const other = out ? e.to : e.from, o = byId.get(other);
    return `<button type="button" class="kg-link" data-node="${esc(other)}"><b style="color:${css(relOf(e.relation).v)}">${out ? '' : '← '}${esc(e.relation)}${out ? ' →' : ''}</b>${esc(o ? o.label : other)} <span class="kg-more">· ${esc(typeOf(o && o.type).label)}</span></button>`;
  }
  function showNode(id) {
    const n = byId.get(id); if (!n) return;
    selected = id; harmActive = null; focusSet = neighbours(id); restyle(); renderRail();
    const ty = typeOf(n.type);
    const outs = D.edges.filter(e => e.from === id), ins = D.edges.filter(e => e.to === id);
    let body = `<div class="kg-field"><span>Role</span>${esc(ty.desc)}</div>`;
    if (n.harm_family) body += `<div class="kg-field"><span>Harm family</span><span class="kg-chip">${esc(harmLabel(n.harm_family))}</span></div>`;
    if (n.concept) body += `<div class="kg-field"><span>Parent concept</span><button type="button" class="kg-link" data-node="${esc(n.concept)}">${esc(n.concept)}</button></div>`;
    if (n.merged_from) body += `<div class="kg-field"><span>Merged from ${n.merged_from.length} other surface form${n.merged_from.length > 1 ? 's' : ''}</span>${n.merged_from.map(m => `<span class="kg-chip">${esc(m)}</span>`).join('')}</div>`;
    const shown = [...outs.map(e => linkButton(e, true)), ...ins.map(e => linkButton(e, false))];
    body += `<div class="kg-field"><span>Links · ${outs.length} out, ${ins.length} in</span>${shown.slice(0, 40).join('') || '<span class="kg-more">None</span>'}${shown.length > 40 ? `<p class="kg-more">+ ${shown.length - 40} more</p>` : ''}</div>`;
    openDetail(ty.label, css(ty.v), n.label, body);
    net.selectNodes([id]);
  }
  function showEdge(eid) {
    const e = edgeRaw.get(eid); if (!e) return;
    const r = relOf(e.relation), a = byId.get(e.from), b = byId.get(e.to);
    focusSet = new Set([e.from, e.to]); restyle();
    let body = `<div class="kg-field"><span>Meaning</span>${esc(r.desc)}</div>
      <div class="kg-field"><span>From</span><button type="button" class="kg-link" data-node="${esc(e.from)}"><b style="color:${css(typeOf(a.type).v)}">${esc(typeOf(a.type).label)}</b>${esc(a.label)}</button></div>
      <div class="kg-field"><span>To</span><button type="button" class="kg-link" data-node="${esc(e.to)}"><b style="color:${css(typeOf(b.type).v)}">${esc(typeOf(b.type).label)}</b>${esc(b.label)}</button></div>`;
    if (e.conditions) body += `<div class="kg-field"><span>Condition</span>${esc(e.conditions)}</div>`;
    if (e.sources && e.sources.length) body += `<div class="kg-field"><span>Source document${e.sources.length > 1 ? 's' : ''} (${e.sources.length})</span>${e.sources.map(s => `<span class="kg-chip">${esc(s.replace(/\.pdf$/i, ''))}</span>`).join('')}</div>`;
    openDetail(e.relation, css(r.v), `${a.label} → ${b.label}`, body);
    net.selectEdges([eid]);
  }
  $('d-body').addEventListener('click', ev => { const t = ev.target.closest('[data-node]'); if (t) focusNode(t.dataset.node); });
  function focusNode(id) { if (!byId.has(id)) return; const nd = nodes.get(id); if (nd.hidden) { shownTypes.add(byId.get(id).type); restyle(); renderRail(); } net.focus(id, { scale: 1.1, animation: { duration: 450 } }); showNode(id); }

  net.on('click', p => { if (p.nodes.length) showNode(p.nodes[0]); else if (p.edges.length) showEdge(p.edges[0]); else closeDetail(); });

  /* ---- search ---- */
  const search = $('kg-search'), msg = $('kg-search-msg');
  function runSearch() {
    const q = search.value.trim().toLowerCase(); if (!q) { msg.textContent = ''; return; }
    const hits = D.nodes.filter(n => n.label.toLowerCase().includes(q));
    if (!hits.length) { msg.textContent = 'No node matches “' + search.value.trim() + '”.'; return; }
    hits.sort((a, b) => (a.label.toLowerCase() === q ? -1 : 0) - (b.label.toLowerCase() === q ? -1 : 0) || b.degree - a.degree);
    msg.textContent = hits.length === 1 ? '1 match.' : `${hits.length} matches · showing the most connected. Matches are kept visible.`;
    focusNode(hits[0].id);
    if (hits.length > 1) { focusSet = new Set(hits.map(h => h.id)); neighbours(hits[0].id).forEach(x => focusSet.add(x)); restyle(); }
  }
  search.addEventListener('keydown', ev => { if (ev.key === 'Enter') runSearch(); });
  search.addEventListener('change', runSearch);

  /* ---- buttons ---- */
  $('btn-fit').onclick = () => net.fit({ animation: { duration: 450 } });
  const pb = $('btn-physics');
  const setPhysics = on => { physicsOn = on; net.setOptions({ physics: on ? FORCE : { enabled: false } }); pb.textContent = on ? 'Pause physics' : 'Resume physics'; pb.setAttribute('aria-pressed', String(on)); };
  pb.onclick = () => { if (layered) return; setPhysics(!physicsOn); };
  $('btn-isa').onclick = function () { showIsa = !showIsa; this.textContent = showIsa ? 'Hide IS_A' : 'Show IS_A'; this.setAttribute('aria-pressed', String(showIsa)); restyle(); };
  const lb = $('btn-layout');
  lb.onclick = () => {
    layered = !layered;
    lb.textContent = layered ? 'Force layout' : 'Layered layout'; lb.setAttribute('aria-pressed', String(layered));
    pb.disabled = layered;
    $('kg-loading').hidden = false;
    setTimeout(() => {
      net.setOptions(layered
        ? { layout: { hierarchical: { enabled: true, direction: 'LR', sortMethod: 'directed', levelSeparation: 480, nodeSpacing: 26, treeSpacing: 24, shakeTowards: 'roots' } }, physics: { enabled: false } }
        : { layout: { hierarchical: { enabled: false } }, physics: FORCE });
      if (!layered) { physicsOn = true; pb.textContent = 'Pause physics'; net.once('stabilizationIterationsDone', settle); net.stabilize(260); }
      else { net.fit(); $('kg-loading').hidden = true; }
    }, 30);
  };
  // Layered mode uses each node's semantic level (feature → mechanism → impact → harm category).

  function settle() {
    setPhysics(false); net.fit({ animation: false }); $('kg-loading').hidden = true;
    // graph.html#q=<text> (used by links on the main page) runs a search once the layout settles.
    const m = location.hash.match(/^#q=(.+)$/);
    if (m) { search.value = decodeURIComponent(m[1]); runSearch(); }
  }
  net.once('stabilizationIterationsDone', settle);
  let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => net.redraw(), 150); });
})();
