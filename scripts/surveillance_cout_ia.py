#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Surveillance coût IA — détecte toute activité payante (deepseek/openrouter).

Sans LLM (no_agent). stdout = message d'alerte (vide = rien à signaler, pas de livraison).
- Anti-spam : 1 alerte/heure max. Retour à la normale après 1 h sans hausse.
- Critère : INCRÉMENT du cumul `estimated_cost_usd` des sessions payantes, comparé au
  dernier scan. Ce critère ne dépend pas de `started_at` : une bascule payante survenue
  au milieu d'une session déjà ouverte est donc vue au scan suivant.
- Premier scan (aucun état) : balayage des 24 dernières heures, message dédié
  « historique 24 h : X $ (modèle ...) ».
- Cumul qui baisse (sessions purgées) : reset du repère, journalisé, SANS alerte.
- Profil sans repère : repère initialisé explicitement et journalisé (pas de saut muet).
- Anti-spam : un incrément bloqué n'est jamais perdu — il est reporté (`hausse_en_attente`)
  et signalé par une alerte « hausse non signalée » dès que l'anti-spam expire ; le retour
  à la normale n'est annoncé qu'après écoulement du report. Un reset/baseline ne le purge pas.
- Aucun secret : ne lit ni n'affiche de clé/token ; uniquement profils, modèles, coûts.
- État : data/route_ia_fix/surveillance_cout.json
"""
import json
import pathlib
import sqlite3
import time

HERMES = pathlib.Path(r"C:\Users\searc\AppData\Local\hermes")
ETAT = HERMES / "data" / "route_ia_fix" / "surveillance_cout.json"

PROFILS = [
    ("default", HERMES / "state.db"),
    ("docs-writer", HERMES / "profiles" / "docs-writer" / "state.db"),
    ("watch", HERMES / "profiles" / "watch" / "state.db"),
    ("veille", HERMES / "profiles" / "veille" / "state.db"),
]

ANTI_SPAM_S = 3600          # 1 alerte / heure
RETOUR_S = 3600             # 1 h sans hausse pour « retour à la normale »
SEUIL_USD = 0.0001          # en dessous : arrondi de lecture, pas une activité payante
FENETRE_INITIALE_S = 24 * 3600
JOURNAL_MAX = 20


def cout_paye(db_path, fenetre_s):
    """UN SEUL passage sur la base, par profil et par scan.

    Retourne {"nb", "cumul", "avant", "modeles", "modeles_fenetre"} :
      cumul           : somme des coûts de toutes les sessions payantes ;
      avant           : somme des coûts des sessions payantes ANTÉRIEURES à la fenêtre ;
      modeles_fenetre : modèles des sessions payantes DANS la fenêtre.
    """
    vide = {"nb": 0, "cumul": 0.0, "avant": 0.0, "modeles": [], "modeles_fenetre": []}
    if not db_path.exists():
        return vide
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path.as_posix(), uri=True)
        rows = list(con.execute(
            "select model, coalesce(estimated_cost_usd,0), started_at from sessions "
            "where billing_provider in ('deepseek','openrouter')"))
        con.close()
    except Exception:
        return vide
    seuil = time.time() - fenetre_s
    cumul = avant = 0.0
    modeles, modeles_fenetre = [], []
    for modele, usd, debut in rows:
        usd = float(usd or 0)
        cumul += usd
        if modele:
            modeles.append(modele)
        if debut is not None and float(debut) > seuil:
            modeles_fenetre.append(modele)
        else:
            avant += usd
    return {"nb": len(rows), "cumul": round(cumul, 4), "avant": round(avant, 4),
            "modeles": modeles, "modeles_fenetre": modeles_fenetre}


def load_state():
    if ETAT.exists():
        try:
            return json.loads(ETAT.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_scan_ts": None, "last_alert_ts": 0.0, "alerting": False}


def journaliser(st, evenement, detail):
    st.setdefault("journal", []).append({"ts": round(time.time(), 1),
                                         "evenement": evenement, "detail": detail})
    del st["journal"][:-JOURNAL_MAX]


def main():
    now = time.time()
    st = load_state()
    couts = st.setdefault("couts", {})
    premier = st.get("last_scan_ts") is None

    # UN SEUL appel par profil et par scan (lecture cohérente).
    mesures = {profil: cout_paye(db, FENETRE_INITIALE_S) for profil, db in PROFILS}

    historique = 0.0
    modeles_hist = set()
    hausses = []

    for profil, db in PROFILS:
        m = mesures[profil]
        base = couts.get(profil)

        if base is None:
            if premier:
                # Balayage initial : l'historique 24 h est remonté comme une hausse dédiée.
                historique += max(0.0, round(m["cumul"] - m["avant"], 4))
                modeles_hist.update(x for x in m["modeles_fenetre"] if x)
            else:
                # Repère posé explicitement : pas de saut muet, pas d'alerte rétroactive.
                journaliser(st, "baseline initialisee",
                            "%s : repère posé à %s $" % (profil, m["cumul"]))
            couts[profil] = m["cumul"]
            continue

        delta = round(m["cumul"] - base, 4)
        if delta < 0:
            # Cumul purgé : reset du repère. Le report en attente n'est PAS purgé
            # (le coût a bien été engagé).
            journaliser(st, "reset", "%s : cumul %s -> %s $" % (profil, base, m["cumul"]))
            couts[profil] = m["cumul"]
        elif delta > SEUIL_USD:
            hausses.append((profil, delta, sorted(set(x for x in m["modeles"] if x))))
            couts[profil] = m["cumul"]
        else:
            couts[profil] = m["cumul"]

    st["last_scan_ts"] = now
    st["dernier_scan"] = {"nb_sessions_payantes": sum(m["nb"] for m in mesures.values()),
                          "cumul_usd": round(sum(m["cumul"] for m in mesures.values()), 4)}

    hausse_scan = round(sum(h[1] for h in hausses), 4)
    report = round(float(st.get("hausse_en_attente", 0.0) or 0.0), 4)
    anti_spam_ok = (now - st.get("last_alert_ts", 0.0)) >= ANTI_SPAM_S
    sortie = None

    if premier:
        if historique > SEUIL_USD and anti_spam_ok:
            sortie = ("Surveillance coût IA · %s\n"
                      "⚠️ historique 24 h : %s $ (modèle %s)\n"
                      "Actions possibles : vérifier la chaîne de repli du profil concerné."
                      % (time.strftime("%Y-%m-%d %H:%M:%S"), historique,
                         ", ".join(sorted(modeles_hist)) or "inconnu"))
            st["last_alert_ts"] = now
            st["alerting"] = True
    elif hausses and anti_spam_ok:
        # Alerte immédiate : elle porte la hausse du scan ET le report éventuel.
        montant = round(hausse_scan + report, 4)
        st["hausse_en_attente"] = 0.0
        detail = "\n".join("- %s : +%s $ (modèle %s)" % (p, d, ", ".join(mm) or "inconnu")
                           for p, d, mm in hausses)
        sortie = ("Surveillance coût IA · %s\n"
                  "⚠️ hausse depuis le dernier scan : +%s $\n%s\n"
                  "Actions possibles : vérifier la chaîne de repli du profil concerné."
                  % (time.strftime("%Y-%m-%d %H:%M:%S"), montant, detail))
        st["last_alert_ts"] = now
        st["alerting"] = True
    elif hausses:
        # Anti-spam actif : l'incrément n'est plus perdu, il est reporté sur l'alerte suivante.
        st["hausse_en_attente"] = round(report + hausse_scan, 4)
    elif report > 0 and anti_spam_ok:
        # Plus rien de neuf, mais un incrément attend : on le signale enfin.
        st["hausse_en_attente"] = 0.0
        sortie = ("Surveillance coût IA · %s\n"
                  "⚠️ hausse non signalée : +%s $ (report d'une alerte bloquée par l'anti-spam)\n"
                  "Actions possibles : vérifier la chaîne de repli du profil concerné."
                  % (time.strftime("%Y-%m-%d %H:%M:%S"), report))
        st["last_alert_ts"] = now
        st["alerting"] = True
    elif st.get("alerting") and report == 0 and (now - st.get("last_alert_ts", 0.0)) >= RETOUR_S:
        sortie = ("Surveillance coût IA · %s\n"
                  "✓ Retour à la normale : aucune hausse payante depuis 1 h."
                  % time.strftime("%Y-%m-%d %H:%M:%S"))
        st["alerting"] = False

    ETAT.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    if sortie:
        print(sortie)


if __name__ == "__main__":
    main()
