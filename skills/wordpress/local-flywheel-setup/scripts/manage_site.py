#!/usr/bin/env python3
"""
Demarre, arrete ou redemarre un site Local by Flywheel.

Utilise l'executable du CLI Local s'il est disponible, sinon Docker.

Usage:
    python manage_site.py --name mon-site --action start
"""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

ACTIONS = ("start", "stop", "restart", "status")


def get_sites_dir():
    """Retourne le dossier des sites Local."""
    return Path.home() / "Local Sites"


def find_local_cli():
    """Cherche l'executable du CLI Local."""
    system = platform.system().lower()
    home = Path.home()

    candidates = []
    if system == "windows":
        candidates = [
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Local" / "local.exe",
            Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local")) / "Local" / "local.exe",
        ]
    elif system == "darwin":
        candidates = [
            Path("/Applications/Local.app/Contents/MacOS/Local"),
            Path("/usr/local/bin/local"),
        ]
    else:
        candidates = [
            Path("/usr/local/bin/local"),
            home / ".local" / "bin" / "local",
        ]

    for path in candidates:
        if path.exists():
            return str(path)
    return None


def docker_action(container, action):
    """Construit la commande Docker correspondante."""
    if action == "status":
        return ["docker", "inspect", "-f", "{{.State.Status}}", container]
    if action in ("start", "stop", "restart"):
        return ["docker", action, container]
    raise ValueError(f"Action inconnue: {action}")


def manage_site(name, action, sites_dir, use_docker):
    """Execute l'action demandee sur le site."""
    site_path = Path(sites_dir) / name
    if not site_path.exists():
        raise FileNotFoundError(f"Site '{name}' introuvable dans {sites_dir}")

    local_cli = None if use_docker else find_local_cli()

    if local_cli:
        cmd = [local_cli, "site", action, name]
        source = f"CLI Local ({local_cli})"
    else:
        container = f"local-{name}"
        cmd = docker_action(container, action)
        source = f"Docker (conteneur {container})"

    print(f"Source: {source}")
    print(f"Commande: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"code de sortie {result.returncode}")

    if action == "status":
        print(f"Statut de '{name}': {result.stdout.strip()}")
    else:
        print(f"Site '{name}': {action} effectue")
    return True


def main():
    parser = argparse.ArgumentParser(description="Gerer un site Local by Flywheel")
    parser.add_argument("--name", required=True, help="Nom du site")
    parser.add_argument("--action", required=True, choices=ACTIONS, help="Action a effectuer")
    parser.add_argument("--sites-dir", default=str(get_sites_dir()), help="Dossier racine des sites")
    parser.add_argument("--docker", action="store_true", help="Forcer l'utilisation de Docker")
    args = parser.parse_args()

    try:
        manage_site(args.name, args.action, args.sites_dir, args.docker)
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        print("Astuce: si aucune commande n'aboutit, utiliser l'interface de Local.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
