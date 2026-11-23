# Task Order: Segment Layers and Workbench Layout

**Task ID:** SLW-001 | **Status:** Planned | **Last updated:** 2026-11-23

## Objective

Treat each stable narration segment as a four-layer production unit: (1) script text and narration audio, (2) visual, (3) music, and (4) sound effects (SFX). Give the workbench room to manage all four without packing more controls into its top bar. The four-tab navigation is already shipped by the [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md); this task covers the consolidated visual-layer manifest and future music/SFX JSON mappings, not a new navigation redesign.

## Current state and boundaries

- The narration manifest owns segment ID, spoken order, approved text, status, voice settings, and take selection. The workbench already edits and previews these.
- The current visual-plan feature stores one optional plan per segment at `audio/visuals/<segment-id>.json`. It is planning data, not a rendered animation. The target architecture in this task replaces those separate plan files as the visual layer's index with one project-level manifest at `audio/visuals/visual_manifest.json`.
- Each visual-manifest entry maps a stable narration segment ID to one selected renderer: `effectcraft`, `manim`, or `gsap`. Renderer-specific implementations may be EffectCraft-supported data, Python files, or JavaScript files, organized in engine-specific folders and referenced with project-relative paths. A library-recipe reference may be used instead of a project-specific source file.
- The existing visual plan remains useful as optional renderer-neutral intent (for example, a description, timing notes, recipe reference, and source-text hash). It is supporting metadata inside the visual-manifest entry, not a required first step, a renderer choice, or a second per-segment manifest. A segment may be assigned a renderer without a plan, or hold a plan before its renderer is chosen.
- Music and SFX have no per-segment mapping, editor, or playback integration yet. The [Asset Finder](../../tools/asset_finder/README.md) can search and download audio with a source/license receipt, but it is not integrated into the workbench and does not make a licensing decision.
- The current top bar contains project identification and narration playback controls. Per-beat visual controls now live under **Visual Layer**; do not add music or SFX controls to the global top bar.

## User workflow

1. Select a beat in the left-hand sequence. Its stable ID, not its position, associates all four layers; reordering beats preserves their mappings.
2. Edit approved words and narration audio in the existing script/audio workflow. In **Visual Layer**, add or edit the selected segment's entry in the shared visual manifest and choose EffectCraft, Manim, or GSAP when an engine is known. Attach optional plan details when they help describe intent; renderer selection and implementation references do not depend on creating a plan first.
3. Open **Music** or **SFX** for the selected beat. Create that layer's JSON only when needed, then map one or more project-local audio assets to cues. Empty/missing mappings are normal and visible.
4. Review the source and license of any candidate asset separately. The initial mapping workflow accepts paths to already-reviewed project assets; finding and downloading them can continue through Asset Finder outside the workbench.
5. Switch beats and see the correct status and mapping for each layer. If approved text changes, keep existing mappings and flag any text-dependent cue for review rather than silently retiming or deleting it.

## Data ownership and proposed storage

| Layer | Source of truth | Initial scope |
|---|---|---|
| Script text + narration audio | Project `audio/narration_manifest.json` and its selected take files | Existing behavior; no duplicate script/audio JSON |
| Visual | Project `audio/visuals/visual_manifest.json`, keyed by stable narration segment ID | One project-level mapping for renderer selection and implementation reference; optional plan metadata may live on the same entry |
| Music | Project `audio/music/<segment-id>.json` | New optional cue mapping |
| SFX | Project `audio/sfx/<segment-id>.json` | New optional cue mapping |

The visual manifest should contain a version and a `segments` object keyed by the exact stable IDs from `narration_manifest.json`. Each entry identifies one renderer (`effectcraft`, `manim`, or `gsap`) and may reference either a reusable library recipe or a renderer-specific project file. Project-file references are relative to the video project, never absolute machine paths. Keep engine code/data in separate, organized files rather than embedding large programs in the manifest. A missing entry means that segment has no visual assignment. A plan may be embedded as optional metadata on the entry; preserve its source-text hash so text changes can be flagged for review. The exact schema, library-reference rules, engine-specific file conventions, and status values are finalized before implementation.

For illustration only, a visual entry could look like this:

```json
{
  "schema_version": 1,
  "segments": {
    "opening-hook": {
      "renderer": "gsap",
      "implementation": {
        "kind": "project_file",
        "path": "audio/visuals/gsap/opening-hook/scene.js"
      },
      "plan": {
        "description": "Reveal the opening title.",
        "source_text_sha256": "<hash of approved spoken words>"
      }
    }
  }
}
```

The example is illustrative, not the final schema. Renderer-specific files can use `.js`, `.py`, or the supported EffectCraft format; they remain ordinary project assets referenced by the manifest. Do not copy external tool installations or machine-specific paths into the project. A plan-only entry may omit the renderer and implementation until the creator chooses an engine.

