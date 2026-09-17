# Yoast SEO Metadata — Update via MySQL (Python + pymysql)

Use this when WP-CLI fails on Local by Flywheel (PHP lacks mysqli/PDO MySQL).

## Prerequisites

```bash
pip install pymysql
```

## Step 1: Find the MySQL port

Local by Flywheel uses ports 10002-10005 on Windows (not 3306). Test each:

```bash
python -c "
import pymysql
for port in [10003, 10004, 10005, 10002]:
    try:
        conn = pymysql.connect(host='127.0.0.1', port=port, user='root',
                               password='root', database='local', connect_timeout=2)
        print(f'MySQL on port {port}')
        conn.close()
        break
    except:
        pass
"
```

DB credentials from `wp-config.php` — typically `local` / `root` / `root` on Local.

## Step 2: Ready-to-run script

Save as `update-yoast.py` and run with `python update-yoast.py`:

```python
import pymysql

MYSQL_PORT = 10005  # adjust after Step 1
DB = 'local'
USER = 'root'
PASSWORD = 'root'

conn = pymysql.connect(
    host='127.0.0.1', port=MYSQL_PORT, user=USER, password=PASSWORD,
    database=DB, charset='utf8mb4', autocommit=True
)
cursor = conn.cursor()

# Get front page ID
cursor.execute("SELECT option_value FROM wp_options WHERE option_name = 'page_on_front'")
front_id = int(cursor.fetchone()[0])
print(f"Front page ID: {front_id}")

# Define your updates: (slug_or_None, title, meta_description)
updates = [
    (None, 'Searching Murphy | Developpeur WordPress a Caen',
          'Thomas Leroyer : creation site WordPress, photo pro, design et IA a Caen.'),
    ('devis-automatique', 'Devis gratuit | Creation site web Caen | Searching Murphy',
          'Obtenez un devis personnalise pour votre site WordPress a Caen. Reponse sous 24h.'),
]

for slug, title, desc in updates:
    if slug is None:
        pid = front_id
        name = 'front-page'
    else:
        cursor.execute(
            "SELECT ID FROM wp_posts WHERE post_name = %s AND post_type = 'page' LIMIT 1",
            (slug,)
        )
        row = cursor.fetchone()
        if not row:
            print(f"WARN: {slug} not found")
            continue
        pid = int(row[0])
        name = slug

    # Replace existing Yoast metas
    cursor.execute(
        "DELETE FROM wp_postmeta WHERE post_id = %s AND meta_key IN "
        "('_yoast_wpseo_title', '_yoast_wpseo_metadesc')",
        (pid,)
    )
    cursor.execute(
        "INSERT INTO wp_postmeta (post_id, meta_key, meta_value) "
        "VALUES (%s, '_yoast_wpseo_title', %s)",
        (pid, title)
    )
    cursor.execute(
        "INSERT INTO wp_postmeta (post_id, meta_key, meta_value) "
        "VALUES (%s, '_yoast_wpseo_metadesc', %s)",
        (pid, desc)
    )
    print(f"OK: {name} (ID={pid})")

# Verify
print("\n=== VERIFICATION ===")
cursor.execute("""
    SELECT p.post_title, pm.meta_key, pm.meta_value
    FROM wp_postmeta pm
    JOIN wp_posts p ON p.ID = pm.post_id
    WHERE pm.meta_key IN ('_yoast_wpseo_title', '_yoast_wpseo_metadesc')
    AND p.ID = %s
""", (front_id,))
for title, key, val in cursor.fetchall():
    print(f"  [{key}] {title}: {val}")

conn.close()
print("\nDONE")
```

## Step 3: Flush WordPress cache

After updating via MySQL, clear the WordPress cache (WP Rocket, LiteSpeed, object cache) so the new metas take effect. If you have WP-CLI available: `wp cache flush`.

## Pitfalls

- **Inline shell quoting** — don't pass the Python script via `python -c "..."` if it contains single quotes. Write to a .py file (`write_file`) and execute it with `terminal(command='python path/to/script.py')`.
- **Accented characters** — pymysql with `charset='utf8mb4'` handles French accents correctly. No need to escape.
- **Port changes across Local restarts** — the MySQL port may change when Local restarts. Always re-test with Step 1 before running.
- **Yoast cache** — Yoast may cache old versions. Flush WP cache after the MySQL update, or save the page in the admin to trigger Yoast's cache rebuild.
