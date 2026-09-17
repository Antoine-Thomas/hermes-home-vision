1|---
2|name: wordpress-theme-optimization
3|description: Audit and optimize WordPress themes for security, performance, SEO, UI/UX, and functionality.
4|---
5|
6|# WordPress Theme Optimization Skill
7|
8|## Description
9|Audit and optimize WordPress themes for security, performance, SEO, UI/UX, and functionality. Provides a systematic approach to reviewing theme code, identifying issues, and applying corrective measures while adhering to WordPress best practices.
10|
11|## Trigger Conditions
12|Use this skill when:
13|- Auditing a WordPress theme for security vulnerabilities (XSS, SQL injection, missing nonces, improper escaping)
14|- Optimizing theme performance (asset loading, caching, render-blocking resources)
15|- Improving SEO (meta tags, structured data, semantic markup)
16|- Enhancing UI/UX (responsive design, visibility of elements, spacing, touch targets)
17|- Verifying theme functionality (JavaScript components, popups, navigation, form handling)
18|- Preparing a theme for production or after significant modifications
19|
20|## Workflow
21|
22|### 1. Security Audit
23|- Check PHP files for direct echo/print of `$_GET`, `$_POST`, `$_REQUEST` without escaping
24|- Verify presence of nonces in forms (`wp_nonce_field()`, `wp_verify_nonce()`)
25|- Ensure input sanitization and validation (using `sanitize_*()`, `esc_*()`, `wp_kses_*()`)
26|- Look for SQL injection risks (avoid raw `$wpdb->query()` with unsanitized input)
27|- Confirm that JavaScript properly escapes dynamic values (if using `wp_add_inline_script`)
28|
29|### 2. Performance Audit
30|- Review `functions.php` for enqueued scripts and styles:
31|  - Identify non-essential external scripts (ads, analytics, social widgets) that may be deferred
32|  - Check for duplicate jQuery or multiple versions of the same library
33|  - Ensure scripts are enqueued in footer where possible (`$in_footer = true`)
34|  - Verify CSS is not excessively fragmented
35|- Assess image optimization: use of `srcset`, `sizes`, lazy loading (`loading="lazy"`)
36|- Check for render-blocking resources in `<head>`
37|- Suggest WP-CLI commands for performance improvements:
38|  - Cache purging: `wp cache flush` (if object cache plugin installed)
39|  - Transient cleanup: `wp transient delete --expired`
40|  - Database optimization: `wp db optimize` (caution on production)
41|
42|### 3. SEO Audit
43|- Confirm theme supports `title-tag` via `add_theme_support('title-tag')`
44|- Check for dynamic meta description (avoid static hardcoded descriptions)
45|  - Prefer using `wp_get_description()` or SEO plugin hooks
46|  - Ensure description is relevant to each page/post type
47|- Verify structured data (JSON-LD) for `LocalBusiness`, `Organization`, `BlogPosting`, etc.
48|  - Typically placed in `footer.php` or via `wp_head` hook
49|- Validate heading structure (H1-H6) used hierarchically and not skipped
50|- Ensure images have meaningful `alt` attributes
51|- Check for proper use of `canonical` URLs (if applicable)
52|
53|### 4. UI/UX Audit
54|- Test responsive breakpoints (320px, 480px, 768px, 1024px) via browser dev tools
55|- Verify footer visibility:
56|  - Footer should be visible by default on all screens
57|  - May be conditionally hidden (e.g., when a Swiper or modal is active) using classes like `.is-article-visible`
58|- Check button spacing and touch targets (minimum 48x48px)
59|- Validate form usability: label association, error messaging, validation
60|- Ensure navigation is accessible (keyboard navigable, ARIA labels where needed)
61|- Confirm color contrast meets WCAG AA standards
62|
63|### 5. Functionality Audit
64|- Test JavaScript-dependent components:
65|  - Swiper sliders: initialization, navigation, pagination, loop mode
66|  - Popups/modals: opening, closing, focus trapping, escape key handling
67|  - AJAX forms: validation, submission, success/error handling
68|  - Navigation: hashchange handling, smooth scrolling, active state updates
69|- Verify that PHP template tags are used correctly (`get_header()`, `get_footer()`, etc.)
70|- Check for template hierarchy adherence
71|- Navigation: hashchange handling, smooth scrolling, active state updates
72|- Verify jQuery selector correctness (e.g., $('selector') not broken/contextless selectors)
73|- Ensure event handler callbacks reference correct objects (e.g., $main._show() not ._show())
74|
75|### 6. Applying Corrections
76|- Use child theme practices: never edit parent theme directly
77|- Apply CSS corrections via `style.css` in child theme, using `!important` sparingly but when necessary to override parent styles
78|- Common CSS corrections:
79|  ```css
80|  /* Footer visibility */
81|  #footer { display:block!important; opacity:1!important; visibility:visible!important; }
82|  body.is-article-visible #footer { display:none!important; }
83|
84|  /* Header compact on small screens */
85|  @media (max-width: 360px) {
86|      #header .logo-link img { width:60%; max-width:80px; }
87|      #header .content .inner img { max-height:130px; }
88|      #header .logo-link, #header .content .inner { margin:0; }
89|      #header nav ul li a { font-size:0.75rem; }
90|  }
91|
92|  /* Article button spacing */
93|  .swiper-slide article .button { margin-bottom:20px!important; }
94|
95|  /* Contact button adjustments */
96|  #contact .button {
97|      width:80% !important;
98|      margin:2px auto 2px auto !important;
99|  }
100|  ```
101|- For functional fixes, modify JavaScript files carefully, ensuring to maintain event delegation and avoid breaking existing functionality
102|- Always test changes across multiple browsers and devices
103|- Keep backups before modifying files
104|
105|## Pitfalls
106|- Overusing `!important` in CSS can lead to specificity wars and maintenance difficulties
107|- Modifying parent theme files directly will cause updates to overwrite changes
108|- Removing nonces or sanitization to "fix" functionality introduces security vulnerabilities
109|- Aggressive script deferral can break dependencies; test thoroughly
110|- Changing structured data incorrectly can cause rich snippet errors in search results
111|- Forgetting to clear caches after changes may result in not seeing updates
112|- Using `display:none` to hide footer may affect accessibility; consider alternative techniques if SEO is concerned
113|- Placing JavaScript code outside the IIFE (after `})(jQuery);`) will break functionality because the code runs outside the scope where theme variables are defined.
114|
115|## Validation
116|After applying changes:
117|- Re-run security checks to ensure no regressions
118|- Test page load performance (using Lighthouse or WebPageTest)
119|- Verify SEO elements with tools like Google's Rich Results Test
120|- Check UI/UX on actual devices or using browser simulator
121|- Confirm functionality: interact with all interactive elements
122|
123|## References
124|- [WordPress Theme Handbook](https://developer.wordpress.org/themes/)
125|- [WordPress Coding Standards](https://developer.wordpress.org/coding-standards/wordpress-coding-standards/)
126|- [WP-CLI Handbook](https://developer.wordpress.org/cli-commands/)
127|- Session-specific reference: `references/searching-murphy-audit.md` (details of audit and corrections applied to searching-murphy theme)
128|
129|## Author
130|Hermes Agent (adapted from session working on searching-murphy theme)