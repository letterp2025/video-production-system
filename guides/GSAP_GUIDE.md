# GSAP Guide

GSAP (GreenSock Animation Platform) is a JavaScript animation engine for sequencing changes to DOM and SVG properties and ordinary JavaScript objects, which can in turn drive canvas drawing. For the Video Production System (VPS), treat GSAP as a way to author and control motion. GSAP does not create a video project, render an MP4, or replace the current EffectCraft and FFmpeg workflows.

This guide describes a study and adaptation path. The VPS does not currently include a browser-based GSAP frame renderer.

## What to study

GSAP's main concepts are:

- **Tweens** change one or more properties over a duration, with an easing curve.
- **Timelines** arrange tweens in sequence or in parallel. Labels, overlaps, staggers, and nested timelines describe choreography without relying on many independent delays.
- **Plugins** add focused capabilities such as text splitting, SVG drawing and morphing, motion paths, and scroll-linked animation.

The [GSAP repository](https://github.com/greensock/GSAP) contains the library source and distribution builds. The [official Demo Hub](https://demos.gsap.com/) is a separate place to explore examples by effect and plugin. Some demo pages link to editable CodePens; for example, the [Magnetic Button demo](https://demos.gsap.com/demo/magnetic-button-overwrite-modes/) links to its CodePen source. The [Showcase](https://gsap.com/showcase/) is primarily a gallery of finished sites and showreels, which is useful for visual research but is not itself a template catalogue. The [official GSAP skills repository](https://github.com/greensock/gsap-skills) adds concise reference patterns and examples for vanilla JavaScript and common frameworks.

Use those sources for different purposes: the Showcase for visual ideas, the Demo Hub and CodePens to inspect techniques, and the GSAP repository and documentation to understand the animation engine.

## Where GSAP can help in video work

GSAP is a useful candidate for motion that can be expressed as a timed sequence, including:

- kinetic titles and word or character reveals;
- layered graphic entrances, exits, and transitions;
- diagram, infographic, and chart motion;
- SVG path drawing, shape movement, and object animation;
- coordinated multi-element choreography with stagger, overlap, holds, and easing.

Animations tied to hover, pointer movement, scrolling, or page navigation need an authored video-time equivalent. For example, replace a `ScrollTrigger`-controlled reveal with a timeline whose progress is driven by seconds.

## Adapt a web demo into a video recipe

1. **Choose the motion idea.** Identify the choreography to reuse, such as a text reveal or a shape transition. Keep the target format, duration, and story purpose in mind.
2. **Inspect the source and dependencies.** Record the demo's author and URL. Identify its HTML, CSS, fonts, images, SVGs, JavaScript, plugins, and any interaction or external service it needs.
3. **Define the recipe before porting.** Describe targets, properties, timing, order, overlap, easing, holds, and parameters such as text, color, direction, and duration.
4. **Remove web-only controls.** Replace scroll, hover, pointer, and page-navigation behavior with a self-contained timeline. Fix the composition size and avoid dependence on a changing viewport.
5. **Make the render repeatable.** Pin the GSAP package version and lock dependencies. Use fixed fonts and assets, avoid uncontrolled random values or wall-clock timing, and ensure images and fonts are ready before capturing frames.
6. **Review the motion as video.** Inspect the opening, key transitions, holds, and final frame. Watch the full sequence at the intended frame rate; a working interactive demo can still have poor pacing as a video.

## Driving a timeline by video time

For a video frame rate of `fps`, frame `n` represents time `n / fps` seconds. A paused GSAP timeline can be moved to an exact point with `seek(time, suppressEvents)`. Suppressing callbacks avoids replaying event callbacks during random access; the renderer should read the resulting scene state and draw each frame itself. See the official [Timeline](https://gsap.com/docs/v3/GSAP/Timeline/) and [`seek()`](https://gsap.com/docs/v3/GSAP/Timeline/seek/) documentation.

The following is a conceptual sketch. `renderFrame` is a placeholder for a renderer; it is not a VPS command or an included GSAP feature.

```js
import { gsap } from "gsap";

const fps = 60;
const frameCount = 180; // 3 seconds at 60 fps
const timeline = gsap.timeline({ paused: true });

timeline.from(".title", {
  y: 48,
  autoAlpha: 0,
  duration: 0.7,
  ease: "power3.out",
});

timeline.from(".accent", {
  scaleX: 0,
  transformOrigin: "left center",
  duration: 0.35,
}, "<0.15");

for (let frame = 0; frame < frameCount; frame += 1) {
  timeline.seek(frame / fps, true);
  await renderFrame(frame); // renderer-specific frame capture
}
```

This approach requires a renderer that can draw the scene after each seek. GSAP supplies the time control and property updates; it does not capture frames. A potential browser-based route is:

```text
HTML / SVG / Canvas scene
        ↓
paused GSAP timeline at frame / fps
        ↓
renderer captures numbered PNG frames
        ↓
FFmpeg encodes the sequence and optionally muxes audio
```

The current VPS video renderer is built around EffectCraft CLI frame renders and FFmpeg section encoding. There is no GSAP or browser-frame capture tool in the repository yet. Until such a renderer is implemented and reviewed, treat GSAP work as a study or prototype, or translate suitable motion recipes into EffectCraft or another supported renderer.

## Add a reusable VPS recipe

Use the existing [Visual Animations Library](../libraries/visual_animations_library/README.md) for reusable motion recipes. Follow its [`ANIMATION_TEMPLATE.md`](../libraries/visual_animations_library/ANIMATION_TEMPLATE.md) and add a tool-specific implementation under the recipe's `code/` directory when the recipe is concrete enough to reuse.

For a GSAP-based entry:

- State clearly that the implementation uses GSAP and record the package version.
- Keep the shared motion idea separate from the HTML, SVG, Canvas, or browser-specific implementation.
- Document parameters, dimensions, frame rate, duration, dependencies, and any renderer assumptions.
- Mark the recipe `Draft` until the output has been rendered and visually reviewed.
- Keep render output, local projects, downloaded media, and other working files out of the public library.

Do not assume that visible demo code or its artwork is cleared for redistribution. Check the terms for each CodePen, font, image, SVG, and other included asset. If reuse rights are unclear, use the demo as a motion reference and create an original implementation and original assets. The library accepts only sources that meet its public-release criteria.

## Licensing checkpoint before integration

GSAP is not MIT-licensed. Its [Standard "No Charge" License](https://gsap.com/standard-license/) grants use for websites, web applications, and digital interfaces, and restricts certain competing no-code animation-builder uses. It does not clearly describe every offline video-rendering or video-production-tool scenario. Before distributing a GSAP runtime with the VPS or building it into a video-rendering tool, confirm that the intended use is covered by the current license; ask GSAP/Webflow for clarification when needed.

The GSAP license covers GSAP products. It does not by itself establish reuse rights for a CodePen author's separate source code or for fonts, images, SVGs, and other media used in a demo. Review those terms separately before adding material to the public library.

## Further reading

- [GSAP documentation](https://gsap.com/docs/v3/GSAP/)
- [Timeline sequencing and controls](https://gsap.com/docs/v3/GSAP/Timeline/)
- [GSAP Demo Hub](https://demos.gsap.com/)
- [GSAP Showcase](https://gsap.com/showcase/)
- [GSAP Standard "No Charge" License](https://gsap.com/standard-license/)
- [GSAP source repository](https://github.com/greensock/GSAP)
- [Official GSAP skills and examples](https://github.com/greensock/gsap-skills)
- [VPS Visual Animations Library](../libraries/visual_animations_library/README.md)
- [EffectCraft section renderer](../tools/effectcraft_ffmpeg_sections/README.md)
