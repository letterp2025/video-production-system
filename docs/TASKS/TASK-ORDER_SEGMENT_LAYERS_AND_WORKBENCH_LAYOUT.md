# Task Order: Segment Layers and Workbench Layout

**Task ID:** SLW-001 | **Status:** Target follow-up steps 1–5 implemented; steps 6–9 pending | **Last updated:** 2026-11-23

## Follow-up implementation record (steps 1–5)

- The top-level workbench has Script and Narration, Visual, and Music tabs. Visual Layer now presents a compact take-first flow for the selected segment. The old per-beat visual-plan and SFX mapping panels have been removed from the interface; existing project files are left untouched.
- The request UI no longer presents legacy per-segment intent, renderer, or implementation fields. Its sequence is: choose/create a whole-video take, choose a segment, add a request, then review its result JSON after terminal Codex updates it. Legacy project JSON is not deleted or migrated.
- Each take/segment can index multiple `VIS-*` request folders. Each folder contains a preserved `request.json` brief and a separate `result.json` scaffold; an optional `sfx.json` belongs to that candidate. A completed candidate can be selected independently per segment. Version-one take manifests without request fields remain valid.
- Visual Layer contains the read-only library catalog: public/private scope, reference/element/animation filters, search, detail notes, and local preview. Attachments store only scope, catalog category, stable ID, and a per-reference note in the new request. Optional private library discovery uses `--library-config` and a local config file.
- The file handoff is intentionally simple: VPS creates the request JSON; a separate terminal Codex session reads it, writes the project implementation/export, and can update `result.json`; VPS reads the result after refresh. Visual Layer does not host a Codex service, launch Codex, or run renderer code. Project-wide music and shared ID presentation remain pending.

## Implementation record

- Added project-root `visual_layer/<take-id>.json` whole-spine visual take manifests and `visual_layer/selected_take.json` selection state. Creating a take scaffolds an entry keyed by every current stable narration segment ID, selects it, and leaves each entry pending for custom project work.
- The current Visual Layer presents take direction, selected segment identity, and repeatable request history. Take JSON can be opened in the operating system's default editor. New take IDs cannot overwrite existing files. Renderer references are never executed.
- The predecessor UI added optional per-beat `audio/music/<segment-id>.json` and `audio/sfx/<segment-id>.json` workflows. Music remains per-segment for now; standalone SFX is superseded in the current interface by optional candidate-specific `sfx.json` inside a visual request. Existing files remain untouched.
- Added strict schemas and project-confined path validation, plus regression coverage for stable IDs, take isolation, stale text, malformed/unsafe mappings, and local API routes.
- Older `audio/visuals/<segment-id>.json` plans and per-segment SFX mapping files are no longer exposed in the workbench UI. Existing files are not moved, deleted, or imported.
- Audio cue mapping is storage only. Asset search/download, preview, mixing, and video rendering remain out of scope; use Asset Finder separately when sourcing is needed.

## Objective

Use stable narration segments as the spine for brainstorming, selecting, and preparing the assets that will be assembled in a separate non-linear video editor (NLE). VPS is an asset-management and preparation workspace, not an NLE, mixer, or final video renderer. Visual Layer is a JSON interface for a separate terminal Codex workflow; it is not a Codex server or renderer launcher. This document records the prototype, the implemented first five follow-up steps, and the remaining target work.

## Product intent and target design

