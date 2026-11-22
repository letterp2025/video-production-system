# Audio Narration Generator

Generate separately reviewable F5-TTS narration takes from an ordered JSON manifest, reuse unchanged takes, and assemble the selected active takes into a WAV review track.

The generator does not bundle F5-TTS, a model checkpoint, or voice recordings. Install and license those separately. Use reference audio only when you have permission to use it for speech generation.

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

Take review metadata can mark a take favorite, acceptable, or rejected without changing which take is selected. Keep useful takes when revising a segment.

Pruning permanently removes unselected take WAV files and their receipts from disk. Before pruning, set project_status to complete and preview the removal:

    python tools/audio_narration_generator/generate_narration.py --manifest path/to/audio/narration_manifest.json --prune-unused --dry-run

After reviewing the list, run the same command without --dry-run. The manifest retains pruned-take metadata; no replacement takes are generated by the prune operation. Favorite takes and takes for inactive segments are preserved by the current pruning rules.

## Validation and privacy

The unit tests cover changed text and settings, ordering, take selection, inactive/deleted handling, and pruning behavior:

    python -m unittest discover -s tools/audio_narration_generator -p "test_*.py"

The generator writes local paths and voice-reference filenames into project receipts. Review and sanitize those records before sharing them. Do not include private narration manifests, voice recordings, transcripts, or generated audio in this repository.
