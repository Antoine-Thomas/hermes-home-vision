#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pipeline_talkinghead.py : orchestrateur talking-head d'un volet, du rush au livrable.

PORTE D'ENTREE UNIQUE. Il enchaine les neuf etapes validees sur les volets 3, 4 et 5 :

  a) audit de la source (frames sans visage, stabilite, nettete, keyframes)
  b) choix de la meilleure fenetre (score composite nettete 0,40 / stabilite 0,25 /
     centrage 0,20 / mouvement 0,15, + 0,10 si la fenetre demarre sur une keyframe)
  c) extraction de la fenetre, SANS reencodage quand elle demarre sur une keyframe
  d) stabilisation verticale (recadrage dynamique + Savitzky-Golay 7,2 / k choisi, 0,65)
  e) boucle adaptee a la duree de l'audio (simple / segments optimises / ping-pong)
  f) LatentSync 1.5 (stage2.yaml 256 px, 25 pas, guidance 1.8, deepcache) via le moniteur
  g) greffe hautes frequences 4K (alpha, masque face, blur 5)
  h) mesures de nettete avant/apres (haut et bas du visage) + planche comparative
  i) rapport MD horodate + notification Telegram

PREREQUIS
  - video source (rush) et audio du clone (WAV 16 kHz mono ou MP3) ;
  - lancer avec le python du venv LatentSync : <racine>/venv/Scripts/python.exe.
    Si cv2 est absent, le script se relance tout seul avec ce venv.
  - ffmpeg et ffprobe dans le PATH.

DUREE
  Le cout est domine par l'etape f : ~149x le temps reel mesure sur le volet 5 (14 h 17 pour
  343,88 s de sortie, source 1080p, 8 Go de VRAM). Segmenter des la premiere minute de sortie
  (regles 41, 58 et 80 du skill talking-head-video-8gb).

EXEMPLES
  # 1. tout le pipeline, volet 6, en tache de fond a partir de l'etape LatentSync
  venv/Scripts/python.exe tests/pipeline_talkinghead.py \\
      --source "C:/Users/searc/Desktop/hermes tuto/psychopompe7.mp4" \\
      --audio  "C:/Users/searc/AppData/Local/hermes/data/xtts/audio_youtube_v6.wav" \\
      --volet 6 --depuis latentsync --detache

  # 2. verification avant de lancer (aucun calcul)
  python tests/pipeline_talkinghead.py --source rush.mp4 --audio voix.wav --volet 6 --plan

  # 3. reprendre apres une coupure (les etapes deja faites sont sautees)
  venv/Scripts/python.exe tests/pipeline_talkinghead.py --source rush.mp4 --audio voix.wav \\
      --volet 6 --depuis boucle

  # 4. ne faire tourner que les mesures sur une sortie existante
  venv/Scripts/python.exe tests/pipeline_talkinghead.py --source rush.mp4 --audio voix.wav \\
      --volet 6 --seulement mesures

SORTIES (toutes dans tests/v4_talking_head_<volet>/)
  audit_<v>_<label>.json, fenetre_<v>.json, source_<v>.mp4, reperes_<v>.json,
  stab_parametres_<v>.json, source_<v>_stab.mp4, mesures_boucles_<v>.json,
  source_<v>_loop.mp4, sortie_latentsync_<v>.mp4, sortie_latentsync_<v>_hf_a<alpha>.mp4,
  mesures_hf/mesures_hf.json, mesures_hf/planche_hf.png, RAPPORT_<v>.md

PIEGES DEJA PAYES (details dans le skill talking-head-video-8gb)
  - jamais de fondu enchainé sur la source destinee au ping-pong de LatentSync (regle 52) ;
  - un segment LatentSync = un multiple du cycle ping-pong, sinon la pose saute (regle 58) ;
  - le budget memoire de LatentSync se calcule en RAM systeme, pas en VRAM (regle 80) ;
  - texte Telegram sans chevron brut et sans parse_mode (regle 81).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

# --------------------------------------------------------------------------- #
# Constantes de la machine (identiques aux scripts valides des volets 3 a 5)
# --------------------------------------------------------------------------- #
RACINE = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\LatentSync"
TESTS = os.path.join(RACINE, "tests")
VENV_PY = os.path.join(RACINE, "venv", "Scripts", "python.exe")
AUDIT_JSON = os.path.join(TESTS, "audit_source.py")   # non utilise : audit natif ci-dessous
HF_TRANSFER = os.path.join(TESTS, "post_hf_transfer.py")
HF_RAPPORT = os.path.join(TESTS, "hf_rapport.py")
MONITEUR = os.path.join(TESTS, "surveiller_latentsync.py")
SEGMENTS = os.path.join(TESTS, "run_latentsync_segments.py")
ENV_HERMES = r"C:\Users\searc\AppData\Local\hermes\.env"
CHAT = "8956868107"

# Sous-processus : environnement sans les variables qui exposent le venv de l'agent Hermes.
# La tache cron Hermes (no_agent) execute ses scripts avec le venv de l'agent sur PYTHONPATH
# (python 3.11, numpy 2.4.3). Herite par les etapes du pipeline, ce chemin passe DEVANT
# site-packages et masque le numpy 1.26.4 du venv LatentSync (python 3.10) : la greffe HF
# echoue sur « No module named 'numpy._core._multiarray_umath' ». Constat volets 6 et 7.
POISON_ENV = ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP")
ENV_SOUS_PROC = {k: v for k, v in os.environ.items() if k not in POISON_ENV}

FPS_DEFAUT = 25.0
FRAMES_DEFAUT = 136          # 5,44 s a 25 fps (fenetre validee au volet 3)
FACTEUR_CROP = 0.90          # recadrage de stabilisation : 3456x1944 sur 3840x2160
MARGE_SECURITE = 8           # px de garde entre le cadrage et le bord de l'image

ETAPES = ["audit", "fenetre", "extraction", "stabilisation", "boucle",
          "latentsync", "hf", "mesures", "rapport"]


# --------------------------------------------------------------------------- #
# Utilitaires
# --------------------------------------------------------------------------- #
def dire(txt: str = "") -> None:
    print(txt, flush=True)


