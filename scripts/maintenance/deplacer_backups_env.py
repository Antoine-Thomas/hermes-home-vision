"""D6 - deplace les 12 sauvegardes .env hors du home Hermes.

Destination : %USERPROFILE%\\hermes-secrets-backup\\<profil>\\ (structure miroir,
sinon trois fichiers homonymes se ecraseraient).

Aucun contenu n'est affiche : seule une empreinte sha256 tronquee est imprimee,
avant puis apres le deplacement, pour prouver l'integrite.
"""
import hashlib
import os
import shutil

HOME = os.path.expandvars(r"%LOCALAPPDATA%\hermes")
DEST_ROOT = os.path.join(os.path.expanduser("~"), "hermes-secrets-backup")

# (chemin relatif au home, sous-dossier cible)
CIBLES = [
    (".env.bak_20260927_134543", "default"),
    (".env.bak_20260927_134622", "default"),
    (r"profiles\docs-writer\.env.bak_20260927_134543", "docs-writer"),
    (r"profiles\docs-writer\.env.bak_20260927_134622", "docs-writer"),
    (r"profiles\veille\.env.bak.pre_update_20260922_164000", "veille"),
    (r"profiles\veille\.env.bak.update_20260919_102818", "veille"),
    (r"profiles\watch\.env.avant_rotation_watch", "watch"),
    (r"profiles\watch\.env.bak.fix_espace_20260927_010912", "watch"),
    (r"profiles\watch\.env.bak.pre_update_20260922_164000", "watch"),
    (r"profiles\watch\.env.bak.update_20260919_102818", "watch"),
    (r"profiles\watch\.env.bak_20260927_134543", "watch"),
    (r"profiles\watch\.env.bak_20260927_134622", "watch"),
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloc in iter(lambda: f.read(65536), b""):
            h.update(bloc)
    return h.hexdigest()[:16]


print("CIBLES : %d" % len(CIBLES))
manquants = []
for rel, _ in CIBLES:
    if not os.path.isfile(os.path.join(HOME, rel)):
        manquants.append(rel)
if manquants:
    print("ABSENTS (arrete) :")
    for m in manquants:
        print("   " + m)
    raise SystemExit(1)

for rel, profil in CIBLES:
    d = os.path.join(DEST_ROOT, profil)
    os.makedirs(d, exist_ok=True)

resultats = []
for rel, profil in CIBLES:
    src = os.path.join(HOME, rel)
    dst = os.path.join(DEST_ROOT, profil, os.path.basename(rel))
    av = sha(src)
    taille = os.path.getsize(src)
    shutil.move(src, dst)
    ap = sha(dst) if os.path.isfile(dst) else "ABSENT"
    reste = os.path.isfile(src)
    resultats.append((profil + "/" + os.path.basename(rel), taille, av, ap, reste))

print("%-58s %10s %-18s %-18s %s" % ("fichier", "octets", "sha256 avant", "sha256 apres", "source encore la"))
ok = True
for nom, taille, av, ap, reste in resultats:
    etat = "IDENTIQUE" if av == ap else "ECART"
    if av != ap or reste:
        ok = False
    print("%-58s %10d %-18s %-18s %-16s %s" % (nom, taille, av, ap, "oui" if reste else "non", etat))
print("VERDICT :", "12/12 deplaces, empreintes identiques, aucune source restante" if ok else "ECART DETECTE")
