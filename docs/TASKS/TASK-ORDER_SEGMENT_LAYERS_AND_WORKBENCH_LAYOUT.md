# Task Order: Segment Layers and Workbench Layout

**Task ID:** SLW-001 | **Status:** Implemented (JSON mapping workflow) | **Last updated:** 2026-11-23

## Implementation record

- Added project-root `visual_layer/<take-id>.json` whole-spine visual take manifests and `visual_layer/selected_take.json` selection state. Creating a take scaffolds an entry keyed by every current stable narration segment ID, selects it, and leaves each entry pending for custom project work.
- The Visual Layer lists/selects takes, shows whole-video direction and selected-beat intent/renderer/implementation status, and opens the manifest in the operating system's default editor. New take IDs cannot overwrite existing files. Renderer references are never executed.
- Added optional per-beat `audio/music/<segment-id>.json` and `audio/sfx/<segment-id>.json` create/open/status workflows. Files are versioned, atomic, non-overwriting mappings; changing approved spoken text marks hash-linked visual/audio entries as needing review.
- Added strict schemas and project-confined path validation, plus regression coverage for stable IDs, take isolation, stale text, malformed/unsafe mappings, and local API routes.
- Preserved the earlier `audio/visuals/<segment-id>.json` recipe-plan flow under a clearly named legacy section; existing files are not moved, deleted, or silently imported.
- Audio cue mapping is storage only. Asset search/download, preview, mixing, and video rendering remain out of scope; use Asset Finder separately when sourcing is needed.

## Objective

Treat each stable narration segment as a four-layer production unit: (1) script text and narration audio, (2) visual, (3) music, and (4) sound effects (SFX). Give the workbench room to manage all four without packing more controls into its top bar. The four-tab navigation is already shipped by the [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md). This task delivers project-local visual takes spanning the whole narration spine and optional music/SFX JSON mappings; synchronized rendering/composition is deferred.

## Current state and boundaries

- The narration manifest owns segment ID, spoken order, approved text, status, voice settings, and take selection. The workbench already edits and previews these.
- The canonical visual source is a project-root `visual_layer/` folder containing multiple manifest JSON files. Each manifest is one alternative visual take for the entire narration spine. The older optional `audio/visuals/<segment-id>.json` plan is retained as a compatibility workflow only.
- A take such as `v_layer_1.json` can try a retro direction across the video; `v_layer_2.json` can try another direction and treat an individual segment differently. Selecting a take selects its mapping for the whole spine. Both manifests remain available, and changing one take does not silently change the other.
- Every take manifest combines planning with implementation references: an overall creative direction, segment-specific intent, and project-relative paths to folders/files defining elements and animations. Segment mappings use the exact stable IDs from `audio/narration_manifest.json`. Each segment may use EffectCraft, Manim, or GSAP within that take.
- Most elements and animations will be created for the video project. Reusable library recipes or elements are optional references, never prerequisites. There is no separate plan JSON required before adding an implementation to a take manifest.
- Music and SFX now have per-segment JSON create/open/status workflows, but no in-app cue editor, playback, or mix integration. The [Asset Finder](../../tools/asset_finder/README.md) can search and download audio with a source/license receipt, but it is not integrated into the workbench and does not make a licensing decision.
- The current top bar contains project identification and narration playback controls. Per-beat visual controls now live under **Visual Layer**; do not add music or SFX controls to the global top bar.

## User workflow

1. Open the video project and select a visual take manifest in **Visual Layer**, or create a new one with a unique `v_layer_*` ID, title, and whole-video creative direction. Creation scaffolds pending entries for the narration IDs and selects the new take.
2. Select a beat in the left-hand sequence. Its stable ID, not its position, locates that beat inside the chosen take and the other layers. Reordering beats preserves the mappings.
3. Open the chosen manifest JSON in the default editor. Describe the beat's visual intent and point it to project-specific element/animation files. Choose EffectCraft, Manim, or GSAP for that beat. A take can change one segment substantially while keeping a coherent direction for the rest of the spine. Add a library reference only when reusing an existing asset or recipe. Reload the workbench to see updated validation and progress.
4. Edit approved words and narration audio in the existing script/audio workflow. A visual take uses the same narration spine; editing narration does not silently copy or rewrite the take's implementation files.
5. Open **Music** or **SFX** for the selected beat. Create that layer's JSON only when needed, then open it in the default editor to map one or more project-relative audio paths to cues. Empty/missing mappings are normal and visible; each beat has at most one mapping file per layer.
6. Source and review assets separately with Asset Finder when ready. The mapper validates project-relative path shape and containment; it does not confirm that a file exists, record provenance, or decide usage rights.
7. Switch beats or visual takes and see the corresponding status and mapping. If approved text changes, keep existing mappings and flag text-dependent visual intent or audio cues for review rather than silently retiming or deleting them.

## Data ownership and storage

