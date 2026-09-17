#!/usr/bin/env python3
"""
Inventaire des sites WordPress locaux : version WP, theme actif, plugins actifs.

Usage:
    python list_sites.py [--json] [--sites-dir DIR]
"""

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_sites_dir():
    """Retourne le dossier des sites Local."""
    return Path.home() / "Local Sites"


def find_wp_cli():
    """Retourne la commande WP-CLI a utiliser."""
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
            return [sys.executable, str(candidate)] if candidate.suffix == ".phar" else [str(candidate)]

    found = shutil.which("wp")
    return [found] if found else None


def wp_output(wp, public_path, args):
    """Retourne la sortie d'une commande WP-CLI, ou None en cas d'echec."""
    if not wp:
        return None
    try:
        result = subprocess.run(
            wp + args + [f"--path={public_path}"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def collect_site(site_dir, wp):
    """Rassemble les informations d'un site."""
    public_path = site_dir / "app" / "public"
    info = {
        "name": site_dir.name,
        "path": str(public_path),
        "wp_version": None,
        "theme": None,
        "active_plugins": 0,
        "provisioned": (public_path / "wp-config.php").exists() if public_path.exists() else False,
    }

    if not info["provisioned"]:
        return info

    version = wp_output(wp, public_path, ["core", "version"])
    if version:
        info["wp_version"] = version

    theme = wp_output(wp, public_path, ["theme", "list", "--status=active", "--field=name"])
    if theme:
        info["theme"] = theme.splitlines()[0].strip()

    plugins = wp_output(wp, public_path, ["plugin", "list", "--status=active", "--field=name"])
    if plugins:
        info["active_plugins"] = len([line for line in plugins.splitlines() if line.strip()])

    return info


def main():
    parser = argparse.ArgumentParser(description="Lister les sites WordPress locaux")
    parser.add_argument("--sites-dir", default=str(get_sites_dir()), help="Racine des sites")
    parser.add_argument("--json", action="store_true", help="Sortie JSON")
    args = parser.parse_args()

    try:
        sites_dir = Path(args.sites_dir)
        if not sites_dir.exists():
            raise FileNotFoundError(f"Dossier introuvable: {sites_dir}")

        wp = find_wp_cli()
        if not wp:
            print("Information: WP-CLI introuvable, les details seront limites.", file=sys.stderr)

        sites = [
            collect_site(item, wp)
            for item in sorted(sites_dir.iterdir())
            if item.is_dir() and not item.name.startswith(".")
        ]

        if args.json:
            print(json.dumps(sites, indent=2, ensure_ascii=False))
            return

        if not sites:
            print(f"Aucun site dans {sites_dir}")
            return

        print(f"{'Nom':<24} {'WP':<10} {'Theme':<22} {'Plugins':<8} {'Provis.'}")
        print("-" * 76)
        for site in sites:
            print(
                f"{site['name'][:23]:<24} "
                f"{str(site['wp_version'] or '?'):<10} "
                f"{str(site['theme'] or '?')[:21]:<22} "
                f"{site['active_plugins']:<8} "
                f"{'oui' if site['provisioned'] else 'non'}"
            )
        print(f"\n{len(sites)} site(s) - racine: {sites_dir}")
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
