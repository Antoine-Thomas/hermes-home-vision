# Site Update Campaign — Friends & Family

Pattern for "I updated my portfolio/site, go check it out" emails to personal contacts.

## When to Use

- You've pushed a significant update to your personal/portfolio site
- You want to share it with friends and family (not B2B/cold outreach)
- You want soft engagement: "dis-moi ce que t'en penses" rather than "buy my services"

## Workflow

### 1. Source Contacts

Export Google Contacts CSV. Filter:
- Remove spam: `facebookmail.com`, `notification@`, `no-reply`, `noreply`
- Remove self: own email addresses
- Categorize by domain: public providers (Gmail, Hotmail, etc.) → amis/famille; professional domains → pro

Save as `campagne_amis.csv` with columns: `email,prenom,nom,categorie`.

### 2. Template

Use `templates/template-site-update.html`. Brand colors:
- Dark background: #1a1a2e (page), #222240 (container)
- Teal header: #0c9f93
- Yellow accents/CTAs: #fdc502

Placeholders:
- `{VERSION}` — site version (e.g. "v7.0.3")
- `{prenom_addresse}` — expands to ` {prenom}` or empty string

Update the highlights section (marked `UPDATE_HIGHLIGHTS` in template) with actual items. Each item: emoji + bold title + description.

### 3. Campaign Script

Use `scripts/campagne_tracking.py` as base. Customize:
- `APP_PASSWORD` — Gmail App Password
- `template_html` — loaded template
- `subject` — email subject line
- `plain` fallback in `send_email()`

Run: `python campagne.py` from the campaign data directory.

### 4. Track Replies

After 2-3 days, run `scripts/verif_reponses.py`. It:
- Connects via IMAP
- Searches recent replies to campaign messages
- Classifies: STOP (opt-out), POSITIF (engagement), NÉGATIF (rejection)
- Updates `tracking.json`

### 5. Respond to Positives

For positive replies, send a follow-up within 24h. Keep it personal — this is NOT a drip sequence.

## Example Campaign (Août 2026)

**Highlights:**
- 📱 Refonte du CSS — cohérence parfaite sur tablette et mobile
- ⚡ Optimisation des performances — Core Web Vitals au vert
- 🔍 Correction de l'indexation — meilleure visibilité sur Google
- 🎨 Fond animé maison — plus de dynamisme sans alourdir

**Subject:** 🔧 Mise à jour de mon portfolio — searching-murphy.com

**Links included:**
- https://www.searching-murphy.com
- https://www.scenario.searching-murphy.com/cv/
- https://searching-murphy.com/#contact

**Results:** 90 contacts, test send validated SMTP, awaiting launch.
