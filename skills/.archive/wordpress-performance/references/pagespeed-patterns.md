# PageSpeed / Lighthouse Patterns — Full Code

Concrete PHP and Apache config snippets for each pattern in the wordpress-performance skill. Copy-paste ready with minimal adaptation needed.

---

## Pattern 1: Critical CSS Inline

Inject in `functions.php` inside the existing `wp_head` hook at priority 1. Include ONLY styles for the initial viewport: :root variables, body, header/logo/nav, LCP image container, fixed overlays. Keep under 2KB.

```php
add_action( 'wp_head', function() {
    // ... existing preconnects and dns-prefetches ...

    echo '<style id="critical-css">';
    echo ':root{--sm-font:"Source Sans Pro",system-ui,sans-serif;--sm-bg:#cbe8e8;--bg:var(--sm-bg)}';
    echo '*,*::before,*::after{box-sizing:border-box}';
    echo 'body{margin:0;font-family:var(--sm-font);background:var(--bg);line-height:1.6}';
    echo '#wrapper{display:flex;flex-direction:column;min-height:100vh;width:100%;z-index:3}';
    echo '#header{position:fixed;top:0;left:0;width:100%;height:88vh!important;z-index:100!important;background-color:#cbe8e8;display:flex;flex-direction:column;align-items:center;justify-content:center}';
    echo '#header .logo{width:6rem;height:6rem;border-radius:50%;overflow:hidden}';
    echo '#header .logo img{width:100%;height:100%;object-fit:cover}';
    echo '#header .content .inner img{max-width:100%;height:auto;display:block}';
    echo '#header nav ul{display:flex;flex-wrap:wrap;justify-content:center;list-style:none;padding:0;margin:0;gap:.5rem}';
    echo '#header nav ul li a{display:inline-block;padding:.4rem .8rem;font-size:.8rem;color:#284543;text-decoration:none}';
    echo '#bg-canvas{position:fixed!important;top:0!important;left:0!important;width:100%!important;height:100%!important;z-index:9999!important;pointer-events:none!important}';
    echo '#footer{width:100%;text-align:center;flex-shrink:0;padding:.5rem 0;font-size:.5rem}';
    echo '</style>' . "\n";
}, 1 );
```

**How to build critical CSS:** Read the existing style.css. Extract only rules that affect elements in the initial viewport. Minify to single-line echo statements. Test: the page should look correct above the fold even with the full stylesheet blocked.

