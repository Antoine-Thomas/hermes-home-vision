#!/usr/bin/env python3
"""
Synchronise la base de donnees locale vers un serveur distant.

Etapes : export local, sauvegarde distante, envoi par scp, import a distance.

Usage:
    python sync_database.py --site mon-site --host bob@serveur.com --remote-path /var/www/html
"""

import argparse
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


def get_sites_dir():
    """Retourne le dossier racine des sites Local."""
    return Path.home() / "Local Sites"


def find_wp_cli():
    """Retourne la commande WP-CLI locale sous forme de liste."""
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
        raise FileNotFoundError("WP-CLI introuvable localement")
    return [found]


def require_tool(tool):
    """Verifie la presence d'un executable."""
    if not shutil.which(tool):
        raise FileNotFoundError(
            f"{tool} introuvable. Sous Windows, lancer depuis Git Bash (OpenSSH inclus)."
        )
    return tool


def run(cmd, label, dry_run=False, check=True):
    """Execute une commande et retourne (code, sortie)."""
    print(f"  - {label}")
    if dry_run:
        print(f"    [simulation] {' '.join(cmd)}")
        return 0, ""

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = (result.stdout or result.stderr).strip()
    if check and result.returncode != 0:
        raise RuntimeError(f"{label} : {output}")
    return result.returncode, output


def sync_database(
    site, sites_dir, host, remote_path, remote_wp, port, ssh_key, skip_remote_backup, keep_dump, dry_run
):
    """Realise la synchronisation et retourne le chemin du dump local."""
    root = Path(sites_dir) if sites_dir else get_sites_dir()
    public_path = root / site / "app" / "public"
    if not public_path.exists():
        raise FileNotFoundError(f"Site '{site}' introuvable: {public_path}")

    wp = find_wp_cli()
    scp = require_tool("scp")
    ssh = require_tool("ssh")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_dir = Path.cwd() / "dumps"
    dump_dir.mkdir(parents=True, exist_ok=True)
    dump_path = dump_dir / f"{site}_sync_{stamp}.sql"

    ssh_opts = ["-p", str(port)]
    if ssh_key:
        ssh_opts.extend(["-i", ssh_key])

    remote_dump = f"/tmp/{site}_sync_{stamp}.sql"

    # 1. Export local
    run(wp + ["db", "export", str(dump_path), f"--path={public_path}"], "export de la base locale", dry_run)
    if not dry_run and (not dump_path.exists() or dump_path.stat().st_size == 0):
        raise RuntimeError("Export local vide (site arrete ?)")

    # 2. Sauvegarde distante
    if not skip_remote_backup:
        remote_backup = f"~/backup_before_sync_{stamp}.sql"
        cmd = [ssh] + ssh_opts + [host, f"{remote_wp} db export {remote_backup} --path={remote_path}"]
        run(cmd, f"sauvegarde distante ({remote_backup})", dry_run, check=False)

    # 3. Envoi du dump
    cmd = [scp] + ["-P", str(port)]
    if ssh_key:
        cmd.extend(["-i", ssh_key])
    cmd.extend([str(dump_path), f"{host}:{remote_dump}"])
    run(cmd, f"envoi vers {host}:{remote_dump}", dry_run)

    # 4. Import a distance
    cmd = [ssh] + ssh_opts + [host, f"{remote_wp} db import {remote_dump} --path={remote_path}"]
    run(cmd, "import de la base a distance", dry_run)

    # 5. Nettoyage
    cmd = [ssh] + ssh_opts + [host, f"rm -f {remote_dump}"]
    run(cmd, "suppression du dump distant", dry_run, check=False)

    if not keep_dump and not dry_run:
        dump_path.unlink(missing_ok=True)
        dump_path = None

    return dump_path


def main():
    parser = argparse.ArgumentParser(description="Synchroniser une base WordPress locale vers un serveur")
    parser.add_argument("--site", required=True, help="Nom du site local")
    parser.add_argument("--sites-dir", help="Racine des sites (defaut: ~/Local Sites)")
    parser.add_argument("--host", required=True, help="Cible SSH (utilisateur@serveur)")
    parser.add_argument("--remote-path", default="/var/www/html", help="Chemin WordPress distant")
    parser.add_argument("--remote-wp", default="wp", help="Commande WP-CLI distante")
    parser.add_argument("--port", type=int, default=22, help="Port SSH")
    parser.add_argument("--ssh-key", help="Cle privee SSH")
    parser.add_argument("--skip-remote-backup", action="store_true", help="Ne pas exporter la base distante")
    parser.add_argument("--keep-dump", action="store_true", help="Conserver le dump local apres envoi")
    parser.add_argument("--dry-run", action="store_true", help="Simulation")
    args = parser.parse_args()

    try:
        dump_path = sync_database(
            args.site,
            args.sites_dir,
            args.host,
            args.remote_path,
            args.remote_wp,
            args.port,
            args.ssh_key,
            args.skip_remote_backup,
            args.keep_dump,
            args.dry_run,
        )

        if args.dry_run:
            print("\nSimulation terminee : aucune donnee transferee.")
            return

        print("\nSynchronisation terminee.")
        if dump_path:
            print(f"  Dump local conserve : {dump_path}")
        print("Etapes suivantes cote serveur : reecrire les URL puis vider les caches.")
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
