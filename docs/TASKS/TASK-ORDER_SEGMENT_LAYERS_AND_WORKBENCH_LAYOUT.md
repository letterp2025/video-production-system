# Task Order: Segment Layers and Workbench Layout

**Task ID:** SLW-001 | **Status:** Initial implementation complete; target design defined; follow-up implementation pending | **Last updated:** 2026-11-23

## Implementation record

- Added project-root `visual_layer/<take-id>.json` whole-spine visual take manifests and `visual_layer/selected_take.json` selection state. Creating a take scaffolds an entry keyed by every current stable narration segment ID, selects it, and leaves each entry pending for custom project work.
- The Visual Layer lists/selects takes, shows whole-video direction and selected-beat intent/renderer/implementation status, and opens the manifest in the operating system's default editor. New take IDs cannot overwrite existing files. Renderer references are never executed.
- Added optional per-beat `audio/music/<segment-id>.json` and `audio/sfx/<segment-id>.json` create/open/status workflows. Files are versioned, atomic, non-overwriting mappings; changing approved spoken text marks hash-linked visual/audio entries as needing review.
- Added strict schemas and project-confined path validation, plus regression coverage for stable IDs, take isolation, stale text, malformed/unsafe mappings, and local API routes.
- Preserved the earlier `audio/visuals/<segment-id>.json` recipe-plan flow under a clearly named legacy section; existing files are not moved, deleted, or silently imported.
- Audio cue mapping is storage only. Asset search/download, preview, mixing, and video rendering remain out of scope; use Asset Finder separately when sourcing is needed.

## Objective

Use stable narration segments as the spine for brainstorming, selecting, and preparing the assets that will be assembled in a separate non-linear video editor (NLE). VPS is an asset-management and preparation workspace, not an NLE, mixer, or final video renderer. This document records the already implemented prototype and the defined target layer model; the target changes below have not been implemented.

## Product intent and target design

- Keep **Script and Narration Layer**, **Visual Layer**, and **Music Layer** as the three top-level work areas. Sound effects (SFX) belong inside **Visual Layer**, alongside the visual take and segment they support; do not expose SFX as a separate top-level tab.
- A visual take is an alternative treatment of the whole narration spine. Its manifest maps stable narration IDs to project-specific visual work. A take may use different visual treatment and SFX for a segment than another take. EffectCraft produces a separate visual asset for each segment; VPS organizes the work and asset references rather than assembling those exports into a timeline.
- Within a selected whole-spine take, each segment can have multiple distinct visual requests over time. Each request asks external Codex to create or revise that segment's project-owned element, animation, and export. Keep previous requests and completed candidates; a new request never overwrites an earlier attempt and does not create a new whole-spine take.
- A visual request can be a custom text-only brief with no library use, or can attach one or more entries from the Visual Library Browser. Each attached entry can have its own user note describing how it should inform or be adapted for the request. Library use is optional.
- Music is a project-wide list, not an independent music layer per segment. Each music item identifies a start segment and an end segment: it starts at the beginning of the start segment and ends at the end of the end segment. The UI should make those segment anchors clear.
- Show the stable narration segment ID clearly in the selected-segment context throughout the layer UI. Display IDs, as well as titles, for music start/end anchors so references remain unambiguous when titles change or beats are reordered.
- VPS supports ideation and preparation: developing script/narration, exploring visual takes, locating/referencing assets, and recording handoff decisions. The chosen NLE assembles the prepared narration, visual exports, music, and SFX and renders the final video. A fast LOW preview is optional; the reviewed HIGH render is the required final product. Do not imply VPS performs that assembly or final render.
- DaVinci Resolve and Artcraft are candidate NLEs, not a decision. The user considers DaVinci Resolve mature; Artcraft is described by the user as a free, open-source Premiere-like option that is not yet mature and is slow. Do not build NLE-specific integration until an NLE is selected and separately scoped.

The Visual Library Browser should be available inside Visual Layer for browsing and attaching references. Attachment records the entry's library category and stable ID plus the user's note; it does not copy or execute library code. External Codex consumes the request and records its progress and outputs in the request's project-owned folder. VPS displays status/results but does not launch Codex or run renderer code.

Still-open design details include exact within-segment SFX timing, whether SFX needs trim/fade fields, and whether the first music workflow needs overlapping items or crossfades. Asset discovery may use Asset Finder; its role is sourcing, while the layer manifests record the chosen project-local assets and intent.

## Current state and boundaries

