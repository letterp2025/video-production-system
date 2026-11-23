# Task Order: Segment Layers and Workbench Layout

**Task ID:** SLW-001 | **Status:** Planned | **Last updated:** 2026-11-23

## Objective

Treat each stable narration segment as a four-layer production unit: (1) script text and narration audio, (2) visual, (3) music, and (4) sound effects (SFX). Give the workbench room to manage all four without packing more controls into its top bar. The four-tab navigation is already shipped by the [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md). This task covers project-local visual takes spanning the whole narration spine and future music/SFX JSON mappings.

## Current state and boundaries

- The narration manifest owns segment ID, spoken order, approved text, status, voice settings, and take selection. The workbench already edits and previews these.
- The current workbench creates optional per-segment planning JSON at `audio/visuals/<segment-id>.json`. It records intent or a library recipe; it does not define or render an animation. The target is a project-root `visual_layer/` folder containing multiple manifest JSON files. Each manifest is one alternative visual take for the entire narration spine.
- A take such as `v_layer_1.json` can try a retro direction across the video; `v_layer_2.json` can try another direction and treat an individual segment differently. Selecting a take selects its mapping for the whole spine. Both manifests remain available, and changing one take does not silently change the other.
- Every take manifest combines planning with implementation references: an overall creative direction, segment-specific intent, and project-relative paths to folders/files defining elements and animations. Segment mappings use the exact stable IDs from `audio/narration_manifest.json`. Each segment may use EffectCraft, Manim, or GSAP within that take.
- Most elements and animations will be created for the video project. Reusable library recipes or elements are optional references, never prerequisites. There is no separate plan JSON required before adding an implementation to a take manifest.
- Music and SFX have no per-segment mapping, editor, or playback integration yet. The [Asset Finder](../../tools/asset_finder/README.md) can search and download audio with a source/license receipt, but it is not integrated into the workbench and does not make a licensing decision.
- The current top bar contains project identification and narration playback controls. Per-beat visual controls now live under **Visual Layer**; do not add music or SFX controls to the global top bar.

## User workflow

1. Open the video project and select a visual take manifest in **Visual Layer**, or create a new one for a different whole-spine treatment. The take chooser shows the take name and creative direction; selecting another manifest switches the full-spine visual mapping.
2. Select a beat in the left-hand sequence. Its stable ID, not its position, locates that beat inside the chosen take and the other layers. Reordering beats preserves the mappings.
3. In the chosen manifest, describe the beat's visual intent and point it to project-specific element/animation files. Choose EffectCraft, Manim, or GSAP for that beat. A take can change one segment substantially while keeping a coherent direction for the rest of the spine. Add a library reference only when reusing an existing asset or recipe.
4. Edit approved words and narration audio in the existing script/audio workflow. A visual take uses the same narration spine; editing narration does not silently copy or rewrite the take's implementation files.
5. Open **Music** or **SFX** for the selected beat. Create that layer's JSON only when needed, then map one or more project-local audio assets to cues. Empty/missing mappings are normal and visible.
6. Review the source and license of any candidate asset separately. The initial mapping workflow accepts paths to already-reviewed project assets; finding and downloading them can continue through Asset Finder outside the workbench.
7. Switch beats or visual takes and see the corresponding status and mapping. If approved text changes, keep existing mappings and flag text-dependent visual intent or audio cues for review rather than silently retiming or deleting them.

## Data ownership and proposed storage

| Layer | Source of truth | Initial scope |
|---|---|---|
| Script text + narration audio | Project `audio/narration_manifest.json` and its selected take files | Existing behavior; no duplicate script/audio JSON |
| Visual | Multiple project `visual_layer/<take-id>.json` manifests, `visual_layer/selected_take.json`, and the project files they reference | Each manifest is one selectable whole-spine take, with creative direction and a stable-ID segment map pointing to its element/animation implementation; selection state identifies the current take |
| Music | Project `audio/music/<segment-id>.json` | New optional cue mapping |
| SFX | Project `audio/sfx/<segment-id>.json` | New optional cue mapping |

### Example video-project folder tree

The example video project is `effectcraft-introduction-01`. The tree starts at that project root, regardless of its private machine-specific parent path. The visual manifests sit directly inside `visual_layer/`, beside their corresponding implementation folders. The two shown segment folders illustrate the pattern; a real take covers the full narration spine.

```text
effectcraft-introduction-01/
├── audio/
│   └── narration_manifest.json
└── visual_layer/
    ├── selected_take.json             # points to the chosen take manifest
    ├── v_layer_1.json                 # whole-spine retro take: direction + segment mappings
    ├── v_layer_2.json                 # whole-spine alternate take
    ├── v_layer_1/
    │   ├── found-effectcraft/
    │   │   ├── scene.js               # example GSAP entry file
    │   │   ├── elements/
    │   │   │   └── title_card.js
    │   │   └── animations/
    │   │       └── title_reveal.js
    │   └── free-motion-graphics/
    │       ├── scene.py               # example Manim entry file
    │       ├── elements/
    │       │   └── diagram.py
    │       └── animations/
    │           └── diagram_reveal.py
    └── v_layer_2/
        ├── found-effectcraft/
        │   ├── scene.js               # different implementation of this segment
        │   ├── elements/
        │   │   └── title_card.js
        │   └── animations/
        │       └── title_reveal.js
        └── free-motion-graphics/
            ├── scene.py
            ├── elements/
            │   └── diagram.py
            └── animations/
                └── diagram_reveal.py
```

