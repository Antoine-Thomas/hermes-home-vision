# -*- coding: utf-8 -*-
"""Assemblage final d'un volet : lipsync 1080p + carton de titre + incrustations + filigrane.

Gabarit versionne : %LOCALAPPDATA%\\hermes\\scripts\\video\\assemble_v6.py (depot git).
Entree : le dernier sortie_latentsync_<VOLET>*.mp4 (greffe HF de l'etape g si elle existe).
Sortie : mp4 1080p H.264 publie (1920x1080, crf 20, preset fast, 25 fps), sans sous-titre.

Correctifs appliques apres le volet 6 (detail : skills/media/talking-head-video/references/pipeline-bugs.md) :
  3  chainage ffmpeg sans double crochet : cour = "0:v" / cour = f"v{idx}" (jamais "[0:v]")
  4  garde-fou contre le flux infini : -loop 1 sans borne -> -shortest (+ -t duree reelle)
  6  flux PNG statiques a 1 image/s : -loop 1 -framerate 1 (25 decodages/s -> 1)
  7  reglages YouTube par defaut : -preset fast -crf 20 (et non medium/crf 18 : 3 h d'encodage)
  8  ffmpeg plus jamais orphelin : taskkill /F /IM ffmpeg.exe si l'assemblage casse
  9  duree cible = duree reelle du dernier sortie_latentsync_<VOLET>*.mp4, pas une valeur ronde
  10 reference = volet precedent publie, refusee sous 60 s (le clip de 19 s donne au volet 6 a
     fausse toutes les estimations)

Parametrable par variables d'environnement : VOLET (defaut 6), VIDEO_REFERENCE, SORTIE_VIDEO, VIDEO_DIR.
Pour le volet 7 : VOLET=7 SORTIE_VIDEO="...\\tutotete21_<slug>.mp4" (la reference reste le volet precedent).

Incrustations du volet 6 (horodatage mesure sur l'audio reel, overlay_timing_v6.json) :
  titre_intro_v6.png        0,0 -> 14,0   6e edition
  overlay_01_schema.png   101,7 -> 158,7  schema d'architecture (3 profils, RAG/Backend/SiYuan, Jev)
  overlay_02_openrouter  187,5 -> 248,8   installation Jev + OpenRouter
  overlay_03_lien_v13    300,9 -> 336,4   lien de telechargement v1.3 + commandes
Le filigrane watermark_logo.png est applique sur toute la duree (comme les volets 3/4/5).
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys

VID = os.environ.get("VIDEO_DIR", r"C:\Users\searc\AppData\Local\hermes\data\video_youtube")
VOLET = os.environ.get("VOLET", "6")
DOSSIER = os.path.join(VID, "LatentSync", "tests", f"v4_talking_head_{VOLET}")
TIMING = os.path.join(VID, f"overlay_timing_v{VOLET}.json")
WM = os.path.join(VID, "watermark_logo.png")
SORTIE = os.environ.get(
    "SORTIE_VIDEO", r"C:\Users\searc\Desktop\hermes tuto\tutotete20_jev_llmwiki.mp4")

# Correctif 10 : la reference de format et de duree d'un volet est le volet PRECEDENT PUBLIE.
# Le fichier nomme tutotete19.mp4 sur le Bureau ne dure que 19,12 s (extrait) : c'est lui qui a
# fausse les estimations du volet 6. Le volet precedent reel est le volet 6 : 336,4 s.
REFERENCE = os.environ.get(
    "VIDEO_REFERENCE", r"C:\Users\searc\Desktop\hermes tuto\tutotete20_jev_llmwiki.mp4")
DUREE_REFERENCE_MIN = 60.0


def duree_ffprobe(chemin: str) -> float:
    """Duree reelle d'un fichier en secondes, lue par ffprobe."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", chemin],
                       capture_output=True, text=True)
    m = re.search(r"[\d.]+", r.stdout or "")
    if not m:
        raise SystemExit(f"duree illisible pour {chemin}\n{(r.stderr or '')[-300:]}")
    return float(m.group(0))


