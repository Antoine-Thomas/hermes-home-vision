# -*- coding: utf-8 -*-
"""Assemblage final V6 (volet 4) : cotes nets + bouche nette.

Differences vs assemble_p1002837.py (version livree) :
  1. transfert passe-haut depuis la source 4K sur TOUTE l'image, plus seulement
     dans l'ellipse du visage : les cotes recuperent le detail 4K au lieu de
     rester sur l'upscale 720p (mesure : cotes a 38 % de la source avant).
  2. keep (part du transfert DANS les levres) reglable : 0,70 au lieu de 0,35.
     Mesure sur 30 s : x1,01 de l'energie haute frequence de la source sans
     fantome, contre 0,78x pour keep=0,35.
  3. source sans fondu enchaine (source_4k_25fps_clean.mp4) : supprime le flou
     de liaison qui revenait a chaque cycle de 8 s.

Chaine ffmpeg inchangee : unsharp 5:5:0,8, logo 280 px haut-droite (marge 40,
alpha 0,9), libx264 preset slow CRF 16, AAC 320k 48 kHz.

Usage :
    assemble_v6.py check                 -> mesures + apercus (pas de rendu)
    assemble_v6.py test [start] [count]  -> rendu court pour valider
    assemble_v6.py run                   -> rendu complet
"""
import os
import subprocess
import sys
import time

import cv2
import numpy as np
from insightface.app import FaceAnalysis

HERE = r"C:\Users\searc\Desktop\hermes_tuto_v4"
DATA = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\p1002837"
SEGDIR = os.environ.get("V4_SEGDIR") or os.path.join(HERE, "ls_segments_p1002837")
LS_OUT = os.environ.get("V4_LSOUT") or os.path.join(HERE, "latentsync_p1002837.mp4")
SRC4K = os.environ.get("V4_SRC4K") or os.path.join(DATA, "source_4k_25fps.mp4")
WAV = os.environ.get("V4_WAV") or os.path.join(HERE, "volet4_voice_v7.wav")
LOGO = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\hermes_logo_icon.png"
ROOT = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\LatentSync\checkpoints\auxiliary"
OUT = os.environ.get("V4_OUT") or os.path.join(HERE, "youtube_volet4_hermes_FINAL_v6.mp4")
PREV = os.path.join(os.environ["LOCALAPPDATA"], "Temp", "v4check", "v6")
os.makedirs(PREV, exist_ok=True)

SIGMA = 1.8
LAMBDA = 1.0
KEEP = float(os.environ.get("V4_KEEP") or 0.70)
# Accentuation locale du CONTOUR des levres (0 = desactivee).
# Le contour est regenere par LatentSync en 720p donc mou ; le transfert HP du 4K ne le
# redresse pas (l'edge source peut tomber a 1-2 px de celui du rendu, les deux se
# compensent partiellement). Un unsharp local, petit rayon, accentue le contour LA OU IL EST.
LIP_SHARP = float(os.environ.get("V4_LIPSHARP") or 0.0)
LIP_SIGMA = float(os.environ.get("V4_LIPSIGMA") or 1.2)
# Variante "contour seulement" : le gain suit le gradient (maximal sur un contour net,
# nul dans les zones plates et sur les pics isoles). Evite d'engraisser la texture.
LIP_EDGE = float(os.environ.get("V4_LIPEDGE") or 0.0)
# Recadrage local des levres : la bouche generee par LatentSync et la bouche de la source
# sont a 1-3 px pres. Transferer le passe-haut de la source sans recaler fait s'annuler
# partiellement les deux contours (bord "mal defini"). On cherche donc, frame par frame,
# le decalage (dx,dy) qui superpose au mieux les CONTOURS de la source sur ceux du rendu,
# et c'est la source recalee qui fournit le passe-haut des levres.
LIP_ALIGN = int(os.environ.get("V4_LIPALIGN") or 0)
LIP_ALIGN_MAX = 3
LIP_FEATHER = 26          # px de fondu du patch pour eviter une couture visible
W, H = 1920, 1080

LOGO_W = 280
LOGO_M = 40
LOGO_A = 0.90
PRESET = "slow"
CRF = "16"

app = FaceAnalysis(name="buffalo_l", root=ROOT)
app.prepare(ctx_id=-1, det_size=(640, 640))


