#!/usr/bin/env python3
"""scan_secrets_history.py - scanne TOUT l'historique git d'un depot (pas seulement HEAD).

Pourquoi un scanner dedie : `git log -p | grep` ne prouve rien sur un gros blob binaire
(un state.db de 192 Mo est traverse sans etre lisible ligne a ligne), et un fichier de-troque
(`git rm --cached`) laisse son blob dans les commits precedents. Ce script enumere TOUS les
blobs du depot, les lit en flux binaire et applique les motifs d'empreinte classiques.

Usage :
    python scan_secrets_history.py [--repo <chemin>] [--quiet]

Sortie : un tableau (chemin, blob, taille, nombre d'occurrences, empreintes sha256[:16] des
valeurs trouvees). JAMAIS la valeur elle-meme. Code de sortie 1 si au moins un motif matche.

Motifs couverts : jeton Telegram, cle Google (AIza), cle sk- (OpenAI/OmniRoute/DeepSeek),
jeton GitHub (ghp_), jeton HuggingFace (hf_), cle privee PEM.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import re
import subprocess
import sys

PATTERNS = {
    "telegram_bot_token": rb"[0-9]{8,12}:[A-Za-z0-9_-]{30,40}",
    "google_api_key": rb"AIza[0-9A-Za-z_-]{35}",
    "sk_key": rb"sk-[A-Za-z0-9_-]{20,}",
    "github_token": rb"ghp_[A-Za-z0-9]{36}",
    "huggingface_token": rb"hf_[A-Za-z0-9]{30,}",
    "pem_private_key": rb"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
}
COMPILED = {k: re.compile(v) for k, v in PATTERNS.items()}

# Placeholders connus : signales mais non bloquants (aucune valeur reelle).
PLACEHOLDER = re.compile(rb"(?i)(example|placeholder|your_|<[A-Z_]+>|xxx|redacted|masked)")


def git(*args: str, repo: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, **kw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    repo = args.repo

    rev = git("rev-list", "--objects", "--all", repo=repo, text=True,
              encoding="utf-8", errors="replace").stdout
    paths: dict[str, str] = {}
    shas: list[str] = []
    for line in rev.splitlines():
        parts = line.split(" ", 1)
        shas.append(parts[0])
        if len(parts) > 1:
            paths[parts[0]] = parts[1]

    bc = git("cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
             repo=repo, input="\n".join(shas), text=True, encoding="utf-8",
             errors="replace").stdout
    blobs = []
    for line in bc.splitlines():
        f = line.split()
        if len(f) == 3 and f[1] == "blob":
            blobs.append((f[0], int(f[2])))

    print(f"depot {repo}")
    print(f"objets={len(shas)} blobs={len(blobs)} volume={sum(s for _, s in blobs) / 1048576:.1f} Mo")

    hits: dict[str, list] = collections.defaultdict(list)
    proc = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)
    for sha, size in blobs:
        proc.stdin.write((sha + "\n").encode())
        proc.stdin.flush()
        header = proc.stdout.readline().decode("utf-8", "replace").split()
        if len(header) != 3 or header[1] != "blob":
            continue
        data = proc.stdout.read(int(header[2]))
        proc.stdout.read(1)
        for name, rx in COMPILED.items():
            ms = rx.findall(data)
            if not ms:
                continue
            vals = sorted({m if isinstance(m, bytes) else m[0] for m in ms})
            emps = [hashlib.sha256(v).hexdigest()[:16] for v in vals]
            # un motif dont TOUTES les occurrences ressemblent a un placeholder est signale a part
            reels = [e for v, e in zip(vals, emps) if not PLACEHOLDER.search(v)]
            hits[name].append({
                "blob": sha[:12], "path": paths.get(sha, "(chemin inconnu)"),
                "size_kb": size / 1024, "n": len(ms),
                "empreintes": emps[:4], "reels": len(reels),
            })
    proc.stdin.close()
    proc.wait()

    print()
    total_reels = 0
    for name in PATTERNS:
        lst = hits.get(name, [])
        if not lst:
            print(f"{name:20} : 0 blob")
            continue
        print(f"{name:20} : {len(lst)} blob(s)")
        for h in lst:
            tag = "REEL" if h["reels"] else "placeholder"
            total_reels += h["reels"]
            print(f"    {tag:11} {h['blob']} | {h['path']} | {h['size_kb']:.0f} Ko | "
                  f"{h['n']} occ. | empreintes {h['empreintes']}")

    print()
    if total_reels == 0:
        print("RESULTAT : aucune valeur de secret reelle dans l'historique (placeholders exclus)")
        return 0
    print(f"RESULTAT : {total_reels} valeur(s) de secret reelle(s) a purger")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
