#!/usr/bin/env python3
"""
Met a jour les plugins d'un site WordPress via WP-CLI.

Usage:
    python update_plugins.py --site mon-site [--dry-run] [--plugins slug1,slug2]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_cli_helper import add_common_arguments, find_wp_cli, get_public_path, run_wp  # noqa: E402


def update_plugins(site, sites_dir, dry_run, plugins):
    """Met a jour un ou tous les plugins et retourne le bilan."""
    public_path = get_public_path(site, sites_dir)
    wp = find_wp_cli()

    if plugins:
        targets = [p.strip() for p in plugins.split(",") if p.strip()]
        print(f"Mise a jour de {len(targets)} plugin(s) sur '{site}'")
    else:
        targets = ["--all"]
        print(f"Mise a jour de tous les plugins sur '{site}'")

    ok_count = fail_count = 0
    for target in targets:
        args = ["plugin", "update", target]
        if dry_run:
            args.append("--dry-run")

        label = "tous les plugins" if target == "--all" else target
        ok, output = run_wp(wp, public_path, args, label)

        if ok and not dry_run:
            if "Success" in output or "Updated" in output:
                ok_count += 1
            elif "already" in output.lower() or "aucune" in output.lower():
                ok_count += 1
            else:
                ok_count += 1
        elif ok:
            ok_count += 1
        else:
            fail_count += 1

    return ok_count, fail_count


def main():
    parser = argparse.ArgumentParser(description="Mettre a jour les plugins WordPress")
    add_common_arguments(parser)
    parser.add_argument("--plugins", help="Slugs separes par des virgules (defaut: tous)")
    args = parser.parse_args()

    try:
        ok_count, fail_count = update_plugins(args.site, args.sites_dir, args.dry_run, args.plugins)
        mode = "simulation" if args.dry_run else "applique"
        print(f"\nBilan ({mode}) - succes: {ok_count} - echecs: {fail_count}")
        if fail_count:
            sys.exit(1)
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
