#!/usr/bin/env python3
"""
Restaure un site WordPress local depuis une sauvegarde produite par backup_site.py.

Usage:
    python restore_site.py --site mon-site --backup ./backups/mon-site_backup_20260101_030000.tar.gz
"""

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


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
        raise FileNotFoundError("WP-CLI introuvable : necessaire pour importer la base de donnees")
    return [found]


def extract_backup(backup_path, work_root):
    """Extrait l'archive et retourne le dossier racine de la sauvegarde."""
    if backup_path.is_dir():
        return backup_path

    print(f"Extraction de {backup_path.name}")
    with tarfile.open(backup_path, "r:gz") as archive:
        members = archive.getnames()
        if not members:
            raise RuntimeError("Archive vide")
        archive.extractall(work_root)

    entries = [entry for entry in work_root.iterdir() if entry.is_dir()]
    if not entries:
        raise RuntimeError("Aucun dossier trouve dans l'archive")
    return entries[0]


def read_metadata(backup_root):
    """Lit metadata.json si present."""
    metadata_file = backup_root / "metadata.json"
    if not metadata_file.exists():
        return {}
    try:
        return json.loads(metadata_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def restore_files(backup_root, public_path):
    """Restaure les fichiers sauvegardes."""
    files_dir = backup_root / "files"
    if not files_dir.exists():
        raise FileNotFoundError("Dossier 'files' absent de la sauvegarde")

    public_path.mkdir(parents=True, exist_ok=True)
    restored = []

    for item in files_dir.iterdir():
        destination = public_path / item.name
        if item.is_dir():
            shutil.copytree(item, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(item, destination)
        restored.append(item.name)

    return restored


def restore_database(backup_root, public_path, wp):
    """Importe la base de donnees sauvegardee."""
    sql_file = backup_root / "database.sql"
    if not sql_file.exists():
        print("Avertissement: aucune base de donnees dans la sauvegarde", file=sys.stderr)
        return False

    if sql_file.stat().st_size < 64 or sql_file.read_text(encoding="utf-8", errors="ignore").startswith("-- Base non exportee"):
        print("Avertissement: database.sql vide ou non exporte, import ignore", file=sys.stderr)
        return False

    print(f"Import de la base ({sql_file.stat().st_size / 1024:.0f} Ko)")
    result = subprocess.run(
        wp + ["db", "import", str(sql_file), f"--path={public_path}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Import de la base echoue: {(result.stderr or result.stdout).strip()}")
    return True


def restore_site(site, sites_dir, backup, force, dry_run):
    """Restaure le site et retourne un rapport."""
    root = Path(sites_dir) if sites_dir else get_sites_dir()
    public_path = root / site / "app" / "public"
    backup_path = Path(backup)

    if not backup_path.exists():
        raise FileNotFoundError(f"Sauvegarde introuvable: {backup_path}")

    report = {"files": [], "database": False, "metadata": {}}

    with tempfile.TemporaryDirectory(prefix="wp_restore_") as tmp:
        work_root = Path(tmp)
        backup_root = extract_backup(backup_path, work_root)

        report["metadata"] = read_metadata(backup_root)

        if report["metadata"]:
            print(
                f"Sauvegarde du {report['metadata'].get('backup_date', '?')} "
                f"(WP {report['metadata'].get('wordpress_version') or '?'})"
            )

        files_dir = backup_root / "files"
        if not files_dir.exists():
            raise FileNotFoundError("Sauvegarde invalide : dossier 'files' absent")

        planned = sorted(item.name for item in files_dir.iterdir())

        if dry_run:
            print("Mode simulation : aucune modification")
            print(f"  Fichiers a restaurer : {', '.join(planned)}")
            print(f"  Cible : {public_path}")
            print(f"  Base de donnees : {'oui' if (backup_root / 'database.sql').exists() else 'non'}")
            report["files"] = planned
            return report

        if public_path.exists():
            if not force:
                answer = input(f"Ecraser {public_path} avec la sauvegarde ? [oui/non] ")
                if answer.strip().lower() not in ("oui", "o", "yes", "y"):
                    print("Restauration annulee.")
                    return report

        report["files"] = restore_files(backup_root, public_path)

        wp = find_wp_cli()
        report["database"] = restore_database(backup_root, public_path, wp)

    return report


def main():
    parser = argparse.ArgumentParser(description="Restaurer un site WordPress local")
    parser.add_argument("--site", required=True, help="Nom du site")
    parser.add_argument("--sites-dir", help="Racine des sites (defaut: ~/Local Sites)")
    parser.add_argument("--backup", required=True, help="Archive .tar.gz ou dossier de sauvegarde")
    parser.add_argument("--force", action="store_true", help="Ecraser sans confirmation")
    parser.add_argument("--dry-run", action="store_true", help="Verifier sans modifier")
    args = parser.parse_args()

    try:
        report = restore_site(args.site, args.sites_dir, args.backup, args.force, args.dry_run)

        if args.dry_run:
            print("\nSimulation terminee, aucune modification effectuee")
            return

        print("\nRestauration terminee")
        print(f"  Fichiers restaures : {', '.join(report['files']) or 'aucun'}")
        print(f"  Base de donnees    : {'importee' if report['database'] else 'non importee'}")
        print("\nVerifier : page d'accueil, back-office, permaliens, images.")
        print("Si le site vient d'un autre environnement, reecrire les URL (skill wordpress-deployment).")
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
