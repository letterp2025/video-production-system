# ANM-cell-grid-shape-reveal — Cell-Grid Shape Reveal and Field Pulse

- **Status:** Flame video rendered and reviewed; alternate heart target rendered as a still
- **Pattern:** Procedural cell-grid reveal with ambient field pulse
- **Target element:** [ELM-pixel-cell-grid / STY-01](../../visual_elements_library/ELM-pixel-cell-grid/NOTES.md)
- **Source scene or reference:** 11K FIRE website implementation: `src/data/flame-grid.js`, `src/components/CellGrid.astro`, and `doc/FEATURE_GRID_AESTHETIC.md`
- **Tool and version:** EffectCraft CLI 0.24.1 with the sectioned FFmpeg tool

## Recipe

- **Intent:** Let a shape assemble from the cells of a quiet grid.
- **Target data:** A 27 x 27 text mask. `#` marks a cell in the object; `.` leaves it in the field. The included flame has 176 active cells; the heart has 274.
- **Animated properties:** Active cells rotate around X and switch from field gray to the configured active palette at the midpoint. Unselected cells vary opacity from 0.62 to 1.0.
- **Time base:** EffectCraft keyframes use composition time. The website source uses milliseconds from page load; the builder converts timing to 60 fps frames.
- **Duration and hold:** The active sweep spans about 260 ms, with up to 19 ms of deterministic per-cell jitter. Each flip lasts 60–84 ms. The completed object holds. Field pulses use 5.2–9.999 second periods.
- **Order:** Active cells use a diagonal `column - row` sweep. The field cells pulse independently through the reveal and hold.
- **Interpolation:** Active-cell rotation is linear. The fill changes as a hold keyframe at the midpoint. Field opacity uses sampled linear keys approximating an ease-in-out pulse.

| Time | Target | Property | Value |
|---:|---|---|---|
| 0–about 280 ms, staggered | Each active cell | Start time | Normalize diagonal position to 0–260 ms, then add deterministic 0–19 ms jitter |
| Cell-local 0% | Active cell | X rotation, fill | 0 degrees, field gray |
| Cell-local 50% | Active cell | X rotation, fill | 90 degrees; switch fill to active color |
| Cell-local 100% | Active cell | X rotation, fill | 0 degrees, active color |
| Repeating 5.2–9.999 s per field cell | Field cell | Opacity | 0.62 ↔ 1.0 |

The website flips each active cell once and leaves it at its final color. Its background cells begin at distributed pulse offsets. The EffectCraft build uses one separate shape layer per cell. Field opacity is sampled every 0.5 seconds in the four-second preview, so this is a practical recreation rather than a frame-exact copy of the website's CSS easing.

## Change the formed shape

Edit `targetMask` near the top of `code/build.jsx`:

```js
targetMask: "flame",
```

Change it to `heart` to use the included heart, or add another named 27-row, 27-character map in [`code/target_masks.jsx`](code/target_masks.jsx). The [target guide](code/README.md) defines the format. The active palette, grid geometry, reveal timing, and field pulse settings remain in the builder.

This recipe reveals one target from the empty grid. Switching between two completed shapes would need a separate transition recipe; the current effect changes grid occupancy and does not morph vector paths.

## Reuse contract

- **Parameters:** Target mask; grid rows and columns; cell size, pitch, origin, and scale; field and active palettes; sweep duration and jitter; flip duration; field opacity and pulse period.
- **Constraints:** Keep square, crisp-edged cells. Keep the field pulse subtle enough to preserve focus on the shape.
- **Implementation:** [`code/build.jsx`](code/build.jsx) creates the per-cell layers and keyframes. [`code/target_masks.jsx`](code/target_masks.jsx) stores target maps. [`code/sections_1080p60.json`](code/sections_1080p60.json) splits the flame render into four contiguous one-second sections.
- **Native project:** `project/pixel-flame-grid_reveal.effectcraft.ecproj` (local and ignored; 35,368,752 bytes).
- **Contact sheet:** `preview/pixel-flame-grid_reveal_contact.png` (local and ignored; not distributed).
- **Rendered preview:** `render/LOW/pixel-grid_flame-reveal_low.mp4` (local and ignored; 1920 x 1080, 60 fps, 4 seconds, 240 frames, HEVC `yuv420p`, 817,725 bytes).
- **Render cost:** From the run record timestamps, the whole run took about 42.15 seconds. EffectCraft rendered the four flame sections in about 27.6 seconds total; FFmpeg encoded them in about 6.5 seconds, then joined them in 0.1 seconds. The render tool reported a 4,784,302-byte peak work folder and 3,954,334-byte peak PNG storage.

## Rebuild

Set `EFFECTCRAFT_CLI` to the EffectCraft CLI executable, then run from the public repository root with EffectCraft CLI 0.24.1:

```powershell
$entry = Join-Path (Get-Location).Path 'libraries\visual_animations_library\ANM-cell-grid-shape-reveal'
$project = "$entry\project\pixel-flame-grid_reveal.effectcraft.ecproj"
New-Item -ItemType Directory -Force -Path "$entry\project", "$entry\render\LOW" | Out-Null
& $env:EFFECTCRAFT_CLI script `
  "$entry\code\build.jsx" --empty --save-as $project --json
```

Render the LOW preview with the public [EffectCraft Section Renderer](../../../tools/effectcraft_ffmpeg_sections/README.md), using the saved project, composition `11K FIRE Cell-Grid Shape Reveal`, and `code/sections_1080p60.json` at 1920 x 1080, 60 fps.

## Review and limits

- **What works:** The flame begins as the empty gray grid, assembles from lower cells upward, changes color as cells turn edge-on, and holds complete. Field cells pulse independently. The creator reviewed the result and said it looked identical and even more perfect.
- **Alternate target:** The heart map was rendered as a complete still at 0.5 seconds. It uses the same builder and forms a different object from the same grid. A full heart video has not been rendered.
- **Known limits:** The measured video is one 1080p60, four-second flame preview with no audio. 4K and other encoders have not been tested. The native project is larger than the static grid because its 729 cells are separate layers. Field opacity keys approximate the website pulse at 0.5-second intervals.
- **Alternate still:** `preview/pixel-grid_heart_complete.png` (local and ignored; complete heart at 0.5 seconds).
- **Contact-sheet review:** `preview/pixel-flame-grid_reveal_contact.png` (local and ignored) samples the empty field, early assembly, completed flame, and hold. It is a quick check of silhouette growth and reveal order; use video playback to judge timing and motion.
- **Reuse check:** Flame preview rendered and reviewed; heart target rendered as a still. The mask format is ready for more silhouettes.
- **Persistent run record:** `render/LOW/performance/pixel-grid_flame-reveal_low_faf0a9b9a330.performance.json` is a visible local copy of the section tool's run state. Generated performance records are ignored by Git.
