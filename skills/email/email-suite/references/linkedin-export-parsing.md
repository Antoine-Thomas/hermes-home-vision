# LinkedIn Data Export Parsing

When the user drops a LinkedIn "Basic_LinkedInDataExport" ZIP (lands in `~/Downloads/Basic_LinkedInDataExport_MM-DD-YYYY.zip`), extract and parse it to harvest emails + enrich contacts. No OAuth/API needed — it's an offline CSV archive.

## Connections.csv — NON-STANDARD header (the big gotcha)

A naive `csv.DictReader` on the whole file returns garbage (`{'Notes:': '...'}`). The file has a **3-line preamble before the real header**:

- Line 0: `Notes:`
- Line 1: a long note explaining emails are only visible for connections who enabled "allow connections to download email" (https://www.linkedin.com/psettings/privacy/email)
- Line 2: empty
- Line 3: real header: `First Name,Last Name,URL,Email Address,Company,Position,Connected On`
- Line 4+: data rows

Parse correctly:

```python
lines = open(path, encoding="utf-8").read().strip().split("\n")
reader = csv.DictReader(lines[3:])   # skip the 3-line preamble
```

The header row itself is NOT line 0 — always skip to index 3.

## Email yield is tiny — set expectations

LinkedIn only exports the `Email Address` for connections who opted into sharing it. Typical yield: **~1-2%** (e.g. 13 emails on 937 connections). Most rows have an empty Email Address. Do NOT overpromise LinkedIn as an email source; its real value is **Company + Position enrichment** (useful for scoring/segmenting pro contacts).

## Other files worth parsing

- `messages.csv` — columns include `CONTENT` and `SUBJECT` (also `FROM`, `TO`). People often paste their email in a message body. Regex-extract `[\w.+-]+@[\w-]+\.[\w.-]+`, then filter out `linkedin`, `bounce`, `invitations`, `noreply`, `notification` addresses. Yield here: ~5-7 real emails.
- `Email Addresses.csv` — the USER's own email addresses. Add these to the self-exclusion set so you never mail yourself.
- `Invitations.csv` — columns `From,To,Sent At,Message,Direction,inviterProfileUrl,inviteeProfileUrl`. Rarely has emails; check `Message` field only.
- `Profile.csv`, `Positions.csv`, `Skills.csv`, `Education.csv` — profile enrichment (for personalizing emails / CV content), not contacts.

## Integration pattern (incremental)

1. Extract emails from Connections.csv (skip preamble) + messages.csv.
2. Deduplicate case-insensitively against the existing campaign CSV.
3. Add only NEW emails to the campaign CSV (mark source `linkedin_connections`).
4. Re-run the campaign script — it skips already-sent addresses via the tracking file, so it sends only the new batch. No need to rebuild the whole list.

## Don't bother crawling LinkedIn/Facebook/GitHub directly

LinkedIn redirects to an authwall for every profile (even partial views) — curl/browser scraping returns nothing. Facebook stopped exposing friend emails in 2018. GitHub masks emails by default and rate-limits without a token. The official data export (above) is the only reliable, legal path. Direct the user to do the export rather than attempting scraping — see `references/contact-verification.md` for the same lesson on French business directories.
