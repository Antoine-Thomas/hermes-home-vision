<!-- Source: email/email-campaign/SKILL.md · section 'CSV-Driven Prospecting Campaign' -->

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
