# Standalone JS Module — Anti-Duplication Pattern

Pattern for creating a zero-dependency JavaScript module that can coexist safely with an integrated version of the same logic in another file (e.g., extracting a feature from a large monolith into a standalone file).

## When to Use

- Extracting a feature from a large JS file (e.g., `theme-cards.js`) into a standalone module
- The original file still contains the logic — you're adding a parallel version, not replacing
- You need the standalone module to work both WITH and WITHOUT the original file loaded
- Preventing double-injection of DOM elements (images, buttons, wrappers)

## The Pattern

```javascript
(function () {
  'use strict';

  /* --- Guard 1: Feature detection — skip if already handled ----------------- */
  // If the integrated version already ran, don't duplicate
  // This is the KEY anti-duplication check
  var existingElements = document.querySelectorAll('.my-injected-element');
  if (existingElements.length > 0) { return; }

  /* --- Guard 2: MatchMedia for responsive features -------------------------- */
  var mq = window.matchMedia ? window.matchMedia('(max-width: 420px)') : null;
  if (!mq) { return; }

  /* --- Guard 3: Required DOM elements present ------------------------------- */
  var containers = document.querySelectorAll('.target-container');
  if (!containers.length) { return; }

  /* --- Core logic: inject/remove based on media query ----------------------- */
  var IMG_SRC = (function () {
    // Priority 1: wp_localize_script URL (survives cache/min/CDN rewrites)
    if (window.MY_NAMESPACE && window.MY_NAMESPACE.assetUrl) {
      return window.MY_NAMESPACE.assetUrl;
    }
    // Priority 2: derive from currentScript.src
    var self = document.currentScript && document.currentScript.src;
    if (self) { return self.replace(/js\/[^/]+\.js(\?.*)?$/, 'img/asset.svg'); }
    // Priority 3: DOM lookup by script src pattern
    var base = document.querySelector('script[src*="my-module-name"]');
    if (base) {
      var s = base.getAttribute('src');
      return s.replace(/js\/[^/]+\.js(\?.*)?$/, 'img/asset.svg');
    }
    return null;
  })();

  function apply() {
    Array.prototype.forEach.call(containers, function (container) {
      var existing = container.querySelector('.my-injected-element');
      if (mq.matches) {
        if (!existing) {
          var el = document.createElement('img');
          el.className = 'my-injected-element';
          el.src = IMG_SRC;
          el.alt = '';
          el.setAttribute('aria-hidden', 'true');
          el.decoding = 'async';
          // Set explicit dimensions to prevent CLS
          el.width = 48;
          el.height = 48;
          container.appendChild(el);
        }
      } else if (existing && existing.parentNode) {
        existing.parentNode.removeChild(existing);
      }
    });
  }

  /* --- Init: DOMContentLoaded or immediate if ready ------------------------- */
  function init() {
    apply();
    if (mq.addEventListener) {
      mq.addEventListener('change', apply);
    } else if (mq.addListener) {
      mq.addListener(apply); // Safari < 14
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

## Key Design Decisions

1. **Anti-duplication check FIRST** — before any DOM manipulation, check if elements already exist. This is the contract that allows standalone and integrated versions to coexist.

2. **Self-resolving asset paths with cache/min survival** — derive image/CSS paths from `document.currentScript.src` as fallback, but ALWAYS try `window.MY_NAMESPACE.assetUrl` first (set via `wp_localize_script` in PHP). The `currentScript.src` derivation breaks when WP Rocket / LiteSpeed Cache / W3 Total Cache rewrites the script URL to `/wp-content/cache/min/1/...`. The localized variable is the only reliable path.

3. **MatchMedia with addListener fallback** — Safari < 14 doesn't support `addEventListener` on MediaQueryList; use `addListener` as fallback.

4. **DOMContentLoaded + readyState guard** — script loaded via `defer` may execute after DOM is ready; check `document.readyState`.

5. **Explicit dimensions on injected images** — set `width`/`height` on injected `<img>` elements to prevent Cumulative Layout Shift (CLS).

## PHP Enqueue Pattern (WordPress)

```php
// In functions.php, inside wp_enqueue_scripts action:
if ( is_front_page() ) {
    $mef_js = get_stylesheet_directory() . '/assets/js/mobile-eye-fallback.js';
    if ( file_exists( $mef_js ) ) {
        wp_enqueue_script(
            'searching-murphy-mobile-eye-fallback',
            get_stylesheet_directory_uri() . '/assets/js/mobile-eye-fallback.js',
            array(),      // standalone: zero dependencies
            _S_VERSION,
            true          // footer
        );
    }
}

// In script_loader_tag filter, add to defer_handles:
'searching-murphy-mobile-eye-fallback',
```

## Pitfalls

- **Forgetting the anti-duplication check** — without `if (existing.length) return`, both the integrated and standalone versions inject elements, causing duplicates.
- **Hardcoding asset paths** — breaks when the theme directory changes. Always derive from `currentScript.src` as fallback, with `wp_localize_script` URL as priority 1.
- **Relying solely on `currentScript.src` for asset paths** — produces 404s when cache/minification plugins (WP Rocket, LiteSpeed Cache, W3 Total Cache) rewrite the script URL to `/wp-content/cache/min/1/...`. The minified SVG/image path does not exist in the cache directory. Always inject the true URL via `wp_localize_script()` in PHP as the primary source.
- **Missing `wp_localize_script` in PHP** — for every JS module that derives asset paths, add in `functions.php` after the enqueue:
```php
wp_localize_script( 'my-script-handle', 'MY_NAMESPACE', array(
    'assetUrl' => get_stylesheet_directory_uri() . '/assets/img/my-icon.svg',
));
```
- **Safari < 14 addEventListener on MediaQueryList** — fails silently. Always include `addListener` fallback.
- **No dimensions on injected images** — causes CLS. Always set `width`/`height`.
- **Skipping `aria-hidden`** — injected decorative images should be hidden from screen readers.
