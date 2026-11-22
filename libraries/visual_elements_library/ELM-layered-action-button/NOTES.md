# ELM-layered-action-button - Layered action button

- **Status:** Preview ready; style review pending
- **Kind:** Composite / UI
- **Purpose:** Make one short call to action feel tactile and easy to notice in a video frame.
- **Source:** 11kfire.com homepage, reviewed 2026-11-19; `.hero-link` in `src/pages/index.astro`.
- **Owner:** 11K FIRE. No source media copied into this entry.

## Parts and reuse contract

- Solid rectangular button, short uppercase label, optional arrow, and two hard-offset shadow slabs.
- Adjustable: label, arrow, size, padding, shadow colors/offsets, and pressed state.
- For video, the hover/press state can become a brief timed nudge.

## Style variants

| Style ID | Style name | Status | Notes |
|---|---|---|---|
| STY-01 | retro-11kfire | EffectCraft build and 1080p still ready; review pending | [Style notes](styles/retro-11kfire-STY-01/STYLE.md) |

## First implementation

- Builder: [`build.jsx`](styles/retro-11kfire-STY-01/code/build.jsx), with the entry-local EffectCraft helper beside it.
- Local project: `styles/retro-11kfire-STY-01/project/layered-action-button.effectcraft.ecproj` (ignored).
- Local preview: `styles/retro-11kfire-STY-01/preview/layered-action-button_1080p.png` (local and ignored; not distributed).
- EffectCraft CLI 0.24.1; 1920 x 1080 still composition. See the library README for rebuild steps.
