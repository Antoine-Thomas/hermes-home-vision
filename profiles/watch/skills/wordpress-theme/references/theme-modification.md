1|---
2|name: wp-theme-modification
3|description: "Modify WordPress themes safely: editing styles, templates, fixing responsive issues, footer visibility, etc."
4|category: wordpress
5|author: Hermes Agent
6|version: 1.0
7|---
8|
9|# WordPress Theme Modification Skill
10|
11|This skill provides a safe, repeatable workflow for modifying a WordPress child theme (or any theme) while preserving upgradeability and following WordPress coding standards.
12|
13|## When to Use
14|- Adjusting CSS (layout, colors, typography)
15|- Fixing template files (header.php, footer.php, front-page.php, etc.)
16|- Adding responsive breakpoints
17|- Ensuring accessibility and visibility requirements
18|- Making structural changes that should persist across updates (use a child theme)
19|
20|## Prerequisites
21|- A WordPress site with the theme installed and active.
22|- Access to the theme files via FTP, file manager, or local development environment.
23|- Basic understanding of CSS, PHP, and WordPress template hierarchy.
24|- Backup of the theme (or at least the files you plan to edit).
25|
26|## Workflow
27|
28|### 1. Backup
29|Before editing any file, create a backup:
30|```bash
31|# Example for style.css
32|cp wp-content/themes/your-theme/style.css wp-content/themes/your-theme/style.css.bak-$(date +%Y%m%d%H%M%S)
33|```
34|Or use the theme’s built-in backup mechanism if available.
35|
36|### 2. Identify the File to Edit
37|Determine which file controls the element you want to change:
38|- **Global styles**: `style.css`
39|- **Header**: `header.php`
40|- **Footer**: `footer.php`
41|- **Homepage / custom page templates**: `front-page.php`, `page.php`, or custom templates.
42|- **Template parts**: Look in `template-parts/` or `inc/`.
43|
44|### 3. Edit with Child Theme Best Practices
45|If you are editing a parent theme, prefer creating a child theme:
46|1. Create a folder `wp-content/themes/your-theme-child`.
47|2. Add a `style.css` with the required header:
48|   ```css
49|   /*
50|   Theme Name: Your Theme Child
51|   Template: parent-theme-folder-name
52|   */
53|   ```
54|3. Enqueue parent and child stylesheets via `functions.php` (if not already done).
55|4. Copy only the files you need to modify into the child theme folder, preserving the same directory structure.
56|
57|### 4. Making CSS Changes
58|- Use `!important` sparingly—only when necessary to override existing rules.
59|- Prefer adding new rules at the bottom of `style.css` or within appropriate media queries.
60|- For responsive adjustments, use media queries that match the theme’s breakpoints (check `style.css` for existing ones).
61|- Example for forcing footer visibility:
62|  ```css
63|  /* Footer always visible */
64|  #footer { display:block!important; opacity:1!important; visibility:visible!important; }
65|  body.is-article-visible #footer { display:none!important; }
66|  ```
67|
68|### 5. Editing PHP Template Files
69|- Always escape output using WordPress escaping functions (`esc_html()`, `esc_attr()`, `wp_kses_post()`, etc.).
70|- When adding inline PHP, keep it minimal and prefer template tags.
71|- Example safe echo:
72|  ```php
73|  echo esc_html( get_theme_mod( 'setting_name' ) );
74|  ```
75|
76|### 6. Testing
77|After each change:
78|1. Clear any caching layers (browser, plugin, server-side).
79|2. Check the frontend on multiple devices/viewports (use browser dev tools).
80|3. Verify no PHP errors or warnings appear (enable `WP_DEBUG` temporarily if needed).
81|4. Confirm that the change does not break layout on other pages.
82|
83|### 7. Common Pitfalls & Fixes
84|| Symptom | Likely Cause | Fix |
85||---------|--------------|-----|
86|| Changes not appearing | Editing parent theme instead of child theme, or caching | Verify you are editing the active theme; clear caches. |
87|| Layout breaks on mobile | Missing or incorrect media query | Add/adjust `@media` rules; use browser dev tools to inspect breakpoint. |
88|| Footer still hidden on desktop | Specific JS hiding it (e.g., `$footer.hide();`) | Locate JS (often `main.js`) and adjust condition, or override with CSS `!important`. |
89|| PHP syntax error | Missing semicolon, unmatched braces | Check error log; fix syntax. |
90|| Styles overridden by more specific selector | CSS specificity conflict | Increase specificity or use `!important` only as last resort. |
91|
92|### 8. Verification Checklist
93|- [ ] Backup created before edit.
94|- [ ] Changes made in child theme (or backed-up parent theme).
95|- [ ] CSS uses proper escaping and avoids unnecessary `!important`.
96|- [ ] PHP uses escaping functions.
97|- [ ] No console errors (JS) or PHP warnings.
98|- [ ] Responsive behavior tested at common widths (320px, 768px, 1024px).
99|- [ ] Footer visible on desktop, hidden when Swiper/article view active (if applicable).
100|- [ ] All links and buttons functional.
101|
102|## References
103|- WordPress Theme Handbook: https://developer.wordpress.org/themes/
104|- Child Themes: https://developer.wordpress.org/themes/advanced-topics/child-themes/
105|- CSS Specificity: https://developer.mozilla.org/en-US/docs/Web/CSS/Specificity
106|
107|## User Constraints and Preferences
108|
109|- Respect explicit user instructions about which files to modify or avoid (e.g., do not alter `main.js` unless explicitly permitted).
110|- Provide explanations in the user's preferred language (user has used French in this session).
111|- Confirm user preferences before making changes that affect behavior or appearance.
112|- Keep modifications minimal and focused on the requested task; avoid side‑effects.
113|
114|## Related Skills
115|- `wp-security` – for auditing and hardening theme code.
116|- `wp-wpcli-and-ops` – for WP‑CLI based maintenance tasks.
117|