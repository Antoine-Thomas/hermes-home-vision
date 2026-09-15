# -*- coding: utf-8 -*-
"""API HTTP locale du RAG (second cerveau de Hermes).

    venv\\Scripts\\python.exe serveur_rag.py            (port 8200)
    venv\\Scripts\\python.exe serveur_rag.py --port 8201

Endpoints :
  GET  /sante            etat du service : fragments, modele, taille de l'index
  POST /search           {"question": "...", "k": 5, "source": "siyuan"}
  POST /v1/embeddings    format OpenAI standard (compatibilite clients existants)
  POST /recharger        relit l'index sur disque (apres une reindexation)

Lancement manuel uniquement : aucune tache planifiee ne demarre ce serveur.

Ce fichier n'appelle que `chercher.py` (aucune logique de recherche n'est reecrite). Ses deux
chargeurs sont memoises au demarrage : sans cela, chaque requete rechargerait le modele
d'embedding et reconstruirait l'index lexical (plusieurs secondes par appel).
"""
import argparse
import functools
import io
import json
import os
import sys
import time

RACINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RACINE)

import chercher as moteur  # noqa: E402

from fastapi import FastAPI, HTTPException  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

MANIFESTE = os.path.join(RACINE, "manifeste.json")
INDEX = os.path.join(RACINE, "index.faiss")

# --- memoisation des chargeurs de chercher.py (le fichier lui-meme n'est pas modifie) --------
moteur.charger = functools.lru_cache(maxsize=1)(moteur.charger)
_cache_modele = {}
_charger_modele_origine = moteur.charger_modele


def _charger_modele(manifeste):
    nom = manifeste.get("modele")
    if nom not in _cache_modele:
        _cache_modele[nom] = _charger_modele_origine(manifeste)
    return _cache_modele[nom]


moteur.charger_modele = _charger_modele


def vider_cache():
    moteur.charger.cache_clear()
    _cache_modele.clear()


# --- modeles de requete / reponse -----------------------------------------------------------
class RequeteRecherche(BaseModel):
    question: str = Field(..., description="question en langage naturel")
    k: int = Field(5, ge=1, le=50)
    source: str = Field(None, description="filtre : siyuan, skill, script_v4, wordpress")
    complet: bool = Field(False, description="renvoyer le fragment entier au lieu d'un extrait")


class RequeteEmbeddings(BaseModel):
    input: object = Field(..., description="texte ou liste de textes")
    model: str = Field(None, description="ignore, present pour la compatibilite OpenAI")
    prefix: str = Field("query: ", description="prefixe e5 : « query: » (question) ou « passage: » (document)")


app = FastAPI(title="RAG local Hermes", version="1.0",
              description="Second cerveau interrogeable : SiYuan, skills, scripts v4, WordPress.")


def manifeste():
    try:
        return json.load(io.open(MANIFESTE, encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=503, detail="manifeste illisible : %s" % e)


@app.get("/sante")
def sante():
    m = manifeste()
    return {"status": "ok",
            "fragments": m.get("fragments"),
            "modele": m.get("modele"),
            "par_source": m.get("par_source"),
            "index_mo": round(os.path.getsize(INDEX) / 1e6, 1) if os.path.exists(INDEX) else None,
            "mis_a_jour": time.strftime("%d/%m/%Y %H:%M", time.localtime(os.path.getmtime(INDEX)))
            if os.path.exists(INDEX) else None}


@app.post("/search")
def search(r: RequeteRecherche):
    if not r.question.strip():
        raise HTTPException(status_code=400, detail="question vide")
    if r.source and r.source not in ("siyuan", "skill", "script_v4", "wordpress"):
        raise HTTPException(status_code=400,
                            detail="source inconnue : siyuan, skill, script_v4, wordpress")
    t0 = time.time()
    brut = moteur.chercher(r.question, k=r.k, source=r.source)
    resultats = []
    for info, f in brut:
        vec = info.get("vectoriel")
        lex = info.get("lexical")
        extrait = f["texte"] if r.complet else f["texte"][:700].strip()
        resultats.append({
            "score": round(info["rrf"], 4),
            "cos": round(vec[1], 3) if vec else None,
            "rang_vectoriel": vec[0] if vec else None,
            "rang_lexical": lex[0] if lex else None,
            "source": f.get("source"),
            "notebook": f.get("notebook"),
            "titre": f.get("titre"),
            "partie": f.get("partie"),
            "chemin": f.get("chemin"),
            "extrait": extrait})
    return {"question": r.question, "k": r.k, "source": r.source,
            "resultats": resultats, "duree_s": round(time.time() - t0, 2)}


@app.post("/v1/embeddings")
def embeddings(r: RequeteEmbeddings):
    textes = r.input if isinstance(r.input, list) else [r.input]
    if not textes or not all(isinstance(t, str) for t in textes):
        raise HTTPException(status_code=400, detail="input doit etre un texte ou une liste de textes")
    m = manifeste()
    modele = _charger_modele(m)
    prefixes = "" if r.prefix is None else r.prefix
    vecteurs = modele.encode([prefixes + t for t in textes],
                             normalize_embeddings=True, convert_to_numpy=True)
    return {"object": "list",
            "data": [{"object": "embedding", "index": i, "embedding": [float(x) for x in v]}
                     for i, v in enumerate(vecteurs)],
            "model": m.get("modele"),
            "usage": {"prompt_tokens": sum(len(t.split()) for t in textes),
                      "total_tokens": sum(len(t.split()) for t in textes)}}


@app.post("/recharger")
def recharger():
    vider_cache()
    m = manifeste()
    return {"status": "ok", "recharge": True, "fragments": m.get("fragments")}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8200)
    p.add_argument("--hote", default="127.0.0.1")
    a = p.parse_args()
    import uvicorn
    m = manifeste()
    print("RAG local sur http://%s:%d — %s fragments, modele %s"
          % (a.hote, a.port, m.get("fragments"), m.get("modele")), flush=True)
    uvicorn.run(app, host=a.hote, port=a.port, log_level="info")
