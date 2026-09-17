<!-- Source: email/email-campaign/SKILL.md · section 'Site Update Campaign (Friends & Family — not B2B)' -->

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
