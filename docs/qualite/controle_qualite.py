# -*- coding: utf-8 -*-
"""Controle qualite d'une video rendue : quatre mesures, quatre seuils, un verdict.

Usage :
  python controle_qualite.py <video_finale> [--source <source_4k_propre.mp4>]
                             [--json <fichier.json>] [--texte <fichier.txt>]
                             [--sans-croise]        (ne pas appeler diag_sauts.py)

Sortie : rapport JSON + rapport texte lisible.
Codes de sortie (pour un pipeline) :
  0 = tout OK   1 = ATTENTION   2 = ALERTE

Les quatre mesures reprennent les methodes et les seuils des scripts de diagnostic
existants, qui ne sont ni modifies ni remplaces :

  1. Sauts d'image          <- diag_sauts.py   : MAD entre images voisines (320x180 gris),
                              pic = MAD > 4x la mediane. 1 pic = ALERTE.
  2. Flou de liaison        <- diag_cotes.py   : nettete (variance du Laplacien) des bandes
                              laterales, chute = sous 75 % de la mediane. ALERTE si 1 chute.
  3. Fantomes sur les levres <- fantomes.py    : densite de cretes de gradient dans la zone
                              des levres, rapportee a la source. OK si <= 1,25 ;
                              ATTENTION jusqu'a 1,5 ; ALERTE au-dela.
  4. Bout des levres        <- contour_levres.py : force du contour (99e percentile du
                              gradient) dans la zone des levres, rapportee a la source.
                              OK si >= 0,95 ; ATTENTION sinon.

Pour ne pas decoder la video quatre fois, les mesures 1 a 4 sont calculees en une seule
passe ; diag_sauts.py est ensuite appele en verification croisee (option --sans-croise pour
l'eviter quand le venv courant n'a pas ses dependances).
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

import cv2
import numpy as np

# --- zone des levres, en 1080p (reprise de contour_levres.py) -------------------------
BOX_1080 = (830, 700, 1090, 870)
# --- bandes laterales, en 1080p (reprises de diag_cotes.py ; la droite s'arrete avant
#     le logo, qui commence vers x = 1600) ---------------------------------------------
BANDES_1080 = {"gauche": (0, 0, 640, 1080), "droite": (1280, 0, 1560, 1080)}

SEUIL_SAUT = 4.0            # multiple de la mediane (diag_sauts.py)
SEUIL_CHUTE = 0.75          # part de la mediane en dessous de laquelle on alerte (diag_cotes.py)
SEUIL_FANTOME_OK = 1.25     # rapport a la source
SEUIL_FANTOME_ALERTE = 1.5
SEUIL_LEVRES = 0.95         # rapport a la source (contour_levres.py)

ECHANTILLONS = 80           # images echantillonnees pour les mesures 2 a 4


def zones(taille):
    """Adapte les zones de reference a la resolution reelle de la video."""
    w, h = taille
    k = h / 1080.0
    levres = tuple(int(v * k) for v in BOX_1080)
    bandes = {n: tuple(int(v * k) for v in z) for n, z in BANDES_1080.items()}
    return levres, bandes


def nettete(img):
    if img.size == 0:
        return float("nan")
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gris, cv2.CV_32F).var())


def mesures_levres(img, box):
    """Force du contour et densite de cretes dans la zone des levres."""
    x1, y1, x2, y2 = box
    zone = img[y1:y2, x1:x2]
    if zone.size == 0:
        return None
    gris = cv2.cvtColor(zone, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gris, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gris, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)
    seuil = np.percentile(mag, 97)
    # cretes = composantes connexes au-dessus du 97e percentile (methode de fantomes.py)
    masque = (mag > seuil).astype(np.uint8)
    n, _ = cv2.connectedComponents(masque, connectivity=8)
    return {"force": float(np.percentile(mag, 99)),
            "pixels_forts": int((mag > 120).sum()),
            "cretes": int(max(0, n - 1))}


def echantillonner(chemin, n=ECHANTILLONS):
    """Parcourt une video et rend les mesures par image echantillonnee."""
    cap = cv2.VideoCapture(chemin)
    if not cap.isOpened():
        raise SystemExit("video illisible : %s" % chemin)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    largeur = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    hauteur = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    pas = max(1, total // n) if total else 1

    levres_box, bandes = zones((largeur, hauteur))
    res = {"chemin": chemin, "images": total, "largeur": largeur, "hauteur": hauteur,
           "fps": round(fps, 3), "mad": [], "bandes": {k: [] for k in bandes},
           "levres": [], "pas": pas}
    i = 0
    precedent = None
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        petit = cv2.cvtColor(cv2.resize(fr, (320, 180), interpolation=cv2.INTER_AREA),
                             cv2.COLOR_BGR2GRAY).astype(np.float32)
        if precedent is not None:
            res["mad"].append((i, float(np.mean(np.abs(petit - precedent)))))
        precedent = petit
        if i % pas == 0:
            for nom, (x1, y1, x2, y2) in bandes.items():
                res["bandes"][nom].append(nettete(fr[y1:y2, x1:x2]))
            m = mesures_levres(fr, levres_box)
            if m:
                res["levres"].append(m)
        i += 1
    cap.release()
    return res


def verdict_sauts(mesures):
    mad = np.array([v for _, v in mesures["mad"]])
    if mad.size == 0:
        return {"controle": "sauts d'image", "verdict": "OK", "detail": "aucune mesure"}
    mediane = float(np.median(mad))
    seuil = SEUIL_SAUT * mediane
    pics = np.where(mad > seuil)[0]
    frames = [(int(mesures["mad"][p][0]), round(mad[p], 2)) for p in pics[:40]]
    return {"controle": "sauts d'image", "methode": "MAD 320x180, pic > 4x la mediane",
            "mediane_MAD": round(mediane, 3), "seuil": round(seuil, 3),
            "max_MAD": round(float(mad.max()), 3),
            "pics": len(pics), "frames": frames,
            "verdict": "OK" if len(pics) == 0 else "ALERTE"}


def verdict_bandes(mesures):
    detail, verdict = {}, "OK"
    for nom, valeurs in mesures["bandes"].items():
        v = np.array([x for x in valeurs if x == x])
        if v.size == 0:
            continue
        mediane = float(np.median(v))
        chutes = [round(float(x), 1) for x in v if x < SEUIL_CHUTE * mediane]
        detail[nom] = {"mediane": round(mediane, 1), "min": round(float(v.min()), 1),
                       "chutes": len(chutes)}
        if chutes:
            verdict = "ALERTE"
    return {"controle": "flou de liaison (bandes laterales)",
            "methode": "variance du Laplacien, chute sous 75 % de la mediane",
            "bandes": detail, "verdict": verdict}


def verdict_levres(mesures, source):
    if source is None or not mesures["levres"] or not source["levres"]:
        return {"controle": "levres", "verdict": "OK",
                "detail": "source non fournie : comparaison impossible"}
    def mediane(cle):
        return float(np.median([m[cle] for m in mesures["levres"]]))
    def mediane_src(cle):
        return float(np.median([m[cle] for m in source["levres"]]))
    force, force_src = mediane("force"), mediane_src("force")
    cretes, cretes_src = mediane("cretes"), mediane_src("cretes")
    r_force = force / force_src if force_src else float("nan")
    r_cretes = cretes / cretes_src if cretes_src else float("nan")

    if r_cretes <= SEUIL_FANTOME_OK:
        v_fantome = "OK"
    elif r_cretes <= SEUIL_FANTOME_ALERTE:
        v_fantome = "ATTENTION"
    else:
        v_fantome = "ALERTE"
    v_bout = "OK" if r_force >= SEUIL_LEVRES else "ATTENTION"
    return {"controle": "levres", "methode": "cretes de gradient et 99e percentile, vs source",
            "rapport_cretes": round(r_cretes, 3), "rapport_force": round(r_force, 3),
            "seuils": {"fantomes_OK": SEUIL_FANTOME_OK, "fantomes_ALERTE": SEUIL_FANTOME_ALERTE,
                       "bout_des_levres": SEUIL_LEVRES},
            "verdict_fantomes": v_fantome, "verdict_bout_des_levres": v_bout,
            "verdict": "ALERTE" if "ALERTE" in (v_fantome, v_bout) else
                       ("ATTENTION" if "ATTENTION" in (v_fantome, v_bout) else "OK")}


def croise_diag_sauts(video):
    """Appelle diag_sauts.py (non modifie) et rend son verdict sur les pics."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diag_sauts.py")
    if not os.path.exists(script):
        return {"disponible": False, "raison": "diag_sauts.py introuvable"}
    try:
        r = subprocess.run([sys.executable, script, video], capture_output=True, text=True,
                           timeout=1800)
    except Exception as e:
        return {"disponible": False, "raison": str(e)}
    sortie = (r.stdout or "") + (r.stderr or "")
    ligne = next((l for l in sortie.splitlines() if "pics >" in l), None)
    return {"disponible": True, "code": r.returncode, "ligne": ligne}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--source", default=None, help="source 4K propre (V4_SRC4K)")
    p.add_argument("--json", default=None)
    p.add_argument("--texte", default=None)
    p.add_argument("--sans-croise", action="store_true")
    a = p.parse_args()

    if not os.path.exists(a.video):
        raise SystemExit("video introuvable : %s" % a.video)
    source = a.source or os.environ.get("V4_SRC4K")
    if source and not os.path.exists(source):
        print("source indiquee mais introuvable, ignoree : %s" % source)
        source = None

    print("analyse de %s ..." % a.video)
    mesures = echantillonner(a.video)
    mesures_src = echantillonner(source, n=40) if source else None

    controles = [verdict_sauts(mesures), verdict_bandes(mesures),
                 verdict_levres(mesures, mesures_src)]
    croise = None if a.sans_croise else croise_diag_sauts(a.video)

    verdicts = [c["verdict"] for c in controles]
    if "ALERTE" in verdicts:
        global_verdict, code = "ALERTE", 2
    elif "ATTENTION" in verdicts:
        global_verdict, code = "ATTENTION", 1
    else:
        global_verdict, code = "OK", 0

    rapport = {"date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
               "video": os.path.abspath(a.video),
               "source": os.path.abspath(source) if source else None,
               "images_analysees": mesures["images"],
               "resolution": "%dx%d" % (mesures["largeur"], mesures["hauteur"]),
               "fps": mesures["fps"], "verdict": global_verdict, "code": code,
               "controles": controles, "verification_croisee": croise}

    # --- rapport texte
    lignes = ["RAPPORT QUALITE — %s" % rapport["date"],
              "video   : %s" % rapport["video"],
              "source  : %s" % (rapport["source"] or "(non fournie)"),
              "format  : %s a %s i/s, %s images" % (rapport["resolution"], rapport["fps"],
                                                    rapport["images_analysees"]),
              "VERDICT : %s (code %d)" % (global_verdict, code), ""]
    for c in controles:
        lignes.append("[%s] %s" % (c["verdict"], c["controle"]))
        lignes.append("      %s" % c.get("methode", c.get("detail", "")))
        if c["controle"] == "sauts d'image":
            lignes.append("      mediane MAD %.3f | seuil %.3f | max %.3f"
                          % (c["mediane_MAD"], c["seuil"], c["max_MAD"]))
            lignes.append("      pics : %d %s" % (c["pics"], c["frames"][:12]))
        elif "bandes" in c:
            for nom, d in c["bandes"].items():
                lignes.append("      %-8s mediane %8.1f | min %8.1f | chutes %d"
                              % (nom, d["mediane"], d["min"], d["chutes"]))
        elif "rapport_cretes" in c:
            lignes.append("      cretes (fantomes) : %.3f x la source | force du contour : "
                          "%.3f x la source" % (c["rapport_cretes"], c["rapport_force"]))
        lignes.append("")
    if croise:
        lignes.append("verification croisee diag_sauts.py : %s"
                      % ("indisponible (%s)" % croise.get("raison") if not croise["disponible"]
                         else croise.get("ligne", "(pas de ligne de pics)")))
    texte = "\n".join(lignes)

    horodatage = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dossier = os.path.dirname(os.path.abspath(a.video))
    chemin_json = a.json or os.path.join(dossier, "rapport_qualite_%s.json" % horodatage)
    chemin_txt = a.texte or os.path.splitext(chemin_json)[0] + ".txt"
    with open(chemin_json, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=1)
    with open(chemin_txt, "w", encoding="utf-8") as f:
        f.write(texte + "\n")

    print(texte)
    print("rapport ecrit : %s" % chemin_json)
    sys.exit(code)


if __name__ == "__main__":
    main()
