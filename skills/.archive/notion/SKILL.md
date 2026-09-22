---
name: notion
description: "Notion API + ntn CLI: pages, databases, markdown, Workers."
version: 2.0.0
author: community
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [NOTION_API_KEY]
metadata:
  hermes:
    tags: [Notion, Productivity, Notes, Database, API, CLI, Workers]
    homepage: https://developers.notion.com
---


# Notion

Talk to Notion two ways. Same integration token works for both — pick by what's available.

◆ **`ntn` CLI** — Notion's official CLI. Shorter syntax, one-line file uploads, required for Workers. macOS + Linux only as of May 2026 (Windows support "coming soon"). **Default when installed.**
◆ **HTTP + curl** — works everywhere including Windows. **Default fallback** when `ntn` isn't installed.

## Sections

Detailed content is split into references. Read the relevant file before the task.

| Section | Reference |
|---|---|
| Setup | `references/setup.md` |
| API Basics | `references/api-basics.md` |
| Path A — `ntn` CLI (preferred, macOS / Linux) | `references/path-a-ntn-cli-preferred-macos-linux.md` |
| Path B — HTTP + curl (cross-platform, default on Windows) | `references/path-b-http-curl-cross-platform-default-on-windows.md` |
| Property Types | `references/property-types.md` |
| API Version 2025-09-03 — Databases vs Data Sources | `references/api-version-2025-09-03-databases-vs-data-sources.md` |
| Notion Workers (advanced, requires `ntn`) | `references/notion-workers-advanced-requires-ntn.md` |
| Notion-Flavored Markdown (used by `/markdown` endpoints) | `references/notion-flavored-markdown-used-by-markdown-endpoints.md` |
| Choosing the Right Path | `references/choosing-the-right-path.md` |
| Notes | `references/notes.md` |
