# Important Notes for Hermes

> Source skill: `airtable` (v1.1.0). Split from SKILL.md on 2026-09-10.


- **Always use the `terminal` tool with `curl`.** Do NOT use `web_extract` (it can't send auth headers) or `browser_navigate` (needs UI auth and is slow).
- **`AIRTABLE_API_KEY` flows from `${HERMES_HOME:-~/.hermes}/.env` into the subprocess automatically** when this skill is loaded — no need to re-export it before each `curl` call.
- **Escape curly braces in formulas carefully.** In a heredoc body, `{Status}` is literal. In a shell argument, `{Status}` is safe outside `{...}` brace-expansion context — but pass dynamic strings through `python urllib.parse.quote` before splicing into a URL.
- **Pretty-print with `python -m json.tool`** (always present) rather than `jq` (optional). Only reach for `jq` when you need filtering/projection.
- **Pagination is per-page, not global.** Airtable's 100-record cap is a hard limit; there is no way to bump it. Loop with `offset` until the field is absent.
- **Read the `errors` array** on non-2xx responses — Airtable returns structured error codes like `AUTHENTICATION_REQUIRED`, `INVALID_PERMISSIONS`, `MODEL_ID_NOT_FOUND`, `INVALID_MULTIPLE_CHOICE_OPTIONS` that tell you exactly what's wrong.
