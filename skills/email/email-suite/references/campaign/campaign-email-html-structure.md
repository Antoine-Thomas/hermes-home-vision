<!-- Source: email/email-campaign/SKILL.md · section 'Email HTML Structure' -->

## Email HTML Structure

Use table-based layouts (not flexbox/grid — email clients have spotty support). Key patterns:

- Outer `<table role="presentation">` wrappers, no semantic tables
- Inline styles only (no `<style>` blocks, no external CSS)
- Max-width 600px for the content container
- Always include a plain-text fallback in a `multipart/alternative`
- Dark backgrounds OK but ensure text contrast
