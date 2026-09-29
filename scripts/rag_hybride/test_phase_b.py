#!/usr/bin/env python
"""Phase B — test du routeur de complexite sur 20 questions variees (RAG reel).

Le hook du plugin anima-memoire-router est appele exactement comme en production, avec deux
differences assumees et documentees :
  * _route est court-circuite pour rendre niveaux=[1,2,3] : on teste le chemin « le RAG est
    demande », donc le routeur de complexite et la selection (la couche JEV est mesuree a part,
    elle peut deja refuser le RAG — quirk pre-existant, voir le rapport) ;
  * _rag_search est le vrai POST /search sur 127.0.0.1:8200 (lecture seule).

Mesures : classe, k de recherche, nombre d'extraits injectes, caracteres injectes, latence.
Comparaison : meme question avec le routeur desactive (routeur=off) = ancien comportement.
"""
from __future__ import annotations

import importlib.util
import json
import os
import statistics
import sys
import time
from pathlib import Path

H = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
PLUG = H / "plugins" / "anima-memoire-router" / "__init__.py"
spec = importlib.util.spec_from_file_location("anima_memoire_router", PLUG)
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)

LOG = H / "data" / "rag" / "logs" / "phase_b_routage.jsonl"
if LOG.exists():
    LOG.unlink()


class Ctx:
    def __init__(self, routeur: str):
        self.routeur = routeur

    def get_config(self, key, default=None):
        return {"mode": "on", "routeur": self.routeur, "log_path": str(LOG),
                "rag_url": "http://127.0.0.1:8200", "rag_k": 5, "rag_k_complexe": 20,
                "timeout_s": 30.0, "max_chars": 4000}.get(key, default)


def faux_route(_text):
    return {"niveaux_a_consulter": [1, 2, 3], "source_decision": "test-phase-b"}


A._route = faux_route

QUESTIONS = [
    # --- attendu : simple (aucune recherche RAG) ---
    ("Bonjour", "simple"),
    ("Merci, c'est parfait", "simple"),
    ("2+2 ?", "simple"),
    ("Traduis « bonjour » en anglais", "simple"),
    ("Quelle heure est-il ?", "simple"),
    ("Résume en une phrase", "simple"),
    # --- attendu : moderee (RAG top-5) ---
    ("Quelle version de Wazuh rejette l'option pcre2 dans les règles ?", "moderee"),
    ("Quelle latence par décision mesure-t-on pour Laya ONNX sur CPU Windows ?", "moderee"),
    ("Quel modèle a provoqué la panne du pool gratuit le 17/09 ?", "moderee"),
    ("Combien de niveaux compte la chaîne de repli après la réparation du 22/09 ?", "moderee"),
    ("De combien le gain réel de récupération d'espace dépasse-t-il le gain annoncé ?", "moderee"),
    ("Quelle règle s'applique à la version de transformers sur ce poste ?", "moderee"),
    ("Que fait le skill windows-driver-integrity ?", "moderee"),
    # --- attendu : complexe (RAG top-20 puis sélection de 5) ---
    ("Quelle brique du second cerveau n'a aucune tâche planifiée, sur quel port écoute-t-elle et avec quel cadre applicatif ?", "complexe"),
    ("Quels seuils le contrôle qualité vidéo applique-t-il aux fantômes sur les lèvres et au flou de liaison ?", "complexe"),
    ("Quelle est la différence entre la couche L1 (wiki) et la couche L2 (RAG) du second cerveau ?", "complexe"),
    ("Combien de fragments compte l'index RAG, et quels chiffres annoncent l'architecture et le skill ?", "complexe"),
    ("Quel piège de polling Telegram fait rejouer une commande one-shot, et quel est le correctif ?", "complexe"),
    ("Le noyau SiYuan et l'API RAG écoutent sur quels ports, et laquelle n'a aucune tâche planifiée ?", "complexe"),
    ("Comment vérifier la version réellement utilisée par le manager Wazuh, et quel piège le .env présente-t-il ?", "complexe"),
]


def mesure(handler, question):
    t0 = time.time()
    res = handler(user_message=question)
    dt = time.time() - t0
    ctx = (res or {}).get("context", "") if isinstance(res, dict) else ""
    return dt, len(ctx), ctx


