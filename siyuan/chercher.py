# -*- coding: utf-8 -*-
"""Interroge la base vectorielle locale (RAG).

Usage :
  python chercher.py "ma question"            # 5 meilleurs fragments
  python chercher.py "ma question" -k 8       # 8 fragments
  python chercher.py "ma question" -s skill   # restreint a une source
                                               # (siyuan, skill, script_v4, wordpress)

Le modele e5 exige le prefixe "query: " cote requete (et "passage: " cote index) :
sans lui, la pertinence s'effondre. C'est fait ici.
"""
import argparse
import io
import json
import os
import sys

RACINE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(RACINE, "index.faiss")
CHUNKS = os.path.join(RACINE, "chunks.jsonl")
MANIFESTE = os.path.join(RACINE, "manifeste.json")


def charger():
    import faiss
    from sentence_transformers import SentenceTransformer

    if not os.path.exists(INDEX):
        raise SystemExit("index absent : lancer indexer.py d'abord")
    manifeste = json.load(io.open(MANIFESTE, encoding="utf-8"))
    index = faiss.read_index(INDEX)
    fragments = [json.loads(l) for l in io.open(CHUNKS, encoding="utf-8")]
    modele = SentenceTransformer(manifeste["modele"], device="cpu")
    return index, fragments, modele, manifeste


def chercher(question, k=5, source=None, extrait=320):
    index, fragments, modele, _ = charger()
    vecteur = modele.encode(["query: " + question], normalize_embeddings=True,
                            convert_to_numpy=True)
    profondeur = k * 6 if source else k
    scores, ids = index.search(vecteur.astype("float32"), profondeur)
    resultats = []
    for score, i in zip(scores[0], ids[0]):
        if i < 0 or i >= len(fragments):
            continue
        f = fragments[i]
        if source and f.get("source") != source:
            continue
        resultats.append((float(score), f))
        if len(resultats) >= k:
            break
    return resultats


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("-k", type=int, default=5)
    p.add_argument("-s", "--source", default=None)
    p.add_argument("--complet", action="store_true", help="afficher le fragment entier")
    a = p.parse_args()
    for score, f in chercher(a.question, a.k, a.source):
        texte = f["texte"] if a.complet else f["texte"][:320].replace("\n", " ")
        ou = f.get("notebook") or f.get("source")
        print("--- %.3f | %s | %s | partie %s" % (score, f["source"], f["titre"], f.get("partie")))
        print("    %s" % ou)
        print("    %s" % texte)
        print()
