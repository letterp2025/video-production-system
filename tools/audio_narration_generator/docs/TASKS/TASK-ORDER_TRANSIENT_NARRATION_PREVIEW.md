# Task Order: Transient Narration Preview

**Task ID:** ANG-001 | **Status:** Next | **Last updated:** 2026-11-22

## Objective

Add an optional Windows preview command for quickly listening to draft narration without retaining an audio file or changing the narration manifest. Keep this audition path separate from F5-TTS take generation and assembly.

## Context

The Audio Narration Generator creates reviewable F5-TTS takes, receipts, and assembled WAV files. That is appropriate for production audio, but it adds setup and storage when someone only wants to hear a wording draft once.

Windows includes Microsoft SAPI voices that can speak directly to the default audio device. A prior local experiment used SAPI but wrote a WAV file, so it did not meet the transient-preview requirement. Do not describe it as faster than F5-TTS until the startup-to-first-audible-output comparison has been measured.

## Proposed interface and behavior

- Add a small Windows-only PowerShell script beside the existing tool, using the installed Windows `System.Speech.Synthesis.SpeechSynthesizer` API. State that Windows with the supported PowerShell and SAPI components is the current supported environment.
- Support either:
  - a manifest path plus a stable segment ID, reading the segment's current `text`; or
  - inline text for a draft that is not in the manifest yet.
- Allow active and inactive segments to be previewed. Reject a missing ID or a segment with `status: "deleted"` with a clear error.
- Send speech directly to the default audio device. Let the user optionally select an installed SAPI voice and adjust the SAPI speaking rate.
- Stop playback and dispose the synthesizer cleanly when playback is interrupted or fails.
- Detect an unsupported operating system or unavailable PowerShell/SAPI prerequisite and return a concise, actionable error with a nonzero exit code. Do not silently switch engines or attempt audio-file output; leave the manifest and filesystem unchanged.
- Do not create WAV files, temporary files, take folders, receipts, caches, or logs containing the spoken text. Do not send text to a remote service.
- Do not load F5-TTS, invoke FFmpeg, or change the manifest, segment hashes, selected takes, assembled narration, or performance records.
- Treat manifest `voice_style` and `tts` fields as F5-TTS settings. They do not select SAPI voices or control SAPI delivery.

## Validation

1. On Windows, list or select an installed SAPI voice and confirm direct playback works through the default audio device.
2. On macOS, Linux, and Windows without the required PowerShell/SAPI components, confirm the command reports that the current preview backend is unsupported and gives a useful next step. It must not create files or modify a manifest.
3. Preview one active segment, one inactive segment, and inline text.
4. Confirm missing and deleted segment IDs fail clearly.
5. Compare the manifest before and after by file hash; it must remain byte-for-byte unchanged. Confirm that no preview audio or receipt is created in the project or operating-system temporary folders.
6. Test interruption and error cleanup.
7. Measure time from command start to first audible output for a short passage. Compare SAPI with F5-TTS cold-start and warm-start runs, separating synthesis/startup latency from speech playback duration. Keep the measurement method and environment in the appropriate validation notes; do not retain preview audio or narration text.
8. Run the existing narration-generator tests plus focused checks for platform detection, manifest lookup, status handling, and command input validation.

## Completion criteria

- A Windows user can audition manifest text or inline draft text without starting F5-TTS.
- No persistent audio or generated records are written, and the manifest remains unchanged.
- Active and inactive segments work; missing and deleted segments fail with useful messages.
- The public tool guide explains Windows and SAPI requirements, usage, voice/rate controls, and the limits of SAPI voice quality and delivery.
- Unsupported systems receive a clear, actionable message and nonzero exit without a silent fallback or file/manifest changes.
- Tests and the measured latency comparison are documented without including private narration, voice recordings, or generated audio.

## Boundaries

This is a disposable listening aid, not a take-selection or production workflow. If a line is approved for the video, generate and review a numbered F5-TTS take through the normal manifest workflow.
