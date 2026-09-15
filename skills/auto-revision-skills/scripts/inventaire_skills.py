# -*- coding: utf-8 -*-
"""Inventaire et audit en lecture seule du dossier de skills de Hermes.

    python inventaire_skills.py                 # rapport dans le dossier courant
    python inventaire_skills.py --sortie "C:\\...\\rapport_revision.md"
    python inventaire_skills.py --etat          # seulement l'etat du declencheur

Ce que le script détecte, mécaniquement :
  - DOUBLONS POSSIBLES : deux skills dont le nom ou la description se recouvrent fortement
  - OBSOLETES : references a des fichiers ou des commandes qui n'existent plus sur la machine
  - MANQUES : scripts/depots de travail qu'aucun skill ne mentionne

Ce qu'il ne fait PAS : aucune modification, aucun deplacement, aucune suppression de skill.
Les propositions sont des propositions : la validation est humaine.

Le fichier d'etat (skills/../revision_skills_etat.json) retient le nombre de skills et la date de
la derniere revision : c'est lui qui dit si le declencheur « 10 nouveaux skills » ou « une semaine »
est atteint.
"""
import argparse
import datetime
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys

SKILLS = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", "skills")
ETAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "revision_skills_etat.json")
ETAT = os.path.abspath(ETAT)
DOSSIERS_TRAVAIL = [r"C:\Users\searc\Desktop\hermes_tuto_v4",
                    r"C:\Users\searc\Desktop\hermes_install",
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", "data", "rag")]
MOTS_VIDES = set("""de la le les des du un une et en pour par avec sans sur dans au aux ce cet
cette qui que quoi dont ou est sont a il elle on nous vous ils elles se sa son ses leur leurs
plus moins tres peu tout tous toute toutes meme aussi comme si ne pas plus d l s qu""".split())


def skills():
    trouves = []
    for chemin in glob.glob(os.path.join(SKILLS, "**", "SKILL.md"), recursive=True):
        t = io.open(chemin, encoding="utf-8", errors="replace").read()
        nom = re.search(r"^name:\s*(.+)$", t, re.M)
        desc = re.search(r"^description:\s*(.+)$", t, re.M)
        rel = os.path.relpath(os.path.dirname(chemin), SKILLS)
        trouve = {"chemin": chemin, "dossier": rel,
                  "nom": (nom.group(1).strip().strip('"') if nom else os.path.basename(os.path.dirname(chemin))),
                  "description": (desc.group(1).strip().strip('"') if desc else ""),
                  "octets": os.path.getsize(chemin),
                  "modifie": datetime.datetime.fromtimestamp(os.path.getmtime(chemin)).strftime("%Y-%m-%d"),
                  "texte": t}
        trouve["fichiers"] = sorted(set(re.findall(r"[A-Za-z]:\\[^\s`\"'\)\]]+", t)))
        trouve["commandes"] = sorted(set(re.findall(r"^\s*(hermes [a-z-]+|wp [a-z-]+|[a-z_]+\.py)",
                                                    t, re.M)))
        trouve["texte"] = t
        trouves.append(trouve)
    return sorted(trouves, key=lambda s: s["nom"])


def mots(texte):
    return {m for m in re.findall(r"[a-z0-9\-]{4,}", texte.lower()) if m not in MOTS_VIDES}


def doublons(liste, seuil=0.34):
    paires = []
    for i, a in enumerate(liste):
        for b in liste[i + 1:]:
            ma, mb = mots(a["nom"] + " " + a["description"]), mots(b["nom"] + " " + b["description"])
            if not ma or not mb:
                continue
            j = len(ma & mb) / float(len(ma | mb))
            if j >= seuil:
                paires.append((round(j, 2), a, b))
    return sorted(paires, key=lambda p: -p[0])


def obsoletes(liste):
    out = []
    for s in liste:
        manquants = [f for f in s["fichiers"] if not os.path.exists(f)]
        commandes_absentes = [c for c in s["commandes"]
                              if not c.startswith(("hermes", "wp"))
                              and not any(os.path.exists(os.path.join(os.path.dirname(s["chemin"]), c))
                                          for c in [c])
                              and shutil.which(c) is None]
        if manquants or commandes_absentes:
            out.append({"skill": s, "fichiers": manquants[:6], "commandes": commandes_absentes[:6]})
    return out


def sans_skill(liste):
    """Scripts de travail qu'aucun skill ne mentionne : taches repetees non couvertes."""
    textes = " ".join(s["texte"] for s in liste).lower()
    orphelins = []
    for dossier in DOSSIERS_TRAVAIL:
        if not os.path.isdir(dossier):
            continue
        for f in sorted(os.listdir(dossier)):
            if f.endswith((".py", ".ps1", ".sh")) and f.lower() not in textes:
                orphelins.append(os.path.join(dossier, f))
    return orphelins


def lire_etat():
    if os.path.exists(ETAT):
        try:
            return json.load(io.open(ETAT, encoding="utf-8"))
        except Exception:
            pass
    return {"derniere_revision": None, "skills_au_moment": 0}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sortie", default=None)
    p.add_argument("--etat", action="store_true", help="afficher seulement l'etat du declencheur")
    a = p.parse_args()

    liste = skills()
    etat = lire_etat()
    nouveaux = len(liste) - (etat.get("skills_au_moment") or 0)
    derniere = etat.get("derniere_revision")
    jours = None
    if derniere:
        try:
            jours = (datetime.date.today()
                     - datetime.datetime.strptime(derniere, "%Y-%m-%d").date()).days
        except Exception:
            pass

    if a.etat:
        print("skills installes : %d" % len(liste))
        print("derniere revision : %s" % (derniere or "jamais"))
        print("nouveaux depuis   : %d (declencheur a 10)" % nouveaux)
        print("jours depuis      : %s (declencheur a 7)" % (jours if jours is not None else "n/a"))
        declenche = nouveaux >= 10 or jours is None or jours >= 7
        print("revision conseillee : %s" % ("OUI" if declenche else "pas encore"))
        sys.exit(0)

    d = doublons(liste)
    o = obsoletes(liste)
    s = sans_skill(liste)

    lignes = ["# Revision des skills — %s" % datetime.date.today().strftime("%d/%m/%Y"), "",
              "Inventaire de **%d skills** dans `%s`." % (len(liste), SKILLS),
              "Derniere revision : %s (%s nouveaux skills depuis, %s jours)."
              % (derniere or "jamais", nouveaux, jours if jours is not None else "n/a"), "",
              "> Rapport en lecture seule : aucun skill n'a ete modifie, deplace ou supprime.", ""]

    lignes += ["## 1. Doublons possibles", ""]
    if d:
        lignes += ["| Recouvrement | Skill A | Skill B |", "|---|---|---|"]
        for j, x, y in d[:15]:
            lignes.append("| %.2f | `%s` | `%s` |" % (j, x["nom"], y["nom"]))
        lignes += ["", "Proposition : lire les deux, fusionner si le role est identique, "
                       "garder l'autre en `references/` du skill conserve."]
    else:
        lignes.append("Aucun recouvrement au-dessus du seuil (0,34 de similarite).")

    lignes += ["", "## 2. Skills a verifier (references disparues)", ""]
    if o:
        for e in o[:20]:
            lignes.append("- **%s**" % e["skill"]["nom"])
            for f in e["fichiers"]:
                lignes.append("  - fichier introuvable : `%s`" % f)
            for c in e["commandes"]:
                lignes.append("  - commande introuvable : `%s`" % c)
        lignes += ["", "Proposition : corriger la reference, ou archiver le skill s'il decrit un "
                       "outil qui n'existe plus (`hermes curator archive <nom>`)."]
    else:
        lignes.append("Aucune reference morte detectee.")

    lignes += ["", "## 3. Taches sans skill", "",
               "Scripts de travail qu'aucun skill ne mentionne :", ""]
    if s:
        for f in s[:25]:
            lignes.append("- `%s`" % f)
        lignes += ["", "Proposition : si un de ces scripts est relance a la main plus d'une fois, "
                       "il merite un skill (procedure + pieges + verification)."]
    else:
        lignes.append("Tous les scripts de travail sont mentionnes par au moins un skill.")

    lignes += ["", "## 4. Etat du declencheur", "",
               "| Indicateur | Valeur | Declencheur |", "|---|---|---|",
               "| Nouveaux skills | %d | 10 |" % nouveaux,
               "| Jours depuis la revision | %s | 7 |" % (jours if jours is not None else "n/a"), ""]

    sortie = a.sortie or os.path.join(os.getcwd(),
                                      "rapport_revision_%s.md" % datetime.date.today().isoformat())
    io.open(sortie, "w", encoding="utf-8", newline="\n").write("\n".join(lignes) + "\n")
    io.open(ETAT, "w", encoding="utf-8").write(json.dumps(
        {"derniere_revision": datetime.date.today().isoformat(), "skills_au_moment": len(liste)},
        ensure_ascii=False, indent=1) + "\n")

    print("skills invoques : %d | doublons possibles : %d | references mortes : %d | scripts sans skill : %d"
          % (len(liste), len(d), len(o), len(s)))
    if d:
        print("  doublon le plus proche : %s <-> %s (%.2f)" % (d[0][1]["nom"], d[0][2]["nom"], d[0][0]))
    print("rapport ecrit : %s" % sortie)
    print("etat enregistre : %s" % ETAT)
