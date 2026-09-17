---
name: record
description: "Enregistre video+audio 30-60s max avec voyant clignotant, respecte ESTOP, envoie par Telegram. Alternative legale au flux infini."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Record - enregistrement limite 30/60s

Enregistre webcam+micro pendant max 60s avec voyant. Respecte ESTOP.

## Quand utiliser

- /record, /record 30, /record 60, enregistrement court

## Quand NE PAS utiliser

- Duree >60s ou infini -> refuse, plafonne a 60s
- ESTOP actif -> refuse

## Fonctionnement

1. Verifie ESTOP comme /photo.
2. Parse duree: premier arg entier 5-60, defaut 30.
3. Voyant Tkinter rouge clignotant topmost pendant toute la duree.
4. Capture (ordre de repli):
   a. ffmpeg dshow `video=<webcam>:audio=<micro>` -> mp4 h264+aac (VRAI audio/video). Noms devices auto-detectes via `ffmpeg -list_devices`. Fallback video seul si micro absent.
   b. OpenCV VideoCapture(0) + VideoWriter mp4 (video sans audio).
   c. dernier recours: rafale PIL.ImageGrab -> GIF (ecran, sans audio ni webcam, depannage).
5. Envoie MEDIA: une fois termine.

Stockage: %LOCALAPPDATA%/hermes/captures/record_*.mp4 .

## Commande

"""bash
python "$HERMES_HOME/skills/record/scripts/capture_record.py" 30
"""
