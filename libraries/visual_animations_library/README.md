# Visual animations library

This library catalogs reusable motion recipes: named, parameterized ways to animate one or more visual elements. A recipe captures choreography and timing, not only raw keyframes.

## Terms

- **Animation recipe:** a reusable change over time described by its target, properties, keyframes, interpolation, and timing.
- **Choreography:** how actions combine, including simultaneous groups, sequences, staggered starts, pauses, holds, and transitions.
- **Scene:** the full composition using elements and recipes. Keep complete reference studies in the [Visual Reference Library](../visual_reference_library/README.md).

EffectCraft provides keyframes, interpolations, expressions, and animation presets. This library records reusable combinations and authored timing: what moves, in which order, with which delays and holds, and how the movement feels. Record the EffectCraft layers and properties used. A recipe can have tool-specific implementations in Manim, GSAP, EffectCraft helpers, or another suitable tool; explain the shared motion idea separately from that code. Keep implementations in `code/`, grouping them by tool (for example, `code/gsap/`) when an entry has multiple versions. A GSAP entry may include JavaScript plus the minimal HTML/CSS host it needs.

Manim patterns such as `Write`, `Transform`, `AnimationGroup`, `Succession`, and `LaggedStart` provide design vocabulary, not an assumed one-to-one port. See the official [Manim composition reference](https://docs.manim.community/en/stable/reference/manim.animation.composition.html) and the [EffectCraft keyframe guide](https://github.com/storytold/effectcraft/blob/main/docs/agents.md).

## Add a recipe

1. Choose a concise descriptive slug, check the public and private animation libraries for a collision, and create the folder using `ANM-<slug>` as both its name and ID.
2. Copy [`ANIMATION_TEMPLATE.md`](ANIMATION_TEMPLATE.md) to the entry as `NOTES.md`.
3. Link its source scene or reference and say whether the motion was observed or invented for the recreation.
4. Describe target elements, animated properties, key times and values, easing, order, stagger, duration, holds, and useful parameters. State whether EffectCraft times use layer or composition time.
5. Add a source example only after the recipe is concrete enough to reuse. Keep projects, renders, and previews local and ignored.
6. Add a row to the index. Keep entries in Draft until an implementation is rendered and reviewed.

Typical entry:

```text
ANM-short-name/
  NOTES.md
  code/       # optional implementation for one or more tools
  project/    # optional local example project; ignored
  preview/    # optional local motion check; ignored
```

## Index

| ID | Recipe | Pattern | Source | Status |
|---|---|---|---|---|
| [ANM-cell-grid-shape-reveal](ANM-cell-grid-shape-reveal/NOTES.md) | Cell-grid shape reveal and field pulse | Multi-element choreography | 11kfire.com; uses [ELM-pixel-cell-grid](../visual_elements_library/ELM-pixel-cell-grid/NOTES.md) | Flame video reviewed; heart target rendered as a still |

Add future recipes from public-domain, permissively licensed, original, or otherwise cleared sources. Keep a separate internal review until a source is suitable for public release.
