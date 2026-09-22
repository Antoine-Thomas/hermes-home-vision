---
name: wordpress-performance
description: "Optimize WordPress PageSpeed scores and Core Web Vitals."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [WordPress, Performance, Lighthouse, PageSpeed, CSS, Caching, Core-Web-Vitals]
---

# WordPress Performance — Lighthouse Optimization

Systematic optimization of WordPress child themes for Lighthouse/PageSpeed scores. Covers the full pipeline from audit analysis to implementation, targeting render-blocking resources, main-thread work, unused CSS/JS, caching, font loading, and LCP optimization.

## When to Use

- User shares a Lighthouse/PageSpeed report showing poor performance (score < 70)
- Core Web Vitals are failing: FCP > 2.5s, LCP > 4s, TBT > 200ms, CLS > 0.1
- Render-blocking resources are flagged as the top opportunity
- User asks to "speed up my WordPress site" or "improve PageSpeed score"

## Quick Decision Tree

| Symptom | Fix |
|---------|-----|
| Render-blocking CSS (2s+ savings) | Critical CSS inline + non-blocking stylesheet pattern |
| Large style.css (>100KB) loaded blocking | Same — critical CSS inline covers above-fold, rest deferred |
| jQuery Migrate loaded | `wp_default_scripts` hook to remove the dependency |
| wp-emoji loaded | `remove_action` on 4 emoji hooks |
| Missing cache headers (30KB+ savings) | `.htaccess` mod_expires 1 year + mod_headers immutable |
| LCP image slow (>5s) | `<link rel="preload" as="image" fetchpriority="high">` in header |
| Font loading delay (FOUT/CLS) | `font-display:swap` on Google Fonts + preload webfonts |
| TBT > 200ms (main thread) | Remove unused JS, defer all scripts, async third-party |
| CLS > 0.1 (layout shifts) | Explicit image width/height, comprehensive critical CSS |

## Workflow

### Phase 1 — Analyze the Report
Extract FCP/LCP/TBT/CLS values and the Opportunities section. Identify which resources are render-blocking and what Lighthouse estimates as savings.

### Phase 2 — Audit the Theme
1. `functions.php`: all `wp_enqueue_style`/`wp_enqueue_script` calls, Google Fonts, third-party scripts
2. `header.php`: preconnects, LCP image, inline scripts
3. `.htaccess`: mod_expires, mod_headers, Gzip
4. CSS size: `wc -c style.css` — if >100KB, critical CSS is mandatory

### Phase 3 — Apply (priority order, see `references/pagespeed-patterns.md`)
1. Critical CSS inline via `wp_head` (priority 1) + non-blocking stylesheets via `style_loader_tag`
2. Remove WordPress bloat (jquery-migrate, wp-emoji)
3. Preload LCP image in header.php + web fonts in `wp_head` (priority 2)
4. Harden `.htaccess` caching (1-year + immutable)
5. Verify defer/async on all scripts

### Phase 4 — Verify
Re-run Lighthouse. Check Network tab — stylesheets should load late. Verify no FOUC. If CLS > 0.1, critical CSS missed elements — add more rules.

## Expected Impact

| Métrique | Avant | Après |
|----------|-------|-------|
| Performance | 50-60 | 75-85 |
| FCP | 5-8s | 2-3s |
| LCP | 10-15s | 3-5s |
| CLS | 0.2-0.4 | <0.1 |

## Key Pitfalls

- **Critical CSS too thin → FOUC → CLS rises.** Cover EVERY above-fold element: header, nav, swiper slides, cards, buttons, headings, footer, canvas. Include design tokens, heading sizes, responsive breakpoints, and state transitions.
- **Non-blocking CSS without critical CSS = broken page.** Always pair them.
- **Font preload URL mismatch = double download.** Must match exact browser request URL including `&display=swap`.
- **`immutable` cache without URL versioning = stale assets.** Use `_S_VERSION` in enqueue calls.
- **Never make admin-area styles non-blocking.** Check `is_admin()` before applying the filter.
- **jQuery Migrate removal is safe; jQuery removal is NOT.** Plugins depend on jQuery itself.

## References

- `references/pagespeed-patterns.md` — Complete PHP/htaccess code blocks for all optimization steps
