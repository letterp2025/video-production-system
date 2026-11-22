# ELM-pixel-cell-grid - Pixel cell grid

- **Status:** Generic base grid implemented; style review pending
- **Kind:** Graphic primitive / cell system
- **Purpose:** Provide a reusable square-cell field that can remain empty or form different silhouettes when paired with a target mask and animation recipe.
- **Source:** 11kfire.com homepage, reviewed 2026-11-19; `src/components/FlameGrid.astro`, `src/components/CellGrid.astro`, and `src/data/flame-grid.js`.
- **Owner:** 11K FIRE. Reuse the source implementation as a design reference; no generated media copied into this entry.
- **ID:** `ELM-pixel-cell-grid` (the full folder name is the stable ID)

## Parts and reuse contract

- One 27 x 27 square-cell field (729 positions) with a pale gray palette. The base element is the empty state; a target mask marks which positions form an object.
- Adjustable: row and column count, cell size, pitch, origin, scale, field palette, target mask, active palette, and animation timing.
- Target-mask data lives with the animation recipe because it describes the object formed over time. [ANM-cell-grid-shape-reveal](../../visual_animations_library/ANM-cell-grid-shape-reveal/NOTES.md) includes the flame and heart examples.
- The static style builder groups same-color vector cells into one editable shape layer to keep the base project small. The animation builder expands cells into individual layers for independent keyframes.

## Style variants

| Style ID | Style name | Status | Notes |
|---|---|---|---|
| STY-01 | retro-11kfire | Empty-state EffectCraft build and 1080p still ready; review pending | [Style notes](styles/retro-11kfire-STY-01/STYLE.md) |

## First implementation

- Builder: [`build.jsx`](styles/retro-11kfire-STY-01/code/build.jsx), with the entry-local EffectCraft helper beside it.
- Local project: `styles/retro-11kfire-STY-01/project/pixel-cell-grid.effectcraft.ecproj` (ignored).
- Local preview: `styles/retro-11kfire-STY-01/preview/pixel-cell-grid_1080p.png` (local and ignored; not distributed).
- EffectCraft CLI 0.24.1; 1920 x 1080 still composition. The 729 pale vector cells are grouped by fill color in one shape layer. See the library README for rebuild steps.
- The website flame silhouette and cell flip/pulse choreography are recorded as the sample target and implementation in [ANM-cell-grid-shape-reveal](../../visual_animations_library/ANM-cell-grid-shape-reveal/NOTES.md).
