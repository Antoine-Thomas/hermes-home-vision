#!/usr/bin/env python3
"""
Prepare l'arborescence et le fichier de configuration d'un nouveau site Local.

Ce script ne remplace pas le provisionnement fait par l'application Local :
il cree la structure attendue et un fichier site.json reutilisable par les
autres skills.

Usage:
    python create_site.py --name mon-site --domain mon-site.local
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def get_sites_dir():
    """Retourne le dossier des sites Local."""
    return Path.home() / "Local Sites"


def create_site(name, domain, php_version, wp_version, admin_user, admin_email, db_password, sites_dir):
    """Cree l'arborescence du site et retourne le chemin cree."""
    site_path = Path(sites_dir) / name

    if (site_path / "site.json").exists():
        raise FileExistsError(f"Le site '{name}' existe deja ({site_path})")

    for sub in ("app/public", "conf", "logs"):
        (site_path / sub).mkdir(parents=True, exist_ok=True)

    config = {
        "name": name,
        "domain": domain or f"{name}.local",
        "phpVersion": php_version,
        "wpVersion": wp_version,
        "mysqlVersion": "8.0",
        "sitePath": str(site_path),
        "publicPath": str(site_path / "app" / "public"),
        "adminUser": admin_user,
        "adminEmail": admin_email,
        "dbPassword": db_password,
        "ssl": True,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
    }

    (site_path / "site.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return site_path, config


def main():
    parser = argparse.ArgumentParser(description="Creer la structure d'un site Local by Flywheel")
    parser.add_argument("--name", required=True, help="Nom du site")
    parser.add_argument("--domain", help="Domaine local (defaut: <nom>.local)")
    parser.add_argument("--php-version", default="8.2", choices=["8.0", "8.1", "8.2", "8.3"])
    parser.add_argument("--wp-version", default="latest")
    parser.add_argument("--admin-user", default="admin")
    parser.add_argument("--admin-email", default="admin@example.com")
    parser.add_argument("--db-password", default="")
    parser.add_argument("--sites-dir", default=str(get_sites_dir()), help="Dossier racine des sites")
    args = parser.parse_args()

    try:
        site_path, config = create_site(
            args.name,
            args.domain,
            args.php_version,
            args.wp_version,
            args.admin_user,
            args.admin_email,
            args.db_password,
            args.sites_dir,
        )
        print(f"Site prepare: {config['name']}")
        print(f"  Chemin  : {site_path}")
        print(f"  Domaine : {config['domain']}")
        print(f"  Config  : {site_path / 'site.json'}")
        print("\nEtape suivante: creer le site dans l'interface Local pour le provisionner.")
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
