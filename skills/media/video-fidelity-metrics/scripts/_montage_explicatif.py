#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Montage explicatif anime : SOURCE | LATENTSYNC A2.0 | VideoReTalking test B.

3 colonnes cote a cote (1920x720, 25 fps, 10 s), audio de LatentSync A2.0.
La variance du Laplacien de la zone BOUCHE est RECALCULEE A CHAQUE FRAME et
affichee en temps reel sous chaque colonne.

Methode de la zone bouche (identique au skill video-fidelity-metrics) :
visage detecte par insightface buffalo_l sur la SOURCE, bouche = landmarks
52-71, la MEME bbox est appliquee aux 3 videos (elles sont alignees au pixel :
MAD(source[i], vr_src[i]) = 0.000 verifie).

Aucun calcul GPU : la detection tourne sur CPUExecutionProvider (~0,46 s/frame,
resultat mis en cache dans _montage_bbox.npz).

Usage (python du venv LatentSync) :
  <venv>/Scripts/python.exe _montage_explicatif.py
  ... --n 250 --sortie F.mp4 --tmp D --sans-cache --garder-frames

Le script ecrit le montage demande. Rien d'autre.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

import cv2
import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
A = r"C:\Users\searc\Desktop\ANIMA"
SRC = os.path.join(A, "tetevideo_300s_alignee.mp4")
A20 = os.path.join(A, r"_work_2c\latentsync\ANIMA_tete_latentsync_hf_a20.mp4")
VRB = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\video-retalking\results\test_B.mp4"
ROOT = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\LatentSync\checkpoints\auxiliary"
SORTIE = os.path.join(A, "ANIMA_montage_VR_explicatif.mp4")

# --- geometrie (1920x720) ---------------------------------------------------
W, H = 1920, 720
COL = 640
H_TOP, H_TIT, H_VID, H_MES = 56, 40, 360, 100
Y_TIT = H_TOP                 #  56
Y_VID = Y_TIT + H_TIT         #  96
Y_MES = Y_VID + H_VID         # 456
Y_BAS = Y_MES + H_MES         # 556   (bandeau bas : 556 -> 719)

FPS = 25
CG = (30, 30, 30)             # gris des bandeaux plein cadre
BLANC, NOIR = (255, 255, 255), (10, 10, 10)
FOND_MES = (238, 238, 238)
COLS = [
    ("SOURCE",                 (105, 105, 105), "reference (100 %)"),
    ("LATENTSYNC A2.0 (67 %)", ( 60, 140,  60), "%s %% de la source"),
    ("VIDEO-RETALKING (8,5 %)", ( 45,  45, 185), "%s %% de la source"),
]
CAUSE_VR = "512 px + visage 256 px + GFPGAN"
LINE_BAS = [
    "VideoReTalking : compositing 512x512 + visage 256 px + lissage GFPGAN   |   "
    "LatentSync A2.0 : 1080p natif, 67 % de la source",
    "La variance du Laplacien de la zone bouche est recalculee a chaque frame "
    "(landmarks 52-71, insightface buffalo_l sur la SOURCE, meme bbox pour les 3 videos).",
    "PSNR d'invariance 512 : LatentSync 40,6-41,5 dB   |   VideoReTalking 46-51 dB, "
    "l'image VR ne contient plus rien au-dela de 512x512.",
]


# --------------------------------------------------------------- outils mesure
def lire(video, n):
    cap = cv2.VideoCapture(video)
    cap.set(cv2.CAP_PROP_POS_FRAMES, n)
    ok, fr = cap.read()
    cap.release()
    return fr if ok else None


def app_face():
    from insightface.app import FaceAnalysis
    a = FaceAnalysis(name="buffalo_l", root=ROOT, providers=["CPUExecutionProvider"])
    a.prepare(ctx_id=-1, det_size=(512, 512))
    return a


def plus_grand(faces):
    return max(faces, key=lambda z: (z.bbox[2] - z.bbox[0]) * (z.bbox[3] - z.bbox[1]))


