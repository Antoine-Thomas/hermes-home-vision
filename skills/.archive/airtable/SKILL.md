---
name: airtable
description: Airtable REST API via curl. Records CRUD, filters, upserts.
version: 1.1.0
author: community
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [AIRTABLE_API_KEY]
  commands: [curl]
metadata:
  hermes:
    tags: [Airtable, Productivity, Database, API]
    homepage: https://airtable.com/developers/web/api/introduction
---


# Airtable — Bases, Tables & Records

Work with Airtable's REST API directly via `curl` using the `terminal` tool. No MCP server, no OAuth flow, no Python SDK — just `curl` and a personal access token.

## Sections

Detailed content is split into references. Read the relevant file before the task.

| Section | Reference |
|---|---|
| Prerequisites | `references/prerequisites.md` |
| API Basics | `references/api-basics.md` |
| Field Types (request body shapes) | `references/field-types-request-body-shapes.md` |
| Common Queries | `references/common-queries.md` |
| Common Mutations | `references/common-mutations.md` |
| Pagination | `references/pagination.md` |
| Typical Hermes Workflow | `references/typical-hermes-workflow.md` |
| Pitfalls | `references/pitfalls.md` |
| Important Notes for Hermes | `references/important-notes-for-hermes.md` |
