<!-- Source: wordpress-theme/SKILL.md · section 'Reference Files' -->

## Reference Files

- **[references/theme-modification.md](references/theme-modification.md)** — Full general theme modification workflow: backup, identify files, CSS/PHP/JS editing, testing, verification checklist.
- **[references/css-bulk-modification.md](references/css-bulk-modification.md)** — CSS bulk-modification pattern for child themes: adding a single organized block at the end of style.css, coordinating with JS and PHP changes, pitfalls.
- **[references/css-variables-card-system.md](references/css-variables-card-system.md)** — CSS custom properties pattern for themable card systems: `:root` variables, media query overrides, palette/typography/shadow control from one place.
- **[references/theme-optimization.md](references/theme-optimization.md)** — Systematic audit: security, performance, asset loading, caching, render-blocking, SEO (meta tags, structured data, heading hierarchy), UI/UX, functionality.
- **[references/seo-local-audit.md](references/seo-local-audit.md)** — Local SEO audit methodology for city-targeted WordPress sites: infrastructure checks, per-page metadata crawl, heading analysis, city-mention density, Google SERP positioning, and competitor analysis.
- **[references/lighthouse-accessibility-fixes.md](references/lighthouse-accessibility-fixes.md)** — Recurring Lighthouse accessibility flags: iframe titles, screen-reader-only labels, color contrast correction, explicit image dimensions for CLS, and image resizing commands.
- **[references/searching-murphy-modifications.md](references/searching-murphy-modifications.md)** — Searching-Murphy Astra child theme specifics: Swiper initialization, dynamic wrapper, hashchange handling, tab synchronization, slide transitions.
- **[references/searching-murphy-session.md](references/searching-murphy-session.md)** — Session-specific lessons from Searching-Murphy theme work.
- **[references/sm-card-system.md](references/sm-card-system.md)** — SM Card System v1.0/v2.0: CSS variable palette, component classes, button hierarchy, map container, responsive breakpoints, and what NOT to change.
- **[references/swiper-custom-navigation.md](references/swiper-custom-navigation.md)** — Swiper API patterns for custom navigation.
- **[references/validation-pipeline.md](references/validation-pipeline.md)** — Automated validation pipeline for theme assets: JS syntax (`node --check`), CSS brace count (Python), SVG well-formedness (`xml.etree.ElementTree`), PHP lint (`php -l`), and git patch integrity (`git apply --check`). Includes workaround for `read_file` truncation in `execute_code`.
- **[references/multi-agent-collaboration.md](references/multi-agent-collaboration.md)** — Pattern for Hermes + Kimi K3 collaboration: `final-collab.json` structure (catalogue, solutions, fallback rules, learning log), cost management, verify-before-create workflow, and validation-before-commit workflow.
- **[references/standalone-js-module.md](references/standalone-js-module.md)** — Zero-dependency JS module pattern with anti-duplication guard, self-resolving asset paths via `document.currentScript.src`, MatchMedia with Safari <14 addListener fallback, and explicit image dimensions for CLS prevention.
