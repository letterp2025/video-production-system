# retro-11kfire - STY-01

- Repeat small signal-red dots (`#e13a2e`) on an approximately 11 px grid.
- Use low opacity (about 0.22) and a 1.25 px dot radius so the pattern reads as printed texture, not foreground content.
- Place it behind the art, inset slightly from its bounds, then offset it about 15 px right and down.
- Website source: `.hero-art::before` in `src/pages/index.astro`.

## EffectCraft first pass

- Builder: [`code/build.jsx`](code/build.jsx); 540 editable ellipse paths are grouped into one shape layer at 22% opacity.
- Local project and preview are recorded in the [element notes](../../NOTES.md). The project is about 1.9 MB and remains local/ignored.
- Rendered at 1920 x 1080 as a still with EffectCraft CLI 0.24.1. Rebuild using the [library instructions](../../../README.md#rebuild-a-still-preview).
