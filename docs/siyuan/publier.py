# -*- coding: utf-8 -*-
"""Publie un fichier Markdown dans un document SiYuan.

Usage :
  python publier.py <notebook> "<chemin du document>" <fichier.md> [--remplacer]

Exemple :
  python publier.py apprentissage-continu "/RAG local - resultat" rag.md --remplacer
"""
import io
import json
import os
import sys
import urllib.request

BASE = "http://127.0.0.1:6806"


def jeton():
    env = os.path.join(os.environ["LOCALAPPDATA"], "hermes", ".env")
    with io.open(env, encoding="utf-8") as f:
        for ligne in f:
            if ligne.startswith("SIYUAN_TOKEN="):
                return ligne.split("=", 1)[1].strip()
    raise SystemExit("SIYUAN_TOKEN introuvable dans le .env")


TOKEN = jeton()


def api(route, charge):
    req = urllib.request.Request(
        BASE + route,
        data=json.dumps(charge, ensure_ascii=True).encode("utf-8"),
        headers={"Authorization": "Token " + TOKEN, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if len(args) != 3:
        raise SystemExit(__doc__)
    notebook, chemin, fichier = args
    remplacer = "--remplacer" in sys.argv

    nbs = api("/api/notebook/lsNotebooks", {})["data"]["notebooks"]
    nid = next((n["id"] for n in nbs if n["name"] == notebook), None)
    if not nid:
        nid = api("/api/notebook/createNotebook", {"name": notebook})["data"]["notebook"]["id"]
        print("notebook cree :", notebook)

    titre = chemin.strip("/").split("/")[-1]
    # Un titre contenant une barre oblique fait creer une HIERARCHIE de documents par SiYuan
    # (constate le 15/09 : « Audit voix - corpus du 15/09/2026 » a cree trois documents :
    # « Audit voix - corpus du 15 », « 09 » et « 2026 »). On refuse net plutot que de laisser
    # une trace silencieuse.
    if "/" in chemin.strip("/"):
        raise SystemExit("titre refuse : « %s » contient une barre oblique, que SiYuan transformerait "
                         "en hierarchie de documents. Utiliser un tiret (ex. 15-09-2026)." % chemin)
    if not chemin.startswith("/"):
        chemin = "/" + chemin
    existants = api("/api/query/sql", {"stmt": "SELECT id, content FROM blocks WHERE type='d' "
                                                "AND box='%s'" % nid})["data"]
    for d in existants:
        if d["content"] == titre:
            if not remplacer:
                print("deja present (utiliser --remplacer) :", titre)
                return
            print("remplacement :", titre, api("/api/filetree/removeDocByID", {"id": d["id"]}).get("code"))

    contenu = io.open(fichier, encoding="utf-8").read()
    r = api("/api/filetree/createDocWithMd", {"notebook": nid, "path": chemin, "markdown": contenu})
    print("publication :", r.get("code"), "|", len(contenu), "caracteres")


if __name__ == "__main__":
    main()