- Keep **Script and Narration Layer**, **Visual Layer**, and **Music Layer** as the three top-level work areas. Sound effects (SFX) belong inside **Visual Layer**, alongside the visual take and segment they support; do not expose SFX as a separate top-level tab.
- A visual take is an alternative treatment of the whole narration spine. Its manifest maps stable narration IDs to project-specific visual work. A take may use different visual treatment and SFX for a segment than another take. EffectCraft produces a separate visual asset for each segment; VPS organizes the work and asset references rather than assembling those exports into a timeline.
- Within a selected whole-spine take, each segment can have multiple distinct visual requests over time. Each request asks external Codex to create or revise that segment's project-owned element, animation, and export. Keep previous requests and completed candidates; a new request never overwrites an earlier attempt and does not create a new whole-spine take.
- A visual request can be a custom text-only brief with no library use, or can attach one or more entries from the Visual Library Browser. Each attached entry can have its own user note describing how it should inform or be adapted for the request. Library use is optional.
- Music is a project-wide list, not an independent music layer per segment. Each music item identifies a start segment and an end segment: it starts at the beginning of the start segment and ends at the end of the end segment. The UI should make those segment anchors clear.
- Show the stable narration segment ID clearly in the selected-segment context throughout the layer UI. Display IDs, as well as titles, for music start/end anchors so references remain unambiguous when titles change or beats are reordered.
- VPS supports ideation and preparation: developing script/narration, exploring visual takes, locating/referencing assets, and recording handoff decisions. The chosen NLE assembles the prepared narration, visual exports, music, and SFX and renders the final video. A fast LOW preview is optional; the reviewed HIGH render is the required final product. Do not imply VPS performs that assembly or final render.
- DaVinci Resolve and Artcraft are candidate NLEs, not a decision. The user considers DaVinci Resolve mature; Artcraft is described by the user as a free, open-source Premiere-like option that is not yet mature and is slow. Do not build NLE-specific integration until an NLE is selected and separately scoped.

The Visual Library Browser is available inside the optional request form in Visual Layer. Attachment records the entry's library category and stable ID plus the user's note; it does not copy or execute library code. The workbench creates a request JSON file. The user's separate terminal Codex session reads that file and writes project-owned implementation/assets; that session may update the separate result JSON. VPS shows the result after refresh. Visual Layer does not provide a Codex server, launch Codex, or run renderer code.

Still-open design details include exact within-segment SFX timing, whether SFX needs trim/fade fields, and whether the first music workflow needs overlapping items or crossfades. Asset discovery may use Asset Finder; its role is sourcing, while the layer manifests record the chosen project-local assets and intent.

## Current state and boundaries

- The narration manifest owns segment ID, spoken order, approved text, status, voice settings, and take selection. The workbench already edits and previews these.
- The canonical visual source is a project-root `visual_layer/` folder containing multiple manifest JSON files. Each manifest is one alternative visual take for the entire narration spine. Older `audio/visuals/<segment-id>.json` plan files may remain on disk but are not part of the current workbench workflow.
- A take such as `v_layer_1.json` can try a retro direction across the video; `v_layer_2.json` can try another direction and treat an individual segment differently. Selecting a take selects its mapping for the whole spine. Both manifests remain available, and changing one take does not silently change the other.
- Every take manifest defines an overall creative direction and indexes the stable narration IDs from `audio/narration_manifest.json`. The segment request folders hold repeatable briefs and result records; those results point to project-relative implementation and export files. A request may use EffectCraft, Manim, or GSAP.
- Most elements and animations will be created for the video project. Reusable library recipes or elements are optional references, never prerequisites. There is no separate plan JSON required before adding an implementation to a take manifest.
- The take schema retains optional legacy direct implementation fields for existing manifests and also accepts a per-segment request ID list and selected completed request ID. New Visual Layer work uses request folders, each with its own brief, result, and optional multiple library references/notes. Existing take manifests remain readable; legacy fields are not the new request workflow.
- Music still uses the existing per-segment JSON workflow while project-wide music remains future work. Candidate-specific SFX JSON stays with its visual request. The old per-segment SFX and visual-plan panels are not shown in the current interface; existing files remain untouched.
- The [Asset Finder](../../tools/asset_finder/README.md) can search and download audio with a source/license receipt, but it is not integrated into the workbench and does not make a licensing decision.
- The current top bar contains project identification and narration playback controls. Keep per-segment layer controls in their layer workspaces, not in the global top bar.

## User workflow

The numbered steps below describe the current interface: per-segment Music JSON and request-level SFX JSON. They do not describe the remaining target model above.

