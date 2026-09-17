#!/usr/bin/env python3
"""
Deploie les fichiers d'un site WordPress local par SSH (rsync, repli scp).

Usage:
    python deploy_ssh.py --site mon-site --host bob@serveur.com --remote-path /var/www/html
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_EXCLUDES = [
    "wp-config.php",
    ".env",
    "*.log",
    ".git/",
    "wp-content/cache/",
    "wp-content/upgrade/",
]


def get_sites_dir():
    """Retourne le dossier racine des sites Local."""
    return Path.home() / "Local Sites"


def have(tool):
    """Indique si un executable est disponible."""
    return shutil.which(tool) is not None


def build_rsync_command(public_path, host, remote_path, ssh_key, port, excludes, delete, dry_run):
    """Construit la commande rsync."""
    cmd = ["rsync", "-avz", "--progress"]

    if delete:
        cmd.append("--delete")
    if dry_run:
        cmd.append("--dry-run")

    for pattern in excludes:
        cmd.extend(["--exclude", pattern])

    ssh_parts = ["ssh", "-p", str(port)]
    if ssh_key:
        ssh_parts.extend(["-i", ssh_key])
    cmd.extend(["-e", " ".join(ssh_parts)])

    cmd.append(f"{public_path}/")
    cmd.append(f"{host}:{remote_path.rstrip('/')}/")
    return cmd


def build_scp_command(public_path, host, remote_path, ssh_key, port, dry_run):
    """Construit la commande scp (repli, sans exclusion)."""
    cmd = ["scp", "-r", "-P", str(port)]
    if ssh_key:
        cmd.extend(["-i", ssh_key])
    if dry_run:
        print("Note: le repli scp ne gere pas --dry-run, la commande sera seulement affichee.")
        return None
    cmd.append(str(public_path))
    cmd.append(f"{host}:{remote_path.rstrip('/')}/")
    return cmd


def deploy(public_path, host, remote_path, ssh_key, port, excludes, delete, dry_run):
    """Execute le deploiement."""
    if have("rsync"):
        cmd = build_rsync_command(public_path, host, remote_path, ssh_key, port, excludes, delete, dry_run)
        tool = "rsync"
    else:
        cmd = build_scp_command(public_path, host, remote_path, ssh_key, port, dry_run)
        tool = "scp"
        if cmd is None:
            return {"tool": tool, "code": 0, "dry_run": True}

    print(f"Outil: {tool}")
    print(f"Commande: {' '.join(cmd)}")
    print("(mot de passe ou passphrase SSH demande par le systeme si necessaire)\n")

    result = subprocess.run(cmd)
    return {"tool": tool, "code": result.returncode, "dry_run": dry_run}


def main():
    parser = argparse.ArgumentParser(description="Deployer un site WordPress par SSH/rsync")
    parser.add_argument("--site", required=True, help="Nom du site local")
    parser.add_argument("--sites-dir", help="Racine des sites (defaut: ~/Local Sites)")
    parser.add_argument("--host", required=True, help="Cible SSH (utilisateur@serveur)")
    parser.add_argument("--remote-path", default="/var/www/html", help="Dossier distant cible")
    parser.add_argument("--ssh-key", help="Cle privee SSH")
    parser.add_argument("--port", type=int, default=22, help="Port SSH")
    parser.add_argument("--exclude", help="Motifs supplementaires, separes par des virgules")
    parser.add_argument("--no-default-excludes", action="store_true", help="Ne pas exclure wp-config.php et logs")
    parser.add_argument("--delete", action="store_true", help="Supprimer a distance ce qui n'existe plus en local")
    parser.add_argument("--dry-run", action="store_true", help="Simulation")
    args = parser.parse_args()

    try:
        root = Path(args.sites_dir) if args.sites_dir else get_sites_dir()
        public_path = root / args.site / "app" / "public"
        if not public_path.exists():
            raise FileNotFoundError(f"Site '{args.site}' introuvable: {public_path}")

        excludes = [] if args.no_default_excludes else list(DEFAULT_EXCLUDES)
        if args.exclude:
            excludes.extend(p.strip() for p in args.exclude.split(",") if p.strip())

        result = deploy(
            public_path,
            args.host,
            args.remote_path,
            args.ssh_key,
            args.port,
            excludes,
            args.delete,
            args.dry_run,
        )

        if result["dry_run"]:
            print("\nSimulation terminee (aucune modification a distance).")
        elif result["code"] == 0:
            print("\nDeploiement termine.")
        else:
            print(f"\nEchec du deploiement (code {result['code']}).", file=sys.stderr)
            sys.exit(1)
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
