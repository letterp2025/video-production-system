# Video Project Instructions

This folder contains one video project. Keep project-specific scripts, audio, visual implementations, source assets, and renders here, not in the public VPS tools repository.

## Project source of truth

- `video_project.json` is the creative brief for the user and future AI sessions: project idea, creative direction, rough conversational narration outline, inspirations, and manually maintained status notes. Preserve the user's voice and uncertainty; do not invent facts or inspirations.
- `audio/narration_manifest.json` is the source of truth for narration segment IDs, order, titles, and approved spoken words. Keep IDs stable when editing words or reordering segments. Do not make unrequested changes to approved wording.
- `sequence_manifest.json` is the source of truth for video story order and planned durations. It can contain narration-linked and visual-only units; do not add empty narration records to represent silent visual intervals.
- Visual take manifests and per-unit visual requests are under `visual_layer/`. Each request is an independent attempt. Keep its `request.json` as the brief and record progress and outputs in its paired `result.json`.
- Project-wide music mapping is under `audio/music/manifest.json` when created. Its `start_segment_id` and `end_segment_id` values refer to IDs in `sequence_manifest.json`, including visual-only units. Optional SFX planning belongs beside the visual request it supports.

## Working with VPS

Public VPS repository: <https://github.com/letterp2025/video-production-system>

Local VPS checkout on this machine: <fill in the local checkout path>

When the checkout is available, read its `guides/VIDEO_PRODUCTION_WORKFLOW.md` and `tools/audio_narration_generator/README.md` before changing VPS data formats or processing a request. For a specific handoff, follow the instructions and schema referenced by that request.

- Inspect existing files before writing. Preserve user data; do not overwrite an existing manifest or request.
- Keep project-relative paths in request results. Never put machine-specific absolute paths in portable project manifests or handoff result paths.
- For narration requests, write the proposal and status only to the paired `result.json`. Do not edit the approved narration manifest as a side effect; the user reviews and accepts proposals through VPS.
- For visual requests, preserve `request.json`, work within that request's folder, and update its paired `result.json` with current status and valid project-relative paths. Do not mark work completed until the referenced outputs exist.
- Do not download assets, run renderers, mix audio, or create a final render unless the user's current instruction or request clearly includes that work. VPS is for planning and asset preparation, not a non-linear video editor.
- Keep private voice references, credentials, and other sensitive material private. Check licenses and source information for externally sourced assets.

The user directs creative choices. Discuss material changes to story, tone, facts, scope, or approved narration before applying them.
