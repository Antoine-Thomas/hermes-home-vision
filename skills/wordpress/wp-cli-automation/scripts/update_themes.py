#!/usr/bin/env python3
"""
Met a jour les themes d'un site WordPress via WP-CLI.

Usage:
    python update_themes.py --site mon-site [--dry-run] [--themes slug1,slug2]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_cli_helper import add_common_arguments, find_wp_cli, get_public_path, run_wp  # noqa: E402


def update_themes(site, sites_dir, dry_run, themes):
    """Met a jour un ou tous les themes et retourne le bilan."""
    public_path = get_public_path(site, sites_dir)
    wp = find_wp_cli()

    if themes:
        targets = [t.strip() for t in themes.split(",") if t.strip()]
        print(f"Mise a jour de {len(targets)} theme(s) sur '{site}'")
    else:
        targets = ["--all"]
        print(f"Mise a jour de tous les themes sur '{site}'")

    ok_count = fail_count = 0
    for target in targets:
        args = ["theme", "update", target]
        if dry_run:
            args.append("--dry-run")

        label = "tous les themes" if target == "--all" else target
        ok, _ = run_wp(wp, public_path, args, label)
        if ok:
            ok_count += 1
        else:
            fail_count += 1

    return ok_count, fail_count


def main():
    parser = argparse.ArgumentParser(description="Mettre a jour les themes WordPress")
    add_common_arguments(parser)
    parser.add_argument("--themes", help="Slugs separes par des virgules (defaut: tous)")
    args = parser.parse_args()

    try:
        ok_count, fail_count = update_themes(args.site, args.sites_dir, args.dry_run, args.themes)
        mode = "simulation" if args.dry_run else "applique"
        print(f"\nBilan ({mode}) - succes: {ok_count} - echecs: {fail_count}")
        if fail_count:
            sys.exit(1)
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
