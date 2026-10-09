"""Inspection en lecture seule d'un lot de fichiers AVANT `git add` / un push.

Par fichier : taille, comptes CR/LF de l'ARBRE DE TRAVAIL, suivi/versionne-a-HEAD,
et verdict de secrets MASQUE (comptes seulement -- aucune valeur n'est imprimee).

  python inspection_pre_push.py <chemin> [<chemin> ...] [--repo <dir>] [--refs]

--refs ajoute la verification des renvois `references/|templates/|scripts/|assets/`
cites par un fichier markdown : existence sur disque ET versionnement git. Exister
sur le disque ne prouve RIEN : un fichier present mais non suivi publie un lien mort.

Regles encodees ici :
  * un renvoi inter-skills se resout depuis la racine de `skills/` ;
  * un `sk-` en minuscules+tirets sans chiffre ni majuscule est un mot compose
    (`delegate-task-...`), pas une cle ;
  * `token[:=]` est un motif de DOCUMENTATION : compte a part, jamais un STOP.

Sortie : une ligne par fichier. `STOP` = hit de forme plausible, ne rien rediger.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "cache"}

KEY_PATTERNS = [
    ("sk-", re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{20,}")),
    ("ghp_", re.compile(r"(?<![A-Za-z0-9])ghp_[A-Za-z0-9]{20,}")),
    ("hf_", re.compile(r"(?<![A-Za-z0-9])hf_[A-Za-z0-9]{20,}")),
    ("AIza", re.compile(r"(?<![A-Za-z0-9])AIza[A-Za-z0-9_\-]{20,}")),
    ("nvapi-", re.compile(r"(?<![A-Za-z0-9])nvapi-[A-Za-z0-9_\-]{20,}")),
    ("xoxb-", re.compile(r"(?<![A-Za-z0-9])xoxb-[A-Za-z0-9\-]{20,}")),
    ("PRIVATE KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]
DOC_PATTERNS = [("token[:=]", re.compile(r"token\s*[:=]"))]

REF_RE = re.compile(r"`?(references|templates|scripts|assets)/([A-Za-z0-9_.\-/]+)`?")


# --------------------------------------------------------------------------- git

def git(repo, *args):
    """Retourne (code, sortie). Un git absent ne doit pas casser l'inspection."""
    try:
        p = subprocess.run(["git", "-C", repo] + list(args), capture_output=True,
                           text=True, errors="replace")
        return p.returncode, p.stdout.strip()
    except OSError as exc:
        return 127, "(git indisponible : %s)" % exc


def rel(repo, path):
    try:
        return os.path.relpath(os.path.abspath(path), os.path.abspath(repo)).replace("\\", "/")
    except ValueError:
        return None


def versioned(repo, path):
    """(suivi, versionne a HEAD) -- les deux verdicts, jamais un seul."""
    r = rel(repo, path)
    if r is None or r.startswith(".."):
        return None, None
    tracked = git(repo, "ls-files", "--error-unmatch", "--", r)[0] == 0
    at_head = git(repo, "cat-file", "-e", "HEAD:%s" % r)[0] == 0
    return tracked, at_head


# ------------------------------------------------------------------------ scans

def plausible(value):
    """Une cle plausible porte au moins un chiffre OU une majuscule."""
    return any(c.isdigit() for c in value) or any(c.isupper() for c in value)


def scan_text(text):
    keys = [(lbl, len(rx.findall(text)), sum(1 for m in rx.finditer(text) if plausible(m.group(0))))
            for lbl, rx in KEY_PATTERNS]
    doc = [(lbl, len(rx.findall(text))) for lbl, rx in DOC_PATTERNS]
    return keys, doc


def eol_counts(path):
    with open(path, "rb") as fh:
        data = fh.read()
    return data.count(b"\r"), data.count(b"\n"), len(data)


# ----------------------------------------------------------------------- sortie

