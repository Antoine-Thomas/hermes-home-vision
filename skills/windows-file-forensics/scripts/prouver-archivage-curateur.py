#!/usr/bin/env python3
"""Prouve qu'un ` D` dans git est un archivage du curateur (deplacement), pas une perte.

Usage:
  python prouver-archivage-curateur.py [--repo <racine>] [--path <specimen>] [--ledger <fichier>]

Sans argument : --repo = repertoire courant, --path = "skills/".
Le ledger est cherche en remontant depuis chaque chemin supprime jusqu'au premier ancetre
contenant .curator_ledger.jsonl (= la racine des skills de ce profil).

Sortie : une ligne par suppression + un resume. Code 0 = tout couvert et contenu conserve,
3 = au moins un ecart (a nommer dans le rapport), 1 = rien a analyser / usage.
"""
import argparse, hashlib, json, os, subprocess, sys


def git_text(args, repo):
    return subprocess.run(["git"] + args, cwd=repo, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def git_bytes(args, repo):
    return subprocess.run(["git"] + args, cwd=repo, capture_output=True).stdout


def sha(data):
    return hashlib.sha256(data).hexdigest()


def norm(p):
    """Chemin comparable : separateurs unifies, lettre de lecteur retiree, minuscules."""
    s = p.replace("\\", "/")
    if len(s) > 1 and s[1] == ":":
        s = s[2:]
    return s.strip("/").lower()


def strip_repo(rel_norm, repo_norm):
    return rel_norm[len(repo_norm):].lstrip("/") if rel_norm.startswith(repo_norm) else rel_norm


def deleted(repo, pathspec):
    out = git_text(["status", "--porcelain", "--", pathspec], repo).stdout
    return [l[3:].strip() for l in out.splitlines() if l.startswith(" D ")]


def find_ledger(repo, rel):
    d = os.path.dirname(os.path.abspath(os.path.join(repo, rel)))
    root = os.path.abspath(repo)
    while len(d) >= len(root):
        cand = os.path.join(d, ".curator_ledger.jsonl")
        if os.path.isfile(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def load_moves(ledger, repo_norm):
    """Indexe les deplacements : chemin d'origine -> (destination, sha256, ts, skill)."""
    moves = {}
    if not ledger or not os.path.isfile(ledger):
        return moves
    with open(ledger, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("action") != "archive":
                continue
            before = {strip_repo(norm(e.get("path", "")), repo_norm): e.get("sha256", "")
                      for e in r.get("before", [])}
            for e in r.get("after", []):
                dst = strip_repo(norm(e.get("path", "")), repo_norm)
                for src, s in before.items():
                    if s and s == e.get("sha256"):
                        moves[src] = (dst, s, r.get("ts", "")[:19], r.get("skill", ""))
    return moves


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--path", default="skills/")
    ap.add_argument("--ledger", default=None)
    a = ap.parse_args()
    repo = os.path.abspath(a.repo)
    repo_norm = norm(repo)

    dels = deleted(repo, a.path)
    if not dels:
        print("aucune suppression ( D ) sous", a.path)
        return 1

    cache = {}
    cov = ok = miss = 0
    ecarts = []
    for rel in dels:
        led = a.ledger or find_ledger(repo, rel)
        if led not in cache:
            cache[led] = load_moves(led, repo_norm)
        mv = cache[led].get(norm(rel))
        if not mv:
            miss += 1
            ecarts.append((rel, "non couvert par une entree 'archive' du ledger", led))
            continue
        cov += 1
        dst, want, ts, skill = mv
        f = os.path.join(repo, dst)
        if os.path.isfile(f) and sha(open(f, "rb").read()) == want:
            ok += 1
            print("OK   %-70s -> %s (%s %s)" % (rel, dst, ts, skill))
        else:
            ecarts.append((rel, "destination absente ou sha different", os.path.join(repo, dst)))

    print()
    print("suppressions analysees                                      : %d" % len(dels))
    print("couvertes par une entree 'archive' (avant/apres)            : %d" % cov)
    print("  destination presente avec le sha256 EXACT du ledger       : %d" % ok)
    print("non couvertes / en ecart                                    : %d" % miss)
    for rel, why, where in ecarts:
        print("   ECART %s : %s -> %s" % (rel, why, where))

    # Contraste explicite : une copie archivee qui differe de HEAD est une DERIVE, pas une perte.
    same = diff = 0
    for rel in dels:
        led = a.ledger or find_ledger(repo, rel)
        mv = cache.get(led, {}).get(norm(rel))
        if not mv:
            continue
        f = os.path.join(repo, mv[0])
        if os.path.isfile(f):
            if sha(git_bytes(["show", "HEAD:" + rel], repo)) == sha(open(f, "rb").read()):
                same += 1
            else:
                diff += 1
    print()
    print("vs HEAD : identique %d | different %d  (different = derive runtime, PAS une perte)"
          % (same, diff))
    print("ledger(s) utilise(s) : %s" % ", ".join(x or "AUCUN" for x in cache))
    return 3 if (miss or len(ecarts)) else 0


if __name__ == "__main__":
    sys.exit(main())
