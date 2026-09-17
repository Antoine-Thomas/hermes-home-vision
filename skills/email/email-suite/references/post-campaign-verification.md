# Post-Campaign Verification

After a batch email campaign completes, run a verification pass to surface bounces, auto-replies, and real human responses that may be hidden in spam or other folders.

## When to Run

Immediately after a campaign finishes (~5-10 minutes), then again 1-2 hours later when more delayed replies may have arrived.

## Step 1: Check Spam for Bounces & Auto-Replies

Gmail often routes delivery failure notifications (bounces) and auto-replies (out-of-office) to the Spam folder. Search with:

```bash
GAPI="python $HOME/AppData/Local/hermes/skills/productivity/google-workspace/scripts/google_api.py"

# Check spam folder
$GAPI gmail search "in:spam newer_than:2d" --max 20
```

### Classify Results

| Type | From | Example | Action |
|------|------|---------|--------|
| **Hard bounce** | `mailer-daemon@googlemail.com` | "Adresse introuvable", "550 5.1.1" | Mark contact as dead, remove from future campaigns |
| **Soft bounce** | `mailer-daemon@googlemail.com` | "Boîte pleine", "Problème temporaire" | Retry later or mark as unreliable |
| **Auto-reply** | Real person's email | "En congés jusqu'au...", "Absent du bureau" | Note for context, no action needed |
| **Real reply** | Real person's email | Actual message content | Read and respond manually |

### Real Replies Hidden in Spam

Gmail sometimes routes legitimate human replies to spam — especially if the sender is not in contacts. Look for:
- `CATEGORY_PERSONAL` or `IMPORTANT` labels in spam (not `CATEGORY_PROMOTIONS` or `CATEGORY_UPDATES`)
- Subject lines that are replies to your campaign (containing "Re:")

## Step 2: Check All Mail for Human Replies

```bash
# Broad search excluding newsletters/promos
$GAPI gmail search "newer_than:2d -category:promotions -from:me -from:noreply" --max 30
```

Filter out:
- `CATEGORY_PROMOTIONS`, `CATEGORY_SOCIAL` — marketing/social
- `from:noreply`, `from:no-reply`, `from:notification` — automated
- `from:linkedin`, `from:facebookmail` — social network notifications
- `from:mailer-daemon` — already handled in Step 1

Focus on emails with `CATEGORY_PERSONAL` or unknown senders with real names in the `From` field.

## Step 3: Identify "STOP" / Opt-Out Replies

Some recipients reply "stop", "non", "désabonnement" — these must be blacklisted immediately.

```bash
# Search for opt-out signals in replies
$GAPI gmail search "subject:Re: newer_than:7d stop OR non OR désabonnement OR désinscription"
```

Add blacklisted emails to the campaign script's `BLACKLIST` set so they're never contacted again.

## Step 4: Bounce Summary

Extract bounce addresses from delivery failure notifications and cross-reference with the campaign CSV:

```
Hard bounces (remove):
- jmuzan@wanadoo.fr → Adresse introuvable
- rideprojectcaen@gmail.com → Adresse introuvable

Soft bounces (retry or flag):
- mcsara@gmx.de → Boîte pleine
- contact@hemisphere.fr → Problème temporaire (auto-retry by Gmail)
```

## Step 5: Auto-Reply to Real Human Replies

When a real person replies to the campaign and their reply is NOT an opt-out, consider responding with a personal follow-up. For batch campaigns where you want to auto-respond with the same announcement:

1. Extract the sender email from the reply
2. Check against blacklist (STOP replies)
3. If not blacklisted and not already in campaign, send the same campaign template
4. Use `terminal()` for the send (never `execute_code` — lacks `googleapiclient`)

## Monitoring with Cron

For ongoing monitoring, see `references/cron-auto-reply.md`. A cron job can poll for new replies and auto-respond with the campaign template, skipping blacklisted senders.
