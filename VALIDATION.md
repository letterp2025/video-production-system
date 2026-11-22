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

## Not covered

- No F5-TTS inference was run; its models, reference recordings, and project narration are not part of this public copy.
- No real media was downloaded with Asset Finder.
- No full EffectCraft render was run from the migrated copy. The renderer passed a syntax check; its measured rendering results are recorded separately in the [benchmark summary](benchmarks/EFFECTCRAFT_RENDERING.md).
- No clean-machine installation test was completed. The fresh clone reused the installed runtimes on the same workstation.
- This validation run predates the GitHub publication. It does not claim a clean-machine installation.