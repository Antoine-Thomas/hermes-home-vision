# -*- coding: utf-8 -*-
"""Audit d'un corpus de voix reelle : inventaire, qualite, verdict par rapport aux seuils XTTS.

    "<venv XTTS>\\python.exe" audit_voix.py "C:\\Users\\searc\\Desktop\\ma voix 12"

Lecture SEULE : le dossier d'entree n'est jamais modifie, aucun fichier n'est deplace ni copie.
L'analyse se fait en flux (blocs de 30 s) pour ne pas charger 1,7 Go en memoire.

Mesures par fichier :
  - format, frequence, canaux, profondeur, duree, taille
  - niveau : RMS par bloc, crete ; pourcentage de voix utile, de silence, de bruit
  - saturation : echantillons |x| >= 0,99 et longueur des series consecutives
  - rapport signal/bruit estime : plancher de bruit (10e centile des blocs) contre niveau de
    parole (90e centile)
  - couleur spectrale sur quelques fenetres : aplatissement (flatness) et centroide, pour
    reperer un fond musical ou un bourdonnement continu
  - hauteur (F0) sur quelques fenetres : un ecart enorme signale un autre locuteur possible
"""
import io
import json
import os
import sys

import numpy as np
import soundfile as sf

BLOC = 30.0            # secondes par bloc d'analyse
SEUIL_SILENCE = -45.0  # dBFS en dessous duquel un bloc est considere silencieux
SEUIL_CRETE = 0.99


def db(x):
    return 20.0 * np.log10(max(float(x), 1e-12))


def analyser(chemin):
    info = sf.info(chemin)
    sr, canaux, duree = info.samplerate, info.channels, info.frames / info.samplerate
    taille = os.path.getsize(chemin)
    n_bloc = int(BLOC * sr)
    rms_db, saturations, series, maxi = [], 0, [], 0.0
    echantillons = 0
    silencieux = 0
    fenetres = []

    with sf.SoundFile(chemin) as f:
        while True:
            bloc = f.read(n_bloc, dtype="float32", always_2d=True)
            if bloc.size == 0:
                break
            mono = bloc.mean(axis=1)
            rms = float(np.sqrt(np.mean(mono ** 2)))
            rms_db.append(db(rms))
            crete = float(np.max(np.abs(bloc)))
            maxi = max(maxi, crete)
            echantillons += mono.size
            if rms < 10 ** (SEUIL_SILENCE / 20.0):
                silencieux += mono.size
            haut = np.abs(mono) >= SEUIL_CRETE
            saturations += int(haut.sum())
            # series consecutives de saturation
            idx = np.flatnonzero(haut)
            if idx.size:
                coupures = np.flatnonzero(np.diff(idx) > 1)
                debuts = np.concatenate(([0], coupures + 1))
                fins = np.concatenate((coupures, [idx.size - 1]))
                series.extend((idx[fins] - idx[debuts] + 1).tolist())
            if 3 <= len(rms_db) <= 9:      # 4 fenetres reparties (90 s a 270 s)
                fenetres.append(mono[: 10 * sr].copy())

    niveaux = np.array(rms_db)
    return {"chemin": os.path.basename(chemin), "format": info.format, "sous_type": info.subtype,
            "frequence": sr, "canaux": canaux, "duree_s": round(duree, 1),
            "duree": "%d min %02d s" % (duree // 60, duree % 60),
            "taille_mo": round(taille / 1e6, 1),
            "rms_median_db": round(float(np.median(niveaux)), 1),
            "crete_max": round(maxi, 4),
            "crete_db": round(db(maxi), 2),
            "plancher_bruit_db": round(float(np.percentile(niveaux, 10)), 1),
            "niveau_parole_db": round(float(np.percentile(niveaux, 90)), 1),
            "snr_estime_db": round(float(np.percentile(niveaux, 90) - np.percentile(niveaux, 10)), 1),
            "part_silence_pct": round(100.0 * silencieux / max(echantillons, 1), 1),
            "echantillons_satures": saturations,
            "part_saturee_pct": round(100.0 * saturations / max(echantillons, 1), 4),
            "serie_saturation_max": int(max(series)) if series else 0,
            "_fenetres": fenetres, "_sr": sr}


def couleur_spectrale(fenetres, sr):
    """Aplatissement et centroide moyens : signalent un fond musical ou un bourdonnement."""
    import librosa
    aplats, centroides, f0 = [], [], []
    for w in fenetres:
        if w.size < sr:
            continue
        aplat = librosa.feature.spectral_flatness(y=w.astype("float32"))
        cent = librosa.feature.spectral_centroid(y=w.astype("float32"), sr=sr)
        aplats.append(float(np.mean(aplat)))
        centroides.append(float(np.mean(cent)))
        try:
            f = librosa.yin(w.astype("float32"), fmin=70, fmax=350, sr=sr)
            f = f[np.isfinite(f)]
            if f.size:
                f0.append(float(np.median(f)))
        except Exception:
            pass
    out = {}
    if aplats:
        out["aplatissement_moyen"] = round(float(np.mean(aplats)), 4)
        out["centroide_moyen_hz"] = round(float(np.mean(centroides)), 0)
    if f0:
        out["f0_mediane_hz"] = round(float(np.median(f0)), 1)
        out["f0_min_hz"] = round(float(np.min(f0)), 1)
        out["f0_max_hz"] = round(float(np.max(f0)), 1)
    return out


if __name__ == "__main__":
    dossier = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\searc\Desktop\ma voix 12"
    extensions = (".wav", ".mp3", ".m4a", ".flac", ".mp4", ".mov", ".mkv")
    fichiers = sorted(os.path.join(dossier, f) for f in os.listdir(dossier)
                      if f.lower().endswith(extensions))
    if not fichiers:
        raise SystemExit("aucun fichier audio ou video dans %s" % dossier)

    resultats = []
    for chemin in fichiers:
        print("analyse de %s ..." % os.path.basename(chemin), flush=True)
        r = analyser(chemin)
        fenetres = r.pop("_fenetres")
        sr = r.pop("_sr")
        try:
            r.update(couleur_spectrale(fenetres, sr))
        except Exception as e:
            r["couleur_spectrale"] = "non mesuree (%s)" % e
        resultats.append(r)

    total = sum(r["duree_s"] for r in resultats)
    utile = sum(r["duree_s"] * (100 - r["part_silence_pct"]) / 100.0 for r in resultats)
    bilan = {"dossier": dossier, "fichiers": len(resultats),
             "duree_totale_s": round(total, 1),
             "duree_totale": "%d h %02d min" % (total // 3600, (total % 3600) // 60),
             "duree_utile_s": round(utile, 1),
             "duree_utile": "%d h %02d min" % (utile // 3600, (utile % 3600) // 60),
             "detail": resultats}
    print(json.dumps(bilan, ensure_ascii=False, indent=1, default=str))
    sortie = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_voix.json")
    io.open(sortie, "w", encoding="utf-8").write(json.dumps(bilan, ensure_ascii=False, indent=1,
                                                            default=str) + "\n")
    print("resultat ecrit : %s" % sortie)
