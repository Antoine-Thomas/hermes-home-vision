#!/usr/bin/env python3
"""
Fonctions partagees pour les scripts du skill wp-cli-automation.

Ce module n'est pas un script executable : il est importe par les autres
scripts du dossier scripts/.
"""

import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_sites_dir():
    """Retourne le dossier racine des sites Local."""
    return Path.home() / "Local Sites"


def get_public_path(site_name, sites_dir=None):
    """Retourne le chemin app/public d'un site, en verifiant son existence."""
    root = Path(sites_dir) if sites_dir else get_sites_dir()
    public_path = root / site_name / "app" / "public"
    if not public_path.exists():
        raise FileNotFoundError(f"Site '{site_name}' introuvable: {public_path}")
    if not (public_path / "wp-config.php").exists():
        raise FileNotFoundError(
            f"{public_path} ne contient pas wp-config.php (site non provisionne ou arrete)"
        )
    return public_path


def find_wp_cli():
    """Retourne la commande WP-CLI sous forme de liste."""
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
            if candidate.suffix == ".phar":
                return [sys.executable, str(candidate)]
            return [str(candidate)]

    found = shutil.which("wp")
    if not found:
        raise FileNotFoundError(
            "WP-CLI introuvable. Installer wp-cli ou utiliser le shell du site dans Local."
        )
    return [found]


def run_wp(wp, public_path, args, label=None):
    """Execute une commande WP-CLI, affiche le resultat et retourne (ok, sortie)."""
    cmd = wp + args + [f"--path={public_path}"]
    if label:
        print(f"  - {label}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = (result.stdout or result.stderr).strip()

    if result.returncode != 0:
        if label:
            print(f"    echec: {output}", file=sys.stderr)
        return False, output

    if output and label:
        print(f"    {output.splitlines()[0][:120]}")
    return True, output


def add_common_arguments(parser):
    """Ajoute les arguments communs (--site, --sites-dir, --dry-run)."""
    parser.add_argument("--site", required=True, help="Nom du site Local")
    parser.add_argument("--sites-dir", help="Racine des sites (defaut: ~/Local Sites)")
    parser.add_argument("--dry-run", action="store_true", help="Simulation, aucune modification")
