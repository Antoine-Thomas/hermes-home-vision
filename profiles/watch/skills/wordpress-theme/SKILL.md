---
name: wordpress-theme
description: "WordPress theme modification, optimization, and auditing — safe editing workflows for child themes, CSS/PHP/JS changes, security audits, performance tuning, and SEO improvements."
version: 1.0.0
author: Hermes Agent (consolidated from wp-theme-modification, wordpress-theme-modification, wordpress-theme-optimization)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [WordPress, Themes, Child-Themes, CSS, PHP, Security, Performance, SEO, Auditing]
---

# WordPress Theme — Modification & Optimization

Safe, repeatable workflows for modifying WordPress child themes, auditing theme health, and optimizing for production. All operations respect WordPress coding standards and child theme best practices.

## When to Use

- Modifying CSS, PHP templates, or JavaScript in a WordPress theme
- Fixing responsive issues, footer visibility, or layout problems
- Adding custom JavaScript behaviors (Swiper navigation, event listeners)
- Auditing a theme for security vulnerabilities, performance, SEO, or accessibility
- Preparing a theme for production after modifications

## Quick Decision Tree

| Task | Reference File |
|------|---------------|
| General theme modification workflow | `references/theme-modification.md` |
| **CSS bulk-modification pattern** (single block at end of style.css) | `references/css-bulk-modification.md` |
| **CSS variables card system** (theming with `:root` custom properties) | `references/css-variables-card-system.md` |
| **SM Card System** (searching-murphy theme structured card pattern) | `references/sm-card-system.md` |
| Security, performance, SEO, UI/UX audit | `references/theme-optimization.md` |
| **Local SEO audit** (city focus, metadata crawl, positions) | `references/seo-local-audit.md` |
| **Lighthouse accessibility fixes** (iframe title, .label, contrast, CLS) | `references/lighthouse-accessibility-fixes.md` |
| **Comprehensive site health audit** (10-point: infrastructure, images, menu, DB, SEO, llms.txt) | `references/comprehensive-site-health-audit.md` |
| Searching-Murphy theme specifics (Swiper, hashchange) | `references/searching-murphy-modifications.md` |
| Session lessons from Searching-Murphy work | `references/searching-murphy-session.md` |
| **Swiper custom navigation patterns** | `references/swiper-custom-navigation.md` |
| **Automated validation pipeline** (JS/CSS/SVG/PHP checks) | `references/validation-pipeline.md` |
| **Multi-agent collaboration** (Hermes + Kimi K3, final-collab.json) | `references/multi-agent-collaboration.md` |
| **Standalone JS module** (anti-duplication, zero-dep, MatchMedia) | `references/standalone-js-module.md` |
| **Session lessons + QA headless + Devis sandbox** | `references/searching-murphy-session.md` |
| **Responsive button: circle→pill** (mobile icon-only, desktop icon+label) | `references/responsive-button-circle-pill.md` |
| **Session lessons + QA headless + Devis sandbox** | `references/searching-murphy-session.md` |
| **Circular home button** (.cat-wp-home-btn / .devis-home-btn pattern) | `references/circular-home-button.md` |

## Safety First — The Golden Rules

1. **Backup before editing.** Always.
2. **Use correct path format on Windows.** In `write_file`/`patch` tools, use `C:\Users\...` (native Windows) — `/c/Users/...` (bash-style) silently resolves to `C:\c\Users\...` which doesn't exist. Always check the tool's `resolved_path` output.
3. **Use a child theme.** Never edit parent theme files directly — updates will overwrite your changes.
3. **Test after every change.** Clear caches, check mobile/desktop, verify behavior.
4. **Escape all PHP output.** Use `esc_html()`, `esc_attr()`, `wp_kses_post()`, etc.
5. **Use `!important` as a last resort** — only when a more specific selector genuinely cannot override a parent-theme rule. Bulk `!important` usage (more than 3-5 in a single change) is a signal that the approach is wrong.
6. **Never rewrite `:root` CSS custom properties** (`--sm-*`, `--primary`, `--card-bg`, etc.) without explicit user permission. These variables control the entire theme's color scheme, spacing, and typography. Changing them is a design-level decision, not a CSS implementation detail.
7. **Respect the existing color scheme.** The theme's accent colors, background colors, and text colors are chosen deliberately. Do not replace them with different colors (e.g., swapping yellow #fdc502 for orange #FF6600) unless the user says precisely which color to change.

