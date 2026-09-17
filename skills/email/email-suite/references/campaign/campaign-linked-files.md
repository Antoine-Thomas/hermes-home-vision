<!-- Source: email/email-campaign/SKILL.md · section 'Linked Files' -->

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
