# Start a Video Project with Codex

This guide is for creating a new, separate video-project folder with Codex using the public Video Production System (VPS) repository as the instruction and tool source.

VPS source repository: [letterp2025/video-production-system](https://github.com/letterp2025/video-production-system)

Keep the two folders distinct:

```text
your-workspace/
|-- VIDEO_PRODUCTION_SYSTEM/  # cloned VPS tools, examples, and guides
`-- your-video-project/       # this video's private or project-owned files
```

The video project can be in its own Git repository. Do not create it inside the public VPS checkout or commit private scripts, voice references, source media, credentials, or renders to the VPS repository.

## 1. Get the VPS instructions

Clone the public repository, or update an existing checkout:

```powershell
git clone https://github.com/letterp2025/video-production-system.git C:\path\to\VIDEO_PRODUCTION_SYSTEM
```

For an existing checkout:

```powershell
git -C 'C:\path\to\VIDEO_PRODUCTION_SYSTEM' pull
```

Before asking Codex to create the project, have it read these files from that checkout:

1. `AGENTS.md`
2. `guides/START_A_VIDEO_PROJECT_WITH_CODEX.md`
3. `guides/VIDEO_PRODUCTION_WORKFLOW.md`
4. `tools/audio_narration_generator/README.md`
5. `tools/audio_narration_generator/narration_manifest.example.json`
6. `guides/templates/VIDEO_PROJECT_AGENTS.md`

Read other tool guides only when the project is ready to use those tools. In particular, visual and music planning are later steps, not prerequisites for getting the narration spine into shape.

## 2. Give Codex the project destination and your raw thinking

Start Codex in a context where it can read the VPS checkout and write to the intended project destination. Tell it the exact project-root folder. If a later Codex session will be launched from the project root, copy the project instructions template there and fill in the local path to the VPS checkout.

Give Codex the material you have, even if it is rough:

- the idea and intended audience;
- what the viewer should understand, feel, or do;
- a conversational narration outline (rambling notes are fine);
- factual boundaries, source notes, or claims that need checking;
- creative direction and inspirations, such as narration samples, YouTube videos, artists, or other references;
- any known constraints, and what is still undecided.

Codex should not invent personal inspirations, factual claims, voice recordings, or asset paths. Unknown information should remain clearly unknown or be brought back to you as a question.

## 3. Create the minimum useful project files

Start with the project brief and narration files. Do not pre-create empty visual, music, sound-effects, asset, or render plans just to fill out a folder tree.

```text
your-video-project/
|-- AGENTS.md                    # copied project instructions, with local VPS checkout path filled in
|-- video_project.json           # creative identity, rough outline, inspirations, status notes
`-- audio/
    `-- narration_manifest.json  # ordered stable-ID segments and current spoken wording
```

This is the minimum starting tree; the workbench also creates the project-root `sequence_manifest.json` the first time it opens a project, initializing it from the existing narration IDs and their current order. That manifest then owns video story order and planned durations, including any later visual-only units. Do not create blank narration segments for silent visual intervals. The workbench also creates a starter `video_project.json` when it starts and finds none, but that starter is intentionally blank. Prefer having Codex create a meaningful brief from your notes before opening the workbench. If you already know the project's F5-TTS speaker reference, optionally record it as `narration.default_voice` in `video_project.json`; it overrides the narration manifest's fallback voice, while a segment-specific named voice style still takes precedence. The brief is for the user and future AI sessions; it does not replace the narration manifest as the source of truth for approved spoken words.

The narration example is a structural template, not a ready-to-generate voice configuration. Copy it from the VPS checkout, then replace its example project name, voice settings and placeholder segments. Do not assume its referenced voice files exist:

```powershell
$VideoProjectPath = 'C:\path\to\your-video-project'
New-Item -ItemType Directory -Force "$VideoProjectPath\audio"
Copy-Item 'C:\path\to\VIDEO_PRODUCTION_SYSTEM\tools\audio_narration_generator\narration_manifest.example.json' `
  "$VideoProjectPath\audio\narration_manifest.json"
Copy-Item 'C:\path\to\VIDEO_PRODUCTION_SYSTEM\guides\templates\VIDEO_PROJECT_AGENTS.md' `
  "$VideoProjectPath\AGENTS.md"
```

Replace both example paths before running these commands. Then edit the copied `AGENTS.md` and set its VPS checkout location. If a destination file already exists, inspect it and preserve it rather than overwriting it.

## 4. Ask Codex to develop the narration with you

Use a prompt along these lines, filling in the actual paths and material:

> Use the VPS checkout at `<VPS checkout path>` as the production guide. Read its root `AGENTS.md`, `guides/START_A_VIDEO_PROJECT_WITH_CODEX.md`, `guides/VIDEO_PRODUCTION_WORKFLOW.md`, and `tools/audio_narration_generator/README.md`. The separate video project is `<project root>`; do not put project files in the VPS checkout. Read the project's `AGENTS.md` and `video_project.json`. Preserve my raw narration outline in the project brief, then help expand it into clear, speakable segments in `audio/narration_manifest.json`. Keep each segment focused on one idea and give it a unique, durable ID, a short title, and draft spoken text. First show me the proposed sequence and discuss it; make only the project-file changes I approve. Do not begin visual implementation, source or download assets, or render a video unless I ask.

The intended first loop is:

1. Codex organizes the project idea and raw outline in `video_project.json`.
2. Codex proposes narration segments and discusses them with you.
3. You and Codex revise the wording and order. Keep segment IDs stable when wording or order changes; create a new ID for a genuinely new segment.
4. You listen to individual lines and the assembled narration in VPS, then continue revising until the narration is a useful approved milestone.

Do not treat the first draft as final. The original VPS project began with rough notes, expanded them into segments, and then improved them through conversation and repeated listening. Visuals and music can wait until the spoken spine is clear enough to guide those decisions.

## 5. Open the project in VPS and listen

From the VPS checkout, start the workbench with the separate project's manifest:

```powershell
python 'C:\path\to\VIDEO_PRODUCTION_SYSTEM\tools\audio_narration_generator\workbench.py' `
  --manifest 'C:\path\to\your-video-project\audio\narration_manifest.json' `
  --port 8766
```

Open `http://127.0.0.1:8766`. **Preview SAPI fast** is the quick wording and pacing check on supported Windows systems. **Build + play F5-TTS** requires a configured F5-TTS environment and valid voice-reference settings; pass `--python` if that environment uses a different Python executable. See the [Audio Narration Generator guide](../tools/audio_narration_generator/README.md) for setup and controls.

VPS creates narration audio takes and assembled review audio under the project as they are generated. It does not make the final video. The project can pause at the reviewed narration milestone and resume later.

## 6. Let terminal Codex find and process file requests

VPS uses provider-neutral JSON handoffs. It creates a `request.json` brief and a paired `result.json` progress/response record; you run Codex, Claude, or another assistant yourself in a terminal with the video-project folder as its working directory. No Codex server is required.

Requests are stored with the project data they concern:

```text
audio/narration_requests/<stable-segment-id>/requests/SCR-001/{request.json,result.json}
visual_layer/<take-id>/segments/<sequence-unit-id>/requests/VIS-001/{request.json,result.json}
```

From the project root, find pending or past requests with ripgrep:

```powershell
rg --files --hidden --no-ignore -g 'request.json' audio/narration_requests
rg --files --hidden --no-ignore -g 'request.json' visual_layer
rg -n '"status"|"updated_at"|"completed_at"|"error"' audio/narration_requests visual_layer -g 'result.json'
```

The search paths may not exist until that layer has been used. `--hidden --no-ignore` is useful because request files may be new or ignored by a project's Git settings.

Each `result.json` starts with status `requested`. The assistant should set it to `in_progress` while working, then `completed` or `failed`, and keep the associated timestamps and output fields consistent with the relevant contract. If the project is a Git repository, `git status --short` can also show new or modified request files; ripgrep is the direct way to locate request JSON and can include ignored files.

For a narration request, read its `request.json` and the linked narration request/result contract in the Audio Narration Generator guide. The assistant writes its proposal and progress to the paired `result.json`; VPS imports it for review when you choose **Refresh AI results**. The accepted proposal changes the approved segment text only after you explicitly choose **Accept**.

For a visual request, read its `request.json`, the take manifest, and the Visual Layer contract in the Audio Narration Generator guide. Keep each attempt in its own request folder, preserve the brief, and write progress and project-relative output paths to that request's `result.json`. VPS validates and displays the record; it does not launch Codex or execute renderer code. Use **Reload manifest** in VPS to refresh the display.

The project's `AGENTS.md` is the instruction entry point for Codex sessions started later from that project root. The request's own task and result schema are the authority for a specific handoff; do not replace the approved narration or rewrite a request just to report progress.

## 7. Add other layers when the narration is ready

- **Visual Layer:** create a whole-video visual take, then make one or more independent requests for each sequence unit, including visual-only units. Implementations and exported unit assets belong to the project. Read-only library references are optional; many visuals will be created specifically for the video.
- **Music Layer:** music is project-wide. Each item starts at a sequence-unit ID and ends at another sequence-unit ID; the IDs may refer to narration-linked or visual-only units. Its JSON maps the intended cue; it does not acquire, mix, or render audio.
- **Sound effects:** optional SFX planning is attached to the visual request it supports. Asset Finder can help locate media when you decide sourcing is needed.
- **Final video:** assemble the prepared assets in the NLE or production tool you choose. A LOW render is an optional fast preview; a HIGH render is required for the final video.

See the [complete video production workflow](VIDEO_PRODUCTION_WORKFLOW.md) for the project folder tree, layer ownership, review checkpoints, and rendering guidance.
