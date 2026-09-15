# -*- coding: utf-8 -*-
"""Etape A de l'essai XTTS : extraire 10 minutes de voix propre depuis ZOOM0005.WAV.

    "<venv XTTS>\\python.exe" extraire_corpus_test.py

Regle de selection d'un segment de 12 s :
  - 70 % au moins de ses fenetres de 0,5 s sont dans la bande utile (-32 a -14 dBFS) :
    les pauses courtes de la parole sont donc tolerees ;
  - aucune fenetre saturee (|x| >= 0,99) : pas d'attaque de consonne ecrasee ;
  - aucun silence long : au plus 1 s (2 fenetres) sous -45 dBFS d'affilee.

Puis : 50 segments d'entrainement (10 minutes) etalees sur tout le fichier + 5 segments de
validation (1 minute) mis de cote. Sortie en MONO 22 050 Hz (frequence attendue par XTTS v2),
transcription par Whisper (le fine-tune a besoin du texte).

Le fichier source est ouvert en lecture seule : rien n'est ecrit dans « ma voix 12 ».
"""
import io
import json
import os
import subprocess

import numpy as np
import soundfile as sf

SOURCE = r"C:\Users\searc\Desktop\ma voix 12\ZOOM0005.WAV"
DESTINATION = r"C:\Users\searc\AppData\Local\hermes\data\xtts\corpus_test"
SR_CIBLE = 22050
DUREE_SEGMENT = 12.0
PAS_SELECTION = 3.0
NB_ENTRAINEMENT = 50
NB_VALIDATION = 5
FENETRE = 0.5
RMS_MIN, RMS_MAX = -32.0, -14.0
SEUIL_SILENCE_DB = -45.0
SILENCE_MAX_FENETRES = 2          # 1 s : au-dela, c'est un silence long
PART_MIN_UTILE = 0.70
SEUIL_SATURATION = 0.99
VENV_WHISPER = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "data", "video_youtube",
                            "echomimic_v2", "venv", "Scripts", "python.exe")
MODELE_WHISPER = os.environ.get("WHISPER_MODELE", "medium")


def db(x):
    return 20.0 * np.log10(max(float(x), 1e-12))


def annonter(chemin):
    """Rend (liste (rms_db, sature) par fenetre, frequence, duree totale)."""
    info = sf.info(chemin)
    sr = info.samplerate
    n = int(FENETRE * sr)
    fenetres = []
    with sf.SoundFile(chemin) as f:
        while True:
            bloc = f.read(n, dtype="float32", always_2d=True)
            if bloc.size == 0:
                break
            mono = bloc.mean(axis=1)
            fenetres.append((db(np.sqrt(np.mean(mono ** 2))),
                             bool((np.abs(bloc) >= SEUIL_SATURATION).any())))
    return fenetres, sr, info


def score(fenetres, debut, longueur):
    tranche = fenetres[debut:debut + longueur]
    if len(tranche) < longueur:
        return None
    if any(s for _, s in tranche):
        return None                                   # saturation : ecarte
    utiles = sum(1 for r, _ in tranche if RMS_MIN <= r <= RMS_MAX)
    if utiles / float(longueur) < PART_MIN_UTILE:
        return None                                   # trop de silence ou trop faible
    suite = maxi = 0
    for r, _ in tranche:
        if r < SEUIL_SILENCE_DB:
            suite += 1
            maxi = max(maxi, suite)
        else:
            suite = 0
    if maxi > SILENCE_MAX_FENETRES:
        return None                                   # silence long
    return utiles / float(longueur)


