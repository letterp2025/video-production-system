# Task Order: Workbench Layer Tabs

**Task ID:** WLT-001 | **Status:** Implemented | **Last updated:** 2026-11-23

## Implementation record

- Added four top-level layer tabs for the selected beat. Scratchpad and F5-TTS remain nested within Script and Narration Layer.
- Moved recipe selection, visual-plan creation/opening, and plan status into Visual Layer. The global header now holds project context and narration playback only.
- Music Layer and SoundEffects Layer show the selected beat and expose the create/open/status workflow for their per-beat JSON mappings. The JSON files open in the default editor; in-app cue editing and audio composition are not implemented.
- Added arrow-key, Home, and End tab navigation with selected-tab semantics. The narrow layout changes from four columns to two and then one.
- Updated the workbench guide to describe the new navigation. Automated tests were not run for this task.

## Objective

Organize the selected beat's editing workspace around four top-level production layers. Nest the existing **Scratchpad** and **F5-TTS** tabs inside **Script and Narration Layer**, and provide separate top-level tabs named **Visual Layer**, **Music Layer**, and **SoundEffects Layer**. This gives each layer a dedicated place and removes per-beat visual controls from the crowded global header.

This task defines the workbench navigation and layout. The larger scope for music/SFX JSON mappings and their boundaries is in the [Segment Layers and Workbench Layout task order](TASK-ORDER_SEGMENT_LAYERS_AND_WORKBENCH_LAYOUT.md).

## Intended navigation

```text
Selected beat
├── Script and Narration Layer
│   ├── Script editor and narration controls
│   ├── Scratchpad
│   └── F5-TTS
├── Visual Layer
├── Music Layer
└── SoundEffects Layer
```

The left beat list remains the shared selector. Switching a top-level tab changes which layer workspace is shown for that same selected beat; selecting another beat updates every layer view to that beat. The existing Scratchpad and F5-TTS controls remain nested views within Script and Narration Layer and retain their current behavior.

## User workflow

1. Select a beat from the existing sequence list.
2. Select **Script and Narration Layer** to edit the segment title and spoken words, use playback, open **Scratchpad**, or open **F5-TTS** for takes and delivery settings.
3. Select **Visual Layer** to view/select a whole-spine visual take and inspect its entry for this beat; the older per-beat plan workflow remains available under a legacy disclosure.
4. Select **Music Layer** or **SoundEffects Layer** to view mapping status or create/open that beat's corresponding JSON file.
5. Switch layers or beats. Each workspace reflects the current selection and reports whether its data is missing, saved, needs review, or invalid as applicable.

## Layout requirements

- Show the four top-level layer tabs together in a consistent, easy-to-find navigation area associated with the selected-beat workspace.
- Place **Scratchpad** and **F5-TTS** as subordinate tabs or equivalent clearly nested navigation inside **Script and Narration Layer**. They must not appear as peer tabs beside the four layer tabs.
- Keep the beat sequence visible during layer navigation so users can move between segments without losing their place.
- Move the per-beat visual recipe selector, create/open action, and status out of the global top bar and into **Visual Layer**. Keep global project identity and narration transport controls available without adding per-layer creation controls to the header.
- Keep each layer's project data associated by stable segment ID, independent of beat order. A layer with no file should have a clear empty state and should not prevent access to other layers.
- Retain current script editing, SAPI/F5-TTS playback, Scratchpad notes and suggestions, take review, and visual-plan creation/opening behavior.
- Make selected and nested tab state clear, keyboard accessible, and announced to assistive technology. Preserve focus visibility and provide sensible focus behavior when switching tabs or beats.
- At narrow widths, allow secondary panels to stack or collapse while retaining access to the top-level layers, the selected beat, and the active layer's primary controls. Test at the supplied screenshot's desktop size and at narrower widths.

## Data ownership

| Workspace | Data source |
|---|---|
| Script and Narration Layer | Existing project `audio/narration_manifest.json`, selected narration takes, and temporary work queue |
| Visual Layer | Canonical project-root `visual_layer/<take-id>.json` whole-spine manifests; earlier `audio/visuals/<segment-id>.json` plans remain available as legacy |
| Music Layer | Optional project `audio/music/<segment-id>.json` cue mapping |
| SoundEffects Layer | Optional project `audio/sfx/<segment-id>.json` cue mapping |

Tabs are navigation only; they do not create a second source of truth. Each layer reads and writes only its own data using the safety and validation rules in its owning task order.

## Implementation phases

1. **Navigation structure:** establish four top-level layer workspaces and nest Scratchpad/F5-TTS under Script and Narration Layer. Keep current actions intact while moving the visual controls into Visual Layer.
2. **Layer integration:** connect Visual Layer to whole-spine take selection/status and retain legacy per-beat plans. Connect Music and SoundEffects to their per-segment JSON create/open/status workflows as specified in the segment-layers task order.
3. **Responsive and accessibility pass:** verify tab hierarchy, selected states, focus management, keyboard operation, and narrow-window behavior.
4. **Regression coverage and docs:** test layer/beat switching, retained nested tab behavior, existing script/audio functions, visual plans, and the music/SFX integration when available. Update the workbench guide with the implemented navigation.

## Acceptance checks

- The four top-level tabs appear with the requested labels: **Script and Narration Layer**, **Visual Layer**, **Music Layer**, and **SoundEffects Layer**.
- **Scratchpad** and **F5-TTS** are visible only within the Script and Narration Layer workspace as subordinate navigation.
- The selected beat remains apparent and consistent when switching among layers; all displayed data belongs to its stable segment ID.
- Visual take selection and selected-beat status live in Visual Layer, with the legacy per-beat plan workflow available there; the global header has no per-beat creation controls.
- Existing narration editing, playback, Scratchpad, take review, and visual-plan operations continue to work.
- Music and SoundEffects workspaces provide clear empty states and create/open/status for their own selected-beat JSON mapping; neither searches for assets nor plays/mixes audio.
- The navigation works with keyboard and assistive technology and remains usable at desktop and narrow viewport sizes.

## Boundaries

- Do not change the narration manifest model or duplicate script/audio data for tab navigation.
- Do not make top-level tab switching modify, delete, or implicitly create layer files.
- Music/SFX cue schemas and file operations remain governed by the segment-layers task order; this document does not define an audio mixer or asset search integration.
- The Visual Layer remains a plan workflow until a separate rendering task adds preview or animation execution.

## Related documents

- [Segment Layers and Workbench Layout](TASK-ORDER_SEGMENT_LAYERS_AND_WORKBENCH_LAYOUT.md)
- [Visual Animation Plans Per Segment](TASK-ORDER_VISUAL_ANIMATION_PER_SEGMENT.md)
- [Narration workbench guide](../../tools/audio_narration_generator/README.md#segment-layers)