1. Open the video project and select a visual take manifest in **Visual Layer**, or create a new one with a unique `v_layer_*` ID, title, and whole-video creative direction. Creation scaffolds pending entries for the narration IDs and selects the new take.
2. Select a beat in the left-hand sequence. Its stable ID, not its position, locates that beat inside the chosen take and the other layers. Reordering beats preserves the mappings.
3. In Visual Layer, add a visual request for the selected stable-ID segment. Write a short custom brief, optionally choose a renderer, and optionally attach library references with notes. VPS saves the brief and result scaffold as project JSON. The task-specific UI keeps take selection, segment identity, and request history together; the raw take JSON can still be opened when needed.
4. Edit approved words and narration audio in the existing script/audio workflow. A visual take uses the same narration spine; editing narration does not silently copy or rewrite the take's implementation files.
5. Open **Music** for the selected segment to create its optional cue JSON. Sound effects belong to a visual request and can be added from that request's details. Empty or missing music mappings are normal; the older standalone `audio/sfx/<segment-id>.json` files are not exposed in the current UI.
6. Source and review assets separately with Asset Finder when ready. The mapper validates project-relative path shape and containment; it does not confirm that a file exists, record provenance, or decide usage rights.
7. Switch beats or visual takes and see the corresponding status and mapping. If approved text changes, keep existing mappings and flag text-dependent visual intent or audio cues for review rather than silently retiming or deleting them.

### Target workflow (planned)

1. Develop and review the script/narration on the stable-ID narration spine.
2. Select a whole-spine visual take and a stable-ID segment within it. Add a visual request for that segment. It may be a custom brief without library use, or attach one or more library entries with a note for each about what to reuse, adapt, or avoid. Alternative whole-spine takes remain separate; repeated requests inside one take are successive attempts for that segment, not new takes.
3. Use a separate Codex session in a terminal to read the request JSON from the project. Codex creates or updates the segment's project-owned element/animation/export files and can record status and project-relative paths in `result.json`. VPS reads and displays that JSON after refresh. New requests create new IDs and preserve previous attempts/results. VPS does not need a Codex server or launch Codex.
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
| SFX | Optional `sfx.json` inside a visual request folder | Candidate-specific data; no search, playback, mixing, or rendering |

### Target ownership and handoff

| Layer | Target source of truth | Intended responsibility |
|---|---|---|
| Script and narration | Project narration manifest and its selected take files | Owns stable segment IDs, spoken text, narration takes, and selected narration. |
| Visual and SFX | Whole-spine visual take manifest, per-segment request/result records, and project files/assets referenced by each request | Each take records overall direction and stable-ID segment slots. Each slot can retain multiple requests/results and a selected completed candidate. Optional SFX planning/assets are attached to the matching request/candidate inside Visual Layer, so choosing a candidate also identifies its associated SFX. The selected candidate's renderer-produced export supplies that segment's visual asset for NLE use. |
| Music | One project-wide music manifest | Each item references a selected asset and start/end stable segment IDs; start/end boundaries mean the beginning of the start segment and the end of the end segment. |
| Asset provenance | Receipts stored with project assets | Records source and usage information for review; does not itself grant rights. |
| Final video | Chosen NLE project and final export | The NLE assembles, mixes, and renders. VPS prepares assets and handoff information only. |

### Example video-project folder tree

The example video project is `effectcraft-introduction-01`. The tree starts at that project root, regardless of its private machine-specific parent path. The take manifests sit directly inside `visual_layer/`; each take/segment request gets a separate folder for its brief and result. The UI creates `request.json` and `result.json`; terminal Codex can place implementation and segment-export files beside them.

