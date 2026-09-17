# -*- coding: utf-8 -*-
"""Prepare un script pour XTTS : remplace les termes par leur graphie phonetique validee.

Usage :
  python preparer_script_tts.py script.txt                 -> ecrit script_tts.txt
  python preparer_script_tts.py script.txt -o autre.txt
  python preparer_script_tts.py script.txt --rapport       -> detail des remplacements

Le fichier d'entree n'est JAMAIS modifie. Le lexique est lu dans lexique_diction.json,
place a cote de ce script (ou indique par --lexique).

Ne modifie aucun script XTTS existant : ce script se contente de produire un texte en
entree des generateurs (gen_voice_*.py).
"""
import argparse
import io
import json
import os
import re
import sys
import unicodedata

ICI = os.path.dirname(os.path.abspath(__file__))


def charger_lexique(chemin=None):
    chemin = chemin or os.path.join(ICI, "lexique_diction.json")
    d = json.load(io.open(chemin, encoding="utf-8"))
    paires = []
    for t in d.get("termes", []):
        # le terme canonique ET ses graphies rejetees doivent devenir la graphie TTS validee
        for entree in [t["canonique"]] + list(t.get("rejetees", [])):
            paires.append((entree, t["graphie_tts"], t["canonique"]))
    for t in d.get("tournures", []):
        for entree in t.get("eviter", []):
            paires.append((entree, t["canonique"], t["canonique"]))
    # plus long d'abord, pour que « double-vé-pé cé-èle-i » passe avant « vé-pé cé-èle-i »
    paires.sort(key=lambda p: -len(p[0]))
    return paires


def normaliser(txt):
    txt = unicodedata.normalize("NFKD", txt.lower())
    return "".join(c for c in txt if not unicodedata.combining(c))


def appliquer(texte, paires, avec_rapport=False):
    """Remplace en respectant les frontieres de mots ; insensible a la casse et aux accents."""
    compte = {}
    plat = normaliser(texte)
    # on travaille sur une version normalisee pour reperer les positions, puis on
    # reconstruit le texte a partir des positions d'origine (longueurs identiques :
    # la normalisation NFKD ne change que les diacritiques, pas le nombre de caracteres).
    for entree, sortie, canonique in paires:
        motif = re.compile(r"(?<![\w-])" + re.escape(normaliser(entree)) + r"(?![\w-])")
        positions = [m.span() for m in motif.finditer(plat)]
        if not positions:
            continue
        for debut, fin in reversed(positions):
            texte = texte[:debut] + sortie + texte[fin:]
        plat = normaliser(texte)
        compte[canonique] = compte.get(canonique, 0) + len(positions)
    if avec_rapport:
        return texte, compte
    return texte


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("script")
    p.add_argument("-o", "--sortie", default=None)
    p.add_argument("--lexique", default=None)
    p.add_argument("--rapport", action="store_true")
    a = p.parse_args()

    if not os.path.exists(a.script):
        raise SystemExit("fichier introuvable : %s" % a.script)
    sortie = a.sortie or os.path.join(os.path.dirname(os.path.abspath(a.script)), "script_tts.txt")
    entree = io.open(a.script, encoding="utf-8").read()
    paires = charger_lexique(a.lexique)
    texte, compte = appliquer(entree, paires, avec_rapport=True)

    io.open(sortie, "w", encoding="utf-8", newline="\n").write(texte)
    print("entree  : %s (%d caracteres, inchange)" % (a.script, len(entree)))
    print("sortie  : %s (%d caracteres)" % (sortie, len(texte)))
    print("lexique : %d graphies" % len(paires))
    if compte:
        print("remplacements :")
        for terme, n in sorted(compte.items(), key=lambda x: -x[1]):
            print("   %-28s %d" % (terme, n))
    else:
        print("remplacements : aucun (le script ne contient aucun terme du lexique)")
