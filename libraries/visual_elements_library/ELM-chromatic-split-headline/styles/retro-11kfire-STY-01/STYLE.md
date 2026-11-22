# retro-11kfire - STY-01

- **Source:** 11kfire.com hero headline, reviewed 2026-11-19.
- **Website reference copy:** `POINT / OF VIEW.` The design is based on the visible hero type treatment.
- **Construction:** Two editable text layers, aligned and offset to form the black and red lines, with a cyan registration shadow.
- **Local project:** `project/chromatic-split-headline.effectcraft.ecproj` (ignored).
- **Local still preview:** `preview/chromatic-split-headline_1080p.png` (ignored).
- **Tool:** EffectCraft CLI 0.24.1. Set `EFFECTCRAFT_CLI` to the CLI executable. If the selected typeface is not installed, set `EFFECTCRAFT_FONT_DIRS` to a local font folder; fonts are not distributed with this entry.
- **Preview:** A lossless still rendered from the saved project with `render-frame`; no video encoder is involved.

Run the build from the public repository root:

```powershell
$styleRoot = Join-Path (Get-Location).Path 'libraries\visual_elements_library\ELM-chromatic-split-headline\styles\retro-11kfire-STY-01'
$project = Join-Path $styleRoot 'project\chromatic-split-headline.effectcraft.ecproj'
$preview = Join-Path $styleRoot 'preview\chromatic-split-headline_1080p.png'
New-Item -ItemType Directory -Force -Path (Split-Path $project), (Split-Path $preview) | Out-Null
& $env:EFFECTCRAFT_CLI script (Join-Path $styleRoot 'code\build.jsx') --empty --save-as $project
& $env:EFFECTCRAFT_CLI --project $project render-frame --comp '11K FIRE Chromatic Split Headline' --time 0 --scale 1 --out $preview
```

This is an authored style example. The typeface remains the user's local font choice; use an available font when the original one is not installed.