The filenames and engine choices above are illustrative. `selected_take.json` stores the selected manifest filename (for example, `v_layer_1.json`); it is selection state, not another visual take. A segment may instead use EffectCraft-supported project data. Element and animation modules may be organized within each segment folder as needed. A take may explicitly reuse project files from another take or a library entry, but newly created takes should have independent editable files by default so experiments do not alter each other.

### Visual take manifest contract

Each `visual_layer/<take-id>.json` is both the creative plan and the map to implementation for one whole-spine take. It contains a schema version, stable take ID, display title, overall creative direction, and a `segments` object keyed by the exact stable IDs from `audio/narration_manifest.json`. Each segment entry records that take's visual intent, source-text hash when relevant, chosen renderer (`effectcraft`, `manim`, or `gsap`), and project-relative path to the folder and entry file defining its elements and animation. Planning text lives in this manifest; there is no required separate per-segment plan JSON or recipe selection. A draft take may mark a segment pending, while complete-take status requires accounting for every active narration segment.

For illustration, `visual_layer/v_layer_1.json` could contain:

```json
{
  "schema_version": 1,
  "take_id": "v_layer_1",
  "title": "Retro take",
  "creative_direction": "Retro typography and bold color across the narration spine.",
  "segments": {
    "found-effectcraft": {
      "visual_intent": "Reveal the product name like a vintage title card.",
      "source_text_sha256": "<hash of approved spoken words>",
      "renderer": "gsap",
      "implementation": {
        "folder": "visual_layer/v_layer_1/found-effectcraft",
        "entry_file": "visual_layer/v_layer_1/found-effectcraft/scene.js"
      }
    },
    "free-motion-graphics": {
      "visual_intent": "Continue the retro treatment with animated diagrams.",
      "renderer": "manim",
      "implementation": {
        "folder": "visual_layer/v_layer_1/free-motion-graphics",
        "entry_file": "visual_layer/v_layer_1/free-motion-graphics/scene.py"
      }
    }
  }
}
```

The JSON shows two entries for brevity. `v_layer_2.json` has its own title, direction, and complete `segments` map; it can point `found-effectcraft` to `visual_layer/v_layer_2/found-effectcraft/scene.js` for a different take on that segment. Selecting `v_layer_2.json` switches the video-wide visual take. The workbench stores that choice in `visual_layer/selected_take.json` and shows the chosen take alongside the selected beat; later preview/render commands must identify which manifest they consume. Renderer entry-file conventions are finalized before implementation.

All paths inside a manifest are relative to the video project and must remain inside it. Keep renderer code/data in project files rather than embedding whole programs in JSON. Do not copy external tool installations or absolute machine paths into the project. Narration text remains owned by the Script and Narration Layer; a visual take can describe a different visual treatment of a segment without silently changing its spoken words.

Music and SFX files should be small, versioned, and independently editable. Each records the segment ID, approved-text hash captured at creation or last explicit review, and a list of cues. A cue maps a **project-relative asset path** to a start offset in the segment, with optional trim, duration, and gain fields only when their timing semantics are defined and validated. Permit multiple cues and an empty list. For Asset Finder downloads, retain source/attribution/license metadata in the neighboring `.asset.json` receipt; manually sourced assets need equivalent provenance. The mapping may reference that record but must not pretend it proves usage rights. Never put machine-specific absolute paths or media files in this public repository. The schema and folder names above are the proposed first-version contract, to be finalized before implementation.

The current per-segment visual plans are an implemented predecessor, documented in [Visual Animation Plans Per Segment](TASK-ORDER_VISUAL_ANIMATION_PER_SEGMENT.md). Migration or compatibility handling must preserve those files and their metadata. If a creator imports an old plan into a chosen take, copy its intent, recipe reference, and source-text hash into that take's corresponding segment entry without deleting or overwriting the old JSON. Import must be explicit or idempotent and must never assign an old plan to every take silently. The take manifests become the canonical visual source for this workflow.

The initial workbench needs a create/select/open/status workflow for visual take manifests and a create/open/status workflow for music/SFX JSON mappings. It should not claim that descriptive text in a manifest has already been rendered. Music/SFX mapping must not automatically mix into the narration review track, trigger asset search/download, or claim a final video mix exists. Later audio composition must define timing, overlap, fades, loudness, and how cue positions respond to narration-length changes before rendering is added.

## Workbench layout requirements

