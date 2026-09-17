# SEO Quick-Fix Code Snippets (Yoast + WordPress)

Patterns applied to searching-murphy.com — tested and verified.

## 1. Force index,follow on all public pages

```php
// functions.php
add_filter( 'wpseo_robots', function( $robots ) {
    if ( is_singular() || is_page() || is_category() || is_tag() ) {
        return 'index,follow';
    }
    return $robots;
});
```

## 2. Custom titles and meta descriptions for categories

```php
// functions.php — fallback if Yoast field is empty
add_filter( 'wpseo_title', function( $title ) {
    if ( is_category( 'wordpress' ) && false === strpos( $title, 'Blog' ) ) {
        return 'Blog WordPress — Conseils création de site à Caen | Searching Murphy';
    }
    return $title;
});
add_filter( 'wpseo_metadesc', function( $desc ) {
    if ( $desc ) { return $desc; } // Yoast priority if filled
    if ( is_category( 'wordpress' ) ) {
        return 'Tutoriels et conseils WordPress...';
    }
    return $desc;
});
```

## 3. Force sitemap to include all content types

```php
add_filter( 'wpseo_sitemap_exclude_post_type', '__return_false' );
add_filter( 'wpseo_sitemap_exclude_taxonomy', '__return_false' );
add_filter( 'wpseo_sitemap_exclude_author', '__return_true' );
```

## 4. robots.txt — block URL parameters that create duplicates

```
User-agent: *
Allow: /
Disallow: /*?PageSpeed=
Disallow: /*?replytocom=
Disallow: /*?srsltid=
Sitemap: https://example.com/sitemap_index.xml
```

## 5. .htaccess — 301 redirect parameter URLs to clean version

```apache
<IfModule mod_rewrite.c>
    RewriteCond %{QUERY_STRING} ^PageSpeed=noscript$ [NC,OR]
    RewriteCond %{QUERY_STRING} ^replytocom=\d+$ [NC,OR]
    RewriteCond %{QUERY_STRING} ^srsltid= [NC]
    RewriteRule ^(.*)$ /$1? [R=301,L]
</IfModule>
```

## 6. Hidden H1 for single-page apps (screen-reader only)

```css
.sr-only {
    position: absolute !important;
    width: 1px !important;
    height: 1px !important;
    padding: 0 !important;
    margin: -1px !important;
    overflow: hidden !important;
    clip: rect(0,0,0,0) !important;
    white-space: nowrap !important;
    border: 0 !important;
}
```

```html
<h1 class="sr-only">Thomas Leroyer — Développeur WordPress, photographe à Caen</h1>
```

## 7. Google Search Console — post-deployment steps

1. Submit `sitemap_index.xml` in Search Console → Sitemaps
2. Configure URL Parameters: set `PageSpeed`, `replytocom`, `srsltid` as "Does not represent different content"
3. Request re-indexing of previously excluded URLs
4. Verify no duplicate titles remain (Yoast → Titles & Metas → check each page)
