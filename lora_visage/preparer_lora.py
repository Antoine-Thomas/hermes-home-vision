# -*- coding: utf-8 -*-
"""3d — Recadrage sur le visage et resize 1024x1024 pour le LoRA.

    "<venv LatentSync>\\python.exe" preparer_lora.py

Lit :
  - filtre_visage.json      (photos retenues en 3b)
  - attributs.json          (angle / expression / arriere_plan / cadrage, produits par l'analyse visuelle)

Pour chaque photo retenue :
  - redetecte le visage (InsightFace) pour avoir la bounding box exacte ;
  - recadre en carre centre sur le visage avec une marge de 1,5x la taille du visage
    (inclut un peu de cou, cheveux, epaules) ;
  - redimensionne en 1024x1024 ;
  - ecrit un PNG (JPG qualite 100 si le PNG depasse 5 Mo) dans lora_visage/ ;
  - nomme selon la convention : face_neutre_01.png, 3-4g_sourire_02.png, profilg_serieux_01.png...

Les originaux ne sont JAMAIS modifies : ils sont seulement lus.
Rend aussi metadata.json (3e).
"""
import glob
import io
import json
import os

import cv2
import numpy as np

D = r"C:\Users\searc\Desktop\40 tof de moi"
SORTIE = os.path.join(D, "lora_visage")
ROOT = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\LatentSync\checkpoints\auxiliary"
CIBLE = 1024
MARGE = 1.5

from insightface.app import FaceAnalysis  # noqa: E402

app = FaceAnalysis(name="buffalo_l", root=ROOT)
app.prepare(ctx_id=0, det_size=(640, 640))

ABREV_ANGLE = {"face": "face", "3-4-gauche": "3-4g", "3-4-droit": "3-4d", "profil-gauche": "profilg",
               "profil-droit": "profild", "plongee": "plongee", "contre-plongee": "contreplongee"}
ABREV_EXPR = {"neutre": "neutre", "sourire-leger": "sourire", "sourire-franc": "sourirefranc",
              "serieux": "serieux", "autre": "autre"}


def cadre_visage(img):
    """Bounding box du plus grand visage, ou None."""
    visages = app.get(img)
    if len(visages) != 1:
        return None
    v = visages[0]
    return [int(max(0, c)) for c in v.bbox]


if __name__ == "__main__":
    mesures = json.load(io.open(os.path.join(SORTIE, "filtre_visage.json"), encoding="utf-8"))
    retenus = {m["fichier"]: m for m in mesures["detail"] if m.get("retenu_3b")}
    chemin_attributs = os.path.join(SORTIE, "attributs.json")
    if not os.path.exists(chemin_attributs):
        raise SystemExit("attributs.json absent : lancer l'analyse visuelle d'abord")
    attributs = {a["fichier"]: a for a in json.load(io.open(chemin_attributs, encoding="utf-8"))}

    compteurs, metadata = {}, []
    for nom, m in sorted(retenus.items()):
        a = attributs.get(nom, {})
        angle = ABREV_ANGLE.get(a.get("angle", "autre"), "autre")
        expr = ABREV_EXPR.get(a.get("expression", "autre"), "autre")
        cle = "%s_%s" % (angle, expr)
        compteurs[cle] = compteurs.get(cle, 0) + 1
        extension = ".png"

        img = cv2.imread(os.path.join(D, nom))
        if img is None:
            print("  ignore (illisible) : %s" % nom)
            continue
        h, w = img.shape[:2]
        boite = cadre_visage(img)
        if boite is None:
            print("  ignore (visage non unique a la redetection) : %s" % nom)
            continue
        x1, y1, x2, y2 = boite
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        cote = max(x2 - x1, y2 - y1) * MARGE
        demi = cote / 2.0
        # on garde le carre dans l'image quand c'est possible, sinon on decale
        gx1, gy1 = int(round(cx - demi)), int(round(cy - demi))
        gx2, gy2 = int(round(cx + demi)), int(round(cy + demi))
        gx1, gy1 = max(0, gx1), max(0, gy1)
        gx2, gy2 = min(w, gx2), min(h, gy2)
        carre = img[gy1:gy2, gx1:gx2]
        if carre.size == 0:
            continue
        cote_carre = min(carre.shape[0], carre.shape[1])
        dec_x = (carre.shape[1] - cote_carre) // 2
        dec_y = (carre.shape[0] - cote_carre) // 2
        carre = carre[dec_y:dec_y + cote_carre, dec_x:dec_x + cote_carre]
        sortie = cv2.resize(carre, (CIBLE, CIBLE), interpolation=cv2.INTER_AREA)

        fichier = "%s_%02d.png" % (cle, compteurs[cle])
        chemin = os.path.join(SORTIE, fichier)
        cv2.imwrite(chemin, sortie, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        if os.path.getsize(chemin) > 5_000_000:
            fichier = os.path.splitext(fichier)[0] + ".jpg"
            chemin = os.path.join(SORTIE, fichier)
            cv2.imwrite(chemin, sortie, [cv2.IMWRITE_JPEG_QUALITY, 100])
            try:
                os.remove(os.path.join(SORTIE, os.path.splitext(fichier)[0] + ".png"))
            except OSError:
                pass
        metadata.append({
            "fichier": fichier, "source_originale": nom,
            "angle": a.get("angle", "?"), "expression": a.get("expression", "?"),
            "arriere_plan": a.get("arriere_plan", "?"), "cadrage": a.get("cadrage", "?"),
            "taille_visage_px": m["visage_px"], "nettete_laplacien": m["nettete_laplacien"],
            "doute_analyse": a.get("doute", False), "note": a.get("note", "")})
        print("  %-28s -> %s" % (nom[:28], fichier))

    io.open(os.path.join(SORTIE, "metadata.json"), "w", encoding="utf-8").write(
        json.dumps(metadata, ensure_ascii=False, indent=1))
    print("\n%d images preparees en %dx%d dans %s" % (len(metadata), CIBLE, CIBLE, SORTIE))
    import collections
    print("repartition angles x expressions :")
    for k, n in sorted(collections.Counter("%s_%s" % (i["fichier"].split("_")[0], i["fichier"].split("_")[1]) for i in metadata).items()):
        print("  %-22s %d" % (k, n))
