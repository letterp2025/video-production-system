# Task Order: Visual Animation Plans Per Segment

**Task ID:** VAP-001 | **Status:** Planned | **Last updated:** 2026-11-23

## Objective

Give each narration segment an optional, clearly associated visual-animation plan. From the local narration workbench, the creator can choose a reusable recipe or start a custom plan, create a JSON file for the selected segment, and see that plan whenever the segment is selected.

The first implementation is a planning and organization workflow. It must not imply that a selected recipe is already rendered, nor change the existing narration, TTS, or video-rendering pipelines.

## Intended workflow

1. Open the local workbench for a project and select a narration segment.
2. Use a **Visual for this beat** dropdown to choose a recipe from the Visual Animations Library, or choose a blank/custom plan.
3. Choose **Create visual JSON**. The workbench creates a plan associated with the selected segment and shows its saved state.
4. Re-selecting that segment shows its recipe and plan status, with a way to open the JSON. Other segments retain their own files and selections.
5. If the segment's approved spoken text changes later, mark its plan as needing review rather than silently rewriting it.

## Workbench changes

- Remove the header's **Codex CLI found** status badge shown in the supplied screenshot. This is a presentation change only: keep the existing Codex suggestion action and error reporting intact.
- Use that header area for the selected segment's visual-recipe dropdown and a clearly named create action. Keep the control compact, keyboard accessible, and responsive; use the workbench's existing paper/ink palette, cyan action color, and typography. Make the selected beat explicit so a file cannot be mistaken as belonging to another beat.
- Populate recipe choices from the tracked Visual Animations Library entries. Include a custom/blank choice so planning remains possible before a library recipe exists.
- Show one of these states for the selected beat: no plan yet, saved plan, plan needs review, or plan unavailable/invalid. Do not overwrite an existing file implicitly.
- Provide a safe way to open the selected segment's JSON. The first version may edit the JSON outside the workbench; a structured in-app visual editor and preview can be planned separately.

## Data model and storage

- Keep visual plans separate from `narration_manifest.json`; creating or changing a visual plan must not alter narration text, manifest hashes, take selection, or audio generation.
- Store one project-local JSON plan per stable segment ID under `audio/visuals/`. Use a deterministic, path-safe filename derived from the segment ID; retain the original ID in the JSON. Keep generated project files inside the selected project's audio folder and never write them into the public repository's library folders.
- Write files atomically, validate the segment against the current manifest, reject path traversal and symlinks, and do not replace an existing plan without an explicit user action.
- Start with a versioned structure along these lines:

  ```json
  {
    "schema_version": 1,
    "segment": {
      "id": "opening-hook",
      "title": "Opening hook",
      "source_text_sha256": "<hash of the approved spoken text>"
    },
    "animation": {
      "recipe_id": "ANM-example-reveal",
      "recipe_title": "Example reveal"
    },
    "visual": {
      "description": "",
      "start_seconds": 0,
      "duration_seconds": null,
      "elements": []
    }
  }
  ```

- Treat `animation.recipe_id` as a reference to a reusable library entry, not copied implementation code. Permit `null` for a custom plan. The schema should be reviewed before it becomes a renderer contract.
- Compare `source_text_sha256` with the current segment text to detect a plan that may need editorial review. Do not delete or silently reset that plan when narration changes.

## Implementation phases

1. **Schema and file lifecycle:** finalize the initial JSON schema, safe filename mapping, conflict behavior, and how `audio/visuals/` is kept project-local.
2. **Workbench integration:** add the recipe dropdown, selected-segment status, create/open actions, and a local API constrained to the selected project.
3. **Validation and documentation:** cover file creation, malformed and oversized JSON, stale plans, duplicate creates, invalid IDs, manifest conflicts, and request-origin/path boundaries. Document where plans live and what they do not render.
4. **Rendering follow-up:** only in a later task, decide how a plan becomes a preview or video segment and which renderer consumes it (for example, EffectCraft, Manim, or a browser/GSAP path). Preserve renderer-neutral intent where practical; do not execute arbitrary code from a plan.

## Acceptance checks

- The marked Codex availability badge is gone, while Codex suggestions still work as before.
- The dropdown reflects the selected narration segment and offers available library recipes plus a custom option.
- Creating a plan produces valid versioned JSON for exactly that segment in the selected project's `audio/visuals/` folder; it does not edit the narration manifest or trigger audio generation.
- Switching segments shows the correct plan or empty state. Existing plans are not overwritten by another create action.
- Changes to approved narration text make the associated plan visibly stale/needs-review without deleting it.
- Local API routes remain loopback/origin constrained and cannot read or write outside the selected project folder.
- Tests and docs explain the distinction between a visual plan JSON and a rendered animation.

## Boundaries

- This task does not render animation frames, compose a video timeline, generate visual assets, or add a GSAP/Manim/EffectCraft renderer.
- Do not bundle media, fonts, model files, or tool implementations into a project plan JSON.
- Do not modify the public visual-library entries when creating a project-specific plan.
- Keep narration generation, segment order, TTS settings, takes, and audio outputs governed by their existing manifest and tools.

## Related documents

- [Visual Animations Library](../../libraries/visual_animations_library/README.md)
- [GSAP Guide](../../guides/GSAP_GUIDE.md)
- [Script and Narration Workbench task order](../../tools/audio_narration_generator/docs/TASKS/TASK-ORDER_SCRIPT_AUDIO_LOCAL_WEB_APP.md)
