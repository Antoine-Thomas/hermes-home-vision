#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Controle OBJECTIF d'une capture de mail HTML (decodeur PNG stdlib, aucune dependance).

Usage :
    python check_render_png.py capture.png ["#fdc502:accent jaune" "#0c9f93:teal liens" ...]

Sans tokens fournis, la palette Searching Murphy est utilisee. Sortie : couleurs
dominantes, presence des tokens (exacte et a +-6 par canal), position des bandes sombres
(en-tete / pied de page), et test "rien n'est coupe" (le pixel du bas doit etre le fond de
page). A lancer apres la capture Chrome headless, en complement du controle statique du
HTML (voir SKILL.md, etapes 3 et 4).
"""
import sys, zlib, struct, collections

DEFAULT_TOKENS = [
    "#fdc502:accent jaune (--sm-accent)",
    "#0c9f93:teal liens (--sm-card-bg)",
    "#284543:dark teal bandeau/pied (--sm-border)",
    "#cbe8e8:light teal encart (--sm-bg)",
    "#1b1f22:texte",
]
BG = (238, 244, 244)   # fond de page attendu (#eef4f4) : adapter si le mail change de fond
DARK = (40, 69, 67)    # couleur des bandes sombres de reference (#284543)


def read_png(path):
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "pas un PNG"
    pos, idat, w, h, ct = 8, b"", None, None, None
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h = struct.unpack(">II", chunk[:8])
            ct = chunk[9]
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
        pos += 12 + ln
    raw = zlib.decompress(idat)
    ch = {2: 3, 6: 4, 0: 1}[ct]
    stride = w * ch
    out = bytearray(h * stride)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        f = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
        if f == 1:
            for i in range(ch, stride):
                line[i] = (line[i] + line[i - ch]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return w, h, ch, bytes(out)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def analyse(path, tokens):
    w, h, ch, px = read_png(path)
    def rgb(x, y):
        i = (y * w + x) * ch
        return px[i], px[i + 1], px[i + 2]
    counts = collections.Counter()
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            counts[rgb(x, y)] += 1
    tot = sum(counts.values())
    print("### %s — %dx%d px" % (path.replace("\\", "/").split("/")[-1], w, h))
    for c, n in counts.most_common(6):
        print("   dominant #%02x%02x%02x  %5.1f%%" % (c[0], c[1], c[2], 100.0 * n / tot))
    for spec in tokens:
        tok, _, label = spec.partition(":")
        t = hex_rgb(tok)
        exact = counts.get(t, 0)
        near = sum(v for k, v in counts.items() if all(abs(k[j] - t[j]) <= 6 for j in range(3)))
        print("   %s %-34s exact=%-6d proche=%-6d %.2f%%" % (tok, label, exact, near, 100.0 * near / tot))
    rows = [sum(1 for x in range(0, w, 5) if all(abs(rgb(x, y)[j] - DARK[j]) <= 8 for j in range(3)))
            for y in range(h)]
    bands, inb, start = [], False, 0
    for y, c in enumerate(rows):
        if c > (w / 5) * 0.5 and not inb:
            inb, start = True, y
        elif c <= (w / 5) * 0.5 and inb:
            inb = False
            bands.append((start, y))
    if inb:
        bands.append((start, h - 1))
    print("   bandes sombres (#%02x%02x%02x) : %s  -> attendu : une en haut (en-tete), une vers le bas (pied)"
          % (DARK[0], DARK[1], DARK[2], bands))
    last = rgb(w // 2, h - 1)
    ok = all(abs(last[j] - BG[j]) <= 14 for j in range(3))
    print("   pixel bas-centre #%02x%02x%02x -> %s" % (last[0], last[1], last[2],
          "fond de page : le mail n'est pas coupe" if ok else "encore du contenu : augmenter la hauteur de fenetre"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    analyse(sys.argv[1], sys.argv[2:] or DEFAULT_TOKENS)
