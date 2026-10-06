#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Etape 4, diagnostic : apres la correction du compositing, ou est la limite restante ?

Teste (frame 150) :
  1) le FOND hors visage (bande gauche) : A l'a-t-il corrige, B l'a-t-il corrige ?
     etalons : source (net) / et.3 512 (flou, 262-265 non corrige).
  2) la resolution intrinseque du visage regenere : on simule « visage regenere en N px
     puis remonte a la taille du visage » pour N = 256 / 384 / 512, et on compare aux
     sorties de VR. Si VR ~ SIM256, la limite restante est la resolution de travail du
     modele, pas le compositing.
  3) PSNR d'invariance 512 sur toute l'image.
"""
import numpy as np
import cv2
import _greffe_hf as G

FR = 150
REPO = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\video-retalking"


def lap(im, box=None):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    if box:
        x1, y1, x2, y2 = [int(v) for v in box]
        g = g[max(0, y1):y2, max(0, x1):x2]
    return float(cv2.Laplacian(np.ascontiguousarray(g, np.uint8), cv2.CV_32F).var())


def psnr(a, b):
    e = a.astype(np.float32) - b.astype(np.float32)
    mse = float((e * e).mean())
    return 99.0 if mse <= 1e-12 else 10.0 * np.log10(255.0 * 255.0 / mse)


def rt(im, n=512):
    h, w = im.shape[:2]
    return cv2.resize(cv2.resize(im, (n, n)), (w, h))


def sim_face(frame, bbox, n):
    """Simule un visage regenere en n x n puis remonte a la taille du visage."""
    out = frame.copy()
    x1, y1, x2, y2 = [int(v) for v in bbox]
    reg = frame[y1:y2, x1:x2]
    out[y1:y2, x1:x2] = cv2.resize(cv2.resize(reg, (n, n)), (x2 - x1, y2 - y1))
    return out


app = G.app_face(True)
src = G.lire(G.SRC, FR)
f = G.plus_grand(app.get(src))
x1, y1, x2, y2 = [int(v) for v in f.bbox]
bv = (x1, y1, x2, y2)
bb = G.fenetre_levres(f.bbox)
fond = (max(0, x1 - 250), y1, max(0, x1 - 30), y2)
print("frame %d | visage bbox %s | fond %s" % (FR, bv, fond))
print()

cas = [("SOURCE (net)", src),
       ("SIM visage 256", sim_face(src, bv, 256)),
       ("SIM visage 384", sim_face(src, bv, 384)),
       ("SIM visage 512", sim_face(src, bv, 512)),
       ("SIM plein 512", rt(src, 512)),
       ("VR et.3 (512, pb=True)", G.lire(REPO + r"\_test_vr_out.mp4", FR)),
       ("VR TEST A (pb=False)", G.lire(REPO + r"\results\test_A.mp4", FR)),
       ("VR TEST B (2048, pb=False)", G.lire(REPO + r"\results\test_B.mp4", FR))]

src_v = None
print("%-26s %10s %10s %10s | %9s %9s" %
      ("cas", "lap_visage", "lap_bouche", "lap_FOND", "PSNR512", "mad_FOND"))
for lab, im in cas:
    if im is None:
        print("%-26s ILLISIBLE" % lab)
        continue
    vs, bo, fo = lap(im, bv), lap(im, bb), lap(im, fond)
    if src_v is None:
        src_v = (vs, bo, fo)
    print("%-26s %10.1f %10.1f %10.1f | %9.1f %9.2f" %
          (lab, vs, bo, fo, psnr(im, rt(im)), np.abs(src.astype(np.float32) - im.astype(np.float32))[
              fond[1]:fond[3], fond[0]:fond[2]].mean()))
print()
print("pourcentages par rapport a la source (visage / bouche / FOND) et PSNR512 de la source = %.1f dB"
      % psnr(src, rt(src)))
for lab, im in cas:
    if im is None or lab.startswith("SOURCE"):
        continue
    vs, bo, fo = lap(im, bv), lap(im, bb), lap(im, fond)
    print("  %-26s %5.1f%% %5.1f%% %6.1f%%" %
          (lab, vs / src_v[0] * 100, bo / src_v[1] * 100, fo / src_v[2] * 100))