## Common Workflow

### 1. Backup
```bash
cp wp-content/themes/theme-name/file.ext wp-content/themes/theme-name/file.ext.bak-$(date +%Y%m%d)
```

### 2. Identify the File
- **Global styles**: `style.css`
- **Header**: `header.php`
- **Footer**: `footer.php`
- **Homepage**: `front-page.php`
- **JavaScript**: `js/main.js` or similar
- **Template parts**: `template-parts/` or `inc/`

### 3. Make Changes
- CSS: Add rules at the bottom of `style.css` or within appropriate `@media` queries
- PHP: Use escaping functions, keep inline PHP minimal
- JS: Insert code inside existing initialization functions, maintain brace balance

### 4. Test
- Clear all caching layers (browser, plugin, server)
- Test at 320px, 480px, 768px, 1024px breakpoints
- Check browser console for JS errors
- Verify no PHP warnings (`WP_DEBUG` temporarily if needed)

## Common CSS Fixes

```css
/* Footer always visible */
#footer { display:block!important; opacity:1!important; visibility:visible!important; }
body.is-article-visible #footer { display:none!important; }

/* Hide Swiper navigation arrows */
.swiper-button-prev, .swiper-button-next { display:none !important; }

/* Fix overlay issues */
.close::after { display:none !important; content:none !important; }

/* Center slide content */
.swiper-slide { display:flex; justify-content:center; align-items:center; }
.swiper-slide article { max-width:800px; margin:40px auto; padding:30px; }
```

## Lighthouse Accessibility Quick Fixes

Three recurring Lighthouse accessibility flags on WordPress themes and their one-step fixes. See `references/lighthouse-accessibility-fixes.md` for full context and contrast-ratio calculations.

### 1. Iframe missing title

Lighthouse flags: "L'élément iframe n'a pas de titre" / "iframe element has no title."

Fix — add a descriptive `title` attribute to every `<iframe>`:

```html
<!-- BEFORE -->
<iframe src="https://maps.google.com/..." width="100%" height="250"></iframe>

<!-- AFTER -->
<iframe src="https://maps.google.com/..." width="100%" height="250"
  title="Carte Google Maps de [Entreprise] à [Ville]"></iframe>
```

The title must describe the iframe's content, not be generic like "Carte" or "Maps".

### 2. Social media icon links without accessible names

Lighthouse flags: "Links do not have a discernible name." Social icons like `<a class="icon brands fa-facebook-f"><span class="label">Facebook</span></a>` fail if the label text is hidden with `display: none`.

Fix — replace `display: none` with the visually-hidden (screen-reader-only) pattern:

```css
/* BEFORE — hidden from everyone, including screen readers */
.icon>.label {
    display: none;
}

/* AFTER — visually hidden but read by screen readers */
.icon>.label {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0,0,0,0);
    border: 0;
}
```

The labels stay visually invisible but NVDA/JAWS/VoiceOver read them ("Facebook", "Instagram", etc.), making the icon links accessible.

### 3. Color contrast — white text on light backgrounds

Lighthouse flags: "Background and foreground colors do not have a sufficient contrast ratio." This often happens when a child theme overrides the body background to a light color (e.g. `#cbe8e8` — light cyan) but leaves the text color as `#ffffff` (white). White on `#cbe8e8` has a contrast ratio of ~1.3:1 — far below the WCAG AA minimum of 4.5:1.

Fix — change all text elements from white to a dark color (`#1b1f22` — near-black gives ~12.8:1 on `#cbe8e8`):