Music and SFX files should be small, versioned, and independently editable. Each records the segment ID, approved-text hash captured at creation or last explicit review, and a list of cues. A cue maps a **project-relative asset path** to a start offset in the segment, with optional trim, duration, and gain fields only when their timing semantics are defined and validated. Permit multiple cues and an empty list. For Asset Finder downloads, retain source/attribution/license metadata in the neighboring `.asset.json` receipt; manually sourced assets need equivalent provenance. The mapping may reference that record but must not pretend it proves usage rights. Never put machine-specific absolute paths or media files in this public repository. The schema and folder names above are the proposed first-version contract, to be finalized before implementation.

The current per-segment visual plans are an implemented predecessor, documented in [Visual Animation Plans Per Segment](TASK-ORDER_VISUAL_ANIMATION_PER_SEGMENT.md). Migration or compatibility handling must preserve those files and their metadata; importing them into the shared manifest must be safe, explicit or idempotent, and non-destructive. After migration, the shared manifest is the canonical visual-layer assignment source, avoiding competing renderer selections across separate plan files.

The initial workbench only needs a create/open/status workflow for these JSON files, akin to the visual plan. It must not automatically mix music/SFX into the narration review track, trigger asset search/download, or claim a final video mix exists. Later audio composition must define timing, overlap, fades, loudness, and how cue positions respond to narration-length changes before rendering is added.

## Workbench layout requirements

- Keep the top bar for global context and narration transport. The visual controls already live in **Visual Layer**; evolve them to use the shared visual manifest without restoring per-beat controls to the header. Do not duplicate the source of truth across plan files and manifest entries.
- Add a clearly labeled layer workspace for the selected beat. The top-level tabs and their nesting are specified in the [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md). Preserve the always-visible beat list and a readable script editor at desktop sizes.
- Show the selected beat ID/title and each layer's state (for example, missing, saved, needs review, invalid) in one consistent place. A create action must say which beat and layer it affects.
- On narrower windows, collapse or stack secondary panels instead of shrinking the editor or forcing the top bar into a single crowded line. Keyboard navigation, focus visibility, labels, and status announcements must remain usable.
- Avoid a wholesale redesign of the existing visual style. Validate the layout at the screenshot-sized desktop viewport and at narrower widths, with long project names and long beat titles.

## Implementation phases

1. **Contracts:** define the shared visual-manifest schema, renderer enum, library/project-file references, optional embedded plan shape, safe project-relative paths, and non-destructive import of existing visual plans. Finalize music/SFX version-1 schemas, cue timing units, stale-text policy, file-size limits, and explicit non-overwrite behavior.
2. **Project APIs:** add safe, project-confined read/write/open/status operations for the visual manifest, including segment-ID validation and conflict handling. Add equivalent create/read/open/status operations for music and SFX with atomic creation and current-manifest hash checks. Separate layer behavior into appropriately sized modules rather than growing the workbench entry point.
3. **Workbench integration:** connect **Visual Layer** to the shared manifest, show per-segment renderer and plan status, allow selecting EffectCraft, Manim, or GSAP, and preserve the optional planning workflow. Add music/SFX create/open/status views. Keep playback, narration editing, Scratchpad, and F5-TTS functional. Handle missing, invalid, and stale layer data visibly.
4. **Tests and docs:** cover switching/reordering beats, renderer changes, importing existing plans without data loss, invalid IDs, path traversal/symlinks, malformed or oversized JSON, concurrent manifest edits, accessibility, and responsive layout. Update user documentation with the actual schemas and workflow.
5. **Later composition:** only after cue semantics and a renderer/mixer are specified, consider synchronized preview and final audio/video assembly. Do not fold this into the initial mapping task.

## Acceptance checks

- One beat can have any combination of the four layers; missing optional layer entries/files are not an error. Every visible layer action targets the selected beat.
- One project-level visual manifest maps entries to the exact stable segment IDs in `narration_manifest.json`; reordering narration never changes those associations.
- A visual entry can select EffectCraft, Manim, or GSAP and reference an organized project file or reusable library recipe. The optional renderer-neutral plan can be kept with that entry but is not a prerequisite for choosing an engine.
- Existing `audio/visuals/<segment-id>.json` plans are preserved and safely imported or supported during migration; migration does not silently overwrite or delete the originals.
- Music and SFX JSON files validate against their own versioned schemas, contain only project-relative asset references, and neither overwrite existing files nor change narration/visual data.
- Reordering beats preserves all layer mappings by stable ID. Editing spoken text leaves mappings intact and gives a clear review signal for visual plans or cues that track the source-text hash.
- Existing script editing, SAPI/F5-TTS playback, visual-plan creation/opening, Scratchpad, and take review remain usable after the layout change.
- The desktop top bar has no per-beat layer creation controls; the selected-beat workspace remains usable at narrow widths with keyboard and screen-reader labels.
- Tests establish that visual mapping does not execute renderer code, and that no music/SFX mapping action downloads media, runs Asset Finder, mixes audio, or renders video.

## Related documents

- [Visual animation per-segment task order](TASK-ORDER_VISUAL_ANIMATION_PER_SEGMENT.md)
- [Workbench Layer Tabs task order](TASK-ORDER_WORKBENCH_LAYER_TABS.md)
- [Narration workbench guide](../../tools/audio_narration_generator/README.md#segment-layers)
- [Asset Finder](../../tools/asset_finder/README.md)
