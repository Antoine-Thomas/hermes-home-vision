# -*- coding: utf-8 -*-
"""Horodatage des incrustations du volet 7, deduit de l'audio reellement genere.

Source de verite : audio_youtube_v6.json (bornes de tranches du volet 6). Le volet 7
utilise desormais audio_youtube_v7.wav = la piste audio extraite de
tutotete20_jev_llmwiki.mp4 (336,384 s, PCM 24 kHz mono), c'est-a-dire la MEME narration
que le volet 6 : les bornes de tranches du volet 6 s'appliquent donc telles quelles.
La fin de la derniere incrustation est bornee par la duree REELLE de l'audio (ffprobe).
Les frontieres de section sont reperees par la phrase qui les ouvre dans le texte, puis
arrondies au debut de la tranche qui la contient.

Sortie : C:\\Users\\searc\\AppData\\Local\\hermes\\data\\video_youtube\\overlay_timing_v7.json
         (meme forme que overlay_timing_v6.json : {ecran, fichier, start, end})
"""
from __future__ import annotations

import json
import os
import subprocess
import re
import unicodedata

BASE = r"C:\Users\searc\AppData\Local\hermes\data\xtts"
VID = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube"
JSON = os.path.join(BASE, "audio_youtube_v6.json")
AUDIO_V7 = os.path.join(BASE, "audio_youtube_v7.wav")


def duree_audio(chemin: str) -> float:
    """Duree reelle du WAV (la somme des tranches peut differer de quelques ms)."""
    if not os.path.exists(chemin):
        return 0.0
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", chemin], capture_output=True, text=True)
    try:
        return float((r.stdout or "").strip())
    except ValueError:
        return 0.0


DUREE_AUDIO = duree_audio(AUDIO_V7)
OUT = os.path.join(VID, "overlay_timing_v7.json")

# incrustation -> phrase d'ouverture (dans la tranche), marge avant (s), fichier PNG
PLAN = [
    ("Carton de titre - 7e edition", None, -1.0, "overlays_v7/titre_intro_v7.png", 0.0, 14.0),
    ("Schema d'architecture (3 profils, RAG 8200, Backend 9119, SiYuan 6806, Jev)",
     "Passons \u00e0 la pratique", 1.2, "overlays_v7/overlay_01_schema.png", None, None),
    ("Jev sur OpenRouter - cle, modele typesafe/jev-1.13",
     "Premi\u00e8re \u00e9tape", 0.0, "overlays_v7/overlay_02_openrouter.png", None, None),
    ("Version 1.3 - lien de telechargement + installation",
     "On termine par la mise en route", 0.8, "overlays_v7/overlay_03_lien_v13.png", None, None),
]
# fin d'une incrustation = phrase qui ouvre le bloc suivant
FINS = {
    "overlays_v7/overlay_01_schema.png": "C'est le sujet qui change le quotidien",
    "overlays_v7/overlay_02_openrouter.png": "Parlons de la nouvelle version",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


data = json.load(open(JSON, encoding="utf-8"))
tranches = data["tranches"]

# bornes de chaque tranche dans l'audio assemble
bornes, t = [], 0.0
for tr in tranches:
    bornes.append((t, t + tr["garde_s"], tr["texte_tts"]))
    t += tr["garde_s"]
duree = round(t, 2)
print(f"duree assemblee : {duree} s ({len(tranches)} tranches)")


def ou_debut(phrase: str):
    p = norm(phrase)
    for deb, fin, texte in bornes:
        if p in norm(texte):
            return deb
    return None


def ou_fin(phrase: str):
    p = norm(phrase)
    for deb, fin, texte in bornes:
        if p in norm(texte):
            return deb
    return None


lignes, precedent = [], None
for ecran, marqueur, marge, fichier, fixe_deb, fixe_fin in PLAN:
    if marqueur is None:
        deb = max(0.0, fixe_deb)
        fin = fixe_fin
    else:
        deb = ou_debut(marqueur)
        if deb is None:
            raise SystemExit(f"marqueur introuvable : {marqueur!r}")
        deb = round(max(0.0, deb + marge), 2)
        fin = None
    lignes.append({"ecran": ecran, "fichier": fichier, "start": deb, "end": fin})

# les fins : soit la fin de la video, soit le debut du bloc suivant
for i, l in enumerate(lignes):
    if l["end"] is not None:
        continue
    fin = ou_fin(FINS[l["fichier"]]) if l["fichier"] in FINS else None
    l["end"] = round(fin - 0.4, 2) if fin is not None else duree
    if l["end"] <= l["start"]:
        raise SystemExit(f"timing incoherent pour {l['fichier']} : {l['start']} -> {l['end']}")

# controle de securite : aucune incrustation au-dela de l'audio, aucun chevauchement
for l in lignes:
    if l["end"] > duree:
        raise SystemExit(f"{l['fichier']} depasse l'audio ({l['end']} > {duree})")
tri = sorted(lignes, key=lambda x: x["start"])
for a, b in zip(tri, tri[1:]):
    if b["start"] < a["end"]:
        raise SystemExit(f"chevauchement : {a['fichier']} et {b['fichier']}")

json.dump(lignes, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

print(f"\n{'incrustation':52s} {'debut':>8s} {'fin':>8s} {'duree':>7s}")
total = 0.0
for l in lignes:
    total += l["end"] - l["start"]
    print(f"{l['fichier']:52s} {l['start']:8.2f} {l['end']:8.2f} {l['end']-l['start']:6.1f}s")
print(f"\nsomme des durees : {total:.2f} s  /  audio : {duree:.2f} s  "
      f"(marge {duree-total:.2f} s)")
print(f"ecrit : {OUT}")
