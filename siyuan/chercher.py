# -*- coding: utf-8 -*-
"""Interroge la base vectorielle locale (RAG) — recherche hybride.

Vectoriel seul : rate les termes rares et le jargon (« lèvres », « connector-11 », « 45 s »).
Lexical seul  : rate les reformulations.
Ici les deux sont combines par fusion de rangs (RRF), ce qui corrige les deux cas.

Usage :
  python chercher.py "ma question"            # 5 meilleurs fragments
  python chercher.py "ma question" -k 8       # 8 fragments
  python chercher.py "ma question" -s skill   # siyuan|skill|script_v4|wordpress
  python chercher.py "ma question" -v         # afficher le detail des rangs

Le modele e5 exige le prefixe "query: " cote requete (et "passage: " cote index) :
sans lui, la pertinence s'effondre. C'est fait ici.
"""
import argparse
import io
import json
import math
import os
import re
import sys
import unicodedata

RACINE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(RACINE, "index.faiss")
CHUNKS = os.path.join(RACINE, "chunks.jsonl")
MANIFESTE = os.path.join(RACINE, "manifeste.json")

VIDES = set("""le la les un une des du de d a au aux et ou ou mais donc or ni car que qui quoi dont
où ce cet cette ces son sa ses leur leurs mon ma mes ton ta tes notre nos votre vos il elle ils
elles je tu nous vous on se s ne pas plus moins tres trop est sont etait etaient ete etre avoir a
ai as ont avait pour par avec sans sur sous dans en vers chez entre the of a an is are to and for
with on in at by from""".split())

# Expansion de requete : le vocabulaire du domaine n'est pas celui des regles redigees a
# l'epoque (une question dit « flou », la regle dit « mou », « mal definie », « recadrage »).
# Chaque famille ajoute une seconde requete, fusionnee ensuite par RRF.
FAMILLES = {
    ("flou", "floue", "flous", "defini", "definition", "nettete", "pique", "mou", "molle"): [
        "mou", "mal definie", "nettete", "contour", "recadrage", "accentuation", "pique"],
    ("levre", "levres"): ["bouche", "contour des levres", "bord des levres"],
    ("lent", "lente", "lenteur", "ralenti", "cadence"): ["s/it", "cadence", "relancer le processus"],
    ("saut", "sauts", "raccord", "raccords", "jointure", "jointures"): [
        "MAD", "ping-pong", "phase", "segment", "raccord"],
    ("fantome", "fantomes", "double"): ["contour", "densite de contours", "grave"],
    ("voix", "diction", "prononciation", "accent"): ["graphie", "phonetique", "XTTS", "Whisper"],
    ("token", "jeton", "authentification", "connexion"): [
        "api.token", "accessAuthCode", "Authorization", "Auth failed"],
    ("ram", "vram", "memoire"): ["VRAM", "offload", "quantification", "GGUF"],
}


def expansions(question):
    """Renvoie les requetes derivees (synonymes du domaine) pour une question."""
    m = set(mots(question))
    ajouts = []
    for famille, synonymes in FAMILLES.items():
        if m & set(famille):
            ajouts += synonymes
    if not ajouts:
        return []
    return [question + " " + " ".join(dict.fromkeys(ajouts))]


def normaliser(txt):
    """Minuscules, sans accents, pour comparer des mots (« lèvres » et « levres »)."""
    txt = unicodedata.normalize("NFKD", txt.lower())
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt


def mots(txt):
    return [m for m in re.split(r"[^a-z0-9]+", normaliser(txt)) if m and m not in VIDES and len(m) > 1]


