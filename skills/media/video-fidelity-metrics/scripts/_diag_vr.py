#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Diagnostic : ou est le flou dans la sortie VideoReTalking ?
Compare SOURCE / result.mp4 brut (mpeg4 du VideoWriter) / _test_vr_out.mp4 (mux h264)."""
import numpy as np
import cv2
import _greffe_hf as G

FR = 150
RAW = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\video-retalking\temp\temp\result.mp4"
OUT = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\video-retalking\_test_vr_out.mp4"


def lap(im, box=None):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    if box:
        x1, y1, x2, y2 = [int(v) for v in box]
        g = g[max(0, y1):y2, max(0, x1):x2]
    return float(cv2.Laplacian(np.ascontiguousarray(g, np.uint8), cv2.CV_32F).var())


def mad(a, b, box=None):
    if box:
        x1, y1, x2, y2 = [int(v) for v in box]
        a, b = a[max(0, y1):y2, max(0, x1):x2], b[max(0, y1):y2, max(0, x1):x2]
    return float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean())


app = G.app_face(True)
src = G.lire(G.SRC, FR)
f = G.plus_grand(app.get(src))
x1, y1, x2, y2 = [int(v) for v in f.bbox]
bv = (x1, y1, x2, y2)
bb = G.fenetre_levres(f.bbox) if hasattr(G, "fenetre_levres") else (x1, int(y1 + 0.6 * (y2 - y1)), x2, y2)
fond = (max(0, x1 - 250), y1, max(0, x1 - 30), y2)
print("visage bbox =", bv, "| fond(bande gauche) =", fond)
print()
print("%-12s %9s %9s %9s %9s | %9s %9s %9s" %
      ("fichier", "lap_full", "lap_vis.", "lap_bouch", "lap_fond", "mad_full", "mad_vis.", "mad_fond"))
for lab, p in [("SOURCE", G.SRC), ("RAW mpeg4", RAW), ("OUT h264", OUT)]:
    im = G.lire(p, FR)
    if im is None:
        print("%-12s ILLISIBLE" % lab)
        continue
    print("%-12s %9.2f %9.2f %9.2f %9.2f | %9.2f %9.2f %9.2f" %
          (lab, lap(im), lap(im, bv), lap(im, bb), lap(im, fond),
           mad(src, im), mad(src, im, bv), mad(src, im, fond)))
def rt512(im, n=512):
    h, w = im.shape[:2]
    return cv2.resize(cv2.resize(im, (n, n)), (w, h))


print()
print("=== TEST DECISIF : la sortie est-elle un aller-retour 512 de la source ? ===")
r = rt512(src)
print("--- rayon de flou : resize->512->1920 applique a la SOURCE")
print("    lap_full %.2f (source %.2f, soit %.1f%%) | lap_visage %.2f | lap_fond %.2f"
      % (lap(r), lap(src), lap(r) / lap(src) * 100, lap(r, bv), lap(r, fond)))
for lab, p in [("RAW mpeg4", RAW), ("OUT h264", OUT)]:
    im = G.lire(p, FR)
    if im is None:
        continue
    print("--- %s" % lab)
    print("    mad(aller-retour512, sortie) : fond %6.2f | visage %6.2f | plein %6.2f"
          % (mad(r, im, fond), mad(r, im, bv), mad(r, im)))
    print("    mad(source          , sortie) : fond %6.2f | visage %6.2f | plein %6.2f"
          % (mad(src, im, fond), mad(src, im, bv), mad(src, im)))

print()
print("--- meme mesure sur la frame 60 (debut) et 245 (fin) pour SOURCE vs OUT ---")
for fr in (60, 245):
    s = G.lire(G.SRC, fr)
    o = G.lire(OUT, fr)
    if s is None or o is None:
        print(" frame %d illisible" % fr)
        continue
    ff = G.plus_grand(app.get(s))
    bx = [int(v) for v in ff.bbox]
    print("frame %3d  lap_full  src %8.2f -> out %8.2f | lap_visage src %8.2f -> out %8.2f | mad_full %6.2f | mad_visage %6.2f"
          % (fr, lap(s), lap(o), lap(s, bx), lap(o, bx), mad(s, o), mad(s, o, bx)))
