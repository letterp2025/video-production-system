# Video Production System Workflow

This guide describes a practical VPS workflow from a rough narration idea through a reviewed video. VPS starts with the narration spine: stable segments hold the spoken words and connect them to visual, music, and sound-effects work. You can stop after any stage and resume later.

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

The exact spoken words and segment order belong in `audio/narration_manifest.json`. A separate `SCRIPT.md` or `PRODUCTION_PLAN.md` can hold editorial notes, research, or a broader brief, but it is not a second source of truth for the words being generated.

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

When VPS starts for a project, it creates a starter `video_project.json` at this root if one is missing. It is a user- and Codex-facing brief: capture the general idea, creative direction, rough conversational narration outline, inspirations (sample narration, YouTube videos, artists, and other references), and project-status notes. Status fields start as `not_assessed` rather than making assumptions about existing project work. The workbench does not overwrite an existing file or automatically synchronize these notes; edit the JSON as the project evolves. **Project manifest** in the workbench header opens a read-only view of it.

The project root is the folder containing `video_project.json` and `audio/`. The first project already uses the narration folders shown below. Visual takes, project-wide music, and project assets are added as that work begins; they are not prerequisites for drafting or reviewing narration. The workbench creates a starter `video_project.json` when absent, but it does not create every optional layer folder in advance.

