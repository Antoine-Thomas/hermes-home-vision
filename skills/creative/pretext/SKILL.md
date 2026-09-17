---
name: pretext
description: Build creative browser demos with DOM-free text layout.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [creative-coding, typography, pretext, ascii-art, canvas, generative, text-layout, kinetic-typography]
    related_skills: [p5js, claude-design, excalidraw, architecture-diagram]
---

# Pretext Creative Demos


## Overview

[`@chenglou/pretext`](https://github.com/chenglou/pretext) is a 15KB zero-dependency TypeScript library by Cheng Lou (React core, ReasonML, Midjourney) for **DOM-free multiline text measurement and layout**. It does one thing: given `(text, font, width)`, return the line breaks, per-line widths, per-grapheme positions, and total height — all via canvas measurement, no reflow.

That sounds like plumbing. It is not. Because it is fast and geometric, it is a **creative primitive**: you can reflow paragraphs around a moving sprite at 60fps, build games whose level geometry is made of real words, drive ASCII logos through prose, shatter text into particles with exact per-grapheme starting positions, or pack shrink-wrapped multiline UI without any `getBoundingClientRect` thrash.

This skill exists so Hermes can make **cool demos** with it — the kind people post to X. See `pretext.cool` and `chenglou.me/pretext` for the community demo corpus.

## References

This skill was split to meet max 200 lines. Details in `references/`:

| Section | File |
|---------|------|
| When to Use | `references/when-to-use.md` |
| Creative Standard | `references/creative-standard.md` |
| Stack | `references/stack.md` |
| The Two Use Cases | `references/the-two-use-cases.md` |
| Demo Recipe Patterns | `references/demo-recipe-patterns.md` |
| Workflow | `references/workflow.md` |
| Performance Notes | `references/performance-notes.md` |
| Common Pitfalls | `references/common-pitfalls.md` |
| Verification Checklist | `references/verification-checklist.md` |
| Reference: Community Demos | `references/reference-community-demos.md` |

