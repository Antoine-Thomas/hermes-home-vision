# Email Scraping — Discovery Patterns

Techniques for finding email addresses from company names when you have no existing contact data.

## Domain Generation

Convert a company name to a probable domain:

```python
def clean_domain(name):
    # Remove commercial name in parentheses
    name = re.sub(r'\(.*?\)', '', name)
    name = name.lower().strip()
    # Remove accents
    for a, b in [('é','e'),('è','e'),('ê','e'),('à','a'),('ô','o'),
                 ('ù','u'),('î','i'),('ï','i'),('ç','c')]:
        name = name.replace(a, b)
    # Remove punctuation
    name = re.sub(r"['\",.&+]", '', name)
    # Keep only alphanumeric
    name = re.sub(r'[^a-z0-9]', '', name)
    return name[:35]
```

## Website Probing Strategy

Try in this order, stop on first success:
1. `https://www.{name}.fr`
2. `http://www.{name}.fr`
3. `https://{name}.fr`
4. `http://{name}.fr`
5. Repeat with `.com` TLD if `.fr` fails

**Timeout:** 6 seconds per probe. Use `ssl.create_default_context()` with `check_hostname=False` for sites with bad SSL.

## Email Extraction

From each successful page load, also try `/contact`, `/contactez-nous`, `/nous-contacter`, `/a-propos`.

```python
def extract_emails(html):
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(pattern, html)
    # Filter out known noise
    skip = ('.png','.jpg','.jpeg','.gif','.svg','.webp','.ico',
            '.example','.domain','sentry','wixpress','sentry-next',
            'user@domain.com','votre@email.com','jean@exemple.fr',
            '@exemple.fr','info@mysite.com','@email.com')
    valid = [e.lower() for e in emails
             if not any(s in e.lower() for s in skip)
             and not e[0].isdigit()
             and len(e) < 80]
    return list(set(valid))[:5]
```

## Fake Email Patterns to Filter

Always filter these when scraping French sites:
- `user@domain.com` / `votre@email.com` — placeholder text
- `jean@exemple.fr` / `prenom@exemple.fr` — example domains
- `info@mysite.com` / `@email.com` — default templates
- `*@sentry.wixpress.com` / `*@sentry-next.wixpress.com` — Wix telemetry
- `8eb368c6...@sentry.wixpress.com` — hex IDs from Wix

## Performance Benchmarks

| Metric | Value |
|---|---|
| Threads | 10 |
| Rate | ~8 req/s |
| 1 850 companies | ~4.5 minutes |
| Sites reachable | ~26% |
| Emails found | ~9-15% |

## Parallel Implementation

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(scrape_entreprise, e): i
               for i, e in enumerate(entreprises)}
    for future in as_completed(futures):
        result = future.result()
        # process result
```
