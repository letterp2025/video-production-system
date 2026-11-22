# Reference Video Analysis

Use this workflow when studying a video to understand its visual structure, elements, and motion. It supports recreation and learning; it does not reveal the source editor's original layers or keyframes.

## Record provenance first

Record the video title, creator or source, URL or local path, relevant time range, dimensions, frame rate when known, and any known ownership or license information. Do not assume that being able to view or download a video grants permission to reuse its footage, artwork, music, or exact design. Keep source media and extracted frames in the project storage, not in a public code repository.

## Review from broad to detailed

1. **Watch the full video once.** Note the overall structure, major scene changes, recurring visual ideas, and passages worth examining.
2. **Create a broad contact sheet.** Sample widely enough to see the whole video's progression. For a longer video, intervals of several seconds can be a useful starting point; adapt the spacing to its pace and length.
3. **Create a closer motion pass.** Sample the full video more densely, often around one frame per second for navigation. For a fast or busy passage, use shorter intervals such as 0.25 seconds. Check neighboring frames at full size because sparse samples can miss brief transitions.
4. **Inspect selected moments at source frame rate.** Use every frame only for a short passage where exact motion matters. Record the time range and sampling rate so the observation can be repeated.
5. **Make an element sheet.** Select representative frames and label the important text treatments, cards, icons, shapes, backgrounds, interface pieces, or characters. Record each element's source timecode. The sheet is an analysis aid, not automatically a reusable asset library or an approved design.
6. **Map selected motion.** Track only the elements needed for the first reconstruction. Record approximate states over time, holds, reveals, overlaps, occlusions, and transitions. Use normalized positions where useful so the map is not tied to one resolution.
7. **Recreate and compare.** Build the selected elements in the chosen tool and compare them at matching timestamps. Note what matches, what differs, what remains unmapped, and what was inferred.

The [Contact Sheet tool](../tools/contact-sheet/README.md) can generate timestamped overview sheets and closer samples. Use its command options to adjust sampling density instead of assuming one interval fits every video.

## Keep observations and guesses separate

Use explicit labels in notes or a motion map:

- **Observed:** directly visible in a frame or established by source metadata.
- **Estimated:** measured or inferred from sampled frames, such as position, duration, or easing.
- **Recreation choice:** a design or implementation decision made for the new project.

An example motion record might include the source timecode, element label, approximate bounds or center, scale, rotation, opacity, layer order, reveal or transition, and confidence. Keep an evidence-frame path with each important observation. Treat the JSON structure as a working analysis format unless a project has deliberately adopted a stable schema.

## Rebuild elements with the right method

Use native shapes when the geometry is manageable and editability matters. A generated image can be a rough visual prompt, then the selected design can be rebuilt as editable shapes. A raster-to-vector tracer can help with a clear silhouette, but review its output: touching objects can merge, contours may be noisy, and the trace does not restore the original vector structure or animation.

Do not attempt to reconstruct every pixel in the first pass. Select a few elements that explain the visual language or motion, compare them against source frames, and expand only when the first slice is useful.

## Keep the analysis reproducible

Save concise notes, sampling settings, element labels, timecodes, and the selected tool's source project or code with the project. Keep contact sheets, extracted frames, downloaded video, and renders in local project storage unless the repository explicitly supports those assets and their rights are clear. For a complete production lifecycle, see the [video production workflow](VIDEO_PRODUCTION_WORKFLOW.md).
