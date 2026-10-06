#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compte les pixels d'une couleur cible a une liste de timecodes.

Usage :
  python verif_popups_timecodes.py VIDEO HEX [TIMES] [TOL] [THR]
  python verif_popups_timecodes.py final.mp4 4cc9f0 15,45,60,225,290
  python verif_popups_timecodes.py final.mp4 0e1420 30,45,275,290 10 2000

Chaque ligne donne les pixels cibles, leur pourcentage de l'image et le verdict.

Pop-up : la cible est la BORDURE de la carte. Piege — un 0 sur un timecode en PLEIN fondu est
normal, la couleur de bordure y est melangee au fond. Ne pas lire ce 0 comme « panneau absent ».

Plein ecran : la cible est le FOND CHARTE, et c'est la FRACTION qui parle — > 30 % panneau plein
plein ecran, < 5 % sujet visible, entre les deux transition. Le seuil absolu par defaut (40 px)
est trop bas pour ce mode (la scene du sujet contient deja quelques % de sombre) : passer THR.

Echantillonnage 1 px sur 2 : le compteur vaut ~1/4 du compte reel.
"""
import os
import subprocess
import sys
import tempfile
from PIL import Image

DEFAULT_TIMES = [30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180,
                 195, 210, 225, 240, 255, 270, 285, 286, 290, 293]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    video = sys.argv[1]
    hexc = sys.argv[2].lstrip("#")
    times = ([float(x) for x in sys.argv[3].split(",")]
             if len(sys.argv) > 3 else DEFAULT_TIMES)
    tol = int(sys.argv[4]) if len(sys.argv) > 4 else 45
    thr = int(sys.argv[5]) if len(sys.argv) > 5 else 40
    target = tuple(int(hexc[i:i + 2], 16) for i in (0, 2, 4))
    tmp = os.path.join(tempfile.gettempdir(), "_verif_popup.png")
    print("video=%s  cible=#%s  tol=%d  seuil presence >%d px" % (video, hexc, tol, thr))
    print("%-9s %8s %7s  %s" % ("t(s)", "px", "%", "etat"))
    for t in times:
        subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-ss", str(t),
                        "-i", video, "-frames:v", "1", "-y", tmp], check=True)
        im = Image.open(tmp).convert("RGB")
        w, h = im.size
        px = im.load()
        n = 0
        for y in range(0, h, 2):
            for x in range(0, w, 2):
                p = px[x, y]
                if (abs(p[0] - target[0]) <= tol and abs(p[1] - target[1]) <= tol
                        and abs(p[2] - target[2]) <= tol):
                    n += 1
        tot = ((w + 1) // 2) * ((h + 1) // 2)
        print("%-9s %8d %6.1f%%  %s" % (t, n, 100.0 * n / tot,
              "present" if n > thr else "absent / en fondu"))
    try:
        os.remove(tmp)
    except OSError:
        pass
    return 0


sys.exit(main())
