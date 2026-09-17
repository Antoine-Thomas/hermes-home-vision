#!/usr/bin/env python3
"""
Reecrit les URL dans la base de donnees d'un site WordPress (WP-CLI search-replace).

Usage:
    python search_replace.py --site mon-site \
        --old-url http://mon-site.local --new-url https://exemple.com
"""

import argparse
import platform
import shutil
import subprocess
import sys
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
        raise FileNotFoundError("WP-CLI introuvable")
    return [found]


def run_search_replace(public_path, old_url, new_url, dry_run, skip_columns, all_tables):
    """Execute wp search-replace."""
    wp = find_wp_cli()

    args = [
        "search-replace",
        old_url,
        new_url,
        "--precise",
        "--report-changed-only",
        "--skip-columns=guid",
    ]
    if all_tables:
        args.append("--all-tables")
    if skip_columns:
        args.extend([f"--skip-columns={skip_columns}"])
    if dry_run:
        args.append("--dry-run")

    print(f"Remplacement: {old_url} -> {new_url}")
    print(f"  tables       : {'toutes' if all_tables else 'celles de WordPress'}")
    print(f"  mode         : {'simulation' if dry_run else 'application reelle'}")

    result = subprocess.run(wp + args + [f"--path={public_path}"], capture_output=True, text=True)
    output = (result.stdout or result.stderr).strip()

    if result.returncode != 0:
        raise RuntimeError(output)

    return output


def main():
    parser = argparse.ArgumentParser(description="Reecrire les URL d'un site WordPress")
    parser.add_argument("--site", required=True, help="Nom du site")
    parser.add_argument("--sites-dir", help="Racine des sites (defaut: ~/Local Sites)")
    parser.add_argument("--old-url", required=True, help="URL actuelle (ex. http://mon-site.local)")
    parser.add_argument("--new-url", required=True, help="URL cible (ex. https://exemple.com)")
    parser.add_argument("--dry-run", action="store_true", help="Simulation")
    parser.add_argument("--all-tables", action="store_true", help="Inclure les tables hors WordPress")
    parser.add_argument("--skip-columns", help="Colonnes a ignorer (en plus de guid)")
    args = parser.parse_args()

    try:
        root = Path(args.sites_dir) if args.sites_dir else get_sites_dir()
        public_path = root / args.site / "app" / "public"
        if not public_path.exists():
            raise FileNotFoundError(f"Site '{args.site}' introuvable: {public_path}")

        output = run_search_replace(
            public_path,
            args.old_url.rstrip("/"),
            args.new_url.rstrip("/"),
            args.dry_run,
            args.skip_columns,
            args.all_tables,
        )

        print("\n" + (output or "Aucun changement necessaire."))
        if args.dry_run:
            print("\nSimulation terminee : relancer sans --dry-run pour appliquer.")
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
