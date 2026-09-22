# WordPress Backdoor Scan — Quick Reference

## One-liner scan (run from WordPress root)

```bash
# Scan for hidden admin backdoors
grep -rn --include="*.php" "HIDDEN_USER_1\|wp-system\|16hayden-boyle\|vc8HfXLUynYU\|chr(104).chr(116)" wp-content/mu-plugins/ wp-content/plugins/ wp-content/themes/

# Scan for eval/base64 obfuscation
grep -rn --include="*.php" -l "eval(\|base64_decode\|gzinflate\|str_rot13" wp-content/mu-plugins/

# Check wp-config and .htaccess
grep -n "HIDDEN_USER_1\|eval(\|base64_decode" wp-config.php .htaccess
```

## Files confirmed as backdoors (searching-murphy project)

| File | Size | Date | Pattern |
|------|------|------|---------|
| `mu-plugins/theme-mock.php` | 3530B | 2025-06-10 | `do { } while(false)`, `HIDDEN_USER_1`, `wp_create_user`, credential POST to `16hayden-boyle.eu.cc` |
| `mu-plugins/file-index.php` | 3647B | 2025-06-10 | `try { } catch(\Throwable) {}`, same logic, different variable names |

Both files:
- Create hidden admin `wp-system` with password `vc8HfXLUynYU7e0JHR@`
- Exfiltrate admin credentials to `https://16hayden-boyle.eu.cc/ingest-7f3a9c/aaxa`
- Hide user from admin user list
- Intercept `wp_authenticate` and `wp_login` hooks
