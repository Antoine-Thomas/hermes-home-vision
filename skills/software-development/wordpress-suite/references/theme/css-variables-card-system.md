# CSS Custom Properties Card System (SM CARD SYSTEM pattern)

When a WordPress child theme has multiple card-like elements (service cards,
article cards, Swiper slides) that share the same design language, using
CSS custom properties (`--sm-card-*`) on `:root` with media query overrides
is dramatically more maintainable than per-selector rules with `!important`.

## Architecture

Define ALL card attributes as CSS variables in `:root`:

```css
:root {
  /* Palette */
  --sm-card-bg: #ffffff;
  --sm-card-accent: #FF6600;
  --sm-card-border: #284543;
  --sm-card-text: #1b1f22;
  --sm-card-text-soft: #555555;
  --sm-card-radius: 16px;

  /* Spacing */
  --sm-card-padding: 24px;
  --sm-card-padding-x: 24px;
  --sm-card-gap: 1rem;
  --sm-card-margin-y: 20px;
  --sm-card-max-width: 800px;

  /* Shadows */
  --sm-card-shadow: 0 8px 24px rgba(0,0,0,0.12);
  --sm-card-shadow-hover: 0 16px 32px rgba(0,0,0,0.18);

  /* Buttons */
  --sm-btn-radius: 50px;
  --sm-btn-shadow: 0 4px 12px rgba(255,102,0,0.4);
  --sm-btn-shadow-hover: 0 6px 16px rgba(255,102,0,0.6);

  /* Navigation (Home/Next buttons) */
  --sm-nav-size: 3.25rem;
  --sm-nav-bg: var(--sm-card-border);
  --sm-nav-bg-hover: var(--sm-card-accent);
  --sm-nav-color: #ffffff;
}
```

Then override the variables at each breakpoint with media queries on `:root`:

```css
@media (max-width: 1024px) {
  :root { --sm-card-padding: 2rem; }
}
@media (max-width: 768px) {
  :root { --sm-card-padding: 1.5rem; }
}
@media (max-width: 480px) {
  :root { --sm-card-padding: 1rem; }
}
```

Card rules reference the variables — no hardcoded values:

```css
#main article.card {
  display: flex !important;
  flex-direction: column !important;
  padding: var(--sm-card-padding) var(--sm-card-padding-x) !important;
  background: var(--sm-card-bg) !important;
  border-radius: var(--sm-card-radius) !important;
  box-shadow: var(--sm-card-shadow) !important;
  color: var(--sm-card-text) !important;
  transition: transform 0.3s ease, box-shadow 0.3s ease !important;
}
```

## When to Use

- **Bulk theme reskin** — one palette change (`--sm-card-bg: #ffffff`,
  `--sm-card-accent: #FF6600`) propagates everywhere
- **Responsive spacing** — media queries on `:root` adjust padding/gaps
  globally without touching each selector
- **Button restyling** — `--sm-btn-radius: 50px` turns all rectangle buttons
  into pills in one line
- **Shadow tuning** — one variable change adjusts all card shadows

## When NOT to Use

- When the theme has no existing card system and only 2-3 card instances.
  The bulk-append pattern (`references/css-bulk-modification.md`) is simpler
  for small changes.
- When the parent theme already has a mature variable system (e.g., Kadence,
  GeneratePress with their own `--global-*` variables). Work WITH those
  variables, don't create a parallel system.

## Real Session Example

The `sm` project (C:\Users\searc\Local Sites\sm) at searching-murphy theme had
the SM CARD SYSTEM v1.0 already in place with `:root` variables. A one-liner
change (`--sm-card-bg: #ffffff`) turned all teal cards white, and
`--sm-card-accent: #FF6600` turned yellow accents orange, without touching
a single selector rule.

## Pitfalls

- **Color contrast** — when changing `--sm-card-bg` to `#ffffff` (white), you
  MUST also change `--sm-card-text` to a dark color and adjust shadow opacity.
  The old text color and border colors designed for a dark background will
  become invisible on white.
- **`!important` on variable-bearing rules** — the card rules that consume the
  variables often need `!important` because they fight against the parent
  theme's years of accumulated overrides. The variable definitions in `:root`
  don't need `!important` — it's the consumer rules that do.
- **Don't shadow parent theme variables** — prefix your variables
  (`--sm-card-*`, `--sm-*`) to avoid colliding with Astra's own system.
- **Read the file BEFORE patching** — CSS files in these projects can exceed
  6000 lines. Open with `read_file(offset=X, limit=Y)` to find the exact
  variable block location before using `patch()`.
