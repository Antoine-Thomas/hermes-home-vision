---
name: contact-filtering
description: Clean, filter, segment, and enrich contact databases (CSV) for B2B prospection. Remove spam, bots, and pseudos; extract names from emails; score and segment contacts.
version: 1.0.0
metadata:
  hermes:
    tags: [contacts, csv, filtering, prospection, email, segmentation, b2b]
---

# Contact Filtering & Segmentation

Clean a raw contact CSV by removing spam, bots, notifications, mailing lists, and pseudos, then segment the survivors into A/B/C tiers for targeted prospection.

## When to Use

- A user provides a raw CSV of contacts (exported from Gmail, LinkedIn, CRM, etc.) and asks to clean it.
- The user wants to remove invalid, spammy, or robotic contacts before an email campaign.
- The user needs contacts scored and segmented by quality for tiered outreach.
- The user wants to enrich contacts via Hunter.io (email verification, professional email discovery).

**Note:** This skill subsumes the former `contact-cleaning` quick-filter workflow. For a single-pass filter without segmentation, use Phase 1–3 of this workflow with a script that stops at the keep/reject decision. The filtering rules below cover all `contact-cleaning` rules (blocked domains, keyword filters, name validation, gibberish detection).

## Workflow

### Phase 1: Inspect the CSV
1. `read_file` with `limit=5` to see the header row and first few records.
2. Count total lines: `wc -l`.
3. Identify the email column(s), name columns, and company column. Google Contacts CSVs use `E-mail 1 - Value`, `First Name`, `Last Name`, `Organization Name`. Adjust column mapping per source.

### Phase 2: Write the Filtering Script

Use Python with the standard library (`csv`, `re`, `pathlib`). The script must include:

**A. Domain blocklist** — domains that are never legitimate contacts:
```python
BLOCKED_DOMAINS = [
    "facebookmail.com", "meetic.com", "secondlife.com",
    "lindenlab.com", "skype.com", "dyndns.com",
    "microsoft.com", "rueducommerce.com",
    "prepaiddigitalsolutions.com", "welcome.skype.com",
    "cimail1.msn.com", "message.myspace.com", "m.facebook.com",
    "fr.facebox.com", "ourstage.com", "starbreeze.com",
]
# Also block subdomains: "newsletter.", "lists."
```

**B. Keyword blocklist** — never-human patterns:
```python
BLOCKED_KEYWORDS = [
    "no-reply", "noreply", "notification", "service",
    "support", "jobs@", "info@", "newsletter",
]
```

**C. Non-name words** — parts of email local that are not names:
```python
NON_NAME_WORDS = {
    "productions", "production", "project", "projects",
    "info", "contact", "hello", "admin", "webmaster",
    "net", "com", "org", "fr", "de", "uk",
    "the", "la", "le", "of",
}
```

**D. Public email providers** — domains where a name is REQUIRED to keep:
```python
PUBLIC_PROVIDERS = {
    "gmail.com", "hotmail.com", "hotmail.fr", "yahoo.com",
    "yahoo.fr", "live.fr", "outlook.fr", "free.fr",
    "wanadoo.fr", "orange.fr", "laposte.net", "gmx.de", etc.
}
```

**E. Name field validation** — `is_name_field_valid(field, email)`:
- Return False if field is empty, equals the full email, equals the email local part, is a known non-name word (`moi`, `unique`, `service`, `support`, `video`, `second`, `life`), starts with a digit, or matches `[a-zA-Z]+\\d+$` (handle pattern like `Unique3858`).
- Return False if the field contains special characters (`^`, `_`, `°`, `@`) — patterns like `d^_°b Hum` are garbage, not real names.
- Return True otherwise. Do NOT reject lowercase short names like `greg` or `sara` — they are real.

**F. Name extraction from email** — `looks_like_name(local_part)` and `extract_names_from_email(email)`:
- Split the local part on `[._\-+]`.
- Use `strip_numeric_suffix()` to handle `juliebessard.28`.
- Return True if ≥2 alphabetic parts ≥2 chars remain after filtering NON_NAME_WORDS.
- For extraction, capitalize the first and last name-part for the output columns.

**G. Gibberish detection** — `looks_like_gibberish(local)`:
- Return True if >25 chars without separators, OR >10 alpha chars with vowel ratio <15%.

**H. Decision logic** — keep a contact if ANY of:
- Has valid first name OR valid last name (explicit name)
- Email local part looks like a name (firstname.lastname pattern)
- Domain is professional (not in PUBLIC_PROVIDERS)

### Phase 3: Run and Verify
1. Execute the script.
2. Spot-check the output file. Look for false positives (pseudos like `zouzou_la_skunkette` slipping through, band names like `slowdive`).
3. If false positives are found, add specific words to NON_NAME_WORDS or tighten the gibberish check.
4. Re-run until clean. Target: <2% false positives.

### Phase 4: Segmentation (optional)
For B2B prospection, add a scoring function:
- Professional domain: +30 pts
- Company name present: +25 pts
- Job title present: +20 pts
- Email has firstname.lastname structure: +15 pts
- Both first AND last name explicit: +15 pts
- Notes present: +5 pts
- Penalty: first name equals email local part (auto-filled): -10 pts

