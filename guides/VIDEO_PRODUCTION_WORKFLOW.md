# Video Production System Workflow

This guide describes a practical VPS workflow from a rough narration idea through a reviewed video. Stable narration segments hold the approved spoken words; the project sequence orders those narration units together with any visual-only openings, pauses, montages, or outros. You can stop after any stage and resume later.

Starting from a fresh VPS clone and creating a separate project with Codex? Begin with [Start a Video Project with Codex](START_A_VIDEO_PROJECT_WITH_CODEX.md). The public VPS checkout is the tool and instruction source; keep the actual video project in its own folder.

## The first video project: narration first

The first project, `effectcraft-introduction-01`, began with a rough narration outline. The creator gave Codex the outline; Codex expanded it into segment entries. Then the creator and Codex revised the wording through conversation and repeated listening. That was the first production milestone: a segment-by-segment narration draft that could be heard and adjusted. Visuals, music, and sound effects did not need to be planned before reaching that point.

Use the same approach for a new project:

1. Give Codex the rough outline, the audience and intended takeaway, and any source notes or factual boundaries. The outline does not need polished wording or a storyboard.
2. Ask Codex to expand it into short, coherent spoken segments. Keep each segment focused on one idea. Give each segment a stable ID, a short title, and draft spoken text.
3. Review the sequence for missing ideas, repetition, accuracy, and a natural spoken voice. Revise one segment or a group of related segments at a time. Reordering a segment does not change its ID.
4. Use VPS to listen. **Preview SAPI fast** is a quick wording and pacing check on supported Windows systems. **Build + play F5-TTS** generates or reuses the configured F5-TTS takes, assembles the selected narration, and plays it from the selected segment.
5. Listen to individual lines for pronunciation and delivery, then listen to the assembled narration for flow and runtime. Adjust the words and listen again. Select the take you want for assembly in each segment; the manifest records that selection, while ratings and notes record how alternate takes sounded.
6. When the narration is clear enough to carry the story, save that as the current milestone. You can begin visuals and sound later, once the spoken spine is stable enough to guide them. This is a valid work-in-progress checkpoint; a finished video still needs its final HIGH render.

The exact spoken words and speech-only assembly order belong in `audio/narration_manifest.json`; the overall video story order belongs in `sequence_manifest.json`. A separate `SCRIPT.md` or `PRODUCTION_PLAN.md` can hold editorial notes, research, or a broader brief, but it is not a second source of truth for approved words.

For another AI-assisted wording pass, write an editorial note in the workbench and choose **Create AI request JSON**. VPS saves the brief and a separate progress/result file under `audio/narration_requests/<stable-segment-id>/requests/<request-id>/`. A terminal Codex, Claude, or other assistant can find it from the project root with `rg --files --hidden --no-ignore -g 'request.json' audio/narration_requests`; no AI server is required. VPS imports a completed result only after **Refresh AI results**. The proposal changes no spoken text until you explicitly accept it; acceptance replaces that segment's `text` in `audio/narration_manifest.json`, while preserving its stable ID. See the [narration request and result contract](../tools/audio_narration_generator/README.md#request-and-result-examples) for JSON examples, status values, and safeguards.

## Set up and open a project

Keep each video's working files together outside the public VPS source repository. Start with the narration manifest template included with the generator:

```powershell
New-Item -ItemType Directory -Force 'C:\path\to\video-project\audio'
Copy-Item 'tools\audio_narration_generator\narration_manifest.example.json' `
  'C:\path\to\video-project\audio\narration_manifest.json'
```

Replace the example project fields, speaker settings, and placeholder segment with your own. Keep voice-reference recordings and transcripts private with the project; do not commit them to the public repository.

From the VPS repository root, start the local workbench with the project's manifest:

```powershell
python tools\audio_narration_generator\workbench.py `
  --manifest 'C:\path\to\video-project\audio\narration_manifest.json' `
  --port 8766
```

If F5-TTS needs a different Python environment, add `--python 'C:\path\to\f5-tts\python.exe'`. Open `http://127.0.0.1:8766` in your browser. The server works with the one selected project and listens on the local computer only. For the full controls and generation details, see the [Audio Narration Generator guide](../tools/audio_narration_generator/README.md).

