# -*- coding: utf-8 -*-
"""Controle objectif d'un montage ANIMA (panneaux incrustes sur une tete parlante).

On croit les PIXELS, pas une relecture d'image : la vision se trompe a pleine echelle
(coins arrondis declares droits, marges declarees invisibles, artefacts inexistants).

Usage :
    python verif_pixels.py <livrable.mp4> <base.mp4> [--calques DOSSIER] [--captures DOSSIER]

Sorties :
  - tableau  t(s) | % fond charte | lecture
  - emprise reelle du panneau (diff avec la base au MEME instant)
  - ecart hors panneau (doit etre ~0 -> decor et personne intacts)
  - conformite au calque dans la boite du panneau
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

import numpy as np
from PIL import Image

# --- reglages du montage v7 (1600x900 centre en 160,90) ---
CARD_X, CARD_Y, CARD_W, CARD_H = 160, 90, 1600, 900
BG = np.array([14, 20, 32])            # #0e1420
SERIES = [(30.0, 42.0), (60.0, 72.0), (90.0, 102.0), (120.0, 132.0),
          (150.0, 162.0), (180.0, 192.0), (210.0, 222.0), (240.0, 252.0)]
CARD_SLOT = (286.0, None)              # jusqu'a la fin


def frame(video: str, t: float, out: str) -> np.ndarray:
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-ss", str(t),
                    "-i", video, "-frames:v", "1", "-y", out], check=True)
    return np.asarray(Image.open(out).convert("RGB")).astype(int)


def frac_bg(a: np.ndarray, tol: int = 8) -> float:
    return float((np.abs(a - BG).max(axis=2) <= tol).mean())


def footprint(cap: np.ndarray, base: np.ndarray, thr: int = 25):
    m = np.abs(cap - base).max(axis=2) > thr
    if m.sum() < 500:
        return None
    ys, xs = np.where(m)
    return xs.min(), xs.max(), ys.min(), ys.max()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("livrable")
    ap.add_argument("base")
    ap.add_argument("--calques", default=None)
    ap.add_argument("--captures", default=".")
    a = ap.parse_args()
    os.makedirs(a.captures, exist_ok=True)

    points = []
    for i, (t0, t1) in enumerate(SERIES, start=1):
        points.append((t0 + 6.0, "PANNEAU %02d" % i, i))      # mi-creneau
        points.append((t1 + 6.0, "respiration apres P%02d" % i, None))
    points.append((290.0, "carte de fin", "card"))

    print("%-8s %-11s %s" % ("t(s)", "% fond", "lecture"))
    for t, libelle, num in points:
        cap = frame(a.livrable, t, os.path.join(a.captures, "chk.png"))
        print("%-8s %-11.1f %s" % (t, 100 * frac_bg(cap), libelle))

    print("\n--- emprise du panneau et integrite du decor ---")
    for t in (36.0, 246.0):
        cap = frame(a.livrable, t, os.path.join(a.captures, "c.png"))
        base = frame(a.base, t, os.path.join(a.captures, "b.png"))
        fp = footprint(cap, base)
        print("  t=%-5s emprise x[%d..%d] y[%d..%d] -> %dx%d" % (t, *fp, fp[1] - fp[0] + 1, fp[3] - fp[2] + 1))
        m = np.ones(cap.shape[:2], bool)
        m[CARD_Y - 25:CARD_Y + CARD_H + 25, CARD_X - 25:CARD_X + CARD_W + 25] = False
        print("        hors panneau+ombre : %.2f/255 d'ecart (0,5-2 = decor intact)"
              % np.abs(cap[m] - base[m]).mean())

    if a.calques:
        print("\n--- conformite au calque (boite du panneau) ---")
        for cal in sorted(os.listdir(a.calques)):
            if cal.endswith(".png") and "_f" not in cal:
                num = int(cal.split("_")[1].split(".")[0]) if not cal.startswith("ov_card") else "card"
                if num == "card":
                    continue
                t = SERIES[int(num) - 1][0] + 6.0
                cap = frame(a.livrable, t, os.path.join(a.captures, "c.png"))
                lay = np.asarray(Image.open(os.path.join(a.calques, cal)).convert("RGBA")).astype(float)
                al = lay[:, :, 3:4] / 255.0
                b = frame(a.base, t, os.path.join(a.captures, "b.png"))
                box = (slice(CARD_Y, CARD_Y + CARD_H), slice(CARD_X, CARD_X + CARD_W))
                ref = b[box] * (1 - al[box]) + lay[box][:, :, :3] * al[box]
                print("  t=%-5s %-12s ecart %.2f/255 (attendu 1,5-2,5)"
                      % (t, cal, np.abs(ref - cap[box]).mean()))
    return 0


sys.exit(main())