def lap(i):
    g = cv2.cvtColor(i.astype(np.uint8), cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(g, cv2.CV_32F).var())


def segment_bounds():
    out, cum = [], 0
    for f in sorted(os.listdir(SEGDIR)):
        if not (f.startswith("out_") and f.endswith(".mp4")):
            continue
        p = os.path.join(SEGDIR, f)
        n = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=nb_frames", "-of", "csv=p=0", p],
                           capture_output=True, text=True).stdout.strip()
        n = int(n) if n.isdigit() else 0
        out.append((p, cum, n))
        cum += n
    return out, cum


BOUNDS, N_TOT = segment_bounds()


def src_index(i, n_src):
    for _, start, n in BOUNDS:
        if start <= i < start + n:
            i -= start
            break
    j = i % (2 * n_src)
    k = j % n_src
    return k if (j // n_src) % 2 == 0 else n_src - 1 - k


def load_src1080():
    cap = cv2.VideoCapture(SRC4K)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA))
    cap.release()
    return out


def face_box(cap, n_out):
    boxes = []
    for f in (0.05, 0.2, 0.4, 0.6, 0.8, 0.95):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(f * (n_out - 1)))
        ok, fr = cap.read()
        if not ok:
            continue
        fs = app.get(cv2.resize(fr, (W, H), interpolation=cv2.INTER_LANCZOS4)
                     if fr.shape[1] != W else fr)
        if fs:
            boxes.append(max(fs, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1])).bbox)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    if not boxes:
        sys.exit("aucun visage detecte")
    return np.median(np.array(boxes, dtype=float), axis=0)


