# Video Production Workflow

This guide gives a repeatable path from an early idea to a reviewed video. It applies to explainers, tutorials, product demonstrations, visual essays, and other motion-led work. Use the dedicated tool guides for installation, project formats, and rendering commands.

## Start with the viewer

Before choosing software or designing motion, write down:

- Who the video is for.
- What question, need, or curiosity gives them a reason to watch.
- What they should understand, feel, or be able to do afterward.
- What evidence supports the main claim: a real demonstration, a reliable source, an experience, or a clearly labeled illustration.

These are prompts, not a form that must be complete before work begins. Start with rough notes and refine them as the idea becomes clearer.

## Production stages

1. **Shape the premise.** Reduce the idea to one viewer-facing promise. Decide what belongs in this video and what should be saved for another one.
2. **Check the facts.** Use current primary sources for claims about products, processes, and events. Separate confirmed behavior from estimates, plans, and opinion.
3. **Choose a story format and visual direction.** Decide how the idea will unfold and what the viewer will see. A format and a visual treatment can be combined; see [Video Formats and Visual Treatments](VIDEO_FORMATS_AND_TREATMENTS.md).
4. **Plan beats and scenes.** Outline the story beats, then storyboard the scenes that communicate them. A beat may span multiple scenes, and a scene may serve more than one beat.
5. **Write or refine the spoken words.** Keep the language consistent with the creator's voice. Make on-screen text support the spoken idea instead of repeating every sentence.
6. **Choose the production method.** Use genuine screen or camera capture when the viewer needs proof of real behavior. Use graphics, animation, or illustration when they make an idea easier to understand. Choose tools based on the work and the required editability.
7. **Build a small reviewable slice.** Create a short representative section before expanding the full video. Check whether the design, text size, motion, and pacing work in context.
8. **Render a review copy.** Inspect it at normal playback size and listen to the audio. Check clarity, accuracy, readability, pacing, continuity, and accidental private information. Use contact sheets to compare visual stages; watch the video to judge timing and sound.
9. **Revise, then render delivery quality.** Fix issues found in review and follow the selected tool's validated delivery process. Keep test and final exports distinguishable by filename, such as `scene_short-description_low.mp4` and `scene_short-description_high.mp4`.
10. **Record what the project taught you.** Keep the source project, code, important settings, and review notes with the project. Record render timing and performance when measured. Mark reusable ideas as candidates until they have been reviewed.

## Explore visual concepts

Concept exploration can happen at two scales:

- **Scene concepts** test a composition, metaphor, mood, or visual treatment for one part of a video.
- **Recurring visual concepts** explore building blocks that may appear across a series or product, such as diagrams, labels, characters, or transitions. These are candidates for a visual vocabulary, not an approved design system or finished artwork.

For either scale, make a few distinct options, review them against the video’s purpose and evidence, and record what to keep, reject, or refine. Keep source references, generated proposals, selected designs, and finished editable artwork clearly distinguished. A generated image can help explore a direction, but it does not prove what a reference looked like and is not automatically ready to use in the final video.

## Suggested project folder

Keep the working materials for one video together. Adapt this structure to the project and tool:

```text
video-project/
  README.md             # brief, status, and links to key files
  storyboard.md         # beats, scenes, visual plan, timing
  script.md             # optional when narration or scripted text is used
  code/                 # editable source or builder code
  project/              # optional native authoring project
  assets/               # project assets and source records
  render/
    LOW/                # review exports and performance records
    HIGH/               # delivery-quality exports and performance records
```

Keep large source media, generated audio, frames, contact sheets, and renders in the project's storage rather than committing them to a source repository. Keep editable source and concise project documentation under version control. Follow the repository's own media and licensing rules.

## Review questions

- Does the opening quickly make clear why this video is worth watching?
- Can the viewer follow the idea without relying on narration alone?
- Are demonstrations genuine and claims supported?
- Is each scene doing useful work for the story?
- Can the text be read at the intended viewing size?
- Does the final export play correctly from beginning to end, with synchronized sound and no missing frames or accidental overlays?

Treat the workflow as a practical baseline. Record deviations and useful discoveries instead of forcing every project into the same shape.
