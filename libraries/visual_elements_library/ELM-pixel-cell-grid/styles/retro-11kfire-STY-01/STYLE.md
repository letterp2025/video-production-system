# retro-11kfire - STY-01

- Use a square 27 x 27 grid: 729 pale cells in the empty base state. Target masks can light selected cells to form an object.
- Reference geometry: 500 x 500 viewBox; 13-unit square cells on an 18-unit pitch; 7-unit outer origin.
- Field palette: `#f0f1f2`, `#e3e5e7`, `#d5d8db`, and `#c7cbcf`. The flame example uses red `#e13a2e`, coral `#f36a5c`, dark red `#aa2119`, and sparse cyan `#29aacf`.
- Keep cells crisp and square. Target masks define the silhouette; do not smooth the cell edges.
- Source grid and flame target: `src/data/flame-grid.js`; rendering: `CellGrid.astro`; the website also documents this in `doc/FEATURE_GRID_AESTHETIC.md`.

## EffectCraft first pass

- Builder: [`code/build.jsx`](code/build.jsx); the empty 27 x 27 field is grouped into one editable shape layer, with paths grouped by fill color.
- The composition contains 729 pale field cells. The grid is scaled from the website's 500-unit coordinate system.
- Local project and preview are recorded in the [element notes](../../NOTES.md). The project is about 6.7 MB and remains local/ignored.
- Rendered at 1920 x 1080 as a still with EffectCraft CLI 0.24.1. Rebuild using the [library instructions](../../../README.md#rebuild-a-still-preview).
- The static element does not include an object mask or motion. The website's flame map and cell reveal/pulse recipe are separate in [ANM-cell-grid-shape-reveal](../../../../visual_animations_library/ANM-cell-grid-shape-reveal/NOTES.md); the flame version has been rendered and reviewed.
