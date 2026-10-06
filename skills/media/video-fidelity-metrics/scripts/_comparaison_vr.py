#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ETAPE 3.4/3.5 — VideoReTalking vs LatentSync alpha 2.0 vs SOURCE (test 10 s).

Meme methode que _comparaison_alpha.py :
  - variance du Laplacien sur 3 zones (bouche = landmarks 52-71, bande basse visage,
    visage entier), lue sur la face detectee par insightface buffalo_l sur la SOURCE ;
  - planche cote a cote SOURCE / LATENTSYNC A2.0 / VIDEO-RETALKING, zoom bouche x3 NEAREST.
Ajout : controle d'alignement de la regle 70 (decalage du FOND hors visage qui minimise
l'ecart avec la source, +/- 3 px) — si le meilleur decalage n'est pas (0,0), la comparaison
n'est pas valable telle quelle et il faut le dire.

    <python LatentSync>/python _comparaison_vr.py
"""
import os
import numpy as np
import cv2
import _greffe_hf as G

FRAMES = (60, 150, 245)
A20 = os.path.join(G.ICI, "ANIMA_tete_latentsync_hf_a20.mp4")
VR = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\video-retalking\_test_vr_out.mp4"
SORTIE = r"C:\Users\searc\Desktop\ANIMA\ANIMA_vr_vs_latentsync.png"

VIDEOS = [("SOURCE", G.SRC), ("LATENTSYNC A2.0", A20), ("VIDEO-RETALKING", VR)]


def zone_bouche(lm):
    bl = lm[52:72]
    zx1, zy1 = [int(v) for v in bl.min(0)]
    zx2, zy2 = [int(v) for v in bl.max(0)]
    return (zx1, zy1, zx2, zy2)


def crop_bouche(bgr, bb):
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    cx, cy = (bb[0] + bb[2]) // 2, bb[1] + 0.72 * h
    x1, x2 = int(cx - 0.34 * w), int(cx + 0.34 * w)
    y1, y2 = int(cy - 0.13 * h), int(cy + 0.13 * h)
    return bgr[max(0, y1):y2, max(0, x1):x2]


def barre_texte(texte, largeur, h=34, fs=0.7, bg=(255, 255, 255), fg=(0, 0, 0)):
    b = np.full((h, largeur, 3), bg, np.uint8)
    cv2.putText(b, texte, (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, fs, fg, 2, cv2.LINE_AA)
    return b


def panel(img, titre, mesure, largeur):
    t = barre_texte(titre, largeur)
    m = np.full((34 * len(mesure), largeur, 3), 255, np.uint8)
    for k, ligne in enumerate(mesure):
        cv2.putText(m, ligne, (10, 34 * (k + 1) - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.72, (20, 20, 20), 2, cv2.LINE_AA)
    return np.vstack([t, img, m])


def decalage_fond(src, out, bbox, p=3):
    """Regle 70 : meilleur decalage du FOND (bande hors visage) entre source et sortie."""
    h, w = src.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in bbox]
    gx2 = max(0, x1 - 20)
    gx1 = max(0, gx2 - 200)
    if gx2 - gx1 < 40:
        gx1, gx2 = min(w, x2 + 20), min(w, x2 + 220)
    gy1, gy2 = max(0, y1), min(h, y2)
    best = None
    for dy in range(-p, p + 1):
        for dx in range(-p, p + 1):
            yy1, yy2, xx1, xx2 = gy1 + dy, gy2 + dy, gx1 + dx, gx2 + dx
            if yy1 < 0 or xx1 < 0 or yy2 > h or xx2 > w:
                continue
            a = src[gy1:gy2, gx1:gx2].astype(np.float32)
            b = out[yy1:yy2, xx1:xx2].astype(np.float32)
            e = float(np.abs(a - b).mean())
            if best is None or e < best[0]:
                best = (e, dx, dy)
    return best


def main():
    app = G.app_face(True)
    lignes = []
    sections = []
    aligns = []

    for i in FRAMES:
        imgs = [G.lire(lab_path[1], i) for lab_path in VIDEOS]
        if any(im is None for im in imgs):
            print("frame %d : lecture impossible (%s)" %
                  (i, [VIDEOS[k][0] for k, im in enumerate(imgs) if im is None]))
            continue
        fs = app.get(imgs[0])
        if not fs:
            print("frame %d : aucun visage" % i)
            continue
        f = G.plus_grand(fs)
        vb = [int(v) for v in f.bbox]
        x1, y1, x2, y2 = vb
        bbouche = zone_bouche(f.landmark_2d_106)
        bbande = (x1, int(y1 + 0.55 * (y2 - y1)), x2, y2)
        bvisage = (x1, y1, x2, y2)

        val = {}
        for (lab, _p), im in zip(VIDEOS, imgs):
            val[lab] = (G.lapv(im, bbouche), G.lapv(im, bbande), G.lapv(im, bvisage))

        src = val["SOURCE"]
        for (lab, _p), im in zip(VIDEOS[1:], imgs[1:]):
            d = decalage_fond(imgs[0], im, vb)
            aligns.append((i, lab, d))

        lignes.append("FRAME %d (visage %dx%d, bouche %dx%d)" %
                      (i, x2 - x1, y2 - y1, bbouche[2] - bbouche[0], bbouche[3] - bbouche[1]))
        cellules = []
        for (lab, _p), im in zip(VIDEOS, imgs):
            b, nd, vs = val[lab]
            pct = (vs / src[2] * 100.0)
            im_crop = cv2.resize(crop_bouche(im, vb), None, fx=3, fy=3,
                                 interpolation=cv2.INTER_NEAREST)
            larg = im_crop.shape[1]
            cell = panel(im_crop, lab,
                         ["bouche   %7.1f" % b,
                          "bande    %7.1f" % nd,
                          "visage   %7.1f  (%4.0f%% src)" % (vs, pct)],
                         larg)
            cellules.append(cell)
            lignes.append("  %-16s bouche %7.1f (%4.0f%%) | bande %7.1f (%4.0f%%) | "
                          "visage %7.1f (%4.0f%%)" %
                          (lab, b, b / src[0] * 100, nd, nd / src[1] * 100, vs, pct))

        H = max(c.shape[0] for c in cellules)
        norm = []
        for c in cellules:
            pad = np.full((H - c.shape[0], c.shape[1], 3), 255, np.uint8)
            norm.append(np.vstack([c, pad]))
        sep = np.full((H, 12, 3), 255, np.uint8)
        ligne = norm[0]
        for c in norm[1:]:
            ligne = np.hstack([ligne, sep, c])
        entete = barre_texte("FRAME %d" % i, ligne.shape[1], h=44, fs=1.0)
        sections.append(np.vstack([entete, ligne]))

    Htitre = 70
    largeur_max = max(sec.shape[1] for sec in sections)
    titre = np.full((Htitre, largeur_max, 3), 30, np.uint8)
    cv2.putText(titre, "ANIMA v7 - VIDEO-RETALKING vs LatentSync alpha 2.0 vs SOURCE (zoom bouche x3 NEAREST)",
                (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(titre, "variance du Laplacien - bouche (landmarks 52-71) / bande basse / visage entier",
                (12, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
    out = titre
    for k, sec in enumerate(sections):
        sec = np.hstack([sec, np.full((sec.shape[0], largeur_max - sec.shape[1], 3), 255, np.uint8)])
        out = np.vstack([out, sec]) if k == 0 else np.vstack(
            [out, np.full((20, largeur_max, 3), 255, np.uint8), sec])

    cv2.imwrite(SORTIE, out)
    print("-> %s  (%dx%d)" % (SORTIE, out.shape[1], out.shape[0]))
    print()
    print("\n".join(lignes))
    print()
    print("CONTROLE D'ALIGNEMENT (regle 70) - meilleur decalage du fond vs source :")
    for (i, lab, d) in aligns:
        if d:
            print("  frame %4d  %-16s ecart %.2f a (dx=%+d, dy=%+d)" % (i, lab, d[0], d[1], d[2]))
        else:
            print("  frame %4d  %-16s pas de bande de fond exploitable" % (i, lab))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