def lapv(bgr, box):
    """Variance du Laplacien (CV_32F, image grise) dans `box`."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    x1, y1, x2, y2 = [int(v) for v in box]
    g = g[max(0, y1):y2, max(0, x1):x2]
    if g.size == 0:
        return 0.0
    return float(cv2.Laplacian(np.ascontiguousarray(g, np.uint8), cv2.CV_32F).var())


def _sig():
    st = os.stat(SRC)
    return (int(st.st_size), int(st.st_mtime))


def bboxes_source(n, cache, force=False):
    """Detecte la bbox du visage et celle de la bouche (52-71) sur les n frames de la SOURCE."""
    if not force and os.path.exists(cache):
        try:
            z = np.load(cache, allow_pickle=False)
            if int(z["n"]) == n and str(z["src"]) == SRC and tuple(z["sig"]) == _sig():
                return z["boxes"], z["bouches"], True
        except Exception:  # noqa: BLE001
            pass
    app = app_face()
    boxes = np.zeros((n, 4), np.int32)
    bouches = np.zeros((n, 4), np.int32)
    prev = None
    for i in range(n):
        f = None
        im = lire(SRC, i)
        if im is not None:
            fs = app.get(im)
            if fs:
                f = plus_grand(fs)
        if f is None:
            if prev is None:
                raise RuntimeError("aucun visage sur la frame %d de la source" % i)
            boxes[i], bouches[i] = prev
            continue
        x1, y1, x2, y2 = [int(v) for v in f.bbox]
        bl = f.landmark_2d_106[52:72]
        zx1, zy1 = [int(v) for v in bl.min(0)]
        zx2, zy2 = [int(v) for v in bl.max(0)]
        boxes[i] = (x1, y1, x2, y2)
        bouches[i] = (zx1, zy1, zx2, zy2)
        prev = (boxes[i], bouches[i])
    np.savez(cache, n=n, src=np.array(SRC), sig=np.array(_sig(), np.int64),
             boxes=boxes, bouches=bouches)
    return boxes, bouches, False


# ------------------------------------------------------------- outils dessin
def txt(img, s, x, y, scale, color, thick=2, max_w=None):
    """putText avec reduction automatique de l'echelle si le texte deborde."""
    if max_w:
        while scale > 0.25:
            (w, _), _ = cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
            if w <= max_w:
                break
            scale -= 0.02
    cv2.putText(img, s, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick,
                cv2.LINE_AA)


def paste_clip(dst, src, x, y):
    """Colle src a (x,y) en rognant ce qui deborde de dst (pas de redimensionnement)."""
    h, w = dst.shape[:2]
    sh, sw = src.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(w, x + sw), min(h, y + sh)
    if x1 <= x0 or y1 <= y0:
        return
    dst[y0:y1, x0:x1] = src[y0 - y:y1 - y, x0 - x:x1 - x]


def cadre(img, x1, y1, x2, y2, color, ep=2):
    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, ep)


