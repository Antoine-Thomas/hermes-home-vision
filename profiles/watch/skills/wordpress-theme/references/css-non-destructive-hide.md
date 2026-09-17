# CSS Non-Destructive Hide Pattern

Hide an element via CSS only while keeping the PHP/HTML markup intact. Preferred over removing markup because it preserves server-side logic, avoids breaking JS selectors, and is trivially reversible.

## When to Use

- Hiding interactive elements (buttons, widgets) on specific page templates
- A/B testing visibility without touching PHP
- Progressive enhancement: element exists in DOM for JS but hidden from visual users
- Any case where removing PHP markup would break `getElementById`/`querySelector` references in JS

## Pattern

```css
/* Hide .target-element on front page only (all viewports) */
.front-page .target-element,
.page-template-front-page .target-element,
body.home .target-element,
.home .target-element {
  display: none !important;
  visibility: hidden !important;
  pointer-events: none !important;
  width: 0 !important;
  height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  border: 0 !important;
  background: transparent !important;
}
```

## Why multiple selectors?

WordPress body classes vary by theme and setup:
- `.front-page` — when `is_front_page()` is true (most themes)
- `.page-template-front-page` — when using a custom page template named `front-page.php`
- `body.home` — WordPress core class for the blog posts index or static front page
- `.home` — generic class, catches edge cases

Using all four ensures the hide works regardless of the theme's body class implementation.

## Why `!important` everywhere?

When overriding existing theme styles that may have high specificity, `!important` on every property ensures the hide is definitive. The alternative (playing specificity wars with parent theme selectors) is fragile and harder to audit.

## Key properties

| Property | Purpose |
|----------|---------|
| `display:none` | Removes from layout flow |
| `visibility:hidden` | Double insurance (some frameworks override display) |
| `pointer-events:none` | Prevents accidental click/hover |
| `width/height:0` | Collapses box model to zero |
| `margin/padding:0` | Eliminates any remaining spacing |
| `border:0` | Removes borders that could occupy space |
| `background:transparent` | Prevents background color leaks |

## Pitfalls

- **Not for elements referenced by JS**: If JS calls `.focus()` or `.scrollIntoView()` on the hidden element, it will still work (element is in DOM) but visual result may be confusing. Prefer `aria-hidden="true"` on the element itself if screen readers should also ignore it.
- **Don't use `aria-hidden` in CSS**: `aria-hidden` is an HTML attribute, not a CSS property. The CSS block above intentionally omits it — add it to the PHP markup if needed.
- **`.home` class collision**: Some themes use `.home` for something other than the front page. Verify with `view-source:` that your theme adds the expected body classes.
- **Reversible**: To restore visibility, remove this CSS block. No PHP changes needed — the markup was never touched.