if __name__ == "__main__":
    os.makedirs(os.path.join(DESTINATION, "wavs"), exist_ok=True)
    os.makedirs(os.path.join(DESTINATION, "validation"), exist_ok=True)

    print("balayage de %s ..." % os.path.basename(SOURCE), flush=True)
    fenetres, sr, info = annonter(SOURCE)
    print("  %d fenetres de 0,5 s | source %d Hz, %d canal(aux), %s"
          % (len(fenetres), sr, info.channels, info.subtype), flush=True)

    longueur = int(round(DUREE_SEGMENT / FENETRE))
    pas = int(round(PAS_SELECTION / FENETRE))
    candidats = []
    for debut in range(0, len(fenetres) - longueur, pas):
        s = score(fenetres, debut, longueur)
        if s is not None:
            candidats.append((debut, s))
    print("  %d fenetres de 12 s acceptees sur %d examinees"
          % (len(candidats), len(range(0, max(1, len(fenetres) - longueur), pas))), flush=True)

    besoin = NB_ENTRAINEMENT + NB_VALIDATION
    if len(candidats) < besoin:
        print("  ATTENTION : %d segments seulement, moins que les %d demandes"
              % (len(candidats), besoin), flush=True)
    # ecarter les bords, puis etaler sur tout le fichier pour varier les intonations
    candidats = candidats[2:-2] if len(candidats) > besoin + 4 else candidats
    if len(candidats) > besoin:
        step = len(candidats) / float(besoin)
        candidats = [candidats[int(i * step)] for i in range(besoin)]

    donnes = []
    with sf.SoundFile(SOURCE) as f:
        for rang, (debut, _) in enumerate(candidats):
            f.seek(int(debut * FENETRE * sr))
            bloc = f.read(int(DUREE_SEGMENT * sr), dtype="float32", always_2d=True)
            if bloc.size == 0:
                continue
            import librosa
            mono = librosa.resample(bloc.mean(axis=1), orig_sr=sr, target_sr=SR_CIBLE)
            validation = rang >= NB_ENTRAINEMENT
            sous = "validation" if validation else "wavs"
            nom = "%s_%03d.wav" % ("val" if validation else "seg", rang)
            sf.write(os.path.join(DESTINATION, sous, nom),
                     mono / max(1e-6, float(np.max(np.abs(mono)))) * 0.95, SR_CIBLE,
                     subtype="PCM_16")
            donnes.append({"fichier": os.path.join(sous, nom),
                           "debut_s": round(debut * FENETRE, 1),
                           "duree_s": round(len(mono) / SR_CIBLE, 2),
                           "validation": validation})
    print("  %d WAV ecrits en %d Hz mono (dont %d de validation)"
          % (len(donnes), SR_CIBLE, sum(1 for d in donnes if d["validation"])), flush=True)

    io.open(os.path.join(DESTINATION, "segments.json"), "w", encoding="utf-8").write(
        json.dumps(donnes, ensure_ascii=False, indent=1))

    if os.path.exists(VENV_WHISPER):
        script = os.path.join(DESTINATION, "_transcrire.py")
        io.open(script, "w", encoding="utf-8").write(
            "import io, json, os, whisper\n"
            "racine = r'%s'\n"
            "modele = whisper.load_model(r'%s')\n"
            "donnees = json.load(io.open(os.path.join(racine, 'segments.json'), encoding='utf-8'))\n"
            "for d in donnees:\n"
            "    r = modele.transcribe(os.path.join(racine, d['fichier']), language='fr', fp16=True)\n"
            "    d['texte'] = r['text'].strip()\n"
            "    print(d['fichier'], '->', d['texte'][:70], flush=True)\n"
            "io.open(os.path.join(racine, 'segments.json'), 'w', encoding='utf-8').write(\n"
            "    json.dumps(donnees, ensure_ascii=False, indent=1))\n" % (DESTINATION, MODELE_WHISPER))
        print("transcription Whisper (%s) ..." % MODELE_WHISPER, flush=True)
        r = subprocess.run([VENV_WHISPER, script], capture_output=True, text=True)
        print((r.stdout or "")[-600:], flush=True)
        if r.returncode != 0:
            print("transcription en echec : %s" % (r.stderr or "")[-300:], flush=True)

    donnees = json.load(io.open(os.path.join(DESTINATION, "segments.json"), encoding="utf-8"))
    for cible, marque in (("train", False), ("validation", True)):
        lignes = ["%s|%s|%s" % (os.path.splitext(os.path.basename(d["fichier"]))[0],
                                d.get("texte", ""), d.get("texte", ""))
                  for d in donnees if d["validation"] == marque and d.get("texte")]
        if lignes:
            io.open(os.path.join(DESTINATION, "metadata_%s.csv" % cible), "w",
                    encoding="utf-8", newline="\n").write("\n".join(lignes) + "\n")
    ent = sum(d["duree_s"] for d in donnees if not d["validation"])
    val = sum(d["duree_s"] for d in donnees if d["validation"])
    print("corpus pret : %.1f min d'entrainement + %.1f min de validation"
          % (ent / 60.0, val / 60.0), flush=True)
