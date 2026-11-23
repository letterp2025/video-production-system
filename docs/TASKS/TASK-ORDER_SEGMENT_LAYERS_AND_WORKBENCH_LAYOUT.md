# Task Order: Segment Layers and Workbench Layout

**Task ID:** SLW-001 | **Status:** Initial implementation complete; target design update in discussion | **Last updated:** 2026-11-23

## Implementation record

- Added project-root `visual_layer/<take-id>.json` whole-spine visual take manifests and `visual_layer/selected_take.json` selection state. Creating a take scaffolds an entry keyed by every current stable narration segment ID, selects it, and leaves each entry pending for custom project work.
- The Visual Layer lists/selects takes, shows whole-video direction and selected-beat intent/renderer/implementation status, and opens the manifest in the operating system's default editor. New take IDs cannot overwrite existing files. Renderer references are never executed.
- Added optional per-beat `audio/music/<segment-id>.json` and `audio/sfx/<segment-id>.json` create/open/status workflows. Files are versioned, atomic, non-overwriting mappings; changing approved spoken text marks hash-linked visual/audio entries as needing review.
- Added strict schemas and project-confined path validation, plus regression coverage for stable IDs, take isolation, stale text, malformed/unsafe mappings, and local API routes.
- Preserved the earlier `audio/visuals/<segment-id>.json` recipe-plan flow under a clearly named legacy section; existing files are not moved, deleted, or silently imported.
- Audio cue mapping is storage only. Asset search/download, preview, mixing, and video rendering remain out of scope; use Asset Finder separately when sourcing is needed.

## Objective

Use stable narration segments as the spine for brainstorming, selecting, and preparing the assets that will be assembled in a separate non-linear video editor (NLE). VPS is an asset-management and preparation workspace, not an NLE, mixer, or final video renderer. This document records the already implemented prototype and the target layer model being discussed; the target changes below have not been implemented.

## Product intent and target design

- Keep **Script and Narration Layer**, **Visual Layer**, and **Music Layer** as the three top-level work areas. Sound effects (SFX) belong inside **Visual Layer**, alongside the visual take and segment they support; do not expose SFX as a separate top-level tab.
- A visual take is an alternative treatment of the whole narration spine. Its manifest maps stable narration IDs to project-specific visual work. A take may use different visual treatment and SFX for a segment than another take. EffectCraft produces a separate visual asset for each segment; VPS organizes the work and asset references rather than assembling those exports into a timeline.
- Music is a project-wide list, not an independent music layer per segment. Each music item identifies a start segment and an end segment: it starts at the beginning of the start segment and ends at the end of the end segment. The UI should make those segment anchors clear.
- Show the stable narration segment ID clearly in the selected-segment context throughout the layer UI. Display IDs, as well as titles, for music start/end anchors so references remain unambiguous when titles change or beats are reordered.
- VPS supports ideation and preparation: developing script/narration, exploring visual takes, locating/referencing assets, and recording handoff decisions. The chosen NLE assembles the prepared narration, visual exports, music, and SFX and renders the final video. A fast LOW preview is optional; the reviewed HIGH render is the required final product. Do not imply VPS performs that assembly or final render.
- DaVinci Resolve and Artcraft are candidate NLEs, not a decision. The user considers DaVinci Resolve mature; Artcraft is described by the user as a free, open-source Premiere-like option that is not yet mature and is slow. Do not build NLE-specific integration until an NLE is selected and separately scoped.

Still-open design details include exact within-segment SFX timing, whether SFX needs trim/fade fields, and whether the first music workflow needs overlapping items or crossfades. Asset discovery may use Asset Finder; its role is sourcing, while the layer manifests record the chosen project-local assets and intent.

## Current state and boundaries

- The narration manifest owns segment ID, spoken order, approved text, status, voice settings, and take selection. The workbench already edits and previews these.
- The canonical visual source is a project-root `visual_layer/` folder containing multiple manifest JSON files. Each manifest is one alternative visual take for the entire narration spine. The older optional `audio/visuals/<segment-id>.json` plan is retained as a compatibility workflow only.
- A take such as `v_layer_1.json` can try a retro direction across the video; `v_layer_2.json` can try another direction and treat an individual segment differently. Selecting a take selects its mapping for the whole spine. Both manifests remain available, and changing one take does not silently change the other.
- Every take manifest combines planning with implementation references: an overall creative direction, segment-specific intent, and project-relative paths to folders/files defining elements and animations. Segment mappings use the exact stable IDs from `audio/narration_manifest.json`. Each segment may use EffectCraft, Manim, or GSAP within that take.
- Most elements and animations will be created for the video project. Reusable library recipes or elements are optional references, never prerequisites. There is no separate plan JSON required before adding an implementation to a take manifest.
- The current prototype has separate per-segment Music and SFX JSON create/open/status workflows and four top-level tabs, including a dedicated SoundEffects tab. These are existing behaviors, not the target model above: music is intended to become project-wide, and SFX is intended to move inside Visual Layer and be associated with a visual take and segment.
- The [Asset Finder](../../tools/asset_finder/README.md) can search and download audio with a source/license receipt, but it is not integrated into the workbench and does not make a licensing decision.
- The current top bar contains project identification and narration playback controls. Keep per-segment layer controls in their layer workspaces, not in the global top bar.

