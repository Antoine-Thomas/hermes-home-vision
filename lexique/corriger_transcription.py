# -*- coding: utf-8 -*-
"""Corrige une transcription Whisper : remet les graphies canoniques pour la relecture.

Usage :
  python corriger_transcription.py transcription.txt            -> ecrit transcription_corrigee.txt
  python corriger_transcription.py transcription.txt -o vue.txt
  python corriger_transcription.py transcription.txt --rapport  -> detail des corrections

Le fichier d'entree n'est jamais modifie. Utile quand la synthese a prononce une graphie
phonetique (« double-vé-pé cé-èle-i », « n-jin-x ») : la transcription brute contient alors
ces graphies, illisibles a la relecture.

Attention : ce script ne « nettoie » pas les horodatages ni ne corrige les erreurs de
reconnaissance ordinaires. Il ne traite que le vocabulaire du lexique.
"""
import argparse
import io
import os

from preparer_script_tts import appliquer, charger_lexique, normaliser


def paires_retour(chemin_lexique=None):
    """Pour chaque terme : toutes ses graphies entendues possibles -> la graphie canonique."""
    import json
    chemin = chemin_lexique or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "lexique_diction.json")
    d = json.load(io.open(chemin, encoding="utf-8"))
    paires = []
    for t in d.get("termes", []):
        canonique = t["canonique"]
        for entree in [t["graphie_tts"]] + list(t.get("retour_whisper", [])):
            if entree.lower() != canonique.lower():
                paires.append((entree, canonique, canonique))
    paires.sort(key=lambda p: -len(p[0]))
    return paires


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("transcription")
    p.add_argument("-o", "--sortie", default=None)
    p.add_argument("--lexique", default=None)
    p.add_argument("--rapport", action="store_true")
    a = p.parse_args()

    if not os.path.exists(a.transcription):
        raise SystemExit("fichier introuvable : %s" % a.transcription)
    base = os.path.splitext(os.path.basename(a.transcription))[0]
    sortie = a.sortie or os.path.join(os.path.dirname(os.path.abspath(a.transcription)),
                                      base + "_corrigee.txt")
    entree = io.open(a.transcription, encoding="utf-8").read()
    paires = paires_retour(a.lexique)
    texte, compte = appliquer(entree, paires, avec_rapport=True)

    io.open(sortie, "w", encoding="utf-8", newline="\n").write(texte)
    print("entree : %s (%d caracteres, inchange)" % (a.transcription, len(entree)))
    print("sortie : %s" % sortie)
    if compte:
        print("graphies remises :")
        for terme, n in sorted(compte.items(), key=lambda x: -x[1]):
            print("   %-28s %d" % (terme, n))
    else:
        print("aucune graphie du lexique trouvee dans cette transcription")
