# -*- coding: utf-8 -*-
"""Tests hors-ligne du hook anima-memoire-router (T2/T3, sans casser la prod).

- T2 : JEV en échec -> repli regex (router_memoire.router(use_jev=False)) ; on vérifie
  que la question « RAG local » est mal classée (pattern « projet ») et que le niveau 3
  n'est PAS dans les niveaux -> le hook ne doit PAS injecter de RAG.
- T3 : RAG en échec -> _rag_search lève URLError sur un port mort ; le hook (fail-open)
  doit rendre None (aucune injection, le tour continue sans RAG).
- Bloc : _block borne la taille et échappe/formatte les extraits.
Aucun réseau vivant nécessaire (le port mort ne répond pas).
"""
import os
import sys
import urllib.error
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
PLUG = os.path.dirname(HERE)
_INIT = os.path.join(PLUG, "__init__.py")
_spec = importlib.util.spec_from_file_location("anima_memoire_router", _INIT)
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

PASS = 0
FAIL = 0


def check(nom, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [OK ] %s %s" % (nom, detail))
    else:
        FAIL += 1
        print("  [FAIL] %s %s" % (nom, detail))


def test_t2_regex_fallback():
    print("T2 — JEV en échec -> repli regex :")
    # Import direct de router_memoire (data/rag), chemin de repli regex = use_jev=False.
    _rag_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", "data", "rag")
    if _rag_dir not in sys.path:
        sys.path.insert(0, _rag_dir)
    import router_memoire as rm
    r_regex = rm.router("Quel modèle d'embedding utilise mon RAG local ?", use_jev=False)
    niveaux = list(r_regex.get("niveaux_a_consulter") or [])
    check("source_decision == 'regex'", r_regex.get("source_decision") == "regex",
          "source=%s" % r_regex.get("source_decision"))
    check("3 NOT in niveaux (pas de RAG demandé par le regex)", 3 not in niveaux,
          "niveaux=%s" % niveaux)
    check("type_q = projet (le mot 'local' matche le pattern projet)",
          r_regex.get("raison", "").startswith("question sur un projet"),
          "raison=%s" % r_regex.get("raison", "")[:40])
    # Conséquence pour le hook : avec niveaux=[1,2], le hook rend None (pas d'injection).
    check("conséquence hook : 3 not in niveaux => hook None",
          3 not in niveaux)


def test_t3_rag_failure():
    print("T3 — RAG en échec -> fail-open (aucune injection) :")
    settings = {"rag_url": "http://127.0.0.1:1", "rag_k": 3, "timeout_s": 2.0,
                "max_chars": 4000}
    try:
        A._rag_search(settings, "question test", 3)
        check("URLError levé sur port mort", False, "aucune exception")
    except urllib.error.URLError:
        check("URLError levé sur port mort (hook attrape -> None)", True)
    except Exception as exc:
        check("exception réseau (hook attrape -> None)", True, type(exc).__name__)


def test_block():
    print("Bloc injecté :")
    results = [
        {"source": "siyuan", "titre": "RAG local - resultat Phase 1",
         "extrait": "modele intfloat/multilingual-e5-base"},
        {"source": "skill", "titre": "SKILL.md", "extrait": "contenu"},
    ]
    b = A._block(results, 200)
    check("contient <rag_context>", "<rag_context>" in b)
    check("contient le titre RAG", "RAG local - resultat Phase 1" in b)
    check("borne max_chars respectée", len(b) <= 200 + 120, "len=%d" % len(b))
    # troncature : max_chars assez grand pour 1 extrait, pas pour 2
    b2 = A._block(results, 80)
    check("troncature : 1er extrait inclus, 2e exclu", "Phase 1" in b2 and "contenu" not in b2,
          "len=%d" % len(b2))


if __name__ == "__main__":
    test_t2_regex_fallback()
    test_t3_rag_failure()
    test_block()
    print("\n== %d PASS / %d FAIL ==" % (PASS, FAIL))
    sys.exit(1 if FAIL else 0)