def weight_map(bbox1080):
    """Poids du transfert HP, pleine image : 1 partout, KEEP dans les levres."""
    x1, y1, x2, y2 = bbox1080
    fw, fh = x2 - x1, y2 - y1
    lip_cx, lip_cy = (x1 + x2) / 2.0, y1 + fh * 0.72
    lip_rx, lip_ry = fw * 0.21, fh * 0.11
    yy, xx = np.mgrid[0:H, 0:W]
    w_lip = np.clip(((xx - lip_cx) / lip_rx) ** 2 + ((yy - lip_cy) / lip_ry) ** 2, 0, 1)
    m = (KEEP + (1.0 - KEEP) * w_lip).astype(np.float32)
    print("visage 1080p : x %.0f..%.0f y %.0f..%.0f | levres cx %.0f cy %.0f rx %.0f ry %.0f | keep %.2f"
          % (x1, x2, y1, y2, lip_cx, lip_cy, lip_rx, lip_ry, KEEP), flush=True)
    return m, (lip_cx, lip_cy, lip_rx, lip_ry)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"

    cap = cv2.VideoCapture(LS_OUT)
    n_out = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print("LatentSync : %dx%d, %d frames | segments %d (%d frames)"
          % (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
             n_out, len(BOUNDS), N_TOT), flush=True)

    bbox = face_box(cap, n_out)
    src = load_src1080()
    n_src = len(src)
    print("source 4K : %d frames (%.2f s)" % (n_src, n_src / 25.0), flush=True)

    wmap, lips = weight_map(bbox)
    hp = []
    for s in src:
        c = s.astype(np.float32)
        hp.append(((c - cv2.GaussianBlur(c, (0, 0), SIGMA)) * wmap[..., None]).astype(np.float16))
    print("HP pleine image : %d frames, %.2f Go (float16)" % (len(hp), sum(a.nbytes for a in hp) / 1024.0 ** 3), flush=True)

    lx, ly, lrx, lry = [int(v) for v in lips]
    lip_roi = (max(0, lx - lrx), max(0, ly - lry), min(W, lx + lrx), min(H, ly + lry))

    # patch d'accentuation locale du contour des levres (options V4_LIPSHARP / V4_LIPEDGE)
    lip_patch = None
    if LIP_SHARP > 0 or LIP_EDGE > 0:
        ex, ey = lrx * 1.35, lry * 1.55
        x1, y1 = int(max(0, lx - ex - LIP_FEATHER)), int(max(0, ly - ey - LIP_FEATHER))
        x2, y2 = int(min(W, lx + ex + LIP_FEATHER)), int(min(H, ly + ey + LIP_FEATHER))
        yy, xx = np.mgrid[y1:y2, x1:x2]
        d = np.sqrt(np.maximum(((xx - lx) / ex) ** 2 + ((yy - ly) / ey) ** 2, 0.0))
        blend = np.clip(1.0 - (d - 0.85) / 0.45, 0, 1).astype(np.float32)
        lip_patch = (x1, y1, x2, y2, blend)
        print("accentuation locale des levres : gain %.2f (sigma %.2f), gain de contour %.2f | patch %dx%d"
              % (LIP_SHARP, LIP_SIGMA, LIP_EDGE, x2 - x1, y2 - y1), flush=True)

    # --- recadrage local des levres (option V4_LIPALIGN) ---
    lip_align = None
    if LIP_ALIGN:
        P = LIP_ALIGN_MAX
        ax1, ay1 = max(0, lip_roi[0] - P), max(0, lip_roi[1] - P)
        ax2, ay2 = min(W, lip_roi[2] + P), min(H, lip_roi[3] + P)
        # le patch de reference doit rester dans les bornes : on decale le point de depart
        ax1, ay1 = max(ax1, P), max(ay1, P)
        ax2, ay2 = min(ax2, W - P), min(ay2, H - P)
        bx1, by1, bx2, by2 = ax1, ay1, ax2, ay2          # patch centre (hors marge)
        patches, grads = [], []
        for s in src:
            patch = s[ay1 - P:ay2 + P, ax1 - P:ax2 + P].copy()
            g = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY).astype(np.float32)
            gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
            patches.append(patch)
            grads.append(cv2.GaussianBlur(np.sqrt(gx * gx + gy * gy), (0, 0), 1.5))
        h, w = by2 - by1, bx2 - bx1
        wsub = wmap[by1:by2, bx1:bx2]
        print("recadrage des levres : patch %dx%d, recherche +/-%d px (w lip = %.2f..%.2f)"
              % (w, h, LIP_ALIGN_MAX, float(wsub.min()), float(wsub.max())), flush=True)
        lip_align = (ax1, ay1, by1, bx1, h, w, P, patches, grads, wsub)

    shifts = {"n": 0, "sum": np.zeros(2, dtype=float)}

    def frame_out(i, fr):
        j = src_index(i, n_src)
        base = cv2.resize(fr, (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
        if lip_align is not None:
            ax1, ay1, by1, bx1, h, w, P, patches, grads, wsub = lip_align
            # le recalage se fait sur la bouche GENREE par LatentSync (avant tout passe-haut),
            # sinon le gradient de la source deja ajoute biaise la recherche vers (0,0)
            center = base[by1:by1 + h, bx1:bx1 + w]
            g = cv2.cvtColor(center.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
            gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
            gr = cv2.GaussianBlur(np.sqrt(gx * gx + gy * gy), (0, 0), 1.5)
            best, bd = (0, 0), None
            for dy in range(-P, P + 1):
                for dx in range(-P, P + 1):
                    sub = grads[j][P + dy:P + dy + h, P + dx:P + dx + w]
                    d = float(np.mean(np.abs(sub - gr)))
                    if bd is None or d < bd:
                        bd, best = d, (dx, dy)
            dx, dy = best
            shifts["n"] += 1
            shifts["sum"] += (dx, dy)
            b = np.clip(base + LAMBDA * hp[j].astype(np.float32), 0, 255)
            ps = patches[j][P + dy:P + dy + h, P + dx:P + dx + w].astype(np.float32)
            pc = patches[j][P:P + h, P:P + w].astype(np.float32)
            hp_s = ps - cv2.GaussianBlur(ps, (0, 0), SIGMA)
            hp_c = pc - cv2.GaussianBlur(pc, (0, 0), SIGMA)
            b[by1:by1 + h, bx1:bx1 + w] += LAMBDA * (hp_s - hp_c) * wsub[..., None]
        else:
            b = np.clip(base + LAMBDA * hp[j].astype(np.float32), 0, 255)
        if lip_patch is not None:
            x1, y1, x2, y2, blend = lip_patch
            p = b[y1:y2, x1:x2]
            w3 = blend[..., None]
            if LIP_SHARP > 0:
                sh = p + LIP_SHARP * (p - cv2.GaussianBlur(p, (0, 0), LIP_SIGMA))
                b[y1:y2, x1:x2] = p * (1.0 - w3) + sh * w3
                p = b[y1:y2, x1:x2]
            if LIP_EDGE > 0:
                g = cv2.cvtColor(p.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
                gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
                gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
                mag = cv2.GaussianBlur(np.sqrt(gx * gx + gy * gy), (0, 0), 1.5)
                m0 = 0.55 * float(np.percentile(mag, 99))       # centre sur les contours nets
                wgt = np.exp(-((mag - m0) / (0.55 * m0 + 1e-6)) ** 2)
                sh = p + (LIP_EDGE * wgt)[..., None] * (p - cv2.GaussianBlur(p, (0, 0), LIP_SIGMA))
                b[y1:y2, x1:x2] = p * (1.0 - w3) + sh * w3
        return np.clip(b, 0, 255).astype(np.uint8)

    if mode == "check":
        for t in (30, 100, 200):
            cap.set(cv2.CAP_PROP_POS_FRAMES, t * 25)
            ok, fr = cap.read()
            if not ok:
                continue
            b = cv2.resize(fr, (W, H), interpolation=cv2.INTER_LANCZOS4)
            b2 = frame_out(t * 25, fr)
            src1080 = src[src_index(t * 25, n_src)]
            for name, img in (("ls", b), ("v6", b2), ("src", src1080)):
                cv2.imwrite(os.path.join(PREV, "%s_%d.png" % (name, t)), img)
            print("t=%ds : cote gauche LS %.1f -> v6 %.1f (source %.1f) | levres LS %.1f -> v6 %.1f (source %.1f)"
                  % (t, lap(b[0:H, 0:600]), lap(b2[0:H, 0:600]), lap(src1080[0:H, 0:600]),
                     lap(b[lip_roi[1]:lip_roi[3], lip_roi[0]:lip_roi[2]]),
                     lap(b2[lip_roi[1]:lip_roi[3], lip_roi[0]:lip_roi[2]]),
                     lap(src1080[lip_roi[1]:lip_roi[3], lip_roi[0]:lip_roi[2]])), flush=True)
        print("apercus ->", PREV, flush=True)
        return

    if mode == "test":
        start = int(sys.argv[2]) if len(sys.argv) > 2 else 2250
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 500
        tag = os.environ.get("V4_TAG") or "%d" % start
        out = os.path.join(HERE, "variantes", "v6_test_%s.mp4" % tag)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        dur = count / 25.0
    else:
        start, count = 0, n_out
        out = OUT
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                    "-of", "csv=p=0", WAV], capture_output=True, text=True).stdout.strip())

    fc = ("[0:v]unsharp=5:5:0.8:5:5:0[sh];[1:v]scale=%d:-1[lg];"
          "[lg]format=yuva420p,colorchannelmixer=aa=%.2f[la];"
          "[sh][la]overlay=W-w-%d:%d[v]" % (LOGO_W, LOGO_A, LOGO_M, LOGO_M))
    cmd = ["ffmpeg", "-y", "-v", "error",
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "%dx%d" % (W, H), "-r", "25", "-i", "pipe:0",
           "-loop", "1", "-i", LOGO, "-i", WAV,
           "-filter_complex", fc, "-map", "[v]", "-map", "2:a",
           "-c:v", "libx264", "-preset", PRESET, "-crf", CRF, "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
           "-t", "%.3f" % dur, "-shortest", out]
    print("rendu -> %s (frames %d..%d, %.1f s)" % (out, start, start + count - 1, dur), flush=True)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    t0 = time.time()
    k = 0
    while k < count:
        ok, fr = cap.read()
        if not ok:
            break
        try:
            proc.stdin.write(frame_out(start + k, fr).tobytes())
        except BrokenPipeError:
            print("ffmpeg a atteint -t : arret de l'envoi a la frame %d" % (start + k), flush=True)
            break
        k += 1
        if k % 250 == 0:
            el = time.time() - t0
            print("%5d/%d (%.0fs, %.1f img/s)" % (k, count, el, k / el), flush=True)
    cap.release()
    if lip_align is not None and shifts["n"]:
        print("recadrage des levres : decalage moyen dx %.2f dy %.2f sur %d frames"
              % (shifts["sum"][0] / shifts["n"], shifts["sum"][1] / shifts["n"], shifts["n"]), flush=True)
    try:
        proc.stdin.close()
    except BrokenPipeError:
        pass
    proc.wait()
    print("TERMINE : %s en %.0fs" % (out, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
