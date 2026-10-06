# -*- coding: utf-8 -*-
"""Audit d'un lot de panneaux PNG : dimensions, mode, transparence, taille, planche de controle.

Usage : python audit_panneaux.py <dossier> [motif] [fond_hex]
  dossier   : dossier des panneaux (defaut .)
  motif     : glob (defaut *.png ; les fichiers commencant par _ sont ignores)
  fond_hex  : couleur de fond de la planche (defaut #0e1422, charte sombre)

A lancer APRES le rendu : un lot qui n'a pas ete audite n'est pas livre.
"""
import glob
import hashlib
import os
import sys

from PIL import Image

CIBLE = (1920, 1080)


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    motif = sys.argv[2] if len(sys.argv) > 2 else "*.png"
    fond = sys.argv[3] if len(sys.argv) > 3 else "#0e1422"

    fs = sorted(f for f in glob.glob(os.path.join(d, motif))
                if not os.path.basename(f).startswith("_"))
    if not fs:
        print("AUCUN fichier pour %s dans %s" % (motif, d))
        return 1

    bg = tuple(int(fond.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    print("%-24s %-11s %-6s %-7s %-9s %s" % ("fichier", "taille_px", "mode", "alpha",
                                             "octets", "sha256[:16]"))
    anomalies = 0
    for f in fs:
        im = Image.open(f)
        a = im.getchannel("A") if im.mode == "RGBA" else None
        coin = a.getpixel((0, 0)) if a else "n/a"
        sha = hashlib.sha256(open(f, "rb").read()).hexdigest()[:16]
        print("%-24s %-11s %-6s %-7s %-9d %s" % (os.path.basename(f), "%dx%d" % im.size,
                                                 im.mode, coin, os.path.getsize(f), sha))
        if im.size != CIBLE or im.mode != "RGBA" or coin != 0:
            anomalies += 1
            print("   !! attendu %dx%d RGBA avec alpha du coin = 0" % CIBLE)

    # Planche de controle sur le fond REEL de la charte, pas sur du blanc.
    cw, ch, cols = 480, 270, 4
    lignes = (len(fs) + cols - 1) // cols
    sheet = Image.new("RGBA", (cw * cols, ch * lignes), bg)
    for i, f in enumerate(fs):
        case = Image.open(f).convert("RGBA").resize((cw, ch), Image.LANCZOS)
        sheet.alpha_composite(case, ((i % cols) * cw, (i // cols) * ch))
    out = os.path.join(d, "_planche_controle.png")
    sheet.convert("RGB").save(out)

    print("planche : %s %s" % (out, sheet.size))
    print("fichiers : %d | anomalies : %d" % (len(fs), anomalies))
    return 0


if __name__ == "__main__":
    sys.exit(main())
