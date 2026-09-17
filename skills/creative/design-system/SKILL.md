---
name: design-system
description: Use when designing HTML/CSS UIs — product pages, design systems, or DESIGN.md tokens.
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [design, html, css, ui, design-systems, tailwind, tokens, wcag]
platforms: [linux, macos, windows]
---

# Design System

Unified entry point for HTML/CSS design work. Three references, one router:

- `claude-design` — design process & taste (brief, variants, artifact verification)
- `popular-web-designs` — 54 real design systems as copy-ready CSS
- `design-md` — author/validate/export Google DESIGN.md token specs

## When to use this skill

- "Design a landing / dashboard / prototype" -> `references/claude-design.md`
- "Make it look like Stripe / Linear / Vercel" -> `references/popular-web-designs.md`
- "Create or validate a DESIGN.md / design tokens" -> `references/design-md.md`

## Routing

| Request | Reference |
|---------|-----------|
| Design process, taste, variants, artifact checks | `references/claude-design.md` |
| Real-world CSS systems (54 templates) | `references/popular-web-designs.md` |
| DESIGN.md spec (YAML tokens + prose) | `references/design-md.md` |

## Workflow

1. Identify the design task (process / system replication / token spec).
2. Read the single matching reference — avoid loading all three at once.
3. Follow that reference's instructions. For cross-skill work (e.g., clone a system then polish with Claude taste), read both sequentially.

## Related skills

- `creative/diagram-suite` for diagrams, `creative/p5js` for generative art.
