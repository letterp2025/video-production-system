# ELM-chromatic-split-headline - Chromatic split headline

- **Status:** Preview ready; style review pending
- **Kind:** Typographic
- **Purpose:** Create a loud two-part title with deliberate line breaks, a red second phrase, and a small cyan print offset.
- **Source:** 11kfire.com homepage, reviewed 2026-11-19; hero `<h1>` and styles in `src/pages/index.astro`.
- **Owner:** 11K FIRE. Website font files remain in their source repository.

## Parts and reuse contract

- One or more short headline phrases; color emphasis can distinguish a phrase or line.
- Adjustable: words, line breaks, scale, weight, tracking, line height, ink/accent placement, and chromatic offset.
- Preserve readability: offset is a small edge accent, not a blur or glow.

## Style variants

| Style ID | Style name | Status | Notes |
|---|---|---|---|
| STY-01 | retro-11kfire | EffectCraft build and 1080p still ready; review pending | [Style notes](styles/retro-11kfire-STY-01/STYLE.md) |

## First implementation

- Editable builder: [`build.jsx`](styles/retro-11kfire-STY-01/code/build.jsx)
- Native project: `styles/retro-11kfire-STY-01/project/chromatic-split-headline.effectcraft.ecproj` (local, ignored)
- Preview: `styles/retro-11kfire-STY-01/preview/chromatic-split-headline_1080p.png` (local and ignored; not distributed)
- Composition: 1920 x 1080, 30 fps, 1 second; four text layers plus a white background.
- Configurable source values include the two phrases, font/style/size/tracking, colors, position, and independent cyan offsets.
- Build uses EffectCraft CLI 0.24.1 and the Big Shoulders Variable font from the read-only website repository. See the style notes for the build command and dependency path.
- This is a still element preview. It does not add animation; motion recipes are tracked separately.
