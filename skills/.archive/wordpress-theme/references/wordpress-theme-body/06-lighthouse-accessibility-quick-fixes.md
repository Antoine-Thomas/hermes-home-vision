<!-- Source: wordpress-theme/SKILL.md · section 'Lighthouse Accessibility Quick Fixes' -->

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
