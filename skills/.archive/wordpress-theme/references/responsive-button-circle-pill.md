# Responsive Button: Circle → Pill Pattern

CSS-only responsive button that transitions from a compact circle (icon only) on mobile to a pill shape (icon + label) on desktop. No JavaScript required.

## When to Use

- Home/back buttons on card-based layouts
- Navigation controls that need to be compact on mobile but informative on desktop
- Any button where label text would overflow on small screens

## Pattern

```css
/* ── Mobile-first: circle, icon only ── */
.cat-wp-home-btn,
.my-responsive-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  padding: 0;
  border-radius: 50%;
  background-color: #fdc502;        /* accent color */
  color: #1b1f22;
  text-decoration: none;
  box-shadow: 0 4px 14px rgba(0,0,0,0.25);
  transition: transform 0.25s ease, background-color 0.25s ease, box-shadow 0.25s ease;
  border: none;
  font-weight: 600;
  -webkit-tap-highlight-color: transparent;
}

/* Icon: centered, inherits color */
.my-responsive-btn .my-btn-icon {
  display: inline-block;
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  color: inherit;
  transform-origin: center;
  transition: transform 180ms cubic-bezier(.2,.9,.2,1);
}

/* Label: hidden on mobile */
.my-responsive-btn .my-btn-label {
  display: none;
  margin-left: 8px;
  font-size: 14px;
  font-weight: 600;
  color: inherit;
}

/* ── Hover (desktop pointer only) ── */
@media (hover: hover) and (pointer: fine) {
  .my-responsive-btn:hover {
    transform: translateY(-4px) scale(1.03);
    box-shadow: 0 10px 30px rgba(0,0,0,0.28);
  }
  .my-responsive-btn:active {
    transform: translateY(-1px) scale(0.995);
  }
}

/* ── Focus ── */
.my-responsive-btn:focus {
  outline: 3px solid rgba(29,161,242,0.18);
  outline-offset: 3px;
}

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .my-responsive-btn {
    transition: none !important;
    transform: none !important;
  }
}

/* ── Desktop (≥900px): pill shape, icon + label ── */
@media (min-width: 900px) {
  .my-responsive-btn .my-btn-label {
    display: inline-block;
  }
  .my-responsive-btn {
    width: auto;
    height: auto;
    padding: 10px 14px;
    border-radius: 12px;
    gap: 10px;
    background: linear-gradient(180deg, #2C6B63 0%, #244E48 100%);
    color: #fff;
    box-shadow: 0 8px 20px rgba(36,78,72,0.14);
  }
  .my-responsive-btn .my-btn-icon {
    color: #fff;
  }
  .my-responsive-btn .my-btn-label {
    color: #fff;
  }
}
```

## HTML

```html
<a href="/" class="my-responsive-btn" title="Retour à l'accueil" aria-label="Retour à l'accueil">
  <svg class="my-btn-icon" width="20" height="20" viewBox="0 0 24 24" fill="none"
       stroke="currentColor" stroke-width="2.5" stroke-linecap="round"
       stroke-linejoin="round" aria-hidden="true" focusable="false">
    <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z"></path>
    <polyline points="9 22 9 12 15 12 15 22"></polyline>
  </svg>
  <span class="my-btn-label">Accueil</span>
</a>
```

## Key points

- **Mobile-first**: `border-radius:50%` + fixed `width/height` → perfect circle
- **Label hidden by default**: `display:none` on the label span
- **Desktop breakpoint**: `@media (min-width: 900px)` → `width:auto`, `border-radius:12px`, label `display:inline-block`
- **Accessibility**: `aria-label` on the anchor ensures screen readers always get the text, even when the visual label is hidden
- **SVG inline**: `stroke="currentColor"` inherits text color — one color change propagates everywhere
- **Classes can be shared** across button variants (`.cat-wp-home-btn`, `.devis-home-btn`) for visual consistency

## Pitfalls

- **Breakpoint value**: 900px is chosen for this project's card layout. Adjust based on when your cards have enough horizontal space for the pill shape.
- **Don't use `font-size:0` to hide text**: screen readers respect `display:none` on the label span correctly because the `aria-label` on the parent anchor provides the accessible name.
- **SVG dimensions**: keep `width/height` attributes on the `<svg>` element for anti-CLS. The CSS `width/height` on the icon class provides the layout size.
