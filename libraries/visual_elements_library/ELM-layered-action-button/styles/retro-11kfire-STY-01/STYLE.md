# retro-11kfire - STY-01

- Fill with signal red `#e13a2e`; set the label in white, uppercase, narrow heavy type (Anton in the website).
- Use crisp offset rectangles: near-black at about 5 px and cyan `#29aacf` at about 9 px, both down and right.
- Keep the label short, add a simple diagonal arrow on the right, and use square corners.
- Optional press motion: shift the button 3 px down/right while reducing both shadow offsets by 3 px.
- Website reference copy: `SEE IT UNFOLD`; source selector: `.hero-link` in `src/pages/index.astro`.

## EffectCraft first pass

- Builder: [`code/build.jsx`](code/build.jsx); editable red face, Anton label, vector arrow, black offset, and cyan offset.
- Local project and preview are recorded in the [element notes](../../NOTES.md).
- Rendered at 1920 x 1080 as a still with EffectCraft CLI 0.24.1. Rebuild using the [library instructions](../../../README.md#rebuild-a-still-preview).
- The optional pressed-state nudge is not animated in this still.
