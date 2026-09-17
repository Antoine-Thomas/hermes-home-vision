---
name: email-campaign
description: "Create and send HTML email campaigns — responsive templates, Python smtplib delivery, Gmail App Password auth, and brand template management."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [email, campaign, html, smtp, gmail, template]
---

# Email Campaign Creation & Sending

Create responsive HTML emails and send them via Python's `smtplib` with Gmail SMTP. This skill covers the programmatic sending path — use when `himalaya` CLI is not installed or when you need fine-grained control over HTML structure.

## Prerequisites

- Python 3 with `smtplib` (stdlib, no extra deps)
- Gmail account with 2FA enabled
- Gmail App Password (generated at https://myaccount.google.com/apppasswords)

## Quick Send (one-shot)

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

sender = 'you@gmail.com'
recipient = 'target@example.com'
app_password = 'xxxx xxxx xxxx xxxx'  # 16-char Gmail App Password

msg = MIMEMultipart('alternative')
msg['From'] = formataddr(('Display Name', sender))
msg['To'] = recipient
msg['Subject'] = 'Subject here'

msg.attach(MIMEText('Plain text fallback', 'plain', 'utf-8'))
msg.attach(MIMEText('<html>...</html>', 'html', 'utf-8'))

with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as server:
    server.starttls()
    server.login(sender, app_password)
    server.sendmail(sender, [recipient], msg.as_string())
```

## Image Integration — Remote URLs Preferred

**Always prefer remote `<img>` tags over CID (Content-ID) attachments.** Reasons:
- Lighter email payload (no base64 bloat)
- Better deliverability (less flagging by spam filters)
- Easier to update images without re-sending
- Consistent rendering across email clients

```html
<!-- Preferred: remote URL -->
<img src="https://example.com/image.webp" alt="Description" style="max-width:100%;height:auto;" />

<!-- Avoid: CID attachment -->
<img src="cid:image-id" ... />
```

Only use CID attachments when the image MUST display offline or when the image is dynamically generated per-recipient.

## Email HTML Structure

Use table-based layouts (not flexbox/grid — email clients have spotty support). Key patterns:

- Outer `<table role="presentation">` wrappers, no semantic tables
- Inline styles only (no `<style>` blocks, no external CSS)
- Max-width 600px for the content container
- Always include a plain-text fallback in a `multipart/alternative`
- Dark backgrounds OK but ensure text contrast

## Searching Murphy Brand Template

For campaigns from searching-murphy.com, use these brand colors:
- **Yellow**: `#fdc502` (accents, CTAs, highlights)
- **Teal**: `#0c9f93` (header bar, secondary accents)
- **Dark background**: `#1a1a2e` (page), `#222240` (container)

**CRITICAL: Always use the HTML template.** The brand template at `templates/searching-murphy-prospection.html` is the primary format. Never send plain-text-only emails for searching-murphy campaigns — always embed the HTML in a `multipart/alternative` with a plain-text fallback. The user expects styled emails matching the Amavada/previous campaign look.

Full template at `templates/searching-murphy-prospection.html`. Reusable campaign script at `scripts/campagne.py`.

For candidature/prospection emails to companies (B2B cold outreach), a variant template exists at `templates/candidature-prospection.html` with a more professional tone while keeping the same brand wrapper.

## Site Update Campaign (Friends & Family — not B2B)

For personal "site update" campaigns targeting friends and family (NOT B2B prospection), use a warmer, simpler approach. Key differences from B2B prospection:

- **Tone**: warm, personal, "je voulais te partager" rather than "je vous propose"
- **Greeting**: `Bonjour{prenom_addresse},` — `{prenom_addresse}` expands to ` {prenom}` when a name is available, or empty string when not (producing `Bonjour,`)
- **CTA**: soft ("va jeter un œil", "dis-moi ce que t'en penses") rather than hard ("audit gratuit")
- **Tracking**: same JSON-based infrastructure as B2B — sent, bounced, no_response, stop, positive, negative categories in `tracking.json`
- **CSV**: `campagne_amis.csv` with columns `email,prenom,nom,categorie`

Reference: `references/campagne-site-update.md` — full workflow.
Template: `templates/template-site-update.html` — brand colors, update highlights, CV link.
Campaign script with integrated tracking: `scripts/campagne_tracking.py`.
Post-campaign IMAP verification: `scripts/verif_reponses.py`.

### Integrated Tracking (Not Just Sending)

The campaign script maintains a `tracking.json` file with these categories, updated after every send:
```json
{"sent": [], "bounced": [], "stop": [], "positive": [], "negative": [], "no_response": []}
```
- `no_response` starts as a copy of `sent` — entries are moved out as replies arrive
- `bounced` entries never get re-sent
- `stop` entries are permanently blacklisted
- The IMAP verification script (`scripts/verif_reponses.py`) reads `tracking.json` and reclassifies entries based on actual replies
- **Incremental re-send**: when you add new contacts later (e.g. from a LinkedIn export or a fresh Google Contacts dump), append them to the CSV and re-run the script — it skips everything already in `sent`, so only the new batch goes out. No need to rebuild the whole list or remember who was already mailed.

### Plain Text Fallback (Mandatory)

Always include a `multipart/alternative` with both `text/plain` and `text/html`. Plain text must summarize all key info: site URL, CV link, version, unsubscribe instruction.

## CSV-Driven Prospecting Campaign

Send personalized batch emails from a CSV contact list with automatic BCC tracking and configurable send intervals.

### CSV Format (`prospects.csv`)

```csv
email,prenom,nom,entreprise
contact@exemple.fr,Jean,Dupont,Agence Web
marie@test.com,Marie,Martin,Studio Digital
```

### Template Personalization

Use `{prenom}` placeholder in the HTML template:

```html
<p style="margin:0 0 15px;">Bonjour {prenom},</p>
```

### Segmented Multi-Template Campaigns

For campaigns targeting different audiences, use a Python dict of segment-specific HTML templates keyed by the CSV `Segment` column. Each segment gets its own CTA while sharing the same brand wrapper (header, signature block, color palette).

```python
TEMPLATES = {
    'agences_web': BASE_STYLE_START + """
        <p>Bonjour l'équipe <strong>{nom_structure}</strong>,</p>
        <p>Je cherche à collaborer avec des agences locales...</p>
    """ + BASE_STYLE_END,
    'coworking': BASE_STYLE_START + """
        <p>Bonjour l'équipe <strong>{nom_structure}</strong>,</p>
        <p>Je propose un atelier gratuit pour vos résidents...</p>
    """ + BASE_STYLE_END,
    # ... more segments
}

# In the send loop:
segment = c['Segment']
template = TEMPLATES.get(segment)
html = template.replace('{nom_structure}', nom)
```

Key pattern: extract the shared wrapper (opening `<div>` with brand colors, signature, CTA button) into `BASE_STYLE_START` / `BASE_STYLE_END` constants, and inject each segment's body between them. This keeps 5+ templates maintainable — one wrapper change propagates everywhere.

### Campaign Script

The reusable campaign script is at `scripts/campagne.py`. Features:
- Reads CSV with `csv.DictReader`
- Replaces `{prenom}` in the HTML template
- BCC to sender for tracking
- Configurable `INTERVAL` between sends (default 120s)
- Progress logging + final summary
- Per-recipient error handling (one failure doesn't block the campaign)

```bash
# Edit CSV then run:
python scripts/campagne.py
```

An alternative template version is at `templates/campaign-script-template.py`.

### Gmail API OAuth2 Sending (Alternative to SMTP)

When OAuth2 is configured (see `google-workspace` skill), use the Gmail API instead of SMTP. **Prefer importing `google_api` directly** rather than shelling out via `subprocess` — the subprocess approach fails in background/detached contexts.

```python
import sys
from pathlib import Path

# Add google-workspace scripts to path and import directly
_gapi_dir = str(Path.home() / "AppData" / "Local" / "hermes" / "skills" / "productivity" / "google-workspace" / "scripts")
if _gapi_dir not in sys.path:
    sys.path.insert(0, _gapi_dir)
import google_api

# Get credentials and build service
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build

creds = google_api.get_credentials()
service = build('gmail', 'v1', credentials=creds)

message = MIMEText(html_body, 'html', 'utf-8')
message['To'] = to_email
message['Subject'] = subject
raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
```

Full working campaign script using this pattern: `references/gmail-oauth2-campaign.py`.

**Pitfall:** On Windows, use absolute paths. The setup.py `--services` flag is not supported — just run `setup.py --auth-url` without arguments.

**Subprocess fallback (only for foreground `terminal()`):**

```python
import subprocess, time
GAPI = r"C:\Users\<user>\AppData\Local\hermes\skills\productivity\google-workspace\scripts\google_api.py"

for i, (email, name) in enumerate(contacts, 1):
    body = f"""<!DOCTYPE html><html>...Bonjour {name}...</html>"""
    cmd = [sys.executable, GAPI, "gmail", "send", "--to", email, "--subject", subject, "--html", "--body", body]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    time.sleep(3)
```

⚠️ The subprocess approach works in `terminal()` but **will fail with `ModuleNotFoundError`** in `execute_code` detached subprocesses or `terminal(background=True)` when the subprocess doesn't inherit the full Python environment.

## Multi-Stage Email Sequences

For B2B prospection, use a 3-email sequence over 2 weeks:
- Email 1 (Day 0): Presentation + value (useful article, no direct sale)
- Email 2 (Day +3): Testimonial / concrete case study
- Email 3 (Day +7): Final follow-up + strong CTA (free audit, meeting)

Adapt tone per segment: Segment A (professional, personalized), Segment B (warm, local), Segment C (content only, 1 email). For B2B strategy format: `references/strategie-b2b-format.md`.

## Contact Verification Before Sending

Before sending a campaign, verify that contact data (websites, emails, locations) is real — not fabricated. See `references/contact-verification.md` for curl-based bulk HTTP checks, location verification via postal codes, email extraction from sites, and Python parallel verification script.

### Audit the recipient list BEFORE writing any copy

A campaign is worth exactly what its list is worth. Twice now the real blocker was the list, not the message — and both times it was discovered only after drafting polished templates. **Run the audit first, report the numbers, then write.**

Six checks, in order — full recipes in `references/audit-liste-avant-envoi.md`:

1. **Undeliverable reserved domains** (RFC 2606): `example.com`, `.test`, `.invalid`, `.localhost`. Their presence almost always means the folder holds *test fixtures*, not real contacts. Filter them, but keep them as commented lines in the output `.txt` with their source file so the user sees the traceability.
2. **Cross-check prior campaigns' `tracking.json`** (`sent` + `bounced` + `stop`) before calling a list "new". Re-mailing the same people is the user's decision, never a side effect.
3. **Regex concatenation artifacts**: `[a-zA-Z0-9._%+-]+@...` on prose glues the preceding word to the local part (`...entrepreneursdaniel_antoni@intuit.com`). Detect with the same-domain suffix heuristic in the reference.
4. **Intent of the address, not just validity**: addresses harvested from *inbound* messages are usually recruiters (`recruitment@`, `rh@`) who wrote to offer a job. Sending them a service pitch is off-target.
5. **Legal basis per segment** (see below).
6. **LinkedIn export ceiling** (~1.4%, see below).

Report before drafting:

```
Retenus ............ N   (dont X particuliers, Y entreprises)
Ecartes : non delivrable n1 | deja contactes n2 | artefact n3 | hors cible n4
```

If `Retenus` is zero or negligible, say so immediately and offer replacement sources instead of producing drafts nobody can send.

### Legal basis differs by segment (France / CNIL)

This decides **which segment is mailable at all**:

- **Professional address**, message related to the organisation's activity → prospecting tolerated without prior consent, provided a visible opt-out. B2B segment is mailable.
- **Individual (particulier)** → prior consent required.

The trap: someone who sent a **CV** gave their address for a **job application**. Reusing it to sell a service is a change of purpose the CNIL does not allow. **CVs are a legitimate source for recruiting, not for commercial prospecting to individuals.** Say this even when the user has already asserted they respect anti-spam rules — their rule is usually right but does not separate these two cases.

### LinkedIn emails: use the data export, never the browser

`Connections.csv` only carries a connection's email if that person enabled sharing. Observed yield: **13 addresses out of 937 connections (1.4%)** — stated in the CSV's own preamble.

Do **not** try to make up the difference by driving a browser on LinkedIn: contact info requires being logged in (so it would need the user's credentials — never do that), automating a logged-in session breaches the ToS and risks restricting the user's account, and it would yield nothing extra since the only reachable addresses are already in the export. The export **is** the complete answer — say that plainly instead of attempting and failing.

### Deferred / scheduled campaigns

When the user wants a campaign prepared now but sent later (e.g. after the summer break, first working day of September):

- Ship the sender in **dry-run by default**; require an explicit `--confirmer` / `-Confirmer` flag to actually send.
- Put a **date guard** in the launcher: refuse to send before the target date unless the user types a literal confirmation. Cheap, and it prevents the whole campaign leaving during holidays by accident.
- Read the SMTP password from an environment variable (`HERMES_GMAIL_APP_PASSWORD`), never from a file in the campaign folder.
- Write `tracking.json` after **each** send so a crash mid-run cannot produce duplicates on restart.
- Best send window observed for B2B French audiences: **Tuesday or Wednesday, 9:00–10:30**. Avoid Monday (inbox backlog) and Friday.
- Do not create the cron until the user has reviewed the drafts. Prefer a **reminder** job over an automatic-send job: nobody proofreads an automatic send.

### Re-engaging a list you already mailed

When the user says "relance the N contacts from the last campaign", two traps fire in sequence. Full recipes: `references/relance-liste-existante.md`.

**Trap 1 — the roster lives in `tracking.json`, not in the acquisition source.**
The user will often hand you the command that *originally built* the list (a LinkedIn export parse, a SIRENE crawl). Re-running it does **not** reproduce the audience: observed 18 contacts instead of 113, because the original campaign was assembled from several CSVs plus manual additions. `tracking.json['sent']` is the authoritative roster of who actually received the previous message. Rebuild from it, then enrich names/companies by joining against every CSV/JSON in the previous campaign folder. Announce the count before going further — if it does not match what the user expects, stop and say so.

**Trap 2 — do not accept a blanket segment label.**
The user asked to categorise all 113 as `entreprise`. Verification showed **106 came from `campagne_amis.csv` (`categorie = amis`) and `contacts_artistes.csv` (`type = artiste_ami`)** — friends, not businesses. Sending them the B2B pitch (security audit, ROI, vouvoiement) would have been a visible mistake.

The segment CSVs are the **only** authority for category. Never infer it from the email domain, and never apply a blanket label:

```python
# "ami" only if present in a friends file; everything else defaults to entreprise.
# An address in sent[] but absent from the friends CSVs is an organisation that
# was added by hand — defaulting it to "ami" would send it a tutoye message.
categorie = infos.get(email, {}).get("categorie") or "entreprise"
```

**Match the register of the message they last received.** Grep the previous template before writing a word:

```bash
grep -ocE "\b(tu|te|ton|ta|tes)\b"   template_amis.html    # -> 4
grep -ocE "\b(vous|votre|vos)\b"     template_amis.html    # -> 0
```

Tutoiement three weeks ago followed by commercial vouvoiement today reads as an automated mailing and burns the relationship. If the previous message tutoyait, the relance must too — that is a third template, not a reuse of the B2B one.

**Segment-conditional prénom derivation.** The generic rule (derive from the email local part when the CSV prénom is missing) must be **disabled for organisations**: `Bonjour Vaticaenproduction,` and `Bonjour Cdar,` are worse than `Bonjour,`. Derive for `ami` / `particulier` only; for an organisation use an explicitly-provided prénom or nothing.

**For a friends segment, the realistic CTA is a referral, not a sale.** A friend does not buy a security audit, but they know someone whose site is broken. Put the referral ask in the body — not as a postscript — and keep the meeting offer as the secondary CTA. The previous friends campaign got 0 replies out of 113 partly because it had no measurable CTA at all.

## Google Contacts Import

Export from Google Contacts can be converted to the campaign CSV format. Two reference guides:
- `references/google-contacts-import.md` — Direct conversion script
- `references/google-contacts-convert.md` — Alternative conversion approach

Format mapping: `First Name` -> prenom, `Last Name` -> nom, `E-mail 1 - Value` -> email, `Organization Name` -> entreprise.

### Cleaning Google Contacts Exports

Google Contacts exports frequently have garbage in the `First Name` field:
- **Email-as-name**: the email address repeated in the first name column (`emilie@tohubohu.fr` as prenom)
- **Gibberish local parts**: `Flo00761`, `Spidrman`, `Zouzou` — extracted from email but not real names
- **Empty first names**: contacts with email only, no name

**Strategy**: when prenom is empty or contains `@`, extract from the email local part (before `@`), then split on `.` `_` `-` and capitalize. Maintain a garbage-set of known unreadable prenoms and fall back to omitting the name entirely ("Bonjour," instead of "Bonjour Spidrman,").

### Finding Missing Contact Emails via Gmail Search

When People API is unavailable (403 disabled), use Gmail search to find contact email addresses in sent mail and inbox. See `references/gmail-contact-lookup.md`.

### Personal vs Professional Campaigns (Dual-Campaign Pattern)

For searching-murphy.com, campaigns use TWO distinct templates keyed by CSV `categorie` column:

| Campaign | CSV filter | Template tone | Greeting | CTA focus |
|----------|-----------|---------------|----------|-----------|
| **Professional** | `categorie != 'createur'` | Formal, value-proposition | `Bonjour l'équipe {structure}` | Collaboration, B2B services |
| **Personal** | `categorie == 'createur'` | Warm, friendly, personal | `Bonjour {prenom}` | Site discovery, services for friends |

Each campaign excludes the other's contacts + blacklist (La Bananerie STOP replies, own email addresses). Run them as separate scripts with separate log files.

### Test Safety Rule

**Never use real external addresses in a test CSV.** Always route test sends to your own address with fake names to validate the pipeline before launching to real prospects.

### Launching Long Campaigns

For campaigns lasting more than a few minutes, there are TWO timeouts to be aware of:

1. **`execute_code` 300s timeout** — the sandbox kills any script after 5 minutes. A campaign of 63 contacts × 3s delay = ~189s succeeds, but 113 contacts × 120s = ~3h48 will time out with no output saved. Use `terminal(background=True)` instead.
2. **`terminal()` background mode** — stdout is not captured in background mode on Windows, but file I/O works reliably.

### Recommended: Write Script to File, Launch via terminal(background=True)

**Step 1:** Write the full campaign script to a `.py` file (not inline `python -c "..."` — escaping passwords with spaces/special chars in inline scripts is fragile):

```python
# In execute_code or write_file, write the complete script including:
# - CSV reading
# - HTML template generation
# - smtplib sending loop
# - Progress logging to a file (flush after each send)
```

**Step 2:** Launch as background terminal process:

```python
terminal(
    command='python "C:/path/to/campagne.py" 2>&1',
    background=True,
    notify_on_complete=True,
    timeout=600
)
```

**Step 3:** Monitor progress by reading the log file with `read_file()`.

### Why Write to a .py File (Not Inline python -c)

Inline `python -c "..."` in terminal fails when:
- The password contains spaces (`wvvi ulwd ynkz avyt`) — shell escaping corrupts it
- The script has nested f-strings or triple-quotes — escaping becomes unmanageable

Always `write_file("campagne.py", ...)` first, then `terminal("python campagne.py", background=True)`.

### Gmail SMTP App Password Reliability

The Gmail SMTP App Password is more reliable than OAuth for automated campaigns:
- **OAuth tokens expire after ~7 days** in Google testing mode — requires interactive re-auth
- **App Passwords never expire** — once generated, they work indefinitely
- **SMTP + App Password** (smtp.gmail.com:587) handled 63/63 emails with 0 failures in one session

Prefer SMTP App Password for automated/programmatic sending. Reserve OAuth for interactive use cases (reading inbox, calendar, etc.).

**Do NOT use `subprocess.Popen` with `DETACHED_PROCESS` from `execute_code`** — the detached subprocess has a restricted Python environment and often can't find pip-installed packages, causing `ModuleNotFoundError`.

## Post-Campaign Response Checking (IMAP)

After a campaign, check for replies — especially STOP/opt-out requests that must be blacklisted immediately.

### IMAP + App Password (Recommended — No Token Expiry)

When OAuth2 tokens are expired, use `imaplib` with the Gmail App Password. This is **more reliable** for automated checks since App Passwords never expire.

```python
import imaplib, email
from email.header import decode_header
from datetime import datetime, timedelta

mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login('you@gmail.com', 'app_password_16_chars')
mail.select('INBOX')

since = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
status, data = mail.search(None, f'(SINCE "{since}")')

for msg_id in data[0].split()[-200:]:
    status, data = mail.fetch(msg_id, '(RFC822)')
    msg = email.message_from_bytes(data[0][1])
    subject = str(decode_header(msg['Subject'] or '')[0][0]) if msg['Subject'] else ''
    from_addr = str(decode_header(msg['From'] or '')[0][0]) if msg['From'] else ''

    # Extract body (handle multipart)
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                break
    else:
        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
```

### STOP Detection — Filter Out Newsletters First

A naive STOP keyword match catches every newsletter with "stop" in marketing copy. Isolate REAL opt-outs with a two-phase filter:

**Phase 1 — Is this actually a reply to the campaign?**
```python
is_campaign_reply = (
    'candidature' in subject.lower() or
    'prospection' in subject.lower() or
    ('re:' in subject.lower() and 'searching murphy' in body.lower()[:500])
)
```

**Phase 2 — If it's a campaign reply, check for opt-out signals:**
```python
STOP_KEYWORDS = [
    'ne plus être contacté', 'ne plus me contacter', 'ne pas me contacter',
    'pas intéressé', 'pas interesse', 'supprimer mon', 'retirez-moi',
    'ne me contactez plus', 'arrêtez', 'désabonner', 'desabonner'
]
is_stop = any(kw in body.lower()[:500] for kw in STOP_KEYWORDS)
```

**False positive example:** "STOP: NVIDIA <news@nvidia.com>" — matches "stop" in subject but is NOT a campaign reply. Phase 1 eliminates it.

**Classify other replies:**
- `"congés"`, `"vacances"`, `"absence"` → 🏖️ Auto-reply, retry later
- `"trompé"`, `"pas la bonne"`, `"erreur sur"` → 🔄 Wrong person, fix in database
- `"intéressé"`, `"RDV"`, `"appelez-moi"` → ✅ Positive, follow up

### IMAP Date Format on Windows

Python's `strftime` with `%b` uses the system locale. On French Windows, `%d-%b-%Y` produces French abbreviations (`juil.` instead of `Jul`). Gmail IMAP `SINCE` expects English abbreviations. If the search returns 0 results unexpectedly, hardcode the English date:
```python
MONTHS = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',
          7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
d = datetime.now() - timedelta(days=2)
since = f"{d.day}-{MONTHS[d.month]}-{d.year}"
```

### Updating the Prospect Database

After identifying STOPs, update the JSON/Excel to mark affected companies:
```python
for e in entreprises:
    if e.get('email') and any(stop_email in e['email'].lower() for stop_email in stop_list):
        e['stop'] = True
        e['note'] = 'A DEMANDÉ À NE PLUS ÊTRE CONTACTÉ'
```

### Gmail API Alternative

When OAuth2 tokens ARE valid, use the Gmail API approach in `references/post-campaign-verification.md` (bounces, spam checking, auto-reply classification).

## B2B Prospection Outreach (from absorbed `contacts-prospection`)

For multi-stage B2B sequences and segment-specific outreach:
- `references/b2b-workflow-complet.md` — Complete B2B prospection workflow (filter → enrich → segment → outreach)
- `references/dry-run-gmail.md` — Gmail sending dry-run protocol
- `references/diagnostic-landing-page.md` — Landing page diagnostic for prospection

## Linked Files

- `references/google-contacts-import.md` — Google Contacts export to prospects.csv
- `references/google-contacts-convert.md` — Alternative Google Contacts conversion
- `references/gmail-contact-lookup.md` — Gmail search fallback for finding contact emails when People API unavailable
- `references/linkedin-export-parsing.md` — Parse LinkedIn "Basic_LinkedInDataExport" ZIP (Connections.csv 3-line preamble gotcha, messages.csv email extraction, ~1-2% email yield)
- `references/contact-verification.md` — Bulk contact verification (HTTP checks, email extraction)
- `references/audit-liste-avant-envoi.md` — Recipient-list audit to run BEFORE writing copy: RFC 2606 undeliverable domains, cross-check against prior `tracking.json`, regex concatenation artifacts, address intent, CNIL basis per segment, LinkedIn 1.4% ceiling
- `references/sirene-crawl-entreprises.md` — SIRENE API crawl to build B2B prospect lists (NAF codes, DNS MX, website scraping, email enrichment)
- `references/strategie-b2b-format.md` — B2B strategy generation format (biopic, SWOT, roadmap)
- `references/b2b-workflow-complet.md` — B2B prospection end-to-end workflow
- `references/dry-run-gmail.md` — Gmail dry-run before campaign sends
- `references/diagnostic-landing-page.md` — Landing page audit for prospect targeting
- `references/post-campaign-verification.md` — After-campaign audit: check spam for bounces/auto-replies, classify hard vs soft failures, identify real human replies needing follow-up
- `references/imap-post-campaign.md` — IMAP-based (App Password) response checking — no OAuth expiry, two-phase STOP detection, summer/holiday awareness
- `references/gmail-imap-folder-utf7.md` — Gmail IMAP folder names are modified UTF-7 (`&AOk-`=é); `imaplib.utf7_decode` is missing in Python 3.11 (custom decoder + base64 padding); custom "sent" folders vs `Sent`; "which account actually sent" triage via reply quoted headers
- `references/oauth-token-refresh.md` — Gmail OAuth2 token expiry: re-auth flow with setup.py
- `references/gmail-oauth2-campaign.py` — Working Gmail API OAuth2 campaign script (direct import pattern, avoids subprocess ModuleNotFoundError)
- `scripts/campagne.py` — Full campaign script with personalization, BCC, intervals
- `scripts/campagne_tracking.py` — Campaign script with integrated JSON tracking (sent/bounced/stop/positive/negative/no_response)
- `scripts/verif_reponses.py` — Post-campaign IMAP reply checker with STOP/positive/negative classification
- `templates/campaign-script-template.py` — Alternative campaign script template
- `templates/searching-murphy-prospection.html` — Brand HTML template (dark theme, teal header, yellow CTA)
- `templates/candidature-prospection.html` — Candidature/prospection variant of the brand template
- `templates/template-site-update.html` — Site update template for friends/family (version badge, highlights, soft CTA)
- `references/campagne-site-update.md` — Site update campaign pattern (friends/family, not B2B)

## Pitfalls

- **Image attachments via CID**: Prefer remote `<img>` URLs over CID. CID-based images bloat the email and increase spam risk. Always host images on the WordPress site.
- **Garbage prenoms in Google Contacts exports**: Google Contacts frequently exports emails or gibberish (`Flo00761`, `Spidrman`, `emilie@tohubohu.fr`) in the First Name field. Always validate prenoms: if they contain `@`, digits, or look like random strings, extract from the email local part or omit the name entirely. Template sending "Bonjour Flo00761" looks unprofessional — fall back to "Bonjour," when no real name is available.
- **Background terminal on Windows**: Python stdout is NOT captured in background mode — not even with `PYTHONUNBUFFERED=1`, `sys.stdout.flush()`, or `print(flush=True)`. Use `terminal(background=True, notify_on_complete=True)` and have the campaign script write progress to a log file (`open(..., buffering=1)`). Monitor via `tail -f log.txt`. Do NOT use `subprocess.Popen` with `DETACHED_PROCESS` from `execute_code` — the detached subprocess loses access to pip-installed packages and fails with `ModuleNotFoundError`.
- **`subprocess` calling `google_api.py` breaks in subprocesses**: When using Gmail API OAuth2, import `google_api` directly in the campaign script and call its functions, rather than shelling out via `subprocess.run`. The subprocess approach may work in `terminal()` but fails silently in background or detached contexts where module resolution differs. See `references/gmail-oauth2-campaign.py` for a working direct-import pattern.
- **Gmail rate limits**: ~100-150 emails/day for free accounts, ~2000/day for Workspace. Keep 2 min minimum interval.
- **Gmail SMTP drops a long-lived connection (~1 h of continuous sending)**: a campaign script that keeps ONE `smtplib` connection open for the whole run hits `please run connect() first` after ~100 emails (~1 h at 35 s/mail) — Gmail silently closes the session. Fix: re-`login()` / reopen the connection every ~25 emails, and catch that error to reconnect+retry. A send that "completes" with fewer sends than the target usually means the connection dropped midway — check the per-recipient log, not the exit code (a dropped connection can still `exit 0`). Re-run the remainder by diffing target vs the OK log.
- **IMAP "Invalid credentials" right at the start of a mass SMTP send is transient**: Gmail's security can briefly block IMAP login for a few minutes when a large SMTP send begins (observed 18:05–18:09, self-resolved; SMTP kept working throughout). Don't rotate the App Password on this signal — re-test IMAP after ~5 min before concluding the credentials are bad.
- **Hermes gateway email adapter keeps throwing `email_imap_fetch_failed` ("The read operation timed out")**: check `EMAIL_POLL_INTERVAL` in `.env`. The adapter defaults to **15 s**, and polling Gmail IMAP every 15 s triggers Gmail throttling → the socket read times out (a recurring lvl10 crash, ~once/day, not every poll). Fix: set `EMAIL_POLL_INTERVAL=300` (5 min) in `.env`. The adapter's read timeout is already 90 s (patched in `plugins/platforms/email/adapter.py`); the real root cause is the poll frequency, not the timeout. Takes effect on the next gateway restart. Verify reachability first (`imap.gmail.com:993` TCP-connectable + SMTP auth passing means it's throttling, not a network/auth outage).
- **Gmail OAuth2 token expires after ~7 days**: Google OAuth tokens in testing mode expire. When `RefreshError: invalid_grant: Token has been expired or revoked` appears, run `python setup.py --auth-url` from the google-workspace skill scripts directory. Have the user open the URL in a browser, sign in with the Gmail account, and paste back the redirect URL (containing `?code=...`). Then run `python setup.py --finish "<redirect_url>"` to regenerate `google_token.json`. See `references/oauth-token-refresh.md`.
- **Secret redactor**: The app password appears masked (`***`) in write_file logs but the actual file content is correct. Verify with `read_file` if unsure.
- **Empty first names**: Template sends "Bonjour ," if the prenom field is empty. Clean CSV before sending.
- **Playwright CLI blocked by Windows App Control**: Use `chrome-headless-shell.exe` directly via the `executable_path` parameter in `p.chromium.launch()`. The shell binary is at `%LOCALAPPDATA%/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe`.
- **`hermes gateway setup` is interactive**: When running non-interactively, pipe answers via stdin: `printf 'n\n23\ny\ny\ny\ny\n' | hermes gateway setup`.
- **`execute_code` sandbox may lack `playwright` or `googleapiclient`**: The sandbox environment does not include pip-installed packages like `playwright`, `google-api-python-client` (`googleapiclient`), or `google-auth`. When a script needs these, write it to a `.py` file and run via `terminal()` — the terminal inherits the system Python environment where these packages are installed. Do NOT write inline scripts in `execute_code` that import from `googleapiclient` or `playwright`.
- **`process(action='wait')` timeout is clamped to 60s**: When monitoring a background campaign via `process wait`, the timeout parameter is silently clamped to 60 seconds regardless of what you pass. For campaigns longer than 60s, don't rely on `process wait` — instead poll the log file directly with `read_file()` or `execute_code` to check progress. The `notify_on_complete=True` flag on `terminal(background=True)` will still fire correctly when the process exits, so you'll get notified eventually — just can't block-wait for it.
- **Email "configured" without `.env`**: The gateway may detect email config from other sources (config.yaml). Don't rely on `.env` presence alone to determine setup state.
- **Never send plain-text-only for Searching Murphy**: The user expects styled HTML emails (dark theme, teal header, yellow CTA). Always use `templates/searching-murphy-prospection.html` or `templates/candidature-prospection.html` as the primary format, wrapped in `multipart/alternative` with a plain-text fallback. Sending text-only will result in the user asking you to re-send with the proper template.
- **DuckDuckGo search returns garbage for French local searches**: Results are completely off-topic (returns US real estate for "agence web Caen"). Do not use for finding French SMBs. Use SIRENE API + DNS MX + website scraping instead (see `references/sirene-crawl-entreprises.md`).
- **Python urllib from execute_code sandbox returns HTTP 400 for French gov APIs**: The SIRENE API rejects requests from the sandbox. Use `curl` in `terminal()` instead — it works reliably.
- **SIRENE crawl to email enrichment**: For building B2B prospect lists from scratch, use the 5-phase workflow in `references/sirene-crawl-entreprises.md`: (1) crawl SIRENE by postal code + NAF, (2) DNS MX check on generated domains, (3) scrape websites for real emails, (4) optional Hunter.io verification, (5) consolidate with confidence scores.
- **Never build the templates before auditing the list**: polished dual-template drafts were produced twice for lists that turned out to be unusable (test-fixture `@example.com` addresses; 13/13 contacts already mailed three weeks earlier). Run `references/audit-liste-avant-envoi.md` first and report the counts. Writing copy for an empty list is wasted work and hides the real blocker from the user.
- **A user-supplied contact folder may be your own test fixtures**: before treating a folder as real contacts, check whether a previous session generated it (e.g. a `make_samples.py` next to it, or all addresses on one reserved domain). Extraction succeeding is not evidence the data is real.
- **NEVER save files to the user's Desktop**: The user hates clutter. Always save work products to `~/AppData/Local/hermes/data/<project>/` or to the skill's own directory. Scripts, CSVs, JSON intermediates, and generated emails all go under `hermes/data/`, not the Desktop. The Desktop is for the user's own files only.
