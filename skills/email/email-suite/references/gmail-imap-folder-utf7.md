# Gmail IMAP — folder names, UTF-7, and finding the "sent" list

## Modified UTF-7 folder names (Gmail IMAP)

Gmail exposes IMAP folder names in **modified UTF-7**, not UTF-8. Accented
characters become `&...-` sequences: `&AOk-` = é, `&AO0-` = à, etc.

- French sent folder `[Gmail]/Messages envoyés` → on the wire
  `"[Gmail]/Messages envoy&AOk-s"`.
- A custom folder `candidatures réponses/candidatures envoyées` appears as
  `candidatures r&AOk-ponses/candidatures envoy&AOk-es`.

## Python gotchas (verified Python 3.11.16)

- **`imaplib.utf7_decode` does NOT exist** in Python 3.11 — it's a module-level
  function only in newer Python. Implement a tiny decoder. Base64 part must be
  re-padded to a multiple of 4 or `b64decode` fails/decodes wrong:

```python
import base64

def utf7_decode(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "&":
            j = s.find("-", i)
            if j == -1:
                out.append(c); i += 1
            elif j == i + 1:
                out.append("&"); i = j + 1
            else:
                b64 = s[i+1:j] + "=" * ((4 - (j - i - 1) % 4) % 4)  # pad!
                out.append(base64.b64decode(b64).decode("utf-16-be"))
                i = j + 1
        else:
            out.append(c); i += 1
    return "".join(out)
```

- Extract the folder name from `imap.list()` as the **last quoted string**:
  `re.search(r'"([^"]*)"\s*$', raw.decode("utf-8", "replace")).group(1)`, then
  `utf7_decode(...)` for display.
- `imap.select()` takes the **RAW (still-UTF-7) name**, NOT the decoded one.
- A bad parse surfaces as `SELECT ... BAD [b'Could not parse command']` — Gmail
  rejects the malformed name. Re-check your regex/extraction; do NOT chase the
  IMAP command syntax, the name is the problem.

## Standard "Sent" vs custom folders

- The standard sent folder is listed BOTH as `"Sent"` and `"[Gmail]/Messages
  envoy&AOk-s"` (both carry the `\Sent` attribute).
- A `SUBJECT "Candidature"` (or `SINCE <date>`) search in the standard `Sent`
  folder may return **0 even when the campaign was sent from this account** —
  because users often MOVE sent campaign mail into custom folders.
- `imap.list()` and grep the decoded folder names for the campaign keyword
  first. Sent copies frequently live in a custom `.../envoyées` sub-folder, not
  in `Sent`.

## "Which account actually sent the campaign?" triage

When the sent list is missing from the account you have credentials for, read a
REPLY's quoted headers: the original message's `From:` line reveals the sending
account. Real example — replies sat in `searching.murphy@gmail.com`'s INBOX, but
their quoted text showed `From: Thomas Leroyer <thomas@searching-murphy.com>`:
the campaign was sent from the custom-domain account, so THIS Gmail `Sent` is
empty and the "N sent" roster is unrecoverable from Gmail.

Then: ask the user which account/tool sent it, or fall back to the acquisition
list (e.g. a SIRENE crawl JSON) minus the replies already seen. Do NOT fabricate
a "who was contacted" list.