- The narration manifest owns segment ID, spoken order, approved text, status, voice settings, and take selection. The workbench already edits and previews these.
- The canonical visual source is a project-root `visual_layer/` folder containing multiple manifest JSON files. Each manifest is one alternative visual take for the entire narration spine. The older optional `audio/visuals/<segment-id>.json` plan is retained as a compatibility workflow only.
- A take such as `v_layer_1.json` can try a retro direction across the video; `v_layer_2.json` can try another direction and treat an individual segment differently. Selecting a take selects its mapping for the whole spine. Both manifests remain available, and changing one take does not silently change the other.
- Every take manifest combines planning with implementation references: an overall creative direction, segment-specific intent, and project-relative paths to folders/files defining elements and animations. Segment mappings use the exact stable IDs from `audio/narration_manifest.json`. Each segment may use EffectCraft, Manim, or GSAP within that take.
- Most elements and animations will be created for the video project. Reusable library recipes or elements are optional references, never prerequisites. There is no separate plan JSON required before adding an implementation to a take manifest.
- The implemented take schema currently has one optional library reference and one direct implementation reference per segment. The target workflow expands this to repeatable per-segment requests, each with optional multiple library references/notes and its own result. This is planned schema evolution, not current behavior.
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
2. Select a whole-spine visual take and a stable-ID segment within it. Create a visual request for that segment. It may be a custom brief without library use, or attach one or more library entries with a note for each about what to reuse, adapt, or avoid. Alternative whole-spine takes remain separate; repeated requests inside one take are successive candidates for that segment, not new takes.
3. Hand the request to external Codex. Codex creates the element/animation and segment export in that request's own project folder, then records progress and output paths in its result record. VPS displays the status and, when present, the preview and project-owned files. New requests create new IDs and preserve previous attempts/results.
4. Compare completed candidates and their optional SFX plans for a segment, then select the candidate to use in that take. Keep other attempts available. The selected whole-spine take can retain a chosen candidate for each narration segment.
5. Add project-wide music items by choosing the segment where each item starts and the segment where it ends. Display both IDs and titles in the UI; do not require users to enter timeline seconds for these segment-boundary placements.
6. Locate/review assets separately (using Asset Finder when appropriate), record project-local references and source information, and prepare segment visual exports and edit notes for handoff.
7. Assemble and mix the prepared assets in the chosen NLE. LOW is an optional fast preview; HIGH is the required final render. VPS does not perform this final assembly or render.

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
| Visual and SFX | Whole-spine visual take manifest, per-segment request/result records, and project files/assets referenced by each request | Each take records overall direction and stable-ID segment slots. Each slot can retain multiple requests/results and a selected completed candidate. Optional SFX planning/assets are attached to the matching request/candidate inside Visual Layer, so choosing a candidate also identifies its associated SFX. The selected candidate's renderer-produced export supplies that segment's visual asset for NLE use. |
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

This illustrates the intended project-wide music manifest and visual-take/segment relationship for SFX and repeatable visual requests. `audio/music/manifest.json` is a suggested location; the exact music schema and SFX serialization still need design. Request IDs and filenames are illustrative. Each request keeps its brief and result distinct; VPS creates a `result.json` scaffold with `requested` status, and external Codex updates that record with progress and project-relative output paths. The take manifest points to the selected completed request for each segment, so candidate exports need not be duplicated into a second take-level folder. The NLE's native project and final render are outside VPS's asset-preparation folders.

```text
effectcraft-introduction-01/
├── audio/
│   ├── narration_manifest.json
│   └── music/
│       └── manifest.json                 # project-wide items with start/end segment IDs
├── visual_layer/
│   ├── selected_take.json
│   ├── v_layer_1.json                     # whole-spine direction + selected request per stable segment ID
│   └── v_layer_1/
│       ├── segments/
│       │   └── <stable-segment-id>/
│       │       └── requests/
│       │           ├── VIS-001/
│       │           │   ├── request.json    # brief + optional library references and notes
│       │           │   ├── result.json     # status + completed output references
│       │           │   ├── sfx.json        # optional SFX plan for this visual candidate
│       │           │   ├── implementation/ # project-owned element/animation source
│       │           │   └── exports/        # this request's segment asset/preview
│       │           └── VIS-002/             # another attempt; does not overwrite VIS-001
└── assets/
    └── audio/
        ├── music/                         # selected music assets and source records
        └── sfx/                           # selected SFX assets and source records
```