def titre(txt: str) -> None:
    dire("\n" + "=" * 78 + f"\n=== {txt}\n" + "=" * 78)


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    """Toujours depuis la racine du depot : post_hf_transfer.py ouvre ses modeles via le
    chemin RELATIF checkpoints/auxiliary, et rule 71 interdit de melanger cwd et chemins
    relatifs. Les chemins passes en argument sont absolus depuis main()."""
    kw.setdefault("cwd", RACINE)
    kw.setdefault("env", ENV_SOUS_PROC)   # sans le PYTHONPATH du cron Hermes (cf. POISON_ENV)
    dire("  $ " + " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def ffprobe_frames(chemin: str) -> int:
    r = sh(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", chemin])
    return int(r.stdout.strip() or 0)


def ffprobe_duree(chemin: str) -> float:
    r = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", chemin])
    return float(r.stdout.strip() or 0.0)


def ffprobe_taille(chemin: str) -> tuple[int, int, float]:
    r = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=width,height,r_frame_rate", "-of", "csv=p=0", chemin])
    w, h, ratio = r.stdout.strip().split(",")
    num, den = ratio.split("/")
    return int(w), int(h), float(num) / float(den)


def keyframes(chemin: str, fps: float) -> list[int]:
    """Indices des frames cles (regle 73 : decider la coupe sur le GOP, pas a l'aveugle).

    PIEGE ffprobe : `-show_entries frame=pts_time,key_frame` renvoie en realite
    `key_frame,pts_time` sur cette version (1,0.000000 puis 0,0.040000). On ne se fie donc
    pas a l'ordre demande : on identifie les deux champs par leur FORME (un entier 0/1 et un
    flottant). Verifie le 20/09/2026 sur l'ancien rush talkinghead.mp4 (keyframe unique a t=0).
    """
    r = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames",
            "-show_entries", "frame=pts_time,key_frame", "-of", "csv=p=0", chemin])
    out = []
    for i, ligne in enumerate(r.stdout.splitlines()):
        morceaux = [m.strip() for m in ligne.split(",") if m.strip()]
        cle, t = None, None
        for morceau in morceaux:
            if morceau in ("0", "1"):
                cle = int(morceau)
            else:
                try:
                    t = float(morceau)
                except ValueError:
                    pass
        if cle == 1:
            out.append(round(t * fps) if t is not None else i)
    return sorted(set(out))


def ram_libre() -> int:
    """RAM physique reellement disponible, en octets (0 si la mesure echoue)."""
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        m = MEMORYSTATUSEX()
        m.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return int(m.ullAvailPhys)
    except Exception:  # noqa: BLE001
        return 0


