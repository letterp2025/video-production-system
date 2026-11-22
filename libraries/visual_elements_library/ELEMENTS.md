# Visual Element Ideas

**Reviewed:** 2026-11-19

**Type:** Planning catalog; entries here are ideas, not completed reusable assets.

This file keeps a working list of visual elements we may build for video. The [Visual Reference Library](../visual_reference_library/README.md) keeps complete scenes and evidence; once an idea has been designed, tested, and is useful beyond its source scene, give it an `ELM-<slug>` entry using the [element template](ELEMENT_TEMPLATE.md).

## One element, many visual treatments

An element describes what is drawn; its visual treatment describes how it is drawn or painted. A card, title, line, or diagram can take many looks: retro, minimal, high contrast, editorial, hand-drawn, and countless combinations of these. These are examples, not the full set of styles or a limit on what we can create. For example, the service card from REF-color-block-service-cards could keep the same image area, title, and caption while we explore retro print texture, clean minimal color, or a bold high-contrast treatment.

Keep those looks as variants of one element when its structure and purpose stay the same. Create separate entries when the structure or use changes meaningfully. Motion belongs in the separate [Visual Animations Library](../visual_animations_library/README.md).

## Inspiration source: Magic UI

[Magic UI](https://magicui.design/docs/components) is an open source React component library. Its component catalog is useful to browse for cards, typography, borders, backgrounds, buttons, and presentation graphics. The [repository license](https://github.com/magicuidesign/magicui/blob/main/LICENSE.md) is MIT.

We are collecting visual ideas from its components, not adopting its React runtime as our video workflow. Recreate an idea with whichever tool fits, usually EffectCraft or Manim. Browser interactions such as hover, scroll, and cursor tracking can be redesigned as planned events on a video timeline. If we later copy upstream source code, retain the MIT copyright and license notice with the copied portion.

## Candidate list

### Layout and composite pieces

| Idea | What we could make for video | Inspiration / source | Status |
|---|---|---|---|
| Color-block service card | Framed image area, bold label, short caption, solid color block; extend a studied three-card scene into a reusable card. | Original recreation candidate | Reference tested; not extracted |
| Bento panel group | Modular grid of panels with varied sizes; useful for feature summaries or several related facts. | [Bento Grid](https://magicui.design/docs/components/bento-grid) | Idea |
| Spotlight card | A card with a moving light pool or highlighted region, timed as a deliberate sweep. | [Magic Card](https://magicui.design/docs/components/magic-card) | Idea |
| Gradient feature card | Large color field, edge treatment, and a simple icon or title. | [Neon Gradient Card](https://magicui.design/docs/components/neon-gradient-card) | Idea |
| Message or quote card | Compact post-like panel with a name, quote, badge, or small image. | [Tweet Card](https://magicui.design/docs/components/tweet-card) | Idea |
| Stacked reveal cards | A short sequence of panels that arrive, overlap, and settle into a group. | [Animated List](https://magicui.design/docs/components/animated-list) | Idea |
| Device frame | Reusable simplified phone or browser window to hold a screenshot, UI, or video still. | [iPhone](https://magicui.design/docs/components/iphone), [Safari](https://magicui.design/docs/components/safari) | Idea |

### Type and labels

| Idea | What we could make for video | Inspiration / source | Status |
|---|---|---|---|
| Headline treatment | A title system with selected words, line breaks, weight contrast, and a consistent safe area. | [Text Animate](https://magicui.design/docs/components/text-animate), [Text Reveal](https://magicui.design/docs/components/text-reveal) | Idea |
| Highlight marker | A hand-drawn line, box, or color swipe that appears behind one phrase. | [Text Highlighter](https://magicui.design/docs/components/text-highlighter) | Idea |
| Word swap title | A fixed text line whose final word changes or morphs between states. | [Morphing Text](https://magicui.design/docs/components/morphing-text), [Word Rotate](https://magicui.design/docs/components/word-rotate) | Idea; animation work is tracked in [ANIMATIONS.md](../visual_animations_library/ANIMATIONS.md) |
| Numeric callout | A large number, label, and supporting line for a statistic or comparison. | [Number Ticker](https://magicui.design/docs/components/number-ticker) | Idea |
| Kinetic word | A single word whose shape, weight, or position becomes the graphic. | [Kinetic Text](https://magicui.design/docs/components/kinetic-text) | Idea |
| Caption tag | Small label, category pill, date, or speaker marker that can attach to a larger element. | [Animated Shiny Text](https://magicui.design/docs/components/animated-shiny-text) | Idea |

### Lines, borders, and framing

| Idea | What we could make for video | Inspiration / source | Status |
|---|---|---|---|
| Drawn outline | Rectangle, circle, underline, arrow, or custom path drawn to frame a point. | [Line Shadow Text](https://magicui.design/docs/components/line-shadow-text) | Idea |
| Traveling border highlight | A short bright segment moving around a panel edge, with duration and direction under timeline control. | [Border Beam](https://magicui.design/docs/components/border-beam) | Idea |
| Border glint | A restrained light sweep across one edge or corner. | [Shine Border](https://magicui.design/docs/components/shine-border) | Idea |
| Connector beam | A line that draws between two objects to show a relationship or transfer. | [Animated Beam](https://magicui.design/docs/components/animated-beam) | Idea |
| Placeholder media frame | A crop window with a clear frame and temporary image placeholder, ready for later replacement. | Original recreation candidate | Reference tested in scene |

### Backdrops and graphic motifs

| Idea | What we could make for video | Inspiration / source | Status |
|---|---|---|---|
| Dot field | Sparse dots, mapped clusters, or a reveal through a dot grid. | [Dot Pattern](https://magicui.design/docs/components/dot-pattern) | Idea |
| Grid field | Quiet grid, animated line draw, or grid that appears behind a diagram. | [Grid Pattern](https://magicui.design/docs/components/grid-pattern) | Idea |
| Retro perspective grid | A floor-like perspective grid for a transition or a data scene. | [Retro Grid](https://magicui.design/docs/components/retro-grid) | Idea |
| Striped field | Diagonal or horizontal lines as a mask, divider, or background texture. | [Striped Pattern](https://magicui.design/docs/components/striped-pattern) | Idea |
| Dither texture | A controlled dot or halftone field for texture and transitions. | [Dither Field](https://magicui.design/docs/components/dither-field) | Idea |
| Aurora color field | Slow, soft color movement behind a title or graphic. | [Aurora Text](https://magicui.design/docs/components/aurora-text) | Idea |
| Particle field | A small number of drifting points or sparks, kept subordinate to the content. | [Particles](https://magicui.design/docs/components/particles), [Meteors](https://magicui.design/docs/components/meteors) | Idea |

### Diagrams and data graphics

| Idea | What we could make for video | Inspiration / source | Status |
|---|---|---|---|
| Orbit diagram | Central subject with a few labels or icons moving on controlled paths. | [Orbiting Circles](https://magicui.design/docs/components/orbiting-circles) | Idea |
| Icon or logo cloud | A controlled field of marks that groups around or moves toward a point. | [Icon Cloud](https://magicui.design/docs/components/icon-cloud) | Idea |
| Progress ring | A circular stroke or small number of steps that fills to a chosen value. | [Animated Circular Progress Bar](https://magicui.design/docs/components/animated-circular-progress-bar) | Idea |
| Simple chart pieces | Bars, connecting lines, dots, labels, and a readable key, built as editable vector pieces. | Manim graphing and geometry objects; add a specific source scene when selected. | Idea |

## Choosing what to build first

When picking an idea, favor pieces that can be reused across different topics, can be built from editable text and vector shapes, and still read clearly at video size. First likely candidates are the service card, headline treatment, highlight marker, outlined callout, connector beam, and a small set of patterned backgrounds. Treat mouse-driven browser effects as a visual reference; simplify or pre-time them for rendered video.
