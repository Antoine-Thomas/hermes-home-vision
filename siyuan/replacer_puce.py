# -*- coding: utf-8 -*-
"""Deplace une puce vers la fin de la section « Pieges » d'un document SiYuan.

Contexte : un premier insertBlock s'est appuye sur un tri SQL (`ORDER BY sort`) qui ne rend
pas l'ordre du document (sort est relatif au parent). La puce a donc atterri ailleurs.
Ici on utilise /api/block/getChildBlocks, qui rend les enfants DANS L'ORDRE.

Usage : python replacer_puce.py <id_document> <id_puce_a_deplacer>
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
    doc, puce = sys.argv[1], sys.argv[2]
    enfants = api("/api/block/getChildBlocks", {"id": doc})["data"]
    print("enfants du document :", len(enfants))

    i_pieges = None
    for i, e in enumerate(enfants):
        if e.get("type") == "h" and e.get("content", "").strip() == "Pièges":
            i_pieges = i
            break
    if i_pieges is None:
        raise SystemExit("section « Pièges » introuvable")

    dernier = None
    for e in enfants[i_pieges + 1:]:
        if e.get("type") == "h":
            break
        if e.get("type") in ("i", "l", "p"):
            dernier = e["id"]
    if dernier is None:
        raise SystemExit("aucun element sous « Pièges »")
    print("dernier element de la section Pièges :", dernier)

    contenu = None
    for e in enfants:
        if e["id"] == puce:
            contenu = e.get("content") or ""
    if contenu is None:
        r = api("/api/query/sql", {"stmt": "SELECT content FROM blocks WHERE id='%s'" % puce})["data"]
        contenu = r[0]["content"] if r else None
    if not contenu:
        raise SystemExit("contenu de la puce introuvable")

    print("suppression de la puce mal placee :", api("/api/block/deleteBlock", {"id": puce}).get("code"))
    r = api("/api/block/insertBlock", {"previousID": dernier, "dataType": "markdown",
                                       "data": "- " + contenu.strip()})
    print("reinsertion en fin de section Pièges :", r.get("code"))

    # controle : ordre reel des enfants
    apres = api("/api/block/getChildBlocks", {"id": doc})["data"]
    j = next(k for k, e in enumerate(apres) if e.get("type") == "h" and e.get("content", "").strip() == "Pièges")
    print("\nsection Pièges apres correction :")
    for e in apres[j:j + 6]:
        print("   %-2s %s" % (e.get("type"), (e.get("content") or "")[:110]))


if __name__ == "__main__":
    main()