- Keep the top bar for global context and narration transport. The visual controls already live in **Visual Layer**; evolve them to choose among take manifests in project `visual_layer/` while excluding `selected_take.json` from the chooser. Do not restore per-beat controls to the header.
- Add a clearly labeled layer workspace for the selected beat. The top-level tabs and their nesting are specified in the [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md). Preserve the always-visible beat list and a readable script editor at desktop sizes.
- Show the chosen visual take and selected beat ID/title together. For that take's segment entry and each other layer, show state such as missing, saved, needs review, or invalid. A create action must identify whether it creates a whole-spine visual take or a selected-beat music/SFX mapping.
- On narrower windows, collapse or stack secondary panels instead of shrinking the editor or forcing the top bar into a single crowded line. Keyboard navigation, focus visibility, labels, and status announcements must remain usable.
- Avoid a wholesale redesign of the existing visual style. Validate the layout at the screenshot-sized desktop viewport and at narrower widths, with long project names and long beat titles.

## Implementation phases

1. **Contracts:** define the `visual_layer/<take-id>.json` and `visual_layer/selected_take.json` schemas, take naming/discovery, full-spine segment coverage and draft states, creative-direction fields, renderer enum, project-file and optional library references, safe project-relative paths, and non-destructive import of existing visual plans into a chosen take. Finalize music/SFX version-1 schemas, cue timing units, stale-text policy, file-size limits, and explicit non-overwrite behavior.
2. **Project APIs:** add safe, project-confined create/list/select/read/write/open/status operations for multiple visual take manifests, including take/segment ID validation, collision handling, and protection against one take silently overwriting another. Define copying or starting a new take so editable project files are independent unless sharing is explicit. Add equivalent create/read/open/status operations for music and SFX with atomic creation and current-manifest hash checks. Separate layer behavior into appropriately sized modules rather than growing the workbench entry point.
3. **Workbench integration:** connect **Visual Layer** to the take chooser and the selected take's segment map. Show whole-spine creative direction, selected beat intent, renderer, implementation folder/entry file, and pending or stale state. Allow a new take with project-specific elements/animations and per-segment EffectCraft, Manim, or GSAP choices; keep library references optional. Add music/SFX create/open/status views. Keep playback, narration editing, Scratchpad, and F5-TTS functional. Handle missing, invalid, and stale layer data visibly.
4. **Tests and docs:** cover switching takes and beats, reordering and adding narration segments, renderer changes, take isolation/shared references, importing old plans without data loss, invalid IDs, path traversal/symlinks, malformed or oversized JSON, concurrent edits, accessibility, and responsive layout. Update user documentation with the actual schemas and workflow.
5. **Later composition:** only after cue semantics and a renderer/mixer are specified, consider synchronized preview and final audio/video assembly. Do not fold this into the initial mapping task.

## Acceptance checks

- One beat can have any combination of the four layers; missing optional layer entries/files are not an error. Every visible layer action targets the selected beat.
- The video project contains `visual_layer/` with multiple manifest JSON files, such as `v_layer_1.json` and `v_layer_2.json`, a `selected_take.json` pointer, and separate folders for project-specific element/animation work. Each manifest combines whole-spine direction with per-segment implementation references.
- Selecting a manifest selects a complete visual take across the narration spine. Take selection persists, switching takes preserves both manifests and their files, and changing one segment in `v_layer_2` does not silently change `v_layer_1`.
- Each take maps the exact stable segment IDs in `audio/narration_manifest.json`. Reordering beats preserves associations; newly added beats appear as pending in existing takes until addressed. A complete take accounts for every active narration segment.
- Each segment entry may choose EffectCraft, Manim, or GSAP and reference its project-specific folder/entry file. Library references are optional. Creative direction and per-segment intent live in the same manifest as implementation references; no separate plan JSON or recipe selection is required.
- Existing `audio/visuals/<segment-id>.json` plans are preserved and safely imported or supported during migration; migration does not silently overwrite or delete the originals.
- Music and SFX JSON files validate against their own versioned schemas, contain only project-relative asset references, and neither overwrite existing files nor change narration/visual data.
- Reordering beats preserves all layer mappings by stable ID. Editing spoken text leaves take mappings intact and gives a clear review signal for visual intent or cues that track the source-text hash.
- Existing script editing, SAPI/F5-TTS playback, visual-plan creation/opening, Scratchpad, and take review remain usable after the layout change.
- The desktop top bar has no per-beat layer creation controls; the selected-beat workspace remains usable at narrow widths with keyboard and screen-reader labels.
- Tests establish that simply selecting or editing a visual take does not execute renderer code, and that no music/SFX mapping action downloads media, runs Asset Finder, mixes audio, or renders video.

## Related documents

- [Visual animation per-segment task order](TASK-ORDER_VISUAL_ANIMATION_PER_SEGMENT.md)
- [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md)
- [Narration workbench guide](../../tools/audio_narration_generator/README.md#segment-layers)
- [Asset Finder](../../tools/asset_finder/README.md)
