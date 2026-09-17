#!/usr/bin/env python3
"""
Liste les sauvegardes disponibles pour un site WordPress local.

Usage:
    python list_backups.py --site mon-site [--backup-dir ./backups]
"""

import argparse
import json
import sys
import tarfile
from datetime import datetime
from pathlib import Path


def human_size(size_bytes):
    """Formate une taille en octets."""
    size = float(size_bytes)
    for unit in ("o", "Ko", "Mo", "Go"):
        if size < 1024 or unit == "Go":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} Go"


def read_archive_metadata(archive_path):
    """Tente de lire metadata.json a l'interieur de l'archive."""
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            for member in archive.getmembers():
                if member.name.endswith("metadata.json") and member.isfile():
                    extracted = archive.extractfile(member)
                    if extracted:
                        return json.loads(extracted.read().decode("utf-8"))
    except (tarfile.TarError, OSError, json.JSONDecodeError):
        pass
    return {}


def parse_stamp(name, site):
    """Extrait l'horodatage du nom de fichier."""
    prefix = f"{site}_backup_"
    if not name.startswith(prefix):
        return None
    stamp = name[len(prefix):].replace(".tar.gz", "")
    try:
        return datetime.strptime(stamp, "%Y%m%d_%H%M%S")
    except ValueError:
        return None


def collect_backups(site, backup_dir):
    """Rassemble les sauvegardes trouvees."""
    directory = Path(backup_dir)
    if not directory.exists():
        return []

    backups = []

    for archive in sorted(directory.glob(f"{site}_backup_*.tar.gz")):
        metadata = read_archive_metadata(archive)
        stamp = parse_stamp(archive.name, site)
        backups.append(
            {
                "path": str(archive),
                "kind": "archive",
                "date": metadata.get("backup_date") or (stamp.isoformat() if stamp else None),
                "size": archive.stat().st_size,
                "wordpress_version": metadata.get("wordpress_version"),
                "site_url": metadata.get("site_url"),
            }
        )

    for folder in sorted(directory.glob(f"{site}_backup_*")):
        if not folder.is_dir():
            continue
        metadata_file = folder / "metadata.json"
        metadata = {}
        if metadata_file.exists():
            try:
                metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                metadata = {}
        total = sum(item.stat().st_size for item in folder.rglob("*") if item.is_file())
        backups.append(
            {
                "path": str(folder),
                "kind": "dossier",
                "date": metadata.get("backup_date"),
                "size": total,
                "wordpress_version": metadata.get("wordpress_version"),
                "site_url": metadata.get("site_url"),
            }
        )

    backups.sort(key=lambda item: item["date"] or "", reverse=True)
    return backups


def main():
    parser = argparse.ArgumentParser(description="Lister les sauvegardes d'un site WordPress")
    parser.add_argument("--site", required=True, help="Nom du site")
    parser.add_argument("--backup-dir", default="./backups", help="Dossier des sauvegardes")
    parser.add_argument("--json", action="store_true", help="Sortie JSON")
    args = parser.parse_args()

    try:
        backups = collect_backups(args.site, args.backup_dir)

        if args.json:
            print(json.dumps(backups, indent=2, ensure_ascii=False))
            return

        if not backups:
            print(f"Aucune sauvegarde pour '{args.site}' dans {args.backup_dir}")
            return

        print(f"{'Date':<21} {'Type':<9} {'Taille':<11} {'WP':<9} {'Chemin'}")
        print("-" * 100)
        for backup in backups:
            date = (backup["date"] or "?")[:19]
            print(
                f"{date:<21} {backup['kind']:<9} {human_size(backup['size']):<11} "
                f"{str(backup['wordpress_version'] or '?'):<9} {backup['path']}"
            )
        print(f"\n{len(backups)} sauvegarde(s) - dossier: {args.backup_dir}")
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
