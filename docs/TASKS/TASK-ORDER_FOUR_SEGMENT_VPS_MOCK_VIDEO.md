# Task Order: Four-Segment VPS Mock Video

**Task ID:** E2E-001 | **Status:** Planned | **Last updated:** 2026-11-23

## Objective

Run a small mock video project from the initial idea through a reviewed final video to learn how the current narration, visual, music, SFX, and rendering workflows fit together in practice.

The video will explain what the Video Production System (VPS) is in exactly four narration segments. Use EffectCraft as the sole visual renderer for all four segments in this pilot. The required outcome is a final-quality video in `render/HIGH/`; a `render/LOW/` preview is optional.

This is a workflow pilot, not a promise that the workbench already joins every layer automatically. Record the actual handoffs, manual steps, timing assumptions, and failures. Do not generalize a pilot-only workaround into VPS behavior without a separate approved implementation task.

## User workflow

1. Start from the user's direction, “describe what VPS is.” Codex drafts a rough four-part narration outline, then expands it into four coherent spoken segments. Review the story order and wording together before treating the text as ready for narration.
2. Create the mock project under `test/mock-vps-introduction/`. Use four stable segment IDs in `audio/narration_manifest.json`; that manifest remains the source of truth for spoken text and selected narration takes.
3. Open the project in the existing narration workbench. Use SAPI for a quick wording/pacing preview where available, generate F5-TTS takes, listen to alternate takes and the assembled narration, revise as needed, and select the takes for assembly.
4. Create one whole-spine visual take, `visual_layer/v_layer_1.json`, mapping all four stable segment IDs to custom EffectCraft work. Keep the same renderer for every segment; do not introduce Manim or GSAP in this pilot.
5. Use Asset Finder to source at least one suitable music bed and one SFX. Codex selects candidate assets, checks the source and usage terms, keeps the source receipts with the project, and writes the existing per-segment cue maps. The music should be audible across the four-segment video; place at least one SFX cue at an intentional narration moment.
6. Render the EffectCraft visuals and assemble/mux the selected narration with the mapped music and SFX using the existing tools and clearly recorded project-specific steps. Check segment boundaries and cue timing against the actual assembled narration; do not assume the workbench performs this composition.
7. Optionally create a fast `LOW` preview and review it. Make any needed revisions, then create and review the required `HIGH` final export.
8. Record what worked, what required manual intervention, and what capability would need a separate implementation task before another project could follow the same path reliably.

## Four-segment story target

The exact wording is developed during the pilot. The four segments should cover these ideas without implying capabilities that do not exist:

1. **The purpose:** VPS is a project-centered system for developing a video from its spoken story toward a final render.
2. **The narration spine:** stable segments hold the approved spoken words and connect narration takes to the rest of the project.
3. **The production layers:** each segment can be associated with visuals, music, and sound effects; visual takes span the narration spine and can point to custom project work.
4. **The current boundary and outcome:** the workbench organizes project data, while renderer execution and final layer assembly still require production tools and explicit handoffs; a finished project needs a reviewed HIGH render.

Keep this as a short explainer suitable for testing timing and joins, not a feature-complete product commercial.

## Project location and illustrative structure

```text
test/
└── mock-vps-introduction/
    ├── README.md                         # pilot status, commands, decisions, and findings
    ├── PRODUCTION_NOTES.md               # rough outline and workflow observations; not script source of truth
    ├── audio/
    │   ├── narration_manifest.json       # canonical four-segment text and selected narration takes
    │   ├── segments/                     # generated per-segment WAV takes (local/ignored)
    │   ├── assembled/                    # assembled narration review audio (local/ignored)
    │   ├── performance/                  # generation receipts (local/ignored)
    │   ├── music/<segment-id>.json       # music cue map(s) covering the pilot timeline
    │   └── sfx/<segment-id>.json         # SFX cue map(s), including at least one cue
    ├── visual_layer/
    │   ├── selected_take.json
    │   ├── v_layer_1.json                 # one visual direction covering all four segment IDs
    │   └── v_layer_1/
    │       ├── segments/<segment-id>/     # custom project-specific visual work
    │       └── effectcraft/               # EffectCraft project and section/timing inputs
    ├── assets/audio/
    │   ├── music/                         # selected local music and source receipts
    │   └── sfx/                           # selected local SFX and source receipts
    └── render/
        ├── LOW/                           # optional fast preview (local/ignored)
        └── HIGH/                          # required final-quality video (local/ignored)
```

This is a target layout, not a requirement to create empty folders. Create folders when that work begins. Follow the EffectCraft project format where its native files require a different internal arrangement. The narration manifest owns the spoken text; `PRODUCTION_NOTES.md` is for the outline and observations, not a competing script.

## Data ownership and handoffs

