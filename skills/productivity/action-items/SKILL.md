---
name: action-items
description: "Extract cited decisions, obligations, deadlines, tasks from docs and meetings."
version: 1.0.0
author: Ben Barclay (benbarclay), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Action-Items, Meetings, Documents, Deadlines, Decisions, Extraction, Follow-Up, Productivity]
    category: productivity
    related_skills: [office-documents, teams-meeting-pipeline, notion]
---

# Action Items

Turn source material into cited, accountable action items: obligations,
deadlines, owners, and follow-up tasks — from documents or from meeting
notes/transcripts. Extraction is not legal advice; low-confidence OCR and
ambiguous language stay visible.

Consolidates the former `document-to-action-items` and
`meeting-action-items` skills (archived under `.archive/productivity/`).

## When to Use

- "Extract deadlines and obligations from this contract." → `references/document-to-action-items.md`
- "Extract action items from this meeting." / "Who owns what?" → `references/meeting-action-items.md`

**Shared discipline (both paths):**

- Cite every fact/action to its source (page, quote, timestamp).
- Never invent owners or due dates — record `unresolved` instead.
- Draft ≠ publish: only write to an external tracker after explicit approval.
- Preserve modality ("may" vs "should" vs "must"); don't turn suggestions or brainstorming into obligations/decisions.
- Before creating anything, reconcile against the existing tracker to avoid duplicates.

## Procedure (shape common to both)

1. Inventory the source (files, version, completeness, scan/transcript quality).
2. Extract evidence with provenance (text/tables + location coordinates).
3. Separate facts vs obligations vs decisions vs proposals vs risks.
4. Validate internally (dates, totals, names, contradictions surfaced).
5. Normalize into action items: outcome, owner, due date, dependency, acceptance, citation.
6. Reconcile with the existing tracker (notion, github-issues, calendar, spreadsheet).
7. Apply only approved changes; read back and verify each record.

## References

- `references/document-to-action-items.md` — full document pipeline + pitfalls.
- `references/meeting-action-items.md` — full meeting pipeline + normalization table + pitfalls.
