---
name: planning-ops
description: "Use when planning or organizing: weekly review/reset, session-library cleanup, next-week plan."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, organization, weekly-review, sessions, productivity]
    category: productivity
    related_skills: [obsidian, notion, airtable, google-workspace]
---

# Planning Ops

One router for planning/organization tasks: the weekly review/reset and
session-library management. No behavior change — full procedures live in the
references below.

## When to use this skill

- "Run my weekly review" / "What did I commit to and what is slipping?" /
  "Plan next week from my calendar, tasks, and notes" -> `references/weekly-review-planning.md`
- "Find/rename/archive/clean up my sessions" / "What sessions do I have
  about X?" / "What did we decide about X?" -> `references/session-librarian.md`

## Routing

| Request | Reference |
|---------|-----------|
| Weekly reset: commitments, stalled work, capacity-aware next-week plan | `references/weekly-review-planning.md` |
| Session library: find, summarize, rename, archive, prune | `references/session-librarian.md` |

## Quick reference

**Weekly review (7 steps, draft-then-approve):** set systems+window →
review calendar evidence → clear capture inboxes → reconcile active projects
→ review waiting/commitments → build capacity-aware plan → apply approved
updates. Default to recommendations, never mutate until scope is approved;
read every changed record back.

**Session library (two surfaces):** `session_search` finds content (FTS5);
`hermes sessions list|rename|archive|delete|prune|export` manage metadata.
Always `--dry-run` destructive commands, prefer `archive` over `delete`, and
show a plan table before anything that mutates.

## Notes

- Each reference is the original SKILL.md verbatim (frontmatter preserved) —
  no prompt or logic was altered.
- Originals `session-librarian` and `weekly-review-planning` archived to
  `.archive/productivity/`.
- Weekly review depends on connector skills (`google-workspace`, `obsidian`,
  `notion`, `airtable`) for calendar/tasks/notes; session library uses the
  `session_search` tool plus the `hermes sessions` CLI.