| Concern | Pilot source of truth | Handoff to final video |
|---|---|---|
| Spoken script and selected takes | `audio/narration_manifest.json` plus generated take files | Existing narration generator assembles selected active takes into review audio. |
| Visual direction and segment mapping | `visual_layer/v_layer_1.json` and referenced EffectCraft work | The pilot must explicitly connect the four entries to the EffectCraft composition/sections; the workbench does not execute them. |
| Music and SFX choices | Per-segment JSON maps under `audio/music/` and `audio/sfx/` | Source assets and cue offsets must be turned into a soundtrack by an explicit production step; the workbench does not search, download, play, or mix them. |
| Asset source details | Asset Finder receipts stored beside project assets | Review source and usage terms before using an asset; a receipt is provenance information, not a rights grant. |
| Final output | `render/LOW/` (optional) and `render/HIGH/` (required) | EffectCraft Section Renderer can render/join EffectCraft sections and optionally mux one audio file. Any preparation/mixing of the final audio track must be documented. |

Music/SFX cue `start_seconds` values are relative to their narration segment. The pilot must establish and record how segment-relative cues are translated onto the assembled timeline, including pauses/crossfades and actual selected-take durations. If the current manifests/tools do not provide enough information to do that reliably, document the gap and the exact pilot workaround; do not silently claim automatic synchronization.

## Boundaries

- Exactly four active narration segments, one whole-spine visual take, and one renderer: EffectCraft.
- No production-channel content, private voice references, credentials, or absolute machine-specific paths in tracked pilot files.
- No Manim/GSAP comparison, reusable renderer framework, generic project orchestrator, new workbench integration, or schema redesign in this task.
- Do not describe the workbench as automatically rendering or mixing the layers; test and document actual behavior.
- Use Asset Finder to source at least one music bed and one SFX for the pilot, and review their source/usage terms. Do not assume an asset is cleared merely because it can be downloaded.
- Generated narration, audio/video assets, EffectCraft binary project files, caches, intermediates, and renders may be ignored by repository rules. Do not force-add generated or large media to Git. Verify ignore behavior before production and keep only suitable, portable manifests, code, notes, and receipts tracked.
- Do not make HIGH rendering optional: `LOW` is optional; a completed pilot requires a reviewed final `HIGH` export.

## Implementation phases

1. **Create the four-segment pilot skeleton:** add the mock project README and production notes, draft the four-part outline, create the project-local narration manifest, and confirm the workbench opens the intended project.
2. **Complete narration:** revise wording, generate/review takes, select the takes, assemble the narration, and record the accepted text and listening decisions.
3. **Implement one visual take in EffectCraft:** map every segment by stable ID, build custom visuals, define section timing, and verify that visual duration follows the selected narration timeline.
4. **Map and source the sound layers:** select a music bed and at least one SFX through Asset Finder, preserve source receipts, create the needed cue maps, and produce a combined audio file using documented steps.
5. **Render and review:** optionally render LOW for fast feedback; render HIGH as the final deliverable; verify video, audio, segment joins, cue placement, and the final file's streams and duration.
6. **Write pilot findings:** update the project README with commands, tool versions/configuration that are safe to share, timing decisions, manual handoffs, known limitations, and prioritized follow-up task-order candidates. Keep private paths and raw records out of tracked notes.

## Acceptance checks

- The tracked pilot project begins with the stated VPS explainer goal and has exactly four active, uniquely identified narration segments.
- The narration workbench opens this project; the chosen segment takes and assembled narration can be reviewed, and revisions are reflected in the final selected narration.
- A single `v_layer_1` manifest maps all four narration IDs, and all four visual sections use EffectCraft only.
- At least one music cue and one SFX cue validate against current schemas, point to project-local assets, and have source/usage details reviewed. The music is heard across the video, the SFX lands at its intended segment moment, and the pilot records how cue offsets align to segment and assembled-audio timing.
- A complete video is rendered to `render/HIGH/` and watched/listened to from beginning to end. It contains all four segments in order, synchronized narration, intended visuals, music, and SFX without missing media, unintended silence/cutoffs, or audible clipping.
- The HIGH output passes the available FFprobe/decoder validation and its duration, dimensions, frame rate, and audio presence are recorded in the project notes. `LOW` may be omitted.
- The project notes clearly distinguish automated behavior from manual steps and identify any blocking gap for repeatable production.
- Generated media remains ignored/untracked; staged paths contain only intentional, reviewable pilot documentation/data/code and no private paths or oversized artifacts.

## Related documents

- [Video Production Workflow](../../guides/VIDEO_PRODUCTION_WORKFLOW.md)
- [Segment Layers and Workbench Layout](TASK-ORDER_SEGMENT_LAYERS_AND_WORKBENCH_LAYOUT.md)
- [Audio Narration Generator](../../tools/audio_narration_generator/README.md)
- [EffectCraft Section Renderer](../../tools/effectcraft_ffmpeg_sections/README.md)
- [Asset Finder](../../tools/asset_finder/README.md)
