#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Panneaux PNG -> calques plein ecran 1920x1080 OPAQUES, contenu centre.

Usage :
  python plein_ecran_94.py SRC_DIR OUT_DIR [MOTIF] [FOND_HEX] [FILL] [WxH]

  python plein_ecran_94.py schemas_v2 calques "panneau_*.png" 0e1420 0.94 1920x1080

Par fichier : recadrage sur la boite englobante du canal alpha, mise a l'echelle a ratio conserve
pour tenir dans FILL de la dimension contraignante, centrage, aplatissement sur un fond opaque de
charte. Le nom de sortie est celui de la source.

Regles portees par ce script (elles ne sont pas des options) :
  - ne JAMAIS etirer pour remplir les deux axes : la deformation est refusee, la marge sombre
    haut/bas sert de cadre. Un contenu large ne remplit donc que ~80 % de la SURFACE, c'est attendu
    et ca se chiffre dans le rapport ;
  - le facteur doit rester <= 1 : rendre la source en SURRÉSOLU (meme figure, dpi x1,5) puis
    reduire. Un agrandissement depuis 1920x1080 rend le texte mou — le script compte les fichiers
    agrandis et le signale en fin de course.

Le fond opaque sous le schema est obligatoire : la charte est en texte blanc, un schema transparent
pose sur une video a fond clair est illisible.
"""
import glob
import os
import sys

from PIL import Image


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src, out = sys.argv[1], sys.argv[2]
    motif = sys.argv[3] if len(sys.argv) > 3 else "*.png"
    fond = (sys.argv[4] if len(sys.argv) > 4 else "0e1420").lstrip("#")
    fill = float(sys.argv[5]) if len(sys.argv) > 5 else 0.94
    w, h = (int(v) for v in (sys.argv[6] if len(sys.argv) > 6 else "1920x1080").lower().split("x"))
    bg = tuple(int(fond[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    os.makedirs(out, exist_ok=True)

    files = sorted(glob.glob(os.path.join(src, motif)))
    print("source=%s  sortie=%s (%dx%d, fill=%.2f, fond=#%s)  %d fichier(s)"
          % (src, out, w, h, fill, fond, len(files)))
    print("%-24s %-14s %-14s %s" % ("fichier", "contenu", "rendu", "facteur"))
    agrandis = 0
    for f in files:
        im = Image.open(f).convert("RGBA")
        bb = im.getchannel("A").getbbox()
        content = im.crop(bb) if bb else im
        cw, ch = content.size
        s = min(fill * w / cw, fill * h / ch)
        if s > 1.0:
            agrandis += 1
        nw, nh = max(1, int(round(cw * s))), max(1, int(round(ch * s)))
        content = content.resize((nw, nh), Image.LANCZOS)
        canvas = Image.new("RGBA", (w, h), bg)
        canvas.alpha_composite(content, ((w - nw) // 2, (h - nh) // 2))
        canvas.save(os.path.join(out, os.path.basename(f)))
        print("%-24s %-14s %-14s x%.2f" % (os.path.basename(f), "%dx%d" % (cw, ch),
                                           "%dx%d" % (nw, nh), s))
    print("%d agrandi(s) sur %d : une source trop petite doit etre RENDUE en surresolu, "
          "pas agrandie apres coup." % (agrandis, len(files)))
    return 0


sys.exit(main())
