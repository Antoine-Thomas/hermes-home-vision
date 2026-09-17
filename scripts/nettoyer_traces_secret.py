#!/usr/bin/env python3
"""Masque un motif de secret dans les traces locales de Hermes (historique + base de sessions).

Usage
    python scripts/nettoyer_traces_secret.py --motif 'github_pat_[A-Za-z0-9_]{20,}'            # DryRun (defaut)
    python scripts/nettoyer_traces_secret.py --motif 'github_pat_[A-Za-z0-9_]{20,}' --apply

Principes
    - La recherche se fait par MOTIF, jamais par valeur : la valeur d'un secret n'a pas a etre
      connue ni affichee. Le masque remplace chaque occurrence par des 'X' de meme longueur, donc
      les offsets des fichiers binaires ne bougent pas.
    - Sauvegarde complete avant toute ecriture (state.db, -wal, -shm) dans backups/.
    - Couvre : etat de session (state.db, tables *messages* + index FTS, tout couple
      table/colonne de type TEXT), fichiers d'historique (.*_history), et verifie a la fin
      qu'il ne reste aucune occurrence.
    - Ne touche a rien d'autre : pas de suppression de messages, pas de changement de schema.
    - Masquer ne rend PAS un secret inoffensif : la seule action qui compte est sa revocation.

Sortie : tableau des emplacements trouves, puis verification finale (0 occurrence attendu).
"""
import argparse
import pathlib
import re
import shutil
import sqlite3
import sys
import time

RACINE = pathlib.Path(__file__).resolve().parent.parent
MASQUE = 'X'


def backup(cibles, dossier):
    dossier.mkdir(parents=True, exist_ok=True)
    faits = []
    for c in cibles:
        if c.exists():
            dst = dossier / c.name
            shutil.copy2(c, dst)
            faits.append(f'{c.name} ({c.stat().st_size / 1048576:.1f} Mo)')
    return faits


def tables_text(con):
    """(table, colonne) de type TEXT ou sans type, hors index FTS."""
    out = []
    for (nom,) in con.execute("select name from sqlite_master where type in ('table','view')"):
        if nom.endswith('_fts') or nom.endswith('_fts_trigram') or nom.endswith('_fts_data') \
           or nom.endswith('_fts_idx') or nom.endswith('_fts_content') or nom.endswith('_fts_docsize') \
           or nom.endswith('_fts_config'):
            continue
        try:
            cols = [(r[1], (r[2] or '').upper()) for r in con.execute(f'pragma table_info("{nom}")')]
        except sqlite3.Error:
            continue
        for col, typ in cols:
            if typ in ('', 'TEXT', 'VARCHAR', 'CLOB', 'JSON', 'CHARACTER'):
                out.append((nom, col))
    return out


