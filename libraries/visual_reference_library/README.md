# Visual reference library guide

Use a reference entry to record what a website, still image, or video shows and how a recreation was made. Recreate a style with whichever available tool fits the work; EffectCraft and Manim are common options, not requirements.

This public library contains the method and template. Add a complete reference study only after checking that its notes, source information, and every included asset are suitable for public release. Keep private studies and downloaded third-party media outside this repository.

## Ways to gather a reference

Use one method or combine them when useful. Record the method, source, date, viewport or dimensions, and evidence in the entry notes.

1. **Read a website.** Inspect the rendered page and, where useful, its public HTML, CSS, JavaScript, and linked assets. Record what came from source inspection separately from what you observed in the browser. Public browser code does not reveal private server code or the original editable project.
2. **Use a single snapshot.** Record the image source, dimensions, and crop. Analyze only what is visible. A still does not establish movement or timing; label motion ideas as recreation choices.
3. **Study a video.** Record the source URL, creator, title, and ownership or license details. Generate a widely spaced contact sheet to understand the full video, then create denser samples for important passages. Inspect selected frames at full size and record their timecodes. Keep downloads, extracted frames, contact sheets, and element sheets local and ignored by Git.

## Reverse-engineer from overview to motion

1. **Scan the full video.** Start with a small contact sheet sampled at a wide interval. Note scene changes, recurring elements, and promising time ranges.
2. **Inspect movement.** Generate a closer pass across the video, such as one frame per second for navigation and a quarter-second interval for busy motion. For a very short passage that needs frame-level detail, sample every source frame. One-second sampling can miss fast reveals.
3. **Build an element sheet.** Select representative frames and label the visual parts that carry the look: type, cards, icons, shapes, backgrounds, or recurring characters. Cite source timecodes. An element sheet is analysis, not automatic approval of every item for the reusable library.
4. **Recreate selected elements.** Draw manageable geometry with native shapes. Image-generation can provide a rough visual starter. Raster tracing can help with contours. These are aids; compare and clean the editable result. Do not claim the recreation reveals the original vector points or source keyframes.
5. **Map selected motion.** Keep observations separate from estimates and design choices. A small `motion-map.json` can record source dimensions, time-stamped bounds, position, scale, rotation, opacity, layer order, holds, reveals, estimated easing, confidence, and evidence frames. Use normalized coordinates when practical. Mark unknowns explicitly.
6. **Compare and record.** Recreate a short passage in the selected tool, compare matching timecodes, and document what matches, differs, or remains unmapped. The native project or source code is the recreation source of truth; the motion map is an analysis aid unless a later workflow deliberately makes it executable.

The goal is to identify reusable components and their movement, not to reproduce every pixel or infer undocumented original keyframes.

## Entry structure

Choose a concise descriptive slug, check the public and private reference libraries for a collision, and use `REF-<slug>` as both the folder name and stable ID. Copy [`NOTES_TEMPLATE.md`](NOTES_TEMPLATE.md) to the entry as `NOTES.md`.

```text
REF-short-name/
  NOTES.md
  reference/
    captures/          # local and ignored
    source/            # local original snapshot/video; ignored
    frames/            # local and ignored
    contact_sheets/    # local and ignored
    element-sheets/    # local and ignored
    analysis/
      motion-map.json  # text analysis may be tracked after privacy review
  code/                # authored recreation source
  project/             # local native project; ignored
  assets/              # local working assets; ignored
  render/
    HIGH/
    LOW/
```

For a public entry, include the public source link, attribution, relevant reuse/license terms, tool and version, and a clear boundary between observed facts and inferred choices. Do not commit downloaded source media, screenshots, rendered images or video, fonts, or native project binaries. A reference link alone does not grant permission to redistribute its media or derived assets.

## Index

There are no cleared reference entries in this public repository yet. Internal studies are kept in the separate private workspace until their sources and public-safe content are reviewed.