```text
effectcraft-introduction-01/
├── audio/
│   ├── narration_manifest.json
│   └── music/
│       └── found-effectcraft.json        # optional current music cue map
└── visual_layer/
    ├── selected_take.json                 # points to the chosen take manifest
    ├── v_layer_1.json                     # whole-spine direction + stable-ID segment index
    ├── v_layer_1/
    │   └── segments/
    │       └── found-effectcraft/          # stable narration segment ID
    │           └── requests/
    │               ├── VIS-001/
    │               │   ├── request.json    # brief + optional library notes
    │               │   ├── result.json     # terminal Codex status + output paths
    │               │   ├── sfx.json        # optional candidate-specific cues
    │               │   └── implementation/
    │               │       └── scene.js    # example terminal Codex output
    │               └── VIS-002/            # another independent attempt
    │                   ├── request.json
    │                   └── result.json
    └── v_layer_2.json                     # alternate whole-spine take (same folder pattern)
```

The filenames above are illustrative. `selected_take.json` stores the selected manifest filename; it is selection state, not another take. Each request is an independent attempt for one stable narration ID. The workbench creates take/request/result scaffolds and optional SFX JSON; terminal Codex creates project-owned implementation and export files and records their project-relative paths in `result.json`. VPS never runs the renderer. Request outputs may be stored anywhere inside the project, provided the result JSON points to them using project-relative paths.

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

### Take manifest contract and legacy fields

The `visual_layer/<take-id>.json` file defines one whole-spine take: schema version, stable take ID, display title, overall creative direction, and a `segments` object keyed by narration IDs. Newly created takes scaffold all current narration IDs as pending. New visual work is recorded in per-segment request folders and selected-request fields. For compatibility, the schema still accepts older direct intent/renderer/implementation/library fields; these are not required for new requests and the simplified UI does not depend on them.

For illustration, `visual_layer/v_layer_1.json` could contain. The all-zero SHA-256 values below are format placeholders and must be replaced with the actual approved-text hashes. The legacy `implementation` examples show how older take manifests may look; current requests store implementation paths in their separate `result.json`:

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

The JSON shows two entries for brevity. `v_layer_2.json` has its own title, direction, and `segments` map. Selecting it switches the video-wide visual take. The workbench stores that choice in `visual_layer/selected_take.json`. It validates manifest and request result paths but does not invoke renderer code; renderer-specific entry conventions and invocation remain deferred.

All paths inside a manifest are relative to the video project and must remain inside it. Keep renderer code/data in project files rather than embedding whole programs in JSON. Do not copy external tool installations or absolute machine paths into the project. Narration text remains owned by the Script and Narration Layer; a visual take can describe a different visual treatment of a segment without silently changing its spoken words.

### Target visual request and library-reference contract

Keep the whole-spine take as the top-level visual alternative. Within the selected take, each stable narration segment can have zero or more distinct visual requests. A request is one attempt to create or revise that segment's visual asset; it is not a separate take and must not alter earlier requests or completed outputs. Give each request a unique, non-overwriting ID within its take/segment.

The take manifest keeps a `selected_request_id` (or equivalent explicit selection) for each segment when the user chooses a completed candidate. A missing selection is valid while work is pending. Selecting a request for one segment must not change the selected take or another segment's candidate.

Each request records its stable take ID and segment ID, the user's free-text visual brief, optional context, an optional renderer preference, and zero or more library references. No library reference is required: a brief such as “retro text-only reveal” is sufficient for Codex to create new project-specific elements and animation. When an entry is attached, record its library category and stable entry ID plus a user-authored note for that particular reference. This supports several inspirations (for example, an element and an animation) in one request. Do not store machine-specific absolute paths or assume referenced library files are copied into the video project.

The Visual Library Browser should be available inside Visual Layer while a take and segment are selected. It should search/filter public and configured private references, elements, and animations; show entry details and available previews; and let the user attach an entry with a note without leaving the selected segment context. Attachment updates only the current/new request for the selected take and segment. The browser remains read-only with respect to library entries. Referenced library code is never executed by VPS. If a reference later becomes unavailable, report that state without deleting the stored reference or request.

An optional SFX section belongs alongside each request/candidate in Visual Layer, not in a separate top-level tab. Its cue/assets are associated with that exact take, segment, and visual request. Selecting a different completed visual candidate selects its corresponding SFX plan too; a candidate without SFX is valid. Keep exact cue timing, trim/fade, and asset acquisition details within the separately scoped audio design work.

