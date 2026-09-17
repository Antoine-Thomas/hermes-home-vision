#!/usr/bin/env python3
"""
Cree un site WordPress local avec WP-CLI (telechargement + installation).

Usage:
    python create_site.py --name mon-site --domain mon-site.local
"""

import argparse
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
    if found:
        return [found]

    raise FileNotFoundError(
        "WP-CLI introuvable. Installer wp-cli ou utiliser le shell du site dans Local."
    )


def run(cmd, step):
    """Execute une commande WP-CLI et leve une erreur explicite en cas d'echec."""
    print(f"  - {step}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{step} : {message}")
    return result.stdout.strip()


def create_site(name, domain, wp_version, admin_user, admin_password, admin_email, sites_dir, skip_install, force):
    """Cree le site et retourne le chemin public."""
    site_root = Path(sites_dir) / name
    public_path = site_root / "app" / "public"

    if public_path.exists() and any(public_path.iterdir()) and not force:
        raise FileExistsError(f"{public_path} existe deja (utiliser --force pour continuer)")

    public_path.mkdir(parents=True, exist_ok=True)
    wp = find_wp_cli()
    domain = domain or f"{name}.local"

    print(f"Creation du site '{name}' dans {public_path}")
    run(wp + ["core", "download", f"--version={wp_version}", f"--path={public_path}"], "telechargement du core")

    run(
        wp
        + [
            "config",
            "create",
            "--dbname=local",
            "--dbuser=root",
            "--dbpass=root",
            "--dbhost=127.0.0.1",
            f"--path={public_path}",
            "--skip-check",
            "--force",
        ],
        "creation de wp-config.php",
    )

    if not skip_install:
        run(
            wp
            + [
                "core",
                "install",
                f"--url=http://{domain}",
                f"--title={name}",
                f"--admin_user={admin_user}",
                f"--admin_password={admin_password}",
                f"--admin_email={admin_email}",
                f"--path={public_path}",
                "--skip-email",
            ],
            "installation de WordPress",
        )

    return public_path, domain


def main():
    parser = argparse.ArgumentParser(description="Creer un site WordPress local avec WP-CLI")
    parser.add_argument("--name", required=True, help="Nom du site (dossier)")
    parser.add_argument("--domain", help="Domaine local (defaut: <nom>.local)")
    parser.add_argument("--wp-version", default="latest", help="Version WordPress")
    parser.add_argument("--admin-user", default="admin")
    parser.add_argument("--admin-password", default="admin")
    parser.add_argument("--admin-email", default="admin@example.com")
    parser.add_argument("--sites-dir", default=str(get_sites_dir()), help="Racine des sites")
    parser.add_argument("--skip-install", action="store_true", help="Telecharger le core uniquement")
    parser.add_argument("--force", action="store_true", help="Ecrire dans un dossier existant")
    args = parser.parse_args()

    try:
        public_path, domain = create_site(
            args.name,
            args.domain,
            args.wp_version,
            args.admin_user,
            args.admin_password,
            args.admin_email,
            args.sites_dir,
            args.skip_install,
            args.force,
        )
        print("\nSite cree avec succes")
        print(f"  Chemin : {public_path}")
        print(f"  URL    : http://{domain}")
        if not args.skip_install:
            print(f"  Admin  : {args.admin_user}")
        print("\nPenser a declarer le site dans l'interface Local pour que le serveur serve ce dossier.")
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
