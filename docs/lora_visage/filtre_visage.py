# -*- coding: utf-8 -*-
"""3b — Filtre qualite base sur le VISAGE (pas sur l'image).

    "<venv LatentSync>\\python.exe" filtre_visage.py

Pour chaque photo de « 40 tof de moi » :
  - detection du visage (InsightFace buffalo_l, GPU) ;
  - bounding box du visage EN PIXELS ;
  - nettete : variance du Laplacien DANS la zone du visage ;
  - exposition : pourcentage de pixels crames (>=250) ou noirs (<=5) DANS le visage ;
  - flou de bouge : largeur du bord sur le contour du visage (un bord etale = traînee) ;
  - nb de visages detectes.

Eliminations appliquees (regles demandees) :
  0 visage · plus d'un visage · petit cote < 512 px · grand cote < 700 px ·
  nettete sous la mediane du corpus · plus de 2 % du visage crame ou noir.

Sortie : filtre_visage.json (mesures completes, rien n'est supprime ni deplace).
Lecture SEULE sur les originaux.
"""
import glob
import io
import json
import os
import sys

import cv2
import numpy as np

D = r"C:\Users\searc\Desktop\40 tof de moi"
SORTIE = os.path.join(D, "lora_visage")
ROOT = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\LatentSync\checkpoints\auxiliary"

from insightface.app import FaceAnalysis  # noqa: E402

app = FaceAnalysis(name="buffalo_l", root=ROOT)
app.prepare(ctx_id=0, det_size=(640, 640))          # GPU

PETIT_MIN, GRAND_MIN = 512, 700


def mesurer(chemin):
    img = cv2.imread(chemin)
    if img is None:
        return {"fichier": os.path.basename(chemin), "erreur": "illisible"}
    h, w = img.shape[:2]
    visages = app.get(img)
    r = {"fichier": os.path.basename(chemin), "image": [w, h], "nb_visages": len(visages)}
    if not visages:
        return r
    # le plus grand visage (s'il y en a plusieurs, la regle elimine de toute facon)
    v = max(visages, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    x1, y1, x2, y2 = [int(max(0, c)) for c in v.bbox]
    r["visage_px"] = [x2 - x1, y2 - y1]
    r["score_detection"] = round(float(v.det_score), 3)
    zone = img[y1:y2, x1:x2]
    if zone.size == 0:
        return r
    gris = cv2.cvtColor(zone, cv2.COLOR_BGR2GRAY)
    r["nettete_laplacien"] = round(float(cv2.Laplacian(gris, cv2.CV_32F).var()), 2)
    r["pct_crame"] = round(100.0 * float((gris >= 250).sum()) / gris.size, 3)
    r["pct_noir"] = round(100.0 * float((gris <= 5).sum()) / gris.size, 3)
    # flou de bouge : gradient du bord du visage. Un bord net a un gradient fort et etroit.
    gx = cv2.Sobel(gris, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gris, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)
    r["gradient_p99"] = round(float(np.percentile(mag, 99)), 1)
    # largeur du bord : part de pixels au-dessus de 40 % du max, indice de traînee
    fort = mag > 0.4 * mag.max() if mag.max() > 0 else mag > 1e9
    r["pct_bord_fort"] = round(100.0 * float(fort.sum()) / mag.size, 3)
    return r


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    fichiers = sorted(f for f in glob.glob(os.path.join(D, "*"))
                      if f.lower().endswith((".jpg", ".jpeg", ".png")))
    print("%d photos a analyser (lecture seule)" % len(fichiers), flush=True)

    mesures = []
    for i, f in enumerate(fichiers, 1):
        m = mesurer(f)
        mesures.append(m)
        if i % 10 == 0:
            print("  %d/%d" % (i, len(fichiers)), flush=True)

    # seuil de nettete calibre sur la mediane du corpus (visages detectes uniquement)
    nets = [m["nettete_laplacien"] for m in mesures if m.get("nettete_laplacien")]
    seuil_nettete = float(np.median(nets)) if nets else 0.0

    for m in mesures:
        raisons = []
        if m.get("erreur"):
            raisons.append("illisible")
        elif m["nb_visages"] == 0:
            raisons.append("aucun visage")
        elif m["nb_visages"] > 1:
            raisons.append("%d visages" % m["nb_visages"])
        else:
            px = m["visage_px"]
            if min(px) < PETIT_MIN:
                raisons.append("petit cote %d px < %d" % (min(px), PETIT_MIN))
            if max(px) < GRAND_MIN:
                raisons.append("grand cote %d px < %d" % (max(px), GRAND_MIN))
            if m.get("nettete_laplacien", 0) < seuil_nettete:
                raisons.append("nettete %.0f < mediane %.0f" % (m["nettete_laplacien"], seuil_nettete))
            if m.get("pct_crame", 0) > 2:
                raisons.append("%.1f %% crame" % m["pct_crame"])
            if m.get("pct_noir", 0) > 2:
                raisons.append("%.1f %% noir" % m["pct_noir"])
        m["retenu_3b"] = not raisons
        m["raisons"] = raisons

    retenus = [m for m in mesures if m["retenu_3b"]]
    elimines = [m for m in mesures if not m["retenu_3b"]]
    bilan = {"photos": len(mesures), "seuil_nettete_mediane": round(seuil_nettete, 2),
             "retenus": len(retenus), "elimines": len(elimines),
             "detail": mesures}
    io.open(os.path.join(SORTIE, "filtre_visage.json"), "w", encoding="utf-8").write(
        json.dumps(bilan, ensure_ascii=False, indent=1))

    print("\nseuil de nettete (mediane du corpus) : %.1f" % seuil_nettete)
    print("RETENUS 3b : %d / %d" % (len(retenus), len(mesures)))
    import collections
    c = collections.Counter()
    for m in elimines:
        for r in m["raisons"]:
            c[r.split(" ")[0]] += 1
    print("principales raisons d'elimination :", dict(c.most_common(6)))
    print("\nvisages (cote le plus grand, en px) des retenus :")
    for m in sorted(retenus, key=lambda x: -max(x["visage_px"])):
        print("  %-28s visage %dx%d  nettete %8.1f  creux %s" %
              (m["fichier"][:28], m["visage_px"][0], m["visage_px"][1], m["nettete_laplacien"],
               m.get("pct_crame", 0) > 0.5))
    print("\nresultat : %s" % os.path.join(SORTIE, "filtre_visage.json"))