VPS creates each request JSON and a separate result JSON scaffold. The user runs Codex independently in a terminal; that session reads the request and writes project-owned implementation files and a segment export. Codex may update only the result record with status (`requested`, `in_progress`, `completed`, or `failed`) and project-relative paths to implementation files, a preview when available, and the exported segment asset. Keep the user's brief/reference notes intact after handoff; a materially different follow-up brief creates a new request ID. VPS validates path confinement, displays result status/paths after refresh, and allows completed candidates to be selected. VPS does not host a Codex service, launch Codex for visual work, run renderer code, or create/execute the animation itself.

The current Music and SFX files use separate version-1 schemas: [`music_mapping.schema.json`](../../tools/audio_narration_generator/music_mapping.schema.json) and [`sfx_mapping.schema.json`](../../tools/audio_narration_generator/sfx_mapping.schema.json). Each records the layer, stable segment ID, approved-text SHA-256, and a list of up to 500 cues; an empty list is valid. A cue's `start_seconds` is relative to the narration segment, `source_offset_seconds` is an offset within the source asset, optional positive `duration_seconds` limits the cue, and optional `gain_db` is constrained to -60 through +12 dB. These schemas describe the existing per-segment prototype, not the target project-wide music model or take-associated SFX model. Any schema changes must preserve project-relative path confinement and must not imply that the workbench verifies licensing or asset availability. Asset Finder provenance remains separate; a receipt is not proof of usage rights. Never put machine-specific absolute paths or media files in this public repository.

The former per-segment visual plans are documented in [Visual Animation Plans Per Segment](TASK-ORDER_VISUAL_ANIMATION_PER_SEGMENT.md). The current workbench no longer exposes their create/open/status workflow. Existing `audio/visuals/<segment-id>.json` files remain untouched; there is no importer. The take manifests and request JSON are canonical for new whole-spine work.

The workbench creates/selects visual take manifests and creates/opens per-segment request, result, and candidate SFX JSON. Take creation scaffolds every current narration ID, selects the new take, and does not overwrite collisions. Music currently retains its per-segment JSON mapping. The interface must not claim that a brief has already been rendered. Music/SFX mappings must not automatically mix into the narration review track, trigger asset search/download, or claim a final video mix exists. Later audio composition must define overlap, fades, loudness, and how cue positions respond to narration-length changes before rendering is added.

## Workbench layout requirements

The requirements below describe the implemented prototype unless explicitly marked as target behavior. The target tab hierarchy is three top-level layers, with SFX nested under Visual Layer.

- Keep the top bar for global context and narration transport. **Visual Layer** lists take manifests in project `visual_layer/` and excludes `selected_take.json` from the chooser. Do not restore per-beat controls to the header.
- Add a clearly labeled layer workspace for the selected beat. The top-level tabs and their nesting are specified in the [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md). Preserve the always-visible beat list and a readable script editor at desktop sizes.
- Show the selected take and selected segment's stable ID/title. Present request status and result paths in the request history; distinguish creating a whole-spine take from adding a request for the selected segment.
- Place optional candidate-specific SFX JSON inside the corresponding visual request. Do not expose SoundEffects as a top-level tab.
- **Pending:** show the stable segment ID in shared context across Script and Narration, Visual, and Music. Project-wide Music items must show start/end segment IDs and titles.
- **Target:** provide project-wide music items with segment-boundary start/end anchors rather than presenting the intended music plan as unrelated per-segment cue files.
- Show the selected take/segment's repeatable visual request history. Allow a custom text brief without library use, optional library entries with a note per entry, and selection among completed candidates without deleting other attempts.
- Keep the Visual Library Browser read-only and collapsible inside the request form; attaching a reference preserves the selected take/segment context and does not copy or execute library content.
- Save a request JSON and separate result JSON for terminal Codex. Refresh and display results, but do not host a Visual Layer Codex service, launch Codex, or execute renderer code from VPS.
- On narrower windows, collapse or stack secondary panels instead of shrinking the editor or forcing the top bar into a single crowded line. Keyboard navigation, focus visibility, labels, and status announcements must remain usable.
- Avoid a wholesale redesign of the existing visual style. Validate the layout at the screenshot-sized desktop viewport and at narrower widths, with long project names and long beat titles.

