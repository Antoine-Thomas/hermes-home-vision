# Common Pitfalls

> Source: creative/pretext/SKILL.md — split 2026-09-10.

1. **Drifting CSS/canvas font strings.** `ctx.font = "16px Inter"` measured, but CSS says `font-family: Inter, sans-serif; font-size: 16px`. Fine *if* Inter loads. If Inter 404s, CSS falls back to sans-serif and measurements drift by 5-20%. Always `preload` the font or use a web-safe family.

2. **Re-preparing inside the animation loop.** Only `layout*` is cheap. Re-calling `prepare` every frame will tank perf. Keep the prepared handle in module scope.

3. **Forgetting `Intl.Segmenter` for grapheme splits.** Emoji, combining marks, CJK — `"é".split("")` gives you two chars. Use `new Intl.Segmenter(undefined, { granularity: "grapheme" })` when sampling individual visible glyphs.

4. **`break: 'never'` chips without `extraWidth`.** In `rich-inline`, if you use `break: 'never'` for an atomic chip/mention, you must also supply `extraWidth` for the pill padding — otherwise chip chrome overflows the container.

5. **Using `@chenglou/pretext` from `unpkg` with TypeScript-only entry.** Use `esm.sh` — it compiles the TS exports to browser-ready ESM automatically. `unpkg` will 404 or serve raw TS.

6. **Monospace fallbacks silently erasing the whole point.** Users seeing monospace-looking output often have a CSS `font-family` that fell through to `monospace`. Verify the actual rendered font via DevTools.

7. **Skipping rows vs adjusting width** when flowing around a shape. If the corridor on this row is too narrow to fit a line, *skip the row* (`y += lineHeight; continue;`) rather than passing a tiny maxWidth to `layoutNextLineRange` — pretext will return one-grapheme lines that look broken.

8. **Shipping a cold demo.** The default first-paint looks tutorial-grade. Add: vignette, subtle scanline, idle auto-motion, one carefully chosen interactive response (drag, hover, scroll, click). Without these, "cool pretext demo" lands as "intern repro of the README."
