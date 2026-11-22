# ELM-dotted-print-field - Dotted print field

- **Status:** Preview ready; style review pending
- **Kind:** Primitive / texture
- **Purpose:** Add a faint offset halftone-like bed behind a larger graphic without competing with it.
- **Source:** 11kfire.com homepage, reviewed 2026-11-19; `.hero-art::before` in `src/pages/index.astro`.
- **Owner:** 11K FIRE. No source media copied into this entry.

## Parts and reuse contract

- Repeating dot pattern behind a foreground element.
- Adjustable: dot size, spacing, color, opacity, bounds, and offset direction.
- Keep the field low contrast and partially tucked behind the main artwork.

## Style variants

| Style ID | Style name | Status | Notes |
|---|---|---|---|
| STY-01 | retro-11kfire | EffectCraft build and 1080p still ready; review pending | [Style notes](styles/retro-11kfire-STY-01/STYLE.md) |

## First implementation

- Builder: [`build.jsx`](styles/retro-11kfire-STY-01/code/build.jsx), with the entry-local EffectCraft helper beside it.
- Local project: `styles/retro-11kfire-STY-01/project/dotted-print-field.effectcraft.ecproj` (ignored; approximately 1.9 MB).
- Local preview: `styles/retro-11kfire-STY-01/preview/dotted-print-field_1080p.png` (local and ignored; not distributed).
- EffectCraft CLI 0.24.1; 1920 x 1080 still composition. The 540 ellipses remain vector paths in one shape layer. See the library README for rebuild steps.
