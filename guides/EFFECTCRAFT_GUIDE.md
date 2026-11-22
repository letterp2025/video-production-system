# EffectCraft Guide

EffectCraft is an open-source motion-graphics and compositing application. This guide treats it as a prompt-led creative workflow: an AI assistant helps plan and build the project, while the desktop GUI is mainly used to inspect, review, and make focused visual adjustments. It also covers installation and the optional FFmpeg section-rendering workflow documented in this repository.

EffectCraft is actively developed. Download links, supported packages, and interface details can change, so use the official download and release pages as the current source for installers.

## Install EffectCraft

You can give this setup request to Codex or Claude:

```text
Build EffectCraft from its official GitHub source on this computer.
Check for Git, Rust 1.95 or newer, and the build tools required for this operating system. Install any missing prerequisites, then clone https://github.com/storytold/effectcraft.git.
Build the desktop app and CLI with:
cargo build --release -p effectcraft -p effectcraft-cli
Verify that the build succeeded and tell me the source commit and the exact paths to the app and CLI.
Use the source build, not a prebuilt installer.
```

### Recommended: build from Git source

This guide recommends the Git build because one checkout and one build produce both the EffectCraft desktop app and its CLI from the same source revision. The CLI is used by MCP and by this repository's FFmpeg section renderer, so you do not need to fetch the app and CLI separately.

Follow these steps:

