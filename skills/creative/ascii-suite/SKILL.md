---
name: ascii-suite
description: Use when generating ASCII art or ASCII video — pyfiglet, image-to-ascii, video-to-ascii.
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [ascii, art, video, pyfiglet, image-to-ascii]
platforms: [linux, macos, windows]
---

# ASCII Suite

Unified entry point for ASCII generation. Two references in one umbrella — shared tools, one router.

## When to use this skill

- Static ASCII (text, image -> ASCII, cowsay, boxes, pyfiglet) -> `references/ascii-art.md`
- Animated ASCII (video/audio -> colored ASCII MP4/GIF) -> `references/ascii-video.md` (+ `references/ascii-video/*.md`)

## Routing

| Request | Reference |
|---------|-----------|
| ASCII art: text/images to ASCII | `references/ascii-art.md` |
| ASCII video: video/audio to ASCII MP4/GIF | `references/ascii-video.md` — details: `references/ascii-video/{architecture,composition,effects,inputs,optimization,scenes,shaders,troubleshooting}.md` |

## Workflow

1. Decide: static art vs. animated video.
2. Read the matching reference for full instructions.
3. Both skills use compatible tooling (pyfiglet, image-to-ascii libs, ffmpeg); pipeline steps are per-reference.

## Notes

- `references/ascii-video.md` was 248 lines + 8 refs (7943 lines total) — refs now at `references/ascii-video/*.md`.
- No behavior change; SKILL.md bodies are preserved verbatim in references/.