Do not infer from this conceptual tree that the workbench already creates or validates these target files. SFX belongs to the visual request/candidate for its take and segment; the exact cue schema and timing semantics remain deferred, but its optional project-local `sfx.json` is scoped to that request.

### Implemented visual take manifest contract

The implemented prototype's `visual_layer/<take-id>.json` is both the creative plan and the map to implementation for one whole-spine take. It contains a schema version, stable take ID, display title, overall creative direction, and a `segments` object keyed by narration IDs. Each segment entry records that take's visual intent, approved-text hash, renderer (`effectcraft`, `manim`, or `gsap`, or null while pending), implementation object (or null while pending), and one optional library reference. Newly created takes scaffold all current narration IDs as pending. A complete take has a valid existing implementation entry for every active narration segment. Newly added beats appear as pending in existing takes until their manifest is explicitly updated. This describes the current prototype; the target request model below replaces the one-direct-implementation workflow for new visual work.

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

### Target visual request and library-reference contract

Keep the whole-spine take as the top-level visual alternative. Within the selected take, each stable narration segment can have zero or more distinct visual requests. A request is one attempt to create or revise that segment's visual asset; it is not a separate take and must not alter earlier requests or completed outputs. Give each request a unique, non-overwriting ID within its take/segment.

The take manifest keeps a `selected_request_id` (or equivalent explicit selection) for each segment when the user chooses a completed candidate. A missing selection is valid while work is pending. Selecting a request for one segment must not change the selected take or another segment's candidate.

Each request records its stable take ID and segment ID, the user's free-text visual brief, optional context, an optional renderer preference, and zero or more library references. No library reference is required: a brief such as “retro text-only reveal” is sufficient for Codex to create new project-specific elements and animation. When an entry is attached, record its library category and stable entry ID plus a user-authored note for that particular reference. This supports several inspirations (for example, an element and an animation) in one request. Do not store machine-specific absolute paths or assume referenced library files are copied into the video project.

The Visual Library Browser should be available inside Visual Layer while a take and segment are selected. It should search/filter public and configured private references, elements, and animations; show entry details and available previews; and let the user attach an entry with a note without leaving the selected segment context. Attachment updates only the current/new request for the selected take and segment. The browser remains read-only with respect to library entries. Referenced library code is never executed by VPS. If a reference later becomes unavailable, report that state without deleting the stored reference or request.

An optional SFX section belongs alongside each request/candidate in Visual Layer, not in a separate top-level tab. Its cue/assets are associated with that exact take, segment, and visual request. Selecting a different completed visual candidate selects its corresponding SFX plan too; a candidate without SFX is valid. Keep exact cue timing, trim/fade, and asset acquisition details within the separately scoped audio design work.

VPS creates each request record and a separate result-record scaffold. External Codex (or the user working with Codex) consumes the request and writes implementation files and a segment export under that request's project-owned folder, updating only the result record with status (`requested`, `in_progress`, `completed`, or `failed`) and project-relative paths to implementation files, a preview when available, and the exported segment asset. Keep the user's brief/reference notes intact after handoff; a materially different follow-up brief creates a new request ID. VPS validates path confinement, displays request status/results, and allows completed candidates to be compared. The user can select one completed candidate for use by that segment in the take; other candidates remain available. Refreshing Visual Layer reveals an updated result. VPS does not launch external Codex, run renderer code, or create/execute the animation itself.

The current Music and SFX files use separate version-1 schemas: [`music_mapping.schema.json`](../../tools/audio_narration_generator/music_mapping.schema.json) and [`sfx_mapping.schema.json`](../../tools/audio_narration_generator/sfx_mapping.schema.json). Each records the layer, stable segment ID, approved-text SHA-256, and a list of up to 500 cues; an empty list is valid. A cue's `start_seconds` is relative to the narration segment, `source_offset_seconds` is an offset within the source asset, optional positive `duration_seconds` limits the cue, and optional `gain_db` is constrained to -60 through +12 dB. These schemas describe the existing per-segment prototype, not the target project-wide music model or take-associated SFX model. Any schema changes must preserve project-relative path confinement and must not imply that the workbench verifies licensing or asset availability. Asset Finder provenance remains separate; a receipt is not proof of usage rights. Never put machine-specific absolute paths or media files in this public repository.

