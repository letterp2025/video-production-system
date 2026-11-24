# Audio Narration Generator

Generate separately reviewable F5-TTS narration takes from an ordered JSON manifest, reuse unchanged takes, and assemble the selected active takes into a WAV review track.

The generator does not bundle F5-TTS, a model checkpoint, or voice recordings. Install and license those separately. Use reference audio only when you have permission to use it for speech generation.

## Code layout

The command-line entry points remain `generate_narration.py`, `workbench.py`, and `preview_narration.py`.

- `narration_manifest.py` owns manifest validation and shared field rules; `generate_narration.py` owns take generation, pruning, and assembly.
- `workbench_common.py` owns shared limits, errors, and atomic JSON helpers. `workbench_project.py` owns manifest-backed editing and the temporary work queue.
- `workbench_sequence.py` owns project-root video order, visual-only units, planned durations, and migration from an existing narration manifest.
- `workbench_visual_takes.py` and `workbench_visual_requests.py` own whole-spine visual takes and their request/result handoff; `workbench_visuals.py` owns the legacy per-beat visual-plan files; `workbench_narration_requests.py` owns provider-neutral narration request/result files; `workbench_audio.py` owns take and assembly lookup.
- `workbench.py` owns the local HTTP routes and launch command. Its optional Codex CLI adapter processes the same saved narration request used by terminal AI tools.

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

The project-root [`sequence_manifest.json`](sequence_manifest.schema.json) is now the workbench's canonical video order. It is initialized once from all narration segments when absent; an existing invalid file is never replaced. Each unit has a stable ID and editable planned `duration_seconds`. Narration units point to real narration IDs; visual-only units have their own title and optional note, but no spoken text or audio take. The left Sequence rail can add, edit, and move visual-only units. Narration playback remains speech-only and skips their planned intervals. When a narration segment is added through the workbench, VPS links it into the sequence; external additions appear as unlinked until explicitly linked. A speech-order mismatch is flagged, with an explicit sync action before playback.

Visual takes and repeated visual requests can target either kind of unit. For visual-only work, the request scaffold uses schema version 2 with `source_unit_sha256` and the result uses version 3; see [`visual_result_visual_only.schema.json`](visual_result_visual_only.schema.json). That hash reflects the unit's title, note, and planned duration, so changing those fields marks prior candidates for review. Narration requests and result JSON retain their existing contracts. Music item anchor field names remain `start_segment_id` and `end_segment_id`, but resolve against sequence-unit IDs and can include visual-only units. The sequence manifest is an NLE planning handoff, not an edit decision list or rendered video.

A narration segment is the stable unit for spoken words and audio. A sequence unit can instead be visual-only. The Visual Layer can keep optional SFX beside the visual request they support. Music is one project-wide list whose items start and end on stable sequence-unit boundaries. The shared context strip shows the selected unit's title and stable ID across Script and Narration, Visual, and Music.

Approved text, narration settings, and selected narration takes live in `audio/narration_manifest.json`. New visual work uses whole-video take manifests in the project's `visual_layer/` folder, keyed by sequence-unit IDs; the selected take is recorded separately. Older `audio/visuals/<segment-id>.json` files remain untouched but have no workflow in the current interface. Project-wide music items live in `audio/music/manifest.json`; older per-beat music JSON files remain untouched and are not shown. Sound effects are optional JSON files attached to individual visual requests. See the [sequence task order](../../docs/TASKS/TASK-ORDER_PROJECT_SEQUENCE_MANIFEST.md) for the new order contract.

The selected-sequence workspace has three top-level tabs: **Script and Narration Layer**, **Visual Layer**, and **Music Layer**. **Scratchpad** and **F5-TTS** are nested under Script and Narration. Visual Layer holds visual requests and optional candidate-specific SFX JSON. The previous per-segment SFX mapping and visual-plan panels are no longer shown. Music is project-wide, and each item's start and end anchors display both the stable sequence-unit ID and current unit title. See the [segment layers task order](../../docs/TASKS/TASK-ORDER_SEGMENT_LAYERS_AND_WORKBENCH_LAYOUT.md).

On workbench startup, VPS creates a starter `video_project.json` at the selected video's root if the file is missing. It never overwrites an existing file. The starter includes the project idea and creative direction, a free-form narration outline, inspiration lists (narration samples, YouTube videos, artists, and other references), project-status fields, and an unset optional narration default voice. Status values begin as `not_assessed`; they are context for the user and Codex, not automatically synchronized progress indicators. Update the JSON as the project develops.

