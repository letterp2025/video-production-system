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

### Starter manifest and voice references

`narration_manifest.example.json` is the generic starter template included with this tool. It contains placeholder transcripts and paths, not a ready-to-use speaker profile. This repository does not include channel-specific templates or voice recordings. Copy the example into each video project's `audio/` folder, then replace the sample values with references you are allowed to use.

Keep reference recordings beside the project when you want the project to move as a unit. Reference paths can be relative to `narration_manifest.json` or absolute. For example, with `audio/reference_audio/default.wav`, set `voice.reference_audio` to `reference_audio/default.wav`. Absolute paths work on the current machine but usually need editing if the project moves to another computer or folder.

The root `voice` object is the fallback profile. Each named entry in `voice_styles` is another profile, with its own `reference_audio` and the exact `reference_text` spoken in that clip. Put a profile key in a segment's `voice_style` to select it; `null` selects the root `voice`. Keep the cue directions used to record a sample out of `reference_text` unless they were actually spoken. The example's profile names are illustrative; create and name profiles for your own recordings.

## Workflow

1. Copy narration_manifest.example.json to the project's audio folder.
2. Add segment objects in playback order and set their IDs, text, status, voice style, and optional TTS overrides.
3. Add local reference recordings and exact transcripts to voice or voice_styles.
4. Preview the work without loading the model:

    python tools/audio_narration_generator/generate_narration.py --manifest path/to/audio/narration_manifest.json --dry-run

5. Generate a new or stale take for one segment:

    python tools/audio_narration_generator/generate_narration.py --manifest path/to/audio/narration_manifest.json --segment opening-hook --generate-only

6. Generate all missing or stale active takes and assemble the selected active beats:

    python tools/audio_narration_generator/generate_narration.py --manifest path/to/audio/narration_manifest.json

7. Change status to inactive to keep a beat out of assembly while preserving its takes, or deleted to retire it from future use. Do not delete manifest history just to reorder the video.

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
