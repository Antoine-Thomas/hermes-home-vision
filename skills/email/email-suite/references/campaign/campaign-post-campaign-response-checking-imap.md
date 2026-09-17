<!-- Source: email/email-campaign/SKILL.md · section 'Post-Campaign Response Checking (IMAP)' -->

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
