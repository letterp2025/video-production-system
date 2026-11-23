# Task Order: Four-Segment VPS Mock Video

**Task ID:** E2E-001 | **Status:** Planned — design discussion in progress; NLE selection and SFX timing pending | **Last updated:** 2026-11-23

## Objective

Use VPS as a brainstorming and asset-preparation workspace in a small mock project: develop the script through narration review, explore visual treatments, and organize the selected media and edit decisions for an external non-linear video editor (NLE). Take the project from the initial idea through a reviewed final video to test that handoff.

The video will explain what the Video Production System (VPS) is in exactly four narration segments. Use EffectCraft as the sole visual renderer, exporting one visual asset per segment. VPS is not the NLE and will not become a video editor or mixer in this task: the selected NLE is where the prepared narration, visual exports, music, and SFX are assembled and the final video is rendered. The required outcome is a reviewed final-quality export in `render/HIGH/`; a `render/LOW/` preview is optional.

This is a workflow pilot, not a promise that the workbench already joins every layer automatically. Record the assets and placement decisions VPS prepares, the handoff to the NLE, manual steps, timing assumptions, and failures. Do not generalize a pilot-only workaround into VPS behavior without a separate approved implementation task.

## User workflow

1. Start from the user's direction, “describe what VPS is.” Codex drafts a rough four-part narration outline, then expands it into four coherent spoken segments. Review the story order and wording together before treating the text as ready for narration.
2. Create the mock project under `test/mock-vps-introduction/`. Use four stable segment IDs in `audio/narration_manifest.json`; that manifest remains the source of truth for spoken text and selected narration takes.
3. Open the project in the existing narration workbench. Use SAPI for a quick wording/pacing preview where available, generate F5-TTS takes, listen to alternate takes and the assembled narration, revise as needed, and select the takes for assembly.
4. Create one whole-spine visual take, `visual_layer/v_layer_1.json`, mapping all four stable segment IDs to custom EffectCraft work. EffectCraft exports a separate visual asset for each segment. Keep the same renderer for every segment; do not introduce Manim or GSAP in this pilot.
5. In **Visual Layer**, manage sound-effect choices with the visual take and segment they support. A different visual take may have different SFX for the same narration segment. Use Asset Finder to source suitable SFX, check source and usage terms, and keep source receipts with the project. SFX remain edit instructions and asset references, not a VPS mix.
6. In **Music Layer**, manage a project-wide list of music items. Each item starts at the beginning of a selected segment and ends at the end of a selected segment; optional fades may be recorded for the NLE. Use Asset Finder to source suitable music and keep reviewed source information with the project.
7. Export the four EffectCraft visual assets for the NLE. Bring in the selected narration, visual exports, music/SFX assets, and their placement information. Assemble the timeline in the chosen NLE, check segment boundaries and cue timing against the narration, and render the final video there.
8. Optionally create a fast `LOW` preview from the NLE and review it. Make any needed revisions, then create and review the required `HIGH` final export.
9. Record what worked, what required manual intervention, and what asset-management or handoff capability would need a separate implementation task before another project could follow the same path reliably.

## Four-segment story target

The exact wording is developed during the pilot. The four segments should cover these ideas without implying capabilities that do not exist:

1. **The purpose:** VPS is a brainstorming and asset-preparation workspace that organizes a video's script, narration, visuals, and planned sound for handoff to an NLE.
2. **The narration spine:** stable segments hold the approved spoken words and connect narration takes to the rest of the project.
3. **The production layers:** visual takes span the narration spine, EffectCraft produces a separate asset for each segment, SFX can accompany the chosen visual treatment, and music is placed across segment boundaries.
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
    │   └── music/manifest.json           # project-wide music items with start/end segment IDs
    ├── visual_layer/
    │   ├── selected_take.json
    │   ├── v_layer_1.json                 # one visual direction covering all four segment IDs
    │   └── v_layer_1/
    │       ├── segments/<segment-id>/     # visual work and take-specific SFX cue plan
    │       ├── effectcraft/               # EffectCraft project and section/timing inputs
    │       └── exports/<segment-id>.*     # one rendered visual asset per narration segment
    ├── assets/audio/
    │   ├── music/                         # selected local music and source receipts
    │   └── sfx/                           # selected local SFX and source receipts
    ├── nle_handoff/                       # asset list and edit instructions for the chosen NLE
    └── render/
        ├── LOW/                           # optional fast preview (local/ignored)
        └── HIGH/                          # required final NLE export (local/ignored)
