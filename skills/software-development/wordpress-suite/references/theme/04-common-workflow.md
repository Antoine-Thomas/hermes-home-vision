<!-- Source: wordpress-theme/SKILL.md · section 'Common Workflow' -->

## Common Workflow

### 1. Backup
```bash
cp wp-content/themes/theme-name/file.ext wp-content/themes/theme-name/file.ext.bak-$(date +%Y%m%d)
```

### 2. Identify the File
- **Global styles**: `style.css`
- **Header**: `header.php`
- **Footer**: `footer.php`
- **Homepage**: `front-page.php`
- **JavaScript**: `js/main.js` or similar
- **Template parts**: `template-parts/` or `inc/`

### 3. Make Changes
- CSS: Add rules at the bottom of `style.css` or within appropriate `@media` queries
- PHP: Use escaping functions, keep inline PHP minimal
- JS: Insert code inside existing initialization functions, maintain brace balance

### 4. Test
- Clear all caching layers (browser, plugin, server)
- Test at 320px, 480px, 768px, 1024px breakpoints
- Check browser console for JS errors
- Verify no PHP warnings (`WP_DEBUG` temporarily if needed)
