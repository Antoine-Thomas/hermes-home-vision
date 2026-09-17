# Swiper Custom Navigation

## Swiper API for Manual Slide Control

When working with Swiper instances, you can control slides programmatically using the following methods:

- `swiper.slideNext()` - Transition to the next slide
- `swiper.slidePrev()` - Transition to the previous slide
- `swiper.slideTo(index, speed, runCallbacks)` - Transition to a specific slide
- `swiper.slideToLoop(index, speed, runCallbacks)` - Transition to a specific slide in loop mode

## Event Listener Best Practices

When adding custom click listeners to navigation elements:

1. **Always prevent default behavior** when overriding native links:
   ```javascript
   link.addEventListener("click", function(e) {
       e.preventDefault();
       // Your custom logic here
   });
   ```

2. **Check if Swiper instance exists** before calling methods:
   ```javascript
   if (window._homeSwiper) {
       window._homeSwiper.slideNext();
   }
   ```

3. **Maintain scope** - Ensure your listener is added after Swiper initialization.

## Example: Custom Next Button Navigation

```javascript
// Add click listeners to .next a for manual slide navigation
document.querySelectorAll(".next a").forEach(function(link) {
    link.addEventListener("click", function(e) {
        e.preventDefault();
        if (window._homeSwiper) {
            window._homeSwiper.slideNext();
        }
    });
});
```

This pattern ensures:
- No unwanted hash changes or page jumps
- Safe access to the Swiper instance
- Proper slide transition with loop compatibility

## Resilience & Bug Prevention

### Stale Dimensions After Hide/Show (THE BIG ONE)

The most common Swiper positioning bug: the container is hidden (`display:none` or jQuery `.hide()`), then re-shown. Swiper's internal slide positions are now stale because it computed them while the container had zero dimensions. Calling `slideTo()` with stale positions causes visual offset/jank.

**Root cause**: Swiper is initialized once, but the container is hidden and re-shown without calling `update()`.

**Fix — three-part defense**:

1. **Config-level auto-detection** (handles most cases):
```javascript
new Swiper(el, {
    observer: true,              // watch for DOM changes inside swiper
    observeParents: true,        // watch for parent element show/hide/resize
    observeSlideChildren: true,  // watch for content changes in slides
    watchSlidesProgress: true,   // better slide position tracking
    resistance: true,            // prevent overscroll jank
});
```

2. **Force `update()` before every `slideTo()`** — guarantees fresh dimensions:
```javascript
function navigateToArticle(articleId) {
    if (!swiper) return;
    swiper.update();  // ALWAYS call before navigating
    var slides = swiper.slides;
    for (var i = 0; i < slides.length; i++) {
        var art = slides[i].querySelector('article');
        if (art && art.id === articleId) {
            swiper.slideTo(i);
            return;
        }
    }
}
```

3. **Show BEFORE navigating** — `update()` needs the container to be visible:
```javascript
// WRONG: navigateToArticle(targetId); $main.show();
// RIGHT:
$main.show();
navigateToArticle(targetId);  // update() now sees real dimensions
```

### Double Swiper Initialization

When a fallback script (e.g., `home-swiper.js`) also creates a Swiper on the same element, two instances fight for control — causing erratic behavior.

**Fix**: The primary init sets a flag; the fallback checks it:
```javascript
// In primary init (main.js):
swiper = new Swiper(el, { ... });
el.setAttribute('data-swiper-ready', '1');

// In fallback (home-swiper.js):
var mainEl = document.getElementById('main');
if (mainEl && mainEl.hasAttribute('data-swiper-ready')) return;
```

### GPU Acceleration for Smooth Swipes