class Lexical:
    """BM25 maison : suffisant pour 1 500 fragments, sans dependance supplementaire."""

    def __init__(self, documents):
        self.docs = [mots(d) for d in documents]
        self.taille = [len(d) for d in self.docs]
        self.moyenne = sum(self.taille) / max(1, len(self.taille))
        self.freq = []
        self.df = {}
        for d in self.docs:
            f = {}
            for m in d:
                f[m] = f.get(m, 0) + 1
            self.freq.append(f)
            for m in f:
                self.df[m] = self.df.get(m, 0) + 1

    def scores(self, requete):
        n = len(self.docs)
        res = []
        for i, f in enumerate(self.freq):
            s = 0.0
            for m in requete:
                if m not in f:
                    continue
                df = self.df.get(m, 0)
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                tf = f[m]
                k1, b = 1.5, 0.75
                s += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * self.taille[i] / self.moyenne))
            if s > 0:
                res.append((s, i))
        res.sort(reverse=True)
        return res


def charger():
    import faiss
    from sentence_transformers import SentenceTransformer

    if not os.path.exists(INDEX):
        raise SystemExit("index absent : lancer indexer.py d'abord")
    manifeste = json.load(io.open(MANIFESTE, encoding="utf-8"))
    index = faiss.read_index(INDEX)
    fragments = [json.loads(l) for l in io.open(CHUNKS, encoding="utf-8")]
    lex = Lexical([f["texte"] for f in fragments])
    modele = None
    return index, fragments, lex, modele, manifeste


def charger_modele(manifeste):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(manifeste["modele"], device="cpu")


def chercher(question, k=5, source=None, detail=False):
    index, fragments, lex, modele, manifeste = charger()
    modele = charger_modele(manifeste)

    requetes = [question] + expansions(question)
    n_vec = min(60, len(fragments))

    fusion = {}
    rangs_vectoriels, rangs_lexicaux = {}, {}
    for rang_q, requete in enumerate(requetes):
        poids = 1.0 if rang_q == 0 else 0.6      # la question d'origine pese plus lourd
        vecteur = modele.encode(["query: " + requete], normalize_embeddings=True,
                                convert_to_numpy=True).astype("float32")
        scores_v, ids_v = index.search(vecteur, n_vec)
        for rang, (s, i) in enumerate(zip(scores_v[0], ids_v[0])):
            if i < 0:
                continue
            i = int(i)
            fusion[i] = fusion.get(i, 0.0) + poids / (60 + rang)
            if i not in rangs_vectoriels:
                rangs_vectoriels[i] = (rang, float(s))
        for rang, (s, i) in enumerate(lex.scores(mots(requete))):
            fusion[i] = fusion.get(i, 0.0) + poids / (60 + rang)
            if i not in rangs_lexicaux:
                rangs_lexicaux[i] = (rang, float(s))
            if rang >= 60:
                break

    classement = sorted(fusion.items(), key=lambda x: -x[1])
    resultats = []
    for i, note in classement:
        f = fragments[i]
        if source and f.get("source") != source:
            continue
        info = {"rrf": note,
                "vectoriel": rangs_vectoriels.get(i),
                "lexical": rangs_lexicaux.get(i),
                "requetes": len(requetes)}
        resultats.append((info, f))
        if len(resultats) >= k:
            break
    return resultats


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("-k", type=int, default=5)
    p.add_argument("-s", "--source", default=None)
    p.add_argument("-v", "--verbeux", action="store_true")
    p.add_argument("--complet", action="store_true")
    a = p.parse_args()
    for info, f in chercher(a.question, a.k, a.source, a.verbeux):
        texte = f["texte"] if a.complet else f["texte"][:300].replace("\n", " ")
        print("--- %s | %s | %s | partie %s" % (f["source"], f["titre"], f.get("notebook") or "", f.get("partie")))
        if a.verbeux:
            v = info["vectoriel"]
            l = info["lexical"]
            print("    vectoriel : %s | lexical : %s | rrf %.4f"
                  % (("rang %d, cos %.3f" % (v[0], v[1])) if v else "absent",
                     ("rang %d, bm25 %.2f" % (l[0], l[1])) if l else "absent",
                     info["rrf"]))
        print("    %s" % texte)
        print()
