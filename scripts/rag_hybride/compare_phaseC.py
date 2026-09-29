#!/usr/bin/env python
"""Phase C — comparaison RAGAS avant/apres phase B (lecture seule, aucun appel reseau)."""
import json, sys, io

R = r"C:/Users/searc/AppData/Local/hermes/data/rag"
METRIQUES = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
SEUIL_ARRET, SEUIL_RERANK = 5.0, 15.0


def charge(nom):
    return json.load(io.open(f"{R}/{nom}", encoding="utf-8"))


def main():
    avant = charge("ragas_baseline_20260929.json")
    apres = charge("ragas_apres_phaseB_20260929.json")
    print("=== moyennes globales ===")
    print(f"{'metrique':18s} {'avant':>8s} {'apres':>8s} {'delta':>9s} {'relatif':>9s}")
    deltas = []
    for m in METRIQUES:
        a, b = avant["moyennes"].get(m), apres["moyennes"].get(m)
        if a is None or b is None:
            print(f"{m:18s} {'n/a':>8s} {'n/a':>8s}")
            continue
        d = b - a
        rel = d / a * 100 if a else 0.0
        deltas.append(rel)
        print(f"{m:18s} {a:8.4f} {b:8.4f} {d:+9.4f} {rel:+8.1f} %")
    if deltas:
        moy = sum(deltas) / len(deltas)
        print(f"\ngain relatif moyen : {moy:+.2f} %")
        if moy < SEUIL_ARRET:
            print(f"decision (regle utilisateur) : gain < {SEUIL_ARRET} % -> ON S'ARRETE LA.")
        elif moy > SEUIL_RERANK:
            print(f"decision (regle utilisateur) : gain > {SEUIL_RERANK} % -> le reranker multilingue peut etre envisage.")
        else:
            print(f"decision (regle utilisateur) : {SEUIL_ARRET} % <= gain <= {SEUIL_RERANK} % -> zone grise, arbitrage utilisateur.")

    # par type
    print("\n=== par type de question ===")
    for t in ("factuelle", "synthese", "transversale"):
        print(f"  {t} :")
        for m in METRIQUES:
            va = [q["scores"].get(m) for q in avant["par_question"] if q["type"] == t and q["scores"].get(m) is not None]
            vb = [q["scores"].get(m) for q in apres["par_question"] if q["type"] == t and q["scores"].get(m) is not None]
            if va and vb:
                ma, mb = sum(va) / len(va), sum(vb) / len(vb)
                print(f"    {m:18s} {ma:7.3f} -> {mb:7.3f}  ({mb - ma:+.3f})")

    # retrieval
    ra = sum(1 for r in avant["resultats"] if r["rang_premier_document_attendu"])
    rb = sum(1 for r in apres["resultats"] if r["rang_premier_document_attendu"])
    print(f"\ndocument attendu dans les fragments injectes : {ra}/{len(avant['resultats'])} -> {rb}/{len(apres['resultats'])}")
    lat_a = [r["latence_rag_s"] for r in avant["resultats"]]
    lat_b = [r["latence_rag_s"] for r in apres["resultats"]]
    print(f"latence RAG mediane : {sorted(lat_a)[len(lat_a)//2]*1000:.1f} ms -> {sorted(lat_b)[len(lat_b)//2]*1000:.1f} ms")
    classes = {}
    for r in apres["resultats"]:
        classes[r.get("classe_routeur")] = classes.get(r.get("classe_routeur"), 0) + 1
    print("classes de routage sur le jeu de 30 :", classes)

    # questions qui gagnent / perdent le plus (moyenne des 4 metriques)
    def m4(q):
        v = [q["scores"].get(m) for m in METRIQUES if q["scores"].get(m) is not None]
        return sum(v) / len(v) if v else 0.0
    pa = {q["id"]: q for q in avant["par_question"]}
    pb = {q["id"]: q for q in apres["par_question"]}
    ecarts = sorted(((m4(pb[i]) - m4(pa[i]), i) for i in pa if i in pb))
    print("\n3 plus fortes baisses :", [(i, round(d, 3)) for d, i in ecarts[:3]])
    print("3 plus fortes hausses :", [(i, round(d, 3)) for d, i in ecarts[-3:]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