## User workflow

The numbered steps below describe the implemented prototype workflow, including its current per-segment Music/SFX mappings. They do not describe the target model above.

1. Open the video project and select a visual take manifest in **Visual Layer**, or create a new one with a unique `v_layer_*` ID, title, and whole-video creative direction. Creation scaffolds pending entries for the narration IDs and selects the new take.
2. Select a beat in the left-hand sequence. Its stable ID, not its position, locates that beat inside the chosen take and the other layers. Reordering beats preserves the mappings.
3. Open the chosen manifest JSON in the default editor. Describe the beat's visual intent and point it to project-specific element/animation files. Choose EffectCraft, Manim, or GSAP for that beat. A take can change one segment substantially while keeping a coherent direction for the rest of the spine. Add a library reference only when reusing an existing asset or recipe. Reload the workbench to see updated validation and progress.
4. Edit approved words and narration audio in the existing script/audio workflow. A visual take uses the same narration spine; editing narration does not silently copy or rewrite the take's implementation files.
5. Open **Music** or **SFX** for the selected beat. Create that layer's JSON only when needed, then open it in the default editor to map one or more project-relative audio paths to cues. Empty/missing mappings are normal and visible; each beat has at most one mapping file per layer.
6. Source and review assets separately with Asset Finder when ready. The mapper validates project-relative path shape and containment; it does not confirm that a file exists, record provenance, or decide usage rights.
7. Switch beats or visual takes and see the corresponding status and mapping. If approved text changes, keep existing mappings and flag text-dependent visual intent or audio cues for review rather than silently retiming or deleting them.

### Target workflow (planned)

1. Develop and review the script/narration on the stable-ID narration spine.
2. Select a whole-spine visual take, then develop or revise the selected segment's visual work and its associated SFX plan. Alternative takes may try different visual treatments and SFX for the same segment.
3. Add project-wide music items by choosing the segment where each item starts and the segment where it ends. Display both IDs and titles in the UI; do not require users to enter timeline seconds for these segment-boundary placements.
4. Locate/review assets separately (using Asset Finder when appropriate), record project-local references and source information, and prepare segment visual exports and edit notes for handoff.
5. Assemble and mix the prepared assets in the chosen NLE. LOW is an optional fast preview; HIGH is the required final render. VPS does not perform this final assembly or render.

## Data ownership and storage

The table below describes the implemented prototype. The target ownership model is listed separately so the current JSON files are not mistaken for the final design.

| Layer | Source of truth | Current behavior |
|---|---|---|
| Script text + narration audio | Project `audio/narration_manifest.json` and its selected take files | Existing behavior; no duplicate script/audio JSON |
| Visual | Multiple project `visual_layer/<take-id>.json` manifests, `visual_layer/selected_take.json`, and the project files they reference | Each manifest is one selectable whole-spine take, with creative direction and a stable-ID segment map pointing to its element/animation implementation; selection state identifies the current take |
| Music | Project `audio/music/<segment-id>.json` | Optional cue mapping; no search, playback, mixing, or rendering |
| SFX | Project `audio/sfx/<segment-id>.json` | Optional cue mapping; no search, playback, mixing, or rendering |

### Target ownership and handoff

| Layer | Target source of truth | Intended responsibility |
|---|---|---|
| Script and narration | Project narration manifest and its selected take files | Owns stable segment IDs, spoken text, narration takes, and selected narration. |
| Visual and SFX | Whole-spine visual take manifest plus project files/assets referenced by each segment | Each take records visual intent and per-segment implementation. SFX cues/assets are associated with the relevant take and segment. EffectCraft exports one visual asset per segment for NLE use. |
| Music | One project-wide music manifest | Each item references a selected asset and start/end stable segment IDs; start/end boundaries mean the beginning of the start segment and the end of the end segment. |
| Asset provenance | Receipts stored with project assets | Records source and usage information for review; does not itself grant rights. |
| Final video | Chosen NLE project and final export | The NLE assembles, mixes, and renders. VPS prepares assets and handoff information only. |