def principal():
    entrees = []
    resultats = []
    print(f"{'attendu':10s} {'obtenu':9s} {'k_rech':>6s} {'inj':>4s} {'chars':>6s} {'latence':>9s}  question")
    for question, attendu in QUESTIONS:
        handler = A.make_hook_handler(Ctx("on"))
        t0 = time.time()
        res = handler(user_message=question)
        dt = time.time() - t0
        ctx = (res or {}).get("context", "") if isinstance(res, dict) else ""
        dec = A._decider_complexite(question) or {}
        obtenu = dec.get("classe")
        k = dec.get("k_recherche", 0)
        n_inj = ctx.count("- [")
        resultats.append({"question": question, "attendu": attendu, "obtenu": obtenu,
                          "k_recherche": k, "extraits_injectes": n_inj,
                          "chars_injectes": len(ctx), "latence_s": round(dt, 4),
                          "conforme": obtenu == attendu})
        print(f"{attendu:10s} {obtenu:9s} {k:6d} {n_inj:4d} {len(ctx):6d} {dt*1000:8.1f}ms  {question[:52]}")

    entrees = [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    injections = [e for e in entrees if e.get("outcome") == "injected"]
    simples = [e for e in entrees if e.get("outcome") == "no_rag_simple"]
    ok_classe = sum(1 for r in resultats if r["conforme"])
    print(f"\nclassification conforme : {ok_classe}/{len(QUESTIONS)}")
    print(f"journal : {len(entrees)} decisions | {len(injections)} injections | {len(simples)} abstentions (simple)")
    for classe in ("simple", "moderee", "complexe"):
        vals = [r["latence_s"] for r in resultats if r["obtenu"] == classe]
        if vals:
            print(f"  latence {classe:9s} : mediane {statistics.median(vals)*1000:7.1f} ms  "
                  f"max {max(vals)*1000:7.1f} ms  (n={len(vals)})")
    lat_argile = [r for r in resultats if r["attendu"] == "simple"]
    lat_complexe = [r for r in resultats if r["obtenu"] == "complexe"]
    if lat_argile:
        print(f"  questions simples : {sum(1 for r in lat_argile if r['chars_injectes'] == 0)}/{len(lat_argile)} "
              f"sans aucune recherche RAG, mediane {statistics.median([r['latence_s'] for r in lat_argile])*1000:.1f} ms")
    if lat_complexe:
        print(f"  questions complexes : mediane {statistics.median([r['chars_injectes'] for r in lat_complexe]):.0f} "
              f"caracteres injectes pour {statistics.median([r['extraits_injectes'] for r in lat_complexe]):.0f} extraits")

    # comparaison : routeur desactive (ancien comportement, RAG top-k systematique)
    print("\n--- comparaison routeur=off (ancien comportement) ---")
    lat_off, lat_on = [], []
    for q, _a in QUESTIONS:
        h_off = A.make_hook_handler(Ctx("off"))
        t0 = time.time(); h_off(user_message=q); lat_off.append(time.time() - t0)
        h_on = A.make_hook_handler(Ctx("on"))
        t0 = time.time(); h_on(user_message=q); lat_on.append(time.time() - t0)
    print(f"  latence mediane avec routeur : {statistics.median(lat_on)*1000:7.1f} ms")
    print(f"  latence mediane sans routeur : {statistics.median(lat_off)*1000:7.1f} ms")
    print(f"  ecart cumule sur {len(QUESTIONS)} questions : {(sum(lat_off) - sum(lat_on))*1000:7.1f} ms "
          f"({(sum(lat_off) - sum(lat_on)) / sum(lat_off) * 100:.1f} % de la latence du hook)")

    json.dump({"resultats": resultats, "entrees_journal": entrees,
               "latence_mediane_routeur_on_s": round(statistics.median(lat_on), 4),
               "latence_mediane_routeur_off_s": round(statistics.median(lat_off), 4)},
              open(H / "data" / "rag" / "phase_b_test20.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\nresultat : data/rag/phase_b_test20.json")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
