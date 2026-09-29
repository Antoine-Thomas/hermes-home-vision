#!/usr/bin/env python
"""Phase A (chantier H) - mesure RAGAS d'un RAG local. LECTURE SEULE cote RAG.

Pipeline mesure : POST /search (127.0.0.1:8200, top-k) -> fragments -> reponse du LLM local
(Ollama) -> quatre metriques RAGAS (faithfulness, answer_relevancy, context_precision,
context_recall) jugees par le meme LLM local.

Deux etapes independantes, pour ne pas payer le juge LLM avant d'avoir verifie la collecte :
  --etape collecte : interroge le RAG et genere les reponses, ecrit le JSON intermediaire
  --etape ragas    : relit le JSON intermediaire et calcule les quatre metriques
  --etape tout     : les deux

Aucune ecriture dans le RAG : ni index, ni venv, ni code. Le script tourne dans ragas_env.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime

SYSTEME = (
    "Tu es un assistant documentaire. Reponds en francais, uniquement a partir du CONTEXTE fourni. "
    "Si le contexte ne contient pas l'information, ecris exactement : « information absente du contexte ». "
    "N'ajoute aucune connaissance personnelle. Sois precis (chiffres, seuils, noms de fichiers)."
)
GABARIT = """CONTEXTE :
{contexte}

QUESTION : {question}

