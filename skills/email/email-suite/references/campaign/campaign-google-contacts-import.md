<!-- Source: email/email-campaign/SKILL.md · section 'Google Contacts Import' -->

## Google Contacts Import

Export from Google Contacts can be converted to the campaign CSV format. Two reference guides:
- `references/google-contacts-import.md` — Direct conversion script
- `references/google-contacts-convert.md` — Alternative conversion approach

Format mapping: `First Name` -> prenom, `Last Name` -> nom, `E-mail 1 - Value` -> email, `Organization Name` -> entreprise.

### Cleaning Google Contacts Exports

Google Contacts exports frequently have garbage in the `First Name` field:
- **Email-as-name**: the email address repeated in the first name column (`emilie@tohubohu.fr` as prenom)
- **Gibberish local parts**: `Flo00761`, `Spidrman`, `Zouzou` — extracted from email but not real names
- **Empty first names**: contacts with email only, no name

**Strategy**: when prenom is empty or contains `@`, extract from the email local part (before `@`), then split on `.` `_` `-` and capitalize. Maintain a garbage-set of known unreadable prenoms and fall back to omitting the name entirely ("Bonjour," instead of "Bonjour Spidrman,").

### Finding Missing Contact Emails via Gmail Search

When People API is unavailable (403 disabled), use Gmail search to find contact email addresses in sent mail and inbox. See `references/gmail-contact-lookup.md`.

### Personal vs Professional Campaigns (Dual-Campaign Pattern)

For searching-murphy.com, campaigns use TWO distinct templates keyed by CSV `categorie` column:

| Campaign | CSV filter | Template tone | Greeting | CTA focus |
|----------|-----------|---------------|----------|-----------|
| **Professional** | `categorie != 'createur'` | Formal, value-proposition | `Bonjour l'équipe {structure}` | Collaboration, B2B services |
| **Personal** | `categorie == 'createur'` | Warm, friendly, personal | `Bonjour {prenom}` | Site discovery, services for friends |

Each campaign excludes the other's contacts + blacklist (La Bananerie STOP replies, own email addresses). Run them as separate scripts with separate log files.

### Test Safety Rule

**Never use real external addresses in a test CSV.** Always route test sends to your own address with fake names to validate the pipeline before launching to real prospects.

### Launching Long Campaigns

For campaigns lasting more than a few minutes, there are TWO timeouts to be aware of:

1. **`execute_code` 300s timeout** — the sandbox kills any script after 5 minutes. A campaign of 63 contacts × 3s delay = ~189s succeeds, but 113 contacts × 120s = ~3h48 will time out with no output saved. Use `terminal(background=True)` instead.
2. **`terminal()` background mode** — stdout is not captured in background mode on Windows, but file I/O works reliably.

### Recommended: Write Script to File, Launch via terminal(background=True)

**Step 1:** Write the full campaign script to a `.py` file (not inline `python -c "..."` — escaping passwords with spaces/special chars in inline scripts is fragile):

```python
# In execute_code or write_file, write the complete script including:
# - CSV reading
# - HTML template generation
# - smtplib sending loop
# - Progress logging to a file (flush after each send)
```

**Step 2:** Launch as background terminal process:

```python
terminal(
    command='python "C:/path/to/campagne.py" 2>&1',
    background=True,
    notify_on_complete=True,
    timeout=600
)
```

**Step 3:** Monitor progress by reading the log file with `read_file()`.

### Why Write to a .py File (Not Inline python -c)

Inline `python -c "..."` in terminal fails when:
- The password contains spaces (`wvvi ulwd ynkz avyt`) — shell escaping corrupts it
- The script has nested f-strings or triple-quotes — escaping becomes unmanageable

Always `write_file("campagne.py", ...)` first, then `terminal("python campagne.py", background=True)`.

### Gmail SMTP App Password Reliability

The Gmail SMTP App Password is more reliable than OAuth for automated campaigns:
- **OAuth tokens expire after ~7 days** in Google testing mode — requires interactive re-auth
- **App Passwords never expire** — once generated, they work indefinitely
- **SMTP + App Password** (smtp.gmail.com:587) handled 63/63 emails with 0 failures in one session

Prefer SMTP App Password for automated/programmatic sending. Reserve OAuth for interactive use cases (reading inbox, calendar, etc.).

**Do NOT use `subprocess.Popen` with `DETACHED_PROCESS` from `execute_code`** — the detached subprocess has a restricted Python environment and often can't find pip-installed packages, causing `ModuleNotFoundError`.
