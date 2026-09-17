#!/usr/bin/env python3
"""
Supprime le dossier d'un site Local by Flywheel.

Usage:
    python delete_site.py --name mon-site [--force] [--backup]
"""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_sites_dir():
    """Retourne le dossier des sites Local."""
    return Path.home() / "Local Sites"


def find_wp_cli():
    """Retourne la commande WP-CLI si un export prealable est demande."""
    found = shutil.which("wp")
    return [found] if found else None


def export_database(wp, public_path, destination):
    """Exporte la base de donnees avant suppression."""
    if not wp:
        print("  export ignore: WP-CLI introuvable", file=sys.stderr)
        return None
    result = subprocess.run(
        wp + ["db", "export", str(destination), f"--path={public_path}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  export echoue: {(result.stderr or result.stdout).strip()}", file=sys.stderr)
        return None
    return destination


def delete_site(name, sites_dir, force, backup):
    """Supprime un site, avec export optionnel de la base."""
    site_path = Path(sites_dir) / name
    if not site_path.exists():
        raise FileNotFoundError(f"Site '{name}' introuvable: {site_path}")

    public_path = site_path / "app" / "public"

    if backup and public_path.exists():
        backup_dir = Path.cwd() / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = backup_dir / f"{name}_db_{stamp}.sql"
        print(f"Export de la base avant suppression -> {target}")
        export_database(find_wp_cli(), public_path, target)

    if not force:
        answer = input(f"Supprimer definitivement '{name}' ({site_path}) ? [oui/non] ")
        if answer.strip().lower() not in ("oui", "o", "yes", "y"):
            print("Suppression annulee.")
            return False

    shutil.rmtree(site_path)
    print(f"Site '{name}' supprime ({site_path})")
    return True


def main():
    parser = argparse.ArgumentParser(description="Supprimer un site Local by Flywheel")
    parser.add_argument("--name", required=True, help="Nom du site")
    parser.add_argument("--sites-dir", default=str(get_sites_dir()), help="Racine des sites")
    parser.add_argument("--force", action="store_true", help="Supprimer sans confirmation")
    parser.add_argument("--backup", action="store_true", help="Exporter la base de donnees avant suppression")
    args = parser.parse_args()

    try:
        delete_site(args.name, args.sites_dir, args.force, args.backup)
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
