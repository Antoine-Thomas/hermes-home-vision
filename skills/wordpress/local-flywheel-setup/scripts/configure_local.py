#!/usr/bin/env python3
"""
Ecrit une configuration de reference pour un site Local by Flywheel.

Usage:
    python configure_local.py --site-name mon-site --php-version 8.2
"""

import argparse
import json
import platform
import sys
from datetime import datetime
from pathlib import Path


def get_local_config_dir():
    """Retourne le dossier de configuration de Local selon l'OS."""
    home = Path.home()
    system = platform.system().lower()
    if system == "windows":
        return home / "AppData" / "Roaming" / "Local"
    if system == "darwin":
        return home / "Library" / "Application Support" / "Local"
    return home / ".config" / "Local"


def get_sites_dir():
    """Retourne le dossier des sites Local."""
    home = Path.home()
    system = platform.system().lower()
    if system == "windows":
        return home / "Local Sites"
    return home / "Local Sites"


def build_config(site_name, php_version, wp_version, admin_user, admin_email, admin_password, db_password, ssl, xdebug):
    """Construit le dictionnaire de configuration."""
    sites_dir = get_sites_dir()
    return {
        "siteName": site_name,
        "domain": f"{site_name}.local",
        "phpVersion": php_version,
        "wpVersion": wp_version,
        "mysqlVersion": "8.0",
        "routerMode": "localhost",
        "sitePath": str(sites_dir / site_name),
        "publicPath": str(sites_dir / site_name / "app" / "public"),
        "adminUser": admin_user,
        "adminEmail": admin_email,
        "adminPassword": admin_password,
        "dbPassword": db_password,
        "ssl": ssl,
        "xdebug": xdebug,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
    }


def main():
    parser = argparse.ArgumentParser(description="Configurer un site Local by Flywheel")
    parser.add_argument("--site-name", required=True, help="Nom du site (minuscules, sans espaces)")
    parser.add_argument("--php-version", default="8.2", choices=["8.0", "8.1", "8.2", "8.3"], help="Version PHP")
    parser.add_argument("--wp-version", default="latest", help="Version WordPress")
    parser.add_argument("--admin-user", default="admin", help="Utilisateur admin WordPress")
    parser.add_argument("--admin-email", default="admin@example.com", help="Email admin")
    parser.add_argument("--admin-password", default="", help="Mot de passe admin (a renseigner dans Local)")
    parser.add_argument("--db-password", default="", help="Mot de passe base de donnees")
    parser.add_argument("--no-ssl", action="store_true", help="Desactiver le certificat SSL local")
    parser.add_argument("--xdebug", action="store_true", help="Activer Xdebug")
    parser.add_argument("--output", help="Fichier de sortie (defaut: <config Local>/sites/<site>.json)")
    args = parser.parse_args()

    try:
        config = build_config(
            args.site_name,
            args.php_version,
            args.wp_version,
            args.admin_user,
            args.admin_email,
            args.admin_password,
            args.db_password,
            not args.no_ssl,
            args.xdebug,
        )

        if args.output:
            output_path = Path(args.output)
        else:
            output_path = get_local_config_dir() / "sites" / f"{args.site_name}.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"Configuration ecrite: {output_path}")
        print(f"  Site        : {config['siteName']}")
        print(f"  Domaine     : {config['domain']}")
        print(f"  PHP         : {config['phpVersion']}")
        print(f"  WordPress   : {config['wpVersion']}")
        print(f"  Admin       : {config['adminUser']} <{config['adminEmail']}>")
        print(f"  SSL         : {'oui' if config['ssl'] else 'non'}")
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
