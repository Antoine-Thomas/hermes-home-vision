# -*- coding: utf-8 -*-
"""Run LatentSync segmente : decoupe source et audio en tranches, un appel par tranche.

POURQUOI. LatentSync decode toute la video en RAM systeme (frames x largeur x hauteur x 3).
Sur le volet 5 (8 600 frames 1080p) cela fait 53 Go pour ~44 Go libres : la machine pagine et
le run passe de 4 h 30 a 14 h 17. Segmenter ramene le besoin a la taille du segment.

REGLE 58 (skill talking-head-video-8gb) : la duree d'un segment doit etre un multiple EXACT du
cycle de la source, sinon le modele repart sur une phase differente au raccord et la pose
saute (mesure volet 4 : MAD 6,5 aux jointures contre 0,71 de mediane).
  - source au moins aussi longue que l'audio (cas du pipeline : la boucle fait la duree de
    l'audio) -> on decoupe la video en tranches contigues, cycle = --cycle (periode de la
    boucle donnee par l'etape e) ;
  - source plus courte que l'audio (cas volet 4 : 200 frames pour 271 s de voix) -> le modele
    boucle la source en ping-pong, cycle = 2 x frames de la source, et la MEME source est
    repassee a chaque segment.

L'audio est decoupe en WAV pcm_s16le : un decoupage sur de l'AAC tomberait sur des trames de
1024 echantillons (~21 ms), pas sur l'echantillon exact.

Reprise : un segment deja produit est saute (relancer le script reprend ou il s'est arrete).

NE PAS definir PYTORCH_CUDA_ALLOC_CONF (regle 10 du skill : cadence divisee par 22).

Usage :
  venv/Scripts/python.exe tests/run_latentsync_segments.py \\
      --source tests/v4_talking_head_v3/source_v5_loop_344.mp4 \\
      --audio  C:/Users/searc/AppData/Local/hermes/data/xtts/audio_youtube_v5.wav \\
      --sortie tests/v4_talking_head_v5/sortie_latentsync_v5.mp4 \\
      --travail tests/v4_talking_head_v5/segments_latentsync_v5 \\
      --cycle 135 --segmenter-frames 1200 --volet v5
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time

RACINE_SCRIPT = os.path.dirname(os.path.abspath(__file__))
LATENTSYNC = os.path.dirname(RACINE_SCRIPT)


def sh(cmd: list[str], cwd: str | None = None, **kw) -> subprocess.CompletedProcess:
    print("  $ " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, **kw)


def ffprobe_frames(video: str) -> int:
    r = sh(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", video])
    try:
        return int((r.stdout or "0").strip().splitlines()[0])
    except (ValueError, IndexError):
        return 0


def ffprobe_duree(chemin: str) -> float:
    r = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", chemin])
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def ffprobe_fps(video: str) -> float:
    r = sh(["ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", video])
    txt = (r.stdout or "0/1").strip()
    try:
        num, _, den = txt.partition("/")
        return float(num) / float(den or 1)
    except ValueError:
        return 0.0


def plan(a) -> dict:
    """Calcule les tranches. Aucune ecriture : sert aussi au mode --lister."""
    fps = a.fps or ffprobe_fps(a.source)
    n_frames_video = a.frames or ffprobe_frames(a.source)
    duree_audio = ffprobe_duree(a.audio)
    n_frames_audio = int(round(duree_audio * fps))

    decoupe_video = n_frames_video >= n_frames_audio - 2   # marge de 2 frames d'arrondi
    if a.cycle > 0:
        cycle = a.cycle
    elif decoupe_video:
        cycle = 1
    else:
        cycle = 2 * n_frames_video      # ping-pong interne du modele

    # On arrondit VERS LE HAUT au multiple du cycle : un segment plus long coute de la RAM,
    # un segment plus court casse la continuite de phase.
    seg = int(math.ceil(max(1, a.segmenter_frames) / cycle) * cycle)
    total = n_frames_audio if n_frames_audio > 0 else n_frames_video
    n_seg = int(math.ceil(total / seg)) if seg else 0

    tranches = []
    for i in range(n_seg):
        n_ici = min(seg, total - i * seg)
        tranches.append({
            "i": i,
            "t0": (i * seg) / fps,
            "duree": n_ici / fps,
            "frames": n_ici,
            "decoupe_video": decoupe_video,
            "debut_frame": i * seg,
        })
    return {
        "fps": fps, "frames_video": n_frames_video, "frames_audio": n_frames_audio,
        "duree_audio": duree_audio, "cycle": cycle, "segment_frames": seg,
        "n_segments": n_seg, "decoupe_video": decoupe_video, "tranches": tranches,
    }


def trancher_video(source: str, t0: float, frames: int, sortie: str, fps: float) -> None:
    """Tranche EXACTE en frames : reencodage, donc seek precis (un -c copy tomberait sur
    l'image-cle precedente et decalerait la tranche par rapport a l'audio)."""
    r = sh(["ffmpeg", "-y", "-v", "error", "-ss", "%.6f" % t0, "-i", source,
            "-frames:v", str(frames), "-c:v", "libx264", "-crf", "16", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", sortie])
    if r.returncode != 0:
        raise RuntimeError(f"tranchage video echoue pour {sortie} : {(r.stderr or '')[-300:]}")


def tranche_video_valide(chemin: str, frames_attendus: int) -> bool:
    """Vrai si la tranche video existe ET correspond au plan courant.

    Un fichier peut exister sans etre valable : ecriture interrompue (index moov absent,
    "Could not open video") ou decoupage issu d'un plan precedent (5400 frames alors que le
    plan en demande 2160, ce qui decale toute la video finale). La reprise sur simple
    existence a fait echouer un run le 26/09 : on controle le nombre de frames decodables.
    """
    if not os.path.exists(chemin) or os.path.getsize(chemin) == 0:
        return False
    r = sh(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", chemin])
    if r.returncode != 0:
        return False
    try:
        return int((r.stdout or "").strip()) == frames_attendus
    except ValueError:
        return False


def tranche_audio_valide(chemin: str, duree_attendue: float) -> bool:
    """Vrai si la tranche audio existe ET fait la duree du plan (tolerance 0,5 s)."""
    if not os.path.exists(chemin) or os.path.getsize(chemin) == 0:
        return False
    r = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", chemin])
    if r.returncode != 0:
        return False
    try:
        return abs(float((r.stdout or "").strip()) - duree_attendue) < 0.5
    except ValueError:
        return False


def trancher_audio(audio: str, t0: float, duree: float, sortie: str) -> None:
    r = sh(["ffmpeg", "-y", "-v", "error", "-ss", "%.6f" % t0, "-t", "%.6f" % duree,
            "-i", audio, "-c:a", "pcm_s16le", sortie])
    if r.returncode != 0:
        raise RuntimeError(f"tranchage audio echoue pour {sortie} : {(r.stderr or '')[-300:]}")


def commande_inference(a, video: str, audio: str, sortie: str) -> list[str]:
    """Meme commande que le moniteur, pour que la progression soit lisible pareil."""
    return [
        a.python, "-u", "-m", "scripts.inference",
        "--unet_config_path", "configs/unet/stage2.yaml",
        "--inference_ckpt_path", "checkpoints/latentsync_unet.pt",
        # volet 7 : 25 pas et guidance 1,8 (au lieu de 20 et 1,5) pour une bouche plus nette.
        # Le correctif officiel (LatentSync 1.6 en 512x512) demande 18 Go de VRAM, indisponible ici.
        "--inference_steps", "25", "--guidance_scale", "1.8", "--enable_deepcache",
        "--video_path", os.path.abspath(video),
        "--audio_path", os.path.abspath(audio),
        "--video_out_path", os.path.abspath(sortie),
        "--temp_dir", os.path.join(a.latentsync, f"temp_{a.volet}"),
    ]


def main() -> int:
    p = argparse.ArgumentParser(add_help=True, description="Run LatentSync segmente")
    p.add_argument("--source", required=True, help="video longue (la boucle du pipeline)")
    p.add_argument("--audio", required=True)
    p.add_argument("--sortie", required=True)
    p.add_argument("--travail", default="", help="dossier des tranches (defaut : a cote de la sortie)")
    p.add_argument("--segmenter-frames", type=int, default=1200,
                   help="duree visee d'un segment, en frames (arrondie au cycle)")
    p.add_argument("--cycle", type=int, default=0,
                   help="periode de la boucle en frames (0 = deduire)")
    p.add_argument("--volet", default="volet")
    p.add_argument("--python", default="", help="interpreteur (venv LatentSync par defaut)")
    p.add_argument("--latentsync", default=LATENTSYNC)
    p.add_argument("--fps", type=float, default=0.0, help="force le fps (sinon lu)")
    p.add_argument("--frames", type=int, default=0, help="force le nombre de frames (sinon lu)")
    p.add_argument("--lister", action="store_true",
                   help="affiche le plan et les commandes, n'ecrit rien, n'execute rien")
    p.add_argument("--refaire", action="store_true", help="refait les tranches deja produites")
    a = p.parse_args()

    a.latentsync = os.path.abspath(a.latentsync)
    a.python = a.python or os.path.join(a.latentsync, "venv", "Scripts", "python.exe")
    a.source = os.path.abspath(a.source)
    a.audio = os.path.abspath(a.audio)
    a.sortie = os.path.abspath(a.sortie)
    a.travail = os.path.abspath(a.travail) if a.travail else \
        os.path.join(os.path.dirname(a.sortie), f"segments_latentsync_{a.volet}")

    if not os.path.exists(a.source):
        raise RuntimeError(f"source introuvable : {a.source}")
    if not os.path.exists(a.audio):
        raise RuntimeError(f"audio introuvable : {a.audio}")

    infos = plan(a)
    seg, total = infos["segment_frames"], infos["frames_audio"] or infos["frames_video"]
    mode = "tranches contigues" if infos["decoupe_video"] else "source rejouee (ping-pong du modele)"
    print(f"source    : {os.path.basename(a.source)} — {infos['frames_video']} frames "
          f"({infos['fps']:.4g} fps)", flush=True)
    print(f"audio     : {os.path.basename(a.audio)} — {infos['duree_audio']:.3f} s "
          f"({total} frames attendues)", flush=True)
    print(f"cycle     : {infos['cycle']} frames  |  mode : {mode}", flush=True)
    print(f"segments  : {infos['n_segments']} x {seg} frames ({seg / max(infos['fps'], 1):.2f} s) "
          f"= {seg // infos['cycle']} cycle(s) de {infos['cycle']} frames", flush=True)

    if a.lister:
        for t in infos["tranches"]:
            aud = os.path.join(a.travail, "aud_%02d.wav" % t["i"])
            vid = os.path.join(a.travail, "src_%02d.mp4" % t["i"])
            out = os.path.join(a.travail, "out_%02d.mp4" % t["i"])
            print(f"\n--- segment {t['i']} : {t['frames']} frames des frame {t['debut_frame']} "
                  f"(t={t['t0']:.3f} s, {t['duree']:.3f} s) ---", flush=True)
            print("  audio  : ffmpeg -ss %.6f -t %.6f -i %s -c:a pcm_s16le %s"
                  % (t["t0"], t["duree"], os.path.basename(a.audio), os.path.basename(aud)))
            if t["decoupe_video"]:
                print("  video  : ffmpeg -ss %.6f -i %s -frames:v %d -c:v libx264 (crf 16) %s"
                      % (t["t0"], os.path.basename(a.source), t["frames"], os.path.basename(vid)))
            else:
                print("  video  : %s (source entiere, passee telle quelle)"
                      % os.path.basename(a.source))
            print("  modele : " + " ".join(
                commande_inference(a, vid if t["decoupe_video"] else a.source, aud, out)))
        return 0

    os.makedirs(a.travail, exist_ok=True)
    journal = os.path.join(a.travail, f"segments_{a.volet}.log")

    def noter(texte: str) -> None:
        with open(journal, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{texte}\n")

    noter(f"plan : {infos['n_segments']} segments de {seg} frames, cycle {infos['cycle']}, "
          f"mode {mode}")

    t_debut = time.time()
    for t in infos["tranches"]:
        i = t["i"]
        aud = os.path.join(a.travail, "aud_%02d.wav" % i)
        vid = os.path.join(a.travail, "src_%02d.mp4" % i)
        out = os.path.join(a.travail, "out_%02d.mp4" % i)

        if os.path.exists(out) and not a.refaire and tranche_video_valide(out, t["frames"]):
            print(f"segment {i + 1}/{infos['n_segments']} : deja fait", flush=True)
            noter(f"segment {i} deja fait")
            continue

        print(f"=== segment {i + 1}/{infos['n_segments']} === {time.strftime('%H:%M:%S')}",
              flush=True)
        if not tranche_audio_valide(aud, t["duree"]) or a.refaire:
            trancher_audio(a.audio, t["t0"], t["duree"], aud)
        if t["decoupe_video"] and (not tranche_video_valide(vid, t["frames"]) or a.refaire):
            trancher_video(a.source, t["t0"], t["frames"], vid, infos["fps"])
        entre_video = vid if t["decoupe_video"] else a.source

        t0 = time.time()
        cmd = commande_inference(a, entre_video, aud, out)
        r = subprocess.run(cmd, cwd=a.latentsync)
        duree = time.time() - t0
        if r.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
            noter(f"segment {i} ECHEC (code {r.returncode}) apres {duree:.0f} s")
            print(f"ECHEC segment {i + 1} (code {r.returncode}) — la reprise reprendra ici",
                  flush=True)
            return 1
        noter(f"segment {i} OK en {duree:.0f} s")
        print(f"segment {i + 1}/{infos['n_segments']} OK en {duree:.0f} s", flush=True)

    # --- concatenation ---
    liste = os.path.join(a.travail, "concat.txt")
    with open(liste, "w", encoding="utf-8") as f:
        for t in infos["tranches"]:
            f.write("file '%s'\n" % os.path.join(a.travail, "out_%02d.mp4" % t["i"])
                    .replace(os.sep, "/"))
    r = sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", liste,
            "-c", "copy", a.sortie], cwd=a.latentsync)
    if r.returncode != 0 or not os.path.exists(a.sortie):
        print("concat -c copy a echoue, reencodage :", (r.stderr or "")[-300:], flush=True)
        r = sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", liste,
                "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-c:a", "aac",
                "-b:a", "320k", a.sortie], cwd=a.latentsync)
        if r.returncode != 0:
            noter(f"concat ECHEC : {(r.stderr or '')[-300:]}")
            return 1

    n_final = ffprobe_frames(a.sortie)
    ecoule = time.time() - t_debut
    print(f"TERMINE -> {a.sortie} ({os.path.getsize(a.sortie) / 1e6:.1f} Mo, {n_final} frames, "
          f"{ecoule / 60:.1f} min)", flush=True)
    noter(f"TERMINE {a.sortie} : {n_final} frames, {ecoule / 60:.1f} min")
    # Les tranches de sortie restent : elles permettent de refaire un seul segment sans
    # relancer le modele sur toute la video. Les tranches d'entree sont supprimables.
    return 0


if __name__ == "__main__":
    sys.exit(main())
