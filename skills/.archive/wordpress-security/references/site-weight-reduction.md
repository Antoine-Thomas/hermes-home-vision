# WordPress Deployment Prep — Site Weight Reduction

## Problem
WordPress local site weighs 1.3 GB. Needs to be under 300 MB for production.

## Common culprits (priority order)

| # | Path | Typical Size | Action |
|---|------|-------------|--------|
| 1 | `wp-content/ai1wm-backups/` | 500MB-2GB | Delete all but latest `.wpress` backup |
| 2 | `wp-content/themes/.git/` | 100-500MB | Delete entire `.git` folder (git history) |
| 3 | `wp-content/themes/<child>/impeccable/` | 50-200MB | External AI agent projects mistakenly placed in theme |
| 4 | `wp-content/themes/<child>/node_modules/` | 100-500MB | Delete if present (not needed in prod) |
| 5 | `wp-content/cache/` | Variable | Clear all cache |
| 6 | `wp-content/upgrade/` | Variable | Delete temporary upgrade files |
| 7 | `wp-content/debug.log` | Can grow huge | Delete or truncate |

## Scan command

```bash
# Find largest directories in wp-content
du -sh wp-content/*/ | sort -rh | head -15

# Or with find (git-bash compatible)
find wp-content/ -maxdepth 3 -type d -exec du -sh {} \; 2>/dev/null | sort -rh | head -20
```

## Cleanup commands

```bash
# Remove AI1WM backups (keep none for max savings)
rm -rf wp-content/ai1wm-backups/

# Remove git history
rm -rf wp-content/themes/.git/

# Remove external projects mistakenly in theme
rm -rf wp-content/themes/<child>/impeccable/

# Clear cache
rm -rf wp-content/cache/*
```

## Suspicious "impeccable" folder pattern

If you find an `impeccable/` folder inside the theme, it's likely an external
project with its own `.git`, agent configs (`.claude`, `.codex`, `.cursor`,
`.gemini`), and a `site/` subdirectory. This has nothing to do with WordPress
and can be safely deleted entirely.

## Post-cleanup verification

```bash
du -sh wp-content/
du -sh .
```

Target: under 300 MB for the entire site.
