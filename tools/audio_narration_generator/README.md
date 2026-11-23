# Audio Narration Generator

Generate separately reviewable F5-TTS narration takes from an ordered JSON manifest, reuse unchanged takes, and assemble the selected active takes into a WAV review track.

The generator does not bundle F5-TTS, a model checkpoint, or voice recordings. Install and license those separately. Use reference audio only when you have permission to use it for speech generation.

## Code layout

The command-line entry points remain `generate_narration.py`, `workbench.py`, and `preview_narration.py`.

- `narration_manifest.py` owns manifest validation and shared field rules; `generate_narration.py` owns take generation, pruning, and assembly.
- `workbench_common.py` owns shared limits, errors, and atomic JSON helpers. `workbench_project.py` owns manifest-backed editing and the temporary work queue.
- `workbench_visuals.py` owns per-beat visual plans; `workbench_audio.py` owns take and assembly lookup. `workbench.py` owns the local HTTP routes, Codex request adapter, and launch command.

Keep new behavior in its owning module and leave the entry-point commands stable. Run the Python and browser tests after moving code across these boundaries.

## Requirements

- Python from a compatible F5-TTS environment
- The F5-TTS package, its dependencies, and a model checkpoint
- NumPy and SoundFile, as required by the installed environment
- FFmpeg on PATH for the optional 48 kHz stereo review copy

