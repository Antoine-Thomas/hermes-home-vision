# -*- coding: utf-8 -*-
"""Ajoute une ligne a la section « Pieges » d'un document SiYuan existant.

Usage : python ajouter_piege.py "<notebook>" "<titre du document>" "texte de la puce"

Utilise insertBlock apres le dernier element de la liste qui suit le titre « ## Pieges »,
afin de rester dans la section au lieu d'ecrire a la fin du document.
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
    raise SystemExit("SIYUAN_TOKEN introuvable")


TOKEN = jeton()


def api(route, charge):
    req = urllib.request.Request(
        BASE + route,
        data=json.dumps(charge, ensure_ascii=True).encode("utf-8"),
        headers={"Authorization": "Token " + TOKEN, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    notebook, titre, texte = sys.argv[1], sys.argv[2], sys.argv[3]
    nbs = api("/api/notebook/lsNotebooks", {})["data"]["notebooks"]
    box = next(n["id"] for n in nbs if n["name"] == notebook)
    docs = api("/api/query/sql", {"stmt": "SELECT id FROM blocks WHERE type='d' AND box='%s' "
                                          "AND content='%s'" % (box, titre)})["data"]
    if not docs:
        raise SystemExit("document introuvable : %s / %s" % (notebook, titre))
    racine = docs[0]["id"]

    blocs = api("/api/query/sql", {"stmt": "SELECT id, type, subtype, content FROM blocks "
                                           "WHERE root_id='%s' ORDER BY sort" % racine})["data"]
    i_pieges = None
    for i, b in enumerate(blocs):
        if b["content"].strip().startswith("## Pièges") or b["content"].strip() == "Pièges":
            i_pieges = i
            break
    if i_pieges is None:
        raise SystemExit("section « ## Pièges » introuvable dans le document")

    dernier = None
    for b in blocs[i_pieges + 1:]:
        if b["content"].strip().startswith("## "):     # section suivante
            break
        if b["subtype"] in ("o", "u", "i") or b["type"] == "i":   # element de liste
            dernier = b["id"]
    if dernier is None:
        raise SystemExit("aucun element de liste trouve sous « ## Pièges »")

    r = api("/api/block/insertBlock", {"previousID": dernier, "dataType": "markdown",
                                       "data": texte if texte.startswith("-") else "- " + texte})
    print("insertion :", r.get("code"), r.get("msg") or "")
    k = api("/api/block/getBlockKramdown", {"id": racine})["data"]["kramdown"]
    for ligne in k.splitlines():
        if "décalage de recadrage" in ligne or "recalage par image" in ligne:
            print("present dans le document :", ligne.strip()[:120])


if __name__ == "__main__":
    main()
