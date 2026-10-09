---
name: youtube-captions-shorts
description: "Use when cutting captions or Shorts from a voice timeline."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [video, sous-titres, srt, vtt, shorts, youtube, ffmpeg, tts, timeline]
    category: media
    related_skills: [video-pipeline-complet, video-assembly, video-editing-automation]
---

# Sous-titres et Shorts depuis une timeline voix/vidéo

Classe de tâche : à partir d'une voix générée segment par segment (Chatterbox, XTTS) et d'une
vidéo qui la porte, produire des sous-titres synchronisés (.srt/.vtt) et découper des Shorts
verticaux 9:16 avec leur packaging YouTube (titre, description, hashtags, tags).

## When to Use

- Générer un .srt / .vtt synchronisé à partir de segments audio déjà générés.
- Découper des Shorts verticaux 9:16 dans une vidéo existante et produire leur packaging.
- Recalculer une timeline à partir de segments TTS dont les durées ne collent pas à l'audio.
- Tout travail de sous-titrage / packaging YouTube sur une vidéo à voix générée ; pour l'audit
  ou la lecture des métadonnées d'une chaîne, voir `social-media/youtube-data-api`.

## Règles toujours actives

- **Règle 0 — lecture seule, aucune publication.** Ne rien uploader, ne rien modifier côté
  YouTube. Terminer le rapport par « aucune modification côté YouTube, aucun upload ».
- **Règle 1 — ne jamais faire confiance au fichier de segments que l'utilisateur nomme.**
  Mesurer la durée réelle de l'audio (`ffprobe -show_entries format=duration`) puis comparer à la
  somme des `duree_s` de CHAQUE `segments_generation*.json` présent. Retenir la génération dont la
  somme colle à l'audio (~0,01 s près). Le fichier nommé est souvent une version obsolète : mesure
  typique, un v1 sommait 1150,88 s pour un audio de 859,88 s alors qu'un v3 collait exactement. Si
  aucun ne colle, le signaler et demander confirmation AVANT de continuer.
- **Règle 2 — timeline par ancres, pas par cumul naïf.** Quand un fichier d'alignement
  (`timestamp_align_*.json`, ancres `idx` -> `debut_s`) existe, s'en servir pour verrouiller les
  débuts de chapitres, puis répartir les durées DANS chaque intervalle proportionnellement aux
  durées d'origine. Un cumul direct sur un fichier non calé décale toute la fin de la vidéo.
- **Règle 3 — sous-titres en français STANDARD, jamais la graphie phonétique.** Le script de
  synthèse est écrit pour la prononciation (`R T X`, `Axi`, `C D Projekt Red`,
  `mille quatre cent quarante p`) ; le spectateur lit l'inverse. Convertir AVANT la découpe
  (tableau dans `references/timeline-et-sous-titres.md`).
- **Règle 4 — découpe des sous-titres.** 42 caractères max par ligne, 2 lignes max, frontières de
  phrase respectées, durée répartie au prorata du nombre de caractères de chaque unité. UTF-8 sans
  BOM. Dernier timestamp ≈ durée du Short.
- **Règle 5 — packaging YouTube.** Titre ≤ 60 caractères avec hook (question, chiffre, affirmation
  forte) ; description ≤ 200 caractères avec 3-5 hashtags ; 3 tags par ordre de pertinence
  décroissante.
- **Règle 6 — autonomie des Shorts.** Chaque fenêtre commence par un hook dans les 3 premières
  secondes (jamais « bonjour », jamais une transition), se termine sur une conclusion ou une
  question ouverte, dure 45-60 s. Quand plusieurs Shorts sont demandés, couvrir des angles
  DIFFÉRENTS (ex. punchline + conseil pratique + révélation), pas trois fois le même sujet.
- **Règle 7 — mesurer et rapporter les écarts, jamais les lisser.** Durée de segments ≠ durée
  audio, Short sous la cible 45 s, résolution upscalée : tout écart se dit explicitement dans le
  rapport avec la valeur mesurée.

## Procédure

1. **Mesurer l'audio** :
   `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 <wav>`.
2. **Choisir la génération de segments** qui colle (règle 1), associer le texte (le fichier
   `segments_v*.json` porte le champ `texte`), construire la timeline (règle 2).
3. **Standardiser le texte** (règle 3) puis découper en unités de sous-titre (règle 4).
4. **Écrire le .srt** (et .vtt) dans le dossier de sortie demandé.
5. **Shorts** : sélectionner les fenêtres sur la timeline, extraire audio + avatar + vidéo,
   recadrer en 9:16 (commandes : `references/shorts-extraction-4k.md`).
6. **Packaging** : titre/description/hashtags/tags, `metadata.json` par Short, CSV récapitulatif.
7. **Rapport final** : tableau (id | timecode | critère | titre | durée | résolution | taille),
   chemins complets, ordre de publication recommandé, écarts.

## Pitfalls

- **Un encodage 4K `-preset slow -crf 16` dépasse le timeout d'`execute_code` (~5 min) et le
  kernel est tué.** Lancer ffmpeg via `terminal` en `background=true` + `notify`, puis suivre avec
  `process_manage` (poll/wait). Un Short de 45 s met ~8 min à s'encoder seul.
- **Ne jamais lancer plusieurs encodages ffmpeg lourds en parallèle.** Ils se disputent le CPU et
  le débit s'effondre (mesure : ~0,17x en solo contre ~0,07x à trois de front). Les enchaîner.
- **Le crop 9:16 d'une source 4K horizontale n'est pas natif.** `crop=ih*9/16:ih` sur du 3840x2160
  donne 1215x2160 ; le `scale` vers 2160x3840 est un upscale ×1,78. Le dire quand l'utilisateur
  croit produire du 4K vertical natif.
- **ffmpeg natif Windows lit `C:/...`, pas `/c/...`** (MSYS) : un chemin MSYS donne « No such file
  or directory » sur un fichier qui existe. Vaut aussi pour les scripts ffmpeg internes.
- **Ne pas laisser traîner les brouillons.** Quand l'utilisateur réduit le nombre de Shorts
  (« exactement N »), archiver les dossiers obsolètes avant de livrer, sinon le dossier de sortie
  ne contient pas le compte demandé.

## Vérification

- Dernier timestamp du .srt ≈ durée du fichier vertical.
- `ffprobe` : 2160x3840, h264, yuv420p, durée et débit dans la cible.
- Titres ≤ 60, descriptions ≤ 200, nombre de Shorts = nombre demandé.
- Écarts (durées, chevauchements, upscales) listés dans le rapport.

## Fichiers

- `references/timeline-et-sous-titres.md` — réconciliation segments/audio, ancres, découpe,
  tableau phonétique → standard, format SRT/VTT.
- `references/shorts-extraction-4k.md` — commandes ffmpeg d'extraction et de recadrage 9:16, math
  du crop 4K, exécution longue (background + poll), champs de packaging.

## Cross-references

- `video-pipeline-complet` — amont : script, voix, synchro, assemblage.
- `media/video-assembly`, `media/video-editing-automation` — montage/assemblage ffmpeg.
- `social-media/youtube-data-api` — lecture/audit de la chaîne (clé API), pas la production.
