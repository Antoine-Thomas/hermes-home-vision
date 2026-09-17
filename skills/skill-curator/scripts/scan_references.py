#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Balayage des citations de references dans les SKILL.md actifs.

Lecture seule, aucune dependance. Sort un tableau markdown
(skill | citation | statut | correction) et signale les entrees d'inventaire
perimees : une skill listee dans _inventaire.json dont le dossier n'existe plus
dans l'arbre actif (absorbee puis deplacee en .archive/) ne doit PAS etre
auditee — ses citations remonteraient en faux positifs.

Usage :
    python scan_references.py [--skills-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import re

CITATION = re.compile(r"`((?:references|scripts|templates)/[^`\s]+\.md)`")
SKIP_DIRS = {".archive", "_archive", ".curator_backups", ".hub", ".locks"}
DEFAULT_ROOT = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes", "skills"
)


def active_skills(root):
    """Dossiers contenant un SKILL.md, hors .archive/ et dossiers caches."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        if "SKILL.md" in filenames:
            yield dirpath


def find_by_basename(skill_dir, rel):
    """Chemin reel d'un fichier de meme nom, s'il a ete deplace."""
    target = os.path.basename(rel)
    for dirpath, _dirnames, filenames in os.walk(skill_dir):
        if target in filenames:
            return os.path.relpath(os.path.join(dirpath, target), skill_dir)
    return None


def scan(root):
    rows = []
    for skill_dir in sorted(active_skills(root)):
        skill = os.path.relpath(skill_dir, root).replace(os.sep, "/")
        skill_md = os.path.join(skill_dir, "SKILL.md")
        try:
            with open(skill_md, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except OSError:
            continue
        for cited in sorted(set(CITATION.findall(text))):
            rel = cited.replace("\\", "/")
            if os.path.exists(os.path.join(skill_dir, rel.replace("/", os.sep))):
                continue  # present sur disque : rien a signaler
            moved = find_by_basename(skill_dir, rel)
            rows.append((
                skill,
                cited,
                "CHEMIN" if moved else "MANQUANT",
                "-> " + moved if moved else "retirer la citation",
            ))
    return rows


def stale_inventory(root):
    """Entrees de _inventaire.json dont le chemin declare n'existe plus."""
    path = os.path.join(root, "_inventaire.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return []
    stale = []
    for entry in data:
        rel = str(entry.get("rel") or entry.get("name") or "")
        if rel and not os.path.exists(os.path.join(root, rel.replace("/", os.sep))):
            stale.append(rel)
    return stale


def main():
    ap = argparse.ArgumentParser(description="Balayage des citations de references")
    ap.add_argument("--skills-dir", default=DEFAULT_ROOT)
    args = ap.parse_args()
    root = os.path.abspath(args.skills_dir)
    if not os.path.isdir(root):
        print("dossier introuvable : %s" % root)
        return 2

    rows = scan(root)
    print("| Skill | Citation | Statut | Correction |")
    print("|---|---|---|---|")
    for row in rows:
        print("| %s | `%s` | %s | %s |" % row)
    print("\ncitations mortes : %d" % len(rows))

    stale = stale_inventory(root)
    if stale:
        print("\ninventaire perime (%d entree(s) sans dossier actif — NE PAS auditer ces skills) :" % len(stale))
        for rel in stale:
            print("  - %s" % rel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
