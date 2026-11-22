# Task Order: Transient Narration Preview

**Task ID:** ANG-001 | **Status:** Complete | **Last updated:** 2026-11-22

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

1. On Windows, list and select installed SAPI voices. Inline playback and one manifest-segment preview both returned success through the default device.
2. Unit tests confirm that an unsupported Linux platform and missing Windows PowerShell prerequisite produce nonzero errors without starting another engine. The script reports SAPI assembly/voice errors clearly. Actual macOS/Linux machines and a Windows machine without SAPI were not available for direct runtime tests.
3. Preview one active segment, one inactive segment, and inline text.
4. Confirm missing and deleted segment IDs fail clearly.
5. Compare the manifest before and after by file hash; it must remain byte-for-byte unchanged. Confirm that no preview audio or receipt is created in the project or operating-system temporary folders.
6. An invalid-voice error returned exit code 2, and the synthesizer is canceled/disposed in `finally`. Ctrl+C cleanup was not separately signal-tested.
7. A short-line timing check measured SAPI process launch to first `SpeakProgress` callback at a median 0.753 seconds. Isolated F5-TTS runs took 92.61 seconds to WAV-ready on the first process and 40.24 seconds on a second launch with file cache warm. The generated speech duration was 1.54 seconds; player startup was not measured. These measurements and environment limits are in the [validation record](../../../../VALIDATION.md#addendum-transient-narration-preview-2026-11-22). The SAPI callback is a proxy, not loopback-confirmed audibility.
8. The Audio Narration Generator test suite passed: 24 tests, including focused checks for platform detection, manifest lookup, status handling, UTF-8 input, and interruption reporting.

## Completion criteria

- A Windows user can audition manifest text or inline draft text without starting F5-TTS.
- No persistent audio or generated records are written, and the manifest remains unchanged.
- Active and inactive segments work; missing and deleted segments fail with useful messages.
- The public tool guide explains Windows and SAPI requirements, usage, voice/rate controls, and the limits of SAPI voice quality and delivery.
- Unsupported systems receive a clear, actionable message and nonzero exit without a silent fallback or file/manifest changes.
- Tests and the measured latency comparison are documented without including private narration, voice recordings, or generated audio. The measurements are a one-workstation check, not a general speed or voice-quality claim.

## Boundaries

This is a disposable listening aid, not a take-selection or production workflow. If a line is approved for the video, generate and review a numbered F5-TTS take through the normal manifest workflow.

## Implementation record

- Added `preview_narration.py` for CLI validation, read-only manifest segment lookup, and platform/prerequisite checks.
- Added `preview_narration.ps1` to call Windows SAPI, list installed voices, and speak through the default audio device. The synthesizer is canceled and disposed in a `finally` block.
- Added focused tests for active/inactive/deleted/missing/duplicate segment handling, input validation, unsupported OS behavior, and unchanged manifest bytes.
- Updated the tool guide and installation table with the Windows requirements and command examples.
- The active segment in a local project manifest previewed successfully, and its manifest hash remained unchanged. A short preview with an explicit voice/rate returned successfully; an invalid SAPI voice returned exit code 2.
- Matched short-line measurements: SAPI's first `SpeakProgress` callback occurred at 1.024, 0.753, and 0.712 seconds from PowerShell launch (median 0.753 seconds). F5-TTS generated a 1.54-second WAV in 92.61 seconds on its first process and 40.24 seconds on a second process with file cache warm. See the [validation addendum](../../../../VALIDATION.md#addendum-transient-narration-preview-2026-11-22) for environment details and limits.
- All benchmark manifests, records, and generated audio were removed with the temporary workspace. No private narration or voice recording is included in the repository.
