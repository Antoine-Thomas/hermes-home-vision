---
name: ffmpeg-video-mux-rescue
description: Use when a video pipeline crashed at the final mux step.
version: "1.0.0"
author: Searching Murphy
license: MIT
tags:
  - ffmpeg
  - ffprobe
  - mux
  - remux
  - videoretalking
  - latentsync
  - wav2lip
  - crash-recovery
---

# ffmpeg-video-mux-rescue

Récupérer une vidéo dont le pipeline a planté en fin de run (dernière étape
écriture/mux), remuxer audio+vidéo proprement, préserver la qualité, sans
relancer le calcul lourd.

## Quand utiliser ce skill

Quand un pipeline vidéo (VideoReTalking, LatentSync, Wav2Lip, SadTalker…) a
planté APRÈS la génération des frames (dernière étape écriture/mux) et que le
fichier brut est encore présent sur disque : on remuxe au lieu de relancer
plusieurs heures de GPU.

--- PRINCIPE ---

De nombreux pipelines vidéo (VideoReTalking, LatentSync, Wav2Lip, etc.)
écrivent d'abord les frames dans un fichier brut (souvent .mp4 mpeg4 ou
.avi), PUIS font un mux audio+vidéo en fin de run via ffmpeg.

Si le run plante juste avant/au moment du mux, le fichier brut est intact
et complet. On peut faire le mux manuellement en quelques secondes au lieu
de relancer plusieurs heures de GPU.

--- DIAGNOSTIC : le résultat brut existe-t-il ? ---

Chercher dans le dossier de travail (souvent temp/ ou output/) :
  - result.mp4, out.mp4, result.avi, temp.mp4
  - fichiers avec la bonne durée attendue et la bonne résolution
  - fichier sans audio (le mux n'a pas eu lieu)

Commande de vérification :
  ffprobe -v error -show_entries stream=codec_name,width,height,nb_frames \
          -show_entries format=duration,size -of default=noprint_wrappers=1 \
          chemin/result.mp4

Si nb_frames correspond à la durée attendue × fps le brut est bon.

--- COMMANDE DE MUX (générique) ---

Cas 1 — VideoReTalking (mux avec -q:v 1, cf. inference.py ligne 273) :
  ffmpeg -y -i temp/temp/result.mp4 -i audio.wav \
         -c:v libx264 -q:v 1 -c:a aac -b:a 192k -ar 16000 -ac 1 \
         -strict -2 -shortest sortie.mp4

Cas 2 — Qualité maximale sans ré-encodage vidéo (si le brut est déjà h264) :
  ffmpeg -y -i brut.mp4 -i audio.wav -c:v copy -c:a aac -b:a 192k \
         -shortest sortie.mp4

Cas 3 — Le brut est en mpeg4 (VideoWriter OpenCV par défaut) :
  ffmpeg -y -i brut.mp4 -i audio.wav -c:v libx264 -crf 10 -preset medium \
         -c:a aac -b:a 192k -shortest sortie.mp4

Cas 4 — Audio déjà muxé mais vidéo floue (bug compositing) :
  Ne pas remuxer, corriger le pipeline en amont (voir skills
talking-head-video-8gb et video-fidelity-metrics).

--- PIÈGES CONNUS ---

1. -q:v 1 n'est PAS du CRF — c'est l'échelle qscale (1 = meilleure qualité,
   ~2,2 Mbit/s pour du 1080p en pratique). Si la qualité importe plus que
   la taille, préférer -crf 10 à -q:v 1.

2. -shortest est indispensable : sans lui, ffmpeg garde le flux le plus
   long et le résultat peut avoir une piste audio/vidéo muette à la fin.

3. -ar 16000 -ac 1 : forcer le format audio attendu par le pipeline en
   amont. VideoReTalking sort en 16 kHz mono, LatentSync aussi.

4. Ne PAS utiliser -c:v copy si le brut est en mpeg4 — le conteneur final
   sera mpeg4, pas h264. Toujours ré-encoder dans ce cas.

5. Le fichier de sortie doit avoir un RÉPERTOIRE explicite (results/out.mp4
   et pas out.mp4) — sinon certains pipelines plantent sur
   os.makedirs(os.path.dirname('')) (cf. VideoReTalking WinError 3).

--- VÉRIFICATION POST-MUX ---

  ffprobe -v error -show_entries stream=codec_type,codec_name,duration,nb_frames \
          -show_entries format=duration,size,bit_rate \
          -of default=noprint_wrappers=1 sortie.mp4

Attendu :
  - 1 stream video (h264) + 1 stream audio (aac)
  - durée vidéo ≈ durée audio ≈ durée attendue
  - bit_rate cohérent avec le mode utilisé

Contrôle visuel rapide :
  ffmpeg -v error -i sortie.mp4 -vf "select=eq(n\,150)" -vframes 1 frame150.png
  → comparer à la source sur la frame 150 avec la méthode du skill
     video-fidelity-metrics

--- EXEMPLE RÉEL (session VR du 2026-10-05) ---

Situation : VideoReTalking a tourné 592 s, a planté à la dernière ligne
(makedirs('')), mais temp/temp/result.mp4 contenait 248 images en mpeg4
1920x1080.

Récupération : mux manuel avec la commande exacte de inference.py:273,
soit :
  ffmpeg -y -i temp/temp/result.mp4 -i _test_vr_aud.wav \
         -c:v libx264 -q:v 1 -c:a aac -b:a 192k -ar 16000 -ac 1 \
         -strict -2 -shortest _test_vr_out.mp4

Résultat : 1920x1080, 248 images, 10,048 s, h264+AAC 16 kHz, 2,86 Mo.
Temps : 5 secondes au lieu de 592 s de GPU.
