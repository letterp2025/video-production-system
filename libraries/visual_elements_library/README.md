# Visual elements library

This library catalogs reusable visual building blocks for motion graphics and video. An entry can be one primitive or a composite component assembled from several parts. Inspiration can come from interfaces, websites, video, print, animation, diagrams, games, or original experiments.

## Terms and variants

- **Primitive:** one drawable, such as a line, rectangle, circle, path, text treatment, or icon.
- **Composite element:** a repeatable unit built from primitives, such as a service card, title lockup, chart label, or lower third.
- **Visual treatment:** how an element is drawn or painted. One structure can have many variants, such as retro, minimal, high contrast, or other directions we may discover. These examples are not a limit.
- **Scene:** the full composition, layout, content, and timing. Reference studies belong in the [Visual Reference Library](../visual_reference_library/README.md).

“Visual element” is the cross-tool catalog term. EffectCraft calls editable objects layers; Manim calls drawable objects Mobjects. Record the actual implementation and tool version in each entry.

Keep an element's structure separate from its visual treatment where practical. The full folder basename is the stable ID, following `ELM-<descriptive-slug>`, and each treatment keeps its own variant ID such as `STY-01`. The full style identity is the pair, for example `ELM-pixel-cell-grid / STY-01`. Put the style name before its ID in a folder such as `styles/retro-STY-01/`.

## Add an element

1. Choose a concise descriptive slug, check the public and private element libraries for a collision, and create the folder using `ELM-<slug>` as both its name and ID.
2. Copy [`ELEMENT_TEMPLATE.md`](ELEMENT_TEMPLATE.md) to the entry as `NOTES.md`.
3. Record its purpose, source, parts, configurable values, dimensions, and tool-specific construction.
4. Keep builder code and small text configuration in `code/`. Keep native editing projects, rendered previews, screenshots, fonts, and other media local and ignored.
5. Add the entry and each style variant to the index below. Record whether a preview is a local-only artifact.

Typical entry:

```text
ELM-short-name/
  NOTES.md
  code/       # reusable builder or integration example
  styles/     # optional variant folders
  project/    # optional local native project; ignored
  preview/    # optional local visual checks; ignored
```

## Index

| ID | Element | Kind | Source | Status | Style |
|---|---|---|---|---|---|
| [ELM-chromatic-split-headline](ELM-chromatic-split-headline/NOTES.md) | Chromatic split headline | Typographic | 11kfire.com | Preview ready; review pending | [retro-11kfire-STY-01](ELM-chromatic-split-headline/styles/retro-11kfire-STY-01/STYLE.md) |
| [ELM-layered-action-button](ELM-layered-action-button/NOTES.md) | Layered action button | Composite / UI | 11kfire.com | Preview ready; review pending | [retro-11kfire-STY-01](ELM-layered-action-button/styles/retro-11kfire-STY-01/STYLE.md) |
| [ELM-pixel-cell-grid](ELM-pixel-cell-grid/NOTES.md) | Pixel cell grid | Graphic primitive / cell system | 11kfire.com | Empty-state preview ready; review pending | [retro-11kfire-STY-01](ELM-pixel-cell-grid/styles/retro-11kfire-STY-01/STYLE.md) |
| [ELM-dotted-print-field](ELM-dotted-print-field/NOTES.md) | Dotted print field | Primitive / texture | 11kfire.com | Preview ready; review pending | [retro-11kfire-STY-01](ELM-dotted-print-field/styles/retro-11kfire-STY-01/STYLE.md) |
| [ELM-angled-caption-tag](ELM-angled-caption-tag/NOTES.md) | Angled caption tag | Composite / typographic | 11kfire.com | Preview ready; review pending | [retro-11kfire-STY-01](ELM-angled-caption-tag/styles/retro-11kfire-STY-01/STYLE.md) |

The public catalog contains five entries. Five 11K FIRE-specific reconstructions were moved out of the public collection on 2026-11-22. The remaining first style pass was built with EffectCraft CLI 0.24.1. Source builders are tracked. `.ecproj` projects and PNG previews are local working files and are excluded from Git. Use the recipe-specific `STYLE.md` for build notes. The 11K FIRE site was the reference for this first collection; these entries are examples, not a required style for future library items.

## Rebuild a still preview

Set `EFFECTCRAFT_CLI` to the EffectCraft CLI executable. Run from the repository root in PowerShell; substitute the entry and composition details for another element.

```powershell
$styleRoot = Join-Path (Get-Location).Path 'libraries\visual_elements_library\ELM-chromatic-split-headline\styles\retro-11kfire-STY-01'
$project = Join-Path $styleRoot 'project\chromatic-split-headline.effectcraft.ecproj'
$preview = Join-Path $styleRoot 'preview\chromatic-split-headline_1080p.png'
New-Item -ItemType Directory -Force -Path (Split-Path $project), (Split-Path $preview) | Out-Null
& $env:EFFECTCRAFT_CLI script (Join-Path $styleRoot 'code\build.jsx') --empty --save-as $project
& $env:EFFECTCRAFT_CLI --project $project render-frame --comp '11K FIRE Chromatic Split Headline' --time 0 --scale 1 --out $preview
```

This makes a still, not a video. For video delivery, use the [EffectCraft Section Renderer](../../tools/effectcraft_ffmpeg_sections/README.md). Local render outputs and receipts remain ignored.
