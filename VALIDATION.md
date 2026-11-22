# Validation Record

**Date:** 2026-11-21
**Scope:** Local public tool repository and a fresh local clone of commit 4ddde8f. Tests used the same workstation and installed runtimes. No user media, narration, or voice recordings were used.

## Checks run

| Check | Result |
|---|---|
| Python source compilation | Passed for the Python tool files |
| Audio Narration Generator unit tests | 11 tests passed in the working tree and fresh clone |
| Asset Finder help and source list | Passed in the fresh clone |
| Contact Sheet help and extraction | Passed in the fresh clone; a 2-second synthetic 160 × 90 clip yielded four samples and one contact sheet in 0.2 seconds |
| Word Focus Subtitles syntax and generation | Passed in the fresh clone; a 9-word generic sample produced a 3,102-byte ASS file |
| EffectCraft renderer PowerShell syntax | Passed in the fresh clone |
| Privacy scan | No personal names, absolute drive paths, or project identifiers found in the public tree |

## Test environment

- Python 3.12.7
- Node.js v22.22.2
- FFmpeg and FFprobe build dated 2024-09-26
- Hardware model and system memory were not recorded in the source benchmark notes.

The contact-sheet timing is only a synthetic smoke test, not a workload benchmark. Subtitle timing in the generated ASS is estimated from word count and is not a measured processing duration.

## Addendum: transient narration preview (2026-11-22)

- The Audio Narration Generator suite passed: 24 tests. The preview tests cover active/inactive/deleted/missing/duplicate segment behavior, UTF-8 input validation, a simulated unsupported Linux host, missing PowerShell, interruption handling, and read-only manifest lookup.
- Windows PowerShell 5.1 listed the installed SAPI voices. Inline preview and explicit voice/rate selection returned success; an invalid voice returned a concise error and exit code 2. One active segment from a local project manifest also previewed successfully; its SHA-256 was unchanged afterward. The spoken words are not recorded here. Physical speaker output was not independently confirmed with loopback capture.
- Three SAPI timing trials with the same short generic line measured PowerShell launch to first `SpeakProgress` callback at 1.024, 0.753, and 0.712 seconds (median 0.753 seconds). The short playback process completed in 3.422, 3.154, and 3.107 seconds (median 3.154 seconds). The callback is an approximate playback-start signal, not a loopback-confirmed audible onset.
- The existing F5-TTS environment (F5-TTS 0.3.4, PyTorch 2.3.0+cu118, CUDA available) generated the same short line in two isolated CLI processes using one local reference clip. The first process took 92.61 seconds from command launch until its WAV was ready; a second launch with the OS file cache warm took 40.24 seconds. Each process loaded the model again, so “warm” means a warmed file cache, not a resident F5 model. The tool's post-model-load segment processing times were 6.45 and 7.45 seconds; each WAV was 1.54 seconds long. Player startup was not measured. These are single workstation samples, not a general benchmark or voice-quality comparison.
- The F5 manifests, run records, and generated audio were isolated in a temporary directory and removed after measurement. No spoken text, private reference path, reference recording, or generated audio is included in this repository.
- The platform and PowerShell-missing cases were exercised with focused tests on Windows; macOS/Linux machines and a Windows machine without SAPI were not available for direct runtime testing. The preview's `finally` path disposes the synthesizer, but Ctrl+C cleanup was not separately signal-tested.

## Addendum: script and audio workbench (2026-11-22)

- Python compilation, JavaScript syntax checking, and `git diff --check` passed. The complete Audio Narration Generator test suite passed: 39 tests. New workbench coverage includes manifest conflict detection, unknown-field and order preservation, private voice-reference exclusion, project-audio path confinement, suggestion acceptance and stale handling, note persistence and cleanup, read-only Codex request construction, loopback host validation, assembly freshness against recorded selected takes, and the provider-unavailable path.
- Codex CLI 0.171.0 completed a live structured suggestion request with generic temporary sample text. A second live check exercised the local HTTP flow: the note was saved, the Codex suggestion appeared as pending while the manifest stayed unchanged, and only acceptance updated the manifest. The temporary project used no channel narration, voice recording, or private project paths and was removed after the check.
- After isolating the request from the Codex user configuration and its custom MCP/profile settings, a fresh live structured suggestion request also completed successfully. Codex authentication remained available.
- The local browser interface loaded successfully in Vivaldi from `127.0.0.1`. It displayed the selected project's segments, Codex CLI status, notes and suggestion review areas, settings controls, and narration actions.
- The workbench delegates persistent generation and assembly to the existing generator. Its generation route uses the generator's incremental mode; a live F5-TTS generation was not run through the browser interface. Existing generator tests cover changed-take regeneration and assembly. Browser-triggered SAPI playback was not separately run; transient-preview platform and CLI checks are recorded above.
- This workbench was tested on Windows with Python 3.12.7 and Codex CLI 0.171.0. macOS/Linux workbench startup was not directly tested; its HTTP app uses the Python standard library. The Windows SAPI preview remains unsupported on those systems. Claude support is not implemented, and the interface does not reorder manifest segments.
- All live suggestions used disposable generic text. No suggestion, note, voice reference, generated take, or project manifest was retained in this repository.

**Follow-up review, 2026-11-22:** The scoped commit and working tree were checked for unrelated changes. A second pass found and corrected result-panel visibility, unsaved-note handling, TTS number coercion, same-time assembly WAV selection, and workbench edit/generation concurrency. A regression test confirmed that editing a title preserves an unchanged take fingerprint. Python compilation, JavaScript syntax checking, and all 43 Audio Narration Generator tests passed after the changes. The live Codex request and browser layout checks above were not repeated; no F5-TTS model run was started for this review. The internal channel repository now ignores the project-local `.workbench` queue.

## Not covered

- No F5 model, reference recording, or project narration is included in this repository. See the transient-preview addendum for the separate, temporary local inference check.
- No real media was downloaded with Asset Finder.
- No full EffectCraft render was run from the migrated copy. The renderer passed a syntax check; its measured rendering results are recorded separately in the [benchmark summary](benchmarks/EFFECTCRAFT_RENDERING.md).
- No clean-machine installation test was completed. The fresh clone reused the installed runtimes on the same workstation.
- This validation run predates the GitHub publication. It does not claim a clean-machine installation.
