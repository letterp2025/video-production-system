# Task Order: Segment Layers and Workbench Layout

**Task ID:** SLW-001 | **Status:** Planned | **Last updated:** 2026-11-23

## Objective

Treat each stable narration segment as a four-layer production unit: (1) script text and narration audio, (2) visual, (3) music, and (4) sound effects (SFX). Add simple, editable JSON mappings for the last two layers, and give the workbench room to manage all four without packing more controls into its top bar. This task order describes future implementation; no music/SFX mapping or layout change is shipped yet.

## Current state and boundaries

- The narration manifest owns segment ID, spoken order, approved text, status, voice settings, and take selection. The workbench already edits and previews these.
- The visual layer has an optional, per-segment JSON plan in `audio/visuals/<segment-id>.json`. It is planning data, not a rendered animation.
- Music and SFX have no per-segment mapping, editor, or playback integration yet. The [Asset Finder](../../tools/asset_finder/README.md) can search and download audio with a source/license receipt, but it is not integrated into the workbench and does not make a licensing decision.
- The current top bar contains project identification, two narration playback buttons, volume, and the visual planner. The screenshot shows that space is already tight. Do not add music and SFX controls to that row.

## User workflow

1. Select a beat in the left-hand sequence. Its stable ID, not its position, associates all four layers; reordering beats preserves their mappings.
2. Edit approved words and narration audio in the existing script/audio workflow. Open the visual layer to see or create its existing plan.
3. Open **Music** or **SFX** for the selected beat. Create that layer's JSON only when needed, then map one or more project-local audio assets to cues. Empty/missing mappings are normal and visible.
4. Review the source and license of any candidate asset separately. The initial mapping workflow accepts paths to already-reviewed project assets; finding and downloading them can continue through Asset Finder outside the workbench.
5. Switch beats and see the correct status and mapping for each layer. If approved text changes, keep existing mappings and flag any text-dependent cue for review rather than silently retiming or deleting it.

## Data ownership and proposed storage

| Layer | Source of truth | Initial scope |
|---|---|---|
| Script text + narration audio | Project `audio/narration_manifest.json` and its selected take files | Existing behavior; no duplicate script/audio JSON |
| Visual | Project `audio/visuals/<segment-id>.json` | Existing optional plan |
| Music | Project `audio/music/<segment-id>.json` | New optional cue mapping |
| SFX | Project `audio/sfx/<segment-id>.json` | New optional cue mapping |

Music and SFX files should be small, versioned, and independently editable. Each records the segment ID, approved-text hash captured at creation or last explicit review, and a list of cues. A cue maps a **project-relative asset path** to a start offset in the segment, with optional trim, duration, and gain fields only when their timing semantics are defined and validated. Permit multiple cues and an empty list. For Asset Finder downloads, retain source/attribution/license metadata in the neighboring `.asset.json` receipt; manually sourced assets need equivalent provenance. The mapping may reference that record but must not pretend it proves usage rights. Never put machine-specific absolute paths or media files in this public repository. The schema and folder names above are the proposed first-version contract, to be finalized before implementation.

The initial workbench only needs a create/open/status workflow for these JSON files, akin to the visual plan. It must not automatically mix music/SFX into the narration review track, trigger asset search/download, or claim a final video mix exists. Later audio composition must define timing, overlap, fades, loudness, and how cue positions respond to narration-length changes before rendering is added.

## Workbench layout requirements

- Keep the top bar for global context and transport. Move the existing visual-plan selector/create/status out of it as part of the layout change; do not duplicate the control in two places.
- Add a clearly labeled layer workspace for the selected beat. The top-level tabs and their nesting are specified in the [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md). Preserve the always-visible beat list and a readable script editor at desktop sizes.
- Show the selected beat ID/title and each layer's state (for example, missing, saved, needs review, invalid) in one consistent place. A create action must say which beat and layer it affects.
- On narrower windows, collapse or stack secondary panels instead of shrinking the editor or forcing the top bar into a single crowded line. Keyboard navigation, focus visibility, labels, and status announcements must remain usable.
- Avoid a wholesale redesign of the existing visual style. Validate the layout at the screenshot-sized desktop viewport and at narrower widths, with long project names and long beat titles.

## Implementation phases

1. **Contracts:** finalize music/SFX version-1 schemas, relative asset-path boundary, cue timing units, stale-text policy, file-size limits, and explicit non-overwrite behavior. Keep visual schema unchanged unless a separate migration is justified.
2. **Project APIs:** add safe, project-confined create/read/open/status operations for music and SFX, with atomic creation and current-manifest hash checks. Separate layer behavior into appropriately sized modules rather than growing the workbench entry point.
3. **Workbench layout:** move visual controls into the selected-beat Layers workspace; add music/SFX create/open/status views. Keep playback, narration editing, Scratchpad, and F5-TTS functional. Handle missing, invalid, and stale layer files visibly.
4. **Tests and docs:** cover switching/reordering beats, duplicate create, invalid IDs, path traversal/symlinks, malformed or oversized JSON, concurrent manifest edits, accessibility and responsive layout. Update user documentation with the actual schema and workflow.
5. **Later composition:** only after cue semantics and a renderer/mixer are specified, consider synchronized preview and final audio/video assembly. Do not fold this into the initial mapping task.

## Acceptance checks

- One beat can have any combination of the four layers; missing optional JSON is not an error. Every visible layer action targets the selected beat.
- Music and SFX JSON files validate against their own versioned schemas, contain only project-relative asset references, and neither overwrite existing files nor change narration/visual data.
- Reordering beats preserves mappings by stable ID. Editing spoken text leaves mappings intact and gives a clear review signal for affected cues.
- Existing script editing, SAPI/F5-TTS playback, visual-plan creation/opening, Scratchpad, and take review remain usable after the layout change.
- The desktop top bar has no per-beat layer creation controls; the selected-beat workspace remains usable at narrow widths with keyboard and screen-reader labels.
- Tests establish that no music/SFX mapping action downloads media, runs Asset Finder, mixes audio, or renders video.

## Related documents

- [Visual animation per-segment task order](TASK-ORDER_VISUAL_ANIMATION_PER_SEGMENT.md)
- [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md)
- [Narration workbench guide](../../tools/audio_narration_generator/README.md#segment-layers)
- [Asset Finder](../../tools/asset_finder/README.md)
