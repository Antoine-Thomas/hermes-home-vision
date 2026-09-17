# Performance Notes

> Source: creative/pretext/SKILL.md — split 2026-09-10.

- `prepare()` / `prepareWithSegments()` is the expensive call. Do it **once** per text+font pair. Cache the handle.
- On resize, only rerun `layout()` / `layoutWithLines()` — never re-prepare.
- For per-frame animations where text doesn't change but geometry does, `layoutNextLineRange` in a tight loop is cheap enough to do every frame at 60fps for normal-length paragraphs.
- When rendering ASCII masks per frame, keep a cell buffer (`Uint8Array`/typed arrays), derive measured per-row obstacle spans from the cells or projected geometry, merge spans, then feed those spans into `layoutNextLineRange` before drawing text.
- Keep visual animation and layout animation coupled. If a sphere morphs into a cube, tween both the rendered cell buffer and the obstacle spans with the same value; otherwise the demo looks painted-on instead of physically reflowed.
- For fades, prefer layer opacity over changing glyph intensity or obstacle scale. Put transient ASCII sprites on their own canvas and fade the canvas with CSS/GSAP opacity so geometry does not appear to shrink.
- Canvas `ctx.font` setting is surprisingly slow; set it **once** per frame if font doesn't vary, not per `fillText` call.
