# Changelog — Version 1.4 — BROUILLON (non publiée)

Statut : **draft**. Aucun tag, aucune release. Ce fichier est la base de travail de la v1.4 ;
il ne doit pas être annoncé comme livré.

Contexte : post-mortem de la production du volet 6 (talking head Jev + Hermes + LLM Wiki,
22-23/09/2026). Le run a produit sa vidéo mais a demandé 4 interventions manuelles ; les
sept erreurs ci-dessous sont toutes issues de ce run (aucune n'est hypothétique).

## Erreurs corrigées pendant la production du volet 6

1. **E1 — numpy non pin dans le venv Python 3.10** : `pip install numpy` avait posé numpy 2.4.3
   (roue cp311) dans le venv 3.10 de LatentSync → `No module named 'numpy._core._multiarray_umath'`
   et greffe HF en échec ; remède `numpy==1.26.4`, figé dans `requirements-latentsync.txt`.
2. **E2 — scikit-image cassé par numpy 2.x** : `numpy.dtype size changed ... Expected 96 from C
   header, got 88` sur `skimage._shared.geometry` ; le couple vérifié est numpy 1.26.4 +
   scikit-image 0.22.0 (dernière branche 1.x).
3. **E3 — `NameError: _taille_segment`** dans `pipeline_talkinghead.py` lors de `--segmenter auto`
   (ligne 730) : la fonction s'appelle `taille_tranche` (ligne 189) ; un seul nom corrigé.
4. **E4 — double crochet ffmpeg dans `assemble_v6.py`** : la variable de chaînage contenait ses
   propres crochets (`cour = "[0:v]"` + f-string) → `Error parsing filterchain '[[0:v]][1:v]overlay=...'`
   / `Trailing garbage after a filter` ; `cour = "0:v"` sans crochets.
5. **E5 — `AttributeError: 'list' object has no attribute 'items'`** à l'étape i du pipeline :
   `mesures_hf.json` est une **liste** d'un dict par instant de mesure, pas un dict ; nouveau
   `blocs_mesures()` qui accepte les deux formes.
6. **E6 — watchdog introuvable par `Get-ScheduledTask`** : le watchdog du volet 6 était un cron job
   Hermes (`no_agent`, toutes les 15 min, 46 ticks, `last_status: ok`), invisible du Planificateur
   Windows, et il a été mis en pause à 13:10 juste avant l'assemblage final (~1 h) ; tâche planifiée
   Windows créée et vérifiée, règle de vérification consignée.
7. **E7 — `Start-Process` et chemins avec espaces** : `-ArgumentList` aplatit ses arguments en ligne
   de commande brute, un chemin contenant un espace est redécoupé (`unrecognized arguments:
   tuto\talkinghead.mp4`) ; **le tableau ne corrige pas le problème** (mesuré) — chaque élément
   contenant un espace doit porter ses propres guillemets, ou utiliser l'appel natif `&`.

## Statut de chaque erreur (mesuré, pas supposé)

| # | Confirmée par | Correction | Consignée dans |
|---|---------------|------------|----------------|
| E1 | `etapes_hfi_6.log` (23/09 03:02, « NumPy version is: 2.4.3 », Python 3.10) | `requirements-latentsync.txt` (numpy==1.26.4) | `skills/mlops/tts-voice-cloning/references/dependances-venv.md` |
| E2 | traceback `skimage/_shared/geometry.pyx` du 18/09 20:12 | idem E1 (numpy 1.26.4 + skimage 0.22.0 vérifiés par import) | idem E1 |
| E3 | sortie de run du 22/09 23:36 (`NameError` ligne 730) | ligne 730 → `taille_tranche` | `skills/media/talking-head-video/references/pipeline-bugs.md` |
| E4 | **erreur non trouvée dans les logs** ; mécanisme reproduit en A/B le 23/09 (ffmpeg : `Error parsing filterchain`) | `cour = "0:v"` (code conforme vérifié) | idem E3 |
| E5 | `mesures_hf.json` réel = liste de 3 dicts + reproduction de l'`AttributeError` | `blocs_mesures()` (3 blocs produits sur le fichier réel) | idem E3 |
| E6 | `cron/jobs.json` : job `4a646bb6eab4`, 46 ticks, `last_status: ok`, `paused_at 13:10` | tâche Windows `volet6-watchdog` créée et vérifiée (`LastTaskResult: 0`) | `skills/devops/windows-ops/references/scheduled-tasks.md` |
| E7 | **erreur non trouvée dans les logs** ; mécanisme reproduit (sonde `args_dump.py`, PowerShell 5.1) | règle consignée, y compris la réfutation du correctif « tableau » | `skills/devops/windows-path-handling/SKILL.md` (règle 12) |

## Fichiers touchés

- `data/video_youtube/pipeline_talkinghead.py` — `blocs_mesures()` (E5).
- `data/video_youtube/assemble_v6.py` — déjà conforme (E4).
- `data/video_youtube/requirements-latentsync.txt` — nouveau, versions réelles de `pip freeze`.
- `skills/mlops/tts-voice-cloning/references/dependances-venv.md` — nouveau (E1, E2).
- `skills/media/talking-head-video/references/pipeline-bugs.md` — nouveau (E3, E4, E5).
- `skills/media/talking-head-video/SKILL.md` — 4 pièges + référence.
- `skills/devops/windows-ops/references/scheduled-tasks.md` — nouveau (E6).
- `skills/devops/windows-ops/SKILL.md` — référence.
- `skills/devops/windows-path-handling/SKILL.md` — règle 12 (E7).

Les scripts du pipeline vivent sous `data/`, **exclu du dépôt git** (`.gitignore`) : seuls les
skills et cette documentation sont versionnés. Copier `pipeline_talkinghead.py` et `assemble_v6.py`
dans le dépôt (ou les suivre par hash) si l'on veut que les correctifs de code soient commits.

## Hors périmètre mais bloquant pour livrer

Le MP4 final au chemin de livraison (`Desktop\hermes tuto\tutotete20_jev_llmwiki.mp4`) est
**tronqué** : l'encodage a été tué à 17:27 le 23/09 (banc d'essai de vitesse), le fichier fait
463 470 640 octets et `ffprobe` répond `moov atom not found`. Il faut relancer `assemble_v6.py`
(CRF 20 preset fast depuis le 23/09 16:11) pour obtenir un fichier livrable. Un assemblage
interrompu ne laisse aucune trace visible côté taille de fichier.

## À faire avant de publier la v1.4

- [ ] Relancer l'assemblage final et vérifier le MP4 livré par `ffprobe` (durée + streams).
- [ ] Décider du sort de `volet6-watchdog` : tâche Windows créée en `Disabled`
      (`schtasks /change /tn "volet6-watchdog" /enable` pour l'activer) et cron job Hermes en pause.
- [ ] Trancher la copie des scripts `data/video_youtube/*.py` dans le dépôt (suivi des correctifs).