REPONSE :"""


def post(url: str, charge: dict, timeout: int = 600) -> dict:
    requete = urllib.request.Request(
        url, data=json.dumps(charge).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    return json.loads(urllib.request.urlopen(requete, timeout=timeout).read().decode("utf-8"))


def cherche(rag: str, question: str, k: int, source: str | None = None, timeout: int = 120) -> dict:
    charge = {"question": question, "k": k}
    if source:
        charge["source"] = source
    return post(f"{rag}/search", charge, timeout=timeout)


def genere(ollama: str, modele: str, question: str, fragments: list[dict], num_ctx: int = 4096) -> tuple[str, float]:
    contexte = "\n\n".join(
        f"[{i}] {f.get('source')} | {f.get('titre')} | partie {f.get('partie')}\n{f.get('extrait','')}"
        for i, f in enumerate(fragments, 1)
    )
    t0 = time.time()
    rep = post(
        f"{ollama}/api/generate",
        {
            "model": modele,
            "prompt": GABARIT.format(contexte=contexte, question=question),
            "system": SYSTEME,
            "stream": False,
            "options": {"temperature": 0.0, "num_ctx": num_ctx, "seed": 42},
        },
        timeout=900,
    )
    return (rep.get("response", "") or "").strip(), time.time() - t0


def etape_collecte(a) -> dict:
    jeu = json.load(open(a.questions, encoding="utf-8"))
    rc = None
    if a.routeur:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import routeur_complexite as rc  # noqa: E402
    resultats = []
    for q in jeu["questions"]:
        classe, k_recherche, k_injecte, raisons = None, a.k, None, None
        t0 = time.time()
        if a.routeur:
            dec = rc.decider(q["question"])
            classe = dec["classe"]
            k_recherche = dec["k_recherche"]
            k_injecte = dec["k_injecte"]
            raisons = dec["raisons"]
            if classe == "simple":  # aucune recherche RAG (chemin phase B)
                rep = {"resultats": []}
            else:
                rep = cherche(a.rag, q["question"], k_recherche)
        else:
            rep = cherche(a.rag, q["question"], a.k)
        fragments = rep.get("resultats", []) or []
        latence_rag = time.time() - t0
        if a.routeur and classe == "complexe" and fragments:
            fragments = rc.selectionner(fragments, q["question"], k_injecte)
        reponse, latence_llm = genere(a.ollama, a.modele, q["question"], fragments)
        rang = None
        for i, f in enumerate(fragments, 1):
            for s in q.get("sources", []):
                if f.get("titre") == s["titre"] and str(f.get("partie")) == str(s["partie"]):
                    rang = i
                    break
            if rang:
                break
        resultats.append(
            {
                "id": q.get("id"),
                "type": q.get("type"),
                "question": q["question"],
                "reponse_attendue": q.get("reponse_attendue"),
                "sources_attendues": q.get("sources", []),
                "reponse_generee": reponse,
                "contextes": [f.get("extrait", "") for f in fragments],
                "fragments": [
                    {k: f.get(k) for k in ("source", "titre", "partie", "score", "cos", "rang_vectoriel", "rang_lexical")}
                    for f in fragments
                ],
                "rang_premier_document_attendu": rang,
                "classe_routeur": classe,
                "k_recherche": k_recherche,
                "k_injecte": k_injecte,
                "raisons_routeur": raisons,
                "latence_rag_s": round(latence_rag, 3),
                "latence_llm_s": round(latence_llm, 2),
            }
        )
        print(f"  {q.get('id')} | RAG {latence_rag:.2f}s | LLM {latence_llm:.1f}s | rang doc attendu : {rang}", flush=True)
    return {
        "horodatage": datetime.now().isoformat(timespec="seconds"),
        "etape": "collecte",
        "rag": a.rag,
        "ollama": a.ollama,
        "modele_juge_et_reponse": a.modele,
        "k": a.k,
        "jeu": jeu.get("jeu"),
        "resultats": resultats,
    }


def etape_ragas(a, donnees: dict) -> dict:
    """Calcule les quatre metriques RAGAS. Juge = LLM local, embeddings = API du RAG (768 d)."""
    import ragas
    from ragas import EvaluationDataset, SingleTurnSample, evaluate

    try:  # ragas >= 0.3 : classes, wrappers langchain
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
    except Exception:  # pragma: no cover
        LangchainLLMWrapper = LangchainEmbeddingsWrapper = None

    from langchain_core.embeddings import Embeddings as BaseEmbeddings

    class EmbeddingsRAG(BaseEmbeddings):
        """Embeddings = endpoint /v1/embeddings du RAG local (e5-base, 768). Aucun modele local."""

        def __init__(self, url: str, taille_lot: int = 16):
            self.url = url.rstrip("/")
            self.taille_lot = taille_lot

        def _appel(self, textes: list[str]) -> list[list[float]]:
            tout = []
            for i in range(0, len(textes), self.taille_lot):
                lot = textes[i : i + self.taille_lot]
                d = post(f"{self.url}/v1/embeddings", {"input": lot}, timeout=300)
                tout.extend(x["embedding"] for x in d["data"])
            return tout

        def embed_documents(self, textes):  # noqa: D102
            return self._appel(list(textes))

        def embed_query(self, texte):  # noqa: D102
            return self._appel([texte])[0]

    from langchain_ollama import ChatOllama

    # Juge local : un seul modele Ollama, requetes serialisees (un GPU), JSON force
    # (les prompts RAGAS attendent du JSON ; format='json' evite les OutputParserException).
    llm = LangchainLLMWrapper(
        ChatOllama(
            model=a.modele,
            base_url=a.ollama,
            temperature=0.0,
            num_ctx=a.num_ctx,
            format="json" if a.json_force else None,
            client_kwargs={"timeout": a.timeout},
        )
    )
    emb = LangchainEmbeddingsWrapper(EmbeddingsRAG(a.rag))

    try:
        from ragas import RunConfig
    except ImportError:  # pragma: no cover
        from ragas.run_config import RunConfig

    try:
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

        metriques = [faithfulness, answer_relevancy, context_precision, context_recall]
    except ImportError:  # pragma: no cover
        from ragas.metrics import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness

        metriques = [Faithfulness(), AnswerRelevancy(), ContextPrecision(), ContextRecall()]

    echantillons = [
        SingleTurnSample(
            user_input=r["question"],
            response=r["reponse_generee"],
            retrieved_contexts=r["contextes"] or [""],
            reference=r["reponse_attendue"],
        )
        for r in donnees["resultats"]
    ]
    jeu = EvaluationDataset(samples=echantillons)
    config = RunConfig(max_workers=a.workers, timeout=a.timeout, max_retries=a.retries)
    print(f"   RunConfig max_workers={a.workers} timeout={a.timeout}s retries={a.retries} json={a.json_force}", flush=True)
    res = evaluate(
        dataset=jeu,
        metrics=metriques,
        llm=llm,
        embeddings=emb,
        run_config=config,
        raise_exceptions=False,
        show_progress=a.progress,
    )
    tableau = res.to_pandas()
    par_question = []
    for i, r in enumerate(donnees["resultats"]):
        ligne = tableau.iloc[i].to_dict()
        par_question.append(
            {
                "id": r["id"],
                "type": r["type"],
                "question": r["question"],
                "scores": {k: (None if ligne.get(k) is None or str(ligne.get(k)) == "nan" else round(float(ligne[k]), 4))
                           for k in ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
                           if k in ligne},
                "rang_premier_document_attendu": r["rang_premier_document_attendu"],
                "reponse_generee": r["reponse_generee"],
                "reponse_attendue": r["reponse_attendue"],
            }
        )

    def moyenne(cle):
        vals = [q["scores"].get(cle) for q in par_question if q["scores"].get(cle) is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    donnees["etape"] = "ragas"
    donnees["version_ragas"] = getattr(ragas, "__version__", "?")
    donnees["par_question"] = par_question
    donnees["moyennes"] = {c: moyenne(c) for c in ("faithfulness", "answer_relevancy", "context_precision", "context_recall")}
    return donnees


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--questions", required=True)
    p.add_argument("--sortie", required=True)
    p.add_argument("--etape", choices=["collecte", "ragas", "tout"], default="tout")
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--rag", default="http://127.0.0.1:8200")
    p.add_argument("--ollama", default="http://127.0.0.1:11434")
    p.add_argument("--modele", default="llama3.2:3b")
    p.add_argument("--workers", type=int, default=2, help="appels LLM concurrents (un seul GPU Ollama)")
    p.add_argument("--timeout", type=int, default=600, help="timeout d'un appel au juge, en secondes")
    p.add_argument("--retries", type=int, default=2)
    p.add_argument("--num-ctx", type=int, default=8192, dest="num_ctx")
    p.add_argument("--json-force", action="store_true", default=True, dest="json_force")
    p.add_argument("--sans-json-force", action="store_false", dest="json_force")
    p.add_argument("--progress", action="store_true", default=False)
    p.add_argument("--routeur", action="store_true", default=False,
                   help="applique le routeur de complexite (phase B) : simple | moderee top-5 | complexe top-20 -> 5")
    a = p.parse_args()

    if a.etape in ("collecte", "tout"):
        print(f"== collecte ({a.questions}) ==", flush=True)
        donnees = etape_collecte(a)
        json.dump(donnees, open(a.sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"   -> {a.sortie} (collecte)", flush=True)
    if a.etape in ("ragas", "tout"):
        if a.etape == "ragas":
            donnees = json.load(open(a.sortie, encoding="utf-8"))
        print("== metriques RAGAS (juge = LLM local) ==", flush=True)
        t0 = time.time()
        donnees = etape_ragas(a, donnees)
        donnees["duree_ragas_s"] = round(time.time() - t0, 1)
        json.dump(donnees, open(a.sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("   moyennes :", json.dumps(donnees["moyennes"], ensure_ascii=False), flush=True)
        print(f"   -> {a.sortie} (ragas, {donnees['duree_ragas_s']}s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
