# When to Use

> Source: creative/pretext/SKILL.md — split 2026-09-10.

Use when the user asks for:
- A "pretext demo" / "cool pretext thing" / "text-as-X"
- Text flowing around a moving shape (hero sections, editorial layouts, animated long-form pages)
- ASCII-art effects using **real words or prose**, not monospace rasters
- Games where the playfield / obstacles / bricks are made of text (Tetris-from-letters, Breakout-of-prose)
- Kinetic typography with per-glyph physics (shatter, scatter, flock, flow)
- Typographic generative art, especially with non-Latin scripts or mixed scripts
- Multiline "shrink-wrap" UI (smallest container width that still fits the text)
- Anything that would require knowing line breaks *before* rendering

Don't use for:
- Static SVG/HTML pages where CSS already solves layout — just use CSS
- Rich text editors, general inline formatting engines (pretext is intentionally narrow)
- Image → text (use `ascii-art` / `ascii-video` skills)
- Pure canvas generative art with no text role — use `p5js`
