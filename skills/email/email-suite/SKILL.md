---
name: email-suite
description: "Email suite: HTML campaigns, inbox triage, and terminal email via Himalaya — templates, smtplib delivery, Gmail auth, IMAP, and brand template management."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [email, campaign, html, smtp, gmail, template]
---

# Email Suite

One router for all email work: HTML campaigns, inbox triage, and terminal email via Himalaya CLI. No behavior change.

## When to use this skill

- Send HTML email campaigns / sequences / prospecting -> `references/campaign/*.md` + `scripts/` + `templates/`
- Triage an inbox and draft replies safely -> `references/inbox-triage.md`
- Send/receive/manage email from the terminal -> `references/himalaya/*.md`

## Routing

| Request | Reference |
|---------|-----------|
| HTML campaign, sequences, B2B prospecting, brand template | `references/campaign/*.md` (14 sections) |
| Inbox triage | `references/inbox-triage.md` |
| Terminal email (IMAP/SMTP) | `references/himalaya/*.md` |

## Campaign body sections

- Prerequisites -> `references/campaign/campaign-prerequisites.md`
- Quick Send (one-shot) -> `references/campaign/campaign-quick-send-one-shot.md`
- Image Integration — Remote URLs Preferred -> `references/campaign/campaign-image-integration-remote-urls-preferred.md`
- Email HTML Structure -> `references/campaign/campaign-email-html-structure.md`
- Searching Murphy Brand Template -> `references/campaign/campaign-searching-murphy-brand-template.md`
- Site Update Campaign (Friends & Family — not B2B) -> `references/campaign/campaign-site-update-campaign-friends-family-not-b2b.md`
- CSV-Driven Prospecting Campaign -> `references/campaign/campaign-csv-driven-prospecting-campaign.md`
- Multi-Stage Email Sequences -> `references/campaign/campaign-multi-stage-email-sequences.md`
- Contact Verification Before Sending -> `references/campaign/campaign-contact-verification-before-sending.md`
- Google Contacts Import -> `references/campaign/campaign-google-contacts-import.md`
- Post-Campaign Response Checking (IMAP) -> `references/campaign/campaign-post-campaign-response-checking-imap.md`
- B2B Prospection Outreach (from absorbed `contacts-prospection`) -> `references/campaign/campaign-b2b-prospection-outreach-from-absorbed-contacts-prospection.md`
- Linked Files -> `references/campaign/campaign-linked-files.md`
- Pitfalls -> `references/campaign/campaign-pitfalls.md`

## Himalaya sections

- References -> `references/himalaya/himalaya-references.md`
- Prerequisites -> `references/himalaya/himalaya-prerequisites.md`
- Configuration Setup -> `references/himalaya/himalaya-configuration-setup.md`
- Hermes Integration Notes -> `references/himalaya/himalaya-hermes-integration-notes.md`
- Common Operations -> `references/himalaya/himalaya-common-operations.md`
- Multiple Accounts -> `references/himalaya/himalaya-multiple-accounts.md`
- Attachments -> `references/himalaya/himalaya-attachments.md`
- Output Formats -> `references/himalaya/himalaya-output-formats.md`
- Debugging -> `references/himalaya/himalaya-debugging.md`
- Tips -> `references/himalaya/himalaya-tips.md`

## Notes

- Campaign content split verbatim from the original `email-campaign` SKILL.md into `references/campaign/`.
- Original scripts (`scripts/`), templates (`templates/`), and reference files (`references/`) preserved as-is.
- `email-inbox-triage` and `himalaya` absorbed as references; originals archived to `.archive/email/`.
