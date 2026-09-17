#!/usr/bin/env python
"""
montage_comparatif.py
=====================
Montage comparatif "Réalité vs Stable Diffusion" pour projet Caen Travelling - Jean-Paul Dub.

Usage:
  python montage_comparatif.py --cuts cuts_visages.json --out clip_comparatif_visages.mp4 --plan
  python montage_comparatif.py --cuts cuts_visages.json --out clip_comparatif_visages.mp4 --crf-seg 20 --crf-final 18

Sources attendues :
  - "reality" : caentravelling.mp4 (version originale)
  - "sd" : caentravelling2_4K60_stable.mp4 (version Stable Diffusion)
"""

import json, subprocess, sys, argparse, os
from pathlib import Path

# Configuration
TARGET_W, TARGET_H, TARGET_FPS = 1920, 1080, 24
AUDIO_FILE = "Jean-Paul Dub - Pélerinage ft. Bout and Huck.wav"
REALITY_SRC = "caentravelling.mp4"
SD_SRC = "caentravelling2_4K60_stable.mp4"

# Transitions par type de contenu
TRANSITIONS = {
    "fade": 0.5,      # visages / plans rapprochés
    "slideleft": 0.4,  # rues / églises / mouvement
    "slideright": 0.4,
}

def build_ffmpeg_filter(segments, cuts_data):
    """Construit le filter_complex ffmpeg pour xfade chain + audio loudnorm."""
    v_filters = []
    a_filters = []
    
    # 1. Inputs vidéo (un par segment)
    for i, seg in enumerate(segments):
        src = REALITY_SRC if seg["source"] == "reality" else SD_SRC
        v_filters.append(f"[{i}:v]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,fps={TARGET_FPS},setpts=PTS-STARTPTS[v{i}]")
        a_filters.append(f"[{i}:a]anull[a{i}]")
    
    # 2. Chaîne xfade vidéo
    last_v = "v0"
    cumulative_dur = segments[0]["duration"]
    cumulative_xfade = 0.0
    
    for i in range(1, len(segments)):
        trans = segments[i]["transition"]
        dur = TRANSITIONS.get(trans, 0.4)
        xfade_name = f"xf{i}"
        
        # offset = cum_dur_prev - cum_xfade_prev
        offset = cumulative_dur - cumulative_xfade
        
        v_filters.append(f"[{last_v}][v{i}]{xfade_name}=transition={trans}:duration={dur}:offset={offset:.6f}[{xfade_name}]")
        last_v = xfade_name
        
        cumulative_dur += segments[i]["duration"]
        cumulative_xfade += dur
    
    # 3. Audio : concat + loudnorm
    a_inputs = "".join([f"[a{i}]" for i in range(len(segments))])
    a_filters.append(f"{a_inputs}concat=n={len(segments)}:v=0:a=1,atrim=0:{cumulative_dur:.6f},loudnorm=I=-16:TP=-3:LRA=11[aout]")
    
    # 4. Sortie vidéo finale
    v_filters.append(f"[{last_v}]trim=0:{cumulative_dur:.6f},setpts=PTS-STARTPTS[vout]")
    
    filter_complex = ";".join(v_filters + a_filters)
    return filter_complex, cumulative_dur

def run_montage(cuts_file, out_file, crf_seg=20, crf_final=18, plan_only=False):
    with open(cuts_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    segments = data["segments"]
    
    if plan_only:
        print(f"=== PLAN {cuts_file} ===")
        print(f"Segments: {len(segments)}")
        print(f"Durée totale: {sum(s['duration'] for s in segments):.2f}s")
        print(f"Sources: reality={sum(1 for s in segments if s['source']=='reality')}, sd={sum(1 for s in segments if s['source']=='sd')}")
        transitions = {}
        for s in segments:
            t = s.get("transition", "none")
            transitions[t] = transitions.get(t, 0) + 1
        print(f"Transitions: {transitions}")
        return
    
    # Construire filter_complex
    filter_complex, total_dur = build_ffmpeg_filter(segments, data)
    
    # Construire commande ffmpeg
    inputs = []
    for seg in segments:
        src = REALITY_SRC if seg["source"] == "reality" else SD_SRC
        in_point = seg["in"]
        dur = seg["duration"]
        inputs.extend(["-ss", f"{in_point:.6f}", "-t", f"{dur:.6f}", "-i", src])
    
    # Ajouter l'audio en dernier input
    inputs.extend(["-i", AUDIO_FILE])
    
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf_final),
        "-c:a", "aac", "-b:a", "192k",
        "-r", str(TARGET_FPS),
        out_file
    ]
    
    print(f"Lancement ffmpeg ({len(segments)} segments, ~{total_dur:.1f}s)...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("ERREUR ffmpeg:")
        print(result.stderr[-2000:])
        sys.exit(1)
    
    print(f"✅ Terminé: {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuts", required=True, help="Fichier JSON de coupes (cuts_*.json)")
    parser.add_argument("--out", required=True, help="Fichier de sortie MP4")
    parser.add_argument("--crf-seg", type=int, default=20, help="CRF segments (non utilisé ici, encodage final direct)")
    parser.add_argument("--crf-final", type=int, default=18, help="CRF final")
    parser.add_argument("--plan", action="store_true", help="Afficher le plan sans encoder")
    args = parser.parse_args()
    
    run_montage(args.cuts, args.out, args.crf_seg, args.crf_final, args.plan)