def verifier_reference() -> float:
    """Correctif 10 : arret immediat si la reference n'est pas le volet precedent publie."""
    if not os.path.exists(REFERENCE):
        raise SystemExit(f"reference manquante : {REFERENCE}\n"
                         "(la reference est le volet precedent publie)")
    duree = duree_ffprobe(REFERENCE)
    if duree < DUREE_REFERENCE_MIN:
        raise SystemExit(f"reference suspecte : {REFERENCE} ne dure que {duree:.1f} s "
                         f"(< {DUREE_REFERENCE_MIN:.0f} s).\n"
                         "ARRET : demander la bonne reference (le volet precedent publie) "
                         "avant de lancer l'assemblage.")
    return duree


def dernier_latentsync() -> str:
    """Correctif 9 : dernier sortie_latentsync_<VOLET>*.mp4 produit, greffe HF prioritaire."""
    candidats = [p for p in glob.glob(os.path.join(DOSSIER, f"sortie_latentsync_{VOLET}*.mp4"))
                 if os.path.isfile(p)]
    if not candidats:
        raise SystemExit(f"aucun sortie_latentsync_{VOLET}*.mp4 dans {DOSSIER}\n"
                         "(produit par l'etape f/latentsync du pipeline)")
    hf = [p for p in candidats if "_hf" in os.path.basename(p)]
    return max(hf or candidats, key=os.path.getmtime)


def run(cmd, label=""):
    print(f"[{label}] ...", flush=True)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except Exception:
        # Correctif 8 : un ffmpeg laisse orphelin garde un coeur pendant des heures (volet 6).
        subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], capture_output=True)
        raise
    if r.returncode != 0:
        print("STDERR:", r.stderr[-1500:])
        subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], capture_output=True)
        sys.exit(1)
    print("  -> OK", flush=True)


def main() -> int:
    duree_ref = verifier_reference()
    entree = dernier_latentsync()
    duree_cible = duree_ffprobe(entree)   # correctif 9 : duree reelle, pas une valeur ronde
    print(f"reference   : {REFERENCE} ({duree_ref:.1f} s)", flush=True)
    print(f"entree      : {entree}", flush=True)
    print(f"duree cible : {duree_cible:.3f} s (duree reelle du dernier LatentSync)", flush=True)
    if not os.path.exists(TIMING):
        raise SystemExit(f"timing manquant : {TIMING}")
    lignes = json.load(open(TIMING, encoding="utf-8"))

    entrees = ["-i", entree]
    filtres = []
    cour = "0:v"          # correctif 3 : sans crochets, les crochets restent dans le f-string
    idx = 1
    for l in lignes:
        chemin = os.path.join(VID, l["fichier"].replace("/", os.sep))
        if not os.path.exists(chemin):
            raise SystemExit(f"incrustation manquante : {chemin}")
        # correctif 6 : une image statique se decode a 1 im/s, pas a 25
        entrees += ["-loop", "1", "-framerate", "1", "-i", chemin]
        filtres.append(f"[{cour}][{idx}:v]overlay=0:0:enable='between(t,{l['start']},{l['end']})'[v{idx}]")
        cour = f"v{idx}"
        idx += 1
    # filigrane permanent en dernier
    entrees += ["-loop", "1", "-framerate", "1", "-i", WM]
    filtres.append(f"[{cour}][{idx}:v]overlay=0:0[vf]")

    cmd = (["ffmpeg", "-y", *entrees, "-filter_complex", ";".join(filtres),
            "-map", "[vf]", "-map", "0:a",
            "-t", f"{duree_cible:.3f}",
            "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-r", "25", "-shortest", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", SORTIE])
    run(cmd, "assemblage final 1080p")

    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration,size:stream=codec_name,width,height,r_frame_rate",
                        "-of", "default=noprint_wrappers=1", SORTIE], capture_output=True, text=True)
    print(r.stdout)
    print(f"=== TERMINE : {SORTIE} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
