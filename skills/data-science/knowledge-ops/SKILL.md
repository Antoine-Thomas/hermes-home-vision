---
name: knowledge-ops
description: "Interactive notebooks + knowledge base: Jupyter live kernel and Obsidian vault."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [jupyter, notebook, repl, obsidian, vault, knowledge-base, data-science, exploration]
    category: data-science
    related_skills: []
---

# Knowledge Ops

Interactive notebooks (stateful Python REPL via hamelnb) + filesystem-first knowledge base (Obsidian vault). One router for iterative exploration and persistent notes.

Consolidates `jupyter-live-kernel` (167l, data-science) + `obsidian` (68l, note-taking) — archived under `.archive/`.

## When to Use

- Stateful Python, incremental exploration, DataFrame inspection → `references/jupyter-live-kernel.md`
- Read, list, search, create, or edit Obsidian vault notes → `references/obsidian.md`

## Skills

| Skill | Reference | Purpose |
|---|---|---|
| jupyter-live-kernel | `references/jupyter-live-kernel.md` | Live Jupyter kernel: stateful REPL, variable inspect, cell editing |
| obsidian | `references/obsidian.md` | Vault ops: vault path, read/list/search/create notes, wikilinks |

## Jupyter Quick Start

```bash
SCRIPT="$HOME/.agent-skills/hamelnb/skills/jupyter-live-kernel/scripts/jupyter_live_kernel.py"
uv run "$SCRIPT" servers --compact
uv run "$SCRIPT" execute --path scratch.ipynb --code 'print(1+1)' --compact
uv run "$SCRIPT" variables --path scratch.ipynb list --compact
```

## Obsidian Quick Start

Resolve vault path from `OBSIDIAN_VAULT_PATH` (or `~/Documents/Obsidian Vault`), then use `read_file`/`search_files`/`write_file` with the absolute path. See `references/obsidian.md` for file vs content search patterns.

## References

- `references/jupyter-live-kernel.md` — verbatim former skill (setup, execute, variables, cell edit, tips).
- `references/obsidian.md` — verbatim former skill (vault path, read/list/search/create, wikilinks).