The current per-segment visual plans are an implemented predecessor, documented in [Visual Animation Plans Per Segment](TASK-ORDER_VISUAL_ANIMATION_PER_SEGMENT.md). Existing `audio/visuals/<segment-id>.json` files remain intact and can still be opened from the **Legacy per-beat visual plan** details in Visual Layer. There is no automatic or bulk importer; creators can manually carry intent into a chosen take. Any future importer must be explicit/idempotent and must never overwrite or delete originals or assign one old plan to every take. The take manifests are canonical for new whole-spine work.

The workbench provides create/select/open/status for visual take manifests and create/open/status for music/SFX JSON mappings. Take creation scaffolds every current narration ID, selects the new take, and does not overwrite collisions. It should not claim that descriptive text in a manifest has already been rendered. Music/SFX mapping must not automatically mix into the narration review track, trigger asset search/download, or claim a final video mix exists. Later audio composition must define overlap, fades, loudness, and how cue positions respond to narration-length changes before rendering is added.

## Workbench layout requirements

The requirements below describe the implemented prototype unless explicitly marked as target behavior. The target tab hierarchy is three top-level layers, with SFX nested under Visual Layer.

- Keep the top bar for global context and narration transport. **Visual Layer** lists take manifests in project `visual_layer/` and excludes `selected_take.json` from the chooser. Do not restore per-beat controls to the header.
- Add a clearly labeled layer workspace for the selected beat. The top-level tabs and their nesting are specified in the [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md). Preserve the always-visible beat list and a readable script editor at desktop sizes.
- Show the chosen visual take and selected beat ID/title together. For that take's segment entry and each other layer, show state such as missing, saved, needs review, or invalid. A create action must identify whether it creates a whole-spine visual take or a selected-beat music/SFX mapping.
- **Target:** show the stable segment ID prominently in the shared selected-segment context across Script and Narration, Visual, and Music views. In Music Layer, show both the stable IDs and titles for each item's start and end segments.
- **Target:** place SFX controls and cue status within the selected visual request/candidate in Visual Layer, scoped to its take and stable segment ID. Do not retain SoundEffects as a top-level tab in the target design.
- **Target:** provide project-wide music items with segment-boundary start/end anchors rather than presenting the intended music plan as unrelated per-segment cue files.
- **Target:** show the selected take/segment's repeatable visual request history. Allow a new custom text brief without library use, or attach one or more library entries and add a note to each. Show request status and completed outputs/previews; allow choosing a completed candidate for the segment without deleting other attempts.
- **Target:** integrate the read-only Visual Library Browser inside Visual Layer so browsing and attaching references preserves the selected take/segment context. Do not copy or execute library content as a side effect of attaching it.
- **Target:** provide a clear handoff record for external Codex to consume and a separate result record for its progress and completed project-relative outputs. Refresh and display results, but do not invoke Codex or execute renderer code from VPS.
- On narrower windows, collapse or stack secondary panels instead of shrinking the editor or forcing the top bar into a single crowded line. Keyboard navigation, focus visibility, labels, and status announcements must remain usable.
- Avoid a wholesale redesign of the existing visual style. Validate the layout at the screenshot-sized desktop viewport and at narrower widths, with long project names and long beat titles.

## Implementation phases

1. **Completed — contracts:** finalized take-selection and take schemas plus separate Music/SFX mapping schemas. Defined draft/completion and stale-text statuses, renderer values, cue units/ranges, 1 MB file limits, project-relative paths, and non-overwrite behavior. Legacy plan files remain supported; no implicit importer was added.
2. **Completed — project APIs:** added project-confined create/list/select/open/status operations, stable-ID mapping, atomic non-overwriting file creation, current narration hash checks, path/symlink validation, and focused visual-take/mapping modules.
3. **Completed — workbench integration:** connected the Visual Layer chooser and selected-beat view; added Music/SFX create/open/status actions. JSON editing opens in the default app. Existing script, playback, Scratchpad, F5-TTS, and legacy visual-plan workflow are retained. Renderer code and audio media are never executed or played.
4. **Completed — tests/docs:** added regression tests for take switching/isolation, reordering/new IDs, stale text, route confinement, unsafe/malformed mappings, and concurrent create collisions. Updated this task order and the narration workbench guide. Layer navigation retains its keyboard model; the new content stacks responsively.
5. **Planned — visual request workflow:** define versioned request/result records, stable per-segment request IDs, safe project-confined output paths, status handling, candidate comparison, and per-segment candidate selection within a whole-spine take. Preserve older take manifests and mappings; do not overwrite or implicitly migrate them.
6. **Planned — library browser integration:** expose the existing read-only catalog inside Visual Layer, including Public/Private and References/Elements/Animations browsing, detail/preview, attach-reference, and per-reference note workflows. Keep private roots in local configuration and store only catalog identity in project files.
7. **Deferred — composition:** synchronized preview, Asset Finder integration, and final audio/video assembly remain future work after cue composition semantics and renderer contracts are specified.

