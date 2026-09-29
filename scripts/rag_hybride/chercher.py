# -*- coding: utf-8 -*-
"""Interroge la base vectorielle locale (RAG) — recherche hybride + reranking.

Vectoriel seul : rate les termes rares et le jargon (« lèvres », « connector-11 », « 45 s »).
Lexical seul  : rate les reformulations.
Ici les deux sont combines par fusion de rangs (RRF). Un etage de reranking cross-encoder
(FlashRank, ONNX CPU) est present mais **desactive par defaut** (RAG_RERANK=1 pour l'activer) :
mesure du 29/09/2026, aucun modele FlashRank ne classe mieux le corpus francais que le RRF seul
et le modele multilingue coute 2 a 6 s par requete. Detail chiffre dans chantier_H.log.

Usage :
  python chercher.py "ma question"            # 5 meilleurs fragments (RRF seul par defaut)
  python chercher.py "ma question" -k 8       # 8 fragments
  python chercher.py "ma question" -s skill   # siyuan|skill|script_v4|wordpress
  python chercher.py "ma question" -v         # afficher le detail des rangs (+ score de rerank si actif)
  python chercher.py "ma question" --rerank      # active le reranking cross-encoder (top-20 -> top-5)
  python chercher.py "ma question" --sans-rerank # force le classement RRF seul

Le modele e5 exige le prefixe "query: " cote requete (et "passage: " cote index) :
sans lui, la pertinence s'effondre. C'est fait ici.
"""
import argparse
import hashlib
import io
import json
import math
import os
import re
import sys
import time
import unicodedata

RACINE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(RACINE, "index.faiss")
CHUNKS = os.path.join(RACINE, "chunks.jsonl")
MANIFESTE = os.path.join(RACINE, "manifeste.json")
CACHE_DB = os.path.join(RACINE, "cache.db")
TTL_DEFAUT = 24 * 3600       # 24 heures
TTL_PURGE = 7 * 24 * 3600    # purge au-delà de 7 jours
import sqlite3 as _sq3

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


# --------------------------------------------------------------------------------------
# Reranking cross-encoder (FlashRank / ONNX, CPU) — etage ajoute le 29/09/2026 (chantier H).
# La fusion RRF classe bien mais remonte du bruit : un cross-encoder relit les 20 premiers
# candidats avec la question et renvoie les meilleurs. Reglages par variables d'environnement
# pour pouvoir comparer sans toucher au code : RAG_RERANK_MODELE, RAG_RERANK_CANDIDATS,
# RAG_RERANK_MAX_CAR.
# DESACTIVE PAR DEFAUT : mesure du 29/09 dans chantier_H.log — aucun des modeles FlashRank ne
# classe mieux le corpus francais que le RRF seul (le document de controle passait du rang 1
# au rang 4-5, voire hors du top 5), et le seul modele multilingue coute 2 a 6 s par requete
# sur CPU (budget vise : < 500 ms). Activer avec RAG_RERANK=1.
# Fail-open : si le modele ou onnxruntime manque, on renvoie le classement RRF tel quel —
# une recherche degradee vaut mieux qu'une recherche en erreur.
# --------------------------------------------------------------------------------------
RERANK_MODELE_DEFAUT = "ms-marco-MultiBERT-L-12"    # seul modele multilingue de FlashRank (mesures dans le log)
RERANK_CACHE = os.path.join(RACINE, "models_flashrank")
_rerankers = {}
_rerank_erreurs = {}


def reglages_rerank():
    return {"actif": os.environ.get("RAG_RERANK", "0") != "0",
            "modele": os.environ.get("RAG_RERANK_MODELE", RERANK_MODELE_DEFAUT),
            "candidats": int(os.environ.get("RAG_RERANK_CANDIDATS", "20")),
            "max_car": int(os.environ.get("RAG_RERANK_MAX_CAR", "1200"))}


def charger_reranker(modele):
    """Ranker FlashRank memoise ; None si indisponible (le motif est conserve)."""
    if modele in _rerankers:
        return _rerankers[modele]
    if modele in _rerank_erreurs:
        return None
    try:
        from flashrank import Ranker
        _rerankers[modele] = Ranker(model_name=modele, cache_dir=RERANK_CACHE, max_length=512)
    except Exception as e:
        _rerank_erreurs[modele] = "%s: %s" % (type(e).__name__, e)
        sys.stderr.write("reranking indisponible (repli RRF) : %s\n" % _rerank_erreurs[modele])
        _rerankers[modele] = None
    return _rerankers[modele]


