# Typical Hermes Workflow

> Source skill: `airtable` (v1.1.0). Split from SKILL.md on 2026-09-10.


1. **Confirm auth.** `curl -s -o /dev/null -w "%{http_code}\n" https://api.airtable.com/v0/meta/bases -H "Authorization: Bearer $AIRTABLE_API_KEY"` — expect `200`.
2. **Find the base.** List bases (step above) OR ask the user for the `app...` ID directly if the token lacks `schema.bases:read`.
3. **Inspect the schema.** `GET /v0/meta/bases/$BASE_ID/tables` — cache the exact field names and primary-field name locally in the session before mutating anything.
4. **Read before you write.** For "update X where Y", `filterByFormula` first to resolve the `rec...` ID, then `PATCH /v0/$BASE_ID/$TABLE/$RECORD_ID`. Never guess record IDs.
5. **Batch writes.** Combine related creates into one 10-record POST to stay under the 5 req/sec budget.
6. **Destructive ops.** Deletions can't be undone via API. If the user says "delete all Xs", echo back the filter + record count and confirm before firing.
