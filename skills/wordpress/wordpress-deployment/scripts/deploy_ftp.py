#!/usr/bin/env python3
"""
Deploie les fichiers d'un site WordPress local par FTP ou FTPS.

Implementation basee sur ftplib (bibliotheque standard) : aucune dependance externe.

Usage:
    python deploy_ftp.py --site mon-site --host ftp.exemple.com --user bob --remote-path /www
"""

import argparse
import fnmatch
import ftplib
import getpass
import sys
from pathlib import Path

DEFAULT_EXCLUDES = [
    "wp-config.php",
    ".env",
    "*.log",
    ".git*",
    "wp-content/cache/*",
    "wp-content/upgrade/*",
]


def get_sites_dir():
    """Retourne le dossier racine des sites Local."""
    return Path.home() / "Local Sites"


def is_excluded(relative_path, patterns):
    """Indique si un chemin relatif correspond a un motif d'exclusion."""
    posix = relative_path.as_posix()
    for pattern in patterns:
        if fnmatch.fnmatch(posix, pattern) or fnmatch.fnmatch(relative_path.name, pattern):
            return True
        if pattern.endswith("/*") and posix.startswith(pattern[:-1]):
            return True
    return False


def collect_files(public_path, patterns):
    """Retourne la liste des fichiers a envoyer (chemin local, chemin relatif)."""
    files = []
    for item in sorted(public_path.rglob("*")):
        if item.is_file():
            relative = item.relative_to(public_path)
            if not is_excluded(relative, patterns):
                files.append((item, relative))
    return files


def ensure_remote_dir(ftp, remote_dir):
    """Cree l'arborescence distante si necessaire."""
    try:
        ftp.mkd(remote_dir)
    except ftplib.error_perm:
        pass


def deploy(public_path, host, user, password, remote_path, port, use_tls, patterns, dry_run):
    """Envoie les fichiers et retourne le bilan."""
    files = collect_files(public_path, patterns)
    print(f"{len(files)} fichier(s) a envoyer vers {host}:{remote_path}")

    if dry_run:
        for local, relative in files[:25]:
            print(f"  [simulation] {relative}")
        if len(files) > 25:
            print(f"  ... et {len(files) - 25} autre(s)")
        return {"sent": 0, "failed": 0, "planned": len(files)}

    ftp_class = ftplib.FTP_TLS if use_tls else ftplib.FTP
    ftp = ftp_class()
    ftp.connect(host, port, timeout=30)
    ftp.login(user, password)
    if use_tls:
        ftp.prot_p()
    ftp.set_pasv(True)

    sent = failed = 0
    created_dirs = set()

    try:
        for local, relative in files:
            remote_file = f"{remote_path.rstrip('/')}/{relative.as_posix()}"
            remote_dir = str(Path(remote_file).parent).replace("\\", "/")

            if remote_dir not in created_dirs:
                parts = remote_dir.split("/")
                current = ""
                for part in parts:
                    if not part:
                        continue
                    current = f"{current}/{part}" if current else part
                    if current not in created_dirs:
                        ensure_remote_dir(ftp, current)
                        created_dirs.add(current)

            try:
                with local.open("rb") as handle:
                    ftp.storbinary(f"STOR {remote_file}", handle)
                sent += 1
                print(f"  envoye: {relative}")
            except (ftplib.all_errors) as exc:
                failed += 1
                print(f"  echec: {relative} ({exc})", file=sys.stderr)
    finally:
        try:
            ftp.quit()
        except ftplib.all_errors:
            ftp.close()

    return {"sent": sent, "failed": failed, "planned": len(files)}


def main():
    parser = argparse.ArgumentParser(description="Deployer un site WordPress par FTP/FTPS")
    parser.add_argument("--site", required=True, help="Nom du site local")
    parser.add_argument("--sites-dir", help="Racine des sites (defaut: ~/Local Sites)")
    parser.add_argument("--host", required=True, help="Serveur FTP")
    parser.add_argument("--user", required=True, help="Utilisateur FTP")
    parser.add_argument("--password", help="Mot de passe FTP (sinon demande interactivement)")
    parser.add_argument("--remote-path", default="/public_html", help="Dossier distant cible")
    parser.add_argument("--port", type=int, default=21, help="Port (21 FTP, 21 FTPS)")
    parser.add_argument("--use-tls", action="store_true", help="Utiliser FTPS explicite")
    parser.add_argument("--exclude", help="Motifs supplementaires, separes par des virgules")
    parser.add_argument("--no-default-excludes", action="store_true", help="Ne pas exclure wp-config.php et logs")
    parser.add_argument("--dry-run", action="store_true", help="Simulation")
    args = parser.parse_args()

    try:
        root = Path(args.sites_dir) if args.sites_dir else get_sites_dir()
        public_path = root / args.site / "app" / "public"
        if not public_path.exists():
            raise FileNotFoundError(f"Site '{args.site}' introuvable: {public_path}")

        patterns = [] if args.no_default_excludes else list(DEFAULT_EXCLUDES)
        if args.exclude:
            patterns.extend(p.strip() for p in args.exclude.split(",") if p.strip())

        password = args.password
        if password is None and not args.dry_run:
            password = getpass.getpass(f"Mot de passe FTP pour {args.user}@{args.host}: ")

        result = deploy(
            public_path,
            args.host,
            args.user,
            password,
            args.remote_path,
            args.port,
            args.use_tls,
            patterns,
            args.dry_run,
        )

        if args.dry_run:
            print(f"\nSimulation terminee : {result['planned']} fichier(s) seraient envoyes.")
        else:
            print(f"\nDeploiement termine - envoyes: {result['sent']} - echecs: {result['failed']}")
            if result["failed"]:
                sys.exit(1)
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