## Project folders and what owns each layer

When VPS starts for a project, it creates a starter `video_project.json` at this root if one is missing. It is a user- and Codex-facing brief: capture the general idea, creative direction, rough conversational narration outline, inspirations (sample narration, YouTube videos, artists, and other references), project-status notes, and optionally the project's default F5-TTS voice. Status fields start as `not_assessed` rather than making assumptions about existing project work. The workbench does not overwrite an existing file or automatically synchronize these notes; edit the JSON as the project evolves. **Project manifest** in the workbench header opens a read-only view of it.

To set a project-wide F5-TTS reference voice, open **Project manifest** in the workbench and fill **Default narration voice** with a project-relative recording path and the exact words spoken in that recording. You can also edit `video_project.json` directly: set `narration.default_voice.reference_audio` and `reference_text`. For example, use `audio/reference_audio/channel-voice.wav` as the path. This overrides the fallback `voice` in `audio/narration_manifest.json` for segments with no named `voice_style`; a segment's explicit named style still takes precedence. Choose **Use narration fallback** in the modal, or set `default_voice` to `null`, to clear the project default. The F5-TTS panel identifies which default source is currently active. Changing the effective voice makes old takes stale so they are regenerated before use.

The project root is the folder containing `video_project.json` and `audio/`. The first project already uses the narration folders shown below. Visual takes, project-wide music, and project assets are added as that work begins; they are not prerequisites for drafting or reviewing narration. The workbench creates a starter `video_project.json` when absent, but it does not create every optional layer folder in advance.

```text
effectcraft-introduction-01/
|-- video_project.json                 # creative identity, narration default voice, inspirations, outline, status
|-- sequence_manifest.json             # ordered video units and planned durations
|-- README.md                          # project status and links (optional)
|-- SCRIPT.md                          # research/editorial notes (optional)
|-- PRODUCTION_PLAN.md                 # broader brief or history (optional)
|-- audio/
|   |-- narration_manifest.json        # source of truth for stable segments and approved words
|   |-- reference_audio/                # optional project-level default F5-TTS speaker samples
|   |-- narration_requests/            # optional AI wording requests and result records
|   |-- segments/                      # generated per-segment narration takes
|   |-- assembled/                     # combined narration review WAVs
|   |-- performance/                   # generator run receipts
|   |-- music/
|   |   `-- manifest.json              # optional project-wide music items and sequence-unit ranges
|   |-- visuals/                       # retained legacy per-segment visual plans; not current workflow
|   `-- sfx/                           # retained legacy per-segment SFX plans; not current workflow
|-- visual_layer/
|   |-- selected_take.json             # selects one whole-video visual direction
|   |-- v_layer_1.json                 # take direction + stable sequence-unit/request index
|   `-- v_layer_1/
|       `-- segments/
|           `-- <sequence-unit-id>/
|               `-- requests/
|                   `-- VIS-001/       # each request is a separate visual attempt
|                       |-- request.json # preserved brief + optional library references
|                       |-- result.json  # status + validated output paths
|                       |-- sfx.json     # optional SFX plan for this visual candidate
|                       |-- implementation/ # project-owned element/animation source
|                       `-- exports/    # preview and sequence-unit export, when created
|-- assets/                            # optional project-owned media and source records
|   `-- audio/
|       |-- music/
|       `-- sfx/
`-- render/                            # final video rendered by the chosen production tool/NLE
    |-- LOW/                           # optional fast, reduced-quality preview
    `-- HIGH/                          # required final-quality render
```

This is an illustrative layout, not a list of folders VPS pre-creates. A project may contain fewer folders or additional tool-specific files. The narration generator creates audio takes, assembled review files, and performance receipts as needed. `audio/.workbench/` is temporary review state, not an editorial manifest. The old `audio/visuals/`, per-segment `audio/music/<segment-id>.json`, and `audio/sfx/<segment-id>.json` formats are legacy; VPS leaves existing files untouched but the current UI does not use them. New visual requests live under project-root `visual_layer/`; project-wide music lives at `audio/music/manifest.json`.

