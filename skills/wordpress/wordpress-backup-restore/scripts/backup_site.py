#!/usr/bin/env python3
"""
Sauvegarde complete d'un site WordPress local (fichiers + base de donnees).

Usage:
    python backup_site.py --site mon-site --output ./backups --compress
"""

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime
from pathlib import Path

COPY_ITEMS = ["wp-config.php", ".htaccess", "wp-content"]
SKIP_IF_EXCLUDED = {"wp-content"}


def get_sites_dir():
    """Retourne le dossier racine des sites Local."""
    return Path.home() / "Local Sites"


def find_wp_cli():
    """Retourne la commande WP-CLI sous forme de liste."""
    system = platform.system().lower()
    candidates = []

    if system == "windows":
        candidates = [
            Path("C:/Program Files/Local/resources/extraResources/bin/wp-cli/wp-cli.phar"),
            Path.home() / "AppData/Local/Local/resources/extraResources/bin/wp-cli/wp-cli.phar",
        ]
    elif system == "darwin":
        candidates = [
            Path("/Applications/Local.app/Contents/Resources/extraResources/bin/wp-cli/wp-cli.phar"),
            Path("/usr/local/bin/wp"),
        ]
    else:
        candidates = [Path("/usr/local/bin/wp"), Path.home() / ".local/bin/wp"]

    for candidate in candidates:
        if candidate.exists():
            if candidate.suffix == ".phar":
                return [sys.executable, str(candidate)]
            return [str(candidate)]

    found = shutil.which("wp")
    if not found:
        raise FileNotFoundError("WP-CLI introuvable : necessaire pour exporter la base de donnees")
    return [found]


def wp_capture(wp, public_path, args):
    """Retourne la sortie d'une commande WP-CLI."""
    try:
        result = subprocess.run(
            wp + args + [f"--path={public_path}"], capture_output=True, text=True, timeout=30
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def export_database(wp, public_path, destination):
    """Exporte la base dans destination."""
    print(f"Export de la base -> {destination.name}")
    result = subprocess.run(
        wp + ["db", "export", str(destination), f"--path={public_path}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Export de la base echoue: {(result.stderr or result.stdout).strip()}")
    if not destination.exists() or destination.stat().st_size == 0:
        raise RuntimeError("Le fichier SQL exporte est vide (site arrete ?)")
    return destination


def copy_files(public_path, files_dir, exclude_uploads):
    """Copie les fichiers utiles du site."""
    print("Copie des fichiers")
    files_dir.mkdir(parents=True, exist_ok=True)

    for item in COPY_ITEMS:
        source = public_path / item
        if not source.exists():
            continue

        if item == "wp-content":
            destination = files_dir / "wp-content"
            destination.mkdir(parents=True, exist_ok=True)
            for child in source.iterdir():
                if child.name in ("cache", "upgrade", "ai1wm-backups"):
                    continue
                if exclude_uploads and child.name == "uploads":
                    print("  uploads exclu")
                    continue
                if child.is_dir():
                    shutil.copytree(child, destination / child.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(child, destination / child.name)
        else:
            shutil.copy2(source, files_dir / item)

    return files_dir


def build_metadata(site_name, public_path, wp):
    """Construit les metadonnees de la sauvegarde."""
    return {
        "site_name": site_name,
        "backup_date": datetime.now().isoformat(timespec="seconds"),
        "wordpress_version": wp_capture(wp, public_path, ["core", "version"]) if wp else None,
        "site_url": wp_capture(wp, public_path, ["option", "get", "siteurl"]) if wp else None,
        "php_version": wp_capture(wp, public_path, ["eval", "echo PHP_VERSION;"]) if wp else None,
        "source_path": str(public_path),
        "backup_type": "full",
    }


def compress(source_dir, archive_path):
    """Compresse un dossier en .tar.gz."""
    print(f"Compression -> {archive_path.name}")
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(source_dir, arcname=source_dir.name)
    return archive_path


def backup_site(site, sites_dir, output, compress_flag, exclude_uploads):
    """Realise la sauvegarde et retourne le chemin produit."""
    root = Path(sites_dir) if sites_dir else get_sites_dir()
    public_path = root / site / "app" / "public"

    if not public_path.exists():
        raise FileNotFoundError(f"Site '{site}' introuvable: {public_path}")
    if not (public_path / "wp-config.php").exists():
        raise FileNotFoundError(f"{public_path} ne contient pas wp-config.php (site non provisionne)")

    try:
        wp = find_wp_cli()
    except FileNotFoundError:
        wp = None
        print("Avertissement: WP-CLI introuvable, la base de donnees ne sera pas sauvegardee.", file=sys.stderr)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{site}_backup_{stamp}"
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = output_dir / backup_name
    work_dir.mkdir(parents=True, exist_ok=True)

    if wp:
        export_database(wp, public_path, work_dir / "database.sql")
    else:
        (work_dir / "database.sql").write_text(
            "-- Base non exportee : WP-CLI introuvable\n", encoding="utf-8"
        )

    copy_files(public_path, work_dir / "files", exclude_uploads)

    metadata = build_metadata(site, public_path, wp)
    (work_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Metadonnees ecrites")

    if compress_flag:
        archive_path = compress(work_dir, output_dir / f"{backup_name}.tar.gz")
        shutil.rmtree(work_dir)
        result_path = archive_path
    else:
        result_path = work_dir

    return result_path, metadata


def main():
    parser = argparse.ArgumentParser(description="Sauvegarder un site WordPress local")
    parser.add_argument("--site", required=True, help="Nom du site")
    parser.add_argument("--sites-dir", help="Racine des sites (defaut: ~/Local Sites)")
    parser.add_argument("--output", default="./backups", help="Dossier de destination")
    parser.add_argument("--compress", action="store_true", help="Produire une archive .tar.gz")
    parser.add_argument("--exclude-uploads", action="store_true", help="Ne pas inclure wp-content/uploads")
    args = parser.parse_args()

    try:
        result_path, metadata = backup_site(
            args.site, args.sites_dir, args.output, args.compress, args.exclude_uploads
        )
        size_mb = (
            result_path.stat().st_size / (1024 * 1024)
            if result_path.is_file()
            else sum(f.stat().st_size for f in result_path.rglob("*") if f.is_file()) / (1024 * 1024)
        )
        print("\nSauvegarde terminee")
        print(f"  Chemin : {result_path}")
        print(f"  Taille : {size_mb:.2f} Mo")
        print(f"  WP     : {metadata.get('wordpress_version') or 'inconnu'}")
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
