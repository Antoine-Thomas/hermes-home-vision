# Full Backdoor Scan Procedure

Complete scan used during the Searching-Murphy incident. Two copies of the same
malware were found in mu-plugins/.

## Step 1: Scan all PHP files

```bash
cd /path/to/wordpress/public

# Primary backdoor fingerprints
grep -rn --include="*.php" "HIDDEN_USER_1\|16hayden-boyle\|vc8HfXLUynYU7e0JHR@" .

# Broader malware patterns
grep -rn --include="*.php" -l "eval(\|base64_decode\|gzinflate\|str_rot13\|create_function" wp-content/
```

## Step 2: Scan wp-config.php and .htaccess

```bash
grep -n "HIDDEN_USER_1\|eval(\|base64_decode" wp-config.php
grep -n "HIDDEN_USER_1\|eval(\|base64_decode" .htaccess
```

## Step 3: List mu-plugins

```bash
ls -la wp-content/mu-plugins/
```

Legitimate mu-plugins to keep:
- `wp-migrate-db-pro-compatibility.php`
- Any plugin with a proper `Plugin Name:` header

Suspicious mu-plugins:
- `theme-mock.php` — backdoor (do...while(false) wrapper, hidden admin)
- `file-index.php` — backdoor (try...catch wrapper, same payload)
- Files without proper WordPress plugin headers

## Step 4: Remove malware

```bash
rm wp-content/mu-plugins/theme-mock.php
rm wp-content/mu-plugins/file-index.php
```

Verify: `ls -la wp-content/mu-plugins/`

## Step 5: Check for hidden admin user

If WP-CLI is available:
```bash
wp user list --fields=ID,user_login,user_email,roles
wp user delete wp-system --reassign=1  # if found
```

Otherwise, check via WP Admin → Users, or directly in the database:
```sql
SELECT ID, user_login, user_email FROM wp_users WHERE user_login='wp-system';
```

## Step 6: Post-cleanup

1. Stop and restart the Local site (clears PHP opcache)
2. Verify the PHP warning is gone
3. Change all admin passwords
4. Audit other admin users

## Malware Behavior (what this backdoor does)

1. Creates a hidden admin user `wp-system` with hardcoded password
2. Hides that user from the WordPress users list (users_list_table_query_args filter)
3. Intercepts admin logins (wp_authenticate hook)
4. On admin login, sends credentials to `https://16hayden-boyle.eu.cc/ingest-7f3a9c/aaxa` via POST
5. Sends: username (base64), password (base64), host, timestamp, HTTP headers, $_SERVER

The attacker receives admin credentials in near-real-time whenever an admin logs in.
