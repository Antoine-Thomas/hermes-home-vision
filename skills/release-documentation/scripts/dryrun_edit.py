"""Montre le diff d'une retouche de fichier AVANT de l'ecrire, puis l'applique avec --write.

Usage (python du runtime, depuis la racine du depot) :

    # 1. remplacer un texte exact (defaut)
    python scripts/dryrun_edit.py --fichier <chemin> --avant '<texte exact>' --apres '<texte>'

    # 2. ajouter un bloc en fin de fichier
    python scripts/dryrun_edit.py --fichier <chemin> --mode append --text-file <bloc.md>

    # 3. inserer un bloc AVANT une ligne precise (l'ancre sert de borne, elle reste en place)
    python scripts/dryrun_edit.py --fichier <chemin> --mode insert-before --ancre '<ligne exacte>' \\
        --text-file <bloc.md>

    # rien n'est ecrit sans --write
    python scripts/dryrun_edit.py --fichier <chemin> --mode append --text-file <bloc.md> --write

Sortie : diff unifie + comptes de lignes et de caracteres. Rien n'est ecrit sans `--write`.

Regles que ce script fait respecter :

- **Le nouveau texte passe par un FICHIER (`--text-file`), pas par la ligne de commande.** Un bloc de
  plusieurs lignes ne peut pas passer en argument : les fins de ligne du fichier cible (souvent CRLF)
  ne sont pas reproductibles dans un guillemet bash, et les antislashs ou guillemets imbriques y sont
  manges. Ecrire le bloc dans `cache/scratch/` puis le passer par `--text-file`.
- **Les fins de ligne du fichier cible sont preservees** : lecture en `newline=''`, convention
  detectee, texte entrant normalise dessus avant insertion. Un fichier CRLF edite en LF devient mixte
  et le diff affiche alors chaque ligne comme modifiee.
- **L'ancre doit matcher EXACTEMENT une fois** (0 ou 2+ occurrences = refus, fichier intact) : une
  ancre ambigue insererait le bloc au mauvais endroit sans le dire.
- Une ecriture qui ne changerait rien est refusee (mauvais fichier, bloc vide).
"""
import argparse
import difflib
import io
import os
import sys


def _read_text(path, what):
    if not os.path.isfile(path):
        sys.exit("refus : %s introuvable (%s)" % (what, path))
    txt = io.open(path, encoding="utf-8", newline="").read()
    if not txt.strip():
        sys.exit("refus : %s vide (%s)" % (what, path))
    return txt


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fichier", required=True)
    p.add_argument("--mode", choices=("replace", "append", "insert-before"), default="replace")
    p.add_argument("--avant", help="mode replace : texte exact a remplacer")
    p.add_argument("--apres", help="mode replace : texte de remplacement (ou --text-file)")
    p.add_argument("--ancre", help="mode insert-before : ligne devant laquelle inserer")
    p.add_argument("--text-file", help="fichier portant le texte a inserer (recommande)")
    p.add_argument("--write", action="store_true")
    p.add_argument("--context", type=int, default=3)
    a = p.parse_args()

    src = _read_text(a.fichier, "fichier cible")
    eol = "\r\n" if "\r\n" in src else "\n"

    if a.mode == "replace":
        if not a.avant:
            sys.exit("refus : --mode replace exige --avant")
        incoming = _read_text(a.text_file, "--text-file") if a.text_file else a.apres
        if incoming is None:
            sys.exit("refus : donner --apres ou --text-file")
        # le texte entrant peut venir d'un fichier ecrit en LF : normaliser sur la convention cible
        incoming = incoming.replace("\r\n", "\n").replace("\n", eol)
        n = src.count(a.avant)
        if n != 1:
            sys.exit("refus : %d occurrence(s) de --avant (il en faut exactement 1)" % n)
        out = src.replace(a.avant, incoming, 1)

    elif a.mode == "append":
        block = _read_text(a.text_file, "--text-file").replace("\r\n", "\n").rstrip("\n")
        block = block.replace("\n", eol)
        base = src if src.endswith(eol) else src + eol
        out = base + eol + block + eol

    else:  # insert-before
        if not a.ancre:
            sys.exit("refus : --mode insert-before exige --ancre")
        block = _read_text(a.text_file, "--text-file").replace("\r\n", "\n").strip("\n")
        block = block.replace("\n", eol) + eol
        n = src.count(a.ancre)
        if n != 1:
            sys.exit("refus : %d occurrence(s) de --ancre (il en faut exactement 1)" % n)
        i = src.index(a.ancre)
        out = src[:i] + block + eol + src[i:]

    if out == src:
        sys.exit("refus : le contenu resultant est identique a l'original (rien a ecrire)")

    print("fins de ligne du fichier : %r" % eol)
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