Use **Project manifest** in the header to open a read-only modal showing all fields from that root file. The manifest is the project's creative brief and context for the user and Codex; it does not replace the detailed layer manifests. Edit the file with your usual editor or terminal Codex session, then reload the modal to see changes.

### Start it

From the public repository root, select one project's manifest and start the server:

```powershell
python tools/audio_narration_generator/workbench.py `
  --manifest 'C:\path\to\video-project\audio\narration_manifest.json'
```

Open `http://127.0.0.1:8766`. Stop the server with `Ctrl+C`. The server binds only to `127.0.0.1` and serves only the project selected when it starts. It does not offer a project-picker or listen on the local network.

The workbench uses the Python standard library. Codex CLI is optional; install and sign in to the [Codex CLI](https://developers.openai.com/codex/cli) only if you want the optional **Run with Codex CLI** action. For persistent F5-TTS generation, pass the Python executable from the compatible F5-TTS environment if it is not the interpreter you used to start the workbench:

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
3. Save an editorial note, then press **Create AI request JSON**. VPS writes a unique `request.json` and a separate `result.json` scaffold under `audio/narration_requests/<stable-segment-id>/requests/SCR-001/`. Use the request from your terminal with Codex, Claude, or another AI assistant; it is provider-neutral and includes the full root project manifest, selected line and note, adjacent lines, and generic AI guide. The external assistant fills `result.json`; it does not edit the approved narration manifest.
4. Return to VPS and press **Refresh AI results**. A completed result appears beside the original wording for review. You can audition the proposal on supported systems. Accepting it is the only way a suggestion changes the manifest; dismissing it leaves the spoken words alone. Each new request gets a distinct ID so previous attempts remain available.
5. Optional: when Codex CLI is installed, each pending request also offers **Run with Codex CLI**. This launches one bounded local `codex exec` for that already-created request and writes its output into the same `result.json` format. No Codex server is hosted or required.
6. Use **Generate missing or changed takes** to run the existing generator's incremental path. It reuses current takes and only renders active segments whose text or generation settings need a new take. Use **Assemble active segments** to create the review narration after the selected takes are ready. For a quick temporary voice, choose a beat and press **Preview SAPI fast** in the header on Windows. For the selected F5-TTS voice, press **Build + play F5-TTS** in the header. That button regenerates stale active takes, assembles only when the selected takes or beat order changed, then plays from the selected beat. Both players follow the audio through later beats; click again to pause and resume. Save unsaved script edits and notes before starting.
7. Use the top-level **Script and Narration Layer** tab for the segment editor and narration tools. **Scratchpad** and **F5-TTS** are nested tabs on its right side. In Scratchpad, the small direction buttons append editable instructions to your note; they do not save it, create a request, or change the approved narration. In **F5-TTS**, review the selected take; other takes stay collapsed under **Show other takes** until needed. Use each take's **Rating** menu to choose Favorite, Acceptable, or Rejected; the workbench saves the review to that segment's `take_reviews` entry in `narration_manifest.json` and keeps any existing note. Rating a take does not select it or change the audio. Each available take also shows its note, playable audio, and parent folder path with a **Copy path** button for opening that folder in Explorer. Pruned takes retain their review record but have no playable file or folder link. Expand **Voice and speech settings** there to change the next render. The global **Build + play F5-TTS** button plays the assembled narration; the page checks both the manifest array hash and the selected-take set recorded with the last successful assembly before labeling it current.

Manual segment edits are saved with a manifest-byte hash check. If another editor changes the file at the same time, the workbench refuses to overwrite it and asks you to reload. Suggestions also store the exact selected-text hash used at request time. If that text changes while an AI is working or before acceptance, the suggestion is marked stale and cannot be applied.

### Whole-spine visual takes

Use **Visual Layer** to create a take for an entire video treatment, not just the currently selected unit. A project can have several alternatives (`v_layer_1`, `v_layer_2`, and so on); each take is an independent JSON manifest that defines its overall direction and indexes stable sequence-unit IDs. A unit may be linked to narration or be visual-only. Each unit's custom visual brief and optional library references are stored in separate request JSON; result JSON records Codex's status and output paths. The workbench creates an entry for every current sequence unit, selects the new take, and never replaces an existing take with the same ID. The project-root `sequence_manifest.json` owns story order and planned durations; the detailed folder tree is in the [video workflow guide](../../guides/VIDEO_PRODUCTION_WORKFLOW.md#project-folder-structure).

```text
video-project/
├── audio/
│   └── narration_manifest.json
└── visual_layer/
    ├── selected_take.json
    ├── v_layer_1.json                 # one whole-video direction
    ├── v_layer_1/
    │   └── segments/
    │       └── opening-hook/          # stable sequence-unit ID (narration-linked in this example)
    │           └── requests/
    │               └── VIS-001/
    │                   ├── request.json
    │                   ├── result.json
    │                   ├── sfx.json   # optional
    │                   └── implementation/  # terminal Codex output
    └── v_layer_2.json                 # another whole-video direction
```

Each take manifest is the whole-video direction and an index of stable sequence-unit IDs. Its `segments` JSON property and the `segments/<unit-id>/` directory name are retained for compatibility; entries can represent narration-linked or visual-only units. `selected_take.json` stores the selected manifest filename; it is not another take. For new work, a unit's brief and optional library references live in its `request.json`; a separate `result.json` records status and project-relative implementation, preview, and export paths. Elements and animations are normally custom to the video project. Older take manifests may still contain direct implementation fields, but the current request workflow does not require them. The workbench checks paths remain project-relative and do not cross symlinks; it does not execute referenced code.

In **Visual Layer**, first select a take to apply it across the whole video sequence. If there is no take yet, choose **Create a visual take** and enter a take ID, name, and direction. Select a narration-linked or visual-only unit in the Sequence rail; its stable ID appears above its request history. Choose **Add visual request** and describe what you want Codex to make. The direction buttons append editable starting points to the brief; they do not create request JSON until you choose **Create request JSON**. **Use this reference** asks you to attach a Visual Library entry first. A renderer preference and library references are optional. Expand **Use a Visual Library reference** to browse Public/Private and References/Elements/Animations, search, inspect notes and previews, and attach entries with a note. The browser only reads catalog entries; the request JSON stores their scope, library category, stable entry ID, and your note. Start the workbench with `--library-config` pointing to a local Visual Library Browser JSON config to enable private entries. Without it, only public entries appear. Use **Open take JSON** only when you want to inspect or edit the whole-video take file directly. Use **Reload manifest** after terminal Codex changes `result.json`. Reordering units keeps visual mappings keyed to stable IDs; narration-linked moves also update speech order when every narration segment is linked. An externally added narration segment stays unlinked until explicitly added to the sequence.

Each request gets its own `visual_layer/<take-id>/segments/<unit-id>/requests/VIS-001/` folder with `request.json` and `result.json`. The brief is preserved when you create another request. The request also carries a `task` instruction that tells the terminal AI to keep the brief and narration manifest unchanged, work within that request folder, and update the paired result contract. A request can also have an optional `sfx.json`. Open the request JSON or let Codex in your terminal read it from the project folder. That Codex session can create the unit's implementation and export, then record status and project-relative output paths in `result.json`. Return to VPS and choose **Reload manifest** to see the updated result and select a completed visual. VPS does not start a Codex service or run the renderer.

Narration-linked requests start with the version-2 result contract in [`visual_result.schema.json`](visual_result.schema.json); visual-only requests use the [version-3 contract](visual_result_visual_only.schema.json). Preserve the take, unit, request, and appropriate source hash from the scaffold. Set `status` to `in_progress` while working and update `updated_at` (ISO 8601 with a timezone) whenever the result changes. On success, set `status` to `completed`, provide `completed_at`, and point `export_path` to the actual rendered unit file. On failure, set `status` to `failed` and explain it in `error`. `implementation_path` can point to a file or folder; `preview_path` and `export_path` must point to files. Any non-null output path must be project-relative, inside this request's folder, and already exist. A completed result is not selectable unless its export exists and its source hash still matches the current unit. VPS validates these rules but never runs or inspects renderer code.

Example completed `result.json`:

```json
{
  "schema_version": 2,
  "take_id": "v_layer_1",
  "segment_id": "found-effectcraft",
  "request_id": "VIS-001",
  "source_text_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "status": "completed",
  "implementation_path": "visual_layer/v_layer_1/segments/found-effectcraft/requests/VIS-001/implementation",
  "preview_path": "visual_layer/v_layer_1/segments/found-effectcraft/requests/VIS-001/exports/preview.mp4",
  "export_path": "visual_layer/v_layer_1/segments/found-effectcraft/requests/VIS-001/exports/segment.mp4",
  "provider": "Codex",
  "updated_at": "2026-11-23T10:08:00+00:00",
  "completed_at": "2026-11-23T10:08:00+00:00",
  "error": null
}
```

Version-1 result files from existing requests remain readable as legacy records, provided their request ID and paths validate; they are marked as legacy in the UI. New requests always use version 2. See [`visual_result.schema.json`](visual_result.schema.json) for both accepted formats and runtime-only path checks.

The take schema is [`visual_take.schema.json`](visual_take.schema.json); the selection-pointer schema is [`selected_visual_take.schema.json`](selected_visual_take.schema.json). Schema version is `1`. Do not place absolute machine paths or whole programs in JSON. Creating, selecting, or opening a take does not render frames or change narration. The workbench does not enforce renderer-specific launch conventions yet.

### Music and sound effects

The **Music Layer** creates and opens one project-wide `audio/music/manifest.json`. Terminal Codex can add, revise, or help source its items; use **Reload manifest** in VPS to see the latest list. Each item has an item ID and title, `start_segment_id`, and `end_segment_id`. These fields refer to sequence-unit IDs: an item begins at the start of its start unit and ends at the end of its end unit. Either unit may be visual-only. Optional `asset_path` points to a project-relative asset and optional `notes` keep concise planning context. Unit titles are resolved from `sequence_manifest.json` when displayed, so stable IDs remain the source of truth after title edits or reordering. See [`music_manifest.schema.json`](music_manifest.schema.json) for the data contract.

Example item:

```json
{
  "id": "MUS-001",
  "title": "Opening bed",
  "asset_path": "assets/audio/music/opening-bed.wav",
  "start_segment_id": "opening-hook",
  "end_segment_id": "project-overview",
  "notes": "Codex: choose a restrained, warm instrumental bed."
}
```

An empty `items` array is valid before music is chosen. The workbench checks the manifest shape, known sequence-unit IDs, story order, and project-relative asset paths; it does not verify file existence, provenance, license, or usage rights. The existing `start_segment_id` and `end_segment_id` property names refer to IDs in `sequence_manifest.json`, including visual-only units. Asset Finder can be used separately when sourcing. The manifest does not trigger downloads, playback, mixing, or rendering. Overlaps and fades remain future composition decisions. Standalone `audio/sfx/<segment-id>.json` mappings and older per-segment music mappings are legacy files, are not exposed in the current interface, and are not migrated or deleted. Optional sound effects are attached to a visual request as `sfx.json`, keeping them beside the visual candidate they support.

### Older visual plan files

The former per-beat recipe workflow stored files at `audio/visuals/<segment-id>.json`. The current Visual Layer does not create, open, or display those files. Existing files remain in the project folder without migration or deletion; new work belongs in `visual_layer/`.

The workbench rejects its own manifest edits while its generator or assembly process is running. Do not run a separate generator CLI against the same manifest at the same time; a separate process does not share the workbench lock. To force another take of unchanged wording or select an older narration take, use the generator CLI and manifest procedure below.

### AI request and privacy

The primary workflow is a project-local file handoff, not a hosted AI service. Every request has a distinct ID and lives beside its result:

```text
audio/
├── narration_manifest.json
└── narration_requests/
    └── <stable-segment-id>/
        └── requests/
            └── SCR-001/
                ├── request.json
                └── result.json
```

`request.json` is created by VPS and should be treated as the preserved brief. Its `project_context` contains the full root `video_project.json` so the AI sees the project idea, direction, narration outline, status, inspiration, and any user-added context. It also contains the target stable segment ID, source-text hash, title and words, your note, only the immediate previous/next words, and the generic tracked [`ai_guide.json`](ai_guide.json). The full root project manifest is part of the request, so review it before using an external AI provider. VPS does not copy `narration_manifest.json`, audio files, takes, or unrelated narration segments into the request. `result.json` is a separate response and progress record. A terminal AI of the user's choice reads the request and updates the paired result file. Use **Refresh AI results** to import completed proposals. VPS checks that the request and result identities and source hash match, and detects if the approved words have changed since the request. See [`narration_request.schema.json`](narration_request.schema.json) and [`narration_result.schema.json`](narration_result.schema.json).

#### Request and result examples

Each request is stored under the selected segment's stable ID. The request ID increments for each attempt; creating another request preserves earlier files:

```text
audio/narration_requests/<stable-segment-id>/requests/SCR-001/
├── request.json
└── result.json
```

Example `request.json` (shortened for readability; in a real request, `project_context` and `ai_guide` contain their full objects):

```json
{
  "schema_version": 1,
  "request_id": "SCR-001",
  "segment_id": "found-effectcraft",
  "created_at": "2026-11-23T10:00:00+08:00",
  "source_text_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "task": "Suggest a complete replacement for this segment while preserving its meaning and natural spoken voice. Do not edit narration_manifest.json or any other project file. Write the response only to the paired result.json, preserving its identity and source hash.",
  "project_context": {
    "project_title": "EffectCraft introduction",
    "project_idea": {
      "summary": "Explain the project in a friendly way.",
      "creative_direction": "Warm and conversational."
    }
  },
  "context": {
    "segment_id": "found-effectcraft",
    "title": "Finding EffectCraft",
    "text": "I found EffectCraft. It's free and open source.",
    "note": "Add a little context before the reveal.",
    "previous_text": null,
    "next_text": "It helps create motion graphics."
  },
  "ai_guide": {
    "purpose": "The full tracked narration editing guide is included here."
  }
}
```

VPS initially creates this `result.json` scaffold:

```json
{
  "schema_version": 1,
  "request_id": "SCR-001",
  "segment_id": "found-effectcraft",
  "source_text_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "status": "requested",
  "proposed_text": "",
  "rationale": "",
  "provider": null,
  "completed_at": null,
  "error": null
}
```

The external assistant should preserve the request ID, segment ID, and source hash; set status to `in_progress` while working; then set it to `completed` with `proposed_text`, `rationale`, `provider`, and `completed_at`. If it cannot finish, set status to `failed` and describe the issue in `error`. For example, a completed result looks like:

```json
{
  "schema_version": 1,
  "request_id": "SCR-001",
  "segment_id": "found-effectcraft",
  "source_text_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "status": "completed",
  "proposed_text": "I recently found EffectCraft, a free, open-source tool for making motion graphics.",
  "rationale": "Adds context before naming the tool.",
  "provider": "Claude",
  "completed_at": "2026-11-23T10:08:00+08:00",
  "error": null
}
```

The status values are `requested`, `in_progress`, `completed`, and `failed`. Only a valid `completed` result is imported as a suggestion. Refreshing may import it for review, but does not edit the narration manifest. After reviewing or auditioning the suggestion, **Accept** replaces only that segment's `text` in `audio/narration_manifest.json`; its stable ID, order, and other settings remain unchanged. Acceptance is refused if the source wording has changed since the request, and the suggestion is marked stale instead.

From the video-project root, a terminal AI can discover request files without relying on Git's untracked-file display:

```bash
rg --files --hidden --no-ignore -g 'request.json' audio/narration_requests
rg -n '"status"|"provider"|"completed_at"|"error"' audio/narration_requests -g 'result.json'
```

Git status can also show the new files when the video project is inside a Git repository and the paths are not ignored. The `rg` commands work independently of that condition.

For a manual handoff: review the request file, ask your chosen AI to follow its `task` field and use the supplied `video_project.json` plus selected-segment context, then have it update only the paired result file while preserving `request_id`, `segment_id`, and `source_text_sha256`. Keep its status current (`in_progress`, then `completed` or `failed`). Return to VPS and press **Refresh AI results**; after review, explicitly accept or dismiss the imported suggestion.

The optional **Run with Codex CLI** action uses the same saved request JSON, with one local `codex exec` in an ephemeral read-only sandbox and temporary working directory. It does not connect to a Codex server or the current Codex chat. The CLI option is secondary; terminal Codex, Claude, or any other AI that can read/write these JSON files can be used without VPS launching it. Neither path edits the narration manifest automatically. Suggestions must still be accepted in VPS. The [Codex CLI documentation](https://developers.openai.com/codex/cli) describes the optional CLI mechanism.

### Temporary work state and platform limits

The temporary review queue is saved to `audio/.workbench/workbench_state.json`. It stores segment notes, imported suggestions, review status, request-import markers, and the base text hash for each suggestion. This public repository ignores `.workbench`; if a video project lives in another Git repository, add `**/.workbench/` to that repository's `.gitignore` too. Save a note before switching beats or running generation; the interface warns before discarding an unsaved note. Use **Clear resolved suggestions** to remove accepted, dismissed, and stale suggestion records; notes and pending suggestions stay. This does not delete the project-owned files in `audio/narration_requests/`; those request/result records remain as the durable AI handoff history. Removing `.workbench` manually clears only the temporary review queue and does not affect narration or request files.

Quick preview uses the existing Windows SAPI preview and creates no audio file. It is unavailable on macOS and Linux; the workbench reports that limit without choosing another engine. Persistent F5-TTS generation remains available on systems where the user has installed its compatible environment. The app does not bundle F5-TTS, models, or voice recordings.

The loopback web API is scoped to the selected project's narration and layer workflows. The former per-beat visual-plan routes are not used by the current interface, and the API is not a general file browser. Never change the bind address from loopback.

### Data boundary

| Data | Stored where | Included in narration hashes? |
|---|---|---|
| Approved script, segment order/status, voice style, TTS settings | Project `audio/narration_manifest.json` | Text and delivery settings affect take fingerprints; array order and status affect the assembly hash |
| Editorial notes and suggestions | Project `audio/.workbench/workbench_state.json` | No |
| Video story order and planned duration | Project-root `sequence_manifest.json` | No |
| Whole-video visual takes and selection | Project-root `visual_layer/<take-id>.json` and `visual_layer/selected_take.json` | No |
| Per-unit visual requests/results and candidate SFX | Project `visual_layer/<take-id>/segments/<unit-id>/requests/<request-id>/` | No |
| Legacy per-beat visual plans | Project `audio/visuals/<segment-id>.json` | No |
| Project-wide Music items | Project `audio/music/manifest.json` | No |
| Candidate sound-effects cues | Optional project `visual_layer/<take-id>/segments/<unit-id>/requests/<request-id>/sfx.json` | No |
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

The root `voice` object in `audio/narration_manifest.json` remains the backward-compatible fallback. To choose one default voice for the whole video project, add this object to the root `video_project.json`:

```json
{
  "narration": {
    "default_voice": {
      "reference_audio": "audio/reference_audio/channel-voice.wav",
      "reference_text": "The exact words spoken in that reference recording."
    }
  }
}
```

That project-level profile overrides `audio/narration_manifest.json`'s top-level `voice` for every segment without a named style. Its relative `reference_audio` path is resolved from the video-project root; the older narration-manifest paths are resolved from the `audio/` folder. A segment with a named `voice_style` in `voice_styles` explicitly overrides both defaults. `default_voice: null` leaves the narration-manifest fallback in effect. When you change the effective voice profile, existing takes are detected as stale and must be regenerated before assembly. Keep the cue directions used to record a sample out of `reference_text` unless they were actually spoken. Because narration request JSON includes the full project manifest as AI context, review the reference transcript and other project details before sending a request to an external provider. The example's profile names are illustrative; create and name profiles for your own recordings.

## Workflow

1. Copy narration_manifest.example.json to the project's audio folder.
2. Add segment objects in playback order and set their IDs, text, status, voice style, and optional TTS overrides.
3. Add local reference recordings and exact transcripts to `video_project.json`'s `narration.default_voice` for the project default, or to the narration manifest's `voice`/`voice_styles` for legacy fallback and segment-specific styles.
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

Take review metadata can mark a take favorite, acceptable, or rejected without changing which take is selected. The workbench provides these ratings in the F5-TTS nested tab under Script and Narration Layer; the manifest remains the source of truth. Keep useful takes when revising a segment.

Pruning permanently removes unselected take WAV files and their receipts from disk. Before pruning, set project_status to complete and preview the removal:

    python tools/audio_narration_generator/generate_narration.py --manifest path/to/audio/narration_manifest.json --prune-unused --dry-run

After reviewing the list, run the same command without --dry-run. The manifest retains pruned-take metadata; no replacement takes are generated by the prune operation. Favorite takes and takes for inactive segments are preserved by the current pruning rules.

## Validation and privacy

The unit tests cover changed text and settings, ordering, take selection, inactive/deleted handling, and pruning behavior:

    python -m unittest discover -s tools/audio_narration_generator -p "test_*.py"

The generator writes local paths and voice-reference filenames into project receipts. Review and sanitize those records before sharing them. Do not include private narration manifests, voice recordings, transcripts, or generated audio in this repository.
