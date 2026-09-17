---
name: video-pipeline-complet
description: "Orchestrer une vidéo complète : script, voix, synchro, QA."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [video, pipeline, orchestration]
---

# Video pipeline complet

## When to Use

Quand une video talking-head doit etre produite de bout en bout : preparation du script,
voix, synchronisation labiale, assemblage, controle qualite, livraison. Un seul point
d'entree pour les 6 etapes au lieu de les enchainer a la main.

## Quick Reference

```
Orchestre : tts-voice-cloning -> talking-head-video-8gb -> video-assembly
Reference : C:\Users\searc\Desktop\hermes_tuto_v4\pipeline_video.py
Branches  : talking-head-video-8gb (A=LatentSync, B=LivePortrait/SadTalker, C=LTX)
Sortie    : Desktop\hermes tuto\<nom>_FINAL.mp4
```

## Procedure

1. **Script** : preparer le texte, marquer les pauses, appliquer le lexique de diction.
2. **Voix** : `tts-voice-cloning` (XTTS venv `data\xtts\venv`) -> WAV de reference.
3. **Synchro** : `talking-head-video-8gb`, branche A (LatentSync) par defaut.
4. **Assemblage** : `video-assembly` (fond bois animes, logo Hermes en coin, CTA).
5. **QA** : mesurer nettete/laplacien, fantomes des levres (seuil 1,5x source), duree.
6. **Livraison** : copier vers le dossier final et notifier (Telegram).

## Pitfalls

- VRAM 8 Go : verifier qu'aucun autre process CUDA ne tourne avant le rendu (`nvidia-smi`).
- Ne jamais definir `PYTORCH_CUDA_ALLOC_CONF` (rend le rendu ~22x plus lent sur cette machine).
- Les chemins contenant des espaces doivent etre entre guillemets (les scripts ffmpeg internes n'en mettent pas).
- Une source 4K native bat une image restauree : privilegier la vraie prise de vue.

## Verification

- Le MP4 final existe, duree coherente, piste audio presente.
- Mesures QA sauvegardees (pas seulement l'absence d'erreur).
