# Video Production System Workflow

This guide describes a practical VPS workflow from a rough narration idea through a reviewed video. VPS starts with the narration spine: stable segments hold the spoken words and connect them to visual, music, and sound-effects work. You can stop after any stage and resume later.

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

The project root is the folder containing `README.md` and `audio/`. The first project already uses the narration folders shown below. The `visual_layer/`, `audio/music/`, `audio/sfx/`, and `assets/` folders are created when that work is started; they are not prerequisites for drafting or reviewing narration.

```text
effectcraft-introduction-01/
├── video_project.json                # creative brief, inspirations, and status context
├── README.md                         # project status and links (optional)
├── SCRIPT.md                         # research/editorial notes (optional)
├── PRODUCTION_PLAN.md                # broader brief or history (optional)
├── audio/
│   ├── narration_manifest.json       # source of truth for segments and narration
│   ├── segments/                     # generated per-segment narration takes
│   │   └── <segment-id>_<title-slug>/
│   │       ├── <segment-id>_take-001.wav
│   │       └── <segment-id>_take-002.wav
│   ├── assembled/                    # combined narration review WAVs
│   ├── performance/                  # generator run receipts
│   ├── music/                        # optional, one cue map per segment
│   │   └── <segment-id>.json
│   ├── sfx/                          # optional, one cue map per segment
│   │   └── <segment-id>.json
│   └── visuals/                      # legacy per-segment visual plans only
│       └── <segment-id>.json
├── visual_layer/                     # optional whole-video visual takes
│   ├── selected_take.json            # selects one whole-spine take
│   ├── v_layer_1.json                # take 1: direction + every segment mapping
│   ├── v_layer_1/
│   │   └── <segment-id>/
│   │       ├── elements/
│   │       ├── animations/
│   │       └── scene.js               # example entry; could also be .py, etc.
│   ├── v_layer_2.json                # take 2: an alternative for the whole video
│   └── v_layer_2/
│       └── <segment-id>/             # independent implementation files
├── assets/                           # project-owned media and source records
│   └── audio/
│       ├── music/
│       └── sfx/
└── render/                            # required final video output location
    ├── LOW/                           # optional fast, reduced-quality preview
    └── HIGH/                          # required final-quality render
```

The exact project may contain fewer folders or additional tool-specific files. The narration generator creates segment takes, assembled review files, and performance receipts as needed. `audio/.workbench/` is local workbench state; leave it under the project rather than treating it as an editorial manifest. `audio/visuals/` is a retained older per-segment plan format. New visual work uses the project-root `visual_layer/` structure.

| Layer | Source of truth | What it contains |
|---|---|---|
| Script and narration | `audio/narration_manifest.json` | Stable segment IDs, spoken order and text, voice settings, and selected narration takes. Generated WAV takes and assembled review files stay under `audio/`. |
| Visual | `visual_layer/<take-id>.json`, `visual_layer/selected_take.json`, and referenced project files | Each take describes a visual direction for the whole narration spine and maps every segment ID to its intent and implementation. Element and animation files are normally created for this video. |
| Music | `audio/music/<segment-id>.json` | Optional cue list for that segment, pointing to project-relative audio assets. |
| Sound effects | `audio/sfx/<segment-id>.json` | Optional cue list for that segment, pointing to project-relative audio assets. |

## Continue from narration into the other layers

### Visual Layer: alternatives for the whole narration spine

Create a visual take when you are ready to explore how the video should look. A take applies across the whole narration spine, even though its JSON has a separate entry for each segment. For example, `v_layer_1` could try a retro treatment across the video, while `v_layer_2` tries a different overall treatment and gives one segment a distinctive variation. Selecting a take selects that complete alternative for the spine; it does not select a different take beat by beat.

Each take manifest combines the creative direction with the map to its implementation. Its segment entries use the stable IDs from `audio/narration_manifest.json` and can point to custom EffectCraft, Manim, or GSAP files and folders. Most elements and animations can be made specifically for the current video; library entries are optional. There is no required separate planning JSON before creating the elements. The selected pointer is only selection state; it is not another take.

The workbench scaffolds a pending entry for each current segment and opens the manifest in your default editor. It checks the JSON and project-relative references, but it does not run renderer code or render the video. See the [Segment Layers and Workbench Layout task order](../docs/TASKS/TASK-ORDER_SEGMENT_LAYERS_AND_WORKBENCH_LAYOUT.md) for the manifest contract and an expanded take example.

### Music and SoundEffects: cue maps per segment

Music and SFX are optional and stored separately from the narration and visual manifests. Each segment can have its own music cue file, SFX cue file, both, or neither. The JSON cue list points to audio files in the project and records when they should begin relative to that narration segment. Codex can choose from available project assets and fill in the mappings when asked; you do not need to hand-design the JSON.

The workbench currently creates, opens, and reports the status of these files. It does not search for music, download assets, play cues, or mix audio. Use Asset Finder separately when sourcing is needed, and review the source and usage terms for outside assets. Keep downloaded media and its neighboring `.asset.json` receipt with the video project. A receipt records source metadata; it does not itself establish usage rights. See the [Asset Finder guide](../tools/asset_finder/README.md).

These are per-segment maps, not a single project-wide music timeline. Reusing the same music asset in several segment files is possible, but continuous playback, fades, crossfades, overlap rules, and final audio mixing are not defined by the current workbench.

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
