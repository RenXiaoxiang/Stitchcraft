# Whiteboard studio — offline Fabric.js demo

A complete, offline whiteboard built with [Fabric.js](https://github.com/fabricjs/fabric.js)
5.2.4 (MIT). It is part of Stitchcraft's aggregated tool packs: the same library
is vendored under `vendor/fabric/` and can be included in generated sites via
the `stitchcraft-whiteboard` house skill and the Fabric.js theme library.

## Features

- Select/move, pen, highlighter, rectangle, ellipse, arrow, text, eraser.
- Colour palette, stroke width, undo/redo, clear, save/load, export PNG.
- Autosaves the board to `localStorage` (`stitchcraft:whiteboard`).
- Keyboard: `V` select, `P` pen, `T` text, `Esc` select mode, `Delete` remove,
  `Ctrl/Cmd+Z` undo, `Ctrl/Cmd+Shift+Z` redo, `Ctrl/Cmd+S` save.
- Accessible toolbar, focus rings, live status region, reduced-motion aware.
- No external fonts, images, CDNs or build step: open `index.html` from disk.

## Run it

Open `index.html` directly, or serve the folder:

```bash
python -m http.server 8799 --directory docs/demo/whiteboard
# then open http://127.0.0.1:8799/
```

The demo is embedded in the GitHub Pages showcase at
`docs/demo/whiteboard/index.html`.

## Layout

| File | Purpose |
| --- | --- |
| `index.html` | Toolbar, stage, dialogs, accessible markup. |
| `styles.css` | Kiroween dark studio styling + responsive layout. |
| `app.js` | Fabric.js canvas, tools, history, persistence, PNG export. |
| `vendor/fabric.min.js` | Pinned Fabric.js 5.2.4 UMD build (unmodified). |
| `vendor/fabric.LICENSE.txt` | Upstream MIT license for the redistributed build. |