```

This is a target layout, not a requirement to create empty folders. Create folders when that work begins. Follow the EffectCraft project format where its native files require a different internal arrangement. The narration manifest owns the spoken text; `PRODUCTION_NOTES.md` is for the outline and observations, not a competing script. SFX cue data belongs to a specific visual take and segment; it may be stored with that segment's project work. The `nle_handoff/` contents and location of the editor's native project depend on the NLE chosen during design discussion.

## Data ownership and handoffs

| Concern | Pilot source of truth | Handoff to final video |
|---|---|---|
| Spoken script and selected takes | `audio/narration_manifest.json` plus generated take files | Existing narration generator assembles selected active takes into review audio. |
| Visual direction and segment mapping | `visual_layer/v_layer_1.json` and referenced EffectCraft work | EffectCraft renders one visual asset per narration segment for import into the NLE; the workbench does not execute the renderer. |
| SFX choices and placement | SFX cue plan associated with a visual take and its segment, plus selected assets | The Visual Layer presents SFX alongside that take's segment animation; another visual take may have different SFX. The cue data is for NLE handoff, not playback or mixing. |
| Music choices and placement | Project-wide `audio/music/manifest.json` plus selected assets | Each music item names its start segment and end segment. It starts at the beginning of the start segment and ends at the end of the end segment. Optional fades may be noted for the NLE. |
| Asset source details | Asset Finder receipts stored beside project assets | Review source and usage terms before using an asset; a receipt is provenance information, not a rights grant. |
| Final output | `render/LOW/` (optional) and `render/HIGH/` (required) | The chosen NLE assembles and renders the final video. VPS prepares assets and instructions; it does not mix or render the finished timeline. |

Music placements use stable segment boundaries rather than arbitrary project seconds: a music item names the segment where it starts and the segment where it ends. The end boundary is the end of that selected segment. Optional fades can be recorded, but VPS does not apply them. SFX placement is associated with the selected visual take and segment; the exact within-segment timing representation remains open. Neither layer is mixed or rendered by VPS. The pilot records how the NLE interprets the placement instructions and how narration revisions affect them.

**Current implementation note:** The current workbench has four top-level tabs, including a separate SoundEffects tab. Music creates `audio/music/<segment-id>.json`, with cue times relative to that segment and a hash of its spoken text; SFX uses a separate per-segment mapping. These are existing prototype behaviors, not the target design below. The target UI has three top-level tabs—Script and Narration, Visual, and Music—with SFX inside the Visual Layer for the selected visual take and segment. The Music Layer uses a project-wide manifest. Supporting those target behaviors requires workbench/schema changes; this task order plans them but does not implement them now.

## Design decisions still open before pilot execution

- Which NLE will receive the prepared assets and produce the final video.
- How SFX cues identify their timing within a segment or visual animation, and whether optional fades/trim details are needed.
- Whether overlapping music items or crossfades are needed in the first pilot; segment-boundary start/end is the baseline.

The agreed decisions are: EffectCraft exports each segment separately; SFX belongs with the selected visual take and segment in Visual Layer; music is project-wide and starts/ends on segment boundaries; the stable narration ID must be clearly visible in the UI. The NLE and detailed SFX cue timing remain open. Resolve those before treating this task order as execution-ready.

NLE candidates under consideration are DaVinci Resolve, which the user views as mature, and Artcraft, an open-source Premiere-like option the user currently considers less mature and slower. Neither is selected by this task order; confirm the choice before the pilot's NLE handoff phase.

## Boundaries

- Exactly four active narration segments, one whole-spine visual take, and one visual renderer: EffectCraft.
- VPS remains an asset-management/planning and handoff workspace. The chosen NLE owns timeline assembly, mixing, and final video rendering.
- No production-channel content, private voice references, credentials, or absolute machine-specific paths in tracked pilot files.
- No Manim/GSAP comparison, reusable renderer framework, generic project orchestrator, or NLE integration. Workbench changes are limited to the planning UI/data model described here; VPS does not play, mix, or render the final timeline.
- Do not describe the workbench as automatically rendering or mixing the layers; test and document actual behavior.
- Use Asset Finder to source music and SFX assets for the pilot, and review their source/usage terms. Do not assume an asset is cleared merely because it can be downloaded.
- Generated narration, audio/video assets, EffectCraft binary project files, caches, intermediates, and renders may be ignored by repository rules. Do not force-add generated or large media to Git. Verify ignore behavior before production and keep only suitable, portable manifests, code, notes, and receipts tracked.
- Do not make HIGH rendering optional: `LOW` is optional; a completed pilot requires a reviewed final `HIGH` export.

## Implementation phases

1. **Update the planning UI and data model:** make the three top-level tabs; move SFX into the selected visual take/segment's Visual Layer workspace; add project-wide Music manifest support with segment-boundary start/end; and show the stable narration ID clearly in the selected-segment context and music anchors.
2. **Create the four-segment pilot skeleton:** add the mock project README and production notes, draft the four-part outline, create the project-local narration manifest, and confirm the workbench opens the intended project.
3. **Complete narration:** revise wording, generate/review takes, select the takes, assemble the narration, and record the accepted text and listening decisions.
4. **Implement one visual take in EffectCraft:** map every segment by stable ID, build custom visuals, define section timing, include take-specific SFX cues, and export one visual asset per segment.
5. **Prepare music and SFX assets:** select suitable assets through Asset Finder, preserve source receipts, and populate the project-wide music placements and take/segment SFX cues. Do not implement playback or mixing in VPS.
6. **Hand off and edit in the NLE:** import narration and the four EffectCraft visual assets, use the music/SFX placements and asset notes, assemble the timeline, and adjust the edit as needed. Record where the handoff was clear or required interpretation.
7. **Render and review:** optionally render LOW in the NLE for fast feedback; render HIGH there as the final deliverable; verify video, audio, segment joins, cue placement, and the final file's streams and duration.
8. **Write pilot findings:** update the project README with commands, selected NLE, safe-to-share tool versions/configuration, timing decisions, manual handoffs, known limitations, and prioritized follow-up task-order candidates. Keep private paths and raw records out of tracked notes.

## Acceptance checks

- The tracked pilot project begins with the stated VPS explainer goal and has exactly four active, uniquely identified narration segments.
- The narration workbench opens this project; the chosen segment takes and assembled narration can be reviewed, and revisions are reflected in the final selected narration.
- The workbench has three top-level tabs: **Script and Narration Layer**, **Visual Layer**, and **Music Layer**. SFX controls are inside Visual Layer for the selected take and segment, not in a separate top-level tab.
- The stable narration ID is clearly visible in the selected-segment header/context across layer views. Music placement rows show the start/end segment IDs alongside their titles.
- A single `v_layer_1` manifest maps all four narration IDs, all four visual assets are exported by EffectCraft separately, and each segment's SFX cues are associated with that visual take. Source/usage details are reviewed.
- The project-wide music manifest identifies selected asset(s), start segment ID, and end segment ID for each item. Music starts at the beginning of its start segment and ends at the end of its end segment; optional fade settings are passed to the NLE as instructions.
- The selected NLE receives the narration, four separate EffectCraft visual assets, audio assets, and placement instructions. The pilot records any asset or timing details that did not transfer cleanly.
- A complete video is rendered by the NLE to `render/HIGH/` and watched/listened to from beginning to end. It contains all four segments in order, synchronized narration, intended visuals, music, and SFX without missing media, unintended silence/cutoffs, or audible clipping.
- The HIGH output passes the available FFprobe/decoder validation and its duration, dimensions, frame rate, and audio presence are recorded in the project notes. `LOW` may be omitted.
- The project notes clearly distinguish automated behavior from manual steps and identify any blocking gap for repeatable production.
- Generated media remains ignored/untracked; staged paths contain only intentional, reviewable pilot documentation/data/code and no private paths or oversized artifacts.

## Related documents

- [Video Production Workflow](../../guides/VIDEO_PRODUCTION_WORKFLOW.md)
- [Segment Layers and Workbench Layout](TASK-ORDER_SEGMENT_LAYERS_AND_WORKBENCH_LAYOUT.md)
- [Workbench Layer Tabs](TASK-ORDER_WORKBENCH_LAYER_TABS.md)
- [Audio Narration Generator](../../tools/audio_narration_generator/README.md)
- [EffectCraft Section Renderer](../../tools/effectcraft_ffmpeg_sections/README.md)
- [Asset Finder](../../tools/asset_finder/README.md)
