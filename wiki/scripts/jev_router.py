"""Routeur Jev : décide pour chaque question si L1 (wiki) ou L2 (RAG).

L1 = wiki compilé (motif Karpathy, skill `llm-wiki`) : connaissances synthétisées,
     cross-référencées, déjà arbitrées. Chemin lu : `$WIKI_PATH`.
L2 = RAG sur `data/` : recherche brute dans les documents indexés.
Le routeur ne répond PAS à la question : il choisit le niveau à interroger.

Jev = TypeSafe System One, primitive `choice` (~0,4 s, ~1,3e-5 $/requête).
Ce module ne fait AUCUN appel LLM de génération : c'est une primitive de décision.

Usage :
    python jev_router.py "Qu'est-ce que le LLM Wiki ?"
    python jev_router.py --json "Quel est le PID du proxy NIM ?"

Codes de sortie :
    0 = OK
    2 = Jev injoignable ou en erreur — l'erreur brute est affichée et AUCUNE
        route n'est inventée (voir contrainte : ne jamais simuler une décision).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Chemin du wiki : WIKI_PATH (.env) d'abord, sinon %LOCALAPPDATA%\hermes\wiki.
WIKI = Path(
    os.environ.get("WIKI_PATH")
    or (Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "wiki")
)

# Helper Jev du skill typesafe-ai (une seule source de vérité pour l'API Jev).
SKILL_SCRIPTS = (
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "hermes"
    / "skills"
    / "typesafe-ai"
    / "scripts"
)
sys.path.insert(0, str(SKILL_SCRIPTS))
from jev_helper import jev  # noqa: E402

# Dossiers de pages compilées (canonique du skill + extension `syntheses/`).
PAGE_DIRS = ("concepts", "entities", "comparisons", "queries", "syntheses")

ROUTE_OPTIONS = {
    "wiki": (
        "Connaissance déjà compilée : définition, synthèse, comparaison, état "
        "d'une décision ou d'une architecture. Répondable en lisant les pages "
        "du wiki, sans rouvrir les sources brutes."
    ),
    "rag": (
        "Besoin des sources brutes : fait précis, valeur exacte, date, PID, "
        "chemin de fichier, extrait de document, sujet jamais compilé."
    ),
    "both": (
        "Question complexe : une synthèse existe mais doit être confrontée aux "
        "sources brutes (vérification d'un chiffre, contradiction à trancher, "
        "articulation de plusieurs briques)."
    ),
}


def wiki_state() -> dict:
    """État du L1, mesuré sur le disque (jamais supposé)."""
    pages = [p for d in PAGE_DIRS for p in (WIKI / d).rglob("*.md")]
    raw = list((WIKI / "raw").rglob("*.md")) if (WIKI / "raw").is_dir() else []
    return {
        "wiki_path": str(WIKI),
        "wiki_page_count": len(pages),
        "wiki_pages": sorted(p.relative_to(WIKI).as_posix() for p in pages)[:40],
        "wiki_index_exists": (WIKI / "index.md").is_file(),
        "raw_source_count": len(raw),
        "rag_available": True,
    }


def route(question: str) -> dict:
    """Renvoie {"route": "wiki"|"rag"|"both", ...} pour `question`.

    Règle en code (Jev n'est pas appelé pour rien) : wiki vide ⇒ `rag`.
    Décider `wiki` sans page compilée serait une réponse creuse garantie.
    """
    st = wiki_state()

    if st["wiki_page_count"] == 0:
        return {
            "question": question,
            "route": "rag",
            "forced": True,
            "forced_reason": "wiki vide (0 page compilée) : L1 ne peut rien servir",
            "route_confidence": None,
            "route_probabilities": None,
            "wiki_coverage": None,
            "model": None,
            "usage": {"cost": 0},
            "elapsed_s": 0.0,
            "wiki_state": st,
        }

    r = jev(
        state={"question": question, **st},
        questions={
            "route": {
                "type": "choice",
                "instructions": (
                    "Cette question doit-elle être servie par le Wiki (L1 : "
                    "connaissances déjà compilées, concepts, entités, synthèses) "
                    "ou par le RAG (L2 : recherche brute dans les documents) ? "
                    "Choisir 'wiki' si les pages compilées suffisent pour "
                    "répondre, 'rag' s'il faut fouiller les sources brutes, "
                    "'both' si une synthèse doit être confrontée aux sources."
                ),
                "criteria": ROUTE_OPTIONS,
            },
            "wiki_coverage": {
                "type": "noul",
                "instructions": (
                    "Les pages déjà compilées du wiki couvrent-elles le sujet de "
                    "la question ? Probabilité de oui. Proche de 0,5 = indécision, "
                    "pas une intensité moyenne."
                ),
            },
        },
    )

    a = r.get("answers", {})
    ch = a.get("route", {}) or {}
    cov = a.get("wiki_coverage", {}) or {}
    return {
        "question": question,
        "route": ch.get("choice"),
        "forced": False,
        "forced_reason": None,
        "route_confidence": ch.get("confidence"),
        "route_probabilities": ch.get("probabilities"),
        "wiki_coverage": cov.get("noul"),
        "model": r.get("model"),
        "usage": r.get("usage", {}),
        "elapsed_s": r.get("_elapsed_s"),
        "wiki_state": st,
    }


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--json"]
    as_json = "--json" in argv
    question = " ".join(args) or "Qu'est-ce que le LLM Wiki ?"

    try:
        res = route(question)
    except Exception as exc:  # erreur brute, jamais paraphrasée
        print("ERREUR Jev : %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2

    if as_json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    st = res["wiki_state"]
    print("Question    : %s" % res["question"])
    print("Route       : %s%s" % (res["route"],
                                  "  (forcé en code)" if res["forced"] else ""))
    if res["forced"]:
        print("Raison      : %s" % res["forced_reason"])
    if res["route_confidence"] is not None:
        print("Confiance   : %.2f" % res["route_confidence"])
    if res["wiki_coverage"] is not None:
        print("Couv. wiki  : %.2f" % res["wiki_coverage"])
    print("Pages wiki  : %d (index: %s, sources brutes: %d)"
          % (st["wiki_page_count"], "oui" if st["wiki_index_exists"] else "non",
             st["raw_source_count"]))
    print("Modèle      : %s" % (res["model"] or "-"))
    print("Latence     : %s s" % res["elapsed_s"])
    print("Coût        : %s $" % res["usage"].get("cost", 0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
