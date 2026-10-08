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
import json
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


def test_t4_routeur_complexite():
    print("T4 — routeur de complexité (phase B) :")
    _rag_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", "data", "rag")
    if _rag_dir not in sys.path:
        sys.path.insert(0, _rag_dir)
    import routeur_complexite as rc

    cas = [
        ("Bonjour", "simple"),
        ("2+2 ?", "simple"),
        ("Traduis 'bonjour' en anglais", "simple"),
        ("Quelle version de Wazuh rejette <pcre2> ?", "moderee"),
        ("Quel modèle d'embedding utilise le RAG local, et combien de dimensions ?", "complexe"),
        ("Quelle est la différence entre la couche L1 (wiki) et la couche L2 (RAG) ?", "complexe"),
    ]
    for question, attendu in cas:
        d = rc.decider(question)
        check("classe %s" % attendu, d["classe"] == attendu,
              "obtenu=%s k=%s | %s" % (d["classe"], d["k_recherche"], question[:40]))

    check("simple -> k_recherche 0", rc.decider("Bonjour")["k_recherche"] == 0)
    check("moderee -> k_recherche 5", rc.decider("Quelle version de Wazuh rejette pcre2 ?")["k_recherche"] == 5)
    check("complexe -> k_recherche 20", rc.decider("Compare A et B, et dis pourquoi ?")["k_recherche"] >= 20)

    # sélection locale : plafond de 2 fragments par document, 5 au total
    candidats = [
        {"source": "skill", "titre": "A", "score": 0.9, "extrait": "port 8200"},
        {"source": "skill", "titre": "A", "score": 0.8, "extrait": "port 8188"},
        {"source": "skill", "titre": "A", "score": 0.7, "extrait": "port 6806"},
        {"source": "skill", "titre": "B", "score": 0.6, "extrait": "index"},
        {"source": "siyuan", "titre": "C", "score": 0.5, "extrait": "index"},
        {"source": "siyuan", "titre": "D", "score": 0.4, "extrait": "index"},
    ]
    sel = rc.selectionner(candidats, "quels ports ?", k=5)
    titres = [f["titre"] for f in sel]
    check("sélection rend 5 fragments", len(sel) == 5, "n=%d" % len(sel))
    check("plafond 2 fragments par document", titres.count("A") <= 2, "titres=%s" % titres)


def test_t5_hook_phase_b():
    print("T5 — hook : décision du routeur AVANT le POST /search :")
    import tempfile

    log_path = os.path.join(tempfile.gettempdir(), "anima_router_test.log")
    if os.path.exists(log_path):
        os.remove(log_path)

    class Ctx:
        def get_config(self, key, default=None):
            return {"mode": "on", "routeur": "on", "log_path": log_path,
                    "rag_k": 5, "rag_k_complexe": 20}.get(key, default)

    appels = []

    def faux_route(text):
        return {"niveaux_a_consulter": [1, 2, 3], "source_decision": "test"}

    def faux_search(settings, text, k):
        appels.append(k)
        return {"resultats": [
            {"source": "skill", "titre": "Doc%d" % i, "score": 0.9 - i / 100.0,
             "extrait": "extrait %d sur les ports" % i} for i in range(k)]}

    vrai_route, vrai_search = A._route, A._rag_search
    A._route, A._rag_search = faux_route, faux_search
    try:
        handler = A.make_hook_handler(Ctx())
        r_simple = handler(user_message="Bonjour")
        check("question simple -> aucune injection", r_simple is None)
        check("question simple -> ZÉRO appel au RAG", appels == [], "appels=%s" % appels)

        r_moderee = handler(user_message="Quelle version de Wazuh rejette pcre2 ?")
        check("question modérée -> injection", isinstance(r_moderee, dict) and "context" in r_moderee)
        check("question modérée -> k_recherche 5", appels[-1] == 5, "k=%s" % appels[-1])

        r_complexe = handler(user_message="Compare le port du RAG et celui de ComfyUI, et dis pourquoi ?")
        check("question complexe -> injection", isinstance(r_complexe, dict) and "context" in r_complexe)
        check("question complexe -> k_recherche 20", appels[-1] == 20, "k=%s" % appels[-1])
        n_extraits = r_complexe["context"].count("- [")
        check("question complexe -> 5 extraits injectés", n_extraits == 5, "n=%d" % n_extraits)
    finally:
        A._route, A._rag_search = vrai_route, vrai_search

    lignes = []
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as fh:
            lignes = [json.loads(l) for l in fh if l.strip()]
    classes = [l.get("classe") for l in lignes if l.get("outcome") == "injected"]
    check("décision journalisée (classe) pour les 2 injections",
          classes == ["moderee", "complexe"], "classes=%s" % classes)
    check("abstention simple journalisée", any(l.get("outcome") == "no_rag_simple" for l in lignes),
          "lignes=%s" % [l.get("outcome") for l in lignes])


if __name__ == "__main__":
    test_t2_regex_fallback()
    test_t3_rag_failure()
    test_block()
    test_t4_routeur_complexite()
    test_t5_hook_phase_b()
    print("\n== %d PASS / %d FAIL ==" % (PASS, FAIL))
    sys.exit(1 if FAIL else 0)
