#!/usr/bin/env python
"""Routeur de complexite (chantier H, phase B). Stdlib uniquement, aucune dependance.

Classe la question AVANT la recherche RAG, pour ne pas payer une recherche (ni injecter
de contexte) quand elle n'apporte rien :

  simple   -> aucune recherche RAG : reponse directe par le LLM
  moderee  -> RAG top-5
  complexe -> RAG top-20 puis selection locale de 5 fragments

Le reranker FlashRank est abandonne (modeles anglais, test d'acceptation en echec) : le
chemin « complexe » n'appelle donc AUCUN modele de reranking. La selection des 5 fragments
parmi les 20 est faite par `selectionner()` : score RRF + couverture des mots de la question
(deterministe, hors ligne) + plafond de 2 fragments par document pour diversifier les sources.

Regles, dans cet ordre (la premiere qui matche gagne) : complexe, puis simple, puis moderee.
Elles sont volontairement explicites : elles doivent etre lisibles et mesurables. Si la
mesure montre qu'elles sont insuffisantes, la migration vers une classification LLM
(qwen2.5:7b) est prevue, mais elle n'est pas faite ici.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata

# ---------------------------------------------------------------- mots outils

MOTS_VIDES = {
    "alors", "apres", "aussi", "autre", "avec", "avoir", "beaucoup", "bien", "cela", "cent",
    "ces", "cette", "chaque", "chez", "comme", "comment", "dans", "des", "donc", "dont", "elle",
    "encore", "entre", "etaient", "etait", "etant", "etre", "faire", "fait", "faut", "grace",
    "leur", "leurs", "mais", "meme", "mes", "moins", "mon", "nous", "par", "parce", "pas", "peu",
    "plus", "pour", "pourquoi", "quand", "que", "quel", "quelle", "quelles", "quels", "qui",
    "sans", "selon", "ses", "son", "sont", "sous", "sur", "tous", "tout", "toute", "toutes",
    "tres", "une", "vers", "voici", "voila", "vous", "votre", "vos", "avec", "est", "les", "aux",
    "dit", "elle", "ils", "elles", "nous", "vous", "ont", "etait", "etre", "avoir", "faut",
}
# Mots qui signalent une question portant sur la memoire documentaire locale.
MOTS_TECHNIQUES = {
    "port", "ports", "version", "modele", "chemin", "commande", "commandes", "seuil", "seuils",
    "script", "fichier", "fichiers", "config", "configuration", "index", "indexation", "rag",
    "skill", "plugin", "hook", "cron", "tache", "taches", "log", "logs", "venv", "gpu", "vram",
    "latence", "bench", "mesure", "controle", "verdict", "algorithme", "pipeline", "embedding",
    "store", "faiss", "bm25", "rrf", "siyuan", "wordpress", "wazuh", "ollama", "comfyui",
    "latentsync", "liveportrait", "ltx", "sdxl", "lora", "whisper", "telegram", "omniroute",
}
# Marqueurs de synthese / transversalite : la reponse est forcement dans plusieurs documents.
MARQUEURS_COMPLEXES = (
    "difference entre", "differences entre", "compare", "comparer", "comparaison",
    "point commun", "points communs", "synthese", "synthetise", "recoupe", "recouper",
    "a la fois", "les deux", "d'un cote", "de l'autre", "ainsi que", "en plus de",
    "quel lien", "quels liens", "impact de", "consequence de", "consequences de",
    "chaine complete", "bout en bout", "de a a z", "plan complet", "liste tous", "liste toutes",
    "quelles sont les etapes", "etapes necessaires",
)
# Marqueurs de questions simples : calcul, traduction, redaction, conversation.
MARQUEURS_SIMPLES = (
    "traduis", "traduire", "corrige", "reformule", "reescris", "resume en une phrase",
    "ecris", "ecrit", "redige", "genere", "donne moi un exemple", "donne un exemple",
    "salut", "bonjour", "bonsoir", "coucou", "hello", "merci", "cava", "ca va", "au revoir",
    "quelle heure", "quel jour", "tu es qui", "qui es tu", "raconte moi une blague",
    "calcule", "combien font", "additionne", "convertis", "explique moi la difference entre a et b",
)
RE_CALCUL = re.compile(r"^\s*\d+\s*[-+*/x]\s*\d+\s*=?\s*\??\s*$")


def _sans_accent(texte: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texte or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _mots(texte: str) -> list[str]:
    return [m for m in re.findall(r"[a-z0-9_./+-]{3,}", _sans_accent(texte)) if m not in MOTS_VIDES]


def classer(question: str) -> dict:
    """Retourne {classe, raisons, signaux}. Ordre : complexe, puis simple, puis moderee."""
    q = _sans_accent(question).strip()
    mots = _mots(question)
    raisons: list[str] = []
    if not q:
        return {"classe": "simple", "raisons": ["question vide"], "signaux": {}}

    n_points_interrogation = question.count("?")
    n_mots_techniques = len({m for m in mots if m in MOTS_TECHNIQUES})
    marqueurs_complexes = [m for m in MARQUEURS_COMPLEXES if m in q]
    marqueurs_simples = [m for m in MARQUEURS_SIMPLES if m in q]

    # --- complexe : question multiple, ou transversale, ou tres longue, ou multi-entites
    if n_points_interrogation >= 2:
        raisons.append(f"{n_points_interrogation} questions dans le meme message")
    if marqueurs_complexes:
        raisons.append("marqueur de synthese/comparaison : " + ", ".join(marqueurs_complexes[:3]))
    if len(question) > 240:
        raisons.append(f"message long ({len(question)} caracteres)")
    if n_mots_techniques >= 3:
        raisons.append(f"{n_mots_techniques} termes techniques distincts")
    if " et " in q and n_mots_techniques >= 2 and n_points_interrogation >= 1:
        raisons.append("question double (et + deux domaines techniques)")
    if raisons:
        return {"classe": "complexe", "raisons": raisons,
                "signaux": {"n_mots_techniques": n_mots_techniques, "n_questions": n_points_interrogation}}

    # --- simple : aucune recherche documentaire necessaire
    if RE_CALCUL.match(q):
        raisons.append("calcul arithmetique nu")
    if marqueurs_simples:
        raisons.append("marqueur de tache simple : " + ", ".join(marqueurs_simples[:2]))
    if len(mots) <= 3 and "?" not in question:
        raisons.append(f"message tres court sans question ({len(mots)} mots utiles)")
    if not mots:
        raisons.append("aucun mot utile")
    if n_mots_techniques == 0 and marqueurs_simples:
        raisons.append("aucun terme technique")
    if raisons:
        return {"classe": "simple", "raisons": raisons,
                "signaux": {"n_mots_techniques": n_mots_techniques, "n_questions": n_points_interrogation}}

    # --- moderee : par defaut, question factuelle mono-document
    raisons.append("question factuelle mono-document (aucun marqueur de synthese)")
    if n_mots_techniques:
        raisons.append(f"{n_mots_techniques} terme(s) technique(s)")
    return {"classe": "moderee", "raisons": raisons,
            "signaux": {"n_mots_techniques": n_mots_techniques, "n_questions": n_points_interrogation}}


K_RECHERCHE = {"simple": 0, "moderee": 5, "complexe": 20}
K_INJECTE = {"simple": 0, "moderee": 5, "complexe": 5}


def decider(question: str, k_complexe: int | None = None, k_moderee: int | None = None) -> dict:
    """Classe la question et donne les parametres de recherche a appliquer."""
    c = classer(question)
    classe = c["classe"]
    k_recherche = dict(K_RECHERCHE)
    if k_complexe:
        k_recherche["complexe"] = int(k_complexe)
    if k_moderee:
        k_recherche["moderee"] = int(k_moderee)
    return {
        "classe": classe,
        "raisons": c["raisons"],
        "signaux": c["signaux"],
        "k_recherche": k_recherche[classe],
        "k_injecte": K_INJECTE[classe],
        "routage": ("aucune recherche RAG" if classe == "simple"
                    else f"RAG top-{k_recherche[classe]} puis {K_INJECTE[classe]} fragment(s) injecte(s)"),
    }


# ---------------------------------------------------------------- selection locale

def _score_couverture(question_mots: set[str], fragment: dict) -> float:
    texte = _sans_accent(f"{fragment.get('titre','')} {fragment.get('extrait','')}")
    if not question_mots:
        return 0.0
    presents = sum(1 for m in question_mots if m in texte)
    return presents / len(question_mots)


def selectionner(candidats: list[dict], question: str, k: int = 5, max_par_doc: int = 2) -> list[dict]:
    """Choisit k fragments parmi les candidats (chemins « complexe » uniquement).

    Critere : score RRF du RAG + 0.30 x couverture des mots de la question (texte et titre),
    puis plafond de `max_par_doc` fragments par document pour ne pas injecter 5 extraits du
    meme page. Aucun modele, aucun reseau : deterministe et reproductible.
    """
    mots = set(_mots(question))
    enrichis = []
    for i, f in enumerate(candidats):
        couv = _score_couverture(mots, f)
        try:
            rrf = float(f.get("score") or 0.0)
        except (TypeError, ValueError):
            rrf = 0.0
        enrichis.append({"f": f, "i": i, "couv": couv, "score": rrf + 0.30 * couv})
    enrichis.sort(key=lambda e: (-e["score"], e["i"]))

    choisis, par_doc = [], {}
    for e in enrichis:
        doc = (e["f"].get("source"), e["f"].get("titre"))
        if par_doc.get(doc, 0) >= max_par_doc:
            continue
        choisis.append(e["f"])
        par_doc[doc] = par_doc.get(doc, 0) + 1
        if len(choisis) >= k:
            return choisis
    # pas assez de diversite : on complete par les meilleurs restants
    for e in enrichis:
        if e["f"] not in choisis:
            choisis.append(e["f"])
            if len(choisis) >= k:
                break
    return choisis[:k]


def main() -> int:
    p = argparse.ArgumentParser(description="Routeur de complexite du RAG (phase B)")
    p.add_argument("question", nargs="*", help="question a classer")
    p.add_argument("--fichier", help="fichier JSON de questions ({'questions':[{question|id}]})")
    p.add_argument("--json", action="store_true", dest="en_json")
    a = p.parse_args()

    if a.fichier:
        donnees = json.load(open(a.fichier, encoding="utf-8"))
        questions = [q.get("question") for q in donnees.get("questions", donnees if isinstance(donnees, list) else [])]
        if a.en_json:
            print(json.dumps([{"question": q, **decider(q)} for q in questions], ensure_ascii=False, indent=1))
            return 0
        for q in questions:
            d = decider(q)
            print(f"  {d['classe']:9s} k={d['k_recherche']:2d} | {q[:70]}")
        return 0

    question = " ".join(a.question)
    if not question:
        p.print_help()
        return 2
    print(json.dumps(decider(question), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
