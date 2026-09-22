---
name: wordpress-security
description: "WP backdoor detection: find hidden admins, scan mu-plugins."
version: 1.0.0
created_by: agent
---

# WordPress Security — Backdoor & Malware Detection

Patterns and workflows for detecting and removing WordPress malware,
specifically hidden admin backdoors in mu-plugins.

## When to Use

- PHP warning: "Constant HIDDEN_USER_1 already defined"
- Suspicious mu-plugins files with obfuscated code
- Hidden admin users appearing in WordPress
- Credential exfiltration via `wp_login` hooks

## Backdoor Signature

### Files to scan
Target files in `wp-content/mu-plugins/`:
- `theme-mock.php`
- `file-index.php`
- Any PHP with `do { ... } while(false)` or `try { ... } catch(\Throwable) {}` wrappers

### Suspicious patterns (grep)
```
HIDDEN_USER_1
wp-system
16hayden-boyle
vc8HfXLUynYU
chr(104).chr(116)       # builds "https://" from ASCII
wp_create_user + set_role('administrator')
wp_authenticate + base64_encode
```

### Removal
```bash
rm "C:/Users/.../wp-content/mu-plugins/theme-mock.php"
rm "C:/Users/.../wp-content/mu-plugins/file-index.php"
ls -la "C:/Users/.../wp-content/mu-plugins/"
```

### Post-cleanup
- Delete hidden admin `wp-system` from WP Admin → Users
- Change all admin passwords
- Check wp-config.php and .htaccess

## Pitfall
- **Files survive deletion on Local by Flywheel** — verify with `ls -la` after `rm`. The files may be restored from a snapshot. Stop/start the site in Local if files reappear. The backdoor is usually duplicated (theme-mock.php + file-index.php = same malware, different obfuscation).
- **Scan ALL PHP files, not just mu-plugins** — the malware can be installed in wp-content/plugins/, wp-content/themes/, or even the root. Use a recursive grep: `grep -rn "HIDDEN_USER_1\|16hayden-boyle" wp-content/ wp-includes/ *.php`
- **Broader malware patterns to scan** — beyond the specific backdoor, scan for: `eval(`, `base64_decode`, `gzinflate`, `str_rot13`, `create_function`, `file_get_contents` combined with an external URL. These are generic PHP malware indicators.
- **Check wp-config.php and .htaccess** — backdoors sometimes modify these files to add remote file inclusion or code execution. Verify they contain only legitimate WordPress directives.
- **After cleanup, the PHP warning may persist** — if the error \"HIDDEN_USER_1 already defined\" still appears after deleting the files, the PHP opcache may have cached the file. Restart PHP (or the Local site) to clear it.