```css
/* Change these from #ffffff to #1b1f22: */
body, input, select, textarea { color: #1b1f22; }
strong, b                    { color: #1b1f22; }
h1, h2, h3, h4, h5, h6      { color: #1b1f22; }
h1.major, h2.major, ...      { border-bottom: solid 1px #1b1f22; }

/* Footer — add explicit color fallback */
#footer { color: #1b1f22; }

/* Buttons on light backgrounds — ensure dark text */
a.button.primary {
  background-color: #cbe8e8;
  color: #1b1f22;
}
```

Check for related rules that also set `color: #ffffff` — search the stylesheet for `#ffffff`, `white`, `#fff` and verify each against its background.

### 4. Explicit image dimensions (CLS prevention)

Lighthouse flags: "Image elements do not have explicit width and height" — this causes Cumulative Layout Shift.

Fix — add `width` and `height` attributes matching the image's display size:

```html
<!-- BEFORE -->
<img src="pic01.webp" class="lazyload" loading="lazy" alt="...">

<!-- AFTER -->
<img src="pic01.webp" width="590" height="197" class="lazyload" loading="lazy" alt="...">
```

Also replace `width="100%" height="auto"` with actual pixel dimensions. After adding explicit dimensions, resize the source images to match (see Image Optimization below).

## Image Optimization

When source images are larger than their display size, resize them to match using ImageMagick or cwebp:

```bash
# Resize to display dimensions with ImageMagick
magick pic01.webp -resize 590x197 pic01.webp

# Same with cwebp (lighter output)
cwebp original.webp -resize 590 197 -o pic01.webp -q 85

# After resizing originals, regenerate WordPress thumbnails
wp media regenerate --only-missing
```

Always back up originals before resizing: `cp pic01.webp originaux/pic01.webp`.

## JavaScript Insertion Pattern

Always insert new code inside the initialization function's scope, before the closing brace, at the correct indentation level:

```javascript
// Add click listeners for manual slide navigation
document.querySelectorAll(".next a").forEach(function(link) {
    link.addEventListener("click", function(e) {
        e.preventDefault();
        if (window._homeSwiper) {
            window._homeSwiper.slideNext();
        }
    });
});
```

## Breadcrumb + Category-to-Pillar Pattern (content.php)

When modifying `template-parts/content.php` for SEO, add a `$pilier_map` array at the top to map category slugs to pillar page URLs:

```php
$pilier_map = array(
    'wordpress' => '/developpeur-web-wordpress-caen/',
    'design'    => '/creation-site-design-graphique-caen/',
    'ia'        => '/developpeur-ia-agentique-caen/',
    'photo'     => '/photographe-professionnel-caen/',
    'video'     => '/photographe-professionnel-caen/',
);
```

### Breadcrumb (single posts only)
```php
if ( is_singular() && 'post' === get_post_type() ) :
    $cats = get_the_category();
    if ( ! empty( $cats ) ) :
        echo '<nav class="breadcrumb">';
        echo '<a href="' . esc_url( home_url( '/' ) ) . '">Accueil</a>';
        foreach ( $cats as $cat ) {
            $cat_slug = strtolower( $cat->slug );
            echo ' / ';
            if ( isset( $pilier_map[ $cat_slug ] ) ) {
                echo '<a href="' . esc_url( home_url( $pilier_map[ $cat_slug ] ) ) . '">'
                    . esc_html( $cat->name ) . '</a>';
            } else {
                echo '<a href="' . esc_url( get_category_link( $cat->term_id ) ) . '">'
                    . esc_html( $cat->name ) . '</a>';
            }
        }
        echo '</nav>';
    endif;
endif;
```

