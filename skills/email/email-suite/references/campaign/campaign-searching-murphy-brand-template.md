<!-- Source: email/email-campaign/SKILL.md · section 'Searching Murphy Brand Template' -->

## Searching Murphy Brand Template

For campaigns from searching-murphy.com, use these brand colors:
- **Yellow**: `#fdc502` (accents, CTAs, highlights)
- **Teal**: `#0c9f93` (header bar, secondary accents)
- **Dark background**: `#1a1a2e` (page), `#222240` (container)

**CRITICAL: Always use the HTML template.** The brand template at `templates/searching-murphy-prospection.html` is the primary format. Never send plain-text-only emails for searching-murphy campaigns — always embed the HTML in a `multipart/alternative` with a plain-text fallback. The user expects styled emails matching the Amavada/previous campaign look.

Full template at `templates/searching-murphy-prospection.html`. Reusable campaign script at `scripts/campagne.py`.

For candidature/prospection emails to companies (B2B cold outreach), a variant template exists at `templates/candidature-prospection.html` with a more professional tone while keeping the same brand wrapper.