### Example video-project folder tree

The example video project is `effectcraft-introduction-01`. This is the implemented prototype layout, including its current per-segment music/SFX mapping files. The tree starts at that project root, regardless of its private machine-specific parent path. The visual manifests sit directly inside `visual_layer/`, beside their corresponding implementation folders. The two shown segment folders illustrate the pattern; a real take covers the full narration spine.

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

### Target project layout (conceptual)

This illustrates the intended project-wide music manifest and visual-take/segment relationship for SFX. `audio/music/manifest.json` is a suggested location; the exact music schema and SFX serialization still need design. The NLE's native project and final render are outside VPS's asset-preparation folders.

```text
effectcraft-introduction-01/
├── audio/
│   ├── narration_manifest.json
│   └── music/
│       └── manifest.json                 # project-wide items with start/end segment IDs
├── visual_layer/
│   ├── selected_take.json
│   ├── v_layer_1.json                     # whole-spine visual take, keyed by stable IDs
│   └── v_layer_1/
│       ├── segments/
│       │   └── <stable-segment-id>/       # visual implementation and take-specific SFX intent
│       ├── effectcraft/                   # renderer-native project/source files
│       └── exports/
│           └── <stable-segment-id>.*      # one EffectCraft visual asset per segment
└── assets/
    └── audio/
        ├── music/                         # selected music assets and source records
        └── sfx/                           # selected SFX assets and source records
```

Do not infer from this conceptual tree that the workbench already creates or validates these target files. In particular, keep SFX logically associated with a visual take and segment, but settle whether its cue data is embedded in the take manifest or stored in a referenced project-local file during schema design.

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

The current Music and SFX files use separate version-1 schemas: [`music_mapping.schema.json`](../../tools/audio_narration_generator/music_mapping.schema.json) and [`sfx_mapping.schema.json`](../../tools/audio_narration_generator/sfx_mapping.schema.json). Each records the layer, stable segment ID, approved-text SHA-256, and a list of up to 500 cues; an empty list is valid. A cue's `start_seconds` is relative to the narration segment, `source_offset_seconds` is an offset within the source asset, optional positive `duration_seconds` limits the cue, and optional `gain_db` is constrained to -60 through +12 dB. These schemas describe the existing per-segment prototype, not the target project-wide music model or take-associated SFX model. Any schema changes must preserve project-relative path confinement and must not imply that the workbench verifies licensing or asset availability. Asset Finder provenance remains separate; a receipt is not proof of usage rights. Never put machine-specific absolute paths or media files in this public repository.

The current per-segment visual plans are an implemented predecessor, documented in [Visual Animation Plans Per Segment](TASK-ORDER_VISUAL_ANIMATION_PER_SEGMENT.md). Existing `audio/visuals/<segment-id>.json` files remain intact and can still be opened from the **Legacy per-beat visual plan** details in Visual Layer. There is no automatic or bulk importer; creators can manually carry intent into a chosen take. Any future importer must be explicit/idempotent and must never overwrite or delete originals or assign one old plan to every take. The take manifests are canonical for new whole-spine work.

The workbench provides create/select/open/status for visual take manifests and create/open/status for music/SFX JSON mappings. Take creation scaffolds every current narration ID, selects the new take, and does not overwrite collisions. It should not claim that descriptive text in a manifest has already been rendered. Music/SFX mapping must not automatically mix into the narration review track, trigger asset search/download, or claim a final video mix exists. Later audio composition must define overlap, fades, loudness, and how cue positions respond to narration-length changes before rendering is added.

## Workbench layout requirements

The requirements below describe the implemented prototype unless explicitly marked as target behavior. The target tab hierarchy is three top-level layers, with SFX nested under Visual Layer.

- Keep the top bar for global context and narration transport. **Visual Layer** lists take manifests in project `visual_layer/` and excludes `selected_take.json` from the chooser. Do not restore per-beat controls to the header.
- Add a clearly labeled layer workspace for the selected beat. The top-level tabs and their nesting are specified in the [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md). Preserve the always-visible beat list and a readable script editor at desktop sizes.
- Show the chosen visual take and selected beat ID/title together. For that take's segment entry and each other layer, show state such as missing, saved, needs review, or invalid. A create action must identify whether it creates a whole-spine visual take or a selected-beat music/SFX mapping.
- **Target:** show the stable segment ID prominently in the shared selected-segment context across Script and Narration, Visual, and Music views. In Music Layer, show both the stable IDs and titles for each item's start and end segments.
- **Target:** place SFX controls and cue status within Visual Layer, scoped to the selected visual take and selected segment. Do not retain SoundEffects as a top-level tab in the target design.
- **Target:** provide project-wide music items with segment-boundary start/end anchors rather than presenting the intended music plan as unrelated per-segment cue files.
- On narrower windows, collapse or stack secondary panels instead of shrinking the editor or forcing the top bar into a single crowded line. Keyboard navigation, focus visibility, labels, and status announcements must remain usable.
- Avoid a wholesale redesign of the existing visual style. Validate the layout at the screenshot-sized desktop viewport and at narrower widths, with long project names and long beat titles.

