# CSS Bulk-Modification Pattern for Child Themes

When applying a large set of coordinated style changes to a WordPress child theme
(e.g., restyling all cards, fixing typography, reshaping a map container, adding
swipe indicators), a single well-organized CSS block appended at the end of
`style.css` is far safer and more maintainable than editing existing rules
in-place.

## Why This Pattern

- **Avoids specificity wars with the parent theme.** Existing rules from the
  parent theme (Astra, in the Searching-Murphy case) often have high specificity
  and rely on exact cascade order. Editing them in-place risks breaking layout.
  New rules at the bottom naturally override earlier rules, and `!important` can
  be used selectively where needed.

- **Easy to audit and revert.** All changes are in one contiguous block. To
  revert everything, delete from the `═══` header to the end. To find what a
  specific section does, search for its subsection marker.

- **Prevents accidental breakage.** No risk of deleting a brace, mangling a
  media query, or introducing syntax errors into existing working code.

## Block Structure

Use a top-level separator header followed by numbered/emoji-marked subsections:

```css
/* ═══════════════════════════════════════════════════════════════
   [MODIFICATIONS YYYY-MM] — BRIEF DESCRIPTION
   ═══════════════════════════════════════════════════════════════ */

/* ──────────────────────────────────────────
   1.  SECTION NAME
   ────────────────────────────────────────── */
.selector-1,
.selector-2 {
    property: value;
}

/* ──────────────────────────────────────────
   2.  SECTION NAME (WITH RESPONSIVE)
   ────────────────────────────────────────── */
.selector {
    property: value;
}

@media (max-width: 768px) {
    .selector {
        property: mobile-value;
    }
}
```

## When to Use `!important`

Use `!important` ONLY when:

1. **The parent theme has an `!important` rule** that you must override.
2. **A rule is set in multiple places with high specificity** and a cascade
   approach would be fragile.
3. **The rule is genuinely meant to be definitive** (e.g., minimum font sizes,
   structural constraints like `overflow-x: hidden` on the body).

Do NOT use `!important` as a first resort. Test with normal specificity first.

## Coordinating JS and PHP Changes

CSS-only changes go in the bulk block. Changes that span CSS + JS + PHP should
be split:

- **CSS** → bulk block at end of `style.css`
- **JS** → targeted edits in the JS file (e.g., `js/main.js`) inside the
  existing IIFE structure
- **PHP templates** → inline edits in the respective template files (e.g.,
  `page-devis-custom.php`, `template-parts/content.php`)

## Real Session Example

From the searching-murphy theme restyle (2025-07), a single ~365-line block
was added covering:

1. Card styles (`.card`, `.swiper-slide article`, `.blog-article`)
2. Swipe indicators (scroll-snap, Swiper arrows, pagination dots)
3. Devis buttons (automatic detection of all "devis" links, pill shape, orange)
4. Typography minimums (`html 16px`, body ≥16px, h1 ≥32px, h2 ≥28px, h3 ≥22px)
5. Google Map container (320×620 centered, responsive)
6. Home button on `/devis-custom` page (top-left, grey, "Accueil" text)
7. General responsive rules (overflow-x hidden, card widths)

The block used `max(font-size, inherit)` with `!important` to enforce minimum
text sizes across all breakpoints, and `:has()` selectors to automatically
target any button containing a file-invoice icon as a "devis" button.

## Pitfalls

- **`max()` inside `font-size` must use `inherit` as the fallback**, not a
  hardcoded value: `font-size: max(16px, inherit) !important;` ensures the
  element keeps its intended size if it's already larger than 16px. Using
  `max(16px, 1rem)` flattens all text to 16px.
- **Pseudo-elements (`::before`/`::after`) are not reliably clickable** across
  all browsers. If you need clickable navigation arrows, use real DOM elements
  (Swiper's built-in `.swiper-button-prev`/`.swiper-button-next`) and style
  them, rather than CSS pseudo-elements.
- **`position: absolute` buttons need a positioned ancestor.** Always verify
  the parent container has `position: relative` (explicitly added if necessary)
  before positioning child elements absolutely.
- **`patch()` tool accidental over-deletion.** When replacing a multi-line
  old_string that includes the end of one CSS rule and the start of another,
  the tool may strip more than intended if the boundary isn't exact. Always
  verify with `read_file` around the patched area after the edit.
