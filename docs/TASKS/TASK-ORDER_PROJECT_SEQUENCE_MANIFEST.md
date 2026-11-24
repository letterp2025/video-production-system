# Task Order: Project Sequence Manifest

**Task ID:** PSM-001 | **Status:** Implemented, regression-tested, and smoke-checked against an existing video project | **Last updated:** 2026-11-24

## Objective

Give the video project one canonical ordered story sequence that can include narration-linked units and visual-only units. Keep approved speech in `audio/narration_manifest.json`, while `sequence_manifest.json` owns story order and editable planned durations. VPS remains a brainstorming and asset-preparation workspace; the selected non-linear editor (NLE) assembles and renders the final video.

## Problem addressed

The narration manifest must contain real spoken segments, so it cannot represent a silent opening, pause, montage, or outro. Using it as the only video order also made it impossible to anchor visuals and project-wide music to a visual-only interval. The sequence manifest now provides that shared story order without adding empty narration placeholders or duplicating approved script text.

`video_project.json` remains the creative brief and manually maintained status record. Whole-video visual takes remain alternative treatments of the sequence; they do not own competing story orders.

## Current user workflow

1. On workbench startup, VPS loads the project-root `sequence_manifest.json`. If it is absent, VPS creates it from every narration segment in its current order, preserving each narration ID. A malformed existing file is reported and left untouched.
2. Use the shared Sequence rail to select and move narration-linked or visual-only units. Their stable IDs remain visible. The sequence order is the video story order; narration playback contains only speech.
3. Add a visual-only unit for a silent opening, pause, montage, transition, or outro. Give it a unique ID, title, editable planned duration, and optional editorial note. It creates no narration text or audio take. A new visual-only unit starts at three seconds.
4. Edit a narration-linked unit's text and title in Script and Narration. Edit its planned duration in the sequence. The selected WAV length supplies an initial duration when available; otherwise VPS uses a word-count estimate. Later audio changes do not silently replace a duration the user has edited.
5. In Visual Layer, create or select a whole-video take and make repeatable visual requests for either kind of sequence unit. Narration-linked requests retain their text-based source hash. Visual-only requests use a hash derived from the unit's title, note, and planned duration. Optional candidate-specific SFX stays beside its visual request.
6. In Music Layer, create or edit project-wide music items. The existing `start_segment_id` and `end_segment_id` field names now refer to sequence-unit IDs, including visual-only units. VPS displays the boundary IDs, titles, and positions.
7. Prepare the narration, selected visual exports, music and SFX references, sequence order, and planned durations for the chosen NLE. LOW is an optional preview. A reviewed HIGH render from the NLE is the final video.

## Data ownership and storage

| File | Current responsibility |
|---|---|
| Project-root `sequence_manifest.json` | Canonical ordered story units, stable IDs, unit kind, and required planned duration. It does not store approved narration text, media, or an NLE edit track. |
| `audio/narration_manifest.json` | Approved spoken words, narration settings/takes, and speech-only order. Narration units link to matching stable narration IDs. |
| Project-root `video_project.json` | Creative identity, rough narration outline, inspirations, and manually maintained project status. |
| `visual_layer/<take-id>.json` and request folders | Alternative whole-video visual directions and candidate requests/results keyed by sequence-unit ID. `visual_layer/selected_take.json` stores take selection. |
| `audio/music/manifest.json` | Project-wide music items with start and end sequence-unit references. |
| `sfx.json` inside a visual request | Optional sound-effect plan associated with that specific visual candidate. |

Example project layout (workbench-created files appear as the relevant work begins):

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
            |-- opening-card/          # visual-only sequence-unit ID
            |   `-- requests/VIS-001/
            |       |-- request.json
            |       `-- result.json
            `-- found-effectcraft/     # narration-linked sequence-unit ID
                `-- requests/VIS-001/
                    |-- request.json
                    `-- result.json
```

## Sequence contract and behavior

The implemented format is defined in [`sequence_manifest.schema.json`](../../tools/audio_narration_generator/sequence_manifest.schema.json). A minimal example:

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
    }
  ]
}
```

- Array order is story order. Unit IDs are unique across both kinds. A narration unit uses the same ID as its `narration_segment_id`; a visual-only unit must not collide with a narration ID.
- Every unit requires a finite, positive `duration_seconds` no greater than 86,400 seconds. Durations are planning targets, not frame-accurate timings or promises about final rendered length.
- A narration unit's title and spoken text come from the linked narration manifest. A visual-only unit owns its title and optional note. Approved words are never copied into the sequence file.
- Initial migration includes every narration record, including inactive and deleted records, so existing IDs and visual mappings are retained. New narration beats created in the workbench are linked to the sequence. Narration added outside the workbench appears as unlinked until the user explicitly links it.
- Moving narration units also updates narration playback order when every narration segment is linked. If sequence and narration orders diverge, VPS reports the mismatch and requires explicit reconciliation before narration playback. It does not discard sequence units to repair the mismatch.
- A malformed existing sequence is reported without replacement. The initializer only creates the file when it is absent.
- Existing per-segment music/SFX files and old `audio/visuals/` plans are left untouched; they are not imported into the current layer workflow.

## Verification record

- Python workbench regression suite and JavaScript browser-interaction suite pass, including sequence initialization, adding and moving visual-only units, narration-order reconciliation, music anchors, visual request behavior, and collision protection between narration and visual-only IDs.
- A smoke check confirmed that the workbench loaded an existing sequence manifest and reconciled its narration links without an ordering conflict. Project-specific details are intentionally omitted.
- Request/result schema versions, project-relative path validation, and non-destructive handling of malformed manifests are documented in the [workbench README](../../tools/audio_narration_generator/README.md) and [workflow guide](../../guides/VIDEO_PRODUCTION_WORKFLOW.md).

## Deferred work and boundaries

The sequence is an asset-planning handoff, not an NLE timeline or edit decision list. Frame-accurate timing, transitions, audio mixing, and final assembly/rendering remain with the chosen NLE. LOW rendering is optional; HIGH rendering and review are required to complete a video project. Testing how the prepared assets move into a chosen NLE belongs to a separate end-to-end production pilot.

## Related documents

- [Video Production Workflow](../../guides/VIDEO_PRODUCTION_WORKFLOW.md)
- [Segment Layers and Workbench Layout](TASK-ORDER_SEGMENT_LAYERS_AND_WORKBENCH_LAYOUT.md)
- [Narration workbench guide](../../tools/audio_narration_generator/README.md)
- [Sequence manifest schema](../../tools/audio_narration_generator/sequence_manifest.schema.json)
- [Visual take schema](../../tools/audio_narration_generator/visual_take.schema.json)
- [Music manifest schema](../../tools/audio_narration_generator/music_manifest.schema.json)
