---
name: photo
description: "Prend une photo unique (webcam ou ecran) avec voyant visible, respecte ESTOP, envoie par Telegram. Alternative legale au flux continu."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Photo - capture unique legale

Prend UNE photo avec voyant a l'ecran. Respecte ESTOP. Remplace le flux infini interdit.

## Quand utiliser

- L'utilisateur dit /photo, photo, snapshot, capture
- Une seule image demandee

## Quand NE PAS utiliser

- Flux continu infini -> refuse, propose /photo ou /record 30
- Si ESTOP actif (fichier %LOCALAPPDATA%/hermes/ESTOP existe) -> refuse, indique /pause off

## Fonctionnement

1. Verifie ESTOP: si C:/Users/searc/AppData/Local/hermes/ESTOP existe => repond "Pause active (ESTOP). Envoie /pause off puis reessaie." et stoppe.
2. Voyant: fenetre Tkinter topmost 800x60 rouge " CAPUTRE PHOTO EN COURS " 1.5s.
3. Capture: tente OpenCV VideoCapture(0), sinon PIL.ImageGrab.grab(). Sauve dans %LOCALAPPDATA%/hermes/captures/photo_YYYYmmdd_HHMMSS.jpg
4. Repond avec chemin MEDIA: et confirmation Telegram.

## Commande

Quand /photo est appele, execute:

"""bash
python "$HERMES_HOME/skills/photo/scripts/capture_photo.py"
"""
