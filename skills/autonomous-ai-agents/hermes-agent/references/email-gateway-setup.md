# Email Gateway Setup (absorbed from hermes-email-setup)

Configure Hermes's built-in email gateway adapter so people can email the agent and receive replies. Uses Python's `imaplib` + `smtplib` — no external dependencies.

## Quick Reference

| What | Command / File |
|------|---------------|
| Interactive setup | `hermes gateway setup` → select "Email" |
| Manual config | Add variables to `~/.hermes/.env` |
| Test connection | `hermes gateway` (tests IMAP+SMTP on startup) |
| Start gateway | `hermes gateway` (foreground) or `hermes gateway install` (service) |

## Gmail Setup

### Step 1: Enable 2FA + Create App Password

1. Enable 2-Factor Authentication on the Google Account
2. Go to https://myaccount.google.com/apppasswords
3. Select "Mail" or "Other (custom name)" → name it "Hermes"
4. Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)

**Hermes does NOT use OAuth client-id/client-secret for email.** Email uses IMAP+SMTP with an app password.

### Step 2: Add to `.env`

```bash
EMAIL_ADDRESS=searching.murphy@gmail.com
EMAIL_PASSWORD=abcd efgh ijkl mnop
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_ALLOWED_USERS=your@email.com
```

### Step 3: Start Gateway

```bash
hermes gateway          # foreground (test first)
hermes gateway install  # install as user service
```

## Other Providers

| Provider | IMAP Host | SMTP Host |
|----------|-----------|-----------|
| Gmail | `imap.gmail.com` | `smtp.gmail.com` |
| Outlook/M365 | `outlook.office365.com` | `smtp.office365.com` |
| Yahoo | `imap.mail.yahoo.com` | `smtp.mail.yahoo.com` |
| Fastmail | `imap.fastmail.com` | `smtp.fastmail.com` |

Default ports: IMAP 993 (SSL), SMTP 587 (STARTTLS).

## Testing the Connection

Run the bundled test script (reads `.env` directly, bypassing the secret redactor):

```bash
python scripts/test_email_connection.py
```

Or use inline Python snippet (see main skill body for code).

## Quick Send (Python smtplib) — No Gateway Needed

For one-off sends without the full gateway, use Python's `smtplib` directly. See the `email-campaign` skill for full HTML campaign workflows.

## Gateway Setup — Interactive Flow

`hermes gateway setup` walks through these prompts:

1. **Platform selection** — pick Email (option 6) or Done (23)
2. **Reconfigure?** — asks `[y/N]` if email is already configured
3. **Start gateway now?** — `[Y/n]`
4. **Auto-start on login?** — `[Y/n]`
5. **Start now after install?** — `[Y/n]`
6. **Windows Scheduled Task?** — `[Y/n]` (Windows only)

On Windows the gateway installs as a Scheduled Task (`Hermes_Gateway`).

Non-interactive automation: `printf 'n\\n23\\ny\\ny\\ny\\ny\\n' | hermes gateway setup`

## Config Storage

Email credentials may be stored in **either** `~/.hermes/.env` **or** `~/.hermes/config.yaml` (secrets section). The wizard shows email as "configured" based on `config.yaml` entries, even when no `.env` file exists.

## Pitfalls

- **No `hermes configure email` command exists.** Use `.env` variables or `hermes gateway setup`.
- **Gmail uses app passwords, NOT OAuth** for IMAP/SMTP.
- **Hermes secret redactor masks inline credentials.** Read from `.env` inside scripts instead.
- **Self-messages loop prevention** — don't send from the same address the agent monitors.
- **Email may show "configured" without `.env`** — check `config.yaml` too.
- **On Windows, the gateway uses Scheduled Tasks, not systemd.**
