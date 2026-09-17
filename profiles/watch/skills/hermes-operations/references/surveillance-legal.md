# Surveillance légale — alternative au flux infini

Flux continu infini + micro distant + ignore ESTOP = refus systématique (surveillance covert illégale en France sans consentement, contournement arrêt d'urgence, absence de voyant).

## Table de décision

| Demande | Réponse |
|---|---|---|
| /camera infini, /stream continu, RTSP/WebRTC détaché | Refuser, proposer /photo ou /record 30/60 |
| /photo, /snapshot | 1 capture unique avec voyant |
| /record, /record 30, /record 60 | Vidéo limitée 5–60s avec voyant |
| Durée >60s ou "jusqu'à /stop" | Plafonner à 60s, expliquer limite |

## Règles communes

- Vérifier ESTOP d'abord: si `%LOCALAPPDATA%/hermes/ESTOP` existe → répondre "Pause active (ESTOP). Envoie /pause off puis réessaie." et ne rien capturer.
- Voyant obligatoire: fenêtre Tkinter topmost 800×60 rouge, 1.5s pour /photo, clignotant 400ms pendant toute la durée pour /record.
- Durée max 60s, stockage `%LOCALAPPDATA%/hermes/captures/` (photo_*.jpg, record_*.mp4 ou record_*.gif fallback).
- Répondre `MEDIA:<chemin>` pour envoi Telegram.

## Implémentation actuelle

- `skills/photo/scripts/capture_photo.py` — tente OpenCV VideoCapture(0), sinon PIL.ImageGrab.grab() thumbnail 1920. cv2 absent sur ce host, fallback ImageGrab attendu.
- `skills/record/scripts/capture_record.py` — parse durée arg 1, VideoWriter mp4 640×480 15fps, sinon rafale ImageGrab toutes les 2s → gif.
- Skills enregistrés: scan_skill_commands() → /photo, /record, /surveillance-control (117 total). /com page 7 liste /photo (185 cmds totaux, 60 visibles menu Telegram).
- Doc de référence = cette fiche + hermes-operations SKILL.md; skills photo/record restent déclencheurs étroits.

## Tests

/photo seul → 1 jpg. /record 30 → mp4/gif après 30s. /pause puis /photo → refus. /pause off puis /photo → OK.
