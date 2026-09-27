"""Copie ciblee pre-update : config, .env par profil, memories, state.db (backup API SQLite).

Les gateways ecrivent pendant la copie -> sqlite3.Connection.backup, jamais un cp brut.
"""
import os
import shutil
import sqlite3
import time

HOME = os.path.expandvars(r"%LOCALAPPDATA%\hermes")
STAMP = time.strftime("%Y%m%d_%H%M%S")
DEST = os.path.join(HOME, "backups", "pre_update_" + STAMP)
os.makedirs(DEST, exist_ok=True)

copied = []
errors = []

targets = [
    "config.yaml",
    ".env",
    "memories/MEMORY.md",
    "memories/USER.md",
    "profiles/docs-writer/.env",
    "profiles/veille/.env",
    "profiles/watch/.env",
]
for rel in targets:
    src = os.path.join(HOME, rel)
    if not os.path.exists(src):
        errors.append("ABSENT " + rel)
        continue
    dst = os.path.join(DEST, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    copied.append(rel)

dbs = [
    "state.db",
    "profiles/docs-writer/state.db",
    "profiles/veille/state.db",
    "profiles/watch/state.db",
]
for rel in dbs:
    src = os.path.join(HOME, rel)
    if not os.path.exists(src):
        errors.append("ABSENT " + rel)
        continue
    dst = os.path.join(DEST, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    src_conn = sqlite3.connect(src, timeout=30)
    dst_conn = sqlite3.connect(dst)
    with dst_conn:
        src_conn.backup(dst_conn)
    src_conn.close()
    dst_conn.close()
    copied.append(rel + " (sqlite backup)")

print("DEST =", DEST)
print("--- copies ---")
for c in copied:
    print("  ok", c)
print("--- erreurs ---")
print("  aucune" if not errors else "\n".join("  " + e for e in errors))

total = 0
for root, _dirs, files in os.walk(DEST):
    for f in files:
        total += os.path.getsize(os.path.join(root, f))
print("--- taille totale: %.1f Mo ---" % (total / 1024 / 1024))
