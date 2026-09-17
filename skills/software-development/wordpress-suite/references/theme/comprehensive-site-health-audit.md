# Comprehensive WordPress Site Health Audit

A 10-point systematic audit covering more than just SEO or theme code — it checks infrastructure, plugins, content, and configuration holistically. Use this when the user asks for a "full audit" or "site health check" of a WordPress site.

## The 10 Audit Points

| # | Check | Method | What to look for |
|---|-------|--------|------------------|
| 1 | **Site accessibility** | curl HTTP status codes for every URL type (front, single post, pillar page, devis/contact) | 200s on all; note response times (<3s good, 3-8s ok, >8s critical) |
| 2 | **Performance** | Check LiteSpeed Cache (is it active? disabled-but-loading?), count enqueued scripts/styles, check image sizes, lazy loading | Disabled plugins must be moved OUT of `plugins/` folder, not just renamed with `_DISABLED` suffix — PHP autoloader still finds them. Count `src="*.js"` in rendered HTML — >10 is heavy |
| 3 | **Missing images** | Crawl all posts/pages via REST API (`/wp-json/wp/v2/posts`) and check all `<img src>` URLs | Check file existence in `wp-content/uploads/`. Check `featured_media` field (0 = no featured image). Check if 16/17 articles reuse the same broken image |
| 4 | **Swiper / JS conflicts** | Verify article-swiper.js has early return guard (`#intro`/`#code`). Verify single.php has no Swiper wrapper classes | Check both PHP enqueue condition AND JS DOM guard — double protection |
| 5 | **PHP errors** | Check `wp-content/debug.log`, `logs/php/error.log`, `logs/nginx/error.log` | Warning: Imagick version mismatch is non-blocking. Fatal: `Uncaught Error: Call to undefined function` needs fixing. Warnings from disabled plugins still firing indicate incomplete deactivation |
| 6 | **Database** | Check DB tables, transients, options (requires wp-cli or direct MySQL) | Expired transients, autoloaded options, large revision tables, wp-options bloat |
| 7 | **SEO / Yoast** | Check schema output in HTML, check Yoast breadcrumbs, check FAQ/HowTo blocks | Empty schema blocks (`<p class="schema-faq-answer"></p>`) hurt SEO. Unique meta descriptions per page? |
| 8 | **Internal links to Devis/Contact** | Scan all post content for links to `/devis-automatique/` and `/contact/` | Every article should link to at least one conversion page |
| 9 | **Menu structure** | Check rendered HTML for `<nav>` content. Check `header.php` for wp_nav_menu vs hardcoded. Check wp-admin menu assignment | Empty `<nav></nav>` = menu not assigned to location. Hardcoded menus need manual updating when pages change |
| 10 | **llms.txt / llms-full.txt** | Check at site root (`/llms.txt`). Should exist for AI-training crawlers | Format: service links, about section, contact info. If missing, create with standard structure |

## Infrastructure Checks (when site is slow)

When response times exceed 8 seconds, the problem is usually not theme code but the local dev stack:

1. **LiteSpeed Cache partially disabled** — a plugin folder renamed `_DISABLED` but still inside `plugins/` will be loaded by WordPress's plugin autoloader. Move it OUT of `plugins/` entirely (e.g. to `plugins-disabled/` at same level).

2. **getimagesize() on broken image URLs** — LiteSpeed's Media optimizer calls `getimagesize()` on every `<img src>` at shutdown. If the image 404s, it tries HTTP fetch which times out (30s+). Fix: remove the plugin OR make the image exist.

3. **PHP-FPM pool exhaustion** — Local by Flywheel often uses tiny PHP-FPM pools. Check `logs/nginx/error.log` for "no live upstreams" or "WSARecv() failed" — these indicate PHP workers dying under load.

4. **MySQL port conflicts** — Local uses ports 10002-10005, not 3306. The bundled `mysql.exe` under Local's `lightning-services/` directory can connect directly on those ports.

## WP-CLI Fallback Strategy

When wp-cli is unavailable (common on Local by Flywheel Windows):
- Use **REST API** (`/wp-json/wp/v2/posts?per_page=100&_fields=id,title,slug,content,featured_media`) for content queries
- Use **direct MySQL** via Local's bundled `mysql.exe` (in `AppData/Roaming/Local/lightning-services/mariadb-10.6.23+0/bin/win32/bin/mysql.exe` or similar)
- Use **PHP scripts** that `require 'wp-load.php'` and run with the server's PHP binary

## Cross-Platform Path Rules (Windows)

- In **terminal tool** (`bash/git-bash`): use `/c/Users/...` (POSIX-style)
- In **write_file / patch / read_file tools**: use `C:\Users\...` (native Windows) — `/c/Users/...` resolves to `C:\c\Users\...` and writes to a wrong location
- Always check `resolved_path` in tool output to verify file landed correctly
