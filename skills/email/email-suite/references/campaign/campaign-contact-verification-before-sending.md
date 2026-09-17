<!-- Source: email/email-campaign/SKILL.md · section 'Contact Verification Before Sending' -->

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