def tables_fts(con):
    return [n for (n,) in con.execute("select name from sqlite_master where type='table' and (name like '%_fts' or name like '%_fts_trigram')")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--motif', required=True, help='expression reguliere du secret (jamais sa valeur)')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--timeout', type=int, default=60)
    args = ap.parse_args()

    pat = re.compile(args.motif)
    patb = re.compile(args.motif.encode('utf-8'))
    masque_b = lambda m: b'X' * len(m.group(0))
    # filtre SQL rapide : prefixe litteral du motif, pour ne pas appeler la regex sur toute la base
    special = set('[](){}*+?.|^$') | {chr(92)}
    lit = args.motif
    for _k, _c in enumerate(args.motif):
        if _c in special:
            lit = args.motif[:_k]
            break
    if not lit:
        print('motif trop generique : donner un prefixe litteral (ex: github_pat_)')
        return 2
    filtre = '%' + lit + '%'
    masque = lambda m: MASQUE * len(m.group(0))          # noqa: E731
    db = RACINE / 'state.db'
    hist = [p for p in RACINE.glob('.*_history')]
    ts = time.strftime('%Y%m%d_%H%M%S')
    mode = 'APPLY' if args.apply else 'DRYRUN'
    print(f'mode {mode} | motif {args.motif!r} | racine {RACINE}')
    print()

    # ---------------------------------------------------------------- fichiers texte
    print('1. fichiers d\'historique')
    total_fichiers = 0
    for f in hist:
        data = f.read_bytes()
        trouves = patb.findall(data)
        if not trouves:
            print(f'   {f.name} : 0 occurrence')
            continue
        total_fichiers += len(trouves)
        print(f'   {f.name} : {len(trouves)} occurrence(s), longueurs {sorted({len(x) for x in trouves})}')
        if args.apply:
            f.write_bytes(patb.sub(masque_b, data))
            print(f'   -> masque ({len(trouves)})')

    # ---------------------------------------------------------------- base de sessions
    print()
    print('2. base de sessions (state.db)')
    if not db.exists():
        print(f'   {db} absent')
    else:
        doss = RACINE / 'backups' / f'token_cleanup_{ts}'
        if args.apply:
            faits = backup([db, pathlib.Path(str(db) + '-wal'), pathlib.Path(str(db) + '-shm')], doss)
            print(f'   sauvegarde : {doss.name} -> ' + ', '.join(faits))
        con = sqlite3.connect(f'file:{db}?mode=rwc', uri=True, timeout=args.timeout)
        con.create_function('masquer', 1, lambda s: pat.sub(masque, s) if isinstance(s, str) else s)
        total_db = 0
        paires = tables_text(con)
        for tbl, col in paires:
            try:
                n = con.execute(f'select count(*) from "{tbl}" where "{col}" like ?', ('%' + args.motif.replace('[A-Za-z0-9_]', '').replace('{20,}', '') + '%',)).fetchone()[0]
            except sqlite3.Error:
                n = 0
            if not n:
                continue
            # comptage reel par motif (le LIKE approximatif ne sert qu'a filtrer les candidats)
            try:
                rows = con.execute(f'select rowid, "{col}" from "{tbl}" where "{col}" like ?', (filtre,)).fetchall()
            except sqlite3.Error:
                # vue ou table sans rowid : on ne lit que la colonne
                rows = [(None, r[0]) for r in con.execute(f'select "{col}" from "{tbl}" where "{col}" like ?', (filtre,)).fetchall()]
            occ = sum(len(pat.findall(r[1])) for r in rows if isinstance(r[1], str))
            if not occ:
                continue
            total_db += occ
            print(f'   {tbl}.{col} : {len(rows)} ligne(s), {occ} occurrence(s)')
            if args.apply:
                try:
                    con.execute(f'update "{tbl}" set "{col}" = masquer("{col}") where "{col}" like ?', (filtre,))
                    con.commit()
                    print(f'   -> masque')
                except sqlite3.Error as e:
                    print(f'   !! echec : {e}')
        # index FTS : reconstruction depuis la table de contenu (external content) ou masquage direct
        if args.apply:
            print('   reconstruction des index FTS')
            for fts in tables_fts(con):
                try:
                    con.execute(f'insert into "{fts}"("{fts}") values(\'rebuild\')')
                    con.commit()
                    print(f'   -> {fts} reconstruit')
                except sqlite3.Error as e:
                    try:
                        con.execute(f'update "{fts}" set content = masquer(content) where content like ?', (filtre,))
                        con.commit()
                        print(f'   -> {fts} masque directement')
                    except sqlite3.Error as e2:
                        print(f'   !! {fts} : {e} / {e2}')
            try:
                r = con.execute('pragma wal_checkpoint(truncate)').fetchone()
                print(f'   -> checkpoint wal : {r}')
            except sqlite3.Error as e:
                print(f'   checkpoint wal impossible : {e}')
            try:
                con.execute('vacuum')
                print('   -> vacuum ok')
            except sqlite3.Error as e:
                print(f'   vacuum impossible (base utilisee) : {e} — sans consequence, les pages seront reutilisees')
        con.close()
        print(f'   total base : {total_db} occurrence(s)')

    # ---------------------------------------------------------------- verification
    print()
    print('3. verification')
    restants = 0
    for f in hist:
        restants += len(patb.findall(f.read_bytes()))
    lignes_fts = 0
    if db.exists():
        con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
        con.create_function('nb_occ', 1, lambda s: len(pat.findall(s)) if isinstance(s, str) else 0)
        for tbl, col in tables_text(con):
            try:
                restants += con.execute(f'select coalesce(sum(nb_occ("{col}")),0) from "{tbl}"').fetchone()[0]
            except sqlite3.Error:
                pass
        for fts in tables_fts(con):
            try:
                lignes_fts += con.execute(f'select count(*) from "{fts}" where "{fts}" like ?', (filtre,)).fetchone()[0]
            except sqlite3.Error:
                pass
        con.close()
        wal = pathlib.Path(str(db) + '-wal')
        if wal.exists():
            restants += len(patb.findall(wal.read_bytes()))
    print(f'   occurrences EXACTES du secret restantes (fichiers + tables + wal) : {restants}')
    if lignes_fts:
        print(f'   index FTS : {lignes_fts} ligne(s) portant le prefixe litteral (faux positifs normaux : le motif lui-meme)')
    print()
    print('   RAPPEL : masquer ne rend pas un secret inoffensif.' if restants == 0 and args.apply else '')
    return 0 if restants == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
