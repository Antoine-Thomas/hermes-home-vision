# Authoring In-Repo Skills (absorbed from hermes-agent-skill-authoring)

There are two places a SKILL.md can live:

1. **User-local:** `~/.hermes/skills/<maybe-category>/<name>/SKILL.md` — personal, created via `skill_manage(action='create')`.
2. **In-repo:** `/home/bb/hermes-agent/skills/<category>/<name>/SKILL.md` — committed, shipped with the package. Use `write_file` + `git add`.

## Required Frontmatter

```yaml
---
name: my-skill-name               # lowercase, hyphens, ≤64 chars
description: Use when <trigger>. <one-line behavior>.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [short, descriptive, tags]
    related_skills: [other-skill]
---
```

- Starts with `---` as the first bytes.
- `name` field present.
- `description` field present, ≤ 1024 chars.
- Non-empty body after closing `---`.

## Size Limits

- Full SKILL.md: ≤ 100,000 chars (~36k tokens). Aim for 8-14k chars.
- Push bulky details to `references/*.md`.

## Writing Quality Principles

1. **Optimize for process predictability** — what behavior should change when this skill loads?
2. **Choose the right context load** — descriptions are paid for every turn.
3. **Use an information hierarchy** — SKILL.md for always-needed steps, references/ for details.
4. **End steps with completion criteria.**
5. **Co-locate rules with the concept they govern.**
6. **Use strong leading words** (e.g. "tight loop," "root cause," "regression test").
7. **Prune duplication and no-ops.** If a line doesn't change behavior, cut it.

## Peer-Matched Structure

```
# <Title>
## Overview
## When to Use
## <Topic sections>
## Common Pitfalls
## Verification Checklist
```

## Workflow for In-Repo Skills

1. Survey peers in the target category: `ls skills/<category>/`
2. Draft with `write_file` to `skills/<category>/<name>/SKILL.md`
3. Validate locally with Python YAML check
4. `git add` + commit

**Note:** `skill_manage(action='create')` writes to `~/.hermes/skills/`, not the repo tree. Use `write_file` for in-repo creation.

## Common Pitfalls

1. Using `skill_manage(action='create')` for an in-repo skill — it goes to user-local.
2. Leading whitespace before `---` — validator checks `content.startswith("---")`.
3. Description too generic — start with "Use when ..." and describe the trigger class.
4. Forgetting `author`/`license`/`metadata` block.
5. Writing a skill that duplicates a peer — prefer extending existing skills.
6. Expecting the current session to see the new skill — loader is cached at session start.