### CTA Block (bottom of single posts)
```php
<?php if ( is_singular() && 'post' === get_post_type() ) : ?>
<div class="post-cta-devis" style="margin-top:40px;padding:25px;background:var(--surface);
     border-radius:var(--radius);border-left:4px solid var(--primary);text-align:center;">
    <p style="margin:0 0 12px 0;font-size:1.1em;">
        <strong>Besoin d'un service similaire à Caen ?</strong>
    </p>
    <p style="margin:0 0 16px 0;color:var(--muted);font-size:0.95em;">
        Développement WordPress, design, IA, photo — je réalise votre projet sur mesure.
    </p>
    <a href="https://www.searching-murphy.com/devis-automatique" class="button primary"
       style="display:inline-block;padding:12px 28px;background:var(--primary);
              color:#fff;text-decoration:none;border-radius:8px;font-weight:600;">
        <i class="fas fa-file-invoice" style="margin-right:8px;"></i>
        Demander un devis gratuit à Caen
    </a>
</div>
<?php endif; ?>
```

## Navigation with Local SEO Anchor Text (header.php)

When the site uses a hardcoded `<nav><ul>` menu (not a WordPress nav menu), update the `<a>` text to include city + service keywords:

```html
<nav>
    <ul>
        <li><a href="#intro">Accueil</a></li>
        <li><a href="#code">Création site WordPress Caen</a></li>
        <li><a href="#Design">Design graphique Caen</a></li>
        <li><a href="#assos">Intelligence Artificielle Caen</a></li>
        <li><a href="#contact">Contact / Devis gratuit</a></li>
    </ul>
</nav>
```

Also update the hardcoded `<meta name="description">` in header.php to reflect the SEO-optimized text with city and service keywords.

## Pitfalls

- **Editing parent theme directly** — changes lost on theme update. Always use a child theme.
- **JS code outside the IIFE** — inserting code after `})(jQuery);` breaks functionality because the code runs outside the scope where theme variables are defined.
- **Missing `e.preventDefault()`** — causes unwanted hash jumps in navigation.
- **Incorrect indentation** — breaking JavaScript formatting or brace balance.
- **Over-engineering CSS buttons** — when the user asks for a card navigation button (home, next, close), start with the SIMPLEST possible version: minimal size (30-48px), one background color, one hover color, basic border-radius. Do NOT add `flex-direction: column`, `font-size`, `font-weight`, `drop-shadow` filters, multi-step media queries, or complex transition chains unless explicitly asked. The user will say "tu as complexifié le design" and ask to restore the simpler version. The .next button (4rem×4rem, #284543, bottom-right) is the reference pattern — mirror it, don't redesign it. If the user asks to reduce the button, just change the size numbers. Don't add new visual properties.
- **Overusing `!important`** — leads to specificity wars. `!important` is a last resort, not a default. Adding dozens of `!important` rules in a single commit (especially alongside color scheme changes) is a destructive anti-pattern that creates irreversible specificity problems and will be rejected. Use `!important` ONLY when you can document exactly which parent-theme rule you're overriding and why a more specific selector won't work. A single well-placed `!important` is defensible; 50 of them is a rollback waiting to happen.
- **`document.currentScript.src` breaks with cache/minification plugins** — JS that derives asset paths from `document.currentScript.src` (e.g., replacing `js/theme-cards.js` with `img/eye-closed.svg`) produces 404s when WP Rocket, LiteSpeed Cache, or W3 Total Cache rewrites script URLs to `/wp-content/cache/min/1/...`. The minified SVG path doesn't exist in the cache directory. **Fix:** pass the correct asset URL from PHP via `wp_localize_script()`:
```php
wp_localize_script( 'my-script-handle', 'MY_NAMESPACE', array(
    'svgUrl' => get_stylesheet_directory_uri() . '/assets/img/my-icon.svg',
));
```
Then in JS, use `window.MY_NAMESPACE.svgUrl` as priority 1, falling back to `currentScript.src` derivation only if the localized variable is absent. This pattern also future-proofs against CDN rewrites and plugin conflicts. See `references/standalone-js-module.md` for the updated fallback chain.
- **Rewriting design-system CSS variables without consent** — many themes (including this user's) have structured `:root` custom properties (`--sm-card-bg`, `--sm-card-accent`, `--sm-card-text`, `--sm-card-radius`, `--sm-card-shadow`, etc.) that define the entire visual identity in one place. Changing these variables — especially the color palette — rewrites the whole site at once. **NEVER modify `:root` CSS custom property values unless the user explicitly asked you to change that specific variable.** If the user wants a different button color or card style, add targeted overrides at the end of the stylesheet, not by rewriting the design tokens. Changing `--sm-card-bg: #0c9f93` to `--sm-card-bg: #ffffff` turns every teal card on the site white in one stroke — that's a design decision only the user can make.
- **Changing theme color scheme without consent** — the user's theme has official brand colors (e.g., teal `#0c9f93` and yellow `#fdc502` for this project). These colors are deliberate. Never replace them with different colors (e.g., orange `#FF6600`) unless the user explicitly instructs you to. If a new element needs a new color, add it as a separate rule, don't repurpose the accent/highlight variables.
- **Modifying global typography without consent** — rules like `body, p, span, a, li { font-size: 16px !important; }` and `h1 { font-size: 32px !important; }` override the theme's entire responsive type scale. The user's theme already has carefully tuned breakpoint-aware font sizes (e.g., `html { font-size: 16pt }` with media queries reducing it for smaller screens). Blowing that away with flat `!important` rules is destructive. Only change typography when the user specifically asks for a size adjustment, and target only the elements they name.
- **Prefer targeted overrides over design-system rewrites** — when the user asks for visual changes to a component (cards, buttons, map), the safe approach is: (1) add new CSS rules at the END of `style.css` scoped to the specific selectors they mentioned, (2) use the theme's existing CSS custom properties where possible, (3) never touch the `:root` block or existing component rules. This keeps the theme's architecture intact and makes your changes easy to audit and roll back.
- **Removing sanitization/nonces** — creates security vulnerabilities.
- **Not clearing caches** — changes appear not to have taken effect.
- **Meta description hardcoded in header.php** — if a `<meta name="description">` exists in header.php, it competes with Yoast's meta description. Either remove the hardcoded tag (let Yoast manage it) or keep it as a fallback with the SEO-optimized text matching Yoast.
- **Yoast meta update on Local by Flywheel** — WP-CLI may fail because the bundled PHP lacks the `mysqli` extension. The Local PHP binary often also lacks the PDO MySQL driver (`could not find driver`). Three workarounds, in order of reliability:

1. **Python + pymysql (most reliable on Windows)** — install `pymysql`, find the MySQL port (Local uses 10002-10005, test with `pymysql.connect(host='127.0.0.1', port=N, user='root', password='root', database='local')`), then update `wp_postmeta` directly: `DELETE FROM wp_postmeta WHERE post_id=X AND meta_key IN ('_yoast_wpseo_title','_yoast_wpseo_metadesc')` followed by `INSERT`. DB creds from `wp-config.php` (typically local/root/root on Local). See `references/yoast-via-mysql.md` for a ready-to-run Python script.
2. **Standalone PHP script with wp-load.php** — write a script that `require 'wp-load.php'` and calls `update_post_meta($id, '_yoast_wpseo_title', $val)`, then run with a PHP binary that has mysqli (not the Local bundled one).
3. **System PHP with PDO** — if the system PHP has `pdo_mysql`, use it with the Local DB credentials. The port is usually NOT 3306 — check `netstat -ano | grep LISTEN` for MySQL-like ports (10002-10005 on Local for Windows).
- **Category-to-pillar mapping must exist** — before adding breadcrumb links from categories to pillar pages, ensure the actual pillar pages exist at the target slugs. If they don't exist yet, the links will 404 and hurt SEO.
- **Character encoding corruption in PHP files** — accented characters (à, é, è, etc.) may appear as `�` (U+FFFD) in theme files, especially those edited outside a proper UTF-8 editor. When a `patch()` old_string containing an accent fails to match despite looking correct, the file bytes differ from what's displayed. Debug with `xxd` on the specific line: `sed -n 'LINEp' file.php | xxd`. For `à` look for `c3 a0` (valid UTF-8) vs `ef bf bd` (U+FFFD replacement char) vs `e0` (Latin-1). Then use the exact raw string from the file (including `�` if present) as the old_string in your patch. Once replaced, the new text will be written in proper UTF-8.
- **Cache/minification plugins rewrite asset URLs & break SVG paths** — plugins like WP Rocket, LiteSpeed Cache, or W3 Total Cache rewrite JS URLs. When JS derives SVG paths from `document.currentScript.src`, the derived path points to the cache directory where the SVG does NOT exist → 404. **Fix**: pass the real asset URL via `wp_localize_script()` in functions.php, and prioritize it in JS. Pattern: `wp_localize_script('handle', 'SM_THEME_CARDS', array('eyeClosedSvg' => get_stylesheet_directory_uri() . '/assets/img/eye-closed.svg'));` then in JS check `window.SM_THEME_CARDS.eyeClosedSvg` first, fall back to `currentScript.src` derivation.
- **Cross-platform path resolution (Windows git-bash)** — When using `write_file` or `patch` from the terminal on Windows (git-bash/MSYS), paths starting with `/c/Users/...` are NOT equivalent to `C:\Users\...`. The tool's resolved path will be `C:\c\Users\...` which doesn't exist. The tool reports success but writes to a ghost location. **ALWAYS use `C:\Users\...` (native Windows paths) in `write_file` and `patch` tool calls** even though the terminal uses POSIX-style `/c/Users/...` paths. The resolved_path in the tool output will tell you where the file actually landed — verify it ends up under `C:\Users\`, not `C:\c\`.
- **Anchors must stay intact when editing hash-navigated pages** — sites using Swiper or hashchange-based navigation (anchor links like `#intro`, `#code`, `#Design`) rely on exact `id` attributes and `href` values to synchronize slides and browser history. When modifying H2 text, paragraphs, or buttons inside `<article id="...">` sections, never alter the `id` attribute on the article element or the `href` anchor in the nav menu (header.php). After all edits, verify every anchor appears both as an `<article id="...">` target and as a matching nav `<a href="#...">` — a single mismatch breaks swipe navigation silently.
- **Images without explicit width/height cause CLS** — Lighthouse flags images missing `width` and `height` attributes as "Image elements do not have explicit width and height." This causes Cumulative Layout Shift (CLS), hurting Core Web Vitals. Add `width` and `height` matching the display size (not the original file size) to every `<img>`. For images using `width="100%" height="auto"`, replace with pixel values from the actual rendered dimensions. After adding dimensions, resize the source images to match to avoid serving oversized files.
- **Footer dark-background contrast** — when giving `#footer` a dark background, you MUST also update ALL child rules that set `color` with `!important` (typically `.copyright`, `.google-business a`, `.home-legal-link a`). These override the footer's `color` and will render invisible (e.g. `#000` on `#1b1f22`) if not changed to a light color like `#cbe8e8`. The pattern: (1) add `background-color: #1b1f22; color: #cbe8e8;` to `#footer`, (2) search the file for `#footer` child rules with `color`, (3) change each to a light color matching the footer text.
- **Swiper stale dimensions after hide/show cause visual offset** — when a Swiper container is hidden (menu open) then re-shown, the slide positions are stale because Swiper computed them at zero dimensions. The fix is three-part: (1) `observer: true, observeParents: true` in Swiper config, (2) call `swiper.update()` before every `slideTo()`, (3) ensure `show()` runs before navigation so `update()` sees real dimensions. See `references/swiper-custom-navigation.md` → Resilience section for full code.
- **Swiper `slidesPerView: 'auto'` collapses slides without explicit CSS width** — when you change a Swiper instance from the default single-slide mode (`slidesPerView: 1`) to auto-width mode (`slidesPerView: 'auto'`), each `.swiper-slide` MUST have an explicit width in CSS (e.g., `width: 90%`) or the slides collapse to zero and nothing renders. Always pair the JS config change with a corresponding CSS rule: `.home-swiper .swiper-slide { width: 90% !important; }`. Also add `centeredSlides: true` in the Swiper config if you want the active slide centered with partial adjacent slides visible.
- **Swiper slide pseudo-elements block navigation buttons** — when `.swiper-slide::before`/`::after` have a z-index equal to or higher than navigation buttons, they block clicks even with `pointer-events: none`. The fix: (1) set `z-index: 5` on the pseudo-elements, (2) set `z-index: 20 !important` + `pointer-events: auto !important` + `cursor: pointer !important` on `.swiper-button-prev`/`.swiper-button-next`, (3) set `z-index: 15` on `.swiper-pagination`. Never use `inset: 0` on pseudo-elements — use `top`/`bottom` + `width` to keep the zone narrow (28px or less). See `references/swiper-custom-navigation.md` → CSS Pitfalls for the full pattern.
- **Swiper button CSS variable indirection** — aliasing `--sm-swiper-nav-size: var(--sm-nav-size)` in `:root` adds an unnecessary hop. When unifying Swiper nav buttons with card buttons (`.card-home-btn`, `.next`), use the same variables directly: `width: var(--sm-nav-size)` on both, not `var(--sm-swiper-nav-size)` on one and `var(--sm-nav-size)` on the other. This avoids drift when one alias is updated but the other isn't. Also: never hardcode pixel values for Swiper button dimensions inside `@media` queries — always use `var(--sm-nav-size)` so the breakpoint cascade works correctly.
- **Home button styling — iterative refinement**: When a user asks to match a button to an existing reference (e.g., `.next`), avoid over-engineering. Start simple (circular, 30-48px, one color, minimal shadows) and let the user request additions (hover effects, active states, positioning). Complex multi-layer CSS (flex-direction, font-size, font-weight, drop-shadow filters) applied in one pass often gets rejected — the user wants to see incremental progress and approve each step. Prefer the simplest version first: `display:flex; width:30px; height:30px; border-radius:50%; background:#0c9f93;` — then layer on hover/active/focus based on explicit user requests.
- **CSS bulk-modification pattern for child themes** — when applying a large set of style changes to a WordPress child theme, prefer adding a single well-organized CSS block at the END of `style.css` rather than editing rules in-place. This avoids specificity conflicts with the parent theme's existing rules, makes all changes easy to find and audit, and keeps the file structure intact. Organize the block with visible ASCII section headers (e.g., `/* ═══ SECTION NAME ═══ */`) and group related rules together. Use `!important` sparingly — only on rules that genuinely need to override parent theme specificity. Apply JS config changes and PHP template edits separately. See `references/css-bulk-modification.md` for the full pattern.
- **"Retire/remove" user command may be a reaction to broken styling, not a removal request** — When the user says "retire les boutons" or "remove X" immediately after styling changes were applied, check first whether the element is rendering broken (wrong size, label visible, missing active state, bad colors). The user may be reacting to a visual bug, not requesting deletion. Fix the CSS before removing markup — and confirm with the user. See `references/circular-home-button.md` for the home button pattern that triggered this pitfall.
- **`execute_code` string escaping with complex terminal commands** — When `terminal()` is called from within an `execute_code` block with a Python f-string containing nested quotes, backslashes, and special characters, the escaping becomes unmanageable and produces `SyntaxError` or `NameError`. The workaround: either (a) use simple `terminal()` calls from the chat level directly, or (b) write the script to a temp file and execute it, or (c) use raw Python `open()`/`os.listdir()` inside `execute_code` instead of shelling out. This is NOT a `terminal()` bug — it's an f-string escaping limitation in `execute_code`.

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

## Templates

- **[templates/wp-theme-backup.sh](templates/wp-theme-backup.sh)** — Automated backup script for WordPress theme files.
- **[templates/swiper-nav-listener.js](templates/swiper-nav-listener.js)** — Ready-to-use Swiper navigation click listener.
- **[templates/swiper-immediate-transition.js](templates/swiper-immediate-transition.js)** — Immediate slide transition without animation.
- **[templates/headless-qa.js](templates/headless-qa.js)** — Puppeteer-core headless QA script for theme testing (screenshots + DOM dumps + selector checks).
