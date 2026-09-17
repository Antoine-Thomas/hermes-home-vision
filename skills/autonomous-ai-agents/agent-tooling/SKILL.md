---
name: agent-tooling
description: "Use when building/tooling for agents: author new Hermes skills, reconcile agent merge conflicts."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [agents, skills, tooling, merge-conflict, meta, generation]
    category: autonomous-ai-agents
    related_skills: [hermes-agent, autonomous-ai-agents]
---

# Agent Tooling

One router for agent-building/tooling tasks: authoring new Hermes skills and
reconciling merge conflicts between autonomous agents. No behavior change —
full procedures live in the references below.

## When to use this skill

- "Create a skill that…" / "turn this procedure into a routine" /
  "capitalize this workflow as a skill" -> `references/quick-skill.md`
- Two agents' branches collide / a git merge between agents halts on
  conflicts -> `references/merge-reconciler.md`

## Routing

| Request | Reference |
|---------|-----------|
| Author + validate + install a new Hermes skill from a description | `references/quick-skill.md` |
| Neutral third-party resolution of agent merge conflicts | `references/merge-reconciler.md` |

## Quick reference

**Author a skill:** extract the 6 elements (name, ≤60-char description,
category, triggers, exact steps, verification), write the body to a temp
file, then `python scripts/newskill.py --name … --category … --body …`
(`--dry-run` to preview, `--check` to validate). Description > 60 chars is
the #1 failure. Don't hand-write YAML; the script validates and installs.

**Reconcile a merge:** gather both sides (git status / merge-base / diff +
each side's intent) → classify every hunk (disjoint-intent / same-question-
different-answer / superseded) → resolve per intent, never favor the side
that spawned you, touch only conflict markers → verify build → hand back a
per-hunk decision summary.

## Notes

- Each reference is the original SKILL.md verbatim (frontmatter preserved) —
  no prompt or logic was altered.
- Originals `quick-skill` and `merge-reconciler` archived to
  `.archive/autonomous-ai-agents/`.
- `quick-skill`'s generator script is preserved at
  `scripts/newskill.py` (also still at
  `.archive/autonomous-ai-agents/quick-skill/scripts/newskill.py`).
- The root `autonomous-ai-agents` skill stays the category router for
  delegating coding tasks to external agents.