| Layer | Source of truth | What it contains |
|---|---|---|
| Story sequence | `sequence_manifest.json` | Canonical video order: narration-linked and visual-only units, stable IDs, and editable planned durations. |
| Script and narration | `audio/narration_manifest.json` and optional `audio/narration_requests/` | Stable narration IDs, speech-only playback order and approved text, per-segment voice-style/TTS overrides, selected takes, and AI wording requests/results. |
| Visual and candidate SFX | `visual_layer/<take-id>.json`, `visual_layer/selected_take.json`, and `visual_layer/<take-id>/segments/<unit-id>/requests/<request-id>/` | A take describes one direction across the video sequence. Each unit can keep multiple independent visual requests; implementation/export assets remain project-owned. Optional SFX planning belongs to the visual candidate it supports. |
| Music | `audio/music/manifest.json` | One project-wide list. Each item's `start_segment_id` and `end_segment_id` values refer to sequence-unit IDs; the cue starts at the beginning of the first unit and ends after the last unit. Optional asset paths refer to project files. |
| Project identity and direction | `video_project.json` | User- and AI-facing creative brief, rough narration outline, inspirations, manually maintained project-status context, and optional project-wide F5-TTS default voice reference/transcript. |
| Final video | Chosen NLE/production-tool project and `render/HIGH/` output | The NLE or production renderer assembles, mixes, and renders; VPS prepares assets and planning handoff information rather than acting as an NLE. |

### Story sequence and visual-only intervals

When the workbench first opens a project without `sequence_manifest.json`, it creates one from all existing narration IDs in their current order, including inactive/deleted records. The narration manifest and existing take files are not overwritten. Each unit has a positive `duration_seconds`: the workbench uses a measured selected WAV length when available, otherwise an editable speech estimate. New visual-only units default to three seconds. These are planning targets, not frame-accurate edit points; review timing in the NLE.

The left **Sequence** rail shows both kinds in one story order. Use **Add visual-only unit** for a silent opening, montage, pause, or outro; give it a unique stable ID, title, duration, and optional note. It creates no blank narration segment or voice take. Select a unit to edit its planned duration or move it; visual-only units also allow title/note edits. Narration titles and spoken words remain in `audio/narration_manifest.json`. The Script and Narration tab shows a no-narration state for a visual-only selection; SAPI/F5 playback covers speech only and skips visual-only intervals. When the video order of spoken units changes, VPS syncs the narration array for playback. If an external edit leaves the two orders different, VPS warns and pauses narration playback until you explicitly sync them.

Visual take entries and request folders use the selected sequence-unit ID for either kind. An existing take can acquire a visual-only entry when you make its first request, without rewriting earlier requests. Visual-only requests use a separate `source_unit_sha256` revision derived from title, note, and planned duration; narration requests keep `source_text_sha256`. Music's existing `start_segment_id` and `end_segment_id` fields still work, but now refer to sequence-unit IDs, so music can start or end on a visual-only unit. A malformed existing sequence is reported and preserved, not replaced. The sequence JSON itself is the readable order/duration handoff for a downstream NLE; VPS still does not assemble the final video.

## Continue from narration into the other layers

### Visual Layer: alternatives for the whole video sequence

Create a visual take when you are ready to explore how the video should look. A take is one alternative direction across the whole story sequence. For example, `v_layer_1` could try a retro treatment across the video, while `v_layer_2` tries a different overall treatment. Within a take, each narration-linked or visual-only sequence unit can have repeated visual requests (`VIS-001`, `VIS-002`, …), so you can explore or revise that unit without replacing earlier attempts or creating another whole-video take. The take manifest tracks requests and which completed candidate is selected for each unit.

Each take manifest combines the creative direction with an index keyed by stable sequence-unit IDs. A request can be a custom brief with no library dependency, or optionally reference items from the read-only Visual Library Browser and include a note for each. The implementation is usually created specifically for this video and may use the renderer best suited to it. The request JSON is the brief and handoff; the paired result JSON records progress and output references. The selected-take pointer is only selection state, not another take.

