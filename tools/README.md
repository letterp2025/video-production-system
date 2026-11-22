# Tool Index

Runnable utilities are under this folder. The two research folders describe options and tests; they do not contain a finished production tool.

| Tool | Type | What it does | Guide |
|---|---|---|---|
| Asset Finder | Runnable Python CLI | Searches Openverse and Wikimedia Commons; downloads a selected item with a metadata receipt after manual terms review | [README](asset_finder/README.md) |
| Audio Narration Generator | Runnable Python CLI and local web app | Creates and tracks F5-TTS takes from an ordered JSON manifest; the local workbench edits narration, keeps temporary notes, reviews Codex suggestions, and assembles selected takes | [README](audio_narration_generator/README.md) |
| Contact Sheet | Runnable Python CLI | Extracts sampled frames and lays them out with timecodes | [README](contact-sheet/README.md) |
| EffectCraft Section Renderer | Runnable PowerShell script | Renders sections, encodes with FFmpeg, validates output, resumes completed work, and writes run records | [README](effectcraft_ffmpeg_sections/README.md) |
| Library Browser | Runnable Python local web app | Browses public visual libraries and an explicitly configured private library root without modifying entries | [README](library-browser/README.md) |
| Word Focus Subtitles | Runnable Node.js script | Creates an ASS file that changes the active word over time | [README](word-focus-subtitles/README.md) |
| Raster-to-Vector | Study | Records an external tracing and EffectCraft SVG-to-shape experiment and its limits | [README](raster-to-vector/README.md) |
| Music and SFX Generator Options | Study | Compares possible tools; custom synthesis remains deferred | [README](music_sfx_generator/README.md) |

Read [Installation](../INSTALLATION.md) before setting up dependencies. Do not commit downloaded media, voice recordings, models, renders, caches, or project files to this repository.
