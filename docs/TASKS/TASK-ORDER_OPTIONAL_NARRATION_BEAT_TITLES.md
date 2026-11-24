# Task Order: Optional Narration Beat Titles

**Task ID:** ONT-001 | **Status:** Planned | **Last updated:** 2026-11-24

## Objective

Make the **Segment title** optional when adding a narration beat in the VPS workbench. Users should be able to add a beat by entering spoken words and choosing its status without having to invent a title first. When a title is supplied, retain it as the beat's display title.

## User workflow

1. Select a narration beat and choose **Add beat**.
2. In the **Add a beat** dialog, optionally enter a segment title, enter required spoken words, and choose Active or Inactive.
3. Choose **Add beat after**. VPS creates the narration segment and links it into the project sequence as it does today.
4. If no title was supplied, VPS uses the segment's stable ID as its display fallback. The user can later provide a title through the existing narration editor.

## Data ownership and storage

| Data | Source of truth |
|---|---|
| Stable narration ID, optional title, status, and approved spoken words | Project `audio/narration_manifest.json` |
| Story order and planned duration | Project-root `sequence_manifest.json` |

When the title is blank or whitespace-only, omit the `title` property on the new narration manifest entry rather than storing an empty string. Generate a unique stable ID independently of a missing title, using the existing collision-safe ID namespace shared with sequence units. If a title is provided, keep the current title-based ID behavior. The sequence unit continues to link by stable ID and must not duplicate narration text or title. Existing project records are not migrated.

## Requirements

- Remove the title requirement from the **Add a beat** dialog and identify the field as optional.
- Accept a missing, empty, or whitespace-only title in the creation request. Trim a supplied title and retain the existing maximum length validation.
- Keep spoken words required and subject to their existing validation and length limit.
- Generate a unique, stable ID for untitled beats without relying on their title. Check collisions against both narration IDs and sequence-unit IDs.
- Preserve current title-derived IDs and stored titles when the user supplies a title.
- Display an untitled beat using its stable ID wherever a title fallback is needed. Do not show an empty label.
- Keep later title editing available. A blank title must not weaken validation for narration text, status, IDs, or other manifest data.
- Keep the existing beat insertion workflow: link the new narration segment into the sequence, estimate its planned duration from spoken words, and select the new beat.
- Update relevant workbench documentation and regression coverage for both titled and untitled beat creation.

## Boundaries

- This task concerns titles in the **Add a beat** flow. It does not make titles optional for visual-only sequence units, visual takes, music items, or other titled records.
- Do not change narration wording, playback order, voice settings, take selection, or existing project data as a side effect.
- Do not rename or regenerate IDs for existing beats. IDs remain stable if a title is later added or changed.
- Do not create empty or placeholder narration segments; spoken words remain mandatory.
- Do not add automatic title generation from narration text.

## Implementation phases

1. **Creation dialog:** mark the title optional, retain focus and validation behavior for required spoken words, and make the field label clear.
2. **API and manifest handling:** accept omitted/blank titles, generate collision-safe IDs when untitled, and omit the title property for those new records.
3. **Regression coverage and documentation:** cover blank, whitespace-only, and supplied titles, ID collisions, sequence linking, and display fallback. Update the narration workbench guide.

## Acceptance checks

- A user can add a beat with spoken words and status while leaving **Segment title** blank.
- Empty and whitespace-only titles are treated the same; the resulting narration manifest record has no empty `title` value.
- An untitled beat receives a unique stable ID even when the default untitled-beat ID already exists in either manifest.
- The new sequence unit links to that same ID, preserves normal order and duration behavior, and the new beat is selected.
- The untitled beat has a readable stable-ID fallback in the workbench and related narration displays.
- A supplied title is trimmed, stored, and continues to produce the existing title-derived ID behavior.
- Existing narration records and IDs are unchanged; adding an untitled beat does not alter approved words or unrelated sequence units.
- Missing or blank spoken words are still rejected, and visual-only titles remain required.

## Related documents

- [Project Sequence Manifest](TASK-ORDER_PROJECT_SEQUENCE_MANIFEST.md)
- [Segment Layers and Workbench Layout](TASK-ORDER_SEGMENT_LAYERS_AND_WORKBENCH_LAYOUT.md)
- [Narration workbench guide](../../tools/audio_narration_generator/README.md)
