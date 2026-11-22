# Raster-to-Vector Study

**Status:** Tested as an assistive workflow; no production-ready one-click tracing utility is included.

This study compared an external color tracer with EffectCraft's SVG-to-shape import path. The experiment showed that a raster trace can become editable native vector paths, but the conversion does not identify semantic objects or recover the original artist's paths.

## Findings

- A trace can be a useful contour starting point for a still image or isolated object.
- More simplification reduces path count but can merge nearby forms and lose color boundaries.
- Keeping more color detail can increase overlapping paths and cleanup.
- EffectCraft can import SVG geometry as editable shape data in the tested path.
- A shape layer does not automatically split a complex illustration into separately named timeline objects.
- Animation still needs manual cleanup, object separation, and keyframes.

## Practical workflow

1. Crop or isolate one object from a frame.
2. Trace it to SVG with a chosen external tool.
3. Inspect path count, color regions, contours, and gradients.
4. Import the SVG into EffectCraft and inspect the resulting native paths.
5. Clean contours and separate semantic parts before animation.
6. Compare the result against the source before using it.

VTracer is one candidate for color tracing. Its output is an approximation and may need substantial cleanup. EffectCraft's built-in Auto-trace is a separate mask workflow and does not segment a full-color image into semantic objects.

## Links

- [VTracer](https://github.com/visioncortex/vtracer)
- [EffectCraft releases and source](https://github.com/storytold/effectcraft)
- [Potrace](https://potrace.sourceforge.net/)

No source artwork, screenshots, traced image, or project file from the original study is included here.