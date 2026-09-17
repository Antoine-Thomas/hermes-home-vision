---
name: diagram-suite
description: Use when creating diagrams — architecture SVG, Excalidraw sketches, or infographics.
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [diagrams, visualization, svg, excalidraw, infographic, architecture]
platforms: [linux, macos, windows]
---

# Diagram Suite

Unified entry point for all diagram/infographic generation. Routes to the right reference based on task type — no behavior change, only structure.

## When to use this skill

- "Create an architecture / infra / cloud diagram" -> `references/architecture-diagram.md`
- "Hand-drawn / whiteboard / Excalidraw sketch" -> `references/excalidraw.md` (+ `references/excalidraw/*.md`)
- "Infographic with layouts/styles (21x21)" -> `references/baoyu-infographic.md` (+ `references/baoyu-infographic/**`)

## Routing

| Request | Reference |
|---------|-----------|
| Dark-themed tech architecture (SVG/HTML, grid-backed) | `references/architecture-diagram.md` |
| Hand-drawn diagrams (Excalidraw JSON) | `references/excalidraw.md` — details: `references/excalidraw/*.md` |
| Infographics (21 layouts x 21 styles) | `references/baoyu-infographic.md` — layouts in `references/baoyu-infographic/layouts/*.md`, styles in `references/baoyu-infographic/styles/*.md` |

## Workflow

1. Identify diagram type from the user's request (architecture / sketch / infographic).
2. Read the matching reference file for full instructions — do not inline all references at once.
3. Follow that reference's workflow to generate the output.

## Notes

- Each reference is the original SKILL.md verbatim (header preserved) — no prompt or logic was altered.
- For animation/video diagrams, prefer `creative/manim-video` or `creative/nle-video-assembly` instead.