Segments: A (≥40), B (20-39), C (<20).

Write output with columns: `Score`, `Segment`, `Critères`.

### Phase 5: Hunter.io Enrichment (optional)

When a Hunter.io API key is available, add email verification and professional email discovery:

**1. Verify existing emails (100 free verifications/month on Free plan):**
```python
def verify_email(email):
    data = hunter("email-verifier", {"email": email})
    return {"status": data["data"]["status"], "score": data["data"]["score"]}
```

**2. Find professional emails (25 free searches/month):**
Only triggers when: contact has a known company AND their current email is on a public provider (Gmail, Hotmail, etc.). Requires a domain mapping for known companies.

**3. Rate limiting and timeouts (CRITICAL):**
```python
req = Request(url, headers={"User-Agent": "Hermes/1.0"})
with urlopen(req, timeout=10) as resp:  # ← timeout required
    return json.loads(resp.read())
time.sleep(0.25)  # 4 req/s max
```
- **Always set `timeout=10`** on urlopen — without it, slow API responses cause the script to hang and time out the entire terminal call.
- **Limit batch size**: verify only segments A+B (not all 80+ contacts) to stay under terminal timeout. Segment C contacts rarely justify the API cost.
- **First run will likely time out** with a naive full-batch approach. Reduce `max_verifications` to 50 and retry.

**4. Realistic expectations:**
When 90%+ of contacts are on public domains (Gmail, Hotmail, Yahoo) with no company info, Hunter.io Email Finder has almost nothing to search against (it needs a company domain). Expect **zero professional email discoveries** in this scenario. The verification step (valid/invalid/accept-all) is the primary value.

## B2B Prospection Pipeline (from absorbed `contacts-prospection`)

For the full end-to-end workflow including email outreach, see the `email-campaign` skill. The filtering + enrichment + segmentation phases (1-3) are covered here; phases 4-5 (outreach templates, sending via Gmail API/Brevo) are in `email-campaign`. Key cross-skill references: `email-campaign/references/b2b-workflow-complet.md` and `email-campaign/references/dry-run-gmail.md`.

## Pitfalls

### Implementation bugs that repeatedly occur

**`extract_local` must use `maxsplit=1`, not `maxsplit=0`:**
```python
# WRONG — maxsplit=0 means NO splitting, returns full email including domain
email.split("@", 0)[0]  # → "user@gmail.com"
# CORRECT
email.split("@", 1)[0]  # → "user"
```
When `extract_local` returns the full email, name extraction sees "gmail" and "com" as name parts, producing output like `Francis Com` instead of `Francis Agranier`.

**`is_name_field_valid` must end with `return True`, not `return False`:**
The function is a series of rejection checks. If none fire, the field IS valid and the function must return `True`. A copy-paste error leaving `return False` at the end silently rejects ALL name fields, causing every contact to be dropped for "no identifiable name."

**`write_file` may display truncated API keys in output but the file on disk is correct.** The Hermes secret redactor can truncate API keys in the tool response display. Always verify with `read_file` if the write output looks corrupted — the actual file content is not affected.

### Web scraping for business directories is futile with curl alone
PagesJaunes, Google Maps, Societe.com, and Kompass all return JavaScript-rendered pages — curl sees only empty shells or redirects. Attempting to scrape them without a real browser (Playwright/Puppeteer) will produce zero usable data. For contact collection, use browser tools (full Chromium), official APIs, or manual CSV exports. A subagent asked to "scrape PagesJaunes via curl" will return fabricated data rather than admit the tool can't do the job.

### Concatenation splitting is NOT reliable
Do NOT attempt to split concatenated lowercase names like `romainbuhan` → `Romain Buhan`. Without a name dictionary, the splitter will produce false positives (`spidrman` → `Spid Rman`, `lamauvaisegraine` → `Lama Uvaisegraine`). The cost of false positives outweighs the recovery of a few genuine concatenated-name contacts. Just apply the separator-based extraction (`[._\-+]`) and accept that ~5% of real contacts with concatenated names will be lost — they'll be in the dropped file for manual review.

### Google Contacts CSV format
Google exports use: `E-mail 1 - Value`, `E-mail 2 - Value`, `E-mail 3 - Value` for emails; `First Name`, `Last Name` for names; `Organization Name` for company; `Organization Title` for job title. Many entries are phone-only (no email). Always filter to `get_all_emails(row)` first and ignore phone-only entries.

### Public domain contacts without company info
When 90%+ of contacts are on Gmail/Hotmail with no company info, Hunter.io enrichment has almost nothing to work with (it needs a company domain). Don't overpromise enrichment results.

### Self-emails and institutional domains
- **Exclude your own email addresses** (primary + alternates like `leroyer_thomas@hotmail.fr`) — they appear in Google Contacts and must be filtered out.
- **Institutional domains** (`pole-emploi.fr`, `ina.fr`) often represent mailing-list subscriptions, not real contacts. Block or flag them.

## References
- `references/google-contacts-csv-format.md` — Google Contacts CSV column reference

## Scripts
- `scripts/filter-contacts.py` — Reference filtering script (domain block, keyword block, name extraction, gibberish detection). Adapt INPUT/OUTPUT paths and column mapping per data source.
