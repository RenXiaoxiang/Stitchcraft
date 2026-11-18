---
name: stitchcraft-whiteboard
description: Add an offline Fabric.js whiteboard or annotation board to a generated site, with drawing tools, autosave and PNG export.
---

# Stitchcraft Whiteboard

## Job

Replace a static "collaboration" section with a working canvas board: a visitor
can sketch, drop sticky notes, annotate a plan or mark up a diagram and export
the result as a PNG. Everything runs offline from the bundled Fabric.js build.

## When to use

- The brief mentions a whiteboard, sketch pad, brainstorm board, annotation
  canvas, planning board or "draw it yourself" experience.
- A personal-space or brand-launch site wants a playful, hands-on section; a
  data site wants a note/annotation layer next to its tables.

## Layout blueprint

1. Section header explains the board in one sentence.
2. Toolbar: select, pen, highlighter, rectangle, ellipse, arrow, text, eraser,
   colour swatches, stroke width, undo/redo, clear, export PNG.
3. Canvas stage with a subtle grid, keyboard-accessible toolbar buttons
   (`aria-pressed`, labels) and a live status region.
4. Footer hint with shortcuts and "autosaves on this device".

## Library contract

- Load `<script src="vendor/fabric/fabric.min.js"></script>` **before** the
  inline site script. The generator copies the pinned Fabric.js 5.2.4 build and
  its LICENSE into `vendor/fabric/` when a generated file references that path.
- Initialise `const canvas = new fabric.Canvas('board-canvas', {...})`, then set
  a viewport transform so the logical board fits the stage on resize.
- Never load Fabric.js from a CDN or any external URL.

## Persistence

- Serialise with `canvas.toJSON()` into `localStorage` under
  `stitchcraft:whiteboard` (debounced), and restore on load with
  `canvas.loadFromJSON`.
- If `window.STITCHCRAFT_DB.mode === "remote"`, optionally mirror the board JSON
  to the configured REST table after the local write; a failed remote write must
  not lose the local board.
- Export PNG with `canvas.toDataURL({ format: "png" })` and a download anchor.

## Motion and quality bar

- Motion: toolbar/state transitions only; honour `prefers-reduced-motion`.
- The board is keyboard-operable for tools and dialogs; `Esc` leaves drawing
  mode, `Delete` removes the selection.
- No external fonts, images or scripts; the page works from `file://`.
- Undo/redo covers at least 30 steps; Clear asks for confirmation in a dialog
  (never `window.confirm`).
- Empty state explains how to start drawing.

## Output contract

Return `{"files":[{"path":"index.html","content":"..."},...],"summary":"..."}}`;
reference the bundled library at `vendor/fabric/fabric.min.js` and keep the
board's JavaScript in `app.js` (or inline in compact single-file mode).