def reranker(question, candidats, reglages):
    """Reclasse [(indice, info, fragment)] par cross-encoder. Renvoie (ordre, scores) ou None."""
    ranker = charger_reranker(reglages["modele"])
    if ranker is None:
        return None
    try:
        from flashrank import RerankRequest
        passages = [{"id": pos, "text": f["texte"][:reglages["max_car"]],
                     "meta": {"source": f["source"], "titre": f["titre"]}}
                    for pos, (_, _, f) in enumerate(candidats)]
        resultat = ranker.rerank(RerankRequest(query=question, passages=passages))
        ordre = [candidats[int(d["id"])] for d in resultat]
        scores = dict((int(d["id"]), float(d["score"])) for d in resultat)
        return ordre, scores
    except Exception as e:
        sys.stderr.write("reranking en echec (repli RRF) : %s: %s\n" % (type(e).__name__, e))
        return None


def chercher(question, k=5, source=None, detail=False):
    reglages = reglages_rerank()
    # --- cache SQLite : même question + même k + même source + même mode de reranking dans le TTL
    h = hashlib.sha256(("%s|%s|%s|%s" % (question, k, source,
                                         ("rerank:" + reglages["modele"]) if reglages["actif"] else "sans-rerank"
                                         )).encode("utf-8")).hexdigest()
    db = None
    try:
        db = _sq3.connect(CACHE_DB, timeout=5)
        # purge des entrées expirées (> 7 jours)
        now = time.time()
        db.execute("DELETE FROM cache WHERE timestamp < ?", (now - TTL_PURGE,))
        # lecture : valide si timestamp + ttl >= now
        row = db.execute("SELECT resultat_json FROM cache WHERE hash=? AND (timestamp + ttl_secondes) >= ?",
                         (h, now)).fetchone()
        if row:
            resultat = json.loads(row[0])
            db.close()
            return resultat
    except Exception:
        pass

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
    # 1) candidats : jusqu'a RERANK_CANDIDATS fragments (au lieu de k) pour laisser le cross-encoder trancher
    candidats = []
    for rang_rrf, (i, note) in enumerate(classement):
        f = fragments[i]
        if source and f.get("source") != source:
            continue
        info = {"rrf": note, "rrf_rang": rang_rrf,
                "vectoriel": rangs_vectoriels.get(i),
                "lexical": rangs_lexicaux.get(i),
                "requetes": len(requetes),
                "rerank": None, "rerank_applique": False, "rerank_modele": None}
        candidats.append((i, info, f))
        if len(candidats) >= (reglages["candidats"] if reglages["actif"] else k):
            break

    # 2) reranking cross-encoder (fail-open : si indisponible, on garde l'ordre RRF)
    if reglages["actif"] and len(candidats) > 1:
        reclassement = reranker(question, candidats, reglages)
        if reclassement is not None:
            ordre, scores = reclassement
            scores_par_i = {}
            for pos, sc in scores.items():
                if 0 <= pos < len(candidats):
                    scores_par_i[candidats[pos][0]] = sc
            candidats = ordre
            for i, info, f in candidats:
                info["rerank"] = scores_par_i.get(i)
                info["rerank_applique"] = True
                info["rerank_modele"] = reglages["modele"]

    resultats = [(info, f) for (i, info, f) in candidats[:k]]

    # écrire dans le cache
    try:
        db.execute("INSERT OR REPLACE INTO cache (hash, question, resultat_json, timestamp, ttl_secondes) "
                   "VALUES (?,?,?,?,?)",
                   (h, question, json.dumps(resultats, ensure_ascii=False), time.time(), TTL_DEFAUT))
        db.commit()
    except Exception:
        pass
    try:
        db.close()
    except Exception:
        pass

    return resultats


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("-k", type=int, default=5)
    p.add_argument("-s", "--source", default=None)
    p.add_argument("-v", "--verbeux", action="store_true")
    p.add_argument("--complet", action="store_true")
    p.add_argument("--rerank", action="store_true",
                   help="active le reranking cross-encoder (FlashRank, top-20 -> top-5)")
    p.add_argument("--sans-rerank", action="store_true",
                   help="force le classement RRF seul (defaut)")
    a = p.parse_args()
    if a.sans_rerank:
        os.environ["RAG_RERANK"] = "0"
    if a.rerank:
        os.environ["RAG_RERANK"] = "1"
    r = reglages_rerank()
    for info, f in chercher(a.question, a.k, a.source, a.verbeux):
        texte = f["texte"] if a.complet else f["texte"][:300].replace("\n", " ")
        print("--- %s | %s | %s | partie %s" % (f["source"], f["titre"], f.get("notebook") or "", f.get("partie")))
        if a.verbeux:
            v = info["vectoriel"]
            l = info["lexical"]
            print("    vectoriel : %s | lexical : %s | rrf %.4f (rang %s)"
                  % (("rang %d, cos %.3f" % (v[0], v[1])) if v else "absent",
                     ("rang %d, bm25 %.2f" % (l[0], l[1])) if l else "absent",
                     info["rrf"], info.get("rrf_rang")))
            if info.get("rerank_applique"):
                print("    rerank    : %.4f  (%s)" % (info["rerank"], info["rerank_modele"]))
            else:
                print("    rerank    : inactif")
        print("    %s" % texte)
        print()
