"""Garde-fou de commit pour cron/jobs.json : definition modifiee, ou bruit de runtime ?

Le planificateur reecrit ce fichier a chaque tir de job et y ajoute de l'etat de runtime
(`completed`, `next_run_at`, `last_run_at`, `updated_at`, `scheduled_at`, `dispatched_at`,
`lateness_seconds`) : il est donc TOUJOURS sale. Un porcelain qui le liste ne signale pas une derive.
Ne le committer que quand une DEFINITION de job a change.

    python scripts/cron_jobs_gate.py [--repo <chemin>] [--path cron/jobs.json] [--staged]
                                     [--noise cle1,cle2] [--list-noise] [--quiet]

Sortie :
    0  aucune definition touchee  -> bruit de runtime seul : ne pas committer
    1  au moins une definition touchee -> committer, les lignes fautives sont listees
    2  erreur d'invocation ou de git

Pourquoi un script et pas un one-liner : la version ecrite a la main filtre `^[+-]` et laisse passer
les deux lignes d'en-tete du diff (`--- a/cron/jobs.json`, `+++ b/cron/jobs.json`), qui matchent
elles aussi `^[+-]` — elle ne renvoie donc JAMAIS « bruit » et valide tout. Un garde-fou se teste sur un
cas de bruit AVANT d'etre fige, sinon il ne dit rien.

Le jeu de cles de runtime est une liste NEGATIVE, volontairement minimale et documentee :
- `created_at` n'y est PAS : il ne bouge que si le job a ete recree, ce qui est une definition.
- `last_status`, `last_error`, `last_delivery_error`, `fire_claim` n'y sont PAS : ce sont bien de
  l'etat, mais les exclure masquerait un job en echec. Etendre avec `--noise` si leur bruit l'emporte.
Un champ de runtime nouvellement ajoute par Hermes sera classe « definition » : faux positif dans le
sens sur (on committe du bruit), jamais l'inverse. L'ajouter ici quand il apparait.
"""
import argparse
import os
import re
import subprocess
import sys

# Cles d'etat de runtime : elles changent a chaque tir sans qu'aucune definition ne bouge.
NOISE_DEFAUT = (
    "completed",
    "next_run_at",
    "last_run_at",
    "updated_at",
    "scheduled_at",
    "dispatched_at",
    "lateness_seconds",
)

CLE = re.compile(r'^[+-]\s*"([^"]+)"\s*:')


def repo_defaut():
    home = os.environ.get("LOCALAPPDATA")
    if home:
        cand = os.path.join(home, "hermes")
        if os.path.isdir(os.path.join(cand, ".git")):
            return cand
    return os.getcwd()


def git_diff(repo, path, staged):
    cmd = ["git", "-C", repo, "diff", "-U0"]
    if staged:
        cmd.append("--cached")
    cmd += ["--", path]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                             errors="replace")
    except FileNotFoundError:
        sys.exit("erreur : git introuvable dans le PATH")
    if out.returncode != 0:
        sys.exit("erreur : %s\n%s" % (" ".join(cmd), (out.stderr or "").strip()))
    return out.stdout


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default=repo_defaut())
    p.add_argument("--path", default="cron/jobs.json")
    p.add_argument("--staged", action="store_true", help="tester l'index au lieu du working tree")
    p.add_argument("--noise", help="cles de runtime supplementaires, separees par des virgules")
    p.add_argument("--list-noise", action="store_true")
    p.add_argument("--quiet", action="store_true")
    a = p.parse_args()

    noise = set(NOISE_DEFAUT)
    if a.noise:
        noise |= {k.strip() for k in a.noise.split(",") if k.strip()}
    if a.list_noise:
        print("\n".join(sorted(noise)))
        return 0

    diff = git_diff(a.repo, a.path, a.staged)
    # On retire les lignes d'en-tete ET le marqueur de fin de fichier sans newline.
    changed = [l for l in diff.splitlines()
               if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    if not changed:
        if not a.quiet:
            print("aucun diff sur %s : rien a committer" % a.path)
        return 0

    defs = [l for l in changed if (CLE.match(l) is None or CLE.match(l).group(1) not in noise)]
    if not defs:
        if not a.quiet:
            print("bruit de runtime seul (%d ligne(s) d'etat) -> ne pas committer" % len(changed))
        return 0

    print("DEFINITION modifiee : %d ligne(s) sur %d — committer." % (len(defs), len(changed)))
    for l in defs:
        print("   " + l[:160])
    return 1


if __name__ == "__main__":
    sys.exit(main())
