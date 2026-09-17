#!/usr/bin/env python3
"""
Importe une base de donnees dans un site WordPress via WP-CLI.

Attention : l'import ECRASE les tables existantes. Utiliser --confirm.

Usage:
    python import_db.py --site mon-site --input sauvegarde.sql --confirm
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_cli_helper import add_common_arguments, find_wp_cli, get_public_path, run_wp  # noqa: E402


def import_db(site, sites_dir, source, confirm, skip_backup):
    """Importe la base, avec export de securite prealable."""
    public_path = get_public_path(site, sites_dir)
    source_path = Path(source)

    if not source_path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {source_path}")

    if not confirm:
        raise RuntimeError("Import refusee : relancer avec --confirm (les donnees seront ecrasees)")

    wp = find_wp_cli()

    if not skip_backup:
        from datetime import datetime

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety = Path.cwd() / f"{site}_before_import_{stamp}.sql"
        print(f"Export de securite -> {safety}")
        ok, message = run_wp(wp, public_path, ["db", "export", str(safety)], "sauvegarde prealable")
        if not ok:
            raise RuntimeError(f"Export de securite impossible: {message}")

    args = ["db", "import", str(source_path)]
    if source_path.suffix == ".gz":
        args.append("--gzip")

    ok, message = run_wp(wp, public_path, args, f"import de {source_path.name}")
    if not ok:
        raise RuntimeError(message)

    return source_path


def main():
    parser = argparse.ArgumentParser(description="Importer une base de donnees WordPress")
    add_common_arguments(parser)
    parser.add_argument("--input", required=True, help="Fichier .sql (ou .sql.gz) a importer")
    parser.add_argument("--confirm", action="store_true", help="Confirmer l'ecrasement des donnees")
    parser.add_argument("--skip-backup", action="store_true", help="Ne pas exporter la base avant import")
    args = parser.parse_args()

    try:
        source = import_db(args.site, args.sites_dir, args.input, args.confirm, args.skip_backup)
        print(f"\nImport termine depuis {source}")
        print("Penser a mettre a jour les URL si la base vient d'un autre environnement :")
        print("  python ../wordpress-deployment/scripts/search_replace.py --site <site> --old-url ... --new-url ...")
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
