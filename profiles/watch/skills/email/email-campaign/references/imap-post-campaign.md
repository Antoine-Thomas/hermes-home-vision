# IMAP Post-Campaign Response Checking

Alternative to Gmail API OAuth2 for checking campaign replies. Uses `imaplib` with App Password — no token expiry, always works.

## Quick Start

```python
import imaplib, email, json
from email.header import decode_header
from datetime import datetime, timedelta

GMAIL = "you@gmail.com"
PASS = "your_app_password"

mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login(GMAIL, PASS)
mail.select('INBOX')

# Date format must use English month abbreviations for Gmail IMAP SINCE
MONTHS = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',
          7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
d = datetime.now() - timedelta(days=2)
since = f"{d.day}-{MONTHS[d.month]}-{d.year}"

status, data = mail.search(None, f'(SINCE "{since}")')
msg_ids = data[0].split()
```

## Two-Phase STOP Detection

### Phase 1: Is this a campaign reply?

```python
def is_campaign_reply(subject, body):
    subj_lower = subject.lower()
    body_lower = body[:500].lower()
    return (
        'candidature' in subj_lower or
        'prospection' in subj_lower or
        ('re:' in subj_lower and 'searching murphy' in body_lower)
    )
```

### Phase 2: Is this an opt-out?

```python
STOP_KEYWORDS = [
    'ne plus être contacté', 'ne plus me contacter', 'ne pas me contacter',
    'pas intéressé', 'pas interesse', 'supprimer mon', 'retirez-moi',
    'ne me contactez plus', 'arrêtez', 'désabonner', 'desabonner',
    'do not contact', 'unsubscribe', 'remove me'
]

ABSENCE_KEYWORDS = ['congés', 'conges', 'vacances', 'absence', 'automatique']
WRONG_KEYWORDS = ['trompé', 'trompe', 'pas la bonne', 'erreur sur']
POSITIVE_KEYWORDS = ['intéressé', 'interesse', 'rdv', 'rendez-vous', 'appelez-moi']

body_low = body[:500].lower()

if any(kw in body_low for kw in STOP_KEYWORDS):
    return 'STOP'
elif any(kw in body_low for kw in ABSENCE_KEYWORDS):
    return 'ABSENCE'
elif any(kw in body_low for kw in WRONG_KEYWORDS):
    return 'WRONG_PERSON'
elif any(kw in body_low for kw in POSITIVE_KEYWORDS):
    return 'POSITIVE'
else:
    return 'OTHER'
```

## Common Pitfall: False Positives

Without Phase 1 filtering, every newsletter with "stop" in marketing copy gets flagged:
- `"STOP: NVIDIA <news@nvidia.com>"` — newsletter, not a reply
- `"Dernier appel : jusqu'à -30 %"` — no "stop" keyword, but irrelevant
- `"Pagup <support@mail.better-robots.com>"` — blog spam, not a reply

Always filter by campaign relevance FIRST.

## Updating the Database

```python
# After identifying STOPs
stop_emails = [s['from'].lower() for s in stop_list]
for e in entreprises:
    email_e = e.get('email', '').lower()
    for se in stop_emails:
        if se in email_e or email_e in se:
            e['stop'] = True
            e['note'] = 'A DEMANDÉ À NE PLUS ÊTRE CONTACTÉ'
```

## Summer/Holiday Awareness

In July-August, most French businesses are closed. Auto-replies like "En congés jusqu'au 17 août" are common. Schedule a follow-up check for September rather than re-sending immediately.