1. **Install the prerequisites:**
   - Git.
   - Rust 1.95 or newer, installed through [rustup](https://rustup.rs/). Rust includes Cargo, the build tool used below.
   - On macOS, Xcode Command Line Tools. Install them with `xcode-select --install`.
   - On Windows, the Visual Studio C++ build tools (MSVC).
   - On Linux, any required system packages listed in EffectCraft's [contributor setup](https://github.com/storytold/effectcraft/blob/main/CONTRIBUTING.md#setup).
   - Node.js is not needed to build the desktop app and CLI.
2. **Clone the source code:**
   ```sh
   git clone https://github.com/storytold/effectcraft.git
   cd effectcraft
   ```
3. **Build the desktop app and CLI:**
   ```sh
   cargo build --release -p effectcraft -p effectcraft-cli
   ```
   The first build downloads Rust dependencies and compiles them, so it may take a while.
4. **Update it later:** from the `effectcraft` folder, run `git pull`, then run the build command again.

- **Windows test status:** we have built EffectCraft from Git on Windows and tested the source-built CLI with the section renderer. We have not tested the official prebuilt installer; specifically, its bundled CLI has not been tested with the renderer.
- **macOS package note:** the source build targets the Mac architecture you build on. It does not create the signed, notarized universal `.dmg`.
- For the upstream overview, see the EffectCraft [build instructions](https://github.com/storytold/effectcraft#build-it-yourself).

### Alternative: install an official package

Use the [official EffectCraft download page](https://www.getartcraft.com/apps/effectcraft) or the [official GitHub releases](https://github.com/storytold/effectcraft/releases) to install a packaged build. Release assets include a `SHA256SUMS.txt` file; use it to verify a downloaded asset when your operating system provides a checksum tool.

Choose the package that matches your computer:

| Platform | Typical choice | Other option |
|---|---|---|
| Windows 10/11, Intel or AMD 64-bit | Windows x64 installer (`.msi`) | Portable x64 `.zip`; extract it and run the app without a conventional install |
| Windows on ARM | ARM64 installer (`.msi`) | Portable ARM64 `.zip` |
| macOS | Universal disk image (`.dmg`) for Apple silicon and Intel | Separate command-line package is available for automation |
| Linux | Select the package for your distribution, such as Flatpak, AppImage, `.deb`, or `.rpm` | Tarball packages are also available |

The official site lists current platform packages and formats. Package availability can vary by release and architecture. On Windows, the default MSI installation is per-user and does not require administrator access. On macOS, open the universal disk image and follow its included steps. On Linux, follow the package-specific installation instructions.

At the time this guide was checked (2026-11-22), the official download page listed version 0.24.1. Use the linked official pages for the current version.

## Prompt-first workflow with an AI assistant

EffectCraft does not interpret natural-language prompts by itself. The AI assistant supplies the planning and reasoning; EffectCraft supplies the project, editing, and rendering tools. Upstream documents an MCP server for AI clients. Its command interface and the desktop interface operate on the same project engine, and the MCP server can run headless or connect to a running desktop app. Check the current [EffectCraft agent documentation](https://github.com/storytold/effectcraft/blob/main/docs/agents.md) and your AI client's MCP setup instructions because both change over time.

**Workflow status:** This is a proposed way to use EffectCraft in this repository, based on the current upstream MCP documentation. We have not yet validated an end-to-end MCP session with an AI client here. Our tested Windows workflow remains the source-built CLI and the FFmpeg section renderer described below.

### Recommended project loop

1. **Describe the video in ordinary language.** Give the assistant the goal, audience, approximate duration, canvas and frame rate, scene beats, text, visual direction, available assets, and any must-keep or must-avoid details. Rough notes are enough to start.
2. **Ask it to inspect before it edits.** Have it inspect the open project or the saved `.ecproj`, summarize its compositions and layers, and outline a small implementation plan. For a new project, ask it to turn the brief into a scene plan before building.
3. **Build in EffectCraft through available tools.** With MCP connected, the assistant can query commands and their schemas, modify project properties, add keyframes, and render frame previews. Ask it to use the available command/API descriptions instead of guessing internal fields. Without MCP, give it the saved project file and let it prepare a project edit, script, or CLI steps for you to run.
4. **Review images, then correct the specific issue.** Ask for stills or a contact sheet at important times. Review composition, timing, text fit, overlap, and motion. Give concrete feedback such as “move the badge left by about 40 pixels” or “delay the title until 1.2 seconds.” Repeat on the parts that need work.
5. **Use the GUI for visual judgment and hands-on tweaks.** Scrub the timeline, inspect the animation at full size, and make direct adjustments when that is quicker. Save the project before handing the next iteration back to the assistant.
6. **Render and verify the deliverable.** Ask the assistant to save the project to the intended path, render a review version, and report what it actually checked. Use the [section renderer](../tools/effectcraft_ffmpeg_sections/README.md) for its supported video workflow, then watch the resulting video yourself.

### Ways to connect the assistant

| Connection | Use it when | What to know |
|---|---|---|
| **Headless MCP** | You want the assistant to create or change a saved project and render previews without opening the desktop app. | The assistant talks to `effectcraft-cli mcp`; no app window is needed. Save the project explicitly and inspect the rendered results. |
| **MCP bridged to the GUI** | You want to watch the assistant make changes in the open EffectCraft project and review them in place. | The desktop app must be started with its control channel, then MCP connects in bridge mode. The upstream guide documents the command and the `ui`/screenshot tools. |
| **Project file and CLI** | Your AI client cannot connect to EffectCraft MCP, or you prefer to review each file operation. | Give the assistant a saved `.ecproj` plus the project brief. The assistant can prepare scripts or structured edits; use the CLI to render previews. It cannot see unsaved GUI changes unless you connect it to the live app. |

Claude Code and Codex can both connect to MCP servers, but their configuration formats differ. Use the current [EffectCraft agent setup](https://github.com/storytold/effectcraft/blob/main/docs/agents.md) with the current [Codex MCP instructions](https://developers.openai.com/codex/extend/mcp) or [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp). Do not paste a Claude-specific configuration into Codex unchanged.

### Method route: code-built shapes and visual iteration

MCP is one way to let an assistant operate EffectCraft. It is not required for code-led construction. Another route is for the assistant to write or edit EffectCraft-native project data, render previews with the CLI or the [section renderer](../tools/effectcraft_ffmpeg_sections/README.md), and refine the result from visual review. This is the route we used for our early reusable elements and animation studies; those runs did not use MCP.

Use this route when you can describe an element as editable shapes, paths, text, or a grid of controllable cells:

1. **Study the reference.** Use a screenshot or contact sheet to identify the element's parts, proportions, colors, placement, and the moments when it changes.
2. **Choose how to construct it.** Build simpler parts from EffectCraft shapes and coordinates. For a cell grid, define the cells and animate their visibility, position, color, or other supported properties. If tracing a raster image with an external tool such as VTracer, treat its SVG as an intermediate trace that may need path cleanup and translation into EffectCraft-native data.
3. **Render a first pass.** Ask the assistant to save the result as an EffectCraft project and render stills or a short preview at useful timestamps. The assistant can write the project data, but you still need to judge the rendered result.
4. **Compare and refine.** Check the preview against the reference. Adjust geometry, color, spacing, timing, and easing, then render again. Complex shapes often take several rounds; tracing does not guarantee a clean or exact result.
5. **Save the reusable result.** Keep the editable project or source data with the library entry, and record which parts are native shapes, traced paths, or approximations.

**Experience status:** Building and animating native grid cells through code, then reviewing and adjusting rendered previews, has been tested in our local studies. The VTracer-to-EffectCraft path has been explored, but its output needed cleanup and was not a dependable one-step conversion. These are practical examples, not a guarantee that every EffectCraft project feature can be authored through project data. Because `.ecproj` is versioned, use documented APIs when available and reopen externally edited projects in the matching EffectCraft version to verify them.

### Connect an AI client on Windows

For the default per-user MSI install, register the bundled CLI as a local MCP server. In PowerShell, run the command for the client you use:

```powershell
$effectCraftCli = "$env:LOCALAPPDATA\Programs\ArtCraft\EffectCraft\effectcraft-cli.exe"

# Codex
codex mcp add effectcraft -- $effectCraftCli mcp

# Claude Code
claude mcp add --transport stdio effectcraft -- $effectCraftCli mcp
```

If you installed EffectCraft elsewhere or built it from source, set `$effectCraftCli` to that `effectcraft-cli.exe` path. Restart the AI client if needed, then verify the connection with `codex mcp list` or `claude mcp list`. These commands start the headless MCP mode, which starts with an empty project unless you open a saved `.ecproj` through the assistant or pass a project path in the MCP arguments. For the live GUI bridge, start the desktop app with `--control 9877` and change the MCP server arguments to `mcp --bridge 9877`; see the upstream agent guide for the current details.

Start by asking the connected assistant to inspect the current project and report its compositions and layers without changing anything. Then try a small edit on a copy of the project. MCP access lets the assistant change the project, so keep experimental work in a separate project file.

### A useful first prompt

```text
I want to make a [duration] video about [topic] for [audience].
The output is [width x height] at [frame rate].
The main idea is [one sentence]. The scenes should cover [rough beats].
Use [available assets or visual direction]. Keep [constraints].

First inspect the current project or turn this brief into a scene plan.
Tell me what you found and what you propose before making project changes.
Then build the first pass in EffectCraft, save it as [project path],
and render previews at [timestamps] so we can review the result.
Use editable text and shapes where practical. Report any missing assets,
unsupported operations, or parts you could not verify.
```

The prompt is the creative direction, not a guarantee that every detail will be implemented correctly. Review the actual project and rendered frames. Work on a copy when experimenting with an existing project, and use one editing route per pass: either the live bridged app or the headless/file workflow. Avoid changing the same project simultaneously in the GUI and a separate headless session.

## GUI and CLI roles

The GUI is the visual workbench for watching, judging, and manually adjusting a composition. In a prompt-led workflow, the assistant handles much of the project inspection, structured setup, and repetitive edits; the GUI helps you make the creative call and tune what still feels wrong. You do not need to author every layer and keyframe by hand.

EffectCraft projects use the `.ecproj` format, which is readable, versioned JSON. Treat the saved project as the shared handoff between you and the assistant. Prefer EffectCraft's documented MCP, scripting, or CLI operations for changes; direct JSON edits are a fallback because the native schema can change between versions. After changing a project file outside the GUI, reopen or reload it in the matching EffectCraft version and review it.

The CLI can load the same project format for scripting and headless rendering. It is also required to run EffectCraft's MCP server and the FFmpeg section renderer in this repository.

The CLI is distributed differently by platform:

- **Windows:** the MSI includes `effectcraft-cli.exe` beside the desktop app. In the default per-user installation, its path is `%LOCALAPPDATA%\Programs\ArtCraft\EffectCraft\effectcraft-cli.exe`. It is not automatically added to `PATH`. The section renderer accepts a full executable path through its `-EffectCraft` parameter.
- **macOS:** the desktop disk image and the command-line tool are separate downloads. Get the CLI archive from the official release assets if you need headless rendering.
- **Linux:** CLI availability and its path depend on the package format. Check the upstream [CLI and agent documentation](https://github.com/storytold/effectcraft/blob/main/docs/agents.md) for the package you chose.

To verify a Windows CLI installation, run its help command in PowerShell, adjusting the path if you chose a different install folder:

```powershell
& "$env:LOCALAPPDATA\Programs\ArtCraft\EffectCraft\effectcraft-cli.exe" --help
```

You do not need the CLI for manual editing in the desktop app. You do need a usable CLI executable for the MCP server and the section renderer.

### Windows source build we tested

Our Windows section-rendering test used the source-built EffectCraft CLI version 0.24.1 from commit `cd9ee1e46a87d2a0951f038e62306058ceaaf621`. The corresponding build command is:

```powershell
git clone https://github.com/storytold/effectcraft.git
Set-Location effectcraft
git checkout cd9ee1e46a87d2a0951f038e62306058ceaaf621
cargo build --release -p effectcraft-cli
```

The resulting CLI is `target\release\effectcraft-cli.exe`. The source-built CLI worked with the section renderer in our test. For a repeatable build, use a specific commit as above instead of whichever revision is newest.

The official MSI is another install route. Upstream documents its CLI path as `%LOCALAPPDATA%\Programs\ArtCraft\EffectCraft\effectcraft-cli.exe`; however, we have not tested the prebuilt installer or its bundled CLI with the section renderer.

## Choose an export workflow

For short previews and ordinary projects, begin with EffectCraft's own export. If a long or high-resolution native export is taking too long, the [EffectCraft Section Renderer](../tools/effectcraft_ffmpeg_sections/README.md) offers an external workflow:

1. EffectCraft CLI renders the requested frame ranges as PNG sequences.
2. FFmpeg encodes the sections and joins them into the output video.
3. The tool validates the result and saves run and performance records.

The renderer needs the EffectCraft CLI, FFmpeg, FFprobe, PowerShell 7 (recommended), a project file, and a section manifest. See the [tool guide](../tools/effectcraft_ffmpeg_sections/README.md) for setup, commands, resume behavior, and storage controls.

### What our benchmark showed

In one 30-second, 4K60 vector-graphics test, FFmpeg completed a one-section export in 4 minutes 51.8 seconds. Six-section runs took about 4 minutes 41 seconds and 5 minutes 16 seconds. Splitting the render did not meaningfully reduce elapsed time in that test. It reduced peak temporary storage from about 716 MB to about 143 MB and allowed completed sections to be reused after interruption.

The matched native GPU export was stopped after 10 minutes 46.6 seconds at 384 of 1,800 frames (21.3%). Its remaining-time display showed about 39 minutes, but the render did not finish. That estimate is not a measured native export time. The evidence supports saying that FFmpeg completed while the native export remained incomplete at the ten-minute mark; it does not support claiming a measured 40-to-5-minute speedup.

These results came from one workstation and one mostly vector-based composition. They are not a performance guarantee for other projects, hardware, EffectCraft versions, or encoders. The [benchmark record](../benchmarks/EFFECTCRAFT_RENDERING.md) includes settings and limits.

## Build from a visual reference

When a video is inspired by an existing design or animation, first record what is visible and how it changes over time. The [Reference Video Analysis guide](REFERENCE_VIDEO_ANALYSIS.md) describes a progression from broad contact sheets to denser frame sampling for specific motion. Use the public [visual libraries](../libraries/README.md) for reviewed reusable examples; keep private or rights-unclear source material out of public entries.

The section renderer and libraries are optional workflows. AI assistance can speed up project construction, but the creator still directs the video and reviews its visual and audio result.

## Sources

- [Official EffectCraft download page](https://www.getartcraft.com/apps/effectcraft)
- [Official GitHub releases](https://github.com/storytold/effectcraft/releases)
- [Official EffectCraft CLI and agent documentation](https://github.com/storytold/effectcraft/blob/main/docs/agents.md)
- [Codex MCP connection instructions](https://developers.openai.com/codex/extend/mcp)
- [Claude Code MCP connection instructions](https://code.claude.com/docs/en/mcp)
- [Public repository installation guide](../INSTALLATION.md)
- [EffectCraft section-rendering benchmark](../benchmarks/EFFECTCRAFT_RENDERING.md)
