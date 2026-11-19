/* =============================================================================
   Stitchcraft Studio — app.js
   Vanilla frontend for the local studio API (no frameworks, no CDN, no build).
   Markup contract (all present in index.html): wizard #step-1..#step-5 with
   #step-N-toggle/#step-N-panel and [data-goto]; tabs #tab-* / #panel-*; empty
   #pipeline-stages filled with the nine-stage timeline; #log-list; preview
   #preview-frame (#preview-open/#preview-export); #history-dialog; #toasts.
   Optional nodes are appended at runtime (#skills-note, #app-confirm) and every
   lookup is null-safe. Motion: local ./vendor/gsap.min.js, guarded, reduced-
   motion aware. API strings reach the DOM only through textContent — never innerHTML.
   ========================================================================== */
(function () {
  'use strict';

  const I18N = window.StitchcraftI18n || null;
  const JOBS = window.StitchcraftJobs || null;
  const SITE_IMPORT = window.StitchcraftImport || null;

  /* ---------- 1. Constants ------------------------------------------------- */
  const UI_CONFIG = window.StitchcraftConfig || {};
  const { STAGES, PRESETS, FALLBACK_THEMES, STORAGE, POLL_MS, MAX_POLL_FAILS, STEP_COUNT, DONE, CANCELLED, FAIL, STAGE_STATUS, LOG_LEVEL } = UI_CONFIG;
  const providerPreset = (id) => PRESETS[id] || PRESETS.custom;
  const state = {
    online: false, themesOffline: false, settings: null, status: null, themes: [], skills: [], projects: [], selectedThemeId: '',
    currentStep: 1, tab: 'preview', generating: false, jobId: null, jobToken: 0, pollTimer: null, pollFails: 0, progress: 0,
    jobStream: null, importFiles: [], importSkipped: [], importRoot: '', importBytes: 0,
    paintedProgress: 0, stages: [], stageEls: [], latestLogs: [], logCursor: 0, preview: null, runningTitle: '', booting: false,
    confirmResolve: null, modalLastFocus: null };
  const BROWSER_POLL_MS = 900;

  /* ---------- 2. DOM helpers (textContent only) ---------------------------- */
  const $ = (id) => document.getElementById(id);
  function el(tag, cls, text) { const node = document.createElement(tag); if (cls) node.className = cls; if (text != null) node.textContent = String(text); return node; }
  const on = (target, type, handler, options) => { if (target) target.addEventListener(type, handler, options); };
  const clear = (node) => { if (node) while (node.firstChild) node.removeChild(node.firstChild); };
  const clamp = (value, min, max) => Math.min(max, Math.max(min, Number(value) || 0));
  const setText = (id, text) => { const node = $(id); if (node) node.textContent = String(text); };
  const setHidden = (id, hidden) => { const node = $(id); if (node) node.hidden = Boolean(hidden); };
  const readStorage = (key) => { try { return localStorage.getItem(key) || ''; } catch (_) { return ''; } };
  const writeStorage = (key, value) => { try { value ? localStorage.setItem(key, value) : localStorage.removeItem(key); } catch (_) { /* denied */ } };
  const shortPath = (value) => { const text = String(value || ''); return text.length > 52 ? '…' + text.slice(-50) : text; };
  const announce = (message) => setText('sr-status', message);
  function isHttpUrl(value) { try { const url = new URL(value); return url.protocol === 'http:' || url.protocol === 'https:'; } catch (_) { return false; } }
  function formatDate(value) {
    if (!value) return I18N ? I18N.translate('Unknown date') : 'Unknown date';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    try { return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(date); } catch (_) { return String(value); } }
  function trashIcon() {
    const ns = 'http://www.w3.org/2000/svg', svg = document.createElementNS(ns, 'svg'), path = document.createElementNS(ns, 'path');
    svg.setAttribute('viewBox', '0 0 16 16'); svg.setAttribute('aria-hidden', 'true');
    path.setAttribute('d', 'M3 4.6h10M6.4 4.6V3.2h3.2v1.4M4.2 4.6l.6 8.2h6.4l.6-8.2M6.6 7.2v3.4M9.4 7.2v3.4');
    [['fill', 'none'], ['stroke', 'currentColor'], ['stroke-width', '1.6'], ['stroke-linecap', 'round']].forEach(([key, value]) => path.setAttribute(key, value));
    svg.appendChild(path); return svg; }

  /* ---------- 3. Motion (guarded) ------------------------------------------ */
  const REDUCE_QUERY = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  const reducedMotion = () => Boolean(REDUCE_QUERY && REDUCE_QUERY.matches);
  const canAnimate = () => Boolean(window.gsap && window.gsap.timeline) && !reducedMotion();
  function animateEntrance() {
    if (!canAnimate()) return;
    window.gsap.timeline({ defaults: { duration: 0.6, ease: 'power3.out' } })
      .from('.topbar', { y: -16, opacity: 0, duration: 0.5 }).from('.rail__head', { y: 14, opacity: 0 }, '-=0.32')
      .from('.steps .step', { y: 16, opacity: 0, stagger: 0.055 }, '-=0.36').from('.rail__foot', { opacity: 0, y: 8 }, '-=0.34')
      .from('.stage', { y: 22, opacity: 0 }, '-=0.58').from('.ambient__glow', { opacity: 0, scale: 0.92, stagger: 0.16, duration: 1.4 }, 0); }
  function makeEmbers() {
    const host = $('embers'); if (!host || host.childElementCount) return;
    for (let i = 0; i < 16; i += 1) {
      const ember = el('span', 'ember'), size = (2 + Math.random() * 3).toFixed(1) + 'px';
      ember.style.left = (4 + Math.random() * 92).toFixed(2) + '%'; ember.style.width = size; ember.style.height = size;
      ember.style.setProperty('--dur', (11 + Math.random() * 12).toFixed(2) + 's');
      ember.style.setProperty('--delay', (-Math.random() * 18).toFixed(2) + 's');
      ember.style.setProperty('--drift', (Math.random() * 64 - 32).toFixed(1) + 'px');
      host.appendChild(ember); } }

  /* ---------- 4. API layer -------------------------------------------------- */
  async function api(path, options) {
    const init = Object.assign({ cache: 'no-store', credentials: 'same-origin', headers: { Accept: 'application/json' } }, options || {});
    if (init.body != null && typeof init.body !== 'string') { init.body = JSON.stringify(init.body); init.headers = Object.assign({}, init.headers, { 'Content-Type': 'application/json' }); }
    const response = await fetch(path, init), raw = await response.text();
    let data = null;
    if (raw) { try { data = JSON.parse(raw); } catch (_) { data = { message: raw.slice(0, 400) }; } }
    if (!response.ok) { const error = new Error(extractApiError(data, response.status)); error.status = response.status; error.data = data; throw error; }
    return data; }
  function extractApiError(data, status) {
    if (!data || typeof data !== 'object') return 'Request failed (HTTP ' + status + ').';
    const raw = data.error;
    if (typeof raw === 'string' && raw.trim()) return data.message || raw;
    if (raw && typeof raw === 'object' && typeof raw.message === 'string' && raw.message.trim()) return raw.message;
    if (raw && typeof raw === 'object' && typeof raw.code === 'string' && raw.code.trim()) return raw.code;
    if (typeof data.message === 'string' && data.message.trim()) return data.message;
    if (typeof data.detail === 'string' && data.detail.trim()) return data.detail;
    return 'Request failed (HTTP ' + status + ').'; }
  const setBusy = (button, busy) => { if (!button) return; button.disabled = Boolean(busy); busy ? button.setAttribute('aria-busy', 'true') : button.removeAttribute('aria-busy'); };
  const showResult = (node, kind, message) => { if (!node) return; node.dataset.state = kind; node.textContent = String(message || ''); node.hidden = false; };

  /* ---------- 5. Toasts ----------------------------------------------------- */
  function toast(message, type, timeout) {
    const host = $('toasts'); if (!host || !message) return;
    const node = el('div', 'toast'); node.dataset.type = type || 'info'; node.setAttribute('role', 'status');
    node.append(el('span', 'toast__dot'), el('span', 'toast__text', message));
    const dismiss = () => { if (!node.isConnected || node.classList.contains('is-leaving')) return; node.classList.add('is-leaving'); window.setTimeout(() => node.remove(), 240); };
    node.addEventListener('click', dismiss); host.appendChild(node);
    while (host.childElementCount > 4) host.firstElementChild.remove();
    window.setTimeout(dismiss, typeof timeout === 'number' ? timeout : 4600);
    announce(message); }

  /* ---------- 6. Custom confirm modal (never window.confirm) ---------------- */
  function ensureConfirmModal() {
    let modal = $('app-confirm'); if (modal) return modal;
    modal = el('div', 'modal'); modal.id = 'app-confirm'; modal.hidden = true;
    const panel = el('div', 'modal__panel');
    panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-modal', 'true');
    panel.setAttribute('aria-labelledby', 'app-confirm-title'); panel.setAttribute('aria-describedby', 'app-confirm-text');
    const title = el('h2', 'modal__title'); title.id = 'app-confirm-title';
    const text = el('p', 'modal__text'); text.id = 'app-confirm-text';
    const cancel = el('button', 'btn btn--ghost', 'Cancel'); cancel.type = 'button'; cancel.dataset.confirm = 'cancel';
    const accept = el('button', 'btn btn--danger', 'Confirm'); accept.type = 'button'; accept.dataset.confirm = 'accept';
    const actions = el('div', 'modal__actions'); actions.append(cancel, accept);
    panel.append(el('p', 'modal__eyebrow', 'Confirm'), title, text, actions); modal.appendChild(panel); document.body.appendChild(modal);
    modal.addEventListener('click', (event) => { if (event.target === modal) closeConfirm(false); });
    on(cancel, 'click', () => closeConfirm(false)); on(accept, 'click', () => closeConfirm(true));
    return modal; }
  function confirmAction(options) {
    const opts = options || {}, modal = ensureConfirmModal();
    return new Promise((resolve) => {
      if (state.confirmResolve) state.confirmResolve(false);
      state.confirmResolve = resolve; state.modalLastFocus = document.activeElement;
      setText('app-confirm-title', opts.title || 'Are you sure?'); setText('app-confirm-text', opts.message || 'This action cannot be undone.');
      const accept = modal.querySelector('[data-confirm="accept"]'), cancel = modal.querySelector('[data-confirm="cancel"]');
      if (accept) { accept.textContent = opts.confirmLabel || 'Confirm'; accept.className = opts.danger === false ? 'btn btn--primary' : 'btn btn--danger'; }
      modal.hidden = false; if (cancel) cancel.focus(); }); }
  function closeConfirm(result) {
    const modal = $('app-confirm'); if (modal) modal.hidden = true;
    const resolve = state.confirmResolve; state.confirmResolve = null;
    if (state.modalLastFocus && typeof state.modalLastFocus.focus === 'function') { try { state.modalLastFocus.focus({ preventScroll: true }); } catch (_) { /* ignore */ } }
    state.modalLastFocus = null; if (resolve) resolve(Boolean(result)); }
  function trapConfirmFocus(event) {
    const modal = $('app-confirm'); if (!modal || modal.hidden || event.key !== 'Tab') return;
    const focusables = Array.from(modal.querySelectorAll('button:not([disabled])')); if (!focusables.length) return;
    const first = focusables[0], last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); } }

  /* ---------- 7. Tabs ------------------------------------------------------- */
  const TABS = [['preview', 'tab-preview', 'panel-preview'], ['pipeline', 'tab-pipeline', 'panel-pipeline'], ['browser', 'tab-browser', 'panel-browser'], ['logs', 'tab-logs', 'panel-logs']];
  function switchTab(name) {
    TABS.forEach(([key, tabId, panelId]) => {
      const active = key === name, tab = $(tabId), panel = $(panelId);
      if (tab) { tab.classList.toggle('is-active', active); tab.setAttribute('aria-selected', String(active)); tab.tabIndex = active ? 0 : -1; }
      if (panel) { panel.classList.toggle('is-active', active); panel.hidden = !active; } });
    state.tab = name;
    if (name === 'logs') scrollLogsToEnd(true); }
  function initTabs() {
    TABS.forEach(([name, tabId], index) => {
      on($(tabId), 'click', () => switchTab(name));
      on($(tabId), 'keydown', (event) => {
        const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
        if (!step) return;
        event.preventDefault();
        const next = TABS[(index + step + TABS.length) % TABS.length];
        switchTab(next[0]); const target = $(next[1]); if (target) target.focus(); }); }); }

  /* ---------- 8. Wizard steps ---------------------------------------------- */
  function setStepOpen(n, open) {
    const step = $('step-' + n); if (!step) return;
    const toggle = $('step-' + n + '-toggle'), panel = $('step-' + n + '-panel');
    step.classList.toggle('is-open', Boolean(open));
    if (toggle) toggle.setAttribute('aria-expanded', String(Boolean(open)));
    if (panel) panel.inert = !open;
    if (open && canAnimate()) {
      const body = panel && panel.querySelector('.step__body');
      if (body) window.gsap.fromTo(body, { opacity: 0, y: 9 }, { opacity: 1, y: 0, duration: 0.3, ease: 'power2.out', clearProps: 'opacity,transform' }); } }
  function goToStep(n) {
    if (n < 1 || n > STEP_COUNT) return;
    if (n > state.currentStep && state.currentStep === 3 && !currentTheme()) { showThemeError('Pick a theme to continue, or refresh the theme list.'); toast('Pick a theme first.', 'error'); return; }
    if (n > state.currentStep && state.currentStep === 4) { const prompt = $('prompt'); if (!(prompt && prompt.value.trim())) { showPromptError('Write a short brief to continue.'); if (prompt) prompt.focus(); return; } }
    for (let i = 1; i <= STEP_COUNT; i += 1) { const step = $('step-' + i); if (step && i < n) step.classList.add('is-complete'); setStepOpen(i, i === n); }
    state.currentStep = n;
    const toggle = $('step-' + n + '-toggle');
    if (toggle) {
      try { toggle.focus({ preventScroll: true }); } catch (_) { /* ignore */ }
      try { toggle.scrollIntoView({ block: 'nearest', behavior: reducedMotion() ? 'auto' : 'smooth' }); } catch (_) { /* ignore */ } } }
  function initWizard() {
    for (let n = 1; n <= STEP_COUNT; n += 1) {
      on($('step-' + n + '-toggle'), 'click', () => {
        const step = $('step-' + n); if (!step) return;
        if (step.classList.contains('is-open')) { setStepOpen(n, false); return; }
        for (let i = 1; i <= STEP_COUNT; i += 1) if (i !== n) setStepOpen(i, false);
        setStepOpen(n, true); state.currentStep = n; });
      const panel = $('step-' + n + '-panel'); if (panel) panel.inert = n !== 1; }
    on($('steps'), 'click', (event) => {
      const trigger = event.target && event.target.closest ? event.target.closest('[data-goto]') : null;
      if (trigger) { const target = Number(trigger.getAttribute('data-goto')); if (target) goToStep(target); } }); }
  const showPromptError = (message) => { const node = $('prompt-error'); if (node) { node.textContent = message; node.hidden = false; } };
  const showGenerateError = (message) => { const node = $('generate-error'); if (node) { node.textContent = message; node.hidden = false; } };

  /* ---------- 9. Themes ----------------------------------------------------- */
  function normalizeTheme(raw) {
    if (!raw || typeof raw !== 'object') return null;
    const id = String(raw.id || '').trim(); if (!id) return null;
    return {
      id: id, name: String(raw.name || id), category: String(raw.category || 'general'), summary: String(raw.summary || ''),
      accent: /^#[0-9a-f]{3,8}$/i.test(String(raw.accent || '')) ? String(raw.accent) : '#ff8a3d',
      tags: Array.isArray(raw.tags) ? raw.tags.map(String).filter(Boolean) : [], has_sample: Boolean(raw.has_sample),
      design_reference: String(raw.design_reference || '') }; }
  const currentTheme = () => state.themes.find((theme) => theme.id === state.selectedThemeId) || null;
  const themeName = (id) => { const theme = state.themes.find((item) => item.id === id); return theme ? theme.name : String(id || 'Unknown theme'); };
  const showThemeError = (message) => { const node = $('theme-error'); if (node) { node.textContent = message; node.hidden = false; } };
  function updateThemeNote() {
    const note = $('theme-note'); if (!note) return;
    const samples = state.themes.filter((theme) => theme.has_sample).length;
    if (I18N) {
      note.textContent = state.themesOffline ? I18N.translate('Offline — showing the built-in theme catalogue.')
        : state.themes.length ? I18N.format('{count} themes · {samples} with demo samples', { count: state.themes.length, samples: samples })
        : I18N.translate('No themes loaded yet.');
    } else {
      note.textContent = state.themesOffline ? 'Offline — showing the built-in theme catalogue.'
        : state.themes.length ? state.themes.length + ' themes · ' + samples + ' with demo samples' : 'No themes loaded yet.';
    } }
  function renderThemes() {
    const grid = $('theme-grid'); if (!grid) return;
    clear(grid);
    state.themes.forEach((theme) => {
      const card = el('button', 'theme-card');
      card.type = 'button'; card.dataset.themeId = theme.id; card.setAttribute('aria-pressed', 'false'); card.style.setProperty('--theme-accent', theme.accent);
      const top = el('div', 'theme-card__top'); top.append(el('span', 'theme-card__swatch'), el('span', 'theme-card__name', theme.name));
      const badge = el('span', 'theme-card__badge', theme.has_sample ? 'Sample' : 'AI only');
      if (!theme.has_sample) badge.classList.add('theme-card__badge--ai');
      top.appendChild(badge);
      card.appendChild(top);
      if (theme.summary) card.appendChild(el('p', 'theme-card__summary', theme.summary));
      if (theme.tags.length || theme.design_reference) {
        const tags = el('div', 'theme-card__tags');
        theme.tags.slice(0, 4).forEach((tag) => tags.appendChild(el('span', 'theme-card__tag', tag)));
        if (theme.design_reference) tags.appendChild(el('span', 'theme-card__tag', 'design: ' + theme.design_reference));
        card.appendChild(tags);
      }
      card.appendChild(el('span', 'theme-card__check', '✓'));
      card.addEventListener('click', () => selectTheme(theme.id));
      grid.appendChild(card); });
    if (!state.themes.length) grid.appendChild(el('p', 'field__hint', 'No themes found. Refresh, or check the backend.'));
    selectTheme(state.selectedThemeId, { persist: false, silent: true });
    if (!currentTheme() && state.themes.length) selectTheme(state.themes[0].id, { persist: false, silent: true });
    updateThemeNote(); updateDemoButton(); }
  function selectTheme(id, options) {
    const opts = options || {}, theme = state.themes.find((item) => item.id === id) || null;
    state.selectedThemeId = theme ? theme.id : '';
    document.querySelectorAll('.theme-card').forEach((card) => {
      const selected = card.dataset.themeId === state.selectedThemeId;
      card.classList.toggle('is-selected', selected); card.setAttribute('aria-pressed', String(selected)); });
    if (opts.persist !== false) writeStorage(STORAGE.theme, state.selectedThemeId);
    if (!opts.silent) { setHidden('theme-error', true); if (theme) announce('Theme selected: ' + theme.name); }
    updateThemeNote(); updateDemoButton(); updateSummary(); }
  async function loadThemes(options) {
    const opts = options || {}; setHidden('theme-error', true);
    const note = $('theme-note'); if (note) note.textContent = 'Loading themes…';
    try {
      const data = await api('/api/themes'), list = Array.isArray(data) ? data : (data && data.themes) || [];
      const themes = list.map(normalizeTheme).filter(Boolean);
      if (!themes.length) throw new Error('The backend returned an empty theme list.');
      state.themes = themes; state.themesOffline = false; renderThemes();
      if (opts.manual) toast(I18N ? I18N.format('Themes refreshed — {count} available.', { count: themes.length }) : 'Themes refreshed — ' + themes.length + ' available.', 'success');
      return true;
    } catch (error) {
      state.themes = FALLBACK_THEMES.map((theme) => Object.assign({}, theme, { tags: theme.tags.slice() }));
      state.themesOffline = true; renderThemes();
      if (opts.manual) toast(I18N ? I18N.format('Could not refresh themes: {message}', { message: error.message }) : 'Could not refresh themes: ' + error.message, 'error');
      return false; } }
  function updateDemoButton() {
    const button = $('preview-demo-btn'), hint = $('preview-demo-hint'), theme = currentTheme();
    if (!button) return;
    button.disabled = !(theme && theme.has_sample && !state.themesOffline && state.online);
    if (!hint) return;
    if (!theme) hint.textContent = I18N ? I18N.translate('Pick a theme in the Style step to preview a demo sample.') : 'Pick a theme in the Style step to preview a demo sample.';
    else if (!theme.has_sample) hint.textContent = I18N ? I18N.format('{theme} has no packaged sample — generate it to see a preview.', { theme: theme.name }) : theme.name + ' has no packaged sample — generate it to see a preview.';
    else if (state.themesOffline || !state.online) hint.textContent = I18N ? I18N.translate('Demo previews need the local backend. Start the server, then retry.') : 'Demo previews need the local backend. Start the server, then retry.';
    else hint.textContent = I18N ? I18N.format('Preview the {theme} sample site.', { theme: theme.name }) : 'Preview the ' + theme.name + ' sample site.'; }

  /* ---------- 10. Settings: presets, masks, save, test --------------------- */
  const PLACEHOLDERS = { api: 'sk-…', db: 'public anon key' };
  const dbMode = () => { const remote = $('db-remote'); return remote && remote.checked ? 'remote' : 'local'; };
  function paintRange() {
    const range = $('temperature'), output = $('temperature-value'); if (!range) return;
    const min = Number(range.min || 0), max = Number(range.max || 1.5);
    range.style.setProperty('--pct', (((Number(range.value || 0) - min) / (max - min)) * 100).toFixed(1) + '%');
    if (output) output.textContent = Number(range.value || 0).toFixed(1); }
  function syncKeyState(kind) {
    const isAI = kind === 'ai', input = isAI ? $('api-key') : $('db-key');
    const hint = isAI ? $('ai-key-state') : $('db-key-state'), label = isAI ? $('ai-key-label') : $('db-key-label-text');
    if (!input || !hint || !label) return;
    const settings = state.settings || {}, section = isAI ? settings.ai || {} : (settings.database || {}).remote || {};
    const saved = Boolean(section.has_key), typed = input.value.trim().length > 0;
    if (isAI && providerPreset((($('provider') || {}).value || 'pollinations')).requires_key === false) {
      input.disabled = true; input.placeholder = I18N ? I18N.translate('not required') : 'not required';
      hint.dataset.state = 'saved'; label.textContent = 'No API key needed for this provider';
      return; }
    input.disabled = false;
    if (typed) { hint.dataset.state = 'typing'; label.textContent = 'New key — will be saved'; }
    else if (saved) { hint.dataset.state = 'saved'; label.textContent = (isAI ? 'Key saved' : 'Database key saved') + (section.key_hint ? ' ' + section.key_hint : ''); }
    else { hint.dataset.state = 'empty'; label.textContent = isAI ? 'No key saved' : 'No database key saved'; }
    input.placeholder = saved ? 'saved' : (isAI ? PLACEHOLDERS.api : PLACEHOLDERS.db); }
  const syncKeyStates = () => { syncKeyState('ai'); syncKeyState('db'); };
  function syncProviderUI() {
    const select = $('provider'), preset = providerPreset((select && select.value) || 'pollinations');
    const note = $('ai-provider-note'), localButton = $('ai-local-btn');
    if (note) {
      clear(note); note.textContent = preset.note || '';
      if (preset.requires_key && preset.key_url) {
        note.append(' ');
        const link = el('a', null, 'Get a free key');
        link.href = preset.key_url; link.target = '_blank'; link.rel = 'noopener noreferrer';
        note.append(link); } }
    if (localButton) localButton.hidden = ((select && select.value) || '') !== 'ollama';
    syncKeyState('ai'); updateSummary(); }
  function applyStatus(data) {
    state.status = data || null;
    const version = $('version-pill');
    if (version && data && data.version) { const raw = String(data.version); version.textContent = /^v/i.test(raw) ? raw : 'v' + raw; }
    const pill = $('status-pill'); if (pill && data && data.config_path) pill.title = 'Backend online · ' + String(data.config_path); }
  function applySettings(data) {
    const config = (state.settings = data && typeof data === 'object' ? data : {});
    const ai = config.ai || {}, database = config.database || {}, remote = database.remote || {}, ui = config.ui || {};
    if ($('provider') && PRESETS[ai.provider]) $('provider').value = ai.provider;
    if ($('base-url') && ai.base_url != null) $('base-url').value = String(ai.base_url);
    if ($('model') && ai.model != null) $('model').value = String(ai.model);
    const temperature = $('temperature');
    if (temperature && Number.isFinite(Number(ai.temperature))) temperature.value = String(clamp(Number(ai.temperature), Number(temperature.min || 0), Number(temperature.max || 1.5)));
    paintRange();
    if ($('db-local')) $('db-local').checked = database.mode !== 'remote';
    if ($('db-remote')) $('db-remote').checked = database.mode === 'remote';
    if ($('db-url') && remote.url != null) $('db-url').value = String(remote.url);
    if ($('db-kind') && remote.kind) $('db-kind').value = remote.kind === 'rest' ? 'rest' : 'supabase';
    if ($('db-prefix') && remote.table_prefix != null) $('db-prefix').value = String(remote.table_prefix);
    const demo = $('demo-mode');
    if (demo) demo.checked = typeof ui.demo_mode === 'boolean' ? ui.demo_mode : typeof config.demo_mode === 'boolean' ? config.demo_mode : demo.checked;
    const browser = config.browser || {};
    if ($('browser-auto-check')) $('browser-auto-check').checked = browser.auto_check !== false;
    if (I18N && ui.language) I18N.setLanguage(ui.language);
    syncProviderUI(); syncDBMode(); updateSummary(); updateGenerateNote(); }
  function aiPayload() {
    const payload = {
      provider: ($('provider') || {}).value || 'openai', base_url: (($('base-url') || {}).value || '').trim(),
      model: (($('model') || {}).value || '').trim(), temperature: Number((($('temperature') || {}).value) || 0.7) };
    const key = (($('api-key') || {}).value || '').trim(); if (key) payload.api_key = key;
    return payload; }
  function databasePayload() {
    const remote = { kind: ($('db-kind') || {}).value || 'supabase', url: (($('db-url') || {}).value || '').trim(), table_prefix: (($('db-prefix') || {}).value || '').trim() || 'stitchcraft' };
    const key = (($('db-key') || {}).value || '').trim(); if (key) remote.anon_key = key;
    return { mode: dbMode(), remote: remote }; }
  function syncDBMode() { const panel = $('db-remote-panel'); if (panel) panel.hidden = dbMode() !== 'remote'; syncKeyState('db'); updateSummary(); }
  function rememberAISaved(payload) {
    const ai = (state.settings && state.settings.ai) || {}; state.settings = state.settings || {};
    state.settings.ai = Object.assign({}, ai, {
      provider: payload.provider, base_url: payload.base_url, model: payload.model, temperature: payload.temperature,
      has_key: Boolean(payload.api_key) || Boolean(ai.has_key), key_hint: payload.api_key ? '' : String(ai.key_hint || '') }); }
  function rememberDBSaved(payload) {
    const current = (state.settings && state.settings.database) || {}, previous = current.remote || {};
    state.settings = state.settings || {};
    state.settings.database = { mode: payload.mode, remote: {
      kind: payload.remote.kind, url: payload.remote.url, table_prefix: payload.remote.table_prefix,
      has_key: Boolean(payload.remote.anon_key) || Boolean(previous.has_key), key_hint: payload.remote.anon_key ? '' : String(previous.key_hint || '')
    } }; }
  async function saveSettings(kind) {
    const isAI = kind === 'ai';
    const button = $(isAI ? 'ai-save-btn' : 'db-save-btn'), result = $(isAI ? 'ai-save-result' : 'db-save-result');
    const payload = isAI ? { ai: aiPayload() } : { database: databasePayload() };
    if (isAI && !payload.ai.base_url) { toast('Base URL is required for the AI provider.', 'error'); return false; }
    if (isAI && !isHttpUrl(payload.ai.base_url)) { toast('Base URL must start with http:// or https://.', 'error'); return false; }
    if (!isAI && payload.database.mode === 'remote' && !payload.database.remote.url) { toast('Add the database URL before saving remote mode.', 'error'); return false; }
    if (!isAI && payload.database.mode === 'remote' && !isHttpUrl(payload.database.remote.url)) { toast('Database URL must start with http:// or https://.', 'error'); return false; }
    setBusy(button, true); if (result) result.hidden = true;
    try {
      const response = await api('/api/settings', { method: 'POST', body: payload });
      if (isAI) { rememberAISaved(payload.ai); if ($('api-key')) $('api-key').value = ''; }
      else { rememberDBSaved(payload.database); if ($('db-key')) $('db-key').value = ''; }
      syncKeyStates(); updateSummary();
      const path = response && response.config_path ? ' · ' + shortPath(response.config_path) : '';
      showResult(result, 'ok', (isAI ? 'AI' : 'Data') + ' settings saved' + path + '.');
      toast((isAI ? 'AI' : 'Data') + ' settings saved.', 'success'); return true;
    } catch (error) {
      showResult(result, 'error', 'Could not save ' + (isAI ? 'AI' : 'data') + ' settings: ' + error.message);
      toast('Could not save settings: ' + error.message, 'error'); return false;
    } finally { setBusy(button, false); } }
  async function runConnectionTest(kind) {
    const isAI = kind === 'ai';
    const button = $(isAI ? 'ai-test-btn' : 'db-test-btn'), result = $(isAI ? 'ai-test-result' : 'db-test-result');
    let body;
    if (isAI) { const payload = aiPayload(); body = Object.assign({ ai: payload }, payload); }
    else {
      if (dbMode() !== 'remote') { toast('Switch the database to Remote to test a connection.', 'info'); return; }
      const database = databasePayload();
      body = { database: database, remote: database.remote, kind: database.remote.kind, url: database.remote.url, table_prefix: database.remote.table_prefix };
      if (database.remote.anon_key) body.anon_key = database.remote.anon_key; }
    setBusy(button, true); if (result) result.hidden = true;
    try {
      const response = await api(isAI ? '/api/ai/test' : '/api/db/test', { method: 'POST', body: body });
      if (response && response.ok === false) {
        const message = response.message || (isAI ? 'The provider rejected the connection test.' : 'The database endpoint could not be reached.');
        showResult(result, 'error', message); toast(message, 'error'); return; }
      const latency = isAI && response && Number.isFinite(Number(response.latency_ms)) ? ' · ' + Math.round(Number(response.latency_ms)) + ' ms' : '';
      const message = String((response && response.message) || (isAI ? 'Connected to the model endpoint.' : 'Database endpoint reachable.')).replace(/\.$/, '');
      showResult(result, 'ok', message + latency + '.');
      toast(isAI ? 'AI connection OK.' : 'Database connection OK.', 'success');
    } catch (error) {
      showResult(result, 'error', error.message);
      toast((isAI ? 'AI connection failed: ' : 'Database test failed: ') + error.message, 'error');
    } finally { setBusy(button, false); } }
  function toggleSecret(inputId, buttonId, label) {
    const input = $(inputId), button = $(buttonId); if (!input || !button) return;
    const reveal = input.type === 'password';
    input.type = reveal ? 'text' : 'password';
    button.setAttribute('aria-pressed', String(reveal)); button.textContent = reveal ? 'Hide' : 'Show';
    button.setAttribute('aria-label', (reveal ? 'Hide ' : 'Show ') + label); }
  function bindSettings() {
    on($('provider'), 'change', () => {
      const preset = PRESETS[($('provider') || {}).value] || PRESETS.custom;
      if ($('base-url')) $('base-url').value = preset.base_url;
      if ($('model')) $('model').value = preset.model;
      syncProviderUI(); announce('Provider set to ' + preset.label);
      if ((($('provider') || {}).value || '') === 'ollama') detectLocalOllama(true); });
    on($('temperature'), 'input', paintRange);
    on($('toggle-key-vis'), 'click', () => toggleSecret('api-key', 'toggle-key-vis', 'API key'));
    on($('toggle-db-key-vis'), 'click', () => toggleSecret('db-key', 'toggle-db-key-vis', 'database key'));
    on($('api-key'), 'input', () => syncKeyState('ai')); on($('db-key'), 'input', () => syncKeyState('db'));
    [['ai-save-btn', 'ai'], ['db-save-btn', 'db']].forEach(([id, kind]) => on($(id), 'click', () => saveSettings(kind)));
    [['ai-test-btn', 'ai'], ['db-test-btn', 'db']].forEach(([id, kind]) => on($(id), 'click', () => runConnectionTest(kind)));
    on($('ai-local-btn'), 'click', () => detectLocalOllama(false));
    on($('demo-mode'), 'change', () => { updateSummary(); updateGenerateNote(); announce(($('demo-mode') || {}).checked ? 'Demo mode on.' : 'AI generation mode.'); });
    on($('db-local'), 'change', syncDBMode); on($('db-remote'), 'change', syncDBMode); syncDBMode(); }

  /* ---------- 11. Brief, summary, localStorage ----------------------------- */
  function updateSummary() {
    const theme = currentTheme(), demo = Boolean(($('demo-mode') || {}).checked);
    const provider = ($('provider') || {}).value || 'pollinations', preset = PRESETS[provider] || PRESETS.custom;
    const model = (($('model') || {}).value || '').trim(), title = (($('site-title') || {}).value || '').trim();
    setText('summary-theme', theme ? theme.name : 'Not selected');
    setText('summary-engine', demo ? 'Demo mode' : 'AI · ' + preset.label + ' / ' + (model || 'default model'));
    setText('summary-db', dbMode() === 'remote' ? 'Remote · ' + ((($('db-kind') || {}).value) === 'rest' ? 'Generic REST' : 'Supabase') : 'Local storage');
    setText('summary-mode', state.importFiles.length ? 'Continue · ' + state.importFiles.length + ' files' : 'New site');
    setText('summary-title', title || 'Auto-generated'); }
  function updateGenerateNote() {
    if (state.generating) return;
    const note = $('generate-note'); if (!note) return;
    if (state.importFiles.length) {
      note.textContent = ($('demo-mode') || {}).checked
        ? 'Continue mode needs the AI engine. Turn off demo mode and configure a provider.'
        : 'Continuing from ' + state.importFiles.length + ' imported file(s). Existing copy and layout are kept unless the brief says otherwise.';
      return;
    }
    note.textContent = ($('demo-mode') || {}).checked
      ? (I18N ? I18N.translate('Demo mode copies a packaged sample and makes no model calls — usually a few seconds.') : 'Demo mode copies a packaged sample and makes no model calls — usually a few seconds.')
      : (I18N ? I18N.translate('Usually 20–60 seconds in AI mode. Every stage reports into the Pipeline tab.') : 'Usually 20–60 seconds in AI mode. Every stage reports into the Pipeline tab.'); }
  function updateCharCount() {
    const prompt = $('prompt'), count = $('prompt-count'); if (!prompt || !count) return;
    count.textContent = String(prompt.value.length);
    if (prompt.value.trim()) setHidden('prompt-error', true); }
  function updateImportUI() {
    const card = $('import-card'), label = $('import-label'), status = $('import-status'), clearButton = $('import-clear');
    const count = state.importFiles.length;
    if (card) card.classList.toggle('is-loaded', count > 0);
    if (label) label.textContent = count ? (state.importRoot || 'Site folder') : 'Select a site folder';
    if (status) {
      status.textContent = count
        ? count + ' file(s) · ' + Math.max(1, Math.round(state.importBytes / 1024)) + ' KB' + (state.importSkipped.length ? ' · ' + state.importSkipped.length + ' skipped' : '')
        : 'No folder selected.';
    }
    if (clearButton) clearButton.hidden = count === 0;
    const button = $('generate-btn'), buttonLabel = button && button.querySelector('.btn__label');
    if (buttonLabel && !state.generating) buttonLabel.textContent = count ? 'Finish this site' : 'Generate website';
    updateSummary(); updateGenerateNote();
  }
  function clearImport() {
    state.importFiles = []; state.importSkipped = []; state.importRoot = ''; state.importBytes = 0;
    const input = $('import-input'); if (input) input.value = '';
    setHidden('import-error', true); updateImportUI();
  }
  async function importFolder(event) {
    const input = event.target, files = input && input.files ? input.files : null;
    if (!files || !files.length) return;
    setHidden('import-error', true);
    const label = $('import-label'); if (label) label.textContent = 'Reading folder…';
    if (!SITE_IMPORT) { setHidden('import-error', false); setText('import-error', 'The import module did not load. Reload the studio and retry.'); return; }
    try {
      const result = await SITE_IMPORT.readFolder(input);
      state.importFiles = result.files; state.importSkipped = result.skipped || [];
      state.importRoot = result.root || ''; state.importBytes = result.bytes || 0;
      updateImportUI();
      if (($('demo-mode') || {}).checked) toast('Continue mode needs the AI engine — turn off demo mode.', 'info', 5000);
    } catch (error) {
      clearImport();
      setHidden('import-error', false); setText('import-error', error.message || 'Could not read that folder.');
    }
  }
  function bindImport() {
    on($('import-input'), 'change', importFolder);
    on($('import-clear'), 'click', clearImport);
  }

  function bindBrief() {
    const prompt = $('prompt'), title = $('site-title'), savedTitle = readStorage(STORAGE.title);
    if (title && savedTitle) title.value = savedTitle;
    on(prompt, 'input', updateCharCount);
    on(title, 'input', () => { writeStorage(STORAGE.title, title.value.trim()); updateSummary(); });
    on($('step-4'), 'click', (event) => {
      const chip = event.target && event.target.closest ? event.target.closest('[data-example]') : null;
      if (!chip || !prompt) return;
      prompt.value = chip.getAttribute('data-example') || ''; updateCharCount(); prompt.focus(); announce('Example brief inserted.'); });
    updateCharCount(); }

  /* ---------- 12. Skills note (appended at runtime) ------------------------ */
  function ensureSkillsNote() {
    let note = $('skills-note'); if (note) return note;
    note = el('p', 'step__note step__note--skills'); note.id = 'skills-note'; note.hidden = true;
    const anchor = $('generate-note');
    if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(note, anchor.nextSibling);
    else if ($('step-5')) $('step-5').appendChild(note); else document.body.appendChild(note);
    return note; }
  function normalizeSkill(raw) {
    if (!raw || typeof raw !== 'object') return null;
    return { id: String(raw.id || ''), name: String(raw.name || raw.id || ''), category: String(raw.category || ''), enabled: raw.enabled !== false }; }
  function renderSkillsNote() {
    const note = ensureSkillsNote(); if (!note) return;
    if (!state.skills.length) { note.hidden = true; return; }
    const names = state.skills.slice(0, 3).map((skill) => skill.name).filter(Boolean).join(', ');
    note.textContent = state.skills.length + ' skills loaded · ' + (names || 'registry ready') + (state.skills.length > 3 ? '…' : '');
    note.hidden = false; }

  /* ---------- 13. Preview -------------------------------------------------- */
  const setPreviewLoading = (loading) => {
    setHidden('preview-loading', !loading);
    const wrap = $('preview-frame-wrap'); if (wrap) wrap.setAttribute('aria-busy', String(Boolean(loading))); };
  function previewBase() {
    const configured = state.status && state.status.preview_base;
    if (configured) return String(configured).replace(/\/$/, '');
    return 'http://localhost:' + (window.location.port || '8765');
  }
  function openPreview(options) {
    const opts = options || {}, preview = $('preview-wrap'), empty = $('preview-empty'), frame = $('preview-frame');
    const id = opts.id ? String(opts.id) : '', demoId = opts.demoTheme ? String(opts.demoTheme) : '';
    const url = id ? previewBase() + '/api/preview/' + encodeURIComponent(id) + '/' : demoId ? previewBase() + '/api/demo/' + encodeURIComponent(demoId) + '/' : '';
    if (!url) return;
    state.preview = { url: url, projectId: id || null, demo: !id, title: opts.title || 'Untitled site' };
    setPreviewLoading(true); if (empty) empty.hidden = true; if (preview) preview.hidden = false;
    setText('preview-title', opts.title || 'Untitled site');
    setText('preview-kind', id ? (opts.engine === 'mock' ? 'Demo output' : 'Generated site') : 'Demo sample');
    if (frame) frame.src = url;
    const openLink = $('preview-open'); if (openLink) openLink.href = url;
    const exportLink = $('preview-export');
    if (exportLink) {
      if (id) { exportLink.hidden = false; exportLink.href = '/api/export/' + encodeURIComponent(id); }
      else { exportLink.hidden = true; exportLink.removeAttribute('href'); } }
    setStageBadge('done', id ? 'Ready' : 'Demo');
    if (id) { api('/api/browser/check/' + encodeURIComponent(id)).then((report) => renderBrowserReport(report)).catch(() => renderBrowserReport(null)); }
    else renderBrowserReport(null);
    if (canAnimate() && preview) window.gsap.fromTo(preview, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.32, ease: 'power2.out', clearProps: 'opacity,transform' }); }
  function resetPreview() {
    state.preview = null;
    setHidden('preview-empty', false); setHidden('preview-wrap', true); setPreviewLoading(false);
    const frame = $('preview-frame'); if (frame) frame.src = 'about:blank';
    setStageBadge('idle', 'Idle'); }
  function bindPreview() {
    on($('preview-frame'), 'load', () => setPreviewLoading(false));
    on($('preview-reload'), 'click', () => {
      const frame = $('preview-frame'); if (!frame || !state.preview) return;
      setPreviewLoading(true);
      try { frame.contentWindow.location.reload(); } catch (_) { frame.src = state.preview.url; } });
    on($('preview-demo-btn'), 'click', () => {
      const theme = currentTheme(); if (!theme || !theme.has_sample) return;
      if (!state.online) { toast('Start the Stitchcraft backend to preview demo samples.', 'error'); return; }
      openPreview({ demoTheme: theme.id, title: theme.name + ' · sample' }); switchTab('preview'); announce('Loading the ' + theme.name + ' demo sample.'); });
    setPreviewLoading(false); }

  /* ---------- 13b. AI browser (optional Obscura runtime) ------------------- */
  function browserBadge(stateName, text) {
    const badge = $('browser-state');
    if (badge) { badge.dataset.state = stateName; badge.textContent = text; } }
  function browserPanelBadge(stateName, text) {
    const badge = $('browser-panel-badge');
    if (badge) { badge.dataset.state = stateName; badge.textContent = text; } }
  function applyBrowser(data) {
    const b = data && typeof data === 'object' ? data : {};
    state.browser = b;
    const installed = Boolean(b.installed), install = b.install || {};
    const busy = ['starting', 'downloading', 'extracting'].indexOf(String(install.state || '')) >= 0;
    const failed = install.state === 'error';
    browserBadge(installed ? 'done' : failed ? 'error' : busy ? 'running' : 'idle',
      installed ? 'Installed' : failed ? 'Install failed' : busy ? (install.percent || 0) + '%' : 'Not installed');
    const desc = $('browser-desc');
    if (desc) desc.textContent = installed
      ? 'Obscura ' + String(b.version || '') + ' is installed locally (' + String(b.license || 'Apache-2.0') + '). Site checks run without Chrome or Edge.'
      : 'Obscura ' + String(b.version || '') + ' (' + String(b.license || 'Apache-2.0') + ', about ' +
        Math.round((Number(b.download_bytes) || 0) / 1024 / 1024) + ' MB) is downloaded on demand and verified with SHA-256.';
    const installBtn = $('browser-install');
    if (installBtn) { installBtn.hidden = installed; installBtn.disabled = busy || b.supported === false; installBtn.textContent = busy ? 'Downloading…' : 'Install AI browser'; }
    const removeBtn = $('browser-remove');
    if (removeBtn) removeBtn.hidden = !installed;
    const panelInstall = $('browser-panel-install');
    if (panelInstall) { panelInstall.hidden = installed; panelInstall.disabled = b.supported === false; }
    const panelCheck = $('browser-panel-check');
    if (panelCheck) panelCheck.hidden = !installed;
    const panelCopy = $('browser-panel-copy');
    if (panelCopy) panelCopy.textContent = installed
      ? 'No browser check yet. Generate a site (or open a project) and the AI browser will capture its screenshot and DOM audit here.'
      : 'Obscura renders the generated page locally and records a screenshot plus a small DOM audit (title, headings, links, images, lang). It is optional, Apache-2.0 and works without Chrome or Edge installed.';
    const progress = $('browser-progress');
    if (progress) {
      progress.hidden = !busy;
      const percent = clamp(install.percent || 0, 0, 100);
      const fill = $('browser-progress-fill'); if (fill) fill.style.width = percent + '%';
      setText('browser-progress-text', failed ? 'Install failed' : busy ? 'Downloading… ' + Math.round(percent) + '%' : '');
    }
    const auto = $('browser-auto-check');
    if (auto && b.settings && typeof b.settings.auto_check === 'boolean') auto.checked = b.settings.auto_check;
    const hint = $('browser-hint');
    if (hint) hint.textContent = installed
      ? 'Local runtime: ' + shortPath(b.binary || '') + ' · checks stay on this machine.'
      : failed ? String(install.error || 'Could not install the AI browser.')
      : b.supported === false ? String(b.missing_reason || 'This platform has no Obscura build.')
      : 'Fetched from the pinned GitHub release; never bundled with the app.';
    const panelStatus = $('browser-panel-status');
    const resultNode = $('browser-panel-result');
    if (panelStatus && (!resultNode || resultNode.hidden)) {
      panelStatus.textContent = installed
        ? 'Generate a site (or open a project) to see its screenshot and DOM audit.'
        : busy ? 'Installing the AI browser…'
        : b.supported === false ? 'The AI browser is not available for this platform.'
        : 'Install the AI browser, then generate a site to see its screenshot and DOM audit.';
    }
  }
  async function loadBrowser() {
    try { applyBrowser(await api('/api/browser')); }
    catch (error) { browserBadge('error', 'Offline'); const hint = $('browser-hint'); if (hint) hint.textContent = 'Could not read the AI browser status: ' + error.message; }
  }
  function scheduleBrowserPoll() {
    window.clearTimeout(state.browserTimer);
    state.browserTimer = window.setTimeout(async () => {
      try {
        const data = await api('/api/browser');
        applyBrowser(data);
        const install = data && data.install ? data.install : {};
        if (install.state === 'installed') { toast('AI browser installed — Obscura is ready.', 'success'); await loadBrowser(); return; }
        if (install.state === 'error') { toast('AI browser install failed: ' + (install.error || 'unknown error'), 'error', 6000); await loadBrowser(); return; }
        scheduleBrowserPoll();
      } catch (error) {
        toast('Could not poll the AI browser install: ' + error.message, 'error');
        const button = $('browser-install'); setBusy(button, false);
      }
    }, BROWSER_POLL_MS);
  }
  async function installBrowser() {
    const button = $('browser-install') || $('browser-panel-install');
    setBusy(button, true);
    try {
      await api('/api/browser/install', { method: 'POST', body: {} });
      toast('Downloading the AI browser (Obscura). This takes a moment…', 'info', 5000);
      scheduleBrowserPoll();
    } catch (error) {
      toast('Could not start the AI browser install: ' + error.message, 'error', 6000);
      setBusy(button, false);
      await loadBrowser();
    }
  }
  async function removeBrowser() {
    const confirmed = await confirmAction({
      title: 'Remove the AI browser?',
      message: 'The downloaded Obscura runtime and its saved screenshots will be removed from this machine. You can install it again later.',
      confirmLabel: 'Remove browser', danger: true });
    if (!confirmed) return;
    try {
      await api('/api/browser', { method: 'DELETE' });
      renderBrowserReport(null);
      await loadBrowser();
      toast('AI browser removed.', 'success');
    } catch (error) { toast('Could not remove the AI browser: ' + error.message, 'error'); } }
  async function toggleBrowserAuto(checked) {
    try {
      await api('/api/settings', { method: 'POST', body: { browser: { auto_check: Boolean(checked) } } });
      if (state.settings) { state.settings.browser = Object.assign({}, state.settings.browser || {}, { auto_check: Boolean(checked) }); }
      toast(checked ? 'AI browser checks will run after each build.' : 'Automatic AI browser checks are off.', 'info');
    } catch (error) {
      const input = $('browser-auto-check'); if (input) input.checked = !checked;
      toast('Could not save the browser setting: ' + error.message, 'error'); } }
  function addBrowserMetric(host, label, value) {
    if (!host) return;
    const row = el('div'); row.appendChild(el('dt', '', label)); row.appendChild(el('dd', '', value)); host.appendChild(row); }
  function renderBrowserReport(report) {
    const empty = $('browser-panel-empty'), result = $('browser-panel-result'), status = $('browser-panel-status');
    if (!report || typeof report !== 'object') {
      if (empty) empty.hidden = false;
      if (result) result.hidden = true;
      browserPanelBadge('idle', 'Idle');
      if (status) status.textContent = 'Generate a site (or open a project) to see the AI browser screenshot and audit.';
      return; }
    if (empty) empty.hidden = true;
    if (result) result.hidden = false;
    const ok = Boolean(report.ok);
    browserPanelBadge(ok ? 'done' : 'warn', ok ? 'Checked' : 'Needs attention');
    if (status) status.textContent = ok
      ? 'Obscura rendered the site and the DOM audit looks clean.'
      : 'Obscura rendered the site; review the notes below.';
    const projectId = String(report.project_id || (state.preview && state.preview.projectId) || '');
    const shot = $('browser-screenshot');
    if (shot) {
      if (projectId) { shot.src = '/api/browser/screenshot/' + encodeURIComponent(projectId) + '?v=' + Date.now(); shot.hidden = false; }
      else { shot.removeAttribute('src'); shot.hidden = true; } }
    const metrics = $('browser-metrics'); clear(metrics);
    const links = report.links || {}, images = report.images || {};
    addBrowserMetric(metrics, 'Title', report.title || '—');
    addBrowserMetric(metrics, 'Language', report.lang || 'missing');
    addBrowserMetric(metrics, 'H1 headings', String(report.h1 != null ? report.h1 : '—'));
    addBrowserMetric(metrics, 'Rendered text', (Number(report.text_chars) || 0) + ' chars');
    addBrowserMetric(metrics, 'Links', String(links.total != null ? links.total : '—') + (Number(links.empty) ? ' · ' + links.empty + ' empty' : ''));
    addBrowserMetric(metrics, 'Images', String(images.total != null ? images.total : '—') + (Number(images.missingAlt) ? ' · ' + images.missingAlt + ' missing alt' : ''));
    const list = $('browser-warnings'); clear(list);
    const issues = (Array.isArray(report.critical) ? report.critical : []).concat(Array.isArray(report.warnings) ? report.warnings : []);
    if (list) {
      if (!issues.length) { const item = el('li', '', 'No accessibility or structure notes from this check.'); item.dataset.kind = 'ok'; list.appendChild(item); }
      else issues.forEach((issue) => list.appendChild(el('li', '', String(issue)))); }
    const open = $('browser-open-shot');
    if (open) {
      if (projectId) { open.href = '/api/browser/screenshot/' + encodeURIComponent(projectId); open.hidden = false; }
      else open.hidden = true; }
  }
  async function runBrowserCheck() {
    const projectId = state.preview && state.preview.projectId;
    if (!projectId) { toast('Open a generated project first, then run the AI browser check.', 'info'); switchTab('preview'); return; }
    const button = $('browser-check-again');
    if (button) setBusy(button, true);
    switchTab('browser');
    browserPanelBadge('running', 'Checking…');
    try {
      const report = await api('/api/browser/check', { method: 'POST', body: { project_id: projectId } });
      renderBrowserReport(report);
      toast(report.ok ? 'AI browser check passed.' : 'AI browser check finished with notes.', report.ok ? 'success' : 'info');
    } catch (error) {
      browserPanelBadge('error', 'Failed');
      toast('AI browser check failed: ' + error.message, 'error', 6000);
    } finally { if (button) setBusy(button, false); } }
  function bindBrowser() {
    on($('browser-install'), 'click', installBrowser);
    on($('browser-panel-install'), 'click', installBrowser);
    on($('browser-panel-check'), 'click', runBrowserCheck);
    on($('browser-remove'), 'click', removeBrowser);
    on($('browser-refresh'), 'click', async () => { await loadBrowser(); toast('AI browser status refreshed.', 'success'); });
    on($('browser-auto-check'), 'change', () => toggleBrowserAuto((($('browser-auto-check') || {}).checked)));
    on($('browser-check-again'), 'click', runBrowserCheck);
  }

  /* ---------- 14. Pipeline: stages, progress, logs ------------------------- */
  const blankStages = () => STAGES.map((stage) => ({ key: stage.key, label: stage.label, status: 'pending', message: '' }));
  const normalizeStageStatus = (value) => STAGE_STATUS[String(value || 'pending').toLowerCase()] || 'pending';
  function normalizeStages(job) {
    const base = blankStages(), raw = job.stages || job.stage_states || null;
    let list = null;
    if (Array.isArray(raw)) list = raw;
    else if (raw && typeof raw === 'object') list = Object.keys(raw).map((key) => (raw[key] && typeof raw[key] === 'object' ? Object.assign({ key: key }, raw[key]) : { key: key, status: raw[key] }));
    if (list && list.length) {
      return base.map((stage, index) => {
        let item = list[index];
        if (!item || (typeof item === 'object' && String(item.key || item.id || item.name || '').toLowerCase() !== stage.key)) {
          const match = list.find((candidate) => candidate && typeof candidate === 'object' && String(candidate.key || candidate.id || candidate.name || '').toLowerCase() === stage.key);
          if (match) item = match; }
        if (!item) return stage;
        if (typeof item === 'string') return { key: stage.key, label: stage.label, status: normalizeStageStatus(item), message: '' };
        return {
          key: String(item.key || item.id || stage.key), label: String(item.label || item.name || item.stage_name || stage.label),
          status: normalizeStageStatus(item.status || item.state), message: String(item.message || item.detail || item.msg || '') }; }); }
    const status = String(job.status || job.state || '').toLowerCase();
    if (DONE.indexOf(status) >= 0) return base.map((stage) => Object.assign({}, stage, { status: 'done' }));
    const numeric = Number(job.stage_index != null ? job.stage_index : typeof job.stage === 'number' ? job.stage : NaN);
    const named = typeof job.stage === 'string' ? job.stage.toLowerCase() : '';
    const current = !Number.isNaN(numeric) ? numeric : base.findIndex((stage) => stage.key === named);
    const percent = clamp(Number(job.progress) || 0, 0, 100);
    base.forEach((stage, index) => { stage.status = current >= 0 ? (index < current ? 'done' : index === current ? 'active' : 'pending') : percent >= Math.round(((index + 1) / base.length) * 100) ? 'done' : 'pending'; });
    return base; }
  function deriveProgress(job, stages, done) {
    if (done) return 100;
    let value = Number(job.progress);
    if (!Number.isFinite(value)) value = Number(job.percent);
    if (!Number.isFinite(value)) value = (stages.filter((stage) => stage.status === 'done').length / stages.length) * 100;
    if (value > 0 && value < 1) value *= 100;
    return clamp(value, 0, 100); }
  function renderStages(stages) {
    const host = $('pipeline-stages'); if (!host) return;
    state.stages = stages;
    if (host.childElementCount !== stages.length) {
      clear(host); state.stageEls = [];
      stages.forEach((stage, index) => {
        const item = el('li', 'pipe-stage'); item.dataset.status = 'pending'; item.dataset.key = stage.key;
        const body = el('div', 'pipe-stage__body'), name = el('span', 'pipe-stage__name', stage.label), message = el('span', 'pipe-stage__msg', 'Waiting');
        message.title = 'Waiting'; body.append(name, message);
        const status = el('span', 'pipe-stage__state', 'Pending');
        item.append(el('span', 'pipe-stage__num', String(index + 1)), body, status); host.appendChild(item);
        state.stageEls.push({ item: item, name: name, message: message, status: status, current: 'pending' }); }); }
    stages.forEach((stage, index) => {
      const ref = state.stageEls[index]; if (!ref) return;
      if (ref.current !== stage.status) {
        ref.item.dataset.status = stage.status;
        if (canAnimate() && (stage.status === 'active' || stage.status === 'done')) window.gsap.from(ref.item, { opacity: 0.55, x: -4, duration: 0.3, ease: 'power2.out', clearProps: 'opacity,transform' });
        ref.current = stage.status; }
      if (ref.name.textContent !== stage.label) ref.name.textContent = stage.label;
      const message = stage.message || ({ pending: 'Waiting', active: 'Working…', done: 'Done', error: 'Failed' }[stage.status] || 'Waiting');
      if (ref.message.textContent !== message) { ref.message.textContent = message; ref.message.title = message; }
      const label = { pending: 'Pending', active: 'Active', done: 'Done', error: 'Failed' }[stage.status] || 'Pending';
      if (ref.status.textContent !== label) ref.status.textContent = label; }); }
  function setProgress(value, instant) {
    const percent = clamp(value, 0, 100); state.progress = percent;
    const fill = $('pipeline-fill'); if (fill) fill.style.width = percent + '%';
    const bar = $('pipeline-progress'); if (bar) bar.setAttribute('aria-valuenow', String(Math.round(percent)));
    const ring = $('pipeline-percent'); if (!ring) return;
    const paint = (next) => { const safe = clamp(next, 0, 100); ring.style.setProperty('--progress', String(safe.toFixed(1))); ring.textContent = Math.round(safe) + '%'; state.paintedProgress = safe; };
    if (instant || !canAnimate() || Math.abs(state.paintedProgress - percent) < 0.5) { paint(percent); return; }
    const proxy = { value: state.paintedProgress };
    window.gsap.to(proxy, { value: percent, duration: 0.6, ease: 'power2.out', overwrite: true, onUpdate: () => paint(proxy.value) }); }
  function setPipelineStatus(kind, message) {
    const badge = $('pipeline-state');
    if (badge) { badge.dataset.state = kind; badge.textContent = { idle: 'Idle', running: 'Running', done: 'Done', error: 'Failed' }[kind] || 'Idle'; }
    if (message != null) setText('pipeline-status-text', message); }
  const setStageBadge = (kind, text) => { const badge = $('stage-badge'); if (badge) { badge.dataset.state = kind; badge.textContent = text; } };
  function showPipelineError(message) {
    setHidden('pipeline-success', true);
    const box = $('pipeline-error'); if (box) box.hidden = false;
    setText('pipeline-error-text', message || 'Something went wrong while generating. Check the logs for the failing stage.'); }
  function scrollLogsToEnd(force) {
    const list = $('log-list'); if (!list) return;
    if (force || list.scrollHeight - list.scrollTop - list.clientHeight < 90) list.scrollTop = list.scrollHeight; }
  const normalizeLogLevel = (value) => LOG_LEVEL[String(value || 'info').toLowerCase()] || 'info';
  function formatLogTime(value) {
    if (!value) return '';
    const text = String(value), date = new Date(text);
    if (!Number.isNaN(date.getTime())) { try { return new Intl.DateTimeFormat(undefined, { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(date); } catch (_) { /* fall through */ } }
    return text.length > 12 ? text.slice(0, 12) : text; }
  function normalizeLogs(raw) {
    let list = raw; if (typeof list === 'string') list = list.split(/\r?\n/);
    if (!Array.isArray(list)) return [];
    const logs = [];
    list.forEach((item) => {
      if (typeof item === 'string') {
        if (!item.trim()) return;
        const match = item.match(/^\[(info|warn|warning|error|debug|success|done|active)\]\s*(.*)$/i);
        logs.push({ level: match ? normalizeLogLevel(match[1]) : 'info', text: match ? match[2] : item, time: '' }); return; }
      if (!item || typeof item !== 'object') return;
      const text = item.message != null ? item.message : item.text != null ? item.text : item.line != null ? item.line : item.msg;
      if (text == null || !String(text).trim()) return;
      logs.push({ level: normalizeLogLevel(item.level != null ? item.level : item.kind != null ? item.kind : item.severity), text: String(text), time: formatLogTime(item.time != null ? item.time : item.ts != null ? item.ts : item.timestamp) }); });
    return logs; }
  function appendLogLine(line) {
    const list = $('log-list'); if (!list) return;
    const item = el('li', 'log-line'); item.dataset.level = line.level || 'info';
    if (line.time) item.appendChild(el('span', 'log-line__time', line.time));
    item.appendChild(el('span', 'log-line__level', line.level || 'info'));
    item.appendChild(el('span', 'log-line__text', line.text || ''));
    list.appendChild(item); }
  function renderLogs(logs) {
    const list = $('log-list'); if (!list || !logs.length) return;
    if (logs.length < state.logCursor) { clear(list); state.logCursor = 0; }
    for (let index = state.logCursor; index < logs.length; index += 1) appendLogLine(logs[index]);
    state.logCursor = logs.length; state.latestLogs = logs;
    setHidden('logs-empty', state.logCursor > 0);
    setText('logs-count', state.logCursor + ' line' + (state.logCursor === 1 ? '' : 's'));
    scrollLogsToEnd(false); }
  function clearLogsPanel() {
    const list = $('log-list'); if (list) clear(list);
    state.logCursor = state.latestLogs.length;
    setHidden('logs-empty', state.logCursor > 0); setText('logs-count', '0 lines'); announce('Logs cleared.'); }
  function resetPipelineUI(theme) {
    state.latestLogs = []; state.logCursor = 0; state.pollFails = 0;
    state.runningTitle = (($('site-title') || {}).value || '').trim() || (theme ? theme.name + ' site' : 'Untitled site');
    const list = $('log-list'); if (list) clear(list);
    setHidden('logs-empty', false); setText('logs-count', '0 lines');
    renderStages(blankStages()); setProgress(0, true);
    setPipelineStatus('running', 'Queued — warming up the stitch.');
    setText('pipeline-stage-name', 'Waiting for the first stage');
    setHidden('pipeline-success', true); setHidden('pipeline-error', true);
    setStageBadge('running', 'Running');
    setText('pipeline-foot', 'Running the nine-stage stitch — every stage reports here.'); }
  function setGenerateBusy(busy) {
    const button = $('generate-btn'); if (!button) return;
    button.disabled = Boolean(busy); button.setAttribute('aria-busy', String(Boolean(busy))); button.classList.toggle('is-busy', Boolean(busy));
    const label = button.querySelector('.btn__label');
    if (label) label.textContent = busy ? 'Stitching…' : (state.importFiles.length ? 'Finish this site' : 'Generate website');
    setHidden('pipeline-cancel', !busy);
    const cancelButton = $('pipeline-cancel');
    if (cancelButton && busy && !state.jobId) cancelButton.disabled = true;
    if (!busy) cancelButton && (cancelButton.disabled = false); }
  function canUseAI() {
    const provider = ($('provider') || {}).value || 'pollinations';
    if (providerPreset(provider).requires_key === false) return true;
    return Boolean((($('api-key') || {}).value || '').trim() || (state.settings && state.settings.ai && state.settings.ai.has_key)); }
  async function detectLocalOllama(silent) {
    const button = $('ai-local-btn'); if (button) setBusy(button, true);
    try {
      const response = await api('/api/ai/local');
      const models = Array.isArray(response && response.models) ? response.models : [];
      if (response && response.ok && models.length) {
        if ($('model')) $('model').value = models[0];
        updateSummary(); syncKeyState('ai');
        const message = 'Ollama detected: ' + models.slice(0, 3).join(', ');
        if (silent) toast(message, 'success'); else showResult($('ai-test-result'), 'ok', message + '.');
      } else if (!silent) {
        const message = String((response && response.message) || 'Ollama was not detected.');
        showResult($('ai-test-result'), 'error', message); toast(message, 'info');
      } } catch (error) { if (!silent) toast('Could not probe Ollama: ' + error.message, 'error'); }
    finally { if (button) setBusy(button, false); } }

  /* ---------- 15. Generation + polling ------------------------------------- */
  function normalizeJob(raw) {
    const job = raw && typeof raw === 'object' ? (raw.job && typeof raw.job === 'object' ? raw.job : raw) : {};
    const status = String(job.status || job.state || 'running').toLowerCase();
    const cancelled = CANCELLED.indexOf(status) >= 0;
    const failed = FAIL.indexOf(status) >= 0, done = DONE.indexOf(status) >= 0 && !failed && !cancelled;
    const stages = normalizeStages(job);
    if (done) stages.forEach((stage) => { stage.status = 'done'; });
    let error = '';
    if (failed) {
      if (typeof job.error === 'string') error = job.error;
      else if (job.error && typeof job.error === 'object') error = job.error.message || job.error.code || '';
      else if (typeof job.message === 'string') error = job.message;
      else if (typeof job.detail === 'string') error = job.detail; }
    const projectId = job.project_id || (job.project && job.project.id) || (job.result && job.result.project_id) || (job.result && job.result.project && job.result.project.id) || '';
    return {
      status: status, done: done, failed: failed, cancelled: cancelled, terminal: done || failed || cancelled,
      cancelRequested: Boolean(job.cancel_requested), importMode: Boolean(job.import_mode), stages: stages, progress: deriveProgress(job, stages, done),
      logs: normalizeLogs(job.logs || job.log || job.events), projectId: projectId ? String(projectId) : '', error: error,
      browser: job.browser && typeof job.browser === 'object' ? job.browser : null,
      queuePosition: Number(job.queue_position) || 0,
      title: String(job.title || (job.project && job.project.title) || ''), engine: String(job.engine || ''), stageName: String(job.stage_name || '') }; }
  const startPolling = (token) => { window.clearTimeout(state.pollTimer); state.pollTimer = window.setTimeout(() => pollJob(token), POLL_MS); };
  function closeJobStream() {
    if (state.jobStream) { try { state.jobStream.close(); } catch (_) { /* already closed */ } state.jobStream = null; }
  }
  function applyJobUpdate(raw, token) {
    if (token !== state.jobToken || !state.jobId) return true;
    const job = normalizeJob(raw);
    renderStages(job.stages); setProgress(job.progress); renderLogs(job.logs);
    if (job.cancelled) { finishJob(job); return true; }
    if (job.status === 'queued') {
      setStageBadge('running', 'Queued');
      setText('pipeline-stage-name', 'Queued');
      setPipelineStatus('running', job.queuePosition ? 'Queued — position ' + job.queuePosition + ' in line.' : 'Queued — waiting for the current build to finish.');
      return false;
    }
    const active = job.stages.find((stage) => stage.status === 'active');
    if (job.stageName || active) setText('pipeline-stage-name', job.stageName || (active ? active.label : 'Stitching…'));
    if (!job.terminal) {
      const activeIndex = job.stages.findIndex((stage) => stage.status === 'active');
      setPipelineStatus('running', job.cancelRequested ? 'Cancelling after the current model request…'
        : activeIndex >= 0 ? 'Stage ' + (activeIndex + 1) + ' of 9 · ' + job.stages[activeIndex].label : 'Stitching the site…');
      return false;
    }
    finishJob(job); return true;
  }
  async function pollJob(token) {
    if (token !== state.jobToken || !state.jobId) return;
    try {
      const raw = await api('/api/jobs/' + encodeURIComponent(state.jobId)); if (token !== state.jobToken) return;
      state.pollFails = 0;
      if (!applyJobUpdate(raw, token)) startPolling(token);
    } catch (error) {
      if (token !== state.jobToken) return;
      state.pollFails += 1;
      if (state.pollFails >= MAX_POLL_FAILS) {
        finishJob({ status: 'error', failed: true, done: false, terminal: true, stages: state.stages, progress: state.progress, logs: [], projectId: '', error: 'Lost the connection to the backend (' + error.message + ').', title: '', engine: '', stageName: '' });
        return; }
      setPipelineStatus('running', 'Connection hiccup — retrying (' + state.pollFails + '/' + MAX_POLL_FAILS + ')…'); startPolling(token); } }
  function followJob(token) {
    if (!state.jobId) return;
    if (JOBS && JOBS.follow) {
      const stream = JOBS.follow(state.jobId, {
        update: (raw) => { if (token === state.jobToken) applyJobUpdate(raw, token); },
        error: () => {
          if (token !== state.jobToken) return;
          state.jobStream = null;
          state.pollFails = 0;
          setPipelineStatus('running', 'Live stream interrupted — falling back to polling.');
          startPolling(token);
        },
      });
      if (stream) { state.jobStream = stream; return; }
    }
    startPolling(token);
  }
  async function cancelGeneration() {
    if (!state.generating || !state.jobId) return;
    const button = $('pipeline-cancel');
    if (button) { button.disabled = true; button.textContent = 'Cancelling…'; }
    try {
      const result = JOBS && JOBS.cancel ? await JOBS.cancel(state.jobId)
        : await api('/api/jobs/' + encodeURIComponent(state.jobId) + '/cancel', { method: 'POST', body: {} });
      if (result && result.already_finished) {
        toast('The build already finished.', 'info');
        const raw = await api('/api/jobs/' + encodeURIComponent(state.jobId));
        applyJobUpdate(raw, state.jobToken);
      } else if (result && result.status === 'cancelled') {
        const raw = await api('/api/jobs/' + encodeURIComponent(state.jobId));
        applyJobUpdate(raw, state.jobToken);
      } else {
        toast('Cancellation requested. The build will stop after the current request.', 'info');
        setPipelineStatus('running', 'Cancelling after the current model request…');
      }
    } catch (error) {
      toast('Could not cancel the build: ' + error.message, 'error');
      if (button) { button.disabled = false; button.textContent = 'Cancel build'; }
    }
  }
  function finishJob(job) {
    state.generating = false; state.jobToken += 1; window.clearTimeout(state.pollTimer); closeJobStream(); setGenerateBusy(false);
    setHidden('pipeline-cancel', true);
    if (job.cancelled) {
      renderStages(job.stages); setProgress(job.progress);
      setPipelineStatus('error', 'Build cancelled. The previous project was left untouched.');
      setStageBadge('error', 'Cancelled');
      showPipelineError(job.error || 'Build cancelled. The previous project was left untouched.');
      setText('pipeline-foot', 'Adjust the brief or settings, then start a new build.');
      toast('Build cancelled. The previous project was left untouched.', 'info', 5000);
      switchTab('pipeline'); return;
    }
    if (job.failed) {
      renderStages(job.stages); setProgress(job.progress);
      const failing = job.stages.find((stage) => stage.status === 'error');
      setPipelineStatus('error', failing ? 'Stopped at “' + failing.label + '” — see the logs.' : 'The stitch stopped unexpectedly.');
      setStageBadge('error', 'Failed');
      showPipelineError(job.error || 'Generation failed. Check the Logs tab for the failing stage.');
      setText('pipeline-foot', 'Check the Logs tab, adjust the brief, then try again.');
      toast(job.error ? 'Generation failed: ' + job.error : 'Generation failed. Check the logs.', 'error', 6000);
      switchTab('pipeline'); return; }
    renderStages(job.stages); setProgress(100);
    setPipelineStatus('done', 'All nine stages stitched. Your site is ready in the Preview tab.');
    setStageBadge('done', 'Ready'); setHidden('pipeline-success', false);
    if (canAnimate()) window.gsap.from($('success-badge'), { scale: 0.4, rotate: -18, opacity: 0, duration: 0.5, ease: 'back.out(2)' });
    setText('success-text', '“' + (job.title || state.runningTitle) + '” is stitched and packaged.');
    setText('pipeline-foot', 'Open the ZIP export or preview the site in a new tab.');
    setText('pipeline-stage-name', 'All nine stages complete');
    if (job.projectId) {
      openPreview({ id: job.projectId, title: job.title || state.runningTitle, engine: job.engine || (($('demo-mode') || {}).checked ? 'mock' : 'ai') });
      switchTab('preview'); toast('Site stitched. Preview is ready.', 'success'); loadProjects();
    } else {
      showPipelineError('The job finished but did not return a project id.');
      toast('Job finished without a project id — check the logs.', 'error'); }
    if (job.browser) renderBrowserReport(job.browser); }
  async function generate() {
    if (state.generating) { toast('A stitch is already running.', 'info'); return; }
    const theme = currentTheme();
    if (!theme) { showThemeError('Pick a theme before generating.'); goToStep(3); toast('Pick a theme first.', 'error'); return; }
    const prompt = $('prompt'), brief = prompt ? prompt.value.trim() : '';
    if (!brief) { showPromptError('Write a short brief before generating.'); goToStep(4); if (prompt) prompt.focus(); return; }
    const engine = ($('demo-mode') || {}).checked ? 'mock' : 'ai';
    if (state.importFiles.length && engine === 'mock') {
      showGenerateError('Continue mode needs the AI engine. Turn off demo mode and configure an AI provider.');
      goToStep(1);
      toast('Continue mode needs an AI provider — demo mode cannot complete an imported site.', 'error', 5500);
      return;
    }
    if (engine === 'ai' && !canUseAI()) {
      showGenerateError('This provider needs an API key — choose a free provider in Setup, add your key, or switch on demo mode.');
      goToStep(1); if ($('api-key')) $('api-key').focus(); toast('Choose a free provider or add a key to generate with AI.', 'error'); return; }
    setHidden('generate-error', true); setHidden('theme-error', true); setHidden('prompt-error', true);
    const titleInput = $('site-title');
    const payload = {
      theme_id: theme.id, title: titleInput ? titleInput.value.trim() : '', prompt: brief, engine: engine,
      database: databasePayload(), import_files: state.importFiles.length ? state.importFiles : undefined,
    };
    state.generating = true; state.jobToken += 1; const token = state.jobToken; state.jobId = null;
    setGenerateBusy(true); resetPipelineUI(theme); switchTab('pipeline');
    try {
      const response = await api('/api/generate', { method: 'POST', body: payload });
      const jobId = response && (response.job_id || response.id);
      if (!jobId) throw new Error('The server did not return a job id.');
      state.jobId = String(jobId);
      const cancelButton = $('pipeline-cancel'); if (cancelButton) { cancelButton.disabled = false; cancelButton.textContent = 'Cancel build'; }
      announce('Generation started.'); followJob(token);
      if (response && response.queued) toast('A build is already running — this one is queued.', 'info');
    } catch (error) {
      state.generating = false; setGenerateBusy(false);
      setPipelineStatus('error', 'Could not start the stitch.'); setStageBadge('error', 'Failed');
      showPipelineError(error.message);
      setText('pipeline-foot', 'The job could not be started. Fix the error above and retry.');
      toast('Could not start generation: ' + error.message, 'error', 6000); } }
  function bindGeneration() {
    on($('generate-btn'), 'click', generate); on($('pipeline-retry'), 'click', generate);
    on($('pipeline-cancel'), 'click', cancelGeneration);
    on($('pipeline-see-logs'), 'click', () => switchTab('logs'));
    on($('success-view'), 'click', () => switchTab('preview'));
    on($('logs-clear'), 'click', clearLogsPanel);
    setPipelineStatus('idle', 'Idle — nothing is being stitched yet.'); setStageBadge('idle', 'Idle');
    renderStages(blankStages()); setProgress(0, true); }

  /* ---------- 16. Project history ------------------------------------------ */
  function normalizeProject(raw) {
    if (!raw || typeof raw !== 'object') return null;
    const id = String(raw.id || ''); if (!id) return null;
    return {
      id: id, title: String(raw.title || 'Untitled site'), theme_id: String(raw.theme_id || raw.theme || ''),
      engine: String(raw.engine || ''), database_mode: String(raw.database_mode || ''), files: Number(raw.files) || 0,
      created_at: String(raw.created_at || raw.updated_at || ''), summary: String(raw.summary || '') }; }
  function renderProjects() {
    setText('history-count', String(state.projects.length));
    setText('history-meta', state.projects.length ? state.projects.length + ' project' + (state.projects.length === 1 ? '' : 's') + ' on this machine' : '');
    setHidden('history-empty', state.projects.length > 0);
    const list = $('history-list'); if (!list) return;
    clear(list);
    state.projects.forEach((project) => {
      const item = el('li', 'history__item'), open = el('button', 'history__open');
      open.type = 'button'; open.appendChild(el('span', 'history__title', project.title));
      const meta = el('span', 'history__meta');
      meta.append(el('span', '', themeName(project.theme_id)), el('span', '', project.engine === 'mock' ? 'Demo' : 'AI'), el('span', '', formatDate(project.created_at)));
      if (project.files) meta.appendChild(el('span', '', project.files + ' file' + (project.files === 1 ? '' : 's')));
      open.appendChild(meta);
      open.addEventListener('click', () => { closeHistory(); openPreview({ id: project.id, title: project.title, engine: project.engine }); switchTab('preview'); announce('Loaded project ' + project.title + '.'); });
      const remove = el('button', 'history__delete');
      remove.type = 'button'; remove.setAttribute('aria-label', 'Delete ' + project.title); remove.appendChild(trashIcon());
      remove.addEventListener('click', (event) => { event.stopPropagation(); deleteProject(project); });
      item.append(open, remove); list.appendChild(item); }); }
  async function loadProjects() {
    try {
      const data = await api('/api/projects'), list = Array.isArray(data) ? data : (data && data.projects) || [];
      state.projects = list.map(normalizeProject).filter(Boolean); renderProjects(); return true;
    } catch (error) {
      if (!state.projects.length) {
        const empty = $('history-empty');
        if (empty) { empty.hidden = false; empty.textContent = 'Could not load project history: ' + error.message; }
        setText('history-meta', 'Offline'); }
      return false; } }
  async function deleteProject(project) {
    const confirmed = await confirmAction({
      title: 'Delete this project?', message: '“' + project.title + '” and its generated files will be removed from this machine. This cannot be undone.',
      confirmLabel: 'Delete project', danger: true });
    if (!confirmed) return;
    try {
      await api('/api/projects/' + encodeURIComponent(project.id), { method: 'DELETE' });
      state.projects = state.projects.filter((item) => item.id !== project.id); renderProjects();
      if (state.preview && state.preview.projectId === project.id) resetPreview();
      toast('Project deleted.', 'success');
    } catch (error) { toast('Could not delete the project: ' + error.message, 'error'); } }
  function openHistory() {
    const dialog = $('history-dialog'); if (!dialog) return;
    if (typeof dialog.showModal === 'function') { if (!dialog.open) dialog.showModal(); } else dialog.setAttribute('open', '');
    loadProjects(); const close = $('history-close'); if (close) close.focus(); }
  function closeHistory() {
    const dialog = $('history-dialog'); if (!dialog) return;
    if (dialog.open && typeof dialog.close === 'function') dialog.close(); else dialog.removeAttribute('open'); }
  function bindHistory() {
    on($('history-open'), 'click', openHistory); on($('preview-history-btn'), 'click', openHistory); on($('history-close'), 'click', closeHistory);
    on($('history-refresh'), 'click', async () => {
      const button = $('history-refresh'); setBusy(button, true);
      const ok = await loadProjects(); setBusy(button, false);
      toast(ok ? 'Project history refreshed.' : 'Could not refresh project history.', ok ? 'success' : 'error'); });
    const dialog = $('history-dialog');
    on(dialog, 'click', (event) => { if (event.target === dialog) closeHistory(); });
    on(dialog, 'cancel', (event) => { event.preventDefault(); closeHistory(); }); }

  /* ---------- 17. Connection + bootstrap ----------------------------------- */
  function setConnection(online) {
    state.online = Boolean(online);
    const pill = $('status-pill'), text = $('status-text');
    if (pill) pill.dataset.state = state.online ? 'online' : 'offline';
    if (text) text.textContent = state.online ? 'Online' : 'Offline';
    setHidden('offline-banner', state.online && !state.themesOffline);
    updateDemoButton(); }
  function ensureInitialTheme() {
    if (!state.themes.length) return;
    if (currentTheme()) { selectTheme(state.selectedThemeId, { persist: false, silent: true }); return; }
    const remembered = readStorage(STORAGE.theme), match = remembered && state.themes.find((theme) => theme.id === remembered);
    selectTheme((match || state.themes[0]).id, { silent: true }); }
  async function bootstrap(options) {
    const opts = options || {}; if (state.booting) return;
    state.booting = true;
    const retry = $('offline-retry'); setBusy(retry, true); setText('status-text', 'Connecting…');
    const [status, settings, themes, skills, projects] = await Promise.allSettled([
      api('/api/status'), api('/api/settings'), api('/api/themes'), api('/api/skills'), api('/api/projects') ]);
    let online = false;
    if (status.status === 'fulfilled' && status.value) { online = true; try { applyStatus(status.value); } catch (_) { /* tolerate drift */ } }
    if (settings.status === 'fulfilled') { try { applySettings(settings.value); } catch (_) { /* tolerate drift */ } }
    if (themes.status === 'fulfilled') {
      const value = themes.value, list = Array.isArray(value) ? value : (value && value.themes) || [];
      const parsed = list.map(normalizeTheme).filter(Boolean);
      if (parsed.length) { state.themes = parsed; state.themesOffline = false; renderThemes(); online = true; } }
    if (!state.themes.length) await loadThemes();
    if (skills.status === 'fulfilled') {
      const value = skills.value, list = Array.isArray(value) ? value : (value && value.skills) || [];
      state.skills = list.map(normalizeSkill).filter(Boolean); if (state.skills.length) online = true; }
    renderSkillsNote();
    if (projects.status === 'fulfilled') {
      const value = projects.value, list = Array.isArray(value) ? value : (value && value.projects) || [];
      state.projects = list.map(normalizeProject).filter(Boolean); renderProjects(); }
    state.booting = false;
    setConnection(online); syncKeyStates(); updateSummary(); updateGenerateNote(); setBusy(retry, false);
    if (!online) toast('Backend offline — showing built-in theme samples. Start the Stitchcraft server, then retry.', 'error', 6500);
    else if (opts.manual) toast('Connected to the Stitchcraft backend.', 'success');
    if (!opts.silent) announce(online ? 'Studio ready.' : 'Backend offline.');
    ensureInitialTheme(); }
  function bindLanguage() {
    const select = $('language-select');
    if (!select || !I18N) return;
    select.value = I18N.getLanguage();
    on(select, 'change', async () => {
      const language = String(select.value || 'en');
      I18N.setLanguage(language);
      state.settings = state.settings || {};
      state.settings.ui = Object.assign({}, state.settings.ui || {}, { language: language });
      try { await api('/api/settings', { method: 'POST', body: { ui: { language: language } } }); }
      catch (_) { /* the choice is still remembered locally */ }
    });
  }

  function bindConnection() {
    on($('offline-retry'), 'click', () => bootstrap({ manual: true }));
    window.addEventListener('offline', () => { setConnection(false); toast('Network offline.', 'error'); });
    window.addEventListener('online', () => bootstrap({ silent: true })); }

  /* ---------- 18. Keyboard + init ------------------------------------------ */
  function bindGlobalKeys() {
    document.addEventListener('keydown', (event) => {
      trapConfirmFocus(event);
      const modal = $('app-confirm');
      if (event.key === 'Escape' && modal && !modal.hidden) { event.preventDefault(); closeConfirm(false); return; }
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') { event.preventDefault(); generate(); } });
    window.addEventListener('unhandledrejection', (event) => { if (window.console && console.warn) console.warn('[stitchcraft] unhandled promise rejection', event.reason); }); }
  async function loadLibrariesNote() {
    if ($('library-note')) return;
    try {
      const response = await api('/api/libraries');
      const libs = Array.isArray(response && response.libraries) ? response.libraries : [];
      if (!libs.length) return;
      const note = el('p', 'step__note step__note--skills');
      note.id = 'library-note';
      note.textContent = 'Bundled tool packs (offline, licensed): ' + libs
        .map((lib) => lib.name + (lib.version ? ' ' + lib.version : ''))
        .join(' · ');
      const grid = $('theme-grid');
      if (grid && grid.parentNode) grid.parentNode.insertBefore(note, grid.nextSibling);
      else if ($('step-3')) $('step-3').appendChild(note);
    } catch (_) { /* optional: the theme list works without it */ } }

  function init() {
    PLACEHOLDERS.api = (($('api-key') || {}).placeholder) || 'sk-…';
    PLACEHOLDERS.db = (($('db-key') || {}).placeholder) || 'public anon key';
    makeEmbers(); initTabs(); initWizard(); bindSettings(); bindBrief(); bindImport(); bindGeneration();
    bindHistory(); bindPreview(); bindLanguage(); bindConnection(); bindGlobalKeys(); bindBrowser();
    paintRange(); updateSummary(); updateGenerateNote(); syncKeyStates(); syncProviderUI(); setPreviewLoading(false);
    bootstrap({ silent: true }); loadLibrariesNote(); loadBrowser();
    animateEntrance(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
