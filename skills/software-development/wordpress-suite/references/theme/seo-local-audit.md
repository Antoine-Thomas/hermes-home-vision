# SEO Local Audit — WordPress

## When to Use

Auditing a WordPress site for local SEO (town/city-level targeting). Used when the user wants a full SEO diagnostic with focus on a geographic area.

## Audit Checklist

### 1. Network & Infrastructure

| Check | Tool | What to look for |
|-------|------|------------------|
| www/non-www canonical | `curl -sI https://domain.com` | 301 → www (or non-www), consistent |
| HTTP→HTTPS redirect | `curl -sI http://domain.com` | 301 → https version |
| HSTS header | `grep -i Strict-Transport-Security` from curl headers | Should be present |
| Server cache | Look for `x-litespeed-cache`, `cf-cache-status`, `x-cache` | Indicates CDN/cache layer |
| Response time | `curl -w '%{time_total}s'` | Target < 200ms |

### 2. Sitemap & Indexation

```
/sitemap.xml
/sitemap_index.xml
/robots.txt
```

Collect all URLs from `page-sitemap.xml` and `post-sitemap.xml`. Count pages vs posts. Check for:
- HTTP 500 on any sitemap URL (common with Yoast slug corruption)
- Duplicate slug patterns (e.g. URL containing the full site URL in the path)
- Pages missing from sitemap that should be there

### 3. Per-Page Metadata Extraction

For each page in the sitemap, extract via curl + grep:

| Field | Command pattern |
|-------|----------------|
| HTTP status | `curl -sL -o /dev/null -w '%{http_code}'` |
| Title | `grep -oP '<title>.*?</title>'` |
| Meta description | `grep -oP 'name="description" content="[^"]*"'` |
| H1 | `grep -oP '<h1[^>]*>.*?</h1>'` — count occurrences |
| H2/H3 | Count of `<h2` / `<h3` tags |
| Images w/o alt | Count `<img` tags missing `alt=` |
| Canonical | `grep -oP 'rel="canonical"[^>]*href="[^"]*"'` |
| JSON-LD schema | `grep -oP 'application/ld\+json">.*?</script>'` |
| Mentions (city) | `echo $html \| grep -oP 'Caen' \| wc -l` |

### 4. Critical SEO Problems to Flag

- **Duplicate titles/meta descriptions** — multiple pages sharing the same title and meta description. This causes internal cannibalization.
- **Missing H1** — home page or key pages have no H1 tag.
- **Double H1** — theme outputs both `the_title()` wrapped in H1 AND a hardcoded H1 in the template.
- **Generic titles on legal pages** — privacy policy and terms pages inheriting the site's generic title template.
- **500 errors on indexed pages** — articles in the sitemap returning HTTP 500.
- **Confidentiality page duplicates** — `/politique-de-confidentialite/` and `/politique-de-confidentialite-2/`.

### 5. Local SEO SEO (City Focus)

Extract city name occurrences per page. Look for:

| Element | What to check |
|---------|---------------|
| City mentions in page text | Count per page — target 15-50+ on service pages |
| Google Maps embed | Present in contact section |
| Google Business Profile | `grep -i 'business\|maps.google'` in HTML |
| Address + phone | Visible NAP (Name, Address, Phone) |
| Schema LocalBusiness | JSON-LD block with `@type: "LocalBusiness"` or `"Person"` |
| Social profiles | Facebook, Instagram, LinkedIn, YouTube links |
| Google site verification | `google-site-verification` meta tag |
| Bing site verification | `msvalidate.01` meta tag |

### 6. Article / Single Post Audit

In `single.php` and `template-parts/content.php`, verify:

- ✅ Breadcrumb with category linked to pillar page
- ✅ Category displayed with hyperlink to corresponding pillar
- ✅ "Read more" text is localized ("Lire l'article complet" for French)
- ✅ CTA block at bottom linking to quote form with city mention
- ✅ Post navigation (prev/next)

### 7. Competitor Position Check (Google SERP)

Direct curl to Google is blocked (requires JavaScript). Use DuckDuckGo HTML mode as fallback:

```bash
curl -sL "https://html.duckduckgo.com/html/?q=mot+clé+ville" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
```

Parse `.result__a` and `.result__snippet` classes. Check whether the audited site appears.

**Keywords to check for local SEO:**
- `"service" + "ville"` (e.g. "création site WordPress Caen")
- `"métier" + "ville"` (e.g. "photographe professionnel Caen")
- `"agence" + "service" + "ville"` (e.g. "agence IA Caen")

## Pitfalls

- **Sitemap accessible at both `/sitemap.xml` AND `/sitemap_index.xml`** — robots.txt may list both; Yoast generates only one canonical index. Keep only the standard one.
- **Yoast article slug corruption** — if an article slug contains a full URL (`https://domain.com/2026/06/26/https-www-domain-com-guide/`), this causes HTTP 500 on the article. Fix by regenerating the slug in Yoast or editing the post.
- **Legal pages with generic titles** — privacy policy and terms pages often copy the site's default title template in Yoast. Set explicit titles per page.
- **Meta description hardcoded in header.php** — if the site has a `<meta name="description">` in `header.php`, it overrides or duplicates the Yoast meta description. The hardcoded version should use the SEO-optimized text, or be removed so Yoast can manage it.
