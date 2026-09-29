# -*- coding: utf-8 -*-
"""Banc de mesure du RAG v2 — latence chaude (chargeurs memoises comme dans serveur_rag.py)
+ classement top-k. Le cache SQLite est purge avant chaque appel (sinon on ne mesure rien).

Usage :
  venv/Scripts/python.exe bench_rag_v2.py <sortie.json>              # rerank actif (modele par env)
  venv/Scripts/python.exe bench_rag_v2.py <sortie.json> --sans-rerank
Env : RAG_RERANK=0|1, RAG_RERANK_MODELE, RAG_RERANK_CANDIDATS
"""
import functools
import io
import json
import os
import sqlite3
import sys
import time

RACINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RACINE)
import chercher  # noqa: E402

QUESTIONS = [
    "Quel modèle d'embedding utilise mon RAG ?",
    "connector-11",
    "ma vidéo est floue après export",
    "comment sauvegarder un site WordPress et le restaurer",
    "pourquoi mon GPU manque de VRAM avec SDXL",
    "combien de fragments dans l'index RAG",
]
K = 5
ATTENDU = "RAG local - resultat Phase 1"   # document de controle (fragments 203-212)


def purger(question):
    try:
        db = sqlite3.connect(chercher.CACHE_DB, timeout=5)
        db.execute("DELETE FROM cache WHERE question=?", (question,))
        db.commit()
        db.close()
    except Exception as e:
        print("purge cache impossible:", e, file=sys.stderr)


def principal():
    sortie = sys.argv[1]
    if "--sans-rerank" in sys.argv:
        os.environ["RAG_RERANK"] = "0"
    reglages = chercher.reglages_rerank()

    # chargeurs memoises : c'est ce que fait serveur_rag.py au demarrage ; sans cela chaque
    # appel recharge le modele e5 (~5,8 s) et noie la mesure du reranking.
    chercher.charger = functools.lru_cache(maxsize=1)(chercher.charger)
    _orig_modele = chercher.charger_modele
    _memo = {}

    def charger_modele_memo(manifeste):
        if "m" not in _memo:                       # manifeste est un dict : on memoise par cle
            _memo["m"] = _orig_modele(manifeste)
        return _memo["m"]

    chercher.charger_modele = charger_modele_memo

    res = {"quand": time.strftime("%Y-%m-%dT%H:%M:%S"), "k": K,
           "rerank_actif": reglages["actif"],
           "rerank_modele": reglages["modele"] if reglages["actif"] else None,
           "rerank_candidats": reglages["candidats"], "questions": []}
    for q in QUESTIONS:
        purger(q)
        t0 = time.perf_counter()
        r = chercher.chercher(q, k=K)
        premier = (time.perf_counter() - t0) * 1000.0
        purger(q)                       # 2e passe : tout est deja charge (ce que voit le serveur)
        t1 = time.perf_counter()
        r = chercher.chercher(q, k=K)
        chaud = (time.perf_counter() - t1) * 1000.0
        top = [{"rang": i + 1, "source": f["source"], "titre": f["titre"], "notebook": f.get("notebook"),
                "partie": f.get("partie"), "extrait": f["texte"][:150].replace("\n", " "),
                "rrf": info.get("rrf"), "rrf_rang": info.get("rrf_rang"), "rerank": info.get("rerank"),
                "rerank_applique": info.get("rerank_applique")}
               for i, (info, f) in enumerate(r)]
        rang_attendu = next((t["rang"] for t in top if t["titre"] == ATTENDU), None)
        res["questions"].append({"question": q, "latence_ms_premier": round(premier, 1),
                                 "latence_ms_chaud": round(chaud, 1),
                                 "rang_document_attendu": rang_attendu, "top": top})
        print("%-52s premier %8.1f ms | chaud %7.1f ms | attendu rang %s"
              % (q[:50], premier, chaud, rang_attendu))
    io.open(sortie, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    print("->", sortie)


if __name__ == "__main__":
    principal()
