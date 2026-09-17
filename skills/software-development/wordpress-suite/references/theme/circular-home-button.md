# Circular Home Button — .cat-wp-home-btn / .devis-home-btn

Pattern for the yellow circular home button used on Searching-Murphy cards
and the `/devis-automatique/` page. Replaces the old Font Awesome `.card-home-btn`.

## HTML Markup

```html
<a href="<?php echo esc_url( home_url( '/' ) ); ?>" class="devis-home-btn cat-wp-home-btn" title="Retour à l'accueil" aria-label="Retour à l'accueil">
  <svg class="devis-home-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
    <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z"></path>
    <polyline points="9 22 9 12 15 12 15 22"></polyline>
  </svg>
  <span class="devis-home-label">Accueil</span>
</a>
```

Key rules:
- Both classes (`devis-home-btn` + `cat-wp-home-btn`) are applied for shared styling
- `<span class="devis-home-label">` is hidden by default (icon only)
- `aria-label="Retour à l'accueil"` required for accessibility
- SVG uses `stroke="currentColor"` — inherits from parent `color`

## CSS (final version, theme-cards.css §14)

### Default (mobile, all screens)
- Circular: `width: 48px; height: 48px; border-radius: 50%`
- Yellow background: `background-color: #fdc502`
- Dark icon: `color: #1b1f22`
- Icon centered via flexbox `justify-content: center`
- Label hidden: `.devis-home-label { display: none }`

### Active / click state
```css
.cat-wp-home-btn:active,
.devis-home-btn:active {
  background-color: #ffd84d;  /* bright yellow — THIS IS REQUIRED */
  transform: translateY(-1px) scale(0.995);
}
```

### Hover (pointer devices)
- Lift: `translateY(-4px) scale(1.03)`
- Shadow deepen: `box-shadow: 0 10px 30px rgba(0,0,0,0.28)`
- Icon animation: `rotate(-6deg) scale(1.03)`

### Desktop ≥900px — pill conversion
- `width: auto; height: auto; border-radius: 12px`
- Gradient green: `linear-gradient(180deg, #2C6B63 0%, #244E48 100%)`
- White icon + label
- Label visible: `display: inline-block`

### Accessibility
- `prefers-reduced-motion: reduce` → all transitions/transforms off
- Focus: `outline: 3px solid rgba(29,161,242,0.18); outline-offset: 3px`
- `aria-label` on anchor

## Pitfalls

### DO NOT show label by default
The label `.devis-home-label` must be `display: none` by default.
The user explicitly wants icon-only on mobile. Label appears only on desktop ≥900px.

### DO NOT forget the active state
`:active` must set `background-color: #ffd84d`. Without this the button
does not visually respond to clicks/taps — the user will report it as "cassé".

### DO NOT use `background-color` transition slower than 0.12s
The active state needs fast visual feedback. `transition: background-color 0.12s ease`
is the right speed. 0.25s is too slow for click feedback.

### "Retire les boutons" — check if it's a style fix, not a removal
When the user says something like "retire les boutons d'accueil" after the button
was just styled, they may be reacting to a broken button (wrong size, label showing,
missing active state). Before removing markup, check:
1. Is the button rendering correctly? (circular, icon-only, yellow active)
2. Is the label accidentally visible?
3. Is the active state missing?

Often the fix is CSS, not markup removal. Confirm with the user before deleting.

### card-home-btn legacy
The old `.card-home-btn` (Font Awesome `<i class="fas fa-home">`) is styled
in theme-cards.css §9 (lines 477-513). If that CSS block is still present,
it may conflict with `.devis-home-btn` on the same elements. Ensure no element
has both classes simultaneously.
