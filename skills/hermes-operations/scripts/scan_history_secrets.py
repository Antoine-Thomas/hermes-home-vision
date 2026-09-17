#!/usr/bin/env python3
"""Auditer les secrets de TOUT l'historique d'un depot git (pas seulement HEAD).

Pourquoi : `git ls-files` + `git grep` ne voient que l'arbre COURANT. Un secret peut
vivre dans des blobs anciens — copie de `.env` de-suivie, `state.db` de plusieurs
centaines de Mo, `.env.avant_*` — qui partent quand meme sur le depot distant. Ce
script enumere chaque blob de chaque commit et cherche les motifs dans son CONTENU.

Usage :
    python scan_history_secrets.py [chemin_depot]              # rapport lisible
    python scan_history_secrets.py <chemin> --json             # rapport machine
    python scan_history_secrets.py <chemin> --purge-cmds       # + lignes filter-repo
    python scan_history_secrets.py <chemin> --with-generic     # + affectations generiques

Sortie : une ligne par (blob, motif) — chemin, taille, nombre d'occurrences et
empreintes sha256[:16] des valeurs uniques. **Aucune valeur n'est jamais affichee.**
Code de sortie : 1 si au moins un motif matche (gate utilisable en pre-commit), 0 sinon.

Apres une purge `git filter-repo`, relancer CE script : `git log -p | grep` ne prouve
rien sur un blob de plusieurs centaines de Mo.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import subprocess
import sys

PATTERNS = {
    "telegram_bot_token": rb"[0-9]{8,12}:[A-Za-z0-9_-]{30,40}",
    "google_api_key": rb"AIza[0-9A-Za-z_-]{35}",
    "sk_key": rb"sk-[A-Za-z0-9_-]{20,}",
    "github_token": rb"ghp_[A-Za-z0-9]{36}",
    "github_pat": rb"github_pat_[A-Za-z0-9_]{20,}",
    "huggingface_token": rb"hf_[A-Za-z0-9]{30,}",
    "pem_private_key": rb"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
}
# Opt-in : genere des faux positifs attendus (noms de variables, placeholders).
GENERIC_PATTERN = (
    "generic_assignment",
    rb"(?:TOKEN|SECRET|PASSWORD|API_KEY)[A-Z_]*\s*[:=]\s*['\"]?[A-Za-z0-9_\-/+]{24,}",
)


def git(repo: str, *args: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, **kw)


def all_objects(repo: str) -> dict[str, str]:
    """{sha: chemin} pour tous les objets de l'historique (chemin vide si inconnu)."""
    out = git(repo, "rev-list", "--objects", "--all", text=True,
              encoding="utf-8", errors="replace").stdout
    paths: dict[str, str] = {}
    for line in out.splitlines():
        sha, _, path = line.partition(" ")
        paths[sha] = path
    return paths


def blobs_of(repo: str, shas: list[str]) -> list[tuple[str, int]]:
    """[(sha, taille)] pour les seuls objets de type blob."""
    p = git(repo, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
            input="\n".join(shas), text=True, encoding="utf-8", errors="replace")
    blobs = []
    for line in p.stdout.splitlines():
        f = line.split()
        if len(f) == 3 and f[1] == "blob":
            blobs.append((f[0], int(f[2])))
    return blobs


def scan(repo: str, patterns: dict[str, bytes]) -> dict[str, list[dict]]:
    """Scanne le CONTENU de chaque blob en flux binaire. Ne renvoie que des empreintes."""
    compiled = {k: re.compile(v) for k, v in patterns.items()}
    paths = all_objects(repo)
    blobs = blobs_of(repo, list(paths))
    print(f"# {len(paths)} objets, {len(blobs)} blobs a scanner "
          f"({sum(s for _, s in blobs) / 1048576:.1f} Mo)", file=sys.stderr)

    hits: dict[str, list[dict]] = collections.defaultdict(list)
    proc = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)
    assert proc.stdin and proc.stdout
    for sha, _size in blobs:
        proc.stdin.write((sha + "\n").encode())
        proc.stdin.flush()
        header = proc.stdout.readline().decode("utf-8", "replace").split()
        if len(header) != 3 or header[1] != "blob":
            continue
        data = proc.stdout.read(int(header[2]))
        proc.stdout.read(1)  # saut de ligne final du protocole batch
        for name, rx in compiled.items():
            found = rx.findall(data)
            if not found:
                continue
            vals = sorted({v if isinstance(v, bytes) else v[0] for v in found})
            hits[name].append({
                "blob": sha[:12],
                "path": paths.get(sha, "(chemin inconnu)"),
                "size_ko": round(_size / 1024),
                "occurrences": len(found),
                "fingerprints": [hashlib.sha256(v).hexdigest()[:16] for v in vals[:5]],
            })
    proc.stdin.close()
    proc.wait()
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?", default=".", help="chemin du depot (defaut: .)")
    ap.add_argument("--json", action="store_true", help="rapport machine")
    ap.add_argument("--purge-cmds", action="store_true", help="ajouter les commandes git filter-repo")
    ap.add_argument("--with-generic", action="store_true", help="inclure les affectations generiques (bruit)")
    args = ap.parse_args()

    patterns = dict(PATTERNS)
    if args.with_generic:
        patterns[GENERIC_PATTERN[0]] = GENERIC_PATTERN[1]
    hits = scan(args.repo, patterns)

    if args.json:
        print(json.dumps(hits, indent=2, ensure_ascii=False))
    else:
        print("=== SCAN DE TOUT L'HISTORIQUE ===")
        if not hits:
            print("  aucun motif de secret dans aucun blob (historique propre)")
        for name, entries in hits.items():
            print(f"  {name} : {len(entries)} blob(s)")
            for e in entries:
                print(f"     blob {e['blob']} | {e['path']} | {e['size_ko']} Ko | "
                      f"{e['occurrences']} occurrence(s) | empreintes {e['fingerprints']}")
        if hits and args.purge_cmds:
            chemins = sorted({e["path"] for entries in hits.values() for e in entries
                              if e["path"] != "(chemin inconnu)"})
            print("\n=== purge en UNE passe (une passe par oubli = une reecriture de SHA de plus) ===")
            print("git filter-repo --force --invert-paths \\")
            for i, c in enumerate(chemins):
                print(f"  --path {c}" + (" \\" if i < len(chemins) - 1 else ""))
            print("\n# puis relancer ce script sur le depot reecrit : attendu 0 blob.")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
