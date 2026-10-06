#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Controler une sortie de tete parlante (MuseTalk / LatentSync) SANS regarder l'image.

Quatre mesures, dans l'ordre ou elles tranchent :

 1. conteneur : duree, fps, nombre d'images, resolution, codecs, debit (ffprobe).
 2. images figees : difference moyenne entre images consecutives (ffmpeg tblend +
    signalstats), sur la sortie ET sur le pilote. Compter les paires sous 0,05 (0-255).
    Un ralenti garde forcement quelques paires quasi identiques : le critere se juge sur
    la SORTIE, ou la bouche regeneree rend chaque image unique.
 3. glissement audio : l'audio de la sortie est-il celui de la source, au meme instant ?
    balayage +-200 ms sur le PCM decode, correlation maximale attendue au decalage 0.
 4. synchro labiale : correlation PIXEL PAR PIXEL entre la variation d'une image a l'autre
    et l'enveloppe audio a 25 Hz. La bouche se designe elle-meme (les pixels les plus
    correles forment un amas compact) et son maximum doit tomber au decalage 0. Controle
    obligatoire : la meme mesure avec l'audio decale de +10 s doit s'effondrer.

Usage :
  qa_tete_parlante.py SORTIE.mp4 [--pilote PILOTE.mp4] [--audio SOURCE.wav]
                                 [--debut 60] [--duree 40] [--json rapport.json]

