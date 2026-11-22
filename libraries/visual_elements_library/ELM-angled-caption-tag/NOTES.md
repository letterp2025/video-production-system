# ELM-angled-caption-tag - Angled caption tag

- **Status:** Preview ready; style review pending
- **Kind:** Composite / typographic
- **Purpose:** Attach a short editorial caption to a larger graphic, like a printed annotation.
- **Source:** 11kfire.com homepage, reviewed 2026-11-19; `.art-caption` in `src/pages/index.astro`.
- **Owner:** 11K FIRE. No source media copied into this entry.

## Parts and reuse contract

- Short uppercase caption set inside a solid rectangular color block.
- Adjustable: wording, position, rotation, padding, type size, and background/foreground colors.
- Keep the tilt subtle and the text compact enough to remain legible.

## Style variants

| Style ID | Style name | Status | Notes |
|---|---|---|---|
| STY-01 | retro-11kfire | EffectCraft build and 1080p still ready; review pending | [Style notes](styles/retro-11kfire-STY-01/STYLE.md) |

## First implementation

- Builder: [`build.jsx`](styles/retro-11kfire-STY-01/code/build.jsx), with the entry-local EffectCraft helper beside it.
- Local project: `styles/retro-11kfire-STY-01/project/angled-caption-tag.effectcraft.ecproj` (ignored).
- Local preview: `styles/retro-11kfire-STY-01/preview/angled-caption-tag_1080p.png` (local and ignored; not distributed).
- EffectCraft CLI 0.24.1; 1920 x 1080 still composition. See the library README for rebuild steps.