## Implementation phases

1. **Completed — contracts:** finalized take-selection and take schemas plus separate Music/SFX mapping schemas. Defined draft/completion and stale-text statuses, renderer values, cue units/ranges, 1 MB file limits, project-relative paths, and non-overwrite behavior. Legacy plan files remain supported; no implicit importer was added.
2. **Completed — project APIs:** added project-confined create/list/select/open/status operations, stable-ID mapping, atomic non-overwriting file creation, current narration hash checks, path/symlink validation, and focused visual-take/mapping modules.
3. **Completed — workbench integration:** connected the Visual Layer chooser and selected-beat view; added Music/SFX create/open/status actions. JSON editing opens in the default app. Existing script, playback, Scratchpad, F5-TTS, and legacy visual-plan workflow are retained. Renderer code and audio media are never executed or played.
4. **Completed — tests/docs:** added regression tests for take switching/isolation, reordering/new IDs, stale text, route confinement, unsafe/malformed mappings, and concurrent create collisions. Updated this task order and the narration workbench guide. Layer navigation retains its keyboard model; the new content stacks responsively.
5. **Deferred — composition:** synchronized preview, Asset Finder integration, and final audio/video assembly remain future work after cue composition semantics and renderer contracts are specified.

## Follow-up scope: target layer model

This work is not implemented by the prototype recorded above. Before treating this task order as complete for the target design, plan and implement the following within a separately approved execution pass:

1. Update navigation to the three target top-level tabs: Script and Narration Layer, Visual Layer, and Music Layer; nest SFX within Visual Layer.
2. Associate SFX planning/assets with the selected visual take and its segment, while preserving the ability for alternate takes to specify different SFX for the same stable narration ID.
3. Replace per-segment music planning as the target workflow with a project-wide manifest whose items reference an asset and start/end segment IDs. Preserve the defined boundary semantics and keep detailed overlap/fade behavior explicitly unresolved until decided.
4. Display stable narration IDs clearly in shared selected-segment context and next to music start/end segment titles.
5. Keep VPS limited to brainstorming, asset references, and preparation/handoff. Do not add NLE integration, timeline assembly, audio mixing, or final video rendering as part of these layer changes.
6. Add tests for take-specific SFX, project-wide music boundaries, stable-ID visibility and persistence, and the absence of playback/mixing/rendering side effects. Keep existing project data safe; any migration must be explicit, non-destructive, and separately reviewed.

The specific NLE remains undecided. DaVinci Resolve and Artcraft are candidates only; choosing one and designing any editor-specific handoff is outside this task-order update.

## Acceptance checks

The checks below record acceptance of the implemented prototype, not completion of the target follow-up scope.

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

## Target-design acceptance checks (pending)

- The top-level tabs are Script and Narration Layer, Visual Layer, and Music Layer; SFX appears within Visual Layer for the selected take and segment, with no separate SoundEffects top-level tab.
- The selected stable narration ID is plainly visible across layer views. Music items display start/end segment IDs and titles.
- Music is represented project-wide, starting at the beginning of its named start segment and ending at the end of its named end segment.
- SFX references belong to a visual take and segment; changing visual takes can change that segment's visual implementation and SFX without changing narration or another take.
- EffectCraft remains responsible for exporting one visual asset per segment; VPS tracks intent and asset references but does not execute renderers or assemble the final video.
- VPS remains a brainstorming and asset-preparation workspace. A separately chosen NLE owns timeline assembly, mixing, and final rendering; no NLE is selected or integrated by these requirements. LOW is optional, while a reviewed HIGH render is required as the final product.

## Related documents

- [Visual animation per-segment task order](TASK-ORDER_VISUAL_ANIMATION_PER_SEGMENT.md)
- [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md)
- [Narration workbench guide](../../tools/audio_narration_generator/README.md#segment-layers)
- [Asset Finder](../../tools/asset_finder/README.md)
