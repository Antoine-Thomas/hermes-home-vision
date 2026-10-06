---
name: video-fidelity-metrics
description: "Mesurer la netteté d'une sortie talking-head vs source."
version: "1.0.0"
author: Searching Murphy
license: MIT
tags:
  - video
  - talking-head
  - metrics
  - laplacian
  - psnr
  - comparison
---

# video-fidelity-metrics

Mesure objective de la netteté d'une sortie talking-head vs sa source.
Méthode Laplacien + PSNR invariance 512 + contrôle alignement fond, avec
scripts réutilisables attachés.

## Quand utiliser ce skill

- tester un nouveau modèle talking-head (VideoReTalking, LatentSync,
  Wav2Lip, SadTalker, etc.) avant de l'adopter
- vérifier qu'une correction de pipeline (compositing, resize, blending)
  a bien amélioré la netteté
- décider si une sortie est utilisable pour un montage final 1080p

## MÉTHODE STANDARD

PRINCIPE
On ne mesure PAS l'articulation labiale (pas de métrique fiable). On
mesure la NETTETÉ, en comparant 3 zones contre la source.

ZONES (sur frame SOURCE, détection insightface buffalo_l) :
- visage entier : bbox de la plus grande détection
- bouche       : landmarks 52-71 → bbox
- bande basse  : moitié inférieure du visage
- fond         : bande latérale hors visage (x1-250, x1-30) → (y1, y2)
- frames test standard : 60, 150, 245

MÉTRIQUES
1. Variance du Laplacien (CV_32F sur image grise) dans chaque zone.
   Valeur en % de la source.
2. PSNR d'invariance 512 :
   r = cv2.resize(cv2.resize(frame, (512,512)), (w, h))
   psnr(frame, r)
   ~40 dB = détail 1080p réel préservé
   ~51 dB = l'image ne contient plus rien au-delà de 512x512
3. Contrôle alignement fond (3 px) : chercher (dx, dy) qui minimise
   l'écart absolu moyen sur la bande de fond. Si le meilleur n'est pas
   (0,0), la comparaison n'est PAS valable sans correction → signaler.

SCRIPTS DE RÉFÉRENCE (dossier scripts/ du skill) :
- _mesure_comp.py     mesure générique + planche comparative multi-vidéos
- _diag_vr.py         diagnostic de flou (source / brut / mux)
- _diag_r256.py       étalon résolution intrinsèque (SIM visage 256/384/512)
- _diag_enc.py        isole l'effet de l'encodage final (qv1 vs crf10)
- _comparaison_vr.py  planche côte-à-côte 3 colonnes
- _montage_explicatif.py  montage animé (voir la section suivante)

Copie de travail d'origine de ces 5 scripts :
C:\Users\searc\Desktop\ANIMA\_work_2c\latentsync\_archive_VR\
(_montage_explicatif.py, écrit plus tard, a pour copie de travail :
C:\Users\searc\Desktop\ANIMA\_work_2c\latentsync\_montage_explicatif.py)

## Générer un montage explicatif animé

_montage_explicatif.py produit un montage 1920x720 (3 colonnes SOURCE | LatentSync A2.0 | VideoReTalking) où la variance du Laplacien de la zone bouche est recalculée à chaque frame et affichée sous chaque colonne, avec zoom bouche x3 NEAREST et l'audio d'origine.
Détection insightface sur CPU uniquement (~0,6 s/frame, bbox mise en cache dans `_montage_bbox.npz` à côté du script) : aucun calcul GPU ; les frames composites sont écrites en PNG puis assemblées par ffmpeg (h264 crf 18 + AAC 192k, 250 frames = 10,000 s à 25 fps).
Exemple : `<venv LatentSync>/Scripts/python.exe _montage_explicatif.py --n 250 --sortie ...\ANIMA_montage_VR_explicatif.mp4`
Un rapport JSON `<sortie>_mesures.json` garde les valeurs affichées aux frames 0/150/249 ; si un clip est plus court que --n (ex. VideoReTalking, 248 frames), la dernière image est répétée et listée dans `frames_tenues`.


DÉPENDANCES : numpy, opencv-python, insightface (buffalo_l), un module
_greffe_hf.py fournissant lire(), app_face(), plus_grand(), fenetre_levres().
→ Si _greffe_hf n'est pas dispo, la méthode se réimplémente en 30 lignes.

CRITÈRE DE DÉCISION
Un modèle est considéré « utilisable pour bouche fidèle » si :
bouche ≥ 60 % de la source ET visage ≥ 90 % ET PSNR512 ≥ 42 dB
LatentSync A2.0 passe (67 %, 98 %, 40,6-41,5 dB).
VideoReTalking échoue (5-13 %, 3-11 %, 46-51 dB).