## Implementation phases

1. **Completed — contracts:** finalized take-selection and take schemas plus separate Music/SFX mapping schemas. Defined draft/completion and stale-text statuses, renderer values, cue units/ranges, 1 MB file limits, project-relative paths, and non-overwrite behavior. Old plan files are not imported or changed.
2. **Completed — project APIs:** added project-confined create/list/select/open/status operations, stable-ID mapping, atomic non-overwriting file creation, current narration hash checks, path/symlink validation, and focused visual-take/mapping modules.
3. **Completed — workbench integration:** connected the Visual Layer chooser and selected-segment view; added Music JSON and candidate-specific SFX actions. JSON editing opens in the default app. Existing script, playback, Scratchpad, and F5-TTS workflows remain. The previous visual-plan and standalone SFX panels are removed from the new interface. Renderer code and audio media are never executed or played.
4. **Completed — tests/docs:** added regression tests for take switching/isolation, reordering/new IDs, stale text, route confinement, unsafe/malformed mappings, and concurrent create collisions. Updated this task order and the narration workbench guide. Layer navigation retains its keyboard model; the new content stacks responsively.
5. **Completed — file-based visual handoff:** create request/result JSON under each take/segment/request folder. A separate terminal Codex session reads the request, creates project-owned outputs, and can update progress and project-relative paths in the result JSON. The workbench reads the result on refresh; no Codex service or auto-launch is required.
6. **Completed — library browser integration:** expose the read-only catalog inside Visual Layer, including Public/Private and References/Elements/Animations browsing, detail/preview, attach-reference, and per-reference note workflows. Keep private roots in local configuration and store only catalog identity in project files.
7. **Deferred — composition:** synchronized preview, Asset Finder integration, and final audio/video assembly remain future work after cue composition semantics and renderer contracts are specified.

## Follow-up scope: target layer model

Steps 1–5 below are implemented in the current follow-up pass. Steps 6–9 remain open before the full target design is complete:

1. Update navigation to the three target top-level tabs: Script and Narration Layer, Visual Layer, and Music Layer; nest SFX within Visual Layer.
2. Keep the optional SFX section inside each visual request/candidate in Visual Layer. SFX follows the selected take, stable segment ID, and selected visual candidate; different candidates or takes may have different SFX, and no candidate is required to have SFX.
3. Add repeatable visual requests under each take/segment. Keep every request and completed result distinct; support custom briefs with no library and optional attached library references with per-reference notes. Let the user compare completed outputs and select one candidate for that segment without converting it into a new whole-spine take.
4. Integrate the read-only Visual Library Browser into Visual Layer so the user can search, inspect, preview, attach, and annotate library entries in the selected request. Do not copy/execute library content or expose private paths.
5. Keep the visual handoff file-based: VPS creates the request JSON; the user's terminal Codex reads it and may update the separate result JSON; VPS reads the result after refresh. Do not add a Codex service, auto-launch Codex, or execute renderers.
6. Replace per-segment music planning as the target workflow with a project-wide manifest whose items reference an asset and start/end segment IDs. Preserve the defined boundary semantics and keep detailed overlap/fade behavior explicitly unresolved until decided.
7. Display stable narration IDs clearly in shared selected-segment context and next to music start/end segment titles.
8. Keep VPS limited to brainstorming, asset references, and preparation/handoff. Do not add NLE integration, timeline assembly, audio mixing, or final video rendering as part of these layer changes.
9. Add tests for request isolation/history, library reference and note persistence, result path/status validation, candidate selection, take-specific SFX, project-wide music boundaries, stable-ID visibility/persistence, and absence of playback/mixing/rendering side effects. Keep existing project data safe; any migration must be explicit, non-destructive, and separately reviewed.

The specific NLE remains undecided. DaVinci Resolve and Artcraft are candidates only; choosing one and designing any editor-specific handoff is outside this task-order update.

## Acceptance checks

The checks below record acceptance of the implemented prototype, not completion of the target follow-up scope.

- One beat can have any combination of the four layers; missing optional layer entries/files are not an error. Every visible layer action targets the selected beat.
- The video project contains `visual_layer/` with whole-spine take manifests, a `selected_take.json` pointer, and per-take/per-segment request folders. Each take defines whole-spine direction and indexes stable segment IDs; request result JSON points to project-specific element/animation and export files.
- Selecting a manifest selects that take across the narration spine. Selection persists, switching takes preserves both manifests/files, and editing one take does not silently change another. New requests and result files are scoped to a take and stable segment ID.
- Each take maps the exact stable segment IDs in `audio/narration_manifest.json`. Reordering beats preserves associations; newly added beats appear as pending in existing takes until addressed. A complete take accounts for every active narration segment.
- Each request may specify a renderer preference or leave that choice to terminal Codex. Library references are optional. The brief and references live in `request.json`; terminal Codex records implementation and export paths in `result.json`.
- The current Visual Layer does not expose the older `audio/visuals/<segment-id>.json` plan workflow. Existing files remain untouched; no migration overwrites or deletes them.
- Music JSON follows its existing mapping schema; candidate SFX JSON is stored beside its visual request. Layer actions do not overwrite existing project JSON or change narration text.
- Reordering beats preserves all layer mappings by stable ID. Editing spoken text leaves take mappings intact and gives a clear review signal for visual intent or cues that track the source-text hash.
- Existing script editing, SAPI/F5-TTS playback, Scratchpad, and take review remain usable after the layout change. Simplified Visual Layer presents take selection, stable segment identity, request history, optional library references, result paths, and candidate SFX JSON. It does not expose predecessor visual-plan or standalone SFX panels; existing files remain untouched.
- The desktop top bar has no per-beat layer creation controls; the selected-beat workspace remains usable at narrow widths with keyboard and screen-reader labels.
- Tests establish that simply selecting or editing a visual take does not execute renderer code, and that no music/SFX mapping action downloads media, runs Asset Finder, mixes audio, or renders video.

## Target-design acceptance checks (status)

- **Implemented:** top-level tabs are Script and Narration Layer, Visual Layer, and Music Layer; optional SFX is nested within Visual Layer.
- **Implemented:** for a selected whole-spine take and stable-ID segment, the user can create distinct requests, each with a custom brief, optional renderer preference, and optional library references/notes.
- **Implemented:** each request has a stable ID and separate request/result records. New requests preserve earlier briefs and candidate files.
- **Implemented:** a separate terminal Codex session can read a request and update result status and project-relative paths. VPS refreshes and displays the result; Visual Layer does not launch Codex or execute renderer code.
- **Implemented:** completed requests can be selected for a segment; other candidates remain available and the selection does not change another segment or take.
- **Implemented:** the read-only Visual Library Browser supports public/private and reference/element/animation browsing, and attaches catalog identity plus a note to a request without copying or executing library code.
- **Pending:** show stable narration IDs as shared context across all layer views and add project-wide Music items with visible start/end segment IDs and titles.
- **Implemented:** optional SFX JSON is scoped to a request/candidate within its take and segment.
- **Implemented boundary:** selected request results may point to a segment export from EffectCraft, Manim, or GSAP. VPS does not execute renderers or assemble the final video.
- **Implemented boundary:** VPS remains a brainstorming and asset-preparation workspace. A separately chosen NLE owns timeline assembly, mixing, and final rendering. LOW is optional; reviewed HIGH is the required final product.

## Related documents

- [Visual animation per-segment task order](TASK-ORDER_VISUAL_ANIMATION_PER_SEGMENT.md)
- [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md)
- [Narration workbench guide](../../tools/audio_narration_generator/README.md#segment-layers)
- [Visual Library Browser](../../tools/library-browser/README.md)
- [Asset Finder](../../tools/asset_finder/README.md)
