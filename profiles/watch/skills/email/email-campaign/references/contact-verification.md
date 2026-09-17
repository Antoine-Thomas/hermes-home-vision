# Website Contact Verification via curl

When a CSV of contacts has been generated but site URLs, emails, and locations
may be fabricated or outdated, verify them before sending any campaign.

## Bulk HTTP Status Check

```bash
for url in "https://www.example.com" "https://www.other.fr"; do
  status=$(curl -sL -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null)
  echo "$status $url"
done
```

- HTTP 200 → site is accessible
- HTTP 000 → DNS failure, timeout, or site doesn't exist
- HTTP 4xx/5xx → site exists but page is broken

## Location Verification (France-specific)

For verifying that a business is actually in Caen (or a target city), grep the HTML
for postal codes and city names:

```bash
curl -sL --max-time 5 "https://www.example.com" 2>/dev/null | \
  grep -oiP '(caen|hérouville|mondeville|ifs\b|14\d{3}|calvados|normandie)' | \
  sort -u | head -5
```

French postal code patterns by département:
- **14xxx** → Calvados (Caen, Deauville, Honfleur)
- **50xxx** → Manche (Cherbourg, Saint-Lô)
- **76xxx** → Seine-Maritime (Rouen, Le Havre)
- **75xxx** → Paris

## Email Extraction from Website

```bash
curl -sL --max-time 5 "https://www.example.com" 2>/dev/null | \
  grep -oP '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' | \
  sort -u | head -5
```

## Python Parallel Verification

For large CSVs, use ThreadPoolExecutor to verify sites in parallel (10 workers,
8-second timeout per site):

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request, ssl, re, csv

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def check_site(contact):
    site = contact.get("Site_Web", "").strip()
    try:
        req = urllib.request.Request(site, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8, context=ssl_ctx) as resp:
            html = resp.read().decode("utf-8", errors="ignore")[:50000]
        caen = bool(re.findall(r'(?i)(caen|hérouville|14\d{3})', html))
        emails = list(set(re.findall(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}', html)))
        return {**contact, "Status": "200", "Caen_OK": str(caen), "Emails": "|".join(emails[:5])}
    except Exception as e:
        return {**contact, "Status": str(e)[:30], "Caen_OK": "False", "Emails": ""}
```

## Common Fabrication Patterns to Flag

When verifying a CSV that may contain fabricated data:

- **Sequential phone numbers**: `02 31 34 56 78`, `02 31 44 55 66`, `06 12 34 56 78` — immediate red flag
- **Mismatched email/domain**: `bonjour@wagence.com` but site is `wagence.fr`
- **Wrong city**: Agency listed as "Caen" but WHOIS/location says Lyon or Paris
- **Generic local parts**: `contact@`, `info@`, `bonjour@` — always verify the domain exists
