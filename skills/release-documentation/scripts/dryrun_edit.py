"""Montre le diff d'une retouche de fichier AVANT de l'ecrire.

Usage (python du runtime, depuis la racine du depot) :

    python scripts/dryrun_edit.py --fichier <chemin> --avant '<texte exact>' --apres '<texte>'
    python scripts/dryrun_edit.py --fichier <chemin> --avant '<texte exact>' --apres '<texte>' --write

Sortie : diff unifie + comptes de lignes et de caracteres. Rien n'est ecrit sans `--write`.
Le fichier est lu en newline='' (fins de ligne du fichier preservees), et `--avant` doit matcher
exactement une fois : 0 ou 2+ occurrences = refus, fichier intact.

Pour une retouche plus large (plusieurs remplacements, ou bornes plutot qu'un texte exact) :
copier ce script dans cache/scratch/, y remplacer les deux chaines par des bornes
(`i = src.index(DEBUT)` / `j = src.index(FIN, i) + len(FIN)`) et garder la meme sortie diff --
c'est ce diff qui est relu par l'operateur avant l'ecriture.
"""
import argparse
import difflib
import io
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fichier", required=True)
    p.add_argument("--avant", required=True)
    p.add_argument("--apres", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--context", type=int, default=3)
    a = p.parse_args()

    src = io.open(a.fichier, encoding="utf-8", newline="").read()
    n = src.count(a.avant)
    if n != 1:
        sys.exit("refus : %d occurrence(s) de --avant (il en faut exactement 1)" % n)

    out = src.replace(a.avant, a.apres, 1)
    print("".join(difflib.unified_diff(
        src.splitlines(True), out.splitlines(True),
        fromfile="a/" + a.fichier, tofile="b/" + a.fichier, n=a.context)))
    print("lignes : %d -> %d | caracteres : %d -> %d"
          % (src.count("\n"), out.count("\n"), len(src), len(out)))

    if not a.write:
        print("dry-run : rien ecrit (ajouter --write pour appliquer)")
        return
    io.open(a.fichier, "w", encoding="utf-8", newline="").write(out)
    print("ECRIT")


if __name__ == "__main__":
    main()
