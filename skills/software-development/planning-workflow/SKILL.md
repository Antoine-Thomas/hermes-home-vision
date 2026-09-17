---
name: planning-workflow
description: Use when planning work — write .hermes/plans/, run spikes, or verify specs before implementing.
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [planning, spike, specs, workflow, hermes-plans]
platforms: [linux, macos, windows]
---

# Planning Workflow

Unified planning entry: plan writing, throwaway spikes, and spec verification — one router, three references.

## When to use this skill

- Write a markdown plan to `.hermes/plans/` (no execution) -> `references/plan.md`
- Throwaway experiment to validate an idea -> `references/spike.md`
- Verify prescribed commands/values before implementing -> `references/verify-specs-before-implementing.md`

## Routing

| Request | Reference |
|---------|-----------|
| Plan to .hermes/plans/ | `references/plan.md` |
| Spike / experiment | `references/spike.md` |
| Verify specs before implementing | `references/verify-specs-before-implementing.md` (+ `references/verify-specs-before-implementing/*.md` 3 files) |

## Workflow

1. Identify planning phase (plan / spike / verify).
2. Read the matching reference only.
3. Follow its workflow — plans are markdown-only, spikes are throwaway, verification is pre-implementation.

## Related

- `software-development/systematic-debugging` for post-plan debugging
