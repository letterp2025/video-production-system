# Installation

The tools in this repository are separate utilities. Install only the runtimes needed for the tools you plan to use. No media, EffectCraft application binary, F5-TTS model, or voice recording is bundled.

## Common prerequisites

### FFmpeg and FFprobe

The contact-sheet tool uses FFmpeg and FFprobe. The EffectCraft section renderer uses both for encoding, probing, and validation.

1. Start at the [official FFmpeg download page](https://ffmpeg.org/download.html). FFmpeg links Windows builds maintained by third parties; review the build provider and its terms.
2. Put the FFmpeg and FFprobe executables on PATH, or pass their full paths to the section-rendering script.
3. Confirm both commands are available:

    ffmpeg -version
    ffprobe -version

For HEVC encoding, check which encoder your build supports:

    ffmpeg -hide_banner -encoders | Select-String 'hevc_nvenc|libx265'

The renderer supports NVIDIA NVENC or libx265. Availability depends on the FFmpeg build and system.

### EffectCraft CLI

Install the desktop application and find the CLI for your platform using the [EffectCraft Guide](guides/EFFECTCRAFT_GUIDE.md#install-effectcraft). Windows MSI packages include the CLI, but do not add it to PATH by default. The section renderer accepts its full path through the EffectCraft parameter. macOS provides the CLI as a separate download; on Linux, its location depends on the package format.

The CLI and GUI are upstream EffectCraft components; this repository does not package them.

## Tool-specific requirements

| Tool | Requirements | Setup check |
|---|---|---|
| Asset Finder | Python 3.10 or newer; standard library only | Run the tool with --help and list its configured sources |
| Contact Sheet | Python 3.10 or newer, Pillow, FFmpeg, FFprobe | Install Pillow with python -m pip install Pillow, then run --help |
| EffectCraft Section Renderer | PowerShell 7 recommended, EffectCraft CLI, FFmpeg, FFprobe | Parse the PowerShell script and verify all three executables are discoverable |
| Word Focus Subtitles | Node.js 18 or newer; no npm packages | Run node generate.mjs --help |
| Audio Narration Generator | Python 3.10+ for the local workbench; Codex CLI signed in for AI suggestions. Persistent F5-TTS generation needs a compatible F5-TTS environment and FFmpeg for stereo review copies. Optional transient preview: Windows, Windows PowerShell 5.1, and an installed SAPI voice | Run the workbench with a selected manifest. Point `--python` to the compatible F5-TTS interpreter for persistent generation. The Windows-only quick preview needs no F5-TTS model. |
| Raster-to-Vector study | Optional VTracer and EffectCraft CLI | The study describes a tested bridge; it is not a packaged end-to-end tool |
| Music and SFX study | No software required to read the guide | No generator has been selected |

Python downloads are available from [python.org](https://www.python.org/downloads/). Pillow installation instructions are in the [Pillow documentation](https://pillow.readthedocs.io/en/stable/installation.html). Node.js downloads are available from [nodejs.org](https://nodejs.org/en/download). PowerShell documentation is at [Microsoft Learn](https://learn.microsoft.com/powershell/).

## First checks

Run these from the repository root in PowerShell:

    python --version
    node --version
    ffmpeg -version
    ffprobe -version
    Get-Command effectcraft-cli.exe -ErrorAction SilentlyContinue

The tools that use external software accept normal local file paths. Keep project media and generated audio, frames, contact sheets, and videos with the project that owns them. Review source-item licenses before using or redistributing discovered media.
