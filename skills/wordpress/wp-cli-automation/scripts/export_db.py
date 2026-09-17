#!/usr/bin/env python3
"""
Exporte la base de donnees d'un site WordPress via WP-CLI.

Usage:
    python export_db.py --site mon-site [--output fichier.sql] [--exclude-tables a,b]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_cli_helper import add_common_arguments, find_wp_cli, get_public_path, run_wp  # noqa: E402


def export_db(site, sites_dir, output, exclude_tables, gzip):
    """Exporte la base et retourne le chemin du fichier cree."""
    public_path = get_public_path(site, sites_dir)
    wp = find_wp_cli()

    if output:
        target = Path(output)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = Path.cwd() / f"{site}_db_{stamp}.sql"

    target.parent.mkdir(parents=True, exist_ok=True)

    args = ["db", "export", str(target)]
    if exclude_tables:
        args.append(f"--exclude_tables={exclude_tables}")
    if gzip:
        args.append("--gzip")

    ok, message = run_wp(wp, public_path, args, f"export de la base vers {target}")
    if not ok:
        raise RuntimeError(message)

    if not target.exists():
        raise RuntimeError(f"WP-CLI s'est termine sans erreur mais {target} est absent")

    size_mb = target.stat().st_size / (1024 * 1024)
    print(f"    taille: {size_mb:.2f} Mo")
    return target


def main():
    parser = argparse.ArgumentParser(description="Exporter la base de donnees WordPress")
    add_common_arguments(parser)
    parser.add_argument("--output", help="Fichier de sortie (defaut: <site>_db_<horodatage>.sql)")
    parser.add_argument("--exclude-tables", help="Tables a exclure (separees par des virgules)")
    parser.add_argument("--gzip", action="store_true", help="Compresser la sortie")
    args = parser.parse_args()

    try:
        target = export_db(args.site, args.sites_dir, args.output, args.exclude_tables, args.gzip)
        print(f"\nExport termine: {target}")
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
