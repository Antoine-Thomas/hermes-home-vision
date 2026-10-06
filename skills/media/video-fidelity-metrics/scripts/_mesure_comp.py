#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Mesure + planche comparative VideoReTalking (etape 4, tests A/B/C).

Identique a _comparaison_alpha.py pour la metrique :
  visage detecte par insightface buffalo_l sur la SOURCE, bouche = landmarks 52-71,
  bande basse = moitie inferieure du visage, visage = bbox entiere.
Ajouts etape 4 :
  - liste de videos en argument (label=chemin), donc autant de panneaux que voulu ;
  - PSNR d'invariance 512 par video : PSNR(frame, resize(resize(frame,512),1920x1080)).
    ~40 dB = detail 1080p reel ; ~51 dB = l'image ne contient rien au-dela de 512x512 ;
  - controle d'alignement du fond (regle 70) pour chaque video.

Usage :
  <python LatentSync>/python _mesure_comp.py "SOURCE=<src>" "LATENTSYNC A2.0=<a20>" ... \
        [--png C:/chemin/sortie.png] [--frames 60,150,245]
"""
import os
import sys
import numpy as np
import cv2
import _greffe_hf as G

A20_DEFAUT = os.path.join(G.ICI, "ANIMA_tete_latentsync_hf_a20.mp4")
PNG_DEFAUT = r"C:\Users\searc\Desktop\ANIMA\ANIMA_vr_correction.png"
FR_DEFAUT = (60, 150, 245)


def lap(im, box=None):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    if box:
        x1, y1, x2, y2 = [int(v) for v in box]
        g = g[max(0, y1):y2, max(0, x1):x2]
    return float(cv2.Laplacian(np.ascontiguousarray(g, np.uint8), cv2.CV_32F).var())


def psnr(a, b):
    e = a.astype(np.float32) - b.astype(np.float32)
    mse = float((e * e).mean())
    if mse <= 1e-12:
        return 99.0
    return 10.0 * np.log10(255.0 * 255.0 / mse)


def rt512(im, n=512):
    h, w = im.shape[:2]
    return cv2.resize(cv2.resize(im, (n, n)), (w, h))


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


def barre(texte, largeur, h=34, fs=0.7, bg=(255, 255, 255), fg=(0, 0, 0)):
    b = np.full((h, largeur, 3), bg, np.uint8)
    cv2.putText(b, texte, (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, fs, fg, 2, cv2.LINE_AA)
    return b


def panel(img, titre, mesure, largeur):
    t = barre(titre, largeur)
    m = np.full((32 * len(mesure), largeur, 3), 255, np.uint8)
    for k, ligne in enumerate(mesure):
        cv2.putText(m, ligne, (10, 32 * (k + 1) - 9), cv2.FONT_HERSHEY_SIMPLEX,
                    0.68, (20, 20, 20), 2, cv2.LINE_AA)
    return np.vstack([t, img, m])


def decalage_fond(src, out, bbox, p=3):
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


def main(argv):
    args = [a for a in argv if "=" in a and not a.startswith("--")]
    png = PNG_DEFAUT
    frames = FR_DEFAUT
    for a in argv:
        if a.startswith("--png"):
            png = a.split("=", 1)[1]
        if a.startswith("--frames"):
            frames = tuple(int(x) for x in a.split("=", 1)[1].split(","))
    if not args:
        args = ["SOURCE=" + G.SRC, "LATENTSYNC A2.0=" + A20_DEFAUT]
    videos = []
    for a in args:
        lab, p = a.split("=", 1)
        videos.append((lab, p))

    app = G.app_face(True)
    sections = []
    for i in frames:
        imgs = [G.lire(p, i) for _l, p in videos]
        src = imgs[0]
        if src is None:
            print("frame %d : source illisible" % i)
            continue
        fs = app.get(src)
        if not fs:
            print("frame %d : aucun visage dans la source" % i)
            continue
        f = G.plus_grand(fs)
        x1, y1, x2, y2 = [int(v) for v in f.bbox]
        bbouche = zone_bouche(f.landmark_2d_106)
        bbande = (x1, int(y1 + 0.55 * (y2 - y1)), x2, y2)
        bvisage = (x1, y1, x2, y2)

        print()
        print("FRAME %d  (visage %dx%d, bouche %dx%d)" %
              (i, x2 - x1, y2 - y1, bbouche[2] - bbouche[0], bbouche[3] - bbouche[1]))
        ref = None
        cellules = []
        for (lab, _p), im in zip(videos, imgs):
            if im is None:
                print("  %-16s ILLISIBLE" % lab)
                continue
            b, nd, vs = lap(im, bbouche), lap(im, bbande), lap(im, bvisage)
            p512 = psnr(im, rt512(im))
            if ref is None:
                ref = (b, nd, vs)
            print("  %-16s bouche %8.1f (%5.1f%%) | bande %8.1f (%5.1f%%) | visage %8.1f (%5.1f%%)"
                  " | PSNR512 %5.1f dB" %
                  (lab, b, b / ref[0] * 100, nd, nd / ref[1] * 100, vs, vs / ref[2] * 100, p512))
            im_crop = cv2.resize(crop_bouche(im, (x1, y1, x2, y2)), None, fx=3, fy=3,
                                 interpolation=cv2.INTER_NEAREST)
            cellules.append(panel(im_crop, lab,
                                  ["bouche  %7.1f  (%4.1f%% src)" % (b, b / ref[0] * 100),
                                   "bande   %7.1f  (%4.1f%%)" % (nd, nd / ref[1] * 100),
                                   "visage  %7.1f  (%4.1f%%)" % (vs, vs / ref[2] * 100),
                                   "PSNR 512 : %5.1f dB" % p512],
                                  im_crop.shape[1]))
        H = max(c.shape[0] for c in cellules)
        norm = [np.vstack([c, np.full((H - c.shape[0], c.shape[1], 3), 255, np.uint8)])
                for c in cellules]
        ligne = norm[0]
        for c in norm[1:]:
            ligne = np.hstack([ligne, np.full((H, 12, 3), 255, np.uint8), c])
        sections.append(np.vstack([barre("FRAME %d" % i, ligne.shape[1], h=44, fs=1.0), ligne]))

    if not sections:
        print("aucune section -> pas de planche")
        return 1

    larg = max(s.shape[1] for s in sections)
    titre = np.full((70, larg, 3), 30, np.uint8)
    cv2.putText(titre, "ANIMA v7 - VideoReTalking, correction du compositing : zoom bouche x3 NEAREST",
                (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(titre, "variance du Laplacien (bouche 52-71 / bande basse / visage) + PSNR d'invariance 512",
                (12, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
    out = titre
    for k, s in enumerate(sections):
        s = np.hstack([s, np.full((s.shape[0], larg - s.shape[1], 3), 255, np.uint8)])
        out = np.vstack([out, s]) if k == 0 else np.vstack(
            [out, np.full((20, larg, 3), 255, np.uint8), s])
    cv2.imwrite(png, out)
    print()
    print("-> %s  (%dx%d)" % (png, out.shape[1], out.shape[0]))

    print()
    print("CONTROLE D'ALIGNEMENT (regle 70) - meilleur decalage du fond vs source :")
    for i in frames:
        s = G.lire(videos[0][1], i)
        if s is None:
            continue
        fs = app.get(s)
        if not fs:
            continue
        vb = [int(v) for v in G.plus_grand(fs).bbox]
        for lab, p in videos[1:]:
            im = G.lire(p, i)
            if im is None:
                continue
            d = decalage_fond(s, im, vb)
            if d:
                print("  frame %4d  %-16s ecart %6.2f a (dx=%+d, dy=%+d)" % (i, lab, d[0], d[1], d[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
