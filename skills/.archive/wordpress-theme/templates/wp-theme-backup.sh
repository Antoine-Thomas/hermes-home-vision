#!/bin/bash
# WordPress Theme Backup Template
# Usage: ./wp-theme-backup.sh /path/to/wp-content/themes/theme-name

THEME_PATH="$1"
TIMESTAMP=$(date +%Y%m%d%H%M%S)
BACKUP_DIR="${THEME_PATH}/../backups/${TIMESTAMP}"

if [ -z "$THEME_PATH" ] || [ ! -d "$THEME_PATH" ]; then
    echo "Error: Please provide a valid theme directory path"
    echo "Usage: $0 /path/to/wp-content/themes/theme-name"
    exit 1
fi

mkdir -p "$BACKUP_DIR"

# Backup key theme files
cp "$THEME_PATH/style.css" "$BACKUP_DIR/style.css.bak" 2>/dev/null || true
cp "$THEME_PATH/header.php" "$BACKUP_DIR/header.php.bak" 2>/dev/null || true
cp "$THEME_PATH/footer.php" "$BACKUP_DIR/footer.php.bak" 2>/dev/null || true
cp "$THEME_PATH/functions.php" "$BACKUP_DIR/functions.php.bak" 2>/dev/null || true
cp "$THEME_PATH/front-page.php" "$BACKUP_DIR/front-page.php.bak" 2>/dev/null || true
cp "$THEME_PATH/page.php" "$BACKUP_DIR/page.php.bak" 2>/dev/null || true
cp "$THEME_PATH/single.php" "$BACKUP_DIR/single.php.bak" 2>/dev/null || true

# Create manifest
echo "Theme backup created at: $(date)" > "$BACKUP_DIR/MANIFEST.txt"
echo "Theme path: $THEME_PATH" >> "$BACKUP_DIR/MANIFEST.txt"
echo "Files backed up:" >> "$BACKUP_DIR/MANIFEST.txt"
ls -la "$BACKUP_DIR"/*.bak 2>/dev/null | sed 's/^.*\//- /' >> "$BACKUP_DIR/MANIFEST.txt"

echo "Backup completed: $BACKUP_DIR"