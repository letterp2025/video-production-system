# Task Order: Project Sequence Manifest

**Task ID:** PSM-001 | **Status:** Planned; no implementation in this task-order pass | **Last updated:** 2026-11-24

## Objective

Make the workbench's left-hand sequence represent the ordered *video story*, not only the narration manifest's spoken beats. A video can contain visual-only openings, pauses, montages, transitions, and outros before, between, or after spoken segments. Introduce project-root `sequence_manifest.json` as the source of truth for the order of those units. Every unit has a required, editable planned duration. VPS remains a brainstorming and asset-preparation tool, not a nonlinear editor (NLE).

## Why this is needed

Today `audio/narration_manifest.json` owns both approved spoken text and the order shown in the left Beats rail. Narration validation requires non-empty text. Visual take entries, visual request folders, and project-wide music boundaries use stable narration IDs. A silent visual unit therefore cannot be inserted without pretending it is narration, and music cannot start at a visual-only opening or end at a visual-only outro.

Keep the narration manifest dedicated to speech. Do not solve this by putting empty-text placeholders in it. `video_project.json` stays the creative brief/status record; it is not the sequence. Visual take manifests continue to represent alternative treatments of the whole video; they do not each own a competing story order.

## User workflow

1. Open an existing video project. VPS finds or safely initializes `sequence_manifest.json` from the current narration segment order, preserving stable narration IDs and leaving existing project files untouched. Initialization happens only when the file is absent; a malformed existing file is reported, not replaced.
2. Use the shared left rail to select and reorder sequence units. A narration unit links to its existing narration segment. A visual-only unit has its own stable ID and title, with no narration segment and no spoken words. The rail clearly distinguishes the two kinds and keeps the stable ID visible.
3. Add a visual-only unit before, after, or between existing units. Give it a title, editable duration, and optional editorial note/intent. Change its position or planned duration without generating a voice take.
4. In Script and Narration Layer, a narration unit retains the current editor, Scratchpad, SAPI preview, and F5-TTS workflow. A visual-only unit shows a clear no-narration state; it must not offer narration editing, TTS generation, or a misleading silent audio take.
5. In Visual Layer, choose a whole-video take and add/review repeated visual requests for either kind of sequence unit. Visual-only work uses the same project-owned implementation/export handoff and optional candidate SFX, without requiring source narration text.
6. In Music Layer, anchor a project-wide item to the start/end of any sequence unit, including visual-only units. Show IDs and current titles for both boundaries.
7. Hand prepared narration, visual exports, SFX, music choices, sequence order, and planned durations to the chosen NLE. The NLE determines final frame timing, assembly, mixing, and render. A LOW preview remains optional; a reviewed HIGH render is the final product.

## Data ownership and storage

| File | Responsibility after implementation |
|---|---|
| Project-root `sequence_manifest.json` | Canonical ordered list of video units, their stable IDs, kind, title/context, and required planned duration. It does not contain approved narration text, media, or edit tracks. |
| `audio/narration_manifest.json` | Approved words, voice settings, segment status, narration takes, and the speech-only playback/assembly order. A linked narration ID remains stable. |
| Project-root `video_project.json` | Creative identity, rough outline, inspirations, and manually maintained project status; not an ordered sequence. |
| `visual_layer/<take-id>.json` and request folders | Alternative whole-sequence visual directions and candidate work keyed by sequence-unit ID; the selected take remains in `visual_layer/selected_take.json`. |
| `audio/music/manifest.json` | Project-wide music items anchored to start/end sequence-unit IDs. Candidate SFX remains with visual requests. |

Illustrative project layout (the folders are not all pre-created):

```text
video-project/
|-- video_project.json
|-- sequence_manifest.json
|-- audio/
|   |-- narration_manifest.json
|   `-- music/
|       `-- manifest.json
`-- visual_layer/
    |-- selected_take.json
    |-- v_layer_1.json
    `-- v_layer_1/
        `-- segments/
            |-- opening-card/          # visual-only unit ID
            |   `-- requests/VIS-001/
            |       |-- request.json
            |       `-- result.json
            `-- found-effectcraft/     # linked narration ID
                `-- requests/VIS-001/
                    |-- request.json
                    `-- result.json
```

## Proposed sequence contract

The precise versioned JSON Schema will be written during implementation. This example establishes the intended ownership and required duration field:

```json
{
  "schema_version": 1,
  "units": [
    {
      "id": "opening-card",
      "kind": "visual_only",
      "title": "Opening card",
      "duration_seconds": 3.0,
      "note": "Introduce the project before speech begins."
    },
    {
      "id": "found-effectcraft",
      "kind": "narration",
      "narration_segment_id": "found-effectcraft",
      "duration_seconds": 5.0
    },
    {
      "id": "interface-montage",
      "kind": "visual_only",
      "title": "Interface montage",
      "duration_seconds": 4.0
    }
  ]
}
```

