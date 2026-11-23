# Task Order: Local Script and Narration Workbench

**Task ID:** SAW-001 | **Status:** Complete | **Last updated:** 2026-11-23

## Objective

Build a local-server web app that provides a user interface for script revision and narration work. The creator can attach a wording note to a segment, create a durable AI request/result JSON handoff for any terminal AI assistant, review the response, and choose whether to apply a suggestion to the narration manifest. A bounded local Codex CLI action is optional, not the primary workflow.

The manifest remains the lasting source of truth for approved spoken text, segment IDs and order, status, voice style, and TTS settings. The app is an interface around the manifest and existing narration tools, not a second script or audio system.

This first phase starts directly with script and audio work. A separate project-idea outline, storyboard, visual-element planning, music, sound effects, and video-editing interface are outside this task.

## Agreed data model

1. **Project manifest:** `narration_manifest.json` holds approved script and narration settings. The existing generator continues to own take generation, take selection, assembly, pruning, hashes, and performance records.
2. **Tracked AI guide:** `ai_guide.json` lives with the public tool and is versioned in Git. It explains how UI concepts map to manifest fields, which fields the assistant may suggest changing, and rules such as preserving stable IDs and treating array order as playback order. It contains no project-specific narration, local paths, or voice recordings.
3. **Temporary work state:** `audio/.workbench/workbench_state.json` stores editorial notes, imported suggestions, review status, request-import markers, and the text hash each suggestion was based on. It survives app restarts until resolved or cleared, but it is not canonical script data and does not affect narration hashes.
4. **AI handoff files:** `audio/narration_requests/<stable-segment-id>/requests/SCR-001/` contains immutable `request.json` plus separate `result.json`. The request is created by VPS and is provider-neutral; a user-run terminal AI reads it and writes only the result file. Repeated requests receive new IDs and preserve history.
5. **Accepted changes:** Only after the creator accepts a suggestion does the app apply the approved text or setting to the manifest. The existing generator then detects changed text or settings and regenerates only the affected take; order changes trigger assembly as defined by the generator.

Use a clearly named local work area such as `audio/.workbench/workbench_state.json`. Keep only this temporary review state out of the public repository and production audio outputs; the project-owned request/result files remain in `audio/narration_requests/` as durable handoff history. Provide a way to clear resolved or stale review state without deleting those request files.

## Proposed workflow

1. Start the local server for one explicitly selected narration project and open its loopback address in a browser.
2. Review the manifest's segments in playback order. Select a segment and add a private editorial note, such as a request to clarify a line or make the transition less abrupt.
3. Press **Create AI request JSON**. VPS writes one stable-ID-scoped `request.json` and a `result.json` scaffold. The user manually gives that file to Codex, Claude, or another terminal AI, which fills the paired result. VPS does not host or launch that AI.
4. Press **Refresh AI results**. VPS validates completed result identity and base-text hash, then imports it into the suggestion review queue. Optionally, the user can choose **Run with Codex CLI** on a request; this processes the same saved JSON and writes the same result format.
5. Do not silently overwrite the manifest. Let the creator compare the original and suggestion, optionally audition the proposed wording, then accept or dismiss it.
6. On acceptance, update the manifest while preserving IDs, order, status, voice style, TTS settings, and unrelated fields. Preview or generate the changed segment with the existing narration tools.
7. Review individual takes and the assembled narration, including transitions between segments.

## AI request and provider boundaries

- The primary AI workflow is file-based and provider-neutral. `request.json` includes all fields from root `video_project.json`, the selected segment, note, immediate neighboring text, and generic guide; it excludes `narration_manifest.json`, audio files, takes, and unrelated narration segments. Since user-added fields in the root project manifest are included, review that file before sending the request to an external provider.
- Keep `request.json` intact. The external assistant writes its proposal and status to the paired `result.json`; that file cannot change the approved narration by itself.
- VPS validates request identity, result identity, and source-text hash before importing the result. A proposal based on words that have since changed is marked stale. The creator explicitly accepts any proposal before the manifest changes.
- The optional local Codex CLI action runs one `codex exec` in an ephemeral read-only sandbox and writes into the same result contract. This is a CLI process, not a Codex server, and it is not required for the file workflow.
- Show the exact context before handoff and keep a distinct request ID for every attempt. Never automatically launch an external assistant or apply a result.

## Requirements

- Serve the interface locally and bind only to `127.0.0.1` by default. Do not expose it on the network.
- Limit file access to the explicitly selected project. Validate paths and prevent requests from reading or writing outside the allowed manifest and narration work area.
- Read and write the existing manifest format while preserving fields the UI does not edit. Validate JSON and show useful errors rather than silently discarding malformed or unknown data.
- Keep spoken text, temporary notes, and AI suggestions visibly distinct. Notes and suggestions must never be sent to TTS as spoken words.
- Preserve stable segment IDs and manifest array order. The array remains the playback-order source of truth; this first UI displays that order but does not reorder it. Support `active`, `inactive`, and `deleted` statuses plus per-segment `voice_style` and `tts` settings.
- Detect stale suggestions by comparing their stored base text hash with the current manifest text. Require a fresh suggestion or explicit review if the segment changed after the AI request.
- Use the existing Audio Narration Generator for persistent F5-TTS takes, selected-take records, assembly, pruning protections, and performance data. Do not create a competing generation or take-numbering system.
- Offer transient preview where the installed platform supports it. The current SAPI preview is Windows-only; on macOS or Linux, report it as unavailable and do not silently substitute another engine.
- Make generation state visible: unchanged takes can be reused, changed text or generation settings can need a new take, and playback-order changes can require a new assembly.
- Support listening to individual takes and the assembled narration so segment joins can be reviewed in context.
- Keep temporary work state separate from the manifest and exclude it from generation and assembly hashes. Resolved state can be cleared without changing approved narration.

## Implementation record

- [x] Inspected the manifest schema, generator CLI, preview tool, and local-library server pattern.
- [x] Added the tracked `ai_guide.json` and strict structured suggestion schema.
- [x] Implemented `workbench.py` and a responsive browser interface using only Python's standard library.
- [x] Added separate project work state at `audio/.workbench/workbench_state.json`; its notes and suggestions do not enter manifest hashes.
- [x] Added text/title/status/voice-style/TTS editing, note persistence, Codex suggestion review, original-text comparison, audition, accept/dismiss, and resolved-suggestion cleanup.
- [x] Connected transient SAPI preview, incremental persistent generation, selected-take playback, and active-segment assembly to the existing tools.
- [x] Added loopback-only host/origin checks, constrained audio routes, manifest-byte conflict detection, atomic JSON writes, stale-suggestion detection, and safe read-only Codex requests.
- [x] Added provider-neutral narration `request.json` / `result.json` handoff, explicit refresh/import, distinct `SCR-*` request history, and optional Codex CLI processing of the saved request.
- [x] Updated this guide, tool index, installation requirements, root overview, and Git ignore rules.
- [x] Tested Codex CLI 0.171.0 live through the local HTTP suggestion and acceptance flow using disposable generic sample text; recorded the outcome in the repository validation record.

The interface supports reordering visible segments and writes that order to `narration_manifest.json`. It does not provide a project picker, persistent F5 model installation, pruning, built-in provider integrations beyond optional Codex CLI, or a separate idea-outline stage. External terminal AI tools can use the JSON handoff without a built-in provider integration.

## Follow-up review (2026-11-22)

- **Tested and corrected:** The generation result remains visible after the page refreshes. Unsaved note text is marked and guarded from accidental loss when switching beats or running an action. Invalid numeric TTS inputs cannot silently clear an override, and unchanged numeric settings preserve their stored type so a title edit does not trigger a needless new take.
- **Tested and corrected:** Manifest edits and suggestion acceptance return a conflict while workbench generation or assembly is running. The stereo review WAV wins when mono and stereo outputs have the same modification time. Save failures report a useful error and leave the previous manifest intact. The temporary work queue checks its size before replacing its saved file.
- **Tested repository boundary:** The public and internal channel repositories now ignore project `audio/.workbench/` state. A project in any other Git repository needs the same ignore rule.
- **Implemented, pending visual review:** The F5-TTS tab shows the selected take and keeps other discovered and manifest-recorded takes behind **Show other takes**. Each take has a rating menu that saves Favorite, Acceptable, or Rejected to the manifest while preserving its note and current selection. Each available take shows its note, playable audio, and parent folder path for Explorer. Pruned records remain visible when expanded. Voice settings live in the same tab. The header owns SAPI preview and assembled F5-TTS playback.
- **Proposed follow-up:** Allow selecting an older take in the interface and offer a deliberate “generate another take” action for unchanged words. The existing generator and manifest already support these operations.

## Completion criteria

- A creator can run the app locally for one selected project and review/edit the manifest-backed narration.
- A segment note survives app restart in temporary work state. A user-run AI can read the project-owned request and write a result which VPS imports and shows for review.
- A suggestion changes the manifest only after explicit acceptance. Rejected, pending, or stale suggestions do not alter spoken text or narration hashes.
- Accepted text edits update the correct stable segment and existing generation behavior regenerates only affected narration; array-order changes are assembled by the existing CLI.
- Segment order, IDs, status, voice style, TTS settings, selected takes, and tool-owned hashes remain consistent with the existing CLI.
- Take ratings can be changed from the F5-TTS tab and are saved to the correct manifest review record without changing selected audio or assembly state.
- The tracked AI guide documents field mapping and guardrails without containing project-specific or private material.
- The app is loopback-only and confined to the selected project. AI requests are file-based, show the context to be sent, and remain usable even when Codex CLI is unavailable.
- The provider-neutral request/result workflow and optional Codex CLI adapter are covered by tests. Other providers can use the JSON contract without a VPS integration.
- Tests and validation records cover success and key error cases; documentation explains setup, launch, provider requirements, temporary-state cleanup, outputs, and limitations.

## Boundaries

- No separate video idea or script-outline stage in this phase.
- Storyboarding, visual libraries, element and animation proposals, music, SFX, timeline editing, export, publishing, and website integration are deferred.
- The app is a local project interface, not a hosted service, project database, or replacement for the manifest and existing narration CLI.
- Do not bundle F5-TTS, model checkpoints, or voice recordings. Users provide and license those independently.

## Related sources

- [Audio Narration Generator guide](../../README.md)
- [Transient Narration Preview task](TASK-ORDER_TRANSIENT_NARRATION_PREVIEW.md)
- [Public tool index](../../../README.md)
- [Visual Library Browser local-server example](../../../library-browser/README.md)