```text
effectcraft-introduction-01/
|-- video_project.json                 # creative identity, inspirations, outline, status notes
|-- README.md                          # project status and links (optional)
|-- SCRIPT.md                          # research/editorial notes (optional)
|-- PRODUCTION_PLAN.md                 # broader brief or history (optional)
|-- audio/
|   |-- narration_manifest.json        # source of truth for stable segments and approved words
|   |-- narration_requests/            # optional AI wording requests and result records
|   |-- segments/                      # generated per-segment narration takes
|   |-- assembled/                     # combined narration review WAVs
|   |-- performance/                   # generator run receipts
|   |-- music/
|   |   `-- manifest.json              # optional project-wide music items and segment ranges
|   |-- visuals/                       # retained legacy per-segment visual plans; not current workflow
|   `-- sfx/                           # retained legacy per-segment SFX plans; not current workflow
|-- visual_layer/
|   |-- selected_take.json             # selects one whole-spine visual direction
|   |-- v_layer_1.json                 # take direction + stable-ID segment/request index
|   `-- v_layer_1/
|       `-- segments/
|           `-- <stable-segment-id>/
|               `-- requests/
|                   `-- VIS-001/       # each request is a separate visual attempt
|                       |-- request.json # preserved brief + optional library references
|                       |-- result.json  # status + validated output paths
|                       |-- sfx.json     # optional SFX plan for this visual candidate
|                       |-- implementation/ # project-owned element/animation source
|                       `-- exports/    # preview and segment export, when created
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
| Script and narration | `audio/narration_manifest.json` and optional `audio/narration_requests/` | Stable segment IDs, spoken order and approved text, voice settings, selected narration takes, and separate AI request/result records for wording suggestions. |
| Visual and candidate SFX | `visual_layer/<take-id>.json`, `visual_layer/selected_take.json`, and `visual_layer/<take-id>/segments/<segment-id>/requests/<request-id>/` | A take describes one direction across the full narration spine. Each segment can keep multiple independent visual requests; request/result JSON track the brief and handoff, with implementation and exported segment assets owned by the project. Optional SFX planning belongs to the visual candidate it supports. |
| Music | `audio/music/manifest.json` | One project-wide list. Each item starts at the beginning of its `start_segment_id` and ends at the end of its `end_segment_id`; optional asset paths refer to project files. |
| Project identity and direction | `video_project.json` | User- and AI-facing creative brief, rough narration outline, inspirations, and manually maintained project-status context. |
| Final video | Chosen NLE/production-tool project and `render/HIGH/` output | The NLE or production renderer assembles, mixes, and renders; VPS prepares assets and planning handoff information rather than acting as an NLE. |

## Continue from narration into the other layers

### Visual Layer: alternatives for the whole narration spine

Create a visual take when you are ready to explore how the video should look. A take is one alternative direction across the whole narration spine. For example, `v_layer_1` could try a retro treatment across the video, while `v_layer_2` tries a different overall treatment. Within a take, each segment can have repeated visual requests (`VIS-001`, `VIS-002`, …), so you can explore or revise that segment without replacing earlier attempts or creating another whole-video take. The take manifest tracks segment requests and which completed candidate is selected for each segment.

Each take manifest combines the creative direction with an index keyed by stable narration IDs. A request can be a custom brief with no library dependency, or optionally reference items from the read-only Visual Library Browser and include a note for each. The implementation is usually created specifically for this video and may use the renderer best suited to it. The request JSON is the brief and handoff; the paired result JSON records progress and output references. The selected-take pointer is only selection state, not another take.

In **Visual Layer**, select or create a take, select a segment by its stable ID, and add a visual request. VPS creates that request's `request.json` brief and `result.json` scaffold under the project. Use terminal Codex (or another AI assistant) to read the request, create the implementation and segment export, and update the paired result. Refresh the workbench to see its status. VPS never auto-launches Codex or executes renderer code. The Visual Library Browser is optional and read-only; it contributes references and notes to the request, not copied or executed library code. See the [Visual Layer guide](../tools/audio_narration_generator/README.md#whole-spine-visual-takes) and [Segment Layers and Workbench Layout task order](../docs/TASKS/TASK-ORDER_SEGMENT_LAYERS_AND_WORKBENCH_LAYOUT.md) for the full workflow.

The v2 result record preserves the take ID, segment ID, request ID, and source-text hash from its scaffold. Keep status current (`requested`, `in_progress`, `completed`, or `failed`) and update `updated_at`; completed work also needs `completed_at` and an existing exported segment file. `implementation_path`, `preview_path`, and `export_path` must be project-relative, remain inside that request folder, and point to existing outputs (implementation may be a file or folder; preview and export are files). A completed candidate can be selected only when its export validates and its source-text hash still matches the narration. The UI surfaces invalid records and legacy v1 results; new requests always use v2. See [`visual_result.schema.json`](../tools/audio_narration_generator/visual_result.schema.json) and the [detailed contract and example](../tools/audio_narration_generator/README.md#whole-spine-visual-takes).

### Project-wide music and candidate-specific sound effects

Music is project-wide, not a separate cue map per segment. The **Music Layer** creates or opens `audio/music/manifest.json`. Each item names its start and end segment by stable ID: playback is intended to begin at the start of the first segment and end after the last segment. The UI resolves and displays current segment titles alongside those IDs. The manifest is simple planning/mapping data; it does not itself acquire, play, mix, or render audio. Codex can help choose music and maintain the JSON when asked.

Sound effects are optional and attached to a visual request as that candidate's `sfx.json`, keeping the effect plan beside the visual it supports. Detailed cue timing, sourcing, playback, and mixing remain outside the current workbench. When sourcing is needed, use Asset Finder separately, keep media and its neighboring `.asset.json` receipt with the project, and review outside-asset usage terms. A receipt records source metadata; it does not itself establish usage rights. See the [Asset Finder guide](../tools/asset_finder/README.md).

### Render and review

Rendering the final video is a required production stage. Keep the `render/` folder in the project. Use its two quality tiers for different jobs:

- **LOW is optional.** It is a fast, reduced-quality preview for checking composition, text readability, timing, and broad visual/audio issues. Make a LOW render when that review will help; revise the project and preview again as needed.
- **HIGH is required for a finished video.** It is the final-quality export and may take substantially longer to render. Once the content and preview are approved, create the HIGH render and review that output. The HIGH file is the final video deliverable; a LOW preview alone does not finish the project.

Keep tier names and filename suffixes aligned, such as `render/LOW/scene_short-description_low.mp4` and `render/HIGH/scene_short-description_high.mp4`. Follow the selected renderer's guide for quality settings and export steps. For example, the [EffectCraft Section Renderer guide](../tools/effectcraft_ffmpeg_sections/README.md) writes output to the requested tier.

The VPS workbench currently organizes the narration and stores visual and audio mappings; it does not assemble renderer code, music, and SFX into a finished video. Render through the selected production tool, watch and listen to the output, and revise the project if review finds issues. The final HIGH export belongs in the project's `render/HIGH/` folder.

## Review checkpoints

- **Narration:** Are the facts supported? Does each segment say one clear thing? Does the complete narration sound natural and have a useful pace?
- **Visuals:** Does the selected take cover every active segment? Can each segment's implementation be located and edited in the project?
- **Music and SFX:** Do the mapped assets fit the spoken moment, stay at an appropriate level, and have reviewed source information when sourced externally?
- **Video:** Are words and graphics readable at normal size? Is the timing clear? Does the complete export play with synchronized sound and no missing media or accidental private information?
- **Project handoff:** Are the editable manifests, code, assets, receipts, and concise review notes kept with the video project? Are generated media and renders kept out of the public VPS source repository?

The workflow is a set of usable checkpoints, not a demand to complete every layer at once. The first project's narration review was a valid place to stop; visual, music, and SFX work can begin when the script is ready for them.
