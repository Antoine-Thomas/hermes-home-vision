# Lighthouse Accessibility Fixes — WordPress Themes

Recurring patterns for fixing Lighthouse accessibility flags on WordPress child themes. Each entry covers the flag, the root cause, the exact fix, and verification steps.

---

## 1. Iframe Missing Title

**Lighthouse flag:** "L'élément iframe n'a pas de titre" / "`<iframe>` elements must have a title"

**Root cause:** Google Maps embeds, YouTube videos, and other third-party iframes are added without a `title` attribute.

**Fix:** Add a descriptive `title` that tells screen-reader users what the iframe contains. Use the business name and city for local SEO benefit.

```html
<!-- BEFORE: flagged by Lighthouse -->
<iframe src="https://www.google.com/maps/embed?..." width="100%" height="250"
  style="border:0; border-radius: 10px;" allowfullscreen="" loading="lazy"></iframe>

<!-- AFTER: passes Lighthouse -->
<iframe src="https://www.google.com/maps/embed?..." width="100%" height="250"
  style="border:0; border-radius: 10px;" allowfullscreen="" loading="lazy"
  title="Carte Google Maps de Searching Murphy à Caen"></iframe>
```

**Verification:** Re-run Lighthouse — the "iframe title" flag should disappear. Test with NVDA/JAWS: the title is announced when the iframe receives focus.

---

## 2. Social Media Icons Without Accessible Names

**Lighthouse flag:** "Links do not have a discernible name" on `<a class="icon brands fa-facebook-f">` elements.

**Root cause:** Font Awesome social icons use `<span class="label">` for their text, but the theme CSS hides labels with `display: none`. This removes the label from the accessibility tree — screen readers get a link with no name.

**Technical detail:** `display: none` removes elements from BOTH the visual rendering AND the accessibility tree. Screen readers skip these elements entirely. WCAG SC 2.4.4 (Link Purpose) requires every link to have a programmatically determinable name.

**Fix:** Replace `display: none` with the visually-hidden (screen-reader-only) pattern. The label stays invisible visually but screen readers announce it.

```css
/* BEFORE: hidden from everyone (accessibility violation) */
.icon>.label {
    display: none;
}

/* AFTER: visually hidden, screen-reader accessible */
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

**Why this pattern works:**
- `position: absolute` — removes from normal flow (no layout shift)
- `width: 1px; height: 1px` — minimal footprint
- `overflow: hidden` — prevents any visible overflow
- `clip: rect(0,0,0,0)` — legacy clip (older browsers)
- `border: 0` — no border artifact

Screen readers (NVDA, JAWS, VoiceOver) see the text content and announce "Facebook link", "Instagram link", etc.

**Verification:** 
1. Re-run Lighthouse — the "discernible name" flag should disappear
2. Open browser DevTools → Accessibility panel → inspect an icon link → verify it has a computed name (e.g. "Facebook")
3. Test with NVDA: Tab to each icon — the label text should be spoken

---

## 3. Color Contrast — White Text on Light Background

**Lighthouse flag:** "Background and foreground colors do not have a sufficient contrast ratio."

**Root cause:** A child theme overrides the body `background` to a light color (e.g. `#cbe8e8` — light cyan) but the text rules (`body`, `strong`, `h1`-`h6`) still use `#ffffff` (white). White on light cyan has a contrast ratio of ~1.3:1 — far below WCAG AA 4.5:1.

**Contrast calculations (session reference):**

| Foreground | Background | Ratio | Pass AA (4.5:1)? |
|-----------|-----------|-------|-------------------|
| `#ffffff` (white) | `#cbe8e8` (light cyan) | 1.29:1 | NO |
| `#1b1f22` (near-black) | `#cbe8e8` (light cyan) | 12.75:1 | YES |

