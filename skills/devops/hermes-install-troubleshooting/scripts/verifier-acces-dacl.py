#!/usr/bin/env python3
"""verifier-acces-dacl.py - sonde d'ACCES a lancer AVANT et APRES une ecriture d'ACL de masse.

Pourquoi cette sonde existe : le bilan d'`icacls` ("N fichiers correctement traites ; echec du
traitement de 0 fichiers") ne prouve RIEN. Une propagation `/T` dont le grant porte des drapeaux
d'heritage (`(OI)(CI)`) applique ce grant aux FICHIERS aussi, ou ces drapeaux n'ont pas de sens :
mesure faite, DACL VIDEE sur ~2400 des 3188 objets d'un arbre de quatre dossiers, en rapportant
zero echec. Seul un ACCES reel tranche - et il faut la mesure AVANT pour pouvoir comparer.

Usage :
    python verifier-acces-dacl.py <racine> [<racine> ...]

A lancer avec le JETON QUI DEVRA TRAVAILLER DANS L'ARBRE ENSUITE (non eleve, celui de l'agent) : un
shell administrateur voit une realite differente et ne reproduit pas la panne.

Sortie : objets testes, objets illisibles, et la classe de chaque echec :
    ACL    = refus d'ACL (DACL vide ou protegee, proprietaire non courant) -> le droit implicite du
             proprietaire ne joue que pour l'utilisateur : reparation ELEVEE obligatoire
             (`takeown /f <dir> /r /d y` puis `icacls <dir> /reset` + `/reset /T /C`)
    USAGE  = objet en cours d'utilisation (partage) -> retenter apres arret du detenteur
    ABSENT = chemin disparu pendant le parcours (reparse point casse, objet supprime)
Code de sortie : 0 si aucun objet illisible, 1 sinon.
"""
from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes

GENERIC_READ = 0x80000000
OPEN_EXISTING = 3
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000  # ouvre aussi les DOSSIERS, pas seulement les fichiers
INVALID = ctypes.c_void_p(-1).value

# ERROR_ACCESS_DENIED / ERROR_SHARING_VIOLATION / ERROR_FILE_NOT_FOUND / ERROR_PATH_NOT_FOUND
CLASSES = {2: "ABSENT", 3: "ABSENT", 5: "ACL", 32: "USAGE", 33: "USAGE"}


class Probes:
    """CreateFileW avec un partage NUL : separe un refus d'ACL d'une violation de partage."""

    def __init__(self) -> None:
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.k.CreateFileW.restype = wintypes.HANDLE
        self.k.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
            wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
        ]
        self.k.CloseHandle.argtypes = [wintypes.HANDLE]

    def classe(self, chemin: str) -> str:
        h = self.k.CreateFileW(chemin, GENERIC_READ, 0, None, OPEN_EXISTING,
                               FILE_FLAG_BACKUP_SEMANTICS, None)
        if h and h != INVALID:
            self.k.CloseHandle(h)
            return "OUVRABLE"
        return CLASSES.get(ctypes.get_last_error(), "err%d" % ctypes.get_last_error())


def main(argv) -> int:
    racines = argv[1:] or ["."]
    probes = Probes()
    total = ko = 0
    echecs: dict = {}

    def noter(cle: str, chemin: str) -> None:
        echecs.setdefault(cle, []).append(chemin)

    def onerror(e) -> None:
        # un dossier non listable n'est pas forcement rendu par os.walk : le compter sous LISTAGE
        noter("LISTAGE", "%s (errno %s)" % (getattr(e, "filename", "?"), getattr(e, "errno", "?")))

    for racine in racines:
        for dirpath, _dirnames, filenames in os.walk(racine, onerror=onerror):
            for chemin in [dirpath] + [os.path.join(dirpath, n) for n in filenames]:
                total += 1
                c = probes.classe(chemin)
                if c != "OUVRABLE":
                    ko += 1
                    noter(c, chemin)

    print("objets testes=%d  ILLISIBLES=%d" % (total, ko))
    for cle in sorted(echecs):
        lst = echecs[cle]
        print("  %-8s %d" % (cle, len(lst)))
        for chemin in lst[:5]:
            print("       ", chemin)
        if len(lst) > 5:
            print("        ... +%d" % (len(lst) - 5))
    return 1 if ko else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
