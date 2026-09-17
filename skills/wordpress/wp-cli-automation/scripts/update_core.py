#!/usr/bin/env python3
"""
Met a jour le core WordPress via WP-CLI.

Usage:
    python update_core.py --site mon-site [--version 6.6] [--minor] [--dry-run]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_cli_helper import add_common_arguments, find_wp_cli, get_public_path, run_wp  # noqa: E402


def update_core(site, sites_dir, version, minor, dry_run, force):
    """Met a jour le core WordPress."""
    public_path = get_public_path(site, sites_dir)
    wp = find_wp_cli()

    ok, current = run_wp(wp, public_path, ["core", "version"], "version installee")
    if ok:
        print(f"    {current}")

    args = ["core", "update"]
    if version:
        args.append(f"--version={version}")
    if minor:
        args.append("--minor")
    if dry_run:
        args.append("--dry-run")
    if force:
        args.append("--force")

    label = "mise a jour du core"
    if version:
        label += f" vers {version}"
    elif minor:
        label += " (version mineure)"

    ok, output = run_wp(wp, public_path, args, label)
    return ok, output


def main():
    parser = argparse.ArgumentParser(description="Mettre a jour le core WordPress")
    add_common_arguments(parser)
    parser.add_argument("--version", help="Version cible (defaut: derniere stable)")
    parser.add_argument("--minor", action="store_true", help="Mise a jour de securite uniquement (meme branche)")
    parser.add_argument("--force", action="store_true", help="Forcer la mise a jour")
    args = parser.parse_args()

    try:
        ok, output = update_core(
            args.site, args.sites_dir, args.version, args.minor, args.dry_run, args.force
        )
        if ok:
            print("\nCore WordPress a jour")
        else:
            print(f"\nEchec de la mise a jour: {output}", file=sys.stderr)
            sys.exit(1)
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