**Fix — change all white text rules to a dark color.** Use `#1b1f22` (consistent with the theme's `.button.primary` color) or `#000000`:

```css
/* Body text */
body, input, select, textarea {
    color: #1b1f22;  /* was #ffffff */
}

/* Bold text */
strong, b {
    color: #1b1f22;  /* was #ffffff */
}

/* Headings */
h1, h2, h3, h4, h5, h6 {
    color: #1b1f22;  /* was #ffffff */
}

/* Heading underline (major class) */
h1.major, h2.major, ... {
    border-bottom: solid 1px #1b1f22;  /* was #ffffff */
}

/* Footer — explicit fallback for inherited text */
#footer {
    color: #1b1f22;  /* ensure footer text is never white */
}

/* Buttons on light backgrounds */
a.button.primary {
    background-color: #cbe8e8;
    color: #1b1f22;  /* was inheriting white */
}
```

**How to find all white text rules:**
```bash
# Search the stylesheet for every white/light color assignment
grep -n '#ffffff\|#fff\b\|white\|color.*#f[ef]' style.css
```

Review each match against its background to verify the contrast passes AA.

**Verification:** Re-run Lighthouse — the "contrast ratio" flag should disappear. Focus on the specific elements Lighthouse flagged (it lists the selectors and offending colors in the report).

---

## 4. Images Without Explicit Dimensions (CLS)

**Lighthouse flag:** "Image elements do not have explicit width and height" — this contributes to Cumulative Layout Shift (CLS), a Core Web Vital.

**Root cause:** `<img>` tags lack `width` and `height` attributes, or use `width="100%" height="auto"`. The browser can't reserve space before the image loads, causing content to jump.

**Fix — step 1: Add dimensions to HTML.** Use the display/rendered size (not the original file dimensions):

```html
<!-- BEFORE: no dimensions — CLS trigger -->
<span class="image main">
    <img src="pic01.webp" class="lazyload" loading="lazy" alt="...">
</span>

<!-- AFTER: explicit dimensions — no CLS -->
<span class="image main">
    <img src="pic01.webp" width="590" height="197" class="lazyload" loading="lazy" alt="...">
</span>

<!-- BEFORE: percentage-based — browser can't reserve space -->
<img src="Fondcarte.webp" width="100%" height="auto" alt="...">

<!-- AFTER: pixel dimensions -->
<img src="Fondcarte.webp" width="210" height="180" alt="...">
```

**Fix — step 2: Resize source images.** After adding display dimensions, resize the source images to match to avoid serving oversized files:

```bash
# Check current file dimensions
ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
  -of csv=p=0 pic01.webp
# → 960,320 (original) — but displayed at 590×197 (2.6× too large)

# Resize with ImageMagick
magick pic01.webp -resize 590x197 pic01.webp

# Or with cwebp (smaller output)
cwebp original.webp -resize 590 197 -o pic01.webp -q 85

# Batch resize all section images
for f in pic01.webp pic02.webp pic032.webp pic05.webp; do
    magick "$f" -resize 590x197 "$f"
done

# REGENERATE WORDPRESS THUMBNAILS after resizing originals
wp media regenerate --only-missing
```

**Verification:** Re-run Lighthouse — the "explicit width and height" and "properly size images" flags should both improve. Check Core Web Vitals in Search Console after deployment.

---

## Session Workflow for Batch Lighthouse Fixes

When fixing multiple Lighthouse flags on a theme with hash-based navigation (Swiper, etc.):

1. **Backup all files first:**
   ```bash
   for f in style.css front-page.php header.php footer.php; do
       cp "$f" "$f.bak-$(date +%Y%m%d-%H%M%S)"
   done
   ```

2. **Group fixes by file** — apply all changes to one file before moving to the next

3. **After each file, verify anchors:** sites using anchor navigation (`#intro`, `#code`, etc.) break if `id` or `href` values change. Run:
   ```bash
   grep -n 'article id=\|href="#' front-page.php header.php
   ```
   Ensure every `#anchor` appearing as `href` also appears as an `article id`.

4. **For contrast fixes, use a consistent dark color** — pick the one already used elsewhere in the theme (e.g., the `.button.primary` color) rather than introducing a new hex value

5. **Re-run Lighthouse** after all fixes to confirm flags are resolved
