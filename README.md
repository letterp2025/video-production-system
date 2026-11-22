# Video Production System

A public collection of small tools and practical notes for planning and producing motion-led videos. It includes local media utilities, EffectCraft-to-FFmpeg rendering support, narration helpers, and working studies of optional tools.

This repository is maintained independently of EffectCraft, FFmpeg, F5-TTS, and the other projects linked here. Those projects keep their own names, source code, and terms.

## Start here

- [Installation guide](INSTALLATION.md)
- [Production and planning guides](guides/README.md)
- [EffectCraft installation and workflow guide](guides/EFFECTCRAFT_GUIDE.md)
- [YouTube growth and script-writing guides](guides/README.md#guides)
- [Tool index](tools/README.md)
- [EffectCraft rendering benchmark](benchmarks/EFFECTCRAFT_RENDERING.md)
- [Validation record](VALIDATION.md)
- [Visual libraries](libraries/README.md)

## Included tools

- Asset Finder: search Openverse and Wikimedia Commons, inspect a selected item, and save it with a source and license metadata receipt.
- Audio Narration Generator: edit narration in a local workbench, review Codex suggestions, generate reviewable F5-TTS takes from an ordered JSON manifest, and assemble selected takes.
- Contact Sheet: sample a video at adaptive or selected intervals and create timestamped overview sheets.
- EffectCraft Section Renderer: render EffectCraft compositions in PNG sections, encode and validate with FFmpeg, and preserve run records.
- Word Focus Subtitles: generate a word-by-word ASS subtitle sequence from text.
- Raster-to-Vector: a study of external tracing and EffectCraft's SVG-to-shape path; no standalone tracing utility is included.
- Music and SFX: a deferred options study; no generator is included.

No private visual-reference entries, downloaded source media, voice recordings, project-specific narration, or rendered outputs are included in this repository. Library previews and native projects may exist locally for review but are ignored by Git.

The guides are general workflows that can be adapted to different channels, projects, and production tools. They do not include any private channel's brand direction, visual library, project files, or media.

The visual-library directory contains public element and animation examples plus a general reference-study guide. Private reference entries and source media remain in their internal workspace until each entry is reviewed for public release.

## License

Source code is released under the MIT License in [LICENSE](LICENSE). Written guides and documentation are released under [CC BY 4.0](LICENSE-DOCS). Third-party software, models, fonts, data, and media remain under their own terms. See each tool guide before using an external dependency or asset.

## Development status

This public repository is available at [GitHub](https://github.com/letterp2025/video-production-system). It was validated from a fresh clone on one workstation using its installed runtimes. A clean-machine installation has not been tested.
