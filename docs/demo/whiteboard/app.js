/*!
 * Stitchcraft Whiteboard — offline demo application
 * Fabric.js 5.2.4 (vendored) · system fonts · no external requests
 * 01 Constants · 02 Helpers · 03 Sticky notes · 04 Canvas · 05 History
 * 06 Persistence · 07 Tools · 08 Counters · 09 Drawing · 10 Sample board
 * 11 Export · 12 Dialog · 13 Keyboard · 14 Wiring + boot
 */
(function () {
  'use strict';

  /* 01 · Constants and state */
  const STORAGE_KEY = 'stitchcraft:whiteboard';
  const BOARD_W = 1280, BOARD_H = 800, BOARD_BG = '#131018';
  const HISTORY_LIMIT = 40, HISTORY_MS = 260, AUTOSAVE_MS = 600, STICKY_PAD = 20;
  const FONT_SANS = '"Segoe UI Variable Text", "Segoe UI", system-ui, Arial, sans-serif';
  const FONT_DISPLAY = '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Palatino, Georgia, serif';
  const FONT_MONO = '"Cascadia Code", "Cascadia Mono", Consolas, Menlo, monospace';
  const TOOL_NAMES = { select: 'Select and move', pen: 'Pen', marker: 'Highlighter', rect: 'Rectangle', ellipse: 'Ellipse', arrow: 'Arrow', text: 'Text', eraser: 'Eraser' };
  const KEY_TOOLS = { v: 'select', p: 'pen', h: 'marker', r: 'rect', o: 'ellipse', a: 'arrow', t: 'text', e: 'eraser' };
  const COLOR_NAMES = { '#ff8a3d': 'ember', '#a78bfa': 'violet', '#f5efe6': 'bone', '#e7c27a': 'gold', '#8fdf9e': 'moss' };
  const state = { tool: 'select', color: '#ff8a3d', width: 3, ready: false, restoring: false, draft: null, history: [], historyIndex: -1, historyTimer: 0, saveTimer: 0 };
  let canvas = null, els = {}, askConfirm = null, dialogReturnFocus = null, resizeFrame = 0;

  /* 02 · DOM helpers */
  const byId = (id) => document.getElementById(id);
  const all = (selector) => Array.from(document.querySelectorAll(selector));
  const bind = (element, type, handler) => { if (element) { element.addEventListener(type, handler); } };
  const announce = (message) => { if (els.status) { els.status.textContent = message; } };
  const isFormField = (target) => Boolean(target) && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT' || target.isContentEditable === true);
  const toolButton = (tool) => els.toolButtons.find((button) => button.dataset.tool === tool) || null;
  const syncToolRoving = (active) => els.toolButtons.forEach((button) => { button.tabIndex = button === active ? 0 : -1; });
  function setSaveChip(mode, label) {
    if (!els.saveChip) { return; }
    els.saveChip.dataset.state = mode;
    if (els.saveChipLabel) { els.saveChipLabel.textContent = label; }
  }
  function hexToRgba(hex, alpha) {
    let value = String(hex || '').replace('#', '');
    if (value.length === 3) { value = value[0] + value[0] + value[1] + value[1] + value[2] + value[2]; }
    const number = parseInt(value, 16);
    if (value.length !== 6 || Number.isNaN(number)) { return `rgba(255, 138, 61, ${alpha})`; }
    return `rgba(${(number >> 16) & 255}, ${(number >> 8) & 255}, ${number & 255}, ${alpha})`;
  }
  function roundRect(ctx, x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + width - r, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + r);
    ctx.lineTo(x + width, y + height - r);
    ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
    ctx.lineTo(x + r, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  /* 03 · Sticky-note class (rounded Textbox with inner padding) */
  function defineStickyClass() {
    fabric.StickyNote = fabric.util.createClass(fabric.Textbox, {
      type: 'stickyNote',
      _getNonTransformedDimensions() {
        const dim = this.callSuper('_getNonTransformedDimensions');
        return { x: dim.x + STICKY_PAD * 2, y: dim.y + STICKY_PAD * 2 };
      },
      getLocalPointer(event, pointer) {
        const local = this.callSuper('getLocalPointer', event, pointer);
        local.x -= STICKY_PAD * this.scaleX;
        local.y -= STICKY_PAD * this.scaleY;
        return local;
      },
      _renderBackground(ctx) {
        const dim = this._getNonTransformedDimensions(), x = -dim.x / 2, y = -dim.y / 2;
        ctx.save();
        ctx.beginPath();
        roundRect(ctx, x, y, dim.x, dim.y, 14);
        ctx.fillStyle = this.backgroundColor || '#f5efe6';
        ctx.fill();
        ctx.save();
        ctx.clip();
        ctx.fillStyle = 'rgba(14, 12, 18, 0.07)';
        ctx.fillRect(x, y, dim.x, 7);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.12)';
        ctx.fillRect(x, y, dim.x, 1.5);
        ctx.restore();
        ctx.beginPath();
        roundRect(ctx, x, y, dim.x, dim.y, 14);
        ctx.strokeStyle = 'rgba(14, 12, 18, 0.14)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.restore();
        this._removeShadow(ctx);
      }
    });
  }
  function styleLine(line, text, style) {
    const styles = { [line]: {} };
    for (let index = 0; index < text.length; index += 1) { styles[line][index] = style; }
    return styles;
  }

  /* 04 · Canvas and viewport */
  function initCanvas() {
    canvas = new fabric.Canvas(els.canvasEl, {
      backgroundColor: BOARD_BG, selectionColor: 'rgba(139, 92, 246, 0.16)', selectionBorderColor: '#8b5cf6',
      selectionLineWidth: 1.5, preserveObjectStacking: true, stopContextMenu: true, renderOnAddRemove: true
    });
    fabric.Object.prototype.set({
      borderColor: '#ff8a3d', cornerColor: '#ff8a3d', cornerStrokeColor: BOARD_BG,
      cornerSize: 9, cornerStyle: 'circle', transparentCorners: false, padding: 4, borderScaleFactor: 1.5
    });
    ['object:added', 'object:modified', 'object:removed', 'path:created', 'text:editing:exited'].forEach((type) => canvas.on(type, onBoardChange));
    canvas.on('text:changed', () => { if (state.ready && !state.restoring) { scheduleAutosave(); } });
    canvas.on('mouse:down', onPointerDown);
    canvas.on('mouse:move', onPointerMove);
    canvas.on('mouse:up', onPointerUp);
    canvas.on('mouse:dblclick', onDoubleClick);
  }
  function resizeCanvas() {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => {
      if (!canvas || !els.stage) { return; }
      const width = Math.max(320, els.stage.clientWidth), height = Math.max(280, els.stage.clientHeight);
      canvas.setDimensions({ width, height });
      const zoom = Math.max(0.2, Math.min(width / BOARD_W, height / BOARD_H) * 0.94);
      canvas.setViewportTransform([zoom, 0, 0, zoom, (width - BOARD_W * zoom) / 2, (height - BOARD_H * zoom) / 2]);
      canvas.calcOffset();
      canvas.requestRenderAll();
    });
  }
  function onBoardChange() {
    if (!state.ready || state.restoring || state.draft) { return; }
    updateCounters();
    scheduleHistory();
  }

  /* 05 · History */
  const snapshot = () => JSON.stringify(canvas.toJSON());
  function updateHistoryButtons() {
    if (els.undo) { els.undo.disabled = state.historyIndex <= 0; }
    if (els.redo) { els.redo.disabled = state.historyIndex >= state.history.length - 1; }
  }
  function resetHistory() {
    state.history = [snapshot()];
    state.historyIndex = 0;
    updateHistoryButtons();
  }
  function scheduleHistory() {
    if (state.ready && !state.restoring) {
      clearTimeout(state.historyTimer);
      state.historyTimer = setTimeout(commitHistory, HISTORY_MS);
    }
  }
  function commitHistory() {
    if (!state.ready || state.restoring) { return; }
    const snap = snapshot();
    if (state.history[state.historyIndex] === snap) { return; }
    state.history = state.history.slice(0, state.historyIndex + 1);
    state.history.push(snap);
    if (state.history.length > HISTORY_LIMIT) { state.history.shift(); }
    state.historyIndex = state.history.length - 1;
    updateHistoryButtons();
    scheduleAutosave();
  }
  function restoreSnapshot(json, done) {
    state.restoring = true;
    canvas.discardActiveObject();
    canvas.loadFromJSON(json, () => {
      state.restoring = false;
      canvas.backgroundColor = canvas.backgroundColor || BOARD_BG;
      canvas.renderAll();
      updateCounters();
      updateHistoryButtons();
      if (typeof done === 'function') { done(); }
    });
  }
  function stepHistory(delta) {
    const next = state.historyIndex + delta;
    if (next < 0) { announce('Nothing left to undo.'); return; }
    if (next >= state.history.length) { announce('Nothing to redo.'); return; }
    clearTimeout(state.historyTimer);
    state.historyIndex = next;
    restoreSnapshot(state.history[next]);
    updateHistoryButtons();
    scheduleAutosave();
    announce(delta < 0 ? 'Undone.' : 'Redone.');
  }
  const undo = () => stepHistory(-1);
  const redo = () => stepHistory(1);

  /* 06 · Persistence (autosave, save, load) */
  function scheduleAutosave() {
    if (!state.ready || state.restoring) { return; }
    setSaveChip('saving', 'Saving…');
    clearTimeout(state.saveTimer);
    state.saveTimer = setTimeout(() => saveBoard(false), AUTOSAVE_MS);
  }
  function saveBoard(announced) {
    if (!canvas) { return false; }
    try {
      const payload = { version: 1, app: 'stitchcraft-whiteboard', savedAt: new Date().toISOString(), board: canvas.toJSON() };
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
      setSaveChip('saved', 'Saved on this device');
      if (announced) { announce('Board saved to this device.'); }
      return true;
    } catch (error) {
      setSaveChip('error', 'Saving unavailable');
      if (announced) { announce('Saving is unavailable in this browser.'); }
      return false;
    }
  }
  function readSavedBoard() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const data = raw ? JSON.parse(raw) : null;
      return data && data.board && Array.isArray(data.board.objects) && data.board.objects.length ? data.board : null;
    } catch (error) {
      return null;
    }
  }
  function loadBoard(announced) {
    const saved = readSavedBoard();
    if (!saved) { if (announced) { announce('No saved board found on this device yet.'); } return; }
    if (announced) { setSaveChip('saving', 'Loading…'); }
    restoreSnapshot(JSON.stringify(saved), () => {
      resetHistory();
      setSaveChip('saved', 'Saved on this device');
      announce('Saved board loaded from this device.');
    });
  }

  /* 07 · Tool selection and styling */
  function configureBrush() {
    if (!canvas) { return; }
    const marker = state.tool === 'marker', brush = new fabric.PencilBrush(canvas);
    brush.width = marker ? Math.max(16, state.width * 4.5) : state.width;
    brush.color = marker ? hexToRgba(state.color, 0.34) : state.color;
    brush.decimate = 2;
    canvas.freeDrawingBrush = brush;
    canvas.freeDrawingCursor = 'crosshair';
  }
  function setTool(tool, options = {}) {
    if (!canvas || !TOOL_NAMES[tool]) { return; }
    state.tool = tool;
    const drawing = tool === 'pen' || tool === 'marker';
    canvas.isDrawingMode = drawing;
    canvas.selection = tool === 'select';
    canvas.defaultCursor = tool === 'select' ? 'default' : 'crosshair';
    canvas.hoverCursor = tool === 'select' ? 'move' : 'crosshair';
    if (drawing) { configureBrush(); }
    canvas.forEachObject((object) => {
      object.selectable = tool === 'select';
      object.evented = tool === 'select' || tool === 'eraser';
    });
    if (!options.keepSelection) { canvas.discardActiveObject(); }
    els.toolButtons.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.tool === tool)));
    const active = toolButton(tool);
    if (active && document.activeElement !== active) { syncToolRoving(active); }
    if (!options.quiet) { announce(`${TOOL_NAMES[tool]} selected · ink ${COLOR_NAMES[state.color] || 'custom'} · weight ${state.width}.`); }
    canvas.requestRenderAll();
  }
  function setColor(hex, options = {}) {
    state.color = hex;
    if (els.colorInput) { els.colorInput.value = hex; }
    els.swatches.forEach((button) => button.setAttribute('aria-pressed', String((button.dataset.color || '').toLowerCase() === hex.toLowerCase())));
    if (state.tool === 'pen' || state.tool === 'marker') { configureBrush(); }
    if (!options.quiet) { announce(`Ink colour ${COLOR_NAMES[hex.toLowerCase()] || hex} · ${TOOL_NAMES[state.tool]}.`); }
  }
  function setWidth(value, options = {}) {
    const width = Math.max(1, Math.min(20, parseInt(value, 10) || 3));
    state.width = width;
    if (els.widthInput) { els.widthInput.value = String(width); }
    if (els.widthValue) { els.widthValue.textContent = String(width); }
    if (state.tool === 'pen' || state.tool === 'marker') { configureBrush(); }
    if (!options.quiet) { announce(`Stroke weight ${width} pixels.`); }
  }

  /* 08 · Counters */
  function updateCounters() {
    const count = canvas ? canvas.getObjects().length : 0;
    if (els.markCount) { els.markCount.textContent = count === 1 ? '1 mark' : `${count} marks`; }
    if (els.empty) { els.empty.hidden = count > 0; }
  }

  /* 09 · Drawing tools */
  function draftShape(kind, x, y) {
    const common = { left: x, top: y, stroke: state.color, strokeWidth: state.width, selectable: false, evented: false, strokeUniform: true, objectCaching: false };
    if (kind === 'rect') { return new fabric.Rect({ ...common, rx: 4, ry: 4, fill: hexToRgba(state.color, 0.09) }); }
    if (kind === 'ellipse') { return new fabric.Ellipse({ ...common, rx: 1, ry: 1, fill: hexToRgba(state.color, 0.09) }); }
    return new fabric.Line([x, y, x, y], { stroke: state.color, strokeWidth: state.width, strokeLineCap: 'round', selectable: false, evented: false, strokeUniform: true, objectCaching: false });
  }
  function addArrow(x1, y1, x2, y2) {
    const angle = Math.atan2(y2 - y1, x2 - x1), head = Math.max(11, state.width * 4.5);
    const line = new fabric.Line([x1, y1, x2, y2], { stroke: state.color, strokeWidth: state.width, strokeLineCap: 'round', strokeUniform: true, selectable: false, evented: false });
    const tip = new fabric.Triangle({ left: x2, top: y2, width: head, height: head * 1.15, fill: state.color, originX: 'center', originY: 'center', angle: angle * 180 / Math.PI + 90, selectable: false, evented: false });
    const group = new fabric.Group([line, tip], { selectable: true, evented: true });
    canvas.add(group);
    return group;
  }
  function updateDraft(pointer, shiftKey) {
    const draft = state.draft;
    if (!draft) { return; }
    const dx = pointer.x - draft.startX, dy = pointer.y - draft.startY;
    if (draft.kind === 'arrow') {
      let endX = pointer.x, endY = pointer.y;
      if (shiftKey) { if (Math.abs(dx) > Math.abs(dy)) { endY = draft.startY; } else { endX = draft.startX; } }
      draft.shape.set({ x2: endX, y2: endY });
      return;
    }
    let width = Math.abs(dx), height = Math.abs(dy);
    if (shiftKey) { width = height = Math.max(width, height); }
    const left = dx < 0 ? draft.startX - width : draft.startX, top = dy < 0 ? draft.startY - height : draft.startY;
    if (draft.kind === 'ellipse') { draft.shape.set({ left, top, rx: width / 2, ry: height / 2 }); }
    else { draft.shape.set({ left, top, width, height }); }
    draft.shape.setCoords();
  }
  function onPointerDown(event) {
    if (!state.ready || state.restoring || !event.e) { return; }
    if (state.tool === 'eraser') {
      if (event.target) { canvas.remove(event.target); canvas.discardActiveObject(); canvas.requestRenderAll(); announce('Mark erased · Ctrl+Z brings it back.'); }
      return;
    }
    if (state.tool === 'text') { createText(canvas.getPointer(event.e)); return; }
    if (!['rect', 'ellipse', 'arrow'].includes(state.tool)) { return; }
    const pointer = canvas.getPointer(event.e);
    state.draft = { kind: state.tool, startX: pointer.x, startY: pointer.y, shape: draftShape(state.tool, pointer.x, pointer.y) };
    canvas.add(state.draft.shape);
    canvas.requestRenderAll();
  }
  function onPointerMove(event) {
    if (!state.draft || !event.e) { return; }
    updateDraft(canvas.getPointer(event.e), event.e.shiftKey);
    canvas.requestRenderAll();
  }
  function onPointerUp(event) {
    const draft = state.draft;
    if (!draft || !event.e) { return; }
    state.draft = null;
    const pointer = canvas.getPointer(event.e);
    canvas.remove(draft.shape);
    if (Math.abs(pointer.x - draft.startX) < 6 && Math.abs(pointer.y - draft.startY) < 6) {
      canvas.requestRenderAll();
      announce(`Drag to draw a ${TOOL_NAMES[draft.kind].toLowerCase()}.`);
      return;
    }
    let object;
    if (draft.kind === 'arrow') {
      object = addArrow(draft.startX, draft.startY, pointer.x, pointer.y);
    } else {
      draft.shape.set({ selectable: true, evented: true });
      canvas.add(draft.shape);
      object = draft.shape;
    }
    setTool('select', { quiet: true, keepSelection: true });
    canvas.setActiveObject(object);
    canvas.requestRenderAll();
    announce(`${TOOL_NAMES[draft.kind]} added · drag to move, Delete to remove.`);
  }
  function createText(pointer) {
    const text = new fabric.Textbox('Type something', { left: pointer.x, top: pointer.y, width: 260, fontSize: 20, fill: state.color, fontFamily: FONT_SANS, lineHeight: 1.35, padding: 6 });
    setTool('select', { quiet: true, keepSelection: true });
    canvas.add(text);
    canvas.setActiveObject(text);
    text.enterEditing();
    text.selectAll();
    canvas.requestRenderAll();
    announce('Text added · type your words, then press Escape.');
  }
  function onDoubleClick(event) {
    const target = event.target;
    if (!target || !['textbox', 'stickyNote'].includes(target.type)) { return; }
    canvas.setActiveObject(target);
    target.enterEditing();
    target.selectAll();
    announce('Editing text · press Escape when you are done.');
  }
  function removeSelection() {
    if (!canvas) { return; }
    const active = canvas.getActiveObject();
    if (!active) { announce('Nothing selected · click a mark first.'); return; }
    if (active.type === 'activeSelection') {
      const items = active.getObjects().slice();
      canvas.discardActiveObject();
      items.forEach((object) => canvas.remove(object));
    } else { canvas.remove(active); canvas.discardActiveObject(); }
    canvas.requestRenderAll();
    announce('Selection removed · Ctrl+Z brings it back.');
  }
  function clearBoard() {
    if (!canvas) { return; }
    state.restoring = true;
    canvas.discardActiveObject();
    canvas.clear();
    canvas.backgroundColor = BOARD_BG;
    state.restoring = false;
    canvas.renderAll();
    setTool(state.tool, { quiet: true });
    commitHistory();
    updateCounters();
    scheduleAutosave();
    announce('Board cleared · Ctrl+Z brings the old board back.');
  }

  /* 10 · Sample board */
  const textAt = (string, options) => { const item = new fabric.Textbox(string, options); canvas.add(item); return item; };
  function addSticky(options) {
    const styles = styleLine(0, options.title, { fontWeight: '700', fontSize: 15.5, fill: options.titleColor || '#241a14', fontFamily: FONT_SANS });
    return textAt(`${options.title}\n${options.body || ''}`, {
      left: options.left, top: options.top, width: options.width - STICKY_PAD * 2,
      backgroundColor: options.fill, fill: options.bodyColor || '#3a2a20',
      fontFamily: FONT_SANS, fontSize: 14.5, lineHeight: 1.42, styles
    });
  }
  function addSpark(size, fill, left, top, opacity) {
    const path = 'M 0 -1 L 0.26 -0.26 L 1 0 L 0.26 0.26 L 0 1 L -0.26 0.26 L -1 0 L -0.26 -0.26 Z';
    const spark = new fabric.Path(path, { left, top, fill, strokeWidth: 0, scaleX: size, scaleY: size, opacity });
    canvas.add(spark);
    return spark;
  }
  function seedBoard() {
    textAt('All Hallows’ Build Night', { left: 72, top: 52, width: 900, fontSize: 46, fontFamily: FONT_DISPLAY, fontWeight: '600', fill: '#f5efe6', lineHeight: 1.05, charSpacing: -8 });
    canvas.add(new fabric.Path('M 0 0 C 74 -9 158 -9 232 -1 S 396 8 466 2', { left: 80, top: 108, stroke: hexToRgba('#ff8a3d', 0.5), strokeWidth: 9, fill: null, strokeLineCap: 'round' }));
    textAt('STITCHCRAFT · HOUSE WHITEBOARD · DEMO 01', { left: 74, top: 126, width: 720, fontSize: 12.5, fontFamily: FONT_MONO, fill: '#8d7f73', charSpacing: 160 });
    [[13, '#e7c27a', 952, 66, 1], [7, '#a78bfa', 992, 96, 0.8], [5, '#f5efe6', 916, 110, 0.45]].forEach((args) => addSpark(...args));
    const notes = [
      addSticky({ left: 72, top: 196, width: 236, fill: '#ffd9bd', title: '01 · SUMMON THE THEME', titleColor: '#2a1406', body: 'Ember, violet, one stubborn idea. Write the hero line before midnight.' }),
      addSticky({ left: 356, top: 196, width: 236, fill: '#c9b6ff', title: '02 · WRITE THE SPELL', titleColor: '#1d1233', body: 'Copy first, code second. The contract is the spell that keeps the build honest.' }),
      addSticky({ left: 640, top: 196, width: 236, fill: '#f5efe6', title: '03 · SHIP BY SUNRISE', titleColor: '#241a12', body: 'Export the board, publish the site, then off to the party. One artifact, one contract.' })
    ];
    const arrowY = notes[0].top + (notes[0].height + STICKY_PAD * 2) / 2;
    addArrow(312, arrowY, 352, arrowY);
    addArrow(596, arrowY, 636, arrowY);
    canvas.add(new fabric.Ellipse({ left: 930, top: 182, rx: 144, ry: 98, fill: hexToRgba('#8b5cf6', 0.07), stroke: '#8b5cf6', strokeWidth: 2.5, strokeDashArray: [10, 7] }));
    textAt('DRESS CODE\nResident ghost\nEmber witch\nOne (1) pumpkin', {
      left: 964, top: 214, width: 220, fontSize: 15, fontFamily: FONT_SANS, fill: '#e4d9cc', lineHeight: 1.5,
      styles: styleLine(0, 'DRESS CODE', { fontWeight: '700', fontSize: 12.5, fill: '#c9b6ff', fontFamily: FONT_SANS })
    });
    textAt('the ritual', { left: 1116, top: 150, width: 150, fontSize: 18, fontFamily: FONT_DISPLAY, fontStyle: 'italic', fill: '#c9b6ff', angle: -10, charSpacing: 40 });
    canvas.add(new fabric.Line([72, 436, 1208, 436], { stroke: 'rgba(245, 239, 230, 0.13)', strokeWidth: 1 }));
    addSticky({ left: 72, top: 464, width: 424, fill: '#1b1522', title: 'THE HOUSE RULE', titleColor: '#ffb27a', bodyColor: '#e4d9cc', body: 'Every site is one artifact with a contract. Draw the contract before you code it.' });
    addSticky({ left: 536, top: 464, width: 268, fill: '#e7c27a', title: 'TONIGHT’S CHECKLIST', titleColor: '#2b1d08', body: '01 · boilerplate\n02 · hero section\n03 · export & publish' });
    [[16, '#a78bfa', 934, 520, 0.95], [9, '#a78bfa', 978, 488, 0.65], [7, '#e7c27a', 902, 490, 0.7]].forEach((args) => addSpark(...args));
    textAt('make it weird', { left: 900, top: 544, width: 250, fontSize: 24, fontFamily: FONT_DISPLAY, fontStyle: 'italic', fill: '#c9b6ff', angle: -4 });
    textAt('STITCHCRAFT WHITEBOARD · FABRIC.JS 5.2.4 · AUTOSAVED ON THIS DEVICE', { left: 72, top: 738, width: 980, fontSize: 10.5, fontFamily: FONT_MONO, fill: '#5f554c', charSpacing: 150 });
    canvas.renderAll();
  }

  /* 11 · Export */
  function exportPng() {
    if (!canvas) { return; }
    canvas.discardActiveObject();
    canvas.renderAll();
    try {
      const link = document.createElement('a');
      link.href = canvas.toDataURL({ format: 'png', quality: 1, multiplier: 2 });
      link.download = 'stitchcraft-whiteboard.png';
      document.body.appendChild(link);
      link.click();
      link.remove();
      setSaveChip('saved', 'PNG exported');
      announce('PNG exported at double resolution · check your downloads.');
    } catch (error) { announce('Export failed in this browser · try Save instead.'); }
  }

  /* 12 · Confirmation dialog */
  function bindDialog() {
    if (!els.dialog) { return; }
    askConfirm = (options) => new Promise((resolve) => {
      if (typeof els.dialog.showModal !== 'function') { resolve(false); return; }
      dialogReturnFocus = document.activeElement;
      els.dialogEyebrow.textContent = options.eyebrow || 'Just checking';
      els.dialogTitle.textContent = options.title || 'Are you sure?';
      els.dialogMessage.textContent = options.message || '';
      els.dialogAccept.textContent = options.confirmLabel || 'Continue';
      els.dialog.returnValue = '';
      const onClose = () => {
        els.dialog.removeEventListener('close', onClose);
        if (dialogReturnFocus && typeof dialogReturnFocus.focus === 'function') { dialogReturnFocus.focus(); }
        resolve(els.dialog.returnValue === 'confirm');
      };
      els.dialog.addEventListener('close', onClose);
      els.dialog.showModal();
      if (els.dialogCancel) { els.dialogCancel.focus(); }
    });
    bind(els.dialog, 'click', (event) => { if (event.target === els.dialog) { els.dialog.close('cancel'); } });
  }

  /* 13 · Keyboard shortcuts */
  function bindShortcuts() {
    document.addEventListener('keydown', (event) => {
      if (els.dialog && els.dialog.open) { return; }
      const mod = event.ctrlKey || event.metaKey, key = (event.key || '').toLowerCase();
      if (isFormField(event.target)) {
        if (mod && key === 's') { event.preventDefault(); saveBoard(true); }
        return;
      }
      const active = canvas && canvas.getActiveObject();
      if (active && active.isEditing) { return; }
      if (mod && key === 'z') { event.preventDefault(); if (event.shiftKey) { redo(); } else { undo(); } return; }
      if (mod && key === 'y') { event.preventDefault(); redo(); return; }
      if (mod && key === 's') { event.preventDefault(); saveBoard(true); return; }
      if (mod) { return; }
      if (event.key === 'Delete' || event.key === 'Backspace') { event.preventDefault(); removeSelection(); return; }
      if (event.key === 'Escape') {
        if (state.tool !== 'select') { setTool('select'); announce('Select mode restored.'); }
        else { canvas.discardActiveObject(); canvas.requestRenderAll(); announce('Selection cleared.'); }
        return;
      }
      if (event.altKey) { return; }
      const mapped = KEY_TOOLS[key];
      if (mapped) { event.preventDefault(); setTool(mapped); const button = toolButton(mapped); if (button) { button.focus(); } }
    });
  }

  /* 14 · Toolbar wiring and boot */
  function bindToolbar() {
    els.toolButtons.forEach((button) => {
      bind(button, 'click', () => setTool(button.dataset.tool));
      bind(button, 'focus', () => syncToolRoving(button));
    });
    bind(els.toolButtons[0] && els.toolButtons[0].parentElement, 'keydown', (event) => {
      if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) { return; }
      event.preventDefault();
      const current = els.toolButtons.indexOf(document.activeElement), last = els.toolButtons.length - 1;
      let next = current;
      if (event.key === 'ArrowRight') { next = (current + 1 + els.toolButtons.length) % els.toolButtons.length; }
      if (event.key === 'ArrowLeft') { next = (current - 1 + els.toolButtons.length) % els.toolButtons.length; }
      if (event.key === 'Home') { next = 0; }
      if (event.key === 'End') { next = last; }
      els.toolButtons[next].focus();
    });
    els.swatches.forEach((button) => bind(button, 'click', () => setColor(button.dataset.color)));
    bind(els.colorInput, 'input', () => setColor(els.colorInput.value));
    bind(els.widthInput, 'input', () => setWidth(els.widthInput.value));
    bind(els.undo, 'click', undo);
    bind(els.redo, 'click', redo);
    bind(els.clear, 'click', () => askConfirm({
      eyebrow: 'Clear the board', title: 'Start from an empty canvas?',
      message: 'Every mark on this board will be cleared. Undo brings it back once, so export a PNG first if you want to keep it.',
      confirmLabel: 'Clear board'
    }).then((accepted) => { if (accepted) { clearBoard(); } }));
    bind(els.save, 'click', () => saveBoard(true));
    bind(els.load, 'click', () => loadBoard(true));
    bind(els.exportBtn, 'click', exportPng);
    bind(els.newBoard, 'click', () => askConfirm({
      eyebrow: 'New board', title: 'Begin a fresh ritual?',
      message: 'This clears the canvas and autosaves the blank board. Undo brings the old one back once — export a PNG first if it matters.',
      confirmLabel: 'New board'
    }).then((accepted) => { if (accepted) { clearBoard(); } }));
    syncToolRoving(toolButton('select'));
  }
  function boot() {
    initCanvas();
    bindToolbar();
    bindShortcuts();
    bindDialog();
    resizeCanvas();
    setTool('select', { quiet: true });
    setColor(state.color, { quiet: true });
    setWidth(state.width, { quiet: true });
    const saved = readSavedBoard();
    if (saved) {
      restoreSnapshot(JSON.stringify(saved), () => {
        state.ready = true;
        resetHistory();
        updateCounters();
        setSaveChip('saved', 'Saved on this device');
        announce('Last board restored from this device. Pick a tool and keep going.');
      });
    } else {
      seedBoard();
      state.ready = true;
      resetHistory();
      updateCounters();
      scheduleAutosave();
      announce('Sample board ready · pick a tool and draw. Everything autosaves on this device.');
    }
    if (window.ResizeObserver) { new ResizeObserver(resizeCanvas).observe(els.stage); }
    else { window.addEventListener('resize', resizeCanvas); }
  }
  function start() {
    els = {
      status: byId('status'), saveChip: byId('save-chip'), saveChipLabel: byId('save-chip-label'), stage: byId('stage'),
      canvasEl: byId('board-canvas'), empty: byId('empty-state'), markCount: byId('mark-count'), colorInput: byId('color-input'),
      widthInput: byId('stroke-width'), widthValue: byId('width-value'), undo: byId('undo'), redo: byId('redo'),
      clear: byId('clear-board'), save: byId('save-board'), load: byId('load-board'), exportBtn: byId('export-png'),
      newBoard: byId('new-board'), dialog: byId('confirm-dialog'), dialogEyebrow: byId('confirm-eyebrow'),
      dialogTitle: byId('confirm-title'), dialogMessage: byId('confirm-message'), dialogAccept: byId('confirm-accept'),
      dialogCancel: byId('confirm-cancel'), toolButtons: all('[data-tool]'), swatches: all('[data-color]')
    };
    if (!els.stage || !els.canvasEl) { return; }
    if (!window.fabric || typeof window.fabric.Canvas !== 'function') {
      setSaveChip('error', 'Fabric.js missing');
      announce('Fabric.js did not load. Check that vendor/fabric.min.js sits next to app.js.');
      return;
    }
    defineStickyClass();
    boot();
  }
  start();
})();