Sans dependance a un modele de vision. Toutes les mesures sont numeriques ; regarder une
image reste utile pour confirmer, jamais pour arbitrer (regle « le Laplacien seul peut
mentir »).
"""
import argparse, json, os, re, subprocess, sys, wave
import numpy as np

FPS = 25            # cadence d'analyse ; la sortie doit etre a ce fps ou a un multiple
L, H = 240, 135     # resolution d'analyse de la correlation pixel/enveloppe
SEUIL_FIGEE = 0.05  # difference moyenne (0-255) sous laquelle deux images sont dites identiques
SEUIL_BOUCHE = 0.10 # correlation minimale du meilleur pixel pour conclure a une synchro


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def conteneur(video):
    v = sh('ffprobe -v error -show_entries stream=index,codec_type,codec_name,width,height,'
           'r_frame_rate,nb_frames,duration,sample_rate,channels -of default=nw=1 "%s"' % video)
    f = sh('ffprobe -v error -show_entries format=duration,size,bit_rate -of default=nw=1 "%s"' % video)
    return v.strip(), f.strip()


def serie_diff(video, crop=None):
    """difference moyenne entre images consecutives (YAVG), une valeur par image."""
    f = ("tblend=all_mode=difference,signalstats,"
         "metadata=print:key=lavfi.signalstats.YAVG:file=-")
    if crop:
        f = crop + "," + f
    out = sh('ffmpeg -v error -i "%s" -vf "%s" -an -f null -' % (video, f))
    d = np.array([float(m) for m in re.findall(r"lavfi\.signalstats\.YAVG=([0-9.]+)", out)])
    return d[1:] if len(d) else d  # la 1re valeur n'a pas d'image precedente


def gris(video, t0, d):
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-t", str(d), "-i", video,
                        "-vf", "scale=%d:%d,format=gray" % (L, H), "-an", "-f", "rawvideo", "-"],
                       capture_output=True).stdout
    n = len(b) // (L * H)
    return np.frombuffer(b[:n * L * H], dtype=np.uint8).reshape(n, H, L).astype(np.float32)


def pcm(video):
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-f", "s16le",
                        "-ac", "1", "-ar", "16000", "-"], capture_output=True).stdout
    return np.frombuffer(b, dtype=np.int16).astype(np.float32) / 32768.0


def enveloppe(x, sr=16000, fps=FPS):
    n = sr // fps
    k = len(x) // n
    return np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(1)) if k else np.zeros(0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("sortie")
    p.add_argument("--pilote", default=None, help="video de conduite, pour comparer les images figees")
    p.add_argument("--audio", default=None, help="WAV source, pour le controle de glissement")
    p.add_argument("--debut", type=float, default=60.0, help="debut de la fenetre de synchro (s)")
    p.add_argument("--duree", type=float, default=40.0, help="duree de la fenetre de synchro (s)")
    p.add_argument("--json", default=None)
    a = p.parse_args()
    verdicts = {}

    print("=== 1. CONTENEUR ===")
    v, f = conteneur(a.sortie)
    print(v)
    print(f)

    print("\n=== 2. IMAGES FIGEES (difference moyenne entre images consecutives, 0-255) ===")
    for lib, vid in (("sortie", a.sortie), ("pilote", a.pilote)):
        if not vid or not os.path.exists(vid):
            continue
        d = serie_diff(vid)
        if not len(d):
            continue
        fig = int((d < SEUIL_FIGEE).sum())
        print("   %-7s images=%d | moy=%.3f | med=%.3f | min=%.4f | paires<%s : %d (%.3f %%)"
              % (lib, len(d), d.mean(), np.median(d), d.min(), SEUIL_FIGEE, fig,
                 100.0 * fig / len(d)))
        verdicts["paires_figees_%s" % lib] = fig
    verdicts["images_figees_sortie"] = verdicts.get("paires_figees_sortie", 0)

    if a.audio and os.path.exists(a.audio):
        print("\n=== 3. GLISSEMENT AUDIO (sortie vs source, balayage +-200 ms) ===")
        xo = pcm(a.sortie)
        w = wave.open(a.audio, "rb")
        xs = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        sr = w.getframerate()
        w.close()
        print("   sortie %.3f s | source %.3f s @%d Hz" % (len(xo) / 16000.0, len(xs) / sr, sr))
        n = min(len(xo), len(xs))
        best, bl = -2.0, 0
        for ms in range(-200, 201, 2):
            d = int(ms * 16)
            x1 = xo[max(0, d):n + min(0, d)]
            x2 = xs[max(0, -d):n - max(0, d)]
            if len(x1) < 100:
                continue
            c = float(np.corrcoef(x1, x2)[0, 1])
            if c > best:
                best, bl = c, ms
        print("   correlation max %.4f au decalage %+d ms (0 ms = aucun glissement)" % (best, bl))
        verdicts["audio_corr"] = round(best, 4)
        verdicts["audio_decalage_ms"] = bl

    print("\n=== 4. SYNCHRO LABIALE (correlation pixel a pixel avec l'enveloppe audio) ===")
    F = gris(a.sortie, a.debut, a.duree)
    if len(F) < 50:
        print("   fenetre trop courte (%d images) : augmenter --duree" % len(F))
    else:
        M = np.abs(np.diff(F, axis=0)).reshape(len(F) - 1, -1)
        env = enveloppe(pcm(a.sortie))
        i0 = int(a.debut * FPS)
        e = env[i0:i0 + len(M)]
        k = min(len(e), len(M))
        M, e = M[:k], e[:k]

        def carte(e_):
            e_ = e_ - e_.mean()
            Mc = M - M.mean(0)
            return (e_ @ Mc) / np.maximum(np.linalg.norm(e_) * np.linalg.norm(Mc, axis=0), 1e-9)

        c = carte(e)
        idx = np.argsort(c)[::-1]
        top = [(int(i % L), int(i // L)) for i in idx[:8]]
        amas = (np.std([t[0] for t in top]), np.std([t[1] for t in top]))
        print("   %d images, %d pixels | max %+.3f | mediane %+.3f | p99 %+.3f | pixels>0,15 : %d"
              % (len(F), M.shape[1], c.max(), np.median(c), np.percentile(c, 99),
                 int((c > 0.15).sum())))
        print("   les 8 pixels les plus correles : %s" % " ".join("x%d,y%d" % t for t in top))
        print("   dispersion de l'amas : ecart-type x=%.1f y=%.1f (compact = une zone du visage)"
              % amas)
        p_ = int(idx[0])
        mp = M[:, p_] - M[:, p_].mean()
        lags = list(range(-50, 51))
        cc = [float(np.corrcoef(e, np.roll(mp, l))[0, 1]) for l in lags]
        bi = int(np.argmax(cc))
        print("   meilleur pixel : corr(0)=%+.3f | max %+.3f au decalage %+d image (%+0.2f s)"
              % (cc[50], cc[bi], bi - 50, (bi - 50) / float(FPS)))
        e2 = env[i0 + 10 * FPS:i0 + 10 * FPS + len(M)]
        if len(e2) == len(M):
            c2 = carte(e2)
            print("   CONTROLE +10 s : max %+.3f | pixels>0,15 : %d (doit s'effondrer)"
                  % (c2.max(), int((c2 > 0.15).sum())))
            verdicts["controle_10s_max"] = round(float(c2.max()), 4)
        verdicts["bouche_max"] = round(float(c.max()), 4)
        verdicts["bouche_mediane"] = round(float(np.median(c)), 4)
        verdicts["bouche_decalage_images"] = bi - 50
        verdicts["synchro_ok"] = bool(cc[50] >= SEUIL_BOUCHE and abs(bi - 50) <= 2)

    print("\n=== VERDICT ===")
    print(json.dumps(verdicts, ensure_ascii=False, indent=1))
    if a.json:
        json.dump(verdicts, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = verdicts.get("images_figees_sortie", 0) == 0 and verdicts.get("synchro_ok", True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
