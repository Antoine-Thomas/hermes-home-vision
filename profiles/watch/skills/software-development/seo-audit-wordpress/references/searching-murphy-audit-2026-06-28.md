# Searching Murphy SEO Audit — 28 June 2026

This is a concrete example of a full SEO audit produced with the seo-audit-wordpress skill.
Site: searching-murphy.com (Thomas Leroyer, développeur WordPress & photographe, Caen).

## Key Findings

1. **Duplicate titles CRITICAL** — All pages (Accueil, Devis, CGU, Politique) used the exact same `<title>`: `Searching Murphy|Thomas Leroyer|Photo|video|WordPress|Caen`. No page differentiation.
2. **scenario.searching-murphy.com in 301 loop** — Portfolio inaccessible, all incoming links broken.
   - Root cause: server-level redirect pushes non-www → HTTPS without adding `www`, WordPress expects `www.scenario.*` as canonical.
   - Fix: .htaccess `RewriteCond %{HTTP_HOST} !^www\\.scenario\\.searching-murphy\\.com$` + `RewriteRule ^ https://www.scenario.searching-murphy.com%{REQUEST_URI} [R=301,L]`
3. **Monopage architecture** — No dedicated service pages, no blog categories, 1 single blog article (HTTP 500!).
4. **Missing content strategy** — Zero pillar pages, no internal linking, no article clusters.

## Header Analysis

| Page | Title | Meta Description | H1 |
|------|-------|-----------------|----|
| / | Searching Murphy\\|Thomas Leroyer\\|Photo\\|video\\|WordPress\\|Caen | Same as title… | (none — single-page site with #sections) |
| /devis-automatique/ | IDENTICAL to above | IDENTICAL | Devis automatique |
| /politique-de-confidentialite/ | IDENTICAL | IDENTICAL | Politique de confidentialité |
| /conditions-dutilisation/ | IDENTICAL | IDENTICAL | Conditions d'utilisation de Searching Murphy |

## Files Produced

| File | Purpose | Lines |
|------|---------|-------|
| `searching-murphy-audit-seo.md` | Full 9-section report | ~400 lines |
| `guide-correction-titres.md` | Step-by-step Yoast fix + SQL alternatives | 144 lines |
| `solution-redirection-scenario.md` | 301 loop diagnostic + 4 solutions | 171 lines |
| `contenu/piliers/pilier-wordpress.md` | Pillar page: création site WordPress Caen | ~600 words |
| `contenu/piliers/pilier-design.md` | Pillar page: design graphique Caen | ~530 words |
| `contenu/piliers/pilier-ia.md` | Pillar page: intelligence artificielle Caen | ~580 words |
| `contenu/piliers/pilier-photo.md` | Pillar page: photographe professionnel Caen | ~580 words |
| `contenu/plan-articles-satellites.md` | 16 article briefs with keywords, CTA, internal links | 247 lines |
| `recherche-google-concurrents.md` | 6-query competitor research template (manual fill) | Template |

## Scanning Approach

The audit used `delegate_task` with 3 parallel sub-agents for multi-site scanning:
- Sub-agent 1: searching-murphy.com (main site) — curl-based metadata extraction
- Sub-agent 2: scenario.searching-murphy.com (portfolio subdomain) — discovered 301 loop
- Sub-agent 3: thescreamingfan.com (creative portfolio) — confirmed accessible

Browser tools failed on this Windows host (Chrome sandbox issue). All work done via curl + grep/pcre, which turned out to be faster and more reliable than browser-based inspection for metadata collection.

## Parallel Content Production Pattern

After scanning, the session produced 4 pillar pages + 1 full article plan + 1 title-fix guide + 1 redirect solution in a single `delegate_task` call, demonstrating that content creation and technical fixes can run in parallel across sub-agents. This is the recommended pattern for maximum efficiency.

## Recommended Top-2 Keywords for Local SEO

1. **"création site WordPress Caen"** — core service, existing content, strong relevance
2. **"photographe professionnel Caen"** — complementary service, zero dedicated page, strong opportunity

## Corrective Titles Suggested

| Page | Suggested Title |
|------|----------------|
| / | Searching Murphy – Développeur WordPress & Photographe à Caen |
| /devis-automatique/ | Devis gratuit – Création site web & photo à Caen \\| Searching Murphy |
| CGU | Conditions d'utilisation – Searching Murphy Caen |
| Politique | Politique de confidentialité – Searching Murphy Caen |