# ------------------------------------------------------------------- montage
def compose(s_img, m_img, v_img, i, n, s_val, m_val, v_val, bbox_bouche):
    img = np.zeros((H, W, 3), np.uint8)
    img[:] = CG

    # bandeau haut (fixe + compteur de frame)
    txt(img, "VideoReTalking vs LatentSync alpha 2.0 vs Source", 16, 38, 0.85, BLANC, 2)
    lab = "frame %03d / %d" % (i + 1, n)
    (tw, _), _ = cv2.getTextSize(lab, cv2.FONT_HERSHEY_SIMPLEX, 0.85, 2)
    txt(img, lab, W - 16 - tw, 38, 0.85, BLANC, 2)


    imgs = [s_img, m_img, v_img]
    vals = [s_val, m_val, v_val]
    for k, (lab_col, coul, gabarit) in enumerate(COLS):
        x0 = k * COL
        # 1. bandeau de titre
        img[Y_TIT:Y_VID, x0:x0 + COL] = coul
        (tw, th), _ = cv2.getTextSize(lab_col, cv2.FONT_HERSHEY_SIMPLEX, 0.62, 2)
        txt(img, lab_col, x0 + (COL - tw) // 2, Y_TIT + (H_TIT + th) // 2, 0.62, BLANC, 2)
        # 2. image video 640x360
        img[Y_VID:Y_MES, x0:x0 + COL] = cv2.resize(imgs[k], (COL, H_VID),
                                                   interpolation=cv2.INTER_AREA)
        # 3. bandeau de mesures en temps reel
        img[Y_MES:Y_BAS, x0:x0 + COL] = FOND_MES
        txt(img, "Laplacien bouche : %8.1f" % vals[k], x0 + 12, Y_MES + 34, 0.66, NOIR, 2,
            max_w=COL - 24)
        if k == 0:
            sous = "zone bouche de reference"
        else:
            pct = (vals[k] / vals[0] * 100.0) if vals[0] > 0 else 0.0
            sous = "%.1f %% de la source" % pct
        txt(img, sous, x0 + 12, Y_MES + 64, 0.62, (60, 60, 60), 2, max_w=COL - 24)
        # 4. nom de la cause pour la colonne VideoReTalking
        if k == 2:
            txt(img, CAUSE_VR, x0 + 12, Y_MES + 92, 0.58, (150, 20, 20), 2, max_w=COL - 24)
        if k:
            cadre(img, x0 - 1, Y_TIT, x0 + 1, Y_BAS, (0, 0, 0), 2)

    # incrustation : zoom bouche x3 NEAREST en bas a droite de la colonne VR
    if bbox_bouche is not None and v_img is not None:
        bx = bbox_bouche
        z = v_img[bx[1]:bx[3], bx[0]:bx[2]]
        if z.size:
            f = min(3.0, (COL - 20.0) / z.shape[1], (H_VID - 20.0) / z.shape[0])
            z3 = cv2.resize(z, None, fx=f, fy=f, interpolation=cv2.INTER_NEAREST)
            zx = W - z3.shape[1] - 10
            zy = Y_MES - z3.shape[0] - 10
            paste_clip(img, z3, zx, zy)
            cadre(img, zx, zy, zx + z3.shape[1], zy + z3.shape[0], (0, 220, 255), 2)
            lab_z = "zoom bouche x%g NEAREST" % f
            (zw, zh), _ = cv2.getTextSize(lab_z, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 2)
            cv2.rectangle(img, (zx + 4, zy + 3), (zx + 14 + zw, zy + 14 + zh), (25, 25, 25), -1)
            txt(img, lab_z, zx + 9, zy + 28, 0.58, (0, 220, 255), 2)



    # bandeau bas (fixe)
    y = Y_BAS + 38
    for ligne in LINE_BAS:
        txt(img, ligne, 16, y, 0.62, (225, 225, 225), 2, max_w=W - 32)
        y += 40
    return img


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=250, help="nombre de frames (250 = 10 s a 25 fps)")
    ap.add_argument("--sortie", default=SORTIE)
    ap.add_argument("--tmp", default=os.path.join(ICI, "_montage_tmp"))
    ap.add_argument("--cache", default=os.path.join(ICI, "_montage_bbox.npz"))
    ap.add_argument("--sans-cache", action="store_true", help="refaire la detection des visages")
    ap.add_argument("--garder-frames", action="store_true")
    ap.add_argument("--crf", type=int, default=18)
    a = ap.parse_args(argv)

    for p in (SRC, A20, VRB):
        if not os.path.exists(p):
            print("MANQUANT : %s" % p)
            return 2

    n = a.n
    t0 = time.time()
    print("=== detection des visages sur la SOURCE (CPU, %d frames) ===" % n)
    boxes, bouches, cache_ok = bboxes_source(n, a.cache, a.sans_cache)
    print("    %s en %.1f s" % ("cache reutilise" if cache_ok else "detecte", time.time() - t0))

    if os.path.isdir(a.tmp):
        for f in os.listdir(a.tmp):
            os.remove(os.path.join(a.tmp, f))
    os.makedirs(a.tmp, exist_ok=True)

    capS, capM, capV = (cv2.VideoCapture(p) for p in (SRC, A20, VRB))
    nS = int(capS.get(cv2.CAP_PROP_FRAME_COUNT))
    nM = int(capM.get(cv2.CAP_PROP_FRAME_COUNT))
    nV = int(capV.get(cv2.CAP_PROP_FRAME_COUNT))
    print("=== frames disponibles : SOURCE %d | A2.0 %d | VR test B %d ===" % (nS, nM, nV))

    holds = {"VR": [], "A20": [], "SRC": []}
    ech = {}
    t0 = time.time()
    for i in range(n):
        okS, s = capS.read()
        okM, m = capM.read()
        okV, v = capV.read()
        if not okS:
            holds["SRC"].append(i)
            break
        if not okM:
            holds["A20"].append(i)
            m = m_last
        if not okV:
            holds["VR"].append(i)
            v = v_last
        m_last, v_last = m, v
        s_last = s

        bx = [int(z) for z in bouches[i]]
        s_val = lapv(s, bx)
        m_val = lapv(m, bx)
        v_val = lapv(v, bx)
        if i in (0, 150, n - 1):
            bbox_v = [int(z) for z in boxes[i]]
            ech[i] = {"source": round(s_val, 1), "latentsync": round(m_val, 1),
                      "vr_b": round(v_val, 1),
                      "pct_latentsync": round(m_val / s_val * 100, 1) if s_val else None,
                      "pct_vr_b": round(v_val / s_val * 100, 1) if s_val else None,
                      "bbox_visage": bbox_v, "bbox_bouche": bx}
        img = compose(s, m, v, i, n, s_val, m_val, v_val, bx)
        cv2.imwrite(os.path.join(a.tmp, "f_%04d.png" % (i + 1)), img)
        if (i + 1) % 25 == 0:
            print("    frame %d/%d  (%.0f s)" % (i + 1, n, time.time() - t0), flush=True)

    capS.release(); capM.release(); capV.release()
    print("=== frames composites ecrites dans %s (%.0f s) ===" % (a.tmp, time.time() - t0))

    cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
           "-i", os.path.join(a.tmp, "f_%04d.png"),
           "-i", A20,
           "-frames:v", str(n), "-t", "%.3f" % (n / FPS),
           "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "libx264", "-crf", str(a.crf), "-preset", "slow",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", a.sortie]
    print("=== assemblage ffmpeg ===")
    r = subprocess.run(cmd)
    if r.returncode:
        print("ffmpeg a echoue (%d)" % r.returncode)
        return 3

    if not a.garder_frames:
        shutil.rmtree(a.tmp, ignore_errors=True)

    # --- controle de la sortie
    def probe(args_):
        return subprocess.run(["ffprobe", "-v", "error"] + args_, capture_output=True,
                              text=True).stdout.strip()

    dur_v = probe(["-select_streams", "v:0", "-show_entries", "stream=duration,nb_frames,"
                   "width,height,r_frame_rate", "-of", "csv=p=0", a.sortie]).splitlines()
    dur_a = probe(["-select_streams", "a:0", "-show_entries", "stream=duration,codec_name,"
                   "sample_rate", "-of", "csv=p=0", a.sortie]).splitlines()
    poids = os.path.getsize(a.sortie)
    print()
    print("SORTIE   %s" % a.sortie)
    print("         %d octets" % poids)
    for l in dur_v:
        print("  video  %s" % l)
    for l in dur_a:
        print("  audio  %s" % l)
    if holds["VR"] or holds["A20"]:
        print("  NB : frames tenues (derniere image repetee) : %s" % holds)

    rap = os.path.splitext(a.sortie)[0] + "_mesures.json"
    with open(rap, "w", encoding="utf-8") as f:
        json.dump({"n": n, "fps": FPS, "frames_tenues": holds, "echantillons": ech,
                   "sources": {"source": SRC, "latentsync_a20": A20, "vr_test_b": VRB},
                   "sortie": a.sortie, "poids_octets": poids}, f, indent=1)
    print("  rapport  %s" % rap)
    print()
    print("ECHANTILLONS (Laplacien zone bouche) :")
    for i in sorted(ech):
        e = ech[i]
        print("  frame %3d (index %3d) : SOURCE %7.1f | A2.0 %7.1f (%s %%) | VR B %7.1f (%s %%)"
              % (i + 1, i, e["source"], e["latentsync"], e["pct_latentsync"],
                 e["vr_b"], e["pct_vr_b"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
