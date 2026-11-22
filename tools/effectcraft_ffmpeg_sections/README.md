# EffectCraft Section Renderer

Render an EffectCraft composition in frame ranges, encode each range with FFmpeg, join the sections, optionally mux audio, validate the result, and save performance records.

The script is a Windows PowerShell utility. It invokes the EffectCraft CLI, FFmpeg, and FFprobe as separate local executables.

## Requirements

- PowerShell 7 recommended
- EffectCraft CLI
- FFmpeg and FFprobe
- A saved EffectCraft project and section manifest
- A video-project root with enough free space for the work files and final output

Put executable commands on PATH or supply explicit executable paths with -EffectCraft, -FFmpeg, and -FFprobe.

## Inputs

The section manifest is JSON with a sections array. Each section contains startFrame and endFrame. Ranges must be adjacent, nonempty, start at frame zero, and cover the intended output.

The project and its section manifest should live with the video project. Render settings are passed on the command line.

## Example

    pwsh -File tools/effectcraft_ffmpeg_sections/render-sections.ps1 -Project path/to/project.ecproj -Composition "Main Composition" -VideoProjectRoot path/to/video-project -BaseName scene-short-description -Tier HIGH -SectionsPath path/to/sections.json -Fps 60 -Width 3840 -Height 2160 -MaxTempBytes 20000000000 -ReserveBytes 5000000000

The final file is written under render/HIGH or render/LOW using the base name and tier suffix. Temporary section data and run.json are stored under the tier's .effectcraft-sections folder. A separate performance record is written under that tier's performance folder.

## Resume and storage controls

- Use -Resume to reuse completed sections from a matching run. The project, section ranges, settings, script, and tool fingerprints must match.
- Use -KeepPng to retain generated frames after a successful export.
- Set -MaxTempBytes for the temporary work folder and -ReserveBytes for the minimum free space to keep available on its volume.
- Use -Replace when intentionally replacing an existing final output or discarding a previous run identity.
- Use -Audio to provide a local audio file for muxing.
- Use -TestFailBeforeSection for a controlled resume test.

The script monitors its work folder and checks available disk space while rendering and encoding. MaxTempBytes limits the temporary work folder; it is not a whole-disk quota and does not include unrelated files or the final MP4 in the render folder. Choose a safe free-space reserve and inspect the run record. A process may write between polling intervals, so treat the value as a guardrail rather than a filesystem-enforced hard cap.

## Output review

The renderer checks frame ranges, stream dimensions and timing, audio duration when audio is provided, and whether FFmpeg can decode the final file. It records tool versions, hashes, timing, output size, and temporary storage peaks.

Run records can contain absolute paths to the project and installed executables. Review and sanitize a record before sharing it. Never copy local project media or raw run records into a public report without inspecting their contents.