## Follow-up scope: target layer model

This work is not implemented by the prototype recorded above. Before treating this task order as complete for the target design, plan and implement the following within a separately approved execution pass:

1. Update navigation to the three target top-level tabs: Script and Narration Layer, Visual Layer, and Music Layer; nest SFX within Visual Layer.
2. Keep the optional SFX section inside each visual request/candidate in Visual Layer. SFX follows the selected take, stable segment ID, and selected visual candidate; different candidates or takes may have different SFX, and no candidate is required to have SFX.
3. Add repeatable visual requests under each take/segment. Keep every request and completed result distinct; support custom briefs with no library and optional attached library references with per-reference notes. Let the user compare completed outputs and select one candidate for that segment without converting it into a new whole-spine take.
4. Integrate the read-only Visual Library Browser into Visual Layer so the user can search, inspect, preview, attach, and annotate library entries in the selected request. Do not copy/execute library content or expose private paths.
5. Define an external-Codex file handoff: VPS creates/presents the request; external Codex records progress and project-relative result paths separately; VPS refreshes and displays status, preview, implementation, and exported segment asset. Do not auto-launch Codex or execute renderers.
6. Replace per-segment music planning as the target workflow with a project-wide manifest whose items reference an asset and start/end segment IDs. Preserve the defined boundary semantics and keep detailed overlap/fade behavior explicitly unresolved until decided.
7. Display stable narration IDs clearly in shared selected-segment context and next to music start/end segment titles.
8. Keep VPS limited to brainstorming, asset references, and preparation/handoff. Do not add NLE integration, timeline assembly, audio mixing, or final video rendering as part of these layer changes.
9. Add tests for request isolation/history, library reference and note persistence, result path/status validation, candidate selection, take-specific SFX, project-wide music boundaries, stable-ID visibility/persistence, and absence of playback/mixing/rendering side effects. Keep existing project data safe; any migration must be explicit, non-destructive, and separately reviewed.

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
- For a selected whole-spine take and stable-ID segment, the user can create any number of distinct visual requests. A request can be custom text-only with no library reference, or include multiple library entries with a note per entry.
- Each request has a stable unique ID and separate request/result records. Creating or revising a request does not overwrite earlier briefs, references, implementation files, previews, or exports.
- The user can hand the request to external Codex. Codex can update progress and record project-relative implementation, preview, and segment-export paths; after refresh, VPS shows the status and available result for that same request. VPS does not launch Codex or execute renderer code.
- Completed requests appear as comparable candidates within their take/segment. The user can select one candidate for that segment; this does not create a new whole-spine take or alter another segment's selection. Unselected candidates remain available.
- The Visual Library Browser is available without leaving the selected take/segment context, supports public/private and reference/element/animation browsing, and attaches stable catalog identity plus a user note to the current request. It does not modify library entries, copy files, execute code, or store private machine paths in project manifests.
- The selected stable narration ID is plainly visible across layer views. Music items display start/end segment IDs and titles.
- Music is represented project-wide, starting at the beginning of its named start segment and ending at the end of its named end segment.
- SFX planning/assets are attached to a visual request/candidate within a take and stable segment. Selecting a different visual candidate selects its associated SFX plan; changing takes or candidates does not change narration or erase other attempts.
- Each visual request retains its own segment export from its chosen renderer (EffectCraft, Manim, or GSAP). The selected completed candidate supplies the visual asset for that segment's NLE handoff; VPS does not execute renderers or assemble the final video.
- VPS remains a brainstorming and asset-preparation workspace. A separately chosen NLE owns timeline assembly, mixing, and final rendering; no NLE is selected or integrated by these requirements. LOW is optional, while a reviewed HIGH render is required as the final product.

## Related documents

- [Visual animation per-segment task order](TASK-ORDER_VISUAL_ANIMATION_PER_SEGMENT.md)
- [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md)
- [Narration workbench guide](../../tools/audio_narration_generator/README.md#segment-layers)
- [Visual Library Browser](../../tools/library-browser/README.md)
- [Asset Finder](../../tools/asset_finder/README.md)
