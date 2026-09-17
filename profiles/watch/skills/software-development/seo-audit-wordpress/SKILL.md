---
name: seo-audit-wordpress
description: "Complete SEO audit workflow for WordPress sites — metadata extraction, duplicate detection, competitor keyword research, content gap analysis, pillar/cluster content architecture, and 4-week action planning. Production-tested on French local-business sites with Yoast SEO."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [SEO, WordPress, Audit, Content-Strategy, Keyword-Research, Yoast, Local-SEO]
---

# SEO Audit — WordPress Site

End-to-end SEO audit for WordPress sites. Covers technical metadata extraction, content gap analysis, competitive keyword research, pillar/cluster architecture design, and phased remediation planning. Designed for local-business SEO (e.g. Caen, Normandie) with Yoast SEO + LiteSpeed Cache stack.

## When to Use

- User asks for an "SEO audit" or "SEO analysis" of a WordPress site
- User asks for a "content strategy" or "content plan" for a WordPress site
- User asks for "keyword research" targeting a specific geographic area
- User asks for "pillar/cluster" or "topic cluster" content architecture
- User asks for "meta tag fixes", "duplicate titles", or "SEO improvements"

## Pre-Audit: Scoping Questions

Before starting, ask (or infer from context):
1. What's the site URL and CMS?
2. What's the geographic focus (city, region)?
3. What are the main services/products offered?
4. Is there an existing blog or content?
5. What SEO plugin is installed (Yoast, Rank Math, SEO Engine, none)?
6. Are there sub-sites, separate domains, or subdirectories?
7. Is the site a one-page (monopage) design or multi-page? (One-page with #sections is bad for SEO — each section needs its own URL)
8. What is the user's language? (If French, produce the full report in French — titles, descriptions, action plan)

## Audit Methodology

### Phase 1: Technical Metadata Extraction

Use `curl` to extract metadata from every accessible page — **not** `browser_navigate` (Google/DDG block scraping; browser may crash on Windows without sandbox; curl is more reliable for HTML inspection).

```bash
# Extract title, meta description, h1, canonical in one pass
curl -sL --max-time 15 --user-agent "Mozilla/5.0" "$URL" 2>&1 | \
  grep -i '<title\|<meta name="description"\|<h1\|name="robots\|<link rel="canonical\|<meta property="og:title\|<meta property="og:description' | head -10

# Full page dump for deeper analysis (watch for truncation)
curl -sL --max-time 15 --user-agent "Mozilla/5.0" "$URL" 2>&1 | head -c 50000
```

**What to check per page:**
- `<title>` is unique across the site
- `<meta name="description">` is unique (150-160 chars)
- `<h1>` exists and contains primary keyword
- `<link rel="canonical">` is correct (not pointing to another page)
- `name='robots'` allows index,follow
- Schema.org (JSON-LD) presence (LocalBusiness, Person, Organization)
- Open Graph tags (og:title, og:description, og:image)

### Phase 2: Site Structure Mapping

Map every page discovered:

```
/ (Accueil)
├── /page-1/
├── /page-2/
├── /blog/ (or /2026/... permalinks)
├── /legal/...
└── /sub-site/ (separate WP install)
    ├── /portfolio/
    └── /service-page/
```

**Multi-site scanning pattern (recommended for sites with subdomains/subdirectories):**
When the user has multiple domains or subdomains (e.g. searching-murphy.com, scenario.searching-murphy.com, thescreamingfan.com), scan them in **parallel** using `delegate_task` with `toolsets: ["terminal", "web", "file"]`. Each sub-agent gets one site to scan and returns a full summary. The parent agent then compiles the cross-site report.

```python
# Pseudocode for parallel scan
delegate_task(tasks=[
    {"goal": "Scan domain A fully: sitemap, metadata, SSL, redirections", "toolsets": ["terminal", "file"]},
    {"goal": "Scan domain B fully: sitemap, metadata, SSL, redirections", "toolsets": ["terminal", "file"]},
    {"goal": "Scan subdomain C fully: sitemap, metadata, SSL, redirections", "toolsets": ["terminal", "file"]},
])
```

Each sub-agent should return a table of all pages with their metadata, plus HTTP headers, response times, and any critical issues found.

**Key cross-site checks:**
- Do pages on site A link to broken pages on site B?
- Are all sites on the same hosting / same IP?
- Do subdomains have the same SEO plugin?
- Is there a canonical domain that should be the hub?

Check for:
- **Monopage structure** — all content in one page with anchor sections (#intro, #services). Bad for SEO because Google can't index separate topic URLs.
- **Isolated blog** — articles without categories/tags. Indicates no content strategy.
- **Duplicate titles across pages** — CRITICAL. Check every page's `<title>` for identity.
- **Broken links** — 301 loops, 404s, inaccessible subdomains.

### Phase 3: RSS / Sitemap Inspection

```bash
# Check RSS feed for blog articles
curl -s --max-time 10 "$SITE/feed/" 2>&1 | grep -o '<title>[^<]*</title>' | head -20
curl -s --max-time 10 "$SITE/feed/" 2>&1 | grep -oP '<link>\K[^<]+' | head -20

# Check sitemap
curl -sI --max-time 10 "$SITE/sitemap.xml" 2>&1
curl -sI --max-time 10 "$SITE/sitemap_index.xml" 2>&1
```

### Phase 4: Competitive Keyword Research

For local SEO, research these classes of keywords:
- **[Service] + [City]** — "création site WordPress Caen", "photographe entreprise Caen"
- **[Service] + [City context]** — "agence IA Caen", "développement web Caen"
- **[Problem] + [City]** — "refonte site internet Caen", "SEO Caen"

**On Google/DuckDuckGo being blocked:**
- Standard curl scraping is blocked by Google (JS-only content, CAPTCHA) and DuckDuckGo (bot challenge needing image selection).
- Use market knowledge: estimate search volumes from known categories (50-150/mois = low, 100-300/mois = medium).
- Classify competition by counting established local agencies/freelancers for each keyword.
- Rate opportunity as: TRÈS FORTE (very few competitors), FORTE (some but not dominant), MOYENNE (many established players).
- **Fallback pattern for `browser_navigate` failures on Windows:** Chrome often crashes with exit code 0 / no DevToolsActivePort. When that happens, do NOT attempt to fix the browser — fall back to curl immediately. Create a `recherche-google-concurrents.md` template file with URLs for manual searching. Include a clear note: "Effectuer les recherches manuellement dans un navigateur standard" and provide the exact Google search URLs.
- **Always produce a template even when scraping fails** — the user can fill it in 2 minutes by searching on their phone. A blank-but-structured template is infinitely better than no data.

### Phase 5: Content Gap & Duplicate Analysis

**Single biggest finding to check: are all pages' `<title>` and `<meta name="description">` identical?** If Yes:
- This is a CRITICAL issue. Google can't differentiate pages.
- Fix: go into the SEO plugin (Yoast, etc.) and set unique title+description per page.
- Provide the corrected table immediately in the report.

**Content gap signs:**
- 0 blog articles (despite WP having blog functionality)
- No categories/tags
- All services described on one page (no dedicated service pages)
- No pillar page structure
- Only 1-2 articles, isolated

### Phase 6: Pillar/Cluster Architecture

Design 3-5 pillars based on the site's actual services. Each pillar:

| Pillar | Page URL | Target Keywords | Articles |
|--------|----------|----------------|----------|

Each article needs:
| Article | Keyword | Search Intent | CTA (which service page) | Internal Links |

**Intent types:** Transactionnelle (buy), Commerciale (compare), Informationnelle (learn), Navigational (find page).

Always include a `references/<site-name>-content-plan.md` with the full table.

### Phase 7: 4-Week Action Plan

| Week | Focus | Daily tasks |
|------|-------|-------------|
| 1 | **Technical fixes** | Fix titles, meta descriptions, broken links, 301 loops, create blog structure |
| 2 | **Content creation** | Write 1-2 pillar pages + 2-3 cluster articles |
| 3 | **More content + local SEO** | Write remaining articles, optimize Google Business Profile, request reviews |
| 4 | **Internal linking + launch** | Maillage interne, sitemap submission, Search Console review |

## Report Template Sections

1. ÉTAT DES LIEUX DES SITES (one table per domain/subdomain)
2. ANALYSE DES MÉTADONNÉES (with before/after tables for titles+descriptions)
3. ANALYSE DE LA STRUCTURE (site map)
4. RECHERCHE DE MOTS-CLÉS (keyword table with volume, competition, opportunity)
5. ARCHITECTURE PILIERS/CLUSTERS (full tables)
6. PAGES PRÊTES EXISTANTES ET INTÉGRATION
7. PLAN D'ACTION 4 SEMAINES
8. TITLES & DESCRIPTIONS RECOMMANDÉS (exact replacements)
9. LES 2 MOTS-CLÉS PRIORITAIRES
10. RÉSUMÉ DES PROBLÈMES CRITIQUES (table with severity)

## Delivery Checklist

At the end of every audit, these files must exist:

| File | Required? | Content |
|------|-----------|---------|
| `<site>-audit-seo.md` | ✅ REQUIRED | Full report: all 10 sections, tables, action plan |
| `guide-correction-titres.md` | ✅ If duplicate titles found | Step-by-step Yoast/DB fix for each affected page |
| `solution-redirection-<issue>.md` | ✅ If 301 loops/broken redirects | Diagnostic + code fix + verification steps |
| `contenu/piliers/pilier-<topic>.md` | ✅ If content gap found | Full pillar page text (600-800 words each) |
| `contenu/plan-articles-satellites.md` | ✅ If content gap found | 4 articles per pillar × N pillars = 4N article briefs |
| `recherche-google-concurrents.md` | ✅ Always (even if scraping fails) | Template for 6+ Google searches, structured table to fill |

**Path convention:** All files go under the website's local project folder (e.g. `C:\Users\<user>\Local Sites\<site-name>\`), with content markdown under a `contenu/` subdirectory.

## Helper: Pillar Page Brief Template

Each pillar page should include:
- H1 containing the target keyword + city
- 3-4 H2 sections (strategy, offering, benefits, maintenance/CTA)
- At least 1 H3 with concrete details
- Blockquote: "Pourquoi me choisir ?" with local social proof
- CTA link to the contact/devis page
- 1 table (comparison, deliverables, pricing, or gains)
- Natural mentions of the target city (at least 10-15 across the text)

## Helper: Article Brief Template

| Field | Value |
|-------|-------|
| **Titre** | [keyword-driven title with city] |
| **Mot-clé principal** | [keyword] |
| **Intention de recherche** | Informationnelle / Commerciale / Transactionnelle |
| **CTA vers page pilier** | [link text → /page-url/] |
| **Résumé du contenu** | 4-5 phrases |
| **Liens internes suggérés** | → Pilier parent → 2-3 other cluster articles → 1 cross-pillar article |

## Pitfalls

- **Browser navigation on Windows** — Chrome may crash with sandbox issues. Fall back to curl for HTML extraction.
- **Google/DuckDuckGo scraping blocked** — both serve CAPTCHA/bot challenges to curl. Use market knowledge and classify competition manually rather than getting empty results. Note this limitation clearly in the report.
- **Large page dumps** — WordPress pages often exceed 100K chars. Use `head -c 30000` or grep-targeted extraction to stay within tool limits.
- **`grep -oP` may fail on Windows git-bash** — the `-P` (Perl regex) flag may not be available. Use `grep -o` with basic regex or `sed` alternatives.
- **UTF-8 encoding issues** — Some WP pages serve iso-8859-1 or have BOM characters. Pass `iconv -f utf-8 -t utf-8//IGNORE` or strip BOM with `sed '1s/^\xEF\xBB\xBF//'`.
- **Yoast + secondary SEO plugin conflict** — On subdirectory installs (e.g. /thescreamingfan/) the site may run SEO Engine instead of Yoast. Check `name="generator"` and plugin-specific meta tags.
- **SSL loop detection** — A 301 redirect from HTTP to HTTPS that loops is usually a server config issue (htaccess RewriteRule), not a DNS problem. Test with `curl -v` to see the redirect chain.
