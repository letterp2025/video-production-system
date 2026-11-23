# Task Order: Four-Segment VPS Mock Video

**Task ID:** E2E-001 | **Status:** Planned — design discussion in progress; not execution-ready | **Last updated:** 2026-11-23

## Objective

Run a small mock video project from the initial idea through a reviewed final video to learn how VPS prepares and organizes assets and edit decisions for a non-linear video editor (NLE).

The video will explain what the Video Production System (VPS) is in exactly four narration segments. Use EffectCraft as the sole visual renderer for all four segments in this pilot. VPS is not the NLE and will not become a video editor or mixer in this task: the selected NLE is where the prepared narration, visual exports, music, and SFX are assembled and the final video is rendered. The required outcome is a reviewed final-quality export in `render/HIGH/`; a `render/LOW/` preview is optional.

This is a workflow pilot, not a promise that the workbench already joins every layer automatically. Record the assets and placement decisions VPS prepares, the handoff to the NLE, manual steps, timing assumptions, and failures. Do not generalize a pilot-only workaround into VPS behavior without a separate approved implementation task.

## User workflow

1. Start from the user's direction, “describe what VPS is.” Codex drafts a rough four-part narration outline, then expands it into four coherent spoken segments. Review the story order and wording together before treating the text as ready for narration.
2. Create the mock project under `test/mock-vps-introduction/`. Use four stable segment IDs in `audio/narration_manifest.json`; that manifest remains the source of truth for spoken text and selected narration takes.
3. Open the project in the existing narration workbench. Use SAPI for a quick wording/pacing preview where available, generate F5-TTS takes, listen to alternate takes and the assembled narration, revise as needed, and select the takes for assembly.
4. Create one whole-spine visual take, `visual_layer/v_layer_1.json`, mapping all four stable segment IDs to custom EffectCraft work. Keep the same renderer for every segment; do not introduce Manim or GSAP in this pilot.
5. Use Asset Finder to source suitable music and SFX assets. Codex selects candidates, checks source and usage terms, and keeps source receipts with the project. Plan music as placements across the project timeline with explicit starts and ends; test how SFX events should be anchored and timed. These are edit instructions and asset references, not a VPS mix.
6. Export the EffectCraft visuals as assets for the NLE. Bring in the selected narration, visual exports, music/SFX assets, and their placement information. Assemble the timeline in the chosen NLE, check segment boundaries and cue timing against the narration, and render the final video there.
7. Optionally create a fast `LOW` preview from the NLE and review it. Make any needed revisions, then create and review the required `HIGH` final export.
8. Record what worked, what required manual intervention, and what asset-management or handoff capability would need a separate implementation task before another project could follow the same path reliably.

## Four-segment story target

The exact wording is developed during the pilot. The four segments should cover these ideas without implying capabilities that do not exist:

1. **The purpose:** VPS is a project-centered system for developing a video from its spoken story toward a final render.
2. **The narration spine:** stable segments hold the approved spoken words and connect narration takes to the rest of the project.
3. **The production layers:** each segment can be associated with visuals, music, and sound effects; visual takes span the narration spine and can point to custom project work.
4. **The current boundary and outcome:** VPS organizes the narration and prepares visual/audio assets and edit decisions; the NLE assembles them into a finished video and produces the reviewed HIGH export.

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
    │   ├── music/manifest.json           # project-wide music placements with explicit start/end
    │   └── sfx/                          # SFX cue plan; organization/timing still to be discussed
    ├── visual_layer/
    │   ├── selected_take.json
    │   ├── v_layer_1.json                 # one visual direction covering all four segment IDs
    │   └── v_layer_1/
    │       ├── segments/<segment-id>/     # custom project-specific visual work
    │       └── effectcraft/               # EffectCraft project and section/timing inputs
    ├── assets/audio/
    │   ├── music/                         # selected local music and source receipts
    │   └── sfx/                           # selected local SFX and source receipts
    ├── nle_handoff/                       # asset list and edit instructions for the chosen NLE
    └── render/
        ├── LOW/                           # optional fast preview (local/ignored)
        └── HIGH/                          # required final NLE export (local/ignored)
