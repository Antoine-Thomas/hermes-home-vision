#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Etape 4 : le fond residuel (mad 2,43 / lap_FOND 4,5 contre 6,8 en source) vient-il
de l'encodage final h264 a 2,6 Mbit/s, ou du blending ?

Methode : on encode le MEME clip source (10 s, sans audio) avec les reglages exacts du mux
de inference.py (-strict -2 -q:v 1) puis avec un reglage haute qualite (-crf 10), et on
mesure le fond et le visage comme pour A et B.
"""
import subprocess
import numpy as np
import cv2
import _greffe_hf as G

FR = 150
REPO = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\video-retalking"
SRC10 = REPO + r"\_test_vr_src.mp4"
ENC1 = REPO + r"\_enc_qv1.mp4"
ENC2 = REPO + r"\_enc_crf10.mp4"


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


print("encodage du clip source avec les reglages du mux (-strict -2 -q:v 1)...")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", SRC10, "-strict", "-2", "-q:v", "1", ENC1], check=True)
print("encodage haute qualite (-crf 10)...")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", SRC10, "-c:v", "libx264", "-crf", "10",
                "-preset", "medium", ENC2], check=True)
for f in (ENC1, ENC2):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=size,bit_rate",
                        "-of", "csv=p=0", f], capture_output=True, text=True)
    print("  %s %s" % (f.split(chr(92))[-1], r.stdout.strip()))

app = G.app_face(True)
src = G.lire(G.SRC, FR)
f = G.plus_grand(app.get(src))
x1, y1, x2, y2 = [int(v) for v in f.bbox]
bv = (x1, y1, x2, y2)
bb = G.fenetre_levres(f.bbox)
fond = (max(0, x1 - 250), y1, max(0, x1 - 30), y2)

cas = [("SOURCE", src),
       ("SOURCE encode qv1", G.lire(ENC1, FR)),
       ("SOURCE encode crf10", G.lire(ENC2, FR)),
       ("VR TEST A", G.lire(REPO + r"\results\test_A.mp4", FR)),
       ("VR TEST B", G.lire(REPO + r"\results\test_B.mp4", FR))]

print()
print("%-20s %10s %10s %10s | %8s %8s %8s | %8s" %
      ("cas", "lap_visage", "lap_bouche", "lap_FOND", "mad_vis", "mad_bouch", "mad_FOND", "PSNR512"))
sv = None
for lab, im in cas:
    if im is None:
        print("%-20s ILLISIBLE" % lab)
        continue
    vals = (lap(im, bv), lap(im, bb), lap(im, fond))
    mads = (np.abs(src.astype(np.float32) - im.astype(np.float32))[y1:y2, x1:x2].mean(),
            np.abs(src.astype(np.float32) - im.astype(np.float32))[bb[1]:bb[3], bb[0]:bb[2]].mean(),
            np.abs(src.astype(np.float32) - im.astype(np.float32))[fond[1]:fond[3], fond[0]:fond[2]].mean())
    if sv is None:
        sv = vals
    print("%-20s %10.1f %10.1f %10.1f | %8.2f %8.2f %8.2f | %8.1f" %
          (lab, vals[0], vals[1], vals[2], mads[0], mads[1], mads[2], psnr(im, rt(im))))
print()
print("=> si « SOURCE encode qv1 » a le meme lap_FOND (~4,5) et le meme mad_FOND (~2,4) que A/B,")
print("   alors le fond residuel est du seul fait de l'encodage final, et le compositing est corrige.")