In **Visual Layer**, select or create a take, select a sequence unit by its stable ID, and add a visual request. VPS creates that request's `request.json` brief and `result.json` scaffold under the project. Use terminal Codex (or another AI assistant) to read the request, create the implementation and unit export, and update the paired result. Refresh the workbench to see its status. VPS never auto-launches Codex or executes renderer code. The Visual Library Browser is optional and read-only; it contributes references and notes to the request, not copied or executed library code. See the [Visual Layer guide](../tools/audio_narration_generator/README.md#whole-spine-visual-takes) and [Segment Layers and Workbench Layout task order](../docs/TASKS/TASK-ORDER_SEGMENT_LAYERS_AND_WORKBENCH_LAYOUT.md) for the full workflow.

Narration-linked results retain the v2 source-text contract. Visual-only requests use `source_unit_sha256` and a v3 result; see the [visual-only result schema](../tools/audio_narration_generator/visual_result_visual_only.schema.json). In both cases keep status current (`requested`, `in_progress`, `completed`, or `failed`) and update `updated_at`; completed work also needs `completed_at` and an existing exported sequence-unit file. Output paths must be project-relative and inside that request folder. VPS validates these before allowing a candidate to be selected.

### Project-wide music and candidate-specific sound effects

Music is project-wide, not a separate cue map per segment. The **Music Layer** creates or opens `audio/music/manifest.json`. Each item names its start and end sequence unit by stable ID; either boundary can be visual-only. The UI resolves and displays current unit titles alongside those IDs. The manifest is simple planning/mapping data; it does not itself acquire, play, mix, or render audio. Codex can help choose music and maintain the JSON when asked.

Sound effects are optional and attached to a visual request as that candidate's `sfx.json`, keeping the effect plan beside the visual it supports. Detailed cue timing, sourcing, playback, and mixing remain outside the current workbench. When sourcing is needed, use Asset Finder separately, keep media and its neighboring `.asset.json` receipt with the project, and review outside-asset usage terms. A receipt records source metadata; it does not itself establish usage rights. See the [Asset Finder guide](../tools/asset_finder/README.md).

### Render and review

Rendering the final video is a required production stage. Keep the `render/` folder in the project. Use its two quality tiers for different jobs:

- **LOW is optional.** It is a fast, reduced-quality preview for checking composition, text readability, timing, and broad visual/audio issues. Make a LOW render when that review will help; revise the project and preview again as needed.
- **HIGH is required for a finished video.** It is the final-quality export and may take substantially longer to render. Once the content and preview are approved, create the HIGH render and review that output. The HIGH file is the final video deliverable; a LOW preview alone does not finish the project.

Keep tier names and filename suffixes aligned, such as `render/LOW/scene_short-description_low.mp4` and `render/HIGH/scene_short-description_high.mp4`. Follow the selected renderer's guide for quality settings and export steps. For example, the [EffectCraft Section Renderer guide](../tools/effectcraft_ffmpeg_sections/README.md) writes output to the requested tier.

The VPS workbench organizes the story sequence and narration, and stores visual, music, and candidate-SFX planning and asset references; it does not assemble them into a finished video. Render through the selected NLE or production tool, watch and listen to the output, and revise the project if review finds issues. The final HIGH export belongs in the project's `render/HIGH/` folder.

## Review checkpoints

- **Narration:** Are the facts supported? Does each segment say one clear thing? Does the complete narration sound natural and have a useful pace?
- **Visuals:** Does the selected take cover each active sequence unit that needs a visual? Can each unit's implementation be located and edited in the project?
- **Music and SFX:** Do the mapped assets fit the spoken moment, stay at an appropriate level, and have reviewed source information when sourced externally?
- **Video:** Are words and graphics readable at normal size? Is the timing clear? Does the complete export play with synchronized sound and no missing media or accidental private information?
- **Project handoff:** Are the editable manifests, code, assets, receipts, and concise review notes kept with the video project? Are generated media and renders kept out of the public VPS source repository?

The workflow is a set of usable checkpoints, not a demand to complete every layer at once. The first project's narration review was a valid place to stop; visual, music, and SFX work can begin when the script is ready for them.
