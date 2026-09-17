# Pitfalls

> Source skill: `airtable` (v1.1.0). Split from SKILL.md on 2026-09-10.


- **`filterByFormula` MUST be URL-encoded.** Field names with spaces or non-ASCII also need encoding (`{My Field}` → `%7BMy%20Field%7D`). Use Python stdlib (pattern above) — never hand-escape.
- **Empty fields are omitted from responses.** A missing `"Assignee"` key doesn't mean the field doesn't exist — it means this record's value is empty. Check the schema (step 3) before concluding a field is missing.
- **PATCH vs PUT.** `PATCH` merges supplied fields into the record. `PUT` replaces the record entirely and clears any field you didn't include. Default to `PATCH`.
- **Single-select options must exist.** Writing `"Status": "Shipping"` when `Shipping` isn't in the field's option list errors with `INVALID_MULTIPLE_CHOICE_OPTIONS` unless you pass `"typecast": true` (which auto-creates the option).
- **Per-base token scoping.** A `403` on one base while another works means the token's Access list doesn't include that base — not a scope or auth issue. Send the user to https://airtable.com/create/tokens to grant it.
- **Rate limits are per base, not per token.** 5 req/sec on `baseA` and 5 req/sec on `baseB` is fine; 6 req/sec on `baseA` alone will throttle. Monitor the `Retry-After` header on `429`.