def report_file(repo, path):
    try:
        cr, lf, size = eol_counts(path)
    except OSError as exc:
        print("  ABSENT   %s (%s)" % (path, exc))
        return 0
    with open(path, "rb") as fh:
        text = fh.read().decode("utf-8", "replace")
    keys, doc = scan_text(text)
    raw = sum(v[1] for v in keys)
    real = sum(v[2] for v in keys)
    docn = sum(v[1] for v in doc)
    tracked, at_head = versioned(repo, path)
    if tracked is None:
        vtxt = "hors depot"
    else:
        vtxt = "suivi=%s versionne-a-HEAD=%s" % ("oui" if tracked else "NON",
                                                  "oui" if at_head else "NON")
    flag = "STOP " if real else "OK   "
    print("  %s %s" % (flag, path))
    print("         %d o   CR=%d  LF=%d  (arbre de travail)   %s" % (size, cr, lf, vtxt))
    detail = " ".join("%s=%d(reel:%d)" % (l, a, b) for l, a, b in keys if a) or "aucun motif de cle"
    print("         cles: %s" % detail)
    if docn:
        print("         doc (compte a part, jamais un STOP): %s" %
              " ".join("%s=%d" % (l, n) for l, n in doc if n))
    if real:
        print("         >>> valeur de forme plausible : NE PAS IMPRIMER, NE RIEN REDIGER <<<")
    return real


def report_refs(repo, path):
    """Renvois cites par un markdown : existe ? versionne ?

    Un renvoi inter-skills (`scripts/x.py` d'une skill nommee dans le texte) se resout
    depuis la racine de `skills/`, sinon la verification rend un faux << manquant >>.
    """
    try:
        with open(path, "rb") as fh:
            text = fh.read().decode("utf-8", "replace")
    except OSError as exc:
        print("  refs   %s : illisible (%s)" % (path, exc))
        return 0
    base = os.path.dirname(os.path.abspath(path))
    skill_dir = os.path.dirname(base) if os.path.basename(base) == "references" else base
    refs = sorted({m.group(0).strip("`") for m in REF_RE.finditer(text)})
    if not refs:
        return 0
    missing = 0
    print("  refs   %s (%d renvois)" % (path, len(refs)))
    for r in refs:
        cands = [os.path.join(base, r), os.path.join(skill_dir, r), os.path.join(repo, r)]
        hit = next((c for c in cands if os.path.exists(c)), None)
        if hit is None:
            search = os.path.join(repo, "skills")
            want = os.path.basename(r)
            for root, dirs, files in os.walk(search):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                if want in files:
                    hit = os.path.join(root, want)
                    break
        if hit is None:
            print("         MANQUANT disque : %s" % r)
            missing += 1
            continue
        tracked, at_head = versioned(repo, hit)
        if not at_head:
            print("         NON VERSIONNE (lien mort si publie) : %s" % r)
            missing += 1
    return missing


# ------------------------------------------------------------------------- main

def collect(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                out.extend(os.path.join(root, f) for f in sorted(files))
        else:
            out.append(p)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Inspection lecture seule avant git add")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--refs", action="store_true",
                    help="verifier aussi les renvois references/templates/scripts/assets")
    args = ap.parse_args(argv)

    repo = args.repo
    code, top = git(repo, "rev-parse", "--show-toplevel")
    if code == 0:
        repo = top
    else:
        print("# depot non resolu (%s) : le versionnement ne sera pas verifie" % top)
    print("# depot : %s" % repo)
    files = collect(args.paths)
    real_total = missing_total = 0
    for f in files:
        real_total += report_file(repo, f)
        if args.refs:
            missing_total += report_refs(repo, f)
    print("\n### fichiers inspectes = %d" % len(files))
    print("### hits de forme plausible = %d" % real_total)
    if args.refs:
        print("### renvois manquants ou non versionnes = %d" % missing_total)
    if real_total:
        print("STOP : secret de forme plausible -- ne rien rediger, signaler.")
    return 1 if real_total else 0


if __name__ == "__main__":
    sys.exit(main())
