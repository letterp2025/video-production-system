# Storyboard and Visual Planning

Story planning answers what the viewer should understand. Visual planning answers what the viewer sees and how it changes. Keeping these questions distinct makes revisions easier while allowing the story and visuals to inform one another.

## Begin with whatever you have

A plan can start from raw notes, a question, a rough script, a real product behavior, a reference frame, or a visual concept. A finished script is useful for narration-led work, but it is not required before exploring visuals.

Start by clarifying the viewer, the central question or tension, the intended takeaway, and what evidence can support it. Preserve the creator's original wording separately from proposed rewrites.

## Plan beats before shots

Story beats describe the steps in the viewer's understanding. Common beats include a hook, setup, development or demonstration, a turn, and a close, but the sequence should fit the subject. Give beats stable identifiers such as `B01` and `B02`; keep their order in the outline rather than relying on an ID to encode the final order.

Then decide which scenes communicate each beat. A sentence does not automatically need its own scene. Combine related ideas when one visual can carry them, and use multiple scenes when a beat needs a setup and payoff.

## Keep story planning and visual planning connected

Treat these as two focused passes, whether one person or an AI collaborator handles both:

- **Story planning** shapes the viewer promise, orders the beats, and drafts or reviews the spoken words.
- **Visual planning** maps those beats to scenes, compositions, visible elements, and motion.

Connect the passes with stable beat and scene IDs. A visual planner can flag a story issue it discovers, but should surface it for review instead of silently rewriting the script. Likewise, when wording changes, revisit the scenes whose timing or layout depends on it.

When working with Codex or another AI collaborator, make the requested role and boundaries explicit. For example:

- “Here are rough notes. Preserve my original phrases, identify the viewer-facing promise, and suggest an ordered beat outline. Mark assumptions.”
- “Using beats `B01–B03`, plan the scenes and list the elements and motion. Do not rewrite the narration; flag any story issue separately.”
- “Build a first review slice for `SC01` only. List what is known, what is proposed, and what needs my review.”

## Plan a scene

Use a lightweight scene note such as:

```text
Scene ID: SC01
Beat ID(s): B01
Purpose:
Spoken words / on-screen text:
Starting composition:
Visible elements:
What changes:
Animation and timing:
Transition / sound:
Source or evidence:
Status: idea / planned / built / reviewed
```

The fields can stay brief. Their purpose is to make the scene understandable and buildable, not to create paperwork.

## Keep elements and animation distinct

- **Element:** a visible object or component, such as text, a card, grid, shape, diagram, interface capture, or illustration.
- **Animation:** a change over time, such as a reveal, movement, scale, rotation, color or shape change, pause, or transition.
- **Scene:** the composition and time interval where elements and their motion serve the story.

An element can appear in several scenes with different motion. An animation recipe can apply to different elements when it fits. If the project has a reusable library, record its stable IDs. Otherwise use clear project-level names and avoid claiming a one-off asset is reusable before review.

## Separate evidence from design choices

For references and product demonstrations, record what was directly observed separately from estimates and recreation choices. A generated image can help brainstorm a composition, but it is not evidence of a source design and is not automatically editable artwork. Mark concepts as candidates until they are selected and rebuilt or approved.

For motion, describe the starting state, ending state, approximate duration, easing, holds, and overlap. If timing is estimated from sampled frames, label it as an estimate. Do not describe inferred timing as the original animation data.

## Iterate in small pieces

Build one representative scene or motion first. Review it at normal playback size, then update the storyboard with what changed. If the visual reveals a story problem, flag it for the story plan; if a script change affects duration or layout, revisit the dependent scenes.

The project folder should remain the source of truth for the current brief, script, storyboard, source code or native project, renders, and review notes. See the [video production workflow](VIDEO_PRODUCTION_WORKFLOW.md) for a suggested folder layout.