```

This is a target layout, not a requirement to create empty folders. Create folders when that work begins. Follow the EffectCraft project format where its native files require a different internal arrangement. The narration manifest owns the spoken text; `PRODUCTION_NOTES.md` is for the outline and observations, not a competing script. The `nle_handoff/` contents and location of the editor's native project depend on the NLE chosen during design discussion.

## Data ownership and handoffs

| Concern | Pilot source of truth | Handoff to final video |
|---|---|---|
| Spoken script and selected takes | `audio/narration_manifest.json` plus generated take files | Existing narration generator assembles selected active takes into review audio. |
| Visual direction and segment mapping | `visual_layer/v_layer_1.json` and referenced EffectCraft work | EffectCraft renders visual assets for import into the NLE; the workbench does not execute them. |
| Music choices and placement | Project-wide `audio/music/manifest.json` plus selected assets | Records which assets to use and when each music cue starts and ends across the project timeline. It is a planning/handoff manifest, not a player or mixer. |
| SFX choices and placement | Project-local SFX cue plan plus selected assets; exact organization remains open | Records the intended event and timing for the NLE handoff. The SFX data shape and time anchors are not finalized by this task order yet. |
| Asset source details | Asset Finder receipts stored beside project assets | Review source and usage terms before using an asset; a receipt is provenance information, not a rights grant. |
| Final output | `render/LOW/` (optional) and `render/HIGH/` (required) | The chosen NLE assembles and renders the final video. VPS prepares assets and instructions; it does not mix or render the finished timeline. |

The music manifest describes placements across the whole project, including exact start and end positions; a cue may span multiple narration segments. The time-coordinate convention is still open: it could use project-timeline time, narration-segment anchors, or a combination. SFX timing/organization is also still under discussion. Do not assume either layer is mixed or rendered by VPS. The pilot should record how its placement instructions are interpreted in the NLE and how revisions to narration affect them.

**Current implementation note:** The workbench's Music Layer currently creates `audio/music/<segment-id>.json`, with cue times relative to that segment and a hash of its spoken text. That is existing prototype behavior, not the whole-project music plan described above. This task order does not claim that the workbench supports `audio/music/manifest.json`; no workbench or schema changes are included here. Decide during the ongoing design discussion whether the pilot should test a simple project-wide music plan manually first or wait for a separate workbench implementation task.

## Design decisions still open before pilot execution

- Which NLE will receive the prepared assets and produce the final video.
- How music start/end positions are represented and anchored to the narration/project timeline.
- Whether SFX uses per-segment files, a project-wide event list, or another simple cue plan, and how exact event timing is recorded.
- Whether EffectCraft supplies one continuous visual export or separate segment exports for the NLE.
- Whether the pilot tests the proposed whole-project music plan as a manual project artifact or follows a separately implemented Music Layer workflow.

These decisions are intentionally left open because the workflow design discussion is still in progress. Resolve them before treating this task order as an execution-ready specification.

## Boundaries

- Exactly four active narration segments, one whole-spine visual take, and one visual renderer: EffectCraft.
- VPS remains an asset-management/planning and handoff workspace. The chosen NLE owns timeline assembly, mixing, and final video rendering.
- No production-channel content, private voice references, credentials, or absolute machine-specific paths in tracked pilot files.
- No Manim/GSAP comparison, reusable renderer framework, generic project orchestrator, NLE integration, or VPS playback/mixing/rendering in this task. Any workbench or schema change needed for whole-project music planning must be discussed and scoped separately.
- Do not describe the workbench as automatically rendering or mixing the layers; test and document actual behavior.
- Use Asset Finder to source music and SFX assets for the pilot, and review their source/usage terms. Do not assume an asset is cleared merely because it can be downloaded.
- Generated narration, audio/video assets, EffectCraft binary project files, caches, intermediates, and renders may be ignored by repository rules. Do not force-add generated or large media to Git. Verify ignore behavior before production and keep only suitable, portable manifests, code, notes, and receipts tracked.
- Do not make HIGH rendering optional: `LOW` is optional; a completed pilot requires a reviewed final `HIGH` export.

## Implementation phases

1. **Create the four-segment pilot skeleton:** add the mock project README and production notes, draft the four-part outline, create the project-local narration manifest, and confirm the workbench opens the intended project.
2. **Complete narration:** revise wording, generate/review takes, select the takes, assemble the narration, and record the accepted text and listening decisions.
3. **Implement one visual take in EffectCraft:** map every segment by stable ID, build custom visuals, define section timing, and verify that visual duration follows the selected narration timeline.
4. **Prepare music and SFX decisions:** select suitable assets through Asset Finder, preserve source receipts, and define the project's music start/end placements and SFX event instructions in the agreed simple data format. Do not implement playback or mixing in VPS.
5. **Hand off and edit in the NLE:** import narration and EffectCraft visual exports, use the music/SFX placements and asset notes, assemble the timeline, and adjust the edit as needed. Record where the handoff was clear or required interpretation.
6. **Render and review:** optionally render LOW in the NLE for fast feedback; render HIGH there as the final deliverable; verify video, audio, segment joins, cue placement, and the final file's streams and duration.
7. **Write pilot findings:** update the project README with commands, selected NLE, safe-to-share tool versions/configuration, timing decisions, manual handoffs, known limitations, and prioritized follow-up task-order candidates. Keep private paths and raw records out of tracked notes.

## Acceptance checks

- The tracked pilot project begins with the stated VPS explainer goal and has exactly four active, uniquely identified narration segments.
- The narration workbench opens this project; the chosen segment takes and assembled narration can be reviewed, and revisions are reflected in the final selected narration.
- A single `v_layer_1` manifest maps all four narration IDs, and all four visual sections use EffectCraft only.
- Music planning identifies the selected asset(s) and exact start/end placements across the project timeline; SFX planning identifies selected asset(s) and intended event timing using the format agreed before execution. Source/usage details are reviewed.
- The selected NLE receives the narration, four-segment EffectCraft visual output, audio assets, and placement instructions. The pilot records any asset or timing details that did not transfer cleanly.
- A complete video is rendered by the NLE to `render/HIGH/` and watched/listened to from beginning to end. It contains all four segments in order, synchronized narration, intended visuals, music, and SFX without missing media, unintended silence/cutoffs, or audible clipping.
- The HIGH output passes the available FFprobe/decoder validation and its duration, dimensions, frame rate, and audio presence are recorded in the project notes. `LOW` may be omitted.
- The project notes clearly distinguish automated behavior from manual steps and identify any blocking gap for repeatable production.
- Generated media remains ignored/untracked; staged paths contain only intentional, reviewable pilot documentation/data/code and no private paths or oversized artifacts.

## Related documents

- [Video Production Workflow](../../guides/VIDEO_PRODUCTION_WORKFLOW.md)
- [Segment Layers and Workbench Layout](TASK-ORDER_SEGMENT_LAYERS_AND_WORKBENCH_LAYOUT.md)
- [Audio Narration Generator](../../tools/audio_narration_generator/README.md)
- [EffectCraft Section Renderer](../../tools/effectcraft_ffmpeg_sections/README.md)
- [Asset Finder](../../tools/asset_finder/README.md)