| Layer | Source of truth | Current behavior |
|---|---|---|
| Script text + narration audio | Project `audio/narration_manifest.json` and its selected take files | Existing behavior; no duplicate script/audio JSON |
| Visual | Multiple project `visual_layer/<take-id>.json` manifests, `visual_layer/selected_take.json`, and the project files they reference | Each manifest is one selectable whole-spine take, with creative direction and a stable-ID segment map pointing to its element/animation implementation; selection state identifies the current take |
| Music | Project `audio/music/<segment-id>.json` | Optional cue mapping; no search, playback, mixing, or rendering |
| SFX | Project `audio/sfx/<segment-id>.json` | Optional cue mapping; no search, playback, mixing, or rendering |

### Example video-project folder tree

The example video project is `effectcraft-introduction-01`. The tree starts at that project root, regardless of its private machine-specific parent path. The visual manifests sit directly inside `visual_layer/`, beside their corresponding implementation folders. The two shown segment folders illustrate the pattern; a real take covers the full narration spine.

```text
effectcraft-introduction-01/
├── audio/
│   ├── narration_manifest.json
│   ├── music/
│   │   └── found-effectcraft.json        # optional per-beat cue map
│   └── sfx/
│       └── found-effectcraft.json        # optional per-beat cue map
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

The filenames and engine choices above are illustrative. `selected_take.json` stores the selected manifest filename (for example, `v_layer_1.json`); it is selection state, not another visual take. A segment may instead use EffectCraft-supported project data. Element and animation modules may be organized within each segment folder as needed. A take may explicitly reuse project files from another take or a library entry, but newly created takes should have independent editable files by default so experiments do not alter each other. The workbench creates only the manifest scaffold; it does not create or run the referenced renderer files.

### Visual take manifest contract

Each `visual_layer/<take-id>.json` is both the creative plan and the map to implementation for one whole-spine take. It contains a schema version, stable take ID, display title, overall creative direction, and a `segments` object keyed by narration IDs. Each segment entry records that take's visual intent, approved-text hash, renderer (`effectcraft`, `manim`, or `gsap`, or null while pending), implementation object (or null while pending), and optional library reference. Planning text lives in this manifest; there is no separate per-segment plan JSON or required recipe selection. Newly created takes scaffold all current narration IDs as pending. A complete take has a valid existing implementation entry for every active narration segment. Newly added beats appear as pending in existing takes until their manifest is explicitly updated.

For illustration, `visual_layer/v_layer_1.json` could contain. The all-zero SHA-256 values below are format placeholders and must be replaced with the actual approved-text hashes:

```json
{
  "schema_version": 1,
  "take_id": "v_layer_1",
  "title": "Retro take",
  "creative_direction": "Retro typography and bold color across the narration spine.",
  "segments": {
    "found-effectcraft": {
      "visual_intent": "Reveal the product name like a vintage title card.",
      "source_text_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
      "renderer": "gsap",
      "implementation": {
        "folder": "visual_layer/v_layer_1/found-effectcraft",
        "entry_file": "visual_layer/v_layer_1/found-effectcraft/scene.js"
      },
      "library_reference": null
    },
    "free-motion-graphics": {
      "visual_intent": "Continue the retro treatment with animated diagrams.",
      "source_text_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
      "renderer": "manim",
      "implementation": {
        "folder": "visual_layer/v_layer_1/free-motion-graphics",
        "entry_file": "visual_layer/v_layer_1/free-motion-graphics/scene.py"
      },
      "library_reference": null
    }
  }
}
```

The JSON shows two entries for brevity. `v_layer_2.json` has its own title, direction, and `segments` map; it can point `found-effectcraft` to `visual_layer/v_layer_2/found-effectcraft/scene.js` for a different take on that segment. Selecting `v_layer_2.json` switches the video-wide visual take. The workbench stores that choice in `visual_layer/selected_take.json` and shows the chosen take alongside the selected beat. It validates renderer and project-relative paths but does not invoke renderer code; renderer-specific entry conventions and invocation remain deferred.

All paths inside a manifest are relative to the video project and must remain inside it. Keep renderer code/data in project files rather than embedding whole programs in JSON. Do not copy external tool installations or absolute machine paths into the project. Narration text remains owned by the Script and Narration Layer; a visual take can describe a different visual treatment of a segment without silently changing its spoken words.

Music and SFX files use separate version-1 schemas: [`music_mapping.schema.json`](../../tools/audio_narration_generator/music_mapping.schema.json) and [`sfx_mapping.schema.json`](../../tools/audio_narration_generator/sfx_mapping.schema.json). Each records the layer, stable segment ID, approved-text SHA-256, and a list of up to 500 cues; an empty list is valid. A cue's `start_seconds` is relative to the narration segment, `source_offset_seconds` is an offset within the source asset, optional positive `duration_seconds` limits the cue, and optional `gain_db` is constrained to -60 through +12 dB. Paths are project-relative and must not traverse outside the project or through symlinks. The workbench validates path shape but does not verify licensing or asset availability. Asset Finder provenance remains separate; a receipt is not proof of usage rights. Never put machine-specific absolute paths or media files in this public repository.

The current per-segment visual plans are an implemented predecessor, documented in [Visual Animation Plans Per Segment](TASK-ORDER_VISUAL_ANIMATION_PER_SEGMENT.md). Existing `audio/visuals/<segment-id>.json` files remain intact and can still be opened from the **Legacy per-beat visual plan** details in Visual Layer. There is no automatic or bulk importer; creators can manually carry intent into a chosen take. Any future importer must be explicit/idempotent and must never overwrite or delete originals or assign one old plan to every take. The take manifests are canonical for new whole-spine work.

The workbench provides create/select/open/status for visual take manifests and create/open/status for music/SFX JSON mappings. Take creation scaffolds every current narration ID, selects the new take, and does not overwrite collisions. It should not claim that descriptive text in a manifest has already been rendered. Music/SFX mapping must not automatically mix into the narration review track, trigger asset search/download, or claim a final video mix exists. Later audio composition must define overlap, fades, loudness, and how cue positions respond to narration-length changes before rendering is added.

## Workbench layout requirements

- Keep the top bar for global context and narration transport. **Visual Layer** lists take manifests in project `visual_layer/` and excludes `selected_take.json` from the chooser. Do not restore per-beat controls to the header.
- Add a clearly labeled layer workspace for the selected beat. The top-level tabs and their nesting are specified in the [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md). Preserve the always-visible beat list and a readable script editor at desktop sizes.
- Show the chosen visual take and selected beat ID/title together. For that take's segment entry and each other layer, show state such as missing, saved, needs review, or invalid. A create action must identify whether it creates a whole-spine visual take or a selected-beat music/SFX mapping.
- On narrower windows, collapse or stack secondary panels instead of shrinking the editor or forcing the top bar into a single crowded line. Keyboard navigation, focus visibility, labels, and status announcements must remain usable.
- Avoid a wholesale redesign of the existing visual style. Validate the layout at the screenshot-sized desktop viewport and at narrower widths, with long project names and long beat titles.

## Implementation phases

1. **Completed — contracts:** finalized take-selection and take schemas plus separate Music/SFX mapping schemas. Defined draft/completion and stale-text statuses, renderer values, cue units/ranges, 1 MB file limits, project-relative paths, and non-overwrite behavior. Legacy plan files remain supported; no implicit importer was added.
2. **Completed — project APIs:** added project-confined create/list/select/open/status operations, stable-ID mapping, atomic non-overwriting file creation, current narration hash checks, path/symlink validation, and focused visual-take/mapping modules.
3. **Completed — workbench integration:** connected the Visual Layer chooser and selected-beat view; added Music/SFX create/open/status actions. JSON editing opens in the default app. Existing script, playback, Scratchpad, F5-TTS, and legacy visual-plan workflow are retained. Renderer code and audio media are never executed or played.
4. **Completed — tests/docs:** added regression tests for take switching/isolation, reordering/new IDs, stale text, route confinement, unsafe/malformed mappings, and concurrent create collisions. Updated this task order and the narration workbench guide. Layer navigation retains its keyboard model; the new content stacks responsively.
5. **Deferred — composition:** synchronized preview, Asset Finder integration, and final audio/video assembly remain future work after cue composition semantics and renderer contracts are specified.

## Acceptance checks

- One beat can have any combination of the four layers; missing optional layer entries/files are not an error. Every visible layer action targets the selected beat.
- The video project contains `visual_layer/` with multiple manifest JSON files, such as `v_layer_1.json` and `v_layer_2.json`, a `selected_take.json` pointer, and separate folders for project-specific element/animation work. Each manifest combines whole-spine direction with per-segment implementation references.
- Selecting a manifest selects that take across the narration spine. Selection persists, switching takes preserves both manifests/files, and editing one take does not silently change another. The workbench reports progress until all active narration IDs have valid implementation files.
- Each take maps the exact stable segment IDs in `audio/narration_manifest.json`. Reordering beats preserves associations; newly added beats appear as pending in existing takes until addressed. A complete take accounts for every active narration segment.
- Each segment entry may choose EffectCraft, Manim, or GSAP and reference its project-specific folder/entry file. Library references are optional. Creative direction and per-segment intent live in the same manifest as implementation references; no separate plan JSON or recipe selection is required.
- Existing `audio/visuals/<segment-id>.json` plans remain available from the legacy Visual Layer disclosure; no migration overwrites or deletes originals.
- Music and SFX JSON files validate against their own versioned schemas, contain only project-relative asset references, and neither overwrite existing files nor change narration/visual data.
- Reordering beats preserves all layer mappings by stable ID. Editing spoken text leaves take mappings intact and gives a clear review signal for visual intent or cues that track the source-text hash.
- Existing script editing, SAPI/F5-TTS playback, legacy visual-plan creation/opening, Scratchpad, and take review remain usable after the layout change.
- The desktop top bar has no per-beat layer creation controls; the selected-beat workspace remains usable at narrow widths with keyboard and screen-reader labels.
- Tests establish that simply selecting or editing a visual take does not execute renderer code, and that no music/SFX mapping action downloads media, runs Asset Finder, mixes audio, or renders video.

## Related documents

- [Visual animation per-segment task order](TASK-ORDER_VISUAL_ANIMATION_PER_SEGMENT.md)
- [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md)
- [Narration workbench guide](../../tools/audio_narration_generator/README.md#segment-layers)
- [Asset Finder](../../tools/asset_finder/README.md)