Promote Swiper slides to their own compositor layer for 60fps:
```css
.home-swiper .swiper-slide {
  will-change: transform;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
}

.home-swiper .swiper-wrapper {
  transition-timing-function: cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

/* Anti-aliasing for text during rapid swipes */
.home-swiper .swiper-slide article.card * {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

### Spacing: spaceBetween vs CSS margins

- Use `spaceBetween` in Swiper config for **horizontal** gap between slides when `slidesPerView > 1`
- Use CSS custom properties (`--sm-card-margin-y`) for **vertical** breathing room — add them via breakpoints:
```css
:root { --sm-card-margin-y: 3.5rem; }
@media (max-width: 1024px) { :root { --sm-card-margin-y: 2.5rem; } }
@media (max-width: 768px)  { :root { --sm-card-margin-y: 2rem; } }
@media (max-width: 480px)  { :root { --sm-card-margin-y: 1.5rem; } }
```
- On `slidesPerView: 1` (mobile), keep `spaceBetween: 0` to avoid horizontal overflow — the card's own `margin` handles vertical spacing.

## CSS Pitfalls

### Pseudo-element z-index vs Navigation Buttons

When slides have `::before`/`::after` pseudo-elements for visual effects (gradients, overlays), they sit within the slide's stacking context. If their `z-index` is equal to or higher than the Swiper navigation buttons, the pseudo-elements block clicks — even with `pointer-events: none` in some rendering scenarios.

**Correct layering** (ascending z-index):
- `z-index: 5` — slide `::before`/`::after` pseudo-elements (decorative only)
- `z-index: 15` — `.swiper-pagination` dots
- `z-index: 20` — `.swiper-button-prev` / `.swiper-button-next` (must be clickable)

**Required properties on navigation buttons** to guarantee clickability:
```css
.swiper-button-next,
.swiper-button-prev {
    z-index: 20 !important;
    pointer-events: auto !important;
    cursor: pointer !important;
}
```

**Required properties on decorative pseudo-elements**:
```css
.swiper-slide::before,
.swiper-slide::after {
    z-index: 5;                  /* below buttons */
    pointer-events: none !important;  /* never capture clicks */
    /* use top/bottom/width, NOT inset:0 — keep the zone limited */
    top: 0; bottom: 0;
    width: 28px;                 /* narrow strips, not full slide */
}
```

**Pitfall**: Using `inset: 0` on the pseudo-element makes it cover the entire slide, guaranteeing it will overlap buttons regardless of z-index on narrow viewports. Always use `top`/`bottom` + `width` + `left`/`right` to limit the hit area.

### CSS Variable Indirection for Swiper Buttons

When unifying Swiper navigation buttons with in-card buttons (`.card-home-btn`, `.next`), avoid creating alias variables (`--sm-swiper-nav-size: var(--sm-nav-size)`) that add an indirection layer with no benefit. Use the same root variables directly so both button types read from a single source of truth.

**Anti-pattern** (unnecessary indirection):
```css
:root {
    --sm-swiper-nav-size: var(--sm-nav-size);
    --sm-swiper-nav-bg: var(--sm-nav-bg);
    /* ... */
}
.home-swiper .swiper-button-prev {
    width: var(--sm-swiper-nav-size);  /* one hop */
}
```

**Correct pattern** (direct):
```css
:root {
    --sm-nav-size: 3.25rem;
    --sm-nav-bg: #284543;
    /* ... */
}
/* Both read from the same tokens */
.card-home-btn { width: var(--sm-nav-size); }
.home-swiper .swiper-button-prev { width: var(--sm-nav-size); }
```

### Hardcoded Pixel Values in Media Queries

When a media query overrides Swiper button dimensions with hardcoded `px` values, it breaks the responsive variable chain. Always use the CSS custom property even inside `@media`:

```css
/* WRONG — breaks variable chain */
@media (max-width: 320px) {
    .swiper-button-prev, .swiper-button-next {
        width: 28px !important;
    }
}
/* RIGHT — honors the design token */
@media (max-width: 320px) {
    .swiper-button-prev, .swiper-button-next {
        width: var(--sm-nav-size) !important;  /* 2.5rem at this BP */
    }
}
```

### Button Size Override via Min-Width/Min-Height

Global accessibility rules (e.g., `button { min-width: 44px; min-height: 44px; }`) can inflate Swiper nav buttons beyond their intended circular size. Reset these so the CSS custom property controls dimensions:

```css
.home-swiper .swiper-button-prev,
.home-swiper .swiper-button-next {
    width: var(--sm-nav-size) !important;
    height: var(--sm-nav-size) !important;
    min-width: 0 !important;
    min-height: 0 !important;
    border-radius: 50% !important;  /* circles */
    padding: 0 !important;           /* no internal offset */
}
```