- Array order is story order. IDs are unique across both unit kinds and remain stable when a unit is renamed, moved, or its duration changes. A narration unit links to exactly one existing narration segment; a visual-only unit must not have a narration link. Avoid duplicated narration links. Existing narration IDs should be reused as sequence-unit IDs for a straightforward migration.
- `duration_seconds` is required on **every** unit, finite, positive, and editable. It is a *planned target*, not a guarantee of rendered duration or a frame-accurate timestamp. On creation, use a documented editable initial value: measured selected narration audio duration when available, otherwise a clearly labeled estimate; use a simple default such as 3 seconds for a new visual-only unit. Do not silently overwrite a user's duration when audio takes change.
- A narration unit's approved text and voice controls are resolved from the linked narration manifest, not copied into the sequence. The UI may display its current narration title; it must not silently fork two editable titles. Decide in implementation whether narration titles are resolved live and the sequence title is an optional fallback, then test that rule.
- A visual-only unit's note is editorial intent, not a second visual request. It can be present before a take or request exists. Units without visual work are valid and visibly pending.
- Validate bounded file size, unique/valid IDs, valid links, sensible lengths, and safe project-relative paths where applicable. Preserve invalid or unknown existing files for inspection rather than rewriting them.

## Cross-manifest behavior and migration

- Existing projects have no sequence manifest. First initialization derives ordered narration units from the current narration array, including inactive units so no historical mapping disappears. The rail's existing active/inactive/deleted filters need explicit sequence-aware behavior; do not silently drop or delete inactive/deleted records. Preserve each narration ID and its associated visual request folders.
- Once a sequence manifest exists, its array controls the left story order. Adding/removing a narration segment must be reconciled explicitly: flag unlinked narration segments and missing/deleted links for review; never silently discard sequence units or rewrite visual take files. Define which UI action inserts a new narration unit into the sequence.
- Narration-only SAPI/F5 playback and assembled audio cannot be presented as a preview of visual-only intervals. Keep those controls scoped to spoken segments, with clear labeling about what the preview omits. Define and test how a narration unit's speech-only playback order is kept consistent with the sequence order when units are moved; do not maintain two contradictory authoritative orders without a reconciliation rule.
- Expand visual take validation/scaffolding/status to all active sequence units. For narration-linked requests, retain source-text hash staleness checks. For visual-only requests, introduce a separate source revision/fingerprint derived from that unit's relevant brief/context; do not invent empty narration text or misuse `source_text_sha256`. Version the request/result contract and keep legacy narration-linked records readable.
- Update music anchors from narration-only `start_segment_id`/`end_segment_id` to sequence-unit references. Design a versioned migration/compatibility rule so existing music items keep their original IDs and intended boundaries. Validate order against the sequence array. Music remains a planning map, not playback or mixing.
- The older `audio/visuals/`, per-segment music, and per-segment SFX formats remain untouched legacy files. No implementation step may remove existing media, requests, takes, or project files merely because the new sequence is introduced.

## Implementation phases

1. **Contract and migration tests:** define `sequence_manifest.json` schema, duration/default semantics, ID/link validation, safe initialization, and fixtures for existing projects. Decide the narration-title and speech-order reconciliation rules before wiring UI mutations.
2. **Project loading and operations:** load/create the sequence, expose ordered units, add/reorder/edit visual-only units, reconcile narration additions/status changes, and guard malformed files without destructive repair.
3. **Shared rail and narration workspace:** relabel the Beats rail to reflect story units, show type/title/ID/duration, preserve selection across tabs, provide a clear no-narration state, and keep narration preview/generation speech-only.
4. **Visual takes and handoff:** key take entries and request folders by sequence-unit ID, allow visual-only requests and candidate SFX, introduce appropriate visual-only revision validation, preserve old requests, and update whole-take completeness against the sequence.
5. **Music and NLE handoff:** migrate music anchor interpretation, display visual-only boundaries, and provide an exportable/readable sequence handoff showing planned durations without implementing an editor or render pipeline.
6. **Regression and documentation:** test old-project initialization, 10-active/26-inactive-style manifests, visual-only insertion/reordering, narration editing and playback, old visual results, music migration, malformed files, and narrow/keyboard-accessible UI. Update the workflow guide and tool README only when implementation lands.

## Acceptance checks

- A new or migrated project shows narration and visual-only units together in one ordered rail, and every unit has an editable required planned duration.
- `narration_manifest.json` still contains only real spoken segments; no blank-text workaround is needed.
- A visual-only unit can have multiple requests/candidates in each whole-video visual take, with optional candidate-specific SFX. Existing narration visual requests remain intact.
- Music can start or end on a visual-only unit; existing narration-anchored items retain their meaning after migration.
- Stable IDs survive reordering and renaming. Missing/invalid cross-references are reported, not silently repaired or dropped.
- SAPI/F5 narration previews remain usable and are accurately described as speech-only. VPS still does not assemble the final video or execute visual renderers.
- No legacy project JSON, media, generated audio, or exports are deleted as part of migration.

## Boundaries and related documents

This is a planned change, not a claim that the workbench or existing JSON already supports visual-only units. Do not implement the schema, migration, UI, or project-file edits in this task-order pass. Exact frame timing, audio mixing, NLE integration, and final render are separate production work.

- [Video Production Workflow](../../guides/VIDEO_PRODUCTION_WORKFLOW.md)
- [Segment Layers and Workbench Layout](TASK-ORDER_SEGMENT_LAYERS_AND_WORKBENCH_LAYOUT.md)
- [Narration workbench guide](../../tools/audio_narration_generator/README.md)
- [Visual take schema](../../tools/audio_narration_generator/visual_take.schema.json)
- [Music manifest schema](../../tools/audio_narration_generator/music_manifest.schema.json)
