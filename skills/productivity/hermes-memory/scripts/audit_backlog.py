"""Inventaire LECTURE SEULE des propositions de memoire en attente.

    python scripts/audit_backlog.py            # tableau + verdict d'ancre
    python scripts/audit_backlog.py --json     # meme chose, exploitable

Pour chaque proposition de <HERMES_HOME>/pending/memory/*.json, imprime une ligne par operation avec
son ancre, puis le verdict par fichier. `old_text` est cherche dans le fichier nomme par
`payload.target` (memory -> MEMORY.md, user -> USER.md) : 1 occurrence = ancre vivante, 0 = l'entree a
ete reecrite depuis le depot de la proposition (morte), 2+ = ambigue.

Deux pieges que ce script traite et qu'un chargement a la main rate :

  * une proposition `batch` porte ses operations dans `payload["operations"]`, mais une proposition
    `replace` simple les porte **a plat sur `payload`** (un `rec["operations"]` en tete renvoie vide
    et fait croire que toutes les propositions sont vides) ;
  * les fichiers de memoire sont en CRLF alors que `old_text` est en LF : sans normalisation, toute
    ancre multi-ligne compte 0 et est declaree morte a tort.

Le script n'ECRIT RIEN — aucune proposition n'est appliquee ni rejetee : la decision revient a
l'utilisateur (`/memory pending`).
"""
import argparse
import datetime
import glob
import json
import os

HERMES = os.environ.get("HERMES_HOME") or os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "hermes")
PENDING = os.path.join(HERMES, "pending", "memory")
MEMORIES = os.path.join(HERMES, "memories")
STORES = {"memory": "MEMORY.md", "user": "USER.md"}


def load_store(kind):
    """Contenu du store, fins de ligne normalisees en LF (le disque est en CRLF)."""
    path = os.path.join(MEMORIES, STORES[kind])
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read().replace("\r\n", "\n")


def operations(payload):
    """Les operations du batch, ou l'operation unique ecrite a plat sur le payload."""
    return payload.get("operations") or [payload]


def audit():
    stores = {kind: load_store(kind) for kind in STORES}
    rows = []
    files = sorted(glob.glob(os.path.join(PENDING, "*.json")), key=os.path.getmtime)
    for path in files:
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
        payload = rec.get("payload") or rec
        kind = payload.get("target", "memory")
        store = stores.get(kind)
        for i, op in enumerate(operations(payload)):
            old = op.get("old_text")
            occ = None
            if old is None:
                anchor = "(add)"
            elif store is None:
                anchor = "?"
            else:
                occ = store.count(old.replace("\r\n", "\n"))
                anchor = "VIVANTE" if occ == 1 else ("MORTE" if occ == 0 else "AMBIGUE(%d)" % occ)
            rows.append({
                "id": rec.get("id") or os.path.basename(path)[:8],
                "file": os.path.basename(path),
                "target": kind,
                "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%d/%m %H:%M"),
                "op": i,
                "action": op.get("action"),
                "anchor": anchor,
                "occurrences": occ,
                "old_text": (old or "")[:70],
            })
    return files, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="sortie JSON au lieu du tableau")
    a = ap.parse_args()

    files, rows = audit()
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    print("%-10s %-7s %-12s %-3s %-8s %-11s %s"
          % ("id", "cible", "mtime", "op", "action", "ancre", "old_text"))
    for r in rows:
        print("%-10s %-7s %-12s %-3d %-8s %-11s %s"
              % (r["id"], r["target"], r["mtime"], r["op"], r["action"], r["anchor"],
                 r["old_text"].replace("\n", "\\n")))

    by_id = {}
    for r in rows:
        by_id.setdefault(r["id"], set()).add(r["anchor"].split("(")[0])
    dead = sorted(i for i, v in by_id.items() if "MORTE" in v)
    mixed = sorted(i for i, v in by_id.items() if "MORTE" in v and "VIVANTE" in v)
    print("\n%d proposition(s), %d operation(s)" % (len(files), len(rows)))
    print("ancre morte        : " + (", ".join(dead) or "aucune"))
    print("mixte (morte+vive) : " + (", ".join(mixed) or "aucune"))
    print("Rien n'a ete applique : decider avec /memory pending.")


if __name__ == "__main__":
    main()
