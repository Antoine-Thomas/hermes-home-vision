<!-- Source: wordpress-theme/SKILL.md · section 'Safety First — The Golden Rules' -->

## Safety First — The Golden Rules

1. **Backup before editing.** Always.
2. **Use correct path format on Windows.** In `write_file`/`patch` tools, use `C:\Users\...` (native Windows) — `/c/Users/...` (bash-style) silently resolves to `C:\c\Users\...` which doesn't exist. Always check the tool's `resolved_path` output.
3. **Use a child theme.** Never edit parent theme files directly — updates will overwrite your changes.
3. **Test after every change.** Clear caches, check mobile/desktop, verify behavior.
4. **Escape all PHP output.** Use `esc_html()`, `esc_attr()`, `wp_kses_post()`, etc.
5. **Use `!important` as a last resort** — only when a more specific selector genuinely cannot override a parent-theme rule. Bulk `!important` usage (more than 3-5 in a single change) is a signal that the approach is wrong.
6. **Never rewrite `:root` CSS custom properties** (`--sm-*`, `--primary`, `--card-bg`, etc.) without explicit user permission. These variables control the entire theme's color scheme, spacing, and typography. Changing them is a design-level decision, not a CSS implementation detail.
7. **Respect the existing color scheme.** The theme's accent colors, background colors, and text colors are chosen deliberately. Do not replace them with different colors (e.g., swapping yellow #fdc502 for orange #FF6600) unless the user says precisely which color to change.
