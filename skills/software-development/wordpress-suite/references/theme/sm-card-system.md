# SM CARD SYSTEM — Design pattern (searching-murphy theme)

## What it is
A structured CSS card system using `:root` custom properties, found in the `searching-murphy` child theme (Astra parent). It powers the homepage's five info cards (intro / code / Design / assos / contact).

## Key files
- `style.css` — contains the full system starting around line 5325 (`SM CARD SYSTEM v1.0`)
- `front-page.php` — uses `<article class="card">` with semantic children

## CSS variable palette (DO NOT CHANGE without permission)
```css
:root {
  --sm-card-bg: #0c9f93;           /* teal background */
  --sm-card-accent: #fdc502;       /* yellow accent */
  --sm-card-border: #284543;       /* dark teal */
  --sm-card-text: #ffffff;         /* white text */
  --sm-card-text-soft: rgba(255,255,255,0.88);
  --sm-card-radius: 14px;
  --sm-card-padding: 2.5rem;
  --sm-card-shadow: 0 8px 24px rgba(0,0,0,0.22);
  --sm-card-shadow-hover: 0 14px 32px rgba(0,0,0,0.28);
  --sm-btn-radius: 8px;
  --sm-nav-size: 3.25rem;         /* nav buttons */
  --sm-nav-bg: #284543;
  --sm-nav-bg-hover: #fdc502;     /* yellow on hover */
}
```

## Component classes
| Class | Role |
|-------|------|
| `#main article.card` | Card container (flex column, centered, max-width 800px) |
| `.card-image` | Image band at top (200px height on desktop) |
| `.card-title` | h2 with yellow underline border |
| `.card-body` | Paragraph text (semi-transparent white) |
| `.card-buttons` | Button group (flex-wrap, centered) |
| `.card-yellow-links` | Band of yellow category links below divider |
| `.card-divider` | Thin separator (80% width, semi-transparent) |
| `.card-home-btn` | Home button (bottom-left corner, rounded to card radius) |
| `.next` | Next slide button (bottom-right corner) |
| `.card-meta` | Small metadata text (phone, etc.) |
| `.card-donate` | PayPal form container |

## Card navigation buttons — mirrored corner pattern

Navigation buttons on cards use a MIRRORED OPPOSITE-CORNER convention. Both buttons share identical dimensions, background, and interaction states — only the corner and border-radius differ.

| Property | `.next` (next slide) | `.card-home-btn` / `.devis-home-btn` (home) |
|----------|---------------------|---------------------------------------------|
| Position | `bottom: 0; right: 0` | `bottom: 0; left: 0` |
| Size | `4rem × 4rem` | `4rem × 4rem` |
| Background | `#284543` | `#284543` |
| Border-radius | `0 0 0.5rem 0` (bottom-right) | `0 0 0 0.5rem` (bottom-left) |
| Icon | Arrow `➤` | SVG house (20×20px) |
| Hover icon | `#fdc502` (yellow) | `#fdc502` (yellow) + `translateY(-2px)` |
| Active bg | `#fdc502` + inset shadow | `#fdc502` + inset shadow + `translateY(1px)` |
| Label visible | N/A | **Never** — labels break the visual ("cassent le visuel") |
| z-index | auto | `20` (above card content) |

### Key rules for adding/modifying card nav buttons
- **Never add text labels** to icon buttons on cards. Use `aria-label` for accessibility.
- **Match the existing pattern** — don't invent new sizes, colors, or positions. If `.next` is bottom-right at 4rem, the home button should be bottom-left at 4rem with the same background.
- **Border-radius mirrors** — the corner facing the card interior gets the radius. Right side for `.next`, left side for home.
- **CSS placement**: use `position: absolute` with `bottom: 0; left: 0` (or `right: 0`). High-specificity selectors like `#main article.card .devis-home-btn` ensure override of global button styles.
- **Devis page exception**: the home button on `/devis-automatique/` is NOT inside an `article.card` and should NOT get absolute positioning — it stays in normal flow. Use the same `.devis-home-btn` class but without the card scoping.

## Map container within cards
```css
.card .map-container {
  width: 100%;
  max-width: 500px;
  margin: 0.5rem auto;
  border: 1px solid var(--sm-card-border);
  border-radius: var(--sm-card-radius);
}
.card .map-container iframe { height: 200px; }
```

## Responsive breakpoints (media queries on :root)
- Desktop ≥1025px: padding 2.5rem, nav 3.25rem
- Desktop 769-1024px: padding 2rem, nav 3rem
- Tablet ≤768px: padding 1.5rem, nav 2.75rem
- Mobile ≤480px: padding 1rem, nav 2.5rem

## How to ADD changes safely
1. **Add new CSS at the END of style.css** — never edit the existing `:root` or component rules
2. **Use the existing selectors** — `#main article.card .button.primary` already has high specificity
3. **Target specific cards if needed** — `#contact.card .map-container` scopes changes to the contact card only
4. **Use the existing CSS variables** — `var(--sm-card-accent)` instead of hardcoding `#fdc502`

## What NOT to do (lessons from session rollback)
- ❌ Change `--sm-card-bg` from teal to white — rewrites every card on the site
- ❌ Change `--sm-card-accent` from yellow to orange — rewrites every accent element
- ❌ Add `font-size: 16px !important` globally — destroys the responsive type scale
- ❌ Add 50+ `!important` rules in one commit — creates specificity hell
- ✅ Add a targeted block at the end of style.css scoped to specific selectors
