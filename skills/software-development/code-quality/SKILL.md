---
name: code-quality
description: Use when reviewing, debugging, or quality-checking code — reviews, pre-commit gates, systematic debugging.
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [code-review, quality, security, debugging, pre-commit]
platforms: [linux, macos, windows]
---

# Code Quality

Unified entry for code review and debugging workflows. No behavior change — each source skill is preserved verbatim in `references/`.

## When to use this skill

- Full repo review (bugs, debt, security, tests) -> `references/code-review.md`
- Pre-commit review (security scan, quality gates, auto-fix) -> `references/requesting-code-review.md`

## Routing

| Request | Reference |
|---------|-----------|
| Revue depot Git (bugs/dette/secu/tests) | `references/code-review.md` |
| Pre-commit review + quality gates | `references/requesting-code-review.md` |

## Workflow

1. Identify review type (full repo vs. pre-commit).
2. Read the single matching reference for full instructions.
3. For systematic debugging, use `software-development/systematic-debugging` directly (kept separate).

## Related

- `software-development/systematic-debugging` (4-phase RCA)
- `software-development/simplify-code` (parallel cleanup)
- `software-development/test-driven-development`
