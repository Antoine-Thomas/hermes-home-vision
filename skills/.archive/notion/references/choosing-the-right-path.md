# Choosing the Right Path

> Source skill: `notion` (v2.0.0). Split from SKILL.md on 2026-09-10.


| Task | mac / Linux | Windows |
|---|---|---|
| Read/write pages, search, query databases | `ntn api ...` | curl |
| Read a page for an agent to summarize | `ntn api v1/pages/{id}/markdown` | curl `/markdown` endpoint |
| Upload a file | `ntn files create < file` | 3-step HTTP flow |
| One-off API exploration | `ntn api ...` | curl |
| Build a sync / webhook / agent tool hosted by Notion | `ntn workers ...` | WSL2 + `ntn workers ...` |
