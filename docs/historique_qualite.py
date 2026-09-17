# -*- coding: utf-8 -*-
"""Historique qualite : rassemble les rapports de controle qualite en un tableau suivi.

    python historique_qualite.py                          # dossier courant
    python historique_qualite.py --dossier "C:\\...\\hermes tuto"
    python historique_qualite.py --dossier . --siyuan      # publie aussi dans SiYuan
    python historique_qualite.py --hausse 4                # tendance sur 4 rendus

Lit tous les `rapport_qualite_*.json` d'un dossier (produits par `controle_qualite.py`), ecrit un
tableau Markdown chronologique dans `historique_qualite.md` a la racine de ce dossier, et signale
les tendances :

  - alerte_sauts    : les 3 derniers rendus sont en ALERTE sur les sauts d'image
  - fantomes_hausse : le ratio de fantomes monte depuis N rendus (defaut 3)
  - levres_baisse   : la force du contour des levres baisse depuis N rendus

Le script ne modifie ni ne supprime aucun rapport : il ne fait que les lire.
"""
import argparse
import datetime
import glob
import io
import json
import os
import subprocess
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
PUBLIER = r"C:\Users\searc\SiYuan\publier.py"


def lire(chemin):
    """Extrait d'un rapport les cinq colonnes utiles. Rend None si le fichier n'est pas lisible."""
    try:
        d = json.load(io.open(chemin, encoding="utf-8"))
    except Exception as e:
        print("  ignore (%s) : %s" % (e, os.path.basename(chemin)))
        return None
    sauts = fantomes = levres = None
    verdict_sauts = verdict_global = d.get("verdict")
    for c in d.get("controles", []):
        nom = (c.get("controle") or "").lower()
        if "sauts" in nom:
            sauts = c.get("pics")
            verdict_sauts = c.get("verdict")
        elif "levres" in nom:
            fantomes = c.get("rapport_cretes")
            levres = c.get("rapport_force")
    date = d.get("date") or ""
    try:
        cle = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    except Exception:
        cle = datetime.datetime.fromtimestamp(os.path.getmtime(chemin))
    return {"fichier": os.path.basename(chemin), "date": date, "cle": cle,
            "video": os.path.basename(d.get("video") or "?"), "verdict": verdict_global,
            "verdict_sauts": verdict_sauts, "sauts": sauts,
            "fantomes": fantomes, "levres": levres,
            "code": d.get("code"), "images": d.get("images_analysees")}


def tendances(lignes, hausse=3):
    """Signale les tendances simples sur les derniers rendus."""
    alertes = []
    derniers = lignes[-3:]
    if len(derniers) == 3 and all(l["verdict_sauts"] == "ALERTE" for l in derniers):
        alertes.append("**3 rendus consecutifs en ALERTE sur les sauts d'image.** "
                       "Chercher une cause devenue permanente (frontieres de segments, source, "
                       "decoupage) plutot qu'un accident isole.")
    for cle, nom in (("fantomes", "fantomes"), ("levres", "contour des levres")):
        vals = [l[cle] for l in lignes[-hausse:] if l[cle] is not None]
        if len(vals) >= hausse:
            if cle == "fantomes" and all(b > a for a, b in zip(vals, vals[1:])):
                alertes.append("Le ratio de %s **est en hausse depuis %d rendus** (%s -> %s). "
                               "Verifier le detourage du visage et le recalage."
                               % (nom, hausse, vals[0], vals[-1]))
            elif cle == "levres" and all(b < a for a, b in zip(vals, vals[1:])):
                alertes.append("La force du %s **est en baisse depuis %d rendus** (%s -> %s). "
                               "Verifier l'accentuation et le recalage de la bouche."
                               % (nom, hausse, vals[0], vals[-1]))
    if not alertes:
        alertes.append("Aucune tendance preoccupante sur les %d derniers rendus." % min(len(lignes), hausse))
    return alertes


def tableau(lignes):
    t = ["| Date | Video | Verdict | Sauts | Ratio fantomes | Ratio levres |",
         "|---|---|---|---|---|---|"]
    for l in lignes:
        t.append("| %s | `%s` | **%s** | %s | %s | %s |"
                 % (l["date"] or l["cle"].strftime("%Y-%m-%d %H:%M"),
                    l["video"], l["verdict"],
                    "-" if l["sauts"] is None else l["sauts"],
                    "-" if l["fantomes"] is None else ("%.3f" % l["fantomes"]),
                    "-" if l["levres"] is None else ("%.3f" % l["levres"])))
    return t


def publier_siyuan(dossier, contenu):
    if not os.path.exists(PUBLIER):
        print("publication impossible : %s introuvable" % PUBLIER)
        return
    provisoire = os.path.join(dossier, "historique_qualite.md")
    r = subprocess.run([sys.executable, PUBLIER, "video-ia", "/Historique qualite", provisoire],
                       capture_output=True, text=True)
    print("SiYuan : %s" % ((r.stdout or r.stderr or "").strip()[-160:] or "aucune reponse"))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dossier", default=".")
    p.add_argument("--hausse", type=int, default=3, help="nombre de rendus pour juger une tendance")
    p.add_argument("--siyuan", action="store_true", help="publier dans video-ia / Historique qualite")
    a = p.parse_args()

    dossier = os.path.abspath(a.dossier)
    rapports = sorted(glob.glob(os.path.join(dossier, "rapport_qualite_*.json")))
    if not rapports:
        raise SystemExit("aucun rapport_qualite_*.json dans %s" % dossier)
    print("%d rapport(s) trouve(s) dans %s" % (len(rapports), dossier))

    lignes = []
    for chemin in rapports:
        l = lire(chemin)
        if l:
            lignes.append(l)
    lignes.sort(key=lambda l: l["cle"])
    if not lignes:
        raise SystemExit("aucun rapport exploitable")

    texte = ["# Historique qualite",
             "",
             "> **Statut** : actif",
             "> **Derniere mise a jour** : %s" % datetime.datetime.now().strftime("%d/%m/%Y"),
             "",
             "%d rapport(s) de controle qualite, du plus ancien au plus recent." % len(lignes),
             ""]
    texte += tableau(lignes)
    texte += ["", "## Tendances", ""]
    for t in tendances(lignes, a.hausse):
        texte.append("- %s" % t)
    texte += ["", "## Comment lire", "",
              "- **Sauts** : nombre d'images dont l'ecart avec la voisine depasse 4 fois la mediane.",
              "- **Ratio fantomes** : cotes de gradient dans la zone des levres, rapportes a la source propre.",
              "- **Ratio levres** : force du contour des levres, rapportee a la source (`1,0` = aussi net).",
              "- Verdicts : `OK` (code 0) · `ATTENTION` (code 1) · `ALERTE` (code 2).",
              "",
              "Regenerer ce fichier : `python historique_qualite.py --dossier \"%s\"`" % dossier]

    sortie = os.path.join(dossier, "historique_qualite.md")
    io.open(sortie, "w", encoding="utf-8", newline="\n").write("\n".join(texte) + "\n")

    print("")
    print("\n".join(tableau(lignes)))
    print("")
    for t in tendances(lignes, a.hausse):
        print("TENDANCE : %s" % t.replace("**", ""))
    print("")
    print("historique ecrit : %s" % sortie)

    if a.siyuan:
        publier_siyuan(dossier, texte)