**Critical CSS scope — what MUST be covered to prevent CLS:**
- `:root` design tokens (every variable used by above-fold elements)
- Body, wrapper, header, logo, navigation
- Swiper container + slides + card articles (if page uses Swiper)
- Card images (with explicit dimensions)
- Navigation buttons (`.card-home-btn`, `.next` — width/height/position)
- Heading sizes (h1-h3) to prevent font-swap layout shift
- Canvas background (#bg-canvas), footer
- State transitions (`body.is-article-visible #header`)
- Responsive breakpoints (@media 736px, @media 480px)

**If CLS rises after optimization:** the critical CSS does not cover enough elements. The full stylesheet loads late and changes something that was already painted. Add the missing rules to the critical CSS block — don't revert to blocking stylesheets.

---

## Pattern 2: Non-Blocking CSS Filter

Extend the `style_loader_tag` filter to transform render-blocking link tags:

```php
add_filter( 'style_loader_tag', function( $tag, $handle ) {
    // Keep existing Google Fonts display=swap logic here...

    $non_blocking_handles = array(
        'astra-parent',           // parent theme CSS
        'searching-murphy-style', // child theme CSS (the big one)
        'font-awesome',           // icon font CSS
        'swiper-css',             // slider CSS
    );
    if ( in_array( $handle, $non_blocking_handles, true ) ) {
        if ( false !== strpos( $tag, 'media=' ) ) {
            $tag = preg_replace(
                '/media=["\'][^"\']+["\']/',
                'media="print" onload="this.media=\'all\'"',
                $tag
            );
        } else {
            $tag = str_replace(
                "rel='stylesheet'",
                "rel='stylesheet' media='print' onload=\"this.media='all'\"",
                $tag
            );
        }
        // noscript fallback for users with JS disabled
        $fallback = str_replace(
            "media='print' onload=\"this.media='all'\"",
            "media='all'",
            $tag
        );
        $tag .= '<noscript>' . $fallback . '</noscript>';
    }
    return $tag;
}, 10, 2 );
```

---

## Pattern 3: LCP Image Preload

Add in `header.php` right after `wp_head()`. Identify the LCP element from the PageSpeed report's "Repartition du LCP" section.

```html
<meta name="viewport" content="width=device-width, initial-scale=1">
<?php wp_head(); ?>

<link rel="preload" as="image" href="/wp-content/uploads/2025/02/Fondcarte.webp" fetchpriority="high">
```

Also add `fetchpriority="high"` to the corresponding `<img>` tag in the template:

```html
<img src="/wp-content/uploads/2025/02/Fondcarte.webp" fetchpriority="high" width="240" height="114" alt="...">
```

---

## Pattern 4: WordPress Core Bloat Removal

```php
// Remove jQuery Migrate (not needed for modern themes/browsers)
add_action( 'wp_default_scripts', function( $scripts ) {
    if ( ! is_admin() && isset( $scripts->registered['jquery'] ) ) {
        $scripts->registered['jquery']->deps = array_diff(
            $scripts->registered['jquery']->deps,
            array( 'jquery-migrate' )
        );
    }
});

// Disable wp-emoji (saves ~15KB JS + CSS, removes extra DNS prefetch)
remove_action( 'wp_head', 'print_emoji_detection_script', 7 );
remove_action( 'wp_print_styles', 'print_emoji_styles' );
remove_action( 'admin_print_scripts', 'print_emoji_detection_script' );
remove_action( 'admin_print_styles', 'print_emoji_styles' );
```

---

## Pattern 5: Font Preloading

Preload the primary web font stylesheet and the most-used icon font weight. Use priority 2 so it fires after preconnects (priority 1) but before stylesheet enqueues.

```php
add_action( 'wp_head', function() {
    echo '<link rel="preload" as="style" href="https://fonts.googleapis.com/css?family=Source+Sans+Pro:400,600,700&display=swap">' . "\n";
    echo '<link rel="preload" as="font" type="font/woff2" crossorigin href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/webfonts/fa-solid-900.woff2">' . "\n";
}, 2 );
```

**Important:** The Font Awesome preload URL must match the version loaded by the CSS. When upgrading Font Awesome, update both the CSS enqueue AND this preload URL.

---

## Pattern 6: Cache Headers (.htaccess)

Replace the existing cache block in `.htaccess`:

```apache
# Cache longue duree pour les assets statiques
<IfModule mod_expires.c>
    ExpiresActive On
    ExpiresByType text/css "access plus 1 year"
    ExpiresByType text/javascript "access plus 1 year"
    ExpiresByType application/javascript "access plus 1 year"
    ExpiresByType image/webp "access plus 1 year"
    ExpiresByType image/png "access plus 1 year"
    ExpiresByType image/jpeg "access plus 1 year"
    ExpiresByType image/svg+xml "access plus 1 year"
    ExpiresByType image/gif "access plus 1 year"
    ExpiresByType image/x-icon "access plus 1 year"
    ExpiresByType font/woff2 "access plus 1 year"
    ExpiresByType font/woff "access plus 1 year"
    ExpiresByType application/font-woff2 "access plus 1 year"
    ExpiresByType application/font-woff "access plus 1 year"
</IfModule>

# Cache-Control immutable evite les requetes 304 de revalidation
<IfModule mod_headers.c>
    <FilesMatch "\.(css|js|webp|png|jpg|jpeg|gif|svg|ico|woff2?)$">
        Header append Cache-Control "public, immutable"
    </FilesMatch>
</IfModule>
```

---

## Pattern 7: Script Deferral

Verify all theme scripts have `defer` and third-party scripts have `async`:

```php
add_filter( 'script_loader_tag', function( $tag, $handle ) {
    $defer_handles = array(
        'jquery', 'swiper-js', 'searching-murphy-util',
        'searching-murphy-main', 'searching-murphy-article-swiper',
        'tracking-events',
    );
    $async_handles = array(
        'adsbygoogle', 'searching-murphy-adsense',
    );
    if ( in_array( $handle, $defer_handles, true ) ) {
        return str_replace( ' src', ' defer src', $tag );
    }
    if ( in_array( $handle, $async_handles, true ) ) {
        return str_replace( ' src', ' async src', $tag );
    }
    return $tag;
}, 10, 2 );
```

---

## Full Session Example

A real session applying all patterns to a WordPress site with a Performance score of 54, FCP 7.1s, LCP 12.8s:

1. Analyzed functions.php: 253KB style.css render-blocking, Font Awesome from CDN, jQuery Migrate loaded
2. Injected ~1.5KB critical CSS covering :root, body, header, logo, nav, canvas, footer
3. Added non-blocking filter for 4 stylesheets (astra-parent, child, font-awesome, swiper-css)
4. Preloaded LCP image (Fondcarte.webp) in header.php with fetchpriority=high
5. Removed jQuery Migrate dependency + wp-emoji hooks
6. Preloaded Google Fonts stylesheet + fa-solid-900.woff2
7. Extended .htaccess cache from 1 month to 1 year + immutable headers
8. Expected result: FCP 2-3s (from 7.1s), LCP 3-5s (from 12.8s), Performance 75-85 (from 54)

Three files modified: functions.php, header.php, .htaccess. No new plugins installed, no parent theme edited.