def charger(p: str) -> dict:
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def taille_tranche(a, cycle: int, w: int, h: int, libre: int) -> int:
    """Frames par tranche, arrondi au multiple SUPERIEUR du cycle de la boucle (regle 58).

    Un segment plus long coute de la RAM, un segment plus court casse la continuite de phase
    au raccord. 'auto' prend le plus grand multiple du cycle qui tient dans 60 % de la RAM
    libre : c'est le remede au mur du volet 5 (49,8 Go demandes pour 43,6 Go libres).
    """
    cycle = max(1, int(cycle))
    if a.segmenter == "auto":
        if not libre:
            brut = 1200          # RAM illisible : on retombe sur la valeur du volet 4 (48 s)
        else:
            brut = max(cycle, int(0.60 * libre / max(1, w * h * 3)))
        return max(cycle, (brut // cycle) * cycle)
    try:
        cible = int(a.segmenter)
    except (TypeError, ValueError):
        raise RuntimeError("--segmenter attend un nombre de frames ou 'auto'")
    if cible <= 0:
        raise RuntimeError("--segmenter attend un nombre de frames positif ou 'auto'")
    return max(cycle, (-(-cible // cycle)) * cycle)


def ecrire(p: str, obj) -> None:
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def jeton_telegram() -> str:
    try:
        with open(ENV_HERMES, encoding="utf-8", errors="replace") as f:
            for ligne in f:
                if ligne.startswith("TELEGRAM_BOT_TOKEN="):
                    return ligne.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def telegram(texte: str) -> bool:
    """Texte brut, sans parse_mode : un chevron dans une mesure ferait rejeter le message."""
    jeton = jeton_telegram()
    if not jeton:
        dire("[telegram] jeton absent, notification non envoyee")
        return False
    donnees = urllib.parse.urlencode({"chat_id": CHAT, "text": texte}).encode()
    try:
        with urllib.request.urlopen(
            f"https://api.telegram.org/bot{jeton}/sendMessage", data=donnees, timeout=30
        ) as r:
            dire(f"[telegram] HTTP {r.status}")
            return r.status == 200
    except Exception as e:  # noqa: BLE001
        dire(f"[telegram] echec : {e}")
        return False


def exiger(chemin: str, etape: str, commande: str) -> None:
    """Arrete net si l'entree d'une etape manque, en nommant l'etape qui la produit."""
    if not os.path.exists(chemin):
        raise SystemExit(f"entree manquante : {chemin}\n"
                         f"  elle est produite par l'etape {etape} : "
                         f"relancer avec --seulement {commande}")


def deja_fait(chemin: str, force: bool) -> bool:
    if os.path.exists(chemin) and not force:
        dire(f"  deja present, etape sautee : {chemin}")
        return True
    return False


# --------------------------------------------------------------------------- #
# a) Audit de la source : visage frame par frame, nettete, mouvement, keyframes
# --------------------------------------------------------------------------- #
def etape_audit(a) -> str:
    """Releve par frame (meme detection que LatentSync : insightface buffalo_l, 512 px)."""
    import cv2
    import insightface
    import numpy as np

    sortie = os.path.join(a.dossier, f"audit_{a.volet}_{a.label}.json")
    if deja_fait(sortie, a.force):
        return sortie

    titre(f"a) audit de la source — {os.path.basename(a.source)}")
    model = insightface.app.FaceAnalysis(
        name="buffalo_l", root=os.path.join(RACINE, "checkpoints", "auxiliary"),
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    model.prepare(ctx_id=0, det_size=(512, 512))

    cap = cv2.VideoCapture(a.source)
    if not cap.isOpened():
        raise FileNotFoundError(a.source)
    w, h, fps = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                 cap.get(cv2.CAP_PROP_FPS) or FPS_DEFAUT)
    frames, i, prec, t0 = [], 0, None, time.time()
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        faces = model.get(fr)
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        if not faces:
            frames.append({"i": i, "ok": False})
        else:
            f = max(faces, key=lambda z: z.det_score)
            x1, y1, x2, y2 = [float(v) for v in f.bbox]
            bw, bh = x2 - x1, y2 - y1
            mg = int(bh * 0.05)
            X1, Y1, X2 = max(0, int(x1 - mg)), max(0, int(y1 - mg)), int(x2 + mg)
            haut = g[Y1:Y1 + int(bh * 0.4), X1:X2]
            bas = g[int(y1 + bh * 0.55):int(y2), int(x1):int(x2)]
            zone = g[int(y1):int(y2), int(x1):int(x2)]
            mv = float(np.abs(zone.astype(np.float32) -
                              prec[int(y1):int(y2), int(x1):int(x2)].astype(np.float32)).mean()) \
                if prec is not None else 0.0
            frames.append({
                "i": i, "ok": True, "s": round(float(f.det_score), 4),
                "cx": round((x1 + x2) / 2.0, 1), "cy": round((y1 + y2) / 2.0, 1),
                "w": round(bw, 1), "h": round(bh, 1), "nb": len(faces),
                "nh": round(float(cv2.Laplacian(haut, cv2.CV_64F).var()), 1),
                "nb2": round(float(cv2.Laplacian(bas, cv2.CV_64F).var()), 1),
                "mv": round(mv, 3)})
        prec = g
        i += 1
        if i % 100 == 0:
            dire(f"  {i} frames  {time.time() - t0:.1f} s")
    cap.release()

    keys = keyframes(a.source, fps)
    pas = (keys[1] - keys[0]) if len(keys) > 1 else 0
    ok = np.array([f["ok"] for f in frames])
    c = lambda k: np.array([f.get(k, np.nan) for f in frames], dtype=float)
    resume = {
        "fichier": a.source, "label": a.label, "n": i, "w": w, "h": h, "fps": fps,
        "sans_visage": int((~ok).sum()),
        "nettete_haut": float(np.nanmean(c("nh"))), "nettete_bas": float(np.nanmean(c("nb2"))),
        "stab": float(np.sqrt(np.nanvar(c("cx")) + np.nanvar(c("cy")))),
        "stab_y": float(np.nanstd(c("cy"))), "h_visage": float(np.nanmean(c("h"))),
        "mouvement": float(np.nanmean(c("mv"))),
        "keyframes": {"n": len(keys), "pas": pas, "premieres": keys[:12]},
        "keyframes_regulier": bool(pas and len(keys) > 3
                                   and all(keys[j + 1] - keys[j] == pas for j in range(len(keys) - 1))),
    }
    ecrire(sortie, {"resume": resume, "frames": frames})
    dire(f"  {i} frames en {time.time() - t0:.1f} s | sans visage {resume['sans_visage']} | "
         f"nettete haut {resume['nettete_haut']:.1f} bas {resume['nettete_bas']:.1f} | "
         f"stab {resume['stab']:.1f} px | mouvement {resume['mouvement']:.3f}")
    dire(f"  keyframes : {len(keys)} (pas {pas} frames) "
         f"{'GOP regulier' if resume['keyframes_regulier'] else 'GOP irregulier ou keyframe unique'}")
    dire(f"-> {sortie}")
    return sortie


# --------------------------------------------------------------------------- #
# b) Choix de la meilleure fenetre (score composite normalise)
# --------------------------------------------------------------------------- #
def etape_fenetre(a, audit_json: str) -> str:
    import numpy as np

    sortie = os.path.join(a.dossier, f"fenetre_{a.volet}.json")
    if deja_fait(sortie, a.force):
        return sortie

    titre(f"b) choix de la fenetre de {a.frames} frames")
    d = charger(audit_json)
    fr, resume = d["frames"], d["resume"]
    fps, N = resume["fps"], a.frames
    keys = set(resume["keyframes"]["premieres"]) if resume["keyframes_regulier"] else None
    if keys is None:
        pas = resume["keyframes"]["pas"]
        keys = set(range(0, resume["n"], pas)) if pas else set()
    ok = np.array([f["ok"] for f in fr])
    c = lambda k: np.array([f.get(k, np.nan) for f in fr], dtype=float)

    cands = []
    for i in range(0, len(fr) - N + 1):
        if not ok[i:i + N].all():
            continue
        w_cx, w_cy = c("cx")[i:i + N], c("cy")[i:i + N]
        cands.append({
            "i": i, "t": round(i / fps, 2), "fin": round((i + N - 1) / fps, 2),
            "keyframe": i in keys,
            "stab": float(np.sqrt(np.var(w_cx) + np.var(w_cy))),
            "d_centre": float(np.sqrt((w_cx - resume["w"] / 2) ** 2 +
                                      (w_cy - resume["h"] / 2) ** 2).mean()),
            "nh": float(np.nanmean(c("nh")[i:i + N])),
            "nb2": float(np.nanmean(c("nb2")[i:i + N])),
            "mv": float(np.nanmean(c("mv")[i:i + N]))})
    if not cands:
        raise RuntimeError("aucune fenetre sans trou de visage : reduire --frames")

    norm = lambda v: (np.asarray(v, float) - min(v)) / (max(v) - min(v) + 1e-9)
    for cle in ("nh", "stab", "d_centre", "mv"):
        z = norm([k[cle] for k in cands])
        for k, zi in zip(cands, z):
            k["z_" + cle] = float(zi)
    for k in cands:
        # poids valides au volet 5 (regle 77) : la nettete, seule a varier du simple au
        # double, doit peser le plus ; le bonus keyframe evite un reencodage a l'etape c.
        k["composite"] = (0.40 * k["z_nh"] + 0.25 * (1 - k["z_stab"]) +
                          0.20 * (1 - k["z_d_centre"]) + 0.15 * (1 - k["z_mv"]) +
                          (0.10 if k["keyframe"] else 0.0))
    classement = sorted(cands, key=lambda x: -x["composite"])
    dire(f"  {len(cands)} fenetres candidates sans trou de visage")
    dire(f"  {'frame':>6} {'t':>6} {'key':>4} {'stab':>7} {'d_cent':>7} {'nett.haut':>10} {'mouv':>6} {'compo':>7}")
    for k in classement[:10]:
        dire(f"  {k['i']:>6} {k['t']:>6.2f} {'KEY' if k['keyframe'] else '   ':>4} "
             f"{k['stab']:>7.1f} {k['d_centre']:>7.0f} {k['nh']:>10.1f} {k['mv']:>6.2f} {k['composite']:>7.3f}")
    best = classement[0]
    ecrire(sortie, {"n_frames": N, "fenetre": best, "classement": classement[:20],
                    "source": audit_json})
    dire(f"  RETENU : frame {best['i']} (t={best['t']} -> {best['fin']} s)"
         f"{'  KEYFRAME : coupe sans reencodage' if best['keyframe'] else '  (pas de keyframe : reencodage)'}")
    dire(f"-> {sortie}")
    return sortie


# --------------------------------------------------------------------------- #
# c) Extraction de la fenetre
# --------------------------------------------------------------------------- #
def etape_extraction(a, fenetre_json: str) -> str:
    sortie = os.path.join(a.dossier, f"source_{a.volet}.mp4")
    if deja_fait(sortie, a.force):
        return sortie
    f = charger(fenetre_json)["fenetre"]
    N, fps = charger(fenetre_json)["n_frames"], FPS_DEFAUT
    titre(f"c) extraction de la fenetre (frame {f['i']}, {N} frames)")

    if f["keyframe"]:
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", str(f["t"]), "-i", a.source,
               "-frames:v", str(N), "-c", "copy", sortie]
        dire("  coupe sur keyframe : aucun reencodage")
    else:
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", str(f["t"]), "-i", a.source,
               "-frames:v", str(N), "-c:v", "libx264", "-crf", "14", "-preset", "slow",
               "-pix_fmt", "yuv420p", "-an", sortie]
        dire("  pas de keyframe au depart : reencodage crf 14 (ecart mesure < 0,75 niveau)")
    r = sh(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg : {r.stderr[-500:]}")

    n = ffprobe_frames(sortie)
    if n != N:
        raise RuntimeError(f"extraction : {n} frames au lieu de {N} "
                           "(regle 73 : le -ss n'est pas tombe juste)")
    w, h, _ = ffprobe_taille(sortie)
    dire(f"  {n} frames, {w}x{h} @ {fps} fps -> {sortie}")
    return sortie


# --------------------------------------------------------------------------- #
# d) Stabilisation verticale
# --------------------------------------------------------------------------- #
def _reperes(video: str, sortie_json: str, label: str) -> dict:
    """Serie par frame du centre des 4 reperes yeux+bouche (regle 78)."""
    import cv2
    import insightface
    import numpy as np

    model = insightface.app.FaceAnalysis(
        name="buffalo_l", root=os.path.join(RACINE, "checkpoints", "auxiliary"),
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    model.prepare(ctx_id=0, det_size=(512, 512))
    cap = cv2.VideoCapture(video)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or FPS_DEFAUT
    frames, i = [], -1
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        i += 1
        if i % 100 == 0:
            dire(f"  repere {i}")
        faces = model.get(fr)
        if not faces:
            frames.append({"i": i, "ok": False})
            continue
        f = max(faces, key=lambda d: (d.bbox[2] - d.bbox[0]) * (d.bbox[3] - d.bbox[1]))
        x1, y1, x2, y2 = [float(v) for v in f.bbox]
        kps = f.kps
        yeux = float((kps[0][1] + kps[1][1]) / 2.0)
        bouche = float((kps[3][1] + kps[4][1]) / 2.0)
        frames.append({"i": i, "ok": True, "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                       "centre_x": (x1 + x2) / 2.0, "centre_y": (y1 + y2) / 2.0,
                       "yeux_y": yeux, "bouche_y": bouche,
                       "centre_4pts_y": (yeux + bouche) / 2.0})
    cap.release()
    ecrire(sortie_json, {"label": label, "fichier": video, "w": w, "h": h, "fps": fps,
                         "frames": frames})
    return {"w": w, "h": h, "n": i + 1, "ok": sum(1 for f in frames if f.get("ok"))}


def _choisir_stab(reperes_json: str, sortie_json: str, facteur: float = FACTEUR_CROP) -> dict:
    """Filtre et taux de suivi : reduction ~65 %, cadrage < 20 px/frame (regle 78)."""
    import numpy as np
    from scipy.signal import savgol_filter

    R = charger(reperes_json)
    H = R["h"]
    y = np.array([f["centre_4pts_y"] for f in R["frames"] if f.get("ok")], dtype=float)
    crop_w, crop_h = int(R["w"] * facteur) // 2 * 2, int(H * facteur) // 2 * 2
    marge_y = (H - crop_h) // 2
    zoom = H / crop_h
    ref = y.std() * zoom

    def lp(v, sigma):
        k = int(max(2, 4 * sigma))
        x = np.arange(-k, k + 1)
        g = np.exp(-0.5 * (x / sigma) ** 2)
        g /= g.sum()
        return np.convolve(np.pad(v, k, mode="edge"), g, mode="valid")

    filtres = {"aucun": lambda: y.copy(), "savgol": lambda: savgol_filter(y, 7, 2),
               "gauss1": lambda: lp(y, 1.0), "gauss2": lambda: lp(y, 2.0)}
    dire(f"  piste brute E-T {y.std():.2f} px -> reference vue finale {ref:.2f} px (zoom {zoom:.4f})")
    dire(f"  {'filtre':>7} {'k':>5} {'E-T sortie':>11} {'reduction':>10} {'vit.med':>8} {'vit.max':>8} {'marge':>7}")
    lignes = []
    for nom, f in filtres.items():
        for k in (0.55, 0.60, 0.65, 0.70, 0.75):
            s = k * (f() - f().mean())
            if np.abs(s).max() > marge_y - MARGE_SECURITE:
                continue
            y_out = (y - s) * zoom
            red = 100 * (1 - y_out.std() / ref)
            vit_med, vit_max = float(np.median(np.abs(np.diff(s)))), float(np.abs(np.diff(s)).max())
            lignes.append({"filtre": nom, "k": k, "et": float(y_out.std()), "reduction": float(red),
                           "vit_med": vit_med, "vit_max": vit_max,
                           "saut_cadrage": float(abs(s[0] - s[-1])),
                           "saut_tete": float(abs(y_out[0] - y_out[-1]))})
            dire(f"  {nom:>7} {k:>5} {y_out.std():>11.2f} {red:>9.1f}% {vit_med:>8.2f} "
                 f"{vit_max:>8.2f} {np.abs(s).max():>7.1f}")
    # Savitzky-Golay impose (regle 78) ; on ne choisit que k : reduction la plus proche de 65 %
    # parmi les candidats a cadrage maitrise.
    ok = [l for l in lignes if l["filtre"] == "savgol" and l["vit_max"] <= 20]
    if not ok:
        ok = [l for l in lignes if l["vit_max"] <= 20] or lignes
    retenu = min(ok, key=lambda l: (abs(l["reduction"] - 65), l["vit_max"]))
    s = retenu["k"] * (savgol_filter(y, 7, 2) - savgol_filter(y, 7, 2).mean())
    ecrire(sortie_json, {"filtre": retenu["filtre"], "k": retenu["k"], "crop_w": crop_w,
                         "crop_h": crop_h, "marge_y": marge_y, "zoom": zoom,
                         "s": s.tolist(), "y": y.tolist(),
                         "reduction_pct": round(retenu["reduction"], 1),
                         "candidats": lignes})
    dire(f"  RETENU : filtre {retenu['filtre']}, k={retenu['k']} -> "
         f"-{retenu['reduction']:.1f} % (E-T {retenu['et']:.2f} px, vit. max {retenu['vit_max']:.2f} px/f)")
    return retenu


def _rendre_stab(video: str, params_json: str, sortie: str, h_cible: int) -> None:
    import cv2
    P = charger(params_json)
    crop_w, crop_h, marge_y, s = P["crop_w"], P["crop_h"], P["marge_y"], P["s"]
    src_w, src_h = int(P["crop_w"] / FACTEUR_CROP), int(P["crop_h"] / FACTEUR_CROP)
    x0 = (src_w - crop_w) // 2
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
         "-s", f"{src_w}x{src_h}", "-r", str(int(FPS_DEFAUT)), "-i", "-",
         "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-pix_fmt", "yuv420p", sortie],
        stdin=subprocess.PIPE)
    cap = cv2.VideoCapture(video)
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i >= len(s):
            raise RuntimeError(f"decalage manquant a la frame {i}")
        y0 = max(0, min(int(round(marge_y + s[i])), src_h - crop_h))
        crop = fr[y0:y0 + crop_h, x0:x0 + crop_w]
        if crop.shape[0] != crop_h or crop.shape[1] != crop_w:
            raise RuntimeError(f"frame {i} : recadrage {crop.shape} au lieu de ({crop_h}, {crop_w})")
        proc.stdin.write(cv2.resize(crop, (src_w, src_h),
                                    interpolation=cv2.INTER_LANCZOS4).tobytes())
        i += 1
    cap.release()
    proc.stdin.close()
    code = proc.wait()
    dire(f"  {i} frames recadrees, ffmpeg exit {code} -> {sortie}")


def etape_stabilisation(a, source_fenetre: str) -> tuple[str, str]:
    titre("d) stabilisation verticale (recadrage dynamique)")
    reperes = os.path.join(a.dossier, f"reperes_{a.volet}.json")
    params = os.path.join(a.dossier, f"stab_parametres_{a.volet}.json")
    sortie = os.path.join(a.dossier, f"source_{a.volet}_stab.mp4")
    exiger(source_fenetre, "c) extraction", "extraction")

    if deja_fait(sortie, a.force):
        return sortie, params
    if not os.path.exists(reperes) or a.force:
        info = _reperes(source_fenetre, reperes, f"source_{a.volet}")
        dire(f"  {info['ok']}/{info['n']} frames avec visage -> {reperes}")
    if not os.path.exists(params) or a.force:
        _choisir_stab(reperes, params)
    R = charger(reperes)
    dire(f"  cible : {R['w']}x{R['h']} -> recadrage {charger(params)['crop_w']}x"
         f"{charger(params)['crop_h']} remis a l'echelle (Lanczos)")
    _rendre_stab(source_fenetre, params, sortie, R["h"])

    # controle : le mouvement vertical doit baisser, la nettete du haut rester intacte
    import numpy as np
    y = np.array([f["centre_4pts_y"] for f in R["frames"] if f.get("ok")])
    P = charger(params)
    apres = (y - np.array(P["s"])) * P["zoom"]
    dire(f"  mouvement vertical : E-T {y.std():.2f} -> {apres.std():.2f} px "
         f"({100 * (1 - apres.std() / y.std()):.1f} % de reduction)")
    return sortie, params


# --------------------------------------------------------------------------- #
# e) Boucle adaptee a la duree de l'audio
# --------------------------------------------------------------------------- #
def _charger_gris(video: str, w: int, h: int):
    import cv2
    import numpy as np
    cap = cv2.VideoCapture(video)
    out = []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        out.append(cv2.cvtColor(cv2.resize(fr, (w, h), interpolation=cv2.INTER_AREA),
                                cv2.COLOR_BGR2GRAY))
    cap.release()
    return np.array(out, dtype=np.uint8)


def etape_boucle(a, source_stab: str, audio: str) -> str:
    """Boucle de la source jusqu'a la duree exacte de l'audio (regle 79)."""
    import numpy as np

    titre("e) boucle adaptee a la duree de l'audio")
    exiger(source_stab, "d) stabilisation", "stabilisation")
    duree_audio = ffprobe_duree(audio)
    n = ffprobe_frames(source_stab)
    duree_src = n / FPS_DEFAUT
    dire(f"  audio {duree_audio:.2f} s | source stabilisee {n} frames ({duree_src:.2f} s) "
         f"-> {duree_audio / duree_src:.1f} cycles")
    mesures = os.path.join(a.dossier, f"mesures_boucles_{a.volet}.json")
    sortie = os.path.join(a.dossier, f"source_{a.volet}_loop.mp4")
    if deja_fait(sortie, a.force):
        return sortie

    grand = _charger_gris(source_stab, 1920, 1080)
    petit = _charger_gris(source_stab, 480, 270).reshape(n, -1).astype(np.int16)
    # Matrice des couts de jonction, calculee UNE fois : sans elle, la descente locale
    # recompare des images entieres a chaque candidat (~160 000 comparaisons, plusieurs
    # minutes pour 136 frames de 4K). Ici : n boucles vectorisees sur les n frames.
    M = np.empty((n, n), dtype=np.float32)
    for i in range(n):
        M[i] = np.abs(petit - petit[i]).mean(axis=1)
    ecart = lambda i, j: float(np.abs(grand[i].astype(np.int16) - grand[j].astype(np.int16)).mean())
    naturel = float(np.mean([ecart(i, i + 1) for i in range(n - 1)]))
    dire(f"  reference : ecart moyen entre frames consecutives = {naturel:.2f} niveaux")

    # Strategie A (retenue par defaut, regle 79) : K segments de L frames dont les points
    # de coupe sont cherches la ou les frames se ressemblent.
    meilleur = None
    for K in (4, 5, 6, 7, 8):
        for L in sorted({int(n / K), int(n / K) + 6, 27, 33, 39}):
            if K * L > n or L < 10:
                continue
            starts = [int(round(i * (n - L) / (K - 1))) for i in range(K)]
            for _ in range(6):
                change = False
                for k in range(K):
                    best_c, best_s = None, starts[k]
                    for cand in range(0, n - L + 1):
                        if cand == starts[k] or any(abs(cand - starts[j]) < max(6, L // 3)
                                                    for j in range(K) if j != k):
                            continue
                        ss = list(starts)
                        ss[k] = cand
                        c = sum(M[ss[i] + L - 1, ss[(i + 1) % K]] for i in range(K))
                        if best_c is None or c < best_c:
                            best_c, best_s = c, cand
                    if best_s != starts[k]:
                        starts[k], change = best_s, True
                if not change:
                    break
            starts = sorted(starts)
            seams = [ecart(starts[i] + L - 1, starts[(i + 1) % K]) for i in range(K)]
            pire, moy = float(max(seams)), float(np.mean(seams))
            dire(f"  A K={K} L={L} cycle={K * L / FPS_DEFAUT:5.2f} s debuts={starts} "
                 f"pire={pire:5.2f} moyenne={moy:5.2f} ({moy / naturel:.2f}x ref)")
            cand = {"K": K, "L": L, "starts": [int(x) for x in starts],
                    "seams": [round(x, 2) for x in seams], "pire": round(pire, 2),
                    "moyenne": round(moy, 2), "ratio": round(moy / naturel, 2),
                    "cycle_s": round(K * L / FPS_DEFAUT, 2)}
            # Critere : la MOYENNE des jonctions (c'est elle qui defile 60 a 80 fois sur la
            # duree du volet : une moyenne a 1,04x la reference passe inapercue, une moyenne a
            # 2,24x se voit a chaque cycle), puis la pire en departage, puis le cycle le plus
            # long. Se classer sur la seule pire jonction retenait une variante tres coupee
            # (5 segments, moyenne 6,50) au detriment d'une variante a 8 segments dont 7
            # jonctions sur 8 sont invisibles (moyenne 3,03).
            rang = (round(moy, 3), round(pire, 3), -K * L)
            if meilleur is None or rang < meilleur["_rang"]:
                cand["_rang"] = rang
                meilleur = cand

    res = {"source": os.path.basename(source_stab), "n_frames": n,
           "ecart_consecutif": round(naturel, 2), "duree_audio": round(duree_audio, 3),
           "segments": {k: v for k, v in meilleur.items() if not k.startswith("_")}}
    # Ping-pong mesure pour memoire : raccord quasi parfait, mais le mouvement s'inverse
    # deux fois par cycle (la bouche repart en arriere) — ecarte pour un talking head.
    res["ping_pong"] = {"periode_s": round((2 * n - 2) / FPS_DEFAUT, 2),
                        "ecart_jonction": round((ecart(n - 1, n - 2) + ecart(0, 1)) / 2, 2)}
    res["boucle_simple"] = {"ecart_jonction": round(ecart(n - 1, 0), 2),
                            "ratio": round(ecart(n - 1, 0) / naturel, 2)}
    dire(f"  ping-pong : jonction {res['ping_pong']['ecart_jonction']:.2f} "
         f"({res['ping_pong']['ecart_jonction'] / naturel:.2f}x) mais mouvement inverse")
    dire(f"  boucle simple : jonction {res['boucle_simple']['ecart_jonction']:.2f} "
         f"({res['boucle_simple']['ratio']:.2f}x)")

    strategie = a.strategie
    if strategie == "auto":
        strategie = "simple" if duree_audio <= duree_src else "segments"
    dire(f"  strategie retenue : {strategie}")

    # ---- budget memoire : le mur du volet 5 (regle 80) --------------------------
    # LatentSync decode TOUTE la video en RAM systeme, a la resolution de la source :
    # frames x largeur x hauteur x 3 octets. Au volet 5 (1080p, 8 600 frames) : 49 Go
    # effectivement tenus, 2,6 Go libres, fichier d'echange a 39 Go, cadence effondree de
    # 13 s/it a 116-127 s/it et 14 h 17 de run au lieu de 4 h 30. Le faire AVANT de lancer.
    w_src, h_src, _ = ffprobe_taille(source_stab)
    h_loop = min(a.hauteur_loop, h_src)
    w_loop = int(round(w_src * h_loop / h_src / 2)) * 2
    n_loop = int(duree_audio * FPS_DEFAUT) + 1
    besoin = n_loop * w_loop * h_loop * 3
    libre_ram = ram_libre()
    dire(f"  budget RAM LatentSync : {n_loop} frames de {w_loop}x{h_loop} = "
         f"{besoin / 2**30:.1f} Go a tenir en memoire systeme")
    dire(f"  RAM libre : {libre_ram / 2**30:.1f} Go")
    seg_frames = 0
    if a.segmenter != "0":
        cycle_r = (len(meilleur["starts"]) * meilleur["L"] if strategie == "segments"
                   else (2 * n - 2 if strategie == "ping-pong" else n))
        seg_frames = taille_tranche(a, cycle_r, w_loop, h_loop, libre_ram)
        besoin_seg = seg_frames * w_loop * h_loop * 3
        dire(f"  run segmente : {seg_frames} frames par tranche "
             f"({seg_frames / FPS_DEFAUT:.1f} s = {seg_frames / max(cycle_r, 1):.4g} cycle(s) "
             f"de {cycle_r}) -> {besoin_seg / 2**30:.1f} Go par appel")
        if libre_ram and besoin_seg > 0.60 * libre_ram:
            raise RuntimeError(
                f"meme segmente a {seg_frames} frames, LatentSync demanderait "
                f"{besoin_seg / 2**30:.1f} Go pour {libre_ram / 2**30:.1f} Go libres : "
                "voir --segmenter avec un nombre plus petit.")
        res_segmente = {"cycle_frames": int(cycle_r), "segment_frames": int(seg_frames)}
    else:
        res_segmente = {}
        if libre_ram and besoin > 0.60 * libre_ram and not a.forcer_ram:
            raise RuntimeError(
                f"LatentSync decoderait {besoin / 2**30:.1f} Go en RAM pour "
                f"{libre_ram / 2**30:.1f} Go libres : c'est exactement le mur du volet 5 "
                "(14 h 17 de pagination). Relancer avec --segmenter auto (regles 41, 58, 80) "
                "ou avec --forcer-ram en connaissance de cause.")
    if h_loop != h_src:
        dire(f"  source ramenee a {w_loop}x{h_loop} pour le run : c'est la resolution de "
             "travail du volet 5 (le 4K quadruplerait la RAM ci-dessus)")

    if strategie == "simple":
        cmd = ["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", source_stab,
               "-t", f"{duree_audio:.3f}", "-vf", f"scale={w_loop}:{h_loop}:flags=lanczos",
               "-c:v", "libx264", "-crf", "16", "-preset", "medium",
               "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", sortie]
    elif strategie == "segments":
        S, L = meilleur["starts"], meilleur["L"]
        cycle = len(S) * L
        filtres = "".join(
            f"[0:v]trim=start_frame={s}:end_frame={s + L},setpts=PTS-STARTPTS[s{i}];"
            for i, s in enumerate(S))
        filtres += "".join(f"[s{i}]" for i in range(len(S))) + f"concat=n={len(S)}:v=1[cat];"
        # PAS de fondu enchainé (regle 52) : il fabriquerait un flou de liaison a chaque cycle.
        filtres += (f"[cat]scale={w_loop}:{h_loop}:flags=lanczos,"
                    f"loop=loop=-1:size={cycle}:start=0[v]")
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", source_stab, "-filter_complex", filtres,
               "-map", "[v]", "-t", f"{duree_audio:.3f}", "-c:v", "libx264", "-crf", "16",
               "-preset", "medium", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart",
               sortie]
    else:  # ping-pong, a demander explicitement
        filtres = (f"[0:v]split[a][b];[b]reverse,trim=start_frame=1:end_frame={n - 1},"
                   f"setpts=PTS-STARTPTS[r];[a][r]concat=n=2:v=1[cat];"
                   f"[cat]scale={w_loop}:{h_loop}:flags=lanczos,"
                   f"loop=loop=-1:size={2 * n - 2}:start=0[v]")
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", source_stab, "-filter_complex", filtres,
               "-map", "[v]", "-t", f"{duree_audio:.3f}", "-c:v", "libx264", "-crf", "16",
               "-preset", "medium", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart",
               sortie]
    r = sh(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg : {r.stderr[-500:]}")
    res["strategie"] = strategie
    res["sortie"] = sortie
    if res_segmente:
        res["run_segmente"] = res_segmente
    res["n_frames_sortie"] = ffprobe_frames(sortie)
    # La source doit couvrir TOUTE la duree : sinon le modele termine la fin en sens inverse.
    if res["n_frames_sortie"] / FPS_DEFAUT < duree_audio - 0.1:
        raise RuntimeError(f"boucle trop courte : {res['n_frames_sortie']} frames pour "
                           f"{duree_audio:.2f} s d'audio")
    ecrire(mesures, res)
    dire(f"  {res['n_frames_sortie']} frames ({res['n_frames_sortie'] / FPS_DEFAUT:.2f} s) "
         f"pour {duree_audio:.2f} s d'audio -> {sortie}")
    dire(f"-> {mesures}")
    return sortie


# --------------------------------------------------------------------------- #
# f) LatentSync
# --------------------------------------------------------------------------- #
def etape_latentsync(a, source_loop: str, audio: str) -> str:
    titre("f) LatentSync 1.5 (stage2.yaml 256 px, 20 pas, guidance 1.5, deepcache)")
    sortie = os.path.join(a.dossier, f"sortie_latentsync_{a.volet}.mp4")
    if os.path.exists(sortie) and not a.force:
        dire(f"  deja present, etape sautee : {sortie}")
        return sortie
    cmd = [VENV_PY, MONITEUR, source_loop, audio, sortie, a.dossier,
           "--volet", a.volet, "--latentsync", RACINE]
    if a.segmenter != "0":
        cycle, seg, n_loop = 0, 0, 0
        mesures = os.path.join(a.dossier, f"mesures_boucles_{a.volet}.json")
        if os.path.exists(mesures):
            d = charger(mesures)
            rs = d.get("run_segmente") or {}
            cycle = int(rs.get("cycle_frames", 0))
            seg = int(rs.get("segment_frames", 0))
            n_loop = int(d.get("n_frames_sortie", 0) or 0)
        if not seg:
            # mesures absentes (boucle reprise d'un autre volet) : on recalcule
            w, h, _ = ffprobe_taille(source_loop)
            cycle = cycle or 1
            seg = taille_tranche(a, cycle, w, h, ram_libre())
        travail = os.path.join(a.dossier, f"segments_latentsync_{a.volet}")
        argv = [VENV_PY, SEGMENTS, "--source", source_loop, "--audio", audio,
                "--sortie", sortie, "--travail", travail,
                "--segmenter-frames", str(seg), "--cycle", str(cycle),
                "--volet", a.volet, "--latentsync", RACINE]
        if n_loop:
            # la longueur de la boucle est deja connue (etape e) : ne pas recompter 8 600
            # frames a l'ffprobe a chaque lancement
            argv += ["--frames", str(n_loop), "--fps", str(FPS_DEFAUT)]
        plan_json = os.path.join(a.dossier, f"commande_segments_{a.volet}.json")
        ecrire(plan_json, argv)
        cmd += ["--commande-json", plan_json]
        dire(f"  run segmente : {seg} frames par tranche ({seg / FPS_DEFAUT:.1f} s), "
             f"cycle {cycle} frames, tranches dans {travail}")
        rp = sh(argv + ["--lister"])
        dire(rp.stdout.strip()[:1400])
    dire("  $ " + " ".join(cmd))
    if a.detache:
        # Run de plusieurs heures : detache du shell pour survivre a la session (14 h 17 au
        # volet 5). Le moniteur notifie Telegram et tient a jour moniteur_<volet>_statut.json.
        log = os.path.join(a.dossier, f"pipeline_latentsync_{a.volet}.log")
        with open(log, "w", encoding="utf-8") as f:
            p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=RACINE,
                                 env=ENV_SOUS_PROC,
                                 creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        dire(f"  lance en tache de fond : PID {p.pid}")
        dire(f"  suivi : {log}")
        dire(f"  etat  : {os.path.join(a.dossier, f'moniteur_{a.volet}_statut.json')}")
        return sortie
    code = subprocess.call(cmd, cwd=RACINE, env=ENV_SOUS_PROC)
    if code != 0:
        raise RuntimeError(f"LatentSync a echoue (code {code})")
    return sortie


# --------------------------------------------------------------------------- #
# g) Greffe hautes frequences
# --------------------------------------------------------------------------- #
def etape_hf(a, source_loop: str, genere: str) -> str:
    titre(f"g) greffe hautes frequences (alpha {a.alpha}, masque face, blur {a.blur})")
    sortie = os.path.join(a.dossier, f"sortie_latentsync_{a.volet}_hf_a{a.alpha}.mp4")
    if deja_fait(sortie, a.force):
        return sortie
    cmd = [VENV_PY, HF_TRANSFER, "--source", source_loop, "--generated", genere,
           "--out", sortie, "--alpha", str(a.alpha), "--blur", str(a.blur),
           "--mask", "face", "--det-cache", os.path.join(a.dossier, f"hf_det_{a.volet}.npz"),
           "--verify-align"]
    r = sh(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"greffe HF : {r.stderr[-800:]}")
    dire(r.stdout[-1500:])
    dire(f"  {ffprobe_frames(sortie)} frames -> {sortie}")
    return sortie


# --------------------------------------------------------------------------- #
# h) Mesures avant / apres
# --------------------------------------------------------------------------- #
def etape_mesures(a, source_loop: str, genere: str, hf: str) -> str:
    titre("h) mesures de nettete avant/apres + planche comparative")
    outdir = os.path.join(a.dossier, "mesures_hf")
    os.makedirs(outdir, exist_ok=True)
    cmd = [VENV_PY, HF_RAPPORT, "--reference", source_loop,
           "--colonne", f"source={source_loop}",
           "--colonne", f"latentsync={genere}",
           "--colonne", f"latentsync+HF={hf}",
           "--outdir", outdir, "--planche", "planche_hf.png", "--mesures", "mesures_hf.json"]
    r = sh(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"mesures : {r.stderr[-800:]}")
    dire(r.stdout[-2500:])
    return os.path.join(outdir, "mesures_hf.json")


# --------------------------------------------------------------------------- #
# i) Rapport MD + Telegram
# --------------------------------------------------------------------------- #
def blocs_mesures(m) -> list:
    """Blocs MD des mesures : accepte un dict {colonne: valeurs} OU une liste d'observations.

    mesures_hf.json (ecrit par hf_rapport.py) est une LISTE, un dict par instant mesure :
    l'ancien `for cle, val in m.items()` levait AttributeError 'list' object has no
    attribute 'items' a l'etape i, apres les heures de calcul du run (volet 6).
    """
    paires = []
    if isinstance(m, dict):
        paires = list(m.items())
    elif isinstance(m, list):
        for i, item in enumerate(m):
            if isinstance(item, dict) and item:
                paires.append((f"t={item.get('t', i)}", item))
    return [f"### {cle}\n\n```json\n{json.dumps(val, ensure_ascii=False, indent=1)[:3000]}\n```"
            for cle, val in paires if isinstance(val, dict)]


def etape_rapport(a, etapes: dict) -> str:
    titre("i) rapport MD + notification Telegram")
    mesures_hf = etapes.get("mesures")
    m = charger(mesures_hf) if mesures_hf and os.path.exists(mesures_hf) else None
    bloques = blocs_mesures(m) if m is not None else []
    lignes = [
        f"# Volet {a.volet} — rapport de run",
        "",
        f"- Source : `{a.source}`",
        f"- Audio : `{a.audio}`",
        f"- Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"- Dossier : `{a.dossier}`",
        "",
        "## Etapes",
        "",
    ]
    for nom in ETAPES:
        chemins = etapes.get(nom)
        if chemins:
            lignes.append(f"- **{nom}** : `{chemins}`")
    lignes += ["", "## Mesures", ""] + (bloques or ["(mesures indisponibles)"])
    rapport = os.path.join(a.dossier, f"RAPPORT_{a.volet}.md")
    with open(rapport, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")
    dire(f"-> {rapport}")

    fin = [f"Volet {a.volet} — pipeline termine",
           f"source  : {os.path.basename(a.source)}",
           f"audio   : {os.path.basename(a.audio)}"]
    for nom in ("boucle", "latentsync", "hf"):
        if etapes.get(nom):
            p = etapes[nom]
            taille = os.path.getsize(p) / 1e6 if os.path.exists(p) else 0
            fin.append(f"{nom:9s}: {os.path.basename(p)} ({taille:.1f} Mo)")
    fin.append(f"rapport : {rapport}")
    telegram("\n".join(fin))
    return rapport


# --------------------------------------------------------------------------- #
# Chef d'orchestre
# --------------------------------------------------------------------------- #
def main() -> int:
    p = argparse.ArgumentParser(description="Pipeline talking-head d'un volet")
    p.add_argument("--source", required=True, help="video source (rush)")
    p.add_argument("--audio", required=True, help="audio du clone (WAV/MP3)")
    p.add_argument("--volet", required=True, help="nom court du volet (ex. 6)")
    p.add_argument("--frames", type=int, default=FRAMES_DEFAUT, help="frames de la fenetre")
    p.add_argument("--alpha", type=float, default=1.0, help="poids de la greffe HF")
    p.add_argument("--blur", type=int, default=5, help="ksize du flou passe-bas")
    p.add_argument("--strategie", choices=("auto", "simple", "segments", "ping-pong"),
                   default="auto")
    p.add_argument("--hauteur-loop", type=int, default=1080,
                   help="hauteur de la source envoyee a LatentSync (defaut 1080 : le 4K "
                        "quadruplerait la RAM systeme exigee par le modele)")
    p.add_argument("--segmenter", default="0",
                   help="lance LatentSync en tranches de N frames (ou 'auto') au lieu d'un "
                        "seul appel : c'est le remede au mur de RAM (regles 41, 58, 80). "
                        "N est arrondi au multiple du cycle de la boucle")
    p.add_argument("--forcer-ram", action="store_true",
                   help="lancer meme si le budget RAM du modele depasse la RAM libre")
    p.add_argument("--depuis", choices=ETAPES, default=ETAPES[0], help="reprendre a cette etape")
    p.add_argument("--seulement", choices=ETAPES, default=None, help="ne faire que cette etape")
    p.add_argument("--detache", action="store_true",
                   help="lancer LatentSync en tache de fond (recommande : plusieurs heures)")
    p.add_argument("--force", action="store_true", help="refaire les etapes deja faites")
    p.add_argument("--plan", action="store_true", help="afficher le plan sans rien executer")
    a = p.parse_args()

    a.dossier = os.path.join(TESTS, f"v4_talking_head_{a.volet}")
    a.label = os.path.splitext(os.path.basename(a.source))[0]
    os.makedirs(a.dossier, exist_ok=True)
    etapes = {}

    # Tous les chemins en absolu des le depart (regle 71 : ne jamais melanger un changement
    # de repertoire et des chemins relatifs — le sous-processus tourne dans la racine du depot).
    a.source = os.path.abspath(a.source)
    a.audio = os.path.abspath(a.audio)
    a.dossier = os.path.abspath(a.dossier)

    for c in (a.source, a.audio):
        if not os.path.exists(c):
            dire(f"fichier introuvable : {c}")
            return 2

    if a.plan:
        dire(f"source   : {a.source}")
        dire(f"audio    : {a.audio}  ({ffprobe_duree(a.audio):.2f} s)")
        dire(f"volet    : {a.volet}  ->  {a.dossier}")
        dire(f"fenetre  : {a.frames} frames")
        dire("etapes   : " + " -> ".join(
            e for e in ETAPES if ETAPES.index(e) >= ETAPES.index(a.depuis) and
            (a.seulement is None or e == a.seulement)))
        dire(f"latentsync : {'detache' if a.detache else 'au premier plan'}"
             + (f"  |  segmente : {a.segmenter} frames par tranche" if a.segmenter != "0"
                else "  |  un seul appel"))
        return 0

    # Un seul interpreteur sait faire tourner tout le pipeline : le venv de LatentSync.
    # Le sondage porte sur numpy ET cv2 : cv2 se contente d'un avertissement quand numpy est
    # casse, donc un sondage sur cv2 seul laisserait passer un environnement pollue.
    try:
        import numpy  # noqa: F401
        import cv2  # noqa: F401
    except ImportError:
        # Correctif 9 : l'echec peut venir de l'environnement (PYTHONPATH du cron Hermes ->
        # numpy 2.4.3 cp311 vu par un python 3.10) et non de l'interpreteur. On relance alors
        # avec l'environnement assaini, meme si l'interpreteur est deja le bon ; le drapeau
        # HERMES_PIPELINE_REEXEC empeche toute boucle.
        if os.environ.get("HERMES_PIPELINE_REEXEC") != "1" and os.path.exists(VENV_PY):
            env = dict(ENV_SOUS_PROC)
            env["HERMES_PIPELINE_REEXEC"] = "1"
            dire(f"numpy/cv2 absents dans cet environnement : relance avec {VENV_PY} "
                 f"(environnement assaini)")
            return subprocess.call([VENV_PY, os.path.abspath(__file__)] + sys.argv[1:],
                                   cwd=RACINE, env=env)

    def actif(nom: str) -> bool:
        if a.seulement:
            return nom == a.seulement
        return ETAPES.index(nom) >= ETAPES.index(a.depuis)

    t0 = time.time()
    if actif("audit"):
        etapes["audit"] = etape_audit(a)
    audit_json = etapes.get("audit") or os.path.join(a.dossier, f"audit_{a.volet}_{a.label}.json")
    if actif("fenetre"):
        etapes["fenetre"] = etape_fenetre(a, audit_json)
    fenetre_json = etapes.get("fenetre") or os.path.join(a.dossier, f"fenetre_{a.volet}.json")
    if actif("extraction"):
        etapes["extraction"] = etape_extraction(a, fenetre_json)
    source_fenetre = etapes.get("extraction") or os.path.join(a.dossier, f"source_{a.volet}.mp4")
    if actif("stabilisation"):
        etapes["stabilisation"], _ = etape_stabilisation(a, source_fenetre)
    source_stab = etapes.get("stabilisation") or os.path.join(a.dossier, f"source_{a.volet}_stab.mp4")
    if actif("boucle"):
        etapes["boucle"] = etape_boucle(a, source_stab, a.audio)
    source_loop = etapes.get("boucle") or os.path.join(a.dossier, f"source_{a.volet}_loop.mp4")
    if actif("latentsync"):
        etapes["latentsync"] = etape_latentsync(a, source_loop, a.audio)
    genere = etapes.get("latentsync") or os.path.join(a.dossier, f"sortie_latentsync_{a.volet}.mp4")
    if actif("hf") and os.path.exists(genere):
        etapes["hf"] = etape_hf(a, source_loop, genere)
    hf = etapes.get("hf") or os.path.join(a.dossier,
                                          f"sortie_latentsync_{a.volet}_hf_a{a.alpha}.mp4")
    if actif("mesures") and os.path.exists(hf) and os.path.exists(genere):
        etapes["mesures"] = etape_mesures(a, source_loop, genere, hf)
    if actif("rapport"):
        etapes["rapport"] = etape_rapport(a, etapes)

    dire(f"\npipeline : {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
