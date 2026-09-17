#!/usr/bin/env python3
"""
Liste les sites Local by Flywheel presents sur la machine.

Usage:
    python list_sites.py [--sites-dir DIR] [--json]
"""

import argparse
import json
import sys
from pathlib import Path


def get_sites_dir():
    """Retourne le dossier des sites Local."""
    return Path.home() / "Local Sites"


def load_site(site_path):
    """Charge les informations d'un site (site.json, sinon deduction)."""
    config_file = site_path / "site.json"
    if config_file.exists():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            return {
                "name": data.get("name", site_path.name),
                "domain": data.get("domain", f"{site_path.name}.local"),
                "php": data.get("phpVersion", "?"),
                "wp": data.get("wpVersion", "?"),
                "path": data.get("publicPath", str(site_path / "app" / "public")),
                "provisioned": (site_path / "app" / "public" / "wp-config.php").exists(),
            }
        except (OSError, json.JSONDecodeError):
            pass

    public_path = site_path / "app" / "public"
    return {
        "name": site_path.name,
        "domain": f"{site_path.name}.local",
        "php": "?",
        "wp": "?",
        "path": str(public_path),
        "provisioned": (public_path / "wp-config.php").exists(),
    }


def list_sites(sites_dir):
    """Retourne la liste des sites trouves."""
    sites_dir = Path(sites_dir)
    if not sites_dir.exists():
        return []

    sites = []
    for item in sorted(sites_dir.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            sites.append(load_site(item))
    return sites


def main():
    parser = argparse.ArgumentParser(description="Lister les sites Local by Flywheel")
    parser.add_argument("--sites-dir", default=str(get_sites_dir()), help="Dossier racine des sites")
    parser.add_argument("--json", action="store_true", help="Sortie JSON")
    args = parser.parse_args()

    try:
        sites = list_sites(args.sites_dir)

        if args.json:
            print(json.dumps(sites, indent=2, ensure_ascii=False))
            return

        if not sites:
            print(f"Aucun site trouve dans {args.sites_dir}")
            return

        print(f"{'Nom':<24} {'Domaine':<28} {'PHP':<6} {'WP':<12} {'Provis.'}")
        print("-" * 84)
        for site in sites:
            print(
                f"{site['name'][:23]:<24} {site['domain'][:27]:<28} "
                f"{site['php']:<6} {str(site['wp'])[:11]:<12} "
                f"{'oui' if site['provisioned'] else 'non'}"
            )
        print(f"\n{len(sites)} site(s) - racine: {args.sites_dir}")
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