Follow the [upstream F5-TTS installation guide](https://github.com/SWivid/F5-TTS). Run this script with the Python interpreter in that environment. The local setup is not installed automatically by this tool.

## Manifest as source of truth

Start from narration_manifest.example.json and store the project manifest beside its local audio folders. Keep voice-reference audio and its exact spoken transcript private with the project; do not commit them to this repository.

Important fields:

- project: short folder-safe project name.
- project_status: in_progress while editing; set to complete only when pruning is intended.
- voice: default reference_audio path and exact reference_text.
- voice_styles: named reference recordings and their exact transcripts.
- settings: project-wide F5-TTS and assembly settings.
- selected_takes: maps stable segment IDs to selected take paths.
- segments: ordered array of narration beats. Array order controls playback order.
- status on each segment: active, inactive, or deleted.
- voice_style: optional key in voice_styles for a segment-specific delivery.
- tts: optional supported per-segment F5-TTS overrides.
- text_sha256 and root segments_sha256: generated and maintained by the tool; do not edit by hand.
- pruned_takes: retained metadata for removed take files.

A segment's id is a stable descriptive key, not its position. Reorder the array to change assembly order. Editing a segment's spoken text or generation settings invalidates its take fingerprint and triggers a new take on the next generation run. Reordering segments changes the assembly fingerprint but does not by itself regenerate the audio.

The supported tts overrides are speed, nfe_step, target_rms, cross_fade_duration, cfg_strength, sway_sampling_coef, and fix_duration. A voice_style selects a recording of the intended delivery; the label itself does not make F5-TTS perform an emotion.

## Quick transient preview

Use the optional preview when you want to hear a wording draft before making an F5-TTS take. It plays through Windows SAPI directly and does not create an audio file or alter the manifest. The current preview backend requires Windows, Windows PowerShell 5.1, and at least one installed SAPI voice. macOS and Linux are not supported by this preview command; it exits with an explanation and does not switch to another engine.

Preview a manifest segment by its stable ID. Active and inactive segments are allowed; deleted, missing, and duplicate IDs are rejected:

    python tools/audio_narration_generator/preview_narration.py --manifest path/to/audio/narration_manifest.json --segment-id opening-hook

Preview text that is not in the manifest yet:

    python tools/audio_narration_generator/preview_narration.py --text "Try this wording before adding it to the manifest."

For longer or multiline drafts, `--text -` reads UTF-8 from standard input:

    $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    Get-Content -Encoding UTF8 draft.txt -Raw | python tools/audio_narration_generator/preview_narration.py --text -

List installed SAPI voices, then optionally select one by its exact name. SAPI rate ranges from -10 to 10, with 0 as the default:

    python tools/audio_narration_generator/preview_narration.py --list-voices
    python tools/audio_narration_generator/preview_narration.py --text "A quick voice check." --voice "Microsoft Zira Desktop" --rate 1

The default Windows SAPI voice and rate are only for a quick wording and pacing check. They do not use manifest `voice_style` or `tts` settings, do not sound like the F5-TTS actor reference, and do not model its delivery. SAPI output is not a production take. For an approved line, use the normal F5-TTS generation and review workflow below.

The preview process sends text only to the local Windows speech API. It does not load F5-TTS, start FFmpeg, write temporary audio, receipts, logs, or caches, or update hashes, takes, assembly records, or any manifest field.

## Script and audio workbench

The local workbench is a browser interface around `narration_manifest.json` and this generator. It does not create another script source or take system.

### Segment layers

A segment (called a **beat** in the workbench) is the stable unit that ties four production layers together: **script text and narration audio**, **visual**, **music**, and **SFX**. The manifest's segment ID and spoken order are the shared identity and sequence. A layer can be empty; adding music or SFX must not change the spoken words or regenerate a narration take.

Today, approved text, narration settings, and selected takes live in `audio/narration_manifest.json`; optional visual planning lives in `audio/visuals/<segment-id>.json`. Music and SFX mappings are **planned, not implemented**. They will be separate project-local JSON files keyed by the same segment ID, referencing reviewed audio assets kept with the video project. Creating a mapping will not download assets, mix audio, or render video. See the [segment layers and workbench layout task order](../../docs/TASKS/TASK-ORDER_SEGMENT_LAYERS_AND_WORKBENCH_LAYOUT.md) for the proposed storage, controls, and acceptance checks.

### Start it

From the public repository root, select one project's manifest and start the server:

```powershell
python tools/audio_narration_generator/workbench.py `
  --manifest 'C:\path\to\video-project\audio\narration_manifest.json'
```

Open `http://127.0.0.1:8766`. Stop the server with `Ctrl+C`. The server binds only to `127.0.0.1` and serves only the project selected when it starts. It does not offer a project-picker or listen on the local network.

The workbench uses the Python standard library. Install and sign in to the [Codex CLI](https://developers.openai.com/codex/cli) to use **Ask Codex**. For persistent F5-TTS generation, pass the Python executable from the compatible F5-TTS environment if it is not the interpreter you used to start the workbench:

```powershell
python tools/audio_narration_generator/workbench.py `
  --manifest 'C:\path\to\video-project\audio\narration_manifest.json' `
  --python 'C:\path\to\f5-tts\python.exe'
```

### Work on a segment

1. Select a beat from the list. Its position in the manifest array is its narration order.
   Use the up and down buttons beside the selected beat's status to move it among the beats currently shown. The manifest array is updated, so the next assembly uses the new order without regenerating unchanged takes. Inactive and deleted beats are hidden from the list by default; use **Show inactive** and **Show deleted** to find and edit them. Hiding a beat in the list does not change its manifest status.
   Hover over a beat and press the **+** button beside it to add a new beat directly after it. Enter a title and spoken words, then choose active or inactive. Saving creates a stable ID from the title (with a numeric suffix if needed); later title edits do not change that ID. A new beat needs its own take when active, and the assembled narration becomes out of date.
2. Edit its title or spoken words, choose `active`, `inactive`, or `deleted`, and optionally select a voice profile or adjust supported TTS overrides. Save the segment to update the manifest. Unknown manifest fields and IDs are preserved.
3. Save an editorial note in the temporary work queue. To request wording help, press **Ask Codex**. The interface shows the exact segment and nearby text that will be sent.
4. Review Codex's proposed wording beside the original. You can audition the proposal on supported systems. Accepting it is the only way a suggestion changes the manifest; dismissing it leaves the spoken words alone.
5. Use **Generate missing or changed takes** to run the existing generator's incremental path. It reuses current takes and only renders active segments whose text or generation settings need a new take. Use **Assemble active segments** to create the review narration after the selected takes are ready. For a quick temporary voice, choose a beat and press **Preview SAPI fast** in the header on Windows. For the selected F5-TTS voice, press **Build + play F5-TTS** in the header. That button regenerates stale active takes, assembles only when the selected takes or beat order changed, then plays from the selected beat. Both players follow the audio through later beats; click again to pause and resume. Save unsaved script edits and notes before starting.
6. Open the **F5-TTS** tab to review the selected take for the beat. Other takes stay collapsed under **Show other takes** until needed. Use each take's **Rating** menu to choose Favorite, Acceptable, or Rejected; the workbench saves the review to that segment's `take_reviews` entry in `narration_manifest.json` and keeps any existing note. Rating a take does not select it or change the audio. Each available take also shows its note, playable audio, and parent folder path with a **Copy path** button for opening that folder in Explorer. Pruned takes retain their review record but have no playable file or folder link. Expand **Voice and speech settings** there to change the next render. The header's **Build + play F5-TTS** button plays the assembled narration; the page checks both the manifest array hash and the selected-take set recorded with the last successful assembly before labeling it current.

Manual segment edits are saved with a manifest-byte hash check. If another editor changes the file at the same time, the workbench refuses to overwrite it and asks you to reload. Suggestions also store the exact selected-text hash used at request time. If that text changes while Codex is working or before acceptance, the suggestion is marked stale and cannot be applied.

### Visual plan for a beat

The header's **Visual for beat …** selector is tied to the currently selected segment. Choose a recipe from the tracked [Visual Animations Library](../../libraries/visual_animations_library/README.md), or keep **Custom plan (no library recipe)**, then choose **Create visual JSON**. The workbench creates `audio/visuals/<segment-id>.json` in the selected project. The stable manifest ID is used for the filename and recorded inside the plan; recipes remain references to library entries rather than copied code.

Each beat gets one file. A second create request will not replace it; use **Open JSON** to open the existing file in the operating system's default app. After editing it outside the workbench, use **Reload manifest** to refresh its displayed status. If the approved spoken words later change, the workbench marks the plan **Needs review** using its saved source-text SHA-256. It does not rewrite the plan. Invalid, oversized, or unavailable plan files are reported instead of being treated as rendered visuals.

The plan's version-1 format is defined in [`visual_plan.schema.json`](visual_plan.schema.json). Custom plans use `null` for both recipe fields; library plans require both a recipe ID and title. The workbench also checks that the recipe ID still exists in the local library. The file is renderer-neutral planning data only: creating or editing it does not change the narration manifest, regenerate audio, render frames, or add it to a video. Rendering and in-app visual editing remain separate future work.

The workbench rejects its own manifest edits while its generator or assembly process is running. Do not run a separate generator CLI against the same manifest at the same time; a separate process does not share the workbench lock. To force another take of unchanged wording or select an older take, use the generator CLI and manifest procedure below.

### Codex connection and privacy

**Ask Codex** starts one local `codex exec` request per click. It uses an ephemeral session, read-only sandbox, structured JSON output, ignores the Codex user configuration, and starts in an empty temporary working directory. It keeps Codex authentication but does not load custom providers, profiles, MCP servers, hooks, or rules from `config.toml`. It does not connect to the current Codex chat conversation. The [Codex CLI documentation](https://developers.openai.com/codex/cli) describes `codex exec` for bounded command-line tasks; the workbench uses it as a small suggestion request rather than granting the model a project workspace.

The request contains the selected segment ID and title, its spoken text, your note, the immediately previous and next segment text when available, and the generic tracked [`ai_guide.json`](ai_guide.json). It excludes the full manifest, unrelated segments, project paths, voice-reference audio and transcripts, takes, and performance records. The UI has **Review what Codex receives** so you can inspect the project text before sending it. The response is schema-checked and stored in `audio/.workbench/workbench_state.json`; no response edits the manifest before you accept it.

The workbench currently supports Codex CLI only. Claude is not configured or tested. If Codex is unavailable, the note remains in the local work queue and the manifest is unchanged.

### Temporary work state and platform limits

The work queue is saved to `audio/.workbench/workbench_state.json`. It stores segment notes, suggestions, review status, timestamps, and the base text hash for each suggestion. This public repository ignores `.workbench`; if a video project lives in another Git repository, add `**/.workbench/` to that repository's `.gitignore` too. Save a note before switching beats or running generation; the interface warns before discarding an unsaved note. Use **Clear resolved suggestions** to remove accepted, dismissed, and stale suggestion records; notes and pending suggestions stay. Removing this folder manually also clears the work queue without affecting narration.

Quick preview uses the existing Windows SAPI preview and creates no audio file. It is unavailable on macOS and Linux; the workbench reports that limit without choosing another engine. Persistent F5-TTS generation remains available on systems where the user has installed its compatible environment. The app does not bundle F5-TTS, models, or voice recordings.

The web API exposes only the manifest-backed segment fields needed by the interface, parent folder paths for discovered take files, confined take/assembled WAV playback routes, and visual-plan operations constrained to the selected project's `audio/visuals/` folder. It does not expose a general path or file browser. Never change the bind address from loopback.

### Data boundary

| Data | Stored where | Included in narration hashes? |
|---|---|---|
| Approved script, segment order/status, voice style, TTS settings | Project `audio/narration_manifest.json` | Text and delivery settings affect take fingerprints; array order and status affect the assembly hash |
| Editorial notes and suggestions | Project `audio/.workbench/workbench_state.json` | No |
| Per-beat visual animation plans | Project `audio/visuals/<segment-id>.json` | No |
| Selected takes, receipts, assembly, and performance records | Project audio folders managed by the existing generator | Existing generator behavior |
| Generic editing rules and response schema | Public tool folder in this repository | No project data |

The workbench tests are included in the normal suite:

```powershell
python -m unittest discover -s tools/audio_narration_generator -p "test_*.py" -v
```

See the repository's [validation record](../../VALIDATION.md#addendum-transient-narration-preview-2026-11-22) for a local latency comparison and its limits. The measured SAPI progress callback is a proxy for audible onset; it was not verified with loopback capture.

### Starter manifest and voice references

`narration_manifest.example.json` is the generic starter template included with this tool. It contains placeholder transcripts and paths, not a ready-to-use speaker profile. This repository does not include channel-specific templates or voice recordings. Copy the example into each video project's `audio/` folder, then replace the sample values with references you are allowed to use.

Keep reference recordings beside the project when you want the project to move as a unit. Reference paths can be relative to `narration_manifest.json` or absolute. For example, with `audio/reference_audio/default.wav`, set `voice.reference_audio` to `reference_audio/default.wav`. Absolute paths work on the current machine but usually need editing if the project moves to another computer or folder.

The root `voice` object is the fallback profile. Each named entry in `voice_styles` is another profile, with its own `reference_audio` and the exact `reference_text` spoken in that clip. Put a profile key in a segment's `voice_style` to select it; `null` selects the root `voice`. Keep the cue directions used to record a sample out of `reference_text` unless they were actually spoken. The example's profile names are illustrative; create and name profiles for your own recordings.

## Workflow

1. Copy narration_manifest.example.json to the project's audio folder.
2. Add segment objects in playback order and set their IDs, text, status, voice style, and optional TTS overrides.
3. Add local reference recordings and exact transcripts to voice or voice_styles.
4. Optionally listen to a draft through Windows SAPI without creating a file:

    python tools/audio_narration_generator/preview_narration.py --manifest path/to/audio/narration_manifest.json --segment-id opening-hook

   This quick preview is Windows-only and does not replace F5-TTS take generation or review.

5. Preview the work without loading the model:

    python tools/audio_narration_generator/generate_narration.py --manifest path/to/audio/narration_manifest.json --dry-run

6. Generate a new or stale take for one segment:

    python tools/audio_narration_generator/generate_narration.py --manifest path/to/audio/narration_manifest.json --segment opening-hook --generate-only

7. Generate all missing or stale active takes and assemble the selected active beats:

    python tools/audio_narration_generator/generate_narration.py --manifest path/to/audio/narration_manifest.json

8. Change status to inactive to keep a beat out of assembly while preserving its takes, or deleted to retire it from future use. Do not delete manifest history just to reorder the video.

The normal run reuses valid selected takes and generates only missing or stale active segments. The result includes a mono master and, when FFmpeg is available, a 48 kHz stereo review copy. Take receipts and run performance records are saved beside the project audio.

## Take review and pruning

Take review metadata can mark a take favorite, acceptable, or rejected without changing which take is selected. The workbench provides these ratings in the F5-TTS tab; the manifest remains the source of truth. Keep useful takes when revising a segment.

Pruning permanently removes unselected take WAV files and their receipts from disk. Before pruning, set project_status to complete and preview the removal:

    python tools/audio_narration_generator/generate_narration.py --manifest path/to/audio/narration_manifest.json --prune-unused --dry-run

After reviewing the list, run the same command without --dry-run. The manifest retains pruned-take metadata; no replacement takes are generated by the prune operation. Favorite takes and takes for inactive segments are preserved by the current pruning rules.

## Validation and privacy

The unit tests cover changed text and settings, ordering, take selection, inactive/deleted handling, and pruning behavior:

    python -m unittest discover -s tools/audio_narration_generator -p "test_*.py"

The generator writes local paths and voice-reference filenames into project receipts. Review and sanitize those records before sharing them. Do not include private narration manifests, voice recordings, transcripts, or generated audio in this repository.
