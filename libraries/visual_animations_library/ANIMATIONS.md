# Animation Ideas and Manim Inventory

**Reviewed:** 2026-11-19

**Type:** Planning catalog; the Manim names below are API references, not a claim that we have tested every animation.

This file has two purposes: keep a cross-tool list of motion ideas we may reuse, and map the full animation class list shown in the current stable Manim Community reference. A selected, concrete recipe may get a draft `ANM-<slug>` entry before implementation; mark it tested only after we render and review it. Use the [animation template](ANIMATION_TEMPLATE.md). Complete reference scenes stay in the [Visual Reference Library](../visual_reference_library/README.md).

## Manim animation families

The current stable reference is Manim Community **v0.22.1**. This inventory follows the class links in its [Animation reference section](https://docs.manim.community/en/stable/reference.html#animations). The page groups the API by module; the short descriptions below summarize the family, and the class names are the documented names.

| Family | What it is useful for | Classes listed in the reference |
|---|---|---|
| Core and timing | Base animation, adding an object, holding a scene, and changing playback speed. | `Add`, `Animation`, `Wait`, `ChangeSpeed` |
| Live changes | Animated boundary or a traced path that follows a moving object. | `AnimatedBoundary`, `TracedPath` |
| Composition | Run motions together, in sequence, or with staggered starts. | `AnimationGroup`, `LaggedStart`, `LaggedStartMap`, `Succession` |
| Creation and removal | Draw paths, reveal text or groups, show partial geometry, type with a cursor, or reverse the reveal. | `AddTextLetterByLetter`, `AddTextWordByWord`, `Create`, `DrawBorderThenFill`, `RemoveTextLetterByLetter`, `ShowIncreasingSubsets`, `ShowPartial`, `ShowSubmobjectsOneByOne`, `SpiralIn`, `TypeWithCursor`, `Uncreate`, `UntypeWithCursor`, `Unwrite`, `Write` |
| Fading | Fade objects into or out of a scene. | `FadeIn`, `FadeOut` |
| Growing and entrance | Grow from a point, edge, or center; spin an object into view. | `GrowArrow`, `GrowFromCenter`, `GrowFromEdge`, `GrowFromPoint`, `SpinInFromNothing` |
| Attention and emphasis | Wave, blink, circle, flash, focus, indicate, pass a highlight, or wiggle. | `ApplyWave`, `Blink`, `Circumscribe`, `Flash`, `FocusOn`, `Indicate`, `ShowPassingFlash`, `ShowPassingFlashWithThinningStrokeWidth`, `Wiggle` |
| Movement and deformation | Follow paths, apply homotopies, or animate phase flow. | `ComplexHomotopy`, `Homotopy`, `MoveAlongPath`, `PhaseFlow`, `SmoothedVectorizedHomotopy` |
| Numbers | Change a decimal display or animate a decimal to a chosen value. | `ChangeDecimalToValue`, `ChangingDecimal` |
| Rotation | Rotate once or keep rotating. | `Rotate`, `Rotating` |
| Specialized | Broadcast a wave of motion outward through objects. | `Broadcast` |
| Transform and morph | Change position, color, shape, function, matrix, or relationship between objects; replace, copy, swap, restore, or transform pieces. | `ApplyComplexFunction`, `ApplyFunction`, `ApplyMatrix`, `ApplyMethod`, `ApplyPointwiseFunction`, `ApplyPointwiseFunctionToCenter`, `ClockwiseTransform`, `CounterclockwiseTransform`, `CyclicReplace`, `FadeToColor`, `FadeTransform`, `FadeTransformPieces`, `MoveToTarget`, `ReplacementTransform`, `Restore`, `ScaleInPlace`, `ShrinkToCenter`, `Swap`, `Transform`, `TransformAnimations`, `TransformFromCopy` |
| Matching transforms | Match compatible pieces between two groups; especially useful for text, equations, and vector symbols. | `TransformMatchingAbstractBase`, `TransformMatchingShapes`, `TransformMatchingTex` |
| Updater-based changes | Update an object or keep it positioned relative to another object. | `MaintainPositionRelativeTo`, `UpdateFromAlphaFunc`, `UpdateFromFunc` |

This is a versioned index, not a promise that every class belongs in our creative vocabulary. The reference can add, rename, deprecate, or regroup classes; check it again before relying on a specific API name.

## Morphing: what it means and what it takes

Manim's basic [`Transform`](https://docs.manim.community/en/stable/reference/manim.animation.transform.Transform.html) moves the points of one Mobject toward a target Mobject. That can look like a genuine shape morph, but Manim is not deciding what two images *mean*. The author chooses the source, target, grouping, path, timing, and how unmatched parts enter or leave.

| Tool | Useful for | What to watch |
|---|---|---|
| `Transform` | Directly change one Mobject into a target, including a different position or shape. | Very different point layouts can stretch or twist in an unattractive way; test the visual path and target structure. |
| `ReplacementTransform` | Morph the source into a target that takes its place in the scene. | Different scene bookkeeping from `Transform`; choose intentionally when later animations refer to the target. |
| `TransformMatchingShapes` | Match subobjects with the same normalized vector shape. It can create letter-to-letter or symbol-to-symbol morphs when glyph contours match. | It matches geometric shape hashes, not spelling or meaning. Repeated or similar glyphs can pair unexpectedly; unmatched parts need a deliberate fade or transform choice. |
| `TransformMatchingTex` | Match rendered LaTeX pieces whose `tex_string` keys match, useful when an equation is regrouped or rearranged. | Specific to Manim's Tex objects, not a general matcher for ordinary text or arbitrary graphics. |
| `FadeTransform` / `FadeTransformPieces` | Blend between objects or their pieces when a point-by-point morph is not the right look. | Often reads more like a designed dissolve/transition than a continuous reshaping. |
| `TransformFromCopy` | Send a visual copy of a source into a new target while retaining the original. | Useful for showing an element being derived, duplicated, or carried into a diagram. |
| `CyclicReplace` / `Swap` | Exchange the places of objects. | Best for clear rearrangement; this is not a contour morph. |

### A small study path

1. **Circle → square.** Use `Transform` on two vector objects. Learn target preparation, easing, runtime, and path direction. Expected effort: low.
2. **One card layout → another.** Transform a few rectangle/text/icon parts together. Compare `Transform`, `ReplacementTransform`, and `FadeTransform`; keep individual parts grouped deliberately. Expected effort: low to medium.
3. **Word → related word.** Use ordinary vector `Text` with `TransformMatchingShapes`; test shared letters, repeated letters, different lengths, and unmatched glyph handling. Expected effort: medium; matching quality matters more than writing the call.
4. **Equation → rearranged equation.** Use `MathTex` and `TransformMatchingTex`; identify which pieces should match by giving them stable Tex strings/groups. Expected effort: medium.
5. **Text or card → icon/logo/diagram.** Break both designs into meaningful subobjects and define or correct the correspondence. Try matched transforms for compatible pieces and fades for the rest. Expected effort: medium to high.
6. **Unrelated complex silhouettes.** Try only after the smaller examples; use hand-built vector paths, subobject mapping, or a designed intermediate state. Expected effort: high and quality-sensitive.

The likely hard part is choosing a good correspondence and shaping the in-between frames, not the basic animation syntax. Vector source shapes are the best first test. A bitmap does not automatically become a well-structured set of vector pieces, and an arbitrary logo/text morph can need manual preparation. Rendering cost and export quality still need their own test; this plan makes no performance claim.

## Reusable motion ideas to consider

| Idea | Manim building blocks to study | Video use |
|---|---|---|
| Word-by-word statement reveal | `AddTextWordByWord`, `Write`, `LaggedStart`, `Wait` | Pace a sentence so one phrase lands at a time. |
| Line drawing | `Create`, `ShowPartial`, `Uncreate` | Draw an underline, box, connector, chart axis, or arrow. |
| Staggered card arrival | `FadeIn`, `GrowFromEdge`, `LaggedStart`, `AnimationGroup` | Bring cards or panels in as one coordinated sequence. |
| Focus cue | `Indicate`, `Circumscribe`, `FocusOn`, `ShowPassingFlash` | Direct attention to one existing object briefly. |
| Path travel | `MoveAlongPath`, `Rotate`, `AnimationGroup` | Move an icon or marker along a vector route. |
| Number count-up | `ChangeDecimalToValue`, `ChangingDecimal` | Introduce a statistic or counter. |
| Morphing statement or graphic | `Transform`, matching transforms, `FadeTransform`, `ReplacementTransform` | Transition between two states with continuity or intentional dissolve. |
| Ordered explanation | `Succession`, `LaggedStart`, `AnimationGroup`, `ChangeSpeed` | Control what happens together, one after another, or with overlap. |

These are starting patterns, not final recipe entries. We can implement a visual idea in Manim, EffectCraft, or another suitable tool; the catalog stores the choreography idea separately from a tool-specific implementation.

## Official references

- [Manim animation reference index](https://docs.manim.community/en/stable/reference.html#animations)
- [Transform](https://docs.manim.community/en/stable/reference/manim.animation.transform.Transform.html)
- [TransformMatchingShapes](https://docs.manim.community/en/stable/reference/manim.animation.transform_matching_parts.TransformMatchingShapes.html)
- [TransformMatchingTex](https://docs.manim.community/en/stable/reference/manim.animation.transform_matching_parts.TransformMatchingTex.html)
- [Transform composition patterns](https://docs.manim.community/en/stable/reference/manim.animation.composition.html)
- [Magic UI component catalog](https://magicui.design/docs/components)
