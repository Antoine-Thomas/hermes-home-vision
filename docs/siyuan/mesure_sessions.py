# -*- coding: utf-8 -*-
"""Mesure la matiere exploitable de la base de sessions Hermes (lecture seule)."""
import os
import sqlite3

chemin = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "state.db")
uri = "file:" + chemin.replace(os.sep, "/") + "?mode=ro"
c = sqlite3.connect(uri, uri=True)

tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("tables dans state.db :", len(tables))
print("  ", ", ".join(sorted(tables)[:16]))

for nom in sorted(tables):
    if any(m in nom.lower() for m in ("message", "session", "conversation", "turn")):
        try:
            n = c.execute("SELECT COUNT(*) FROM %s" % nom).fetchone()[0]
            print("  %-26s %8d lignes" % (nom, n))
        except Exception as e:
            print("  %-26s erreur : %s" % (nom, e))

for nom in ("messages", "message"):
    if nom in tables:
        try:
            for role, n, taille in c.execute(
                    "SELECT role, COUNT(*), SUM(LENGTH(content)) FROM %s GROUP BY role" % nom):
                print("  role %-10s %7d messages  %8.1f Mo de texte"
                      % (role, n, (taille or 0) / 1e6))
        except Exception as e:
            print("  statistiques :", e)

# volume total des sessions, si la table existe
for nom in ("sessions", "session"):
    if nom in tables:
        cols = [r[1] for r in c.execute("PRAGMA table_info(%s)" % nom)]
        print("  colonnes de %s : %s" % (nom, ", ".join(cols[:10])))
