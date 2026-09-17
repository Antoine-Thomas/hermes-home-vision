#!/usr/bin/env python3
"""
Installe une liste de plugins sur un site WordPress via WP-CLI.

Usage:
    python install_plugins.py --site mon-site --plugins woocommerce,yoast-seo
    python install_plugins.py --site mon-site --from-file plugins.txt
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_cli_helper import add_common_arguments, find_wp_cli, get_public_path, run_wp  # noqa: E402


def parse_plugins(plugins_arg, from_file):
    """Construit la liste des plugins a installer."""
    slugs = []

    if plugins_arg:
        slugs.extend(s.strip() for s in plugins_arg.split(",") if s.strip())

    if from_file:
        path = Path(from_file)
        if not path.exists():
            raise FileNotFoundError(f"Fichier introuvable: {path}")
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                slugs.append(line)

    # Deduplication en conservant l'ordre
    seen = set()
    unique = []
    for slug in slugs:
        if slug not in seen:
            seen.add(slug)
            unique.append(slug)
    return unique


def install_plugins(site, sites_dir, slugs, activate, force, dry_run):
    """Installe les plugins demandes."""
    public_path = get_public_path(site, sites_dir)
    wp = find_wp_cli()

    printed, failed = [], []
    print(f"Installation de {len(slugs)} plugin(s) sur '{site}'")

    for slug in slugs:
        if dry_run:
            print(f"  - {slug} (simulation)")
            printed.append(slug)
            continue

        args = ["plugin", "install", slug]
        if activate:
            args.append("--activate")
        if force:
            args.append("--force")

        ok, message = run_wp(wp, public_path, args, slug)
        if ok:
            printed.append(slug)
        else:
            failed.append((slug, message))

    return printed, failed


def main():
    parser = argparse.ArgumentParser(description="Installer des plugins WordPress")
    add_common_arguments(parser)
    parser.add_argument("--plugins", help="Slugs separes par des virgules")
    parser.add_argument("--from-file", help="Fichier texte avec un slug par ligne")
    parser.add_argument("--no-activate", action="store_true", help="Installer sans activer")
    parser.add_argument("--force", action="store_true", help="Reinstaller si deja present")
    args = parser.parse_args()

    if not args.plugins and not args.from_file:
        parser.error("indiquer --plugins ou --from-file")

    try:
        slugs = parse_plugins(args.plugins, args.from_file)
        if not slugs:
            print("Aucun plugin a installer.", file=sys.stderr)
            sys.exit(1)

        printed, failed = install_plugins(
            args.site, args.sites_dir, slugs, not args.no_activate, args.force, args.dry_run
        )

        print(f"\nBilan - installes: {len(printed)} - echecs: {len(failed)}")
        for slug, message in failed:
            print(f"  x {slug}: {message.splitlines()[0] if message else 'erreur inconnue'}", file=sys.stderr)

        if failed:
            sys.exit(1)
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
