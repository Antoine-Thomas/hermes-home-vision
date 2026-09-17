# Re-engaging an already-mailed list — detailed recipes

Companion to the SKILL.md section "Re-engaging a list you already mailed".
That section states the rules; this file holds the working code and the
observed numbers so a future session can reproduce them.

Case: 113 recipients mailed on 12/08, 0 replies. Task on 26/08: relance for the
September re-entry.

## 1. Rebuild the roster from tracking.json, not from the acquisition source

The user supplied the command that originally *acquired* the contacts (a
LinkedIn export parse with its exclusion flag removed). Running it produced
**18** contacts, not 113.

Why: the LinkedIn export only ever contained 13 published addresses (+5 scraped
from message bodies). The 113 had been assembled from several files plus manual
additions. Proof by cross-check:

```python
import json, csv
sent = set(x.lower() for x in json.load(open('tracking.json'))['sent'])
print('sent[] =', len(sent))                      # 113  <- the real roster

for f in ('campagne_amis.csv', 'campagne_pro.csv', 'contacts_artistes.csv'):
    rows = list(csv.DictReader(open(f, encoding='utf-8-sig')))
    em = set((r.get('email') or '').strip().lower() for r in rows if r.get('email'))
    print('%-24s %3d rows, %3d in sent[]' % (f, len(rows), len(em & sent)))
```

Observed:

```
sent[] = 113
campagne_amis.csv        102 rows, 102 in sent[]
campagne_pro.csv           7 rows,   0 in sent[]     <- prepared but never sent
contacts_artistes.csv      4 rows,   4 in sent[]
```

102 + 4 = 106, leaving **7 orphans** present in `sent[]` but in no CSV. Listing
them showed they were organizations added by hand (`14310@aidec.pro`,
`contact@amavada.com`, `lencrage@gmail.com`, `vaticaenproduction@gmail.com`, …).

Note `campagne_pro.csv` existed but none of its 7 addresses were ever sent — a
file's existence is not evidence it was used. Always intersect with `sent[]`.

## 2. Enrichment + categorization

```python
# "ami" ONLY if present in a friends file. Everything else -> entreprise.
# Default-to-friend is the dangerous direction: it sends a tutoye message
# to a business.
categorie = infos.get(email, {}).get('categorie') or 'entreprise'

# Derive a first name from the local part for individuals only.
if categorie != 'ami' and not explicit_prenom:
    prenom = ''                      # avoids "Bonjour Vaticaenproduction,"
if local_part in ('contact','info','infos','rh','admin','direction'):
    prenom = ''                      # generic mailbox: never a first name
```

Result: **106 ami + 7 entreprise = 113**, matching the source files exactly.
A domain-based heuristic had given 110/3 — it misclassified `14310@aidec.pro`
(a `.pro` domain) and three organizations on gmail.

Report coverage so bad data is visible before sending:
`first name known for 105 / 113`.

## 3. Match the register of the previous message

```bash
grep -ocE "\b(tu|te|ton|ta|tes)\b"  template_amis.html   # -> 4
grep -ocE "\b(vous|votre|vos)\b"    template_amis.html   # -> 0
```

The previous mail used *tu* throughout ("je voulais te la partager", "si t'as
30 secondes, va jeter un œil", "réponds simplement STOP"). A relance in formal
register with a security-audit pitch would have read as an automated mailing.

Consequence: three templates, not two — `ami` (informal), `entreprise`
(formal), `particulier` (formal, kept for future real prospects).

Extract the previous body for reading with:

```python
import re, html
h = open('template_amis.html', encoding='utf-8').read()
t = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', h, flags=re.S)
t = re.sub(r'</(p|div|tr|h1|li)>', '\n', t)
t = re.sub(r'<[^>]+>', '', t)
print(re.sub(r'\n\s*\n+', '\n', html.unescape(t)).strip())
```

## 4. Reconcile the final list before sending

```python
from collections import Counter
lines = [l.strip() for l in open('emails_campagne.txt', encoding='utf-8')
         if l.strip() and not l.startswith('#')]
print(len(lines), dict(Counter(l.split(';')[3] for l in lines)))
# 113 {'ami': 106, 'entreprise': 7}
```

If the total or the split disagrees with what the source files imply, the
categorization is wrong — do not send.

## 5. Parking rather than deleting off-target addresses

5 addresses came from inbound LinkedIn messages and belonged to recruiters
(Intuit, Century 21, Jaguar Land Rover, Golden Goose Events). They are valid and
deliverable but wrong for a service pitch.

Move them to a parked file (`linkedin_recruteurs_parkes.json`) rather than
deleting: the user may want them for a job search later, and an unexplained
disappearance looks like a bug. Say in the report why they were parked.

## 6. Guard rails that made the deferred send safe

- sender in dry-run unless `-Confirmer`
- launcher refuses to send before the target date unless the user types `OUI`
  (verified: answering `NON` aborted with 0 emails sent, log showing only
  `SIMULATION` lines)
- SMTP password read from `HERMES_GMAIL_APP_PASSWORD`, never stored
- `tracking.json` written after each send, so a crash cannot duplicate
- 113 previews rendered to `apercus/` and grepped for leftover `{placeholder}`
  tokens and for `Bonjour ,` before anything left

## 7. Duration and quota arithmetic worth stating up front

113 recipients × 120 s interval = **3 h 46**. Starting at 09:00 finishes ~12:45.
A free Gmail account caps around 100-150 sends/day, so 113 is the high end —
tell the user not to send anything else from that address that day, and offer
`-Intervalle 90` (2 h 50) if they want to finish before noon.
