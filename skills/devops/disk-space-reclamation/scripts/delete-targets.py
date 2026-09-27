#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase B : supprime une liste de cibles en mesurant, verifiant et cumulant le gain REEL.

Usage :
    python delete-targets.py cibles.txt             # une cible par ligne, '#' = commentaire
    python delete-targets.py cibles.txt --dry-run   # mesure seulement, ne supprime RIEN

Sortie : tableau `ETAT | octets | cumul | chemin` puis le total, a recopier dans le rapport.

Regles encodees ici (elles viennent d'erreurs deja payees) :
  - mesurer la cible EXACTE qui sera supprimee, pas le sous-chemin chiffre a l'audit ;
  - verifier l'ABSENCE apres suppression : une cible encore presente est signalee RESTE et ne compte pas
    dans le cumul (un echec partiel ne doit pas gonfler le gain annonce) ;
  - refuser un chemin racine : aucune cible d'audit n'est un volume.
"""
import os
import shutil
import stat
import sys

GB = 1e9


def size(p):
    """Taille recursive en octets (logique, pas occupee)."""
    if os.path.isfile(p) or os.path.islink(p):
        try:
            return os.path.getsize(p)
        except OSError:
            return 0
    total = 0
    for root, _dirs, files in os.walk(p):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def force_rm(p):
    """Suppression robuste : retire l'attribut lecture seule qui bloque os.remove/rmtree."""
    if os.path.isfile(p) or os.path.islink(p):
        try:
            os.chmod(p, stat.S_IWRITE)
        except OSError:
            pass
        os.remove(p)
    else:
        def onerr(func, path, _exc):
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception:
                raise
        shutil.rmtree(p, onerror=onerr)


def est_racine(p):
    """Vrai si le chemin est un volume : jamais une cible d'audit."""
    norm = os.path.abspath(p)
    return norm == os.path.splitdrive(norm)[0] + os.sep


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry-run' in sys.argv
    if not args:
        print(__doc__)
        return 2
    with open(args[0], 'r', encoding='utf-8') as f:
        cibles = [l.strip().strip('"') for l in f if l.strip() and not l.strip().startswith('#')]

    cumul = 0
    lignes = []
    for p in cibles:
        if est_racine(p):
            print(f'[REFUS] chemin racine : {p}')
            continue
        if not os.path.exists(p):
            lignes.append(('ABSENT', 0, p))
            print(f'[absent] {p}')
            continue
        av = size(p)
        if dry:
            lignes.append(('MESURE', av, p))
            print(f'[mesure] {av/GB:8.3f} Go  {p}')
            continue
        try:
            force_rm(p)
        except Exception as e:
            lignes.append(('ECHEC', 0, p))
            print(f'[ECHEC] {type(e).__name__}: {e}  {p}')
            continue
        if os.path.exists(p):
            lignes.append(('RESTE', 0, p))
            print(f'[RESTE] {p} — encore present, non compte')
            continue
        cumul += av
        lignes.append(('OK', av, p))
        print(f'[OK] {av/GB:9.3f} Go  cumul={cumul/GB:9.3f} Go  {p}')

    print('\n' + '=' * 78)
    for etat, b, p in lignes:
        print(f'{etat:7s} {b/GB:9.3f} Go  {p}')
    print('=' * 78)
    print(f'TOTAL SUPPRIME : {cumul} o = {cumul/GB:.2f} Go')
    if not dry:
        print("Controle final obligatoire : relire l'espace libre du volume EN OCTETS")
        print('  powershell -NoProfile -Command "(Get-CimInstance Win32_LogicalDisk \'
              '-Filter \"DeviceID=\'C:\'\").FreeSpace"')
    return 0


if __name__ == '__main__':
    sys.exit(main())
