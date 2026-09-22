# API Basics

> Source skill: `airtable` (v1.1.0). Split from SKILL.md on 2026-09-10.


- **Endpoint:** `https://api.airtable.com/v0`
- **Auth header:** `Authorization: Bearer $AIRTABLE_API_KEY`
- **All requests** use JSON (`Content-Type: application/json` for any POST/PATCH/PUT body).
- **Object IDs:** bases `app...`, tables `tbl...`, records `rec...`, fields `fld...`. IDs never change; names can. Prefer IDs in automations.
- **Rate limit:** 5 requests/sec/base. `429` → back off. Burst on a single base will be throttled.

Base curl pattern:
```bash
curl -s "https://api.airtable.com/v0/$BASE_ID/$TABLE?maxRecords=5" \
  -H "Authorization: Bearer $AIRTABLE_API_KEY" | python -m json.tool
```

`-s` suppresses curl's progress bar — keep it set for every call so the tool output stays clean for Hermes. Pipe through `python -m json.tool` (always present) or `jq` (if installed) for readable JSON.
