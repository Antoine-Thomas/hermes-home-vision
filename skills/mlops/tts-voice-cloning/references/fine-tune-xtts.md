# Fine-tune XTTS v2 — recette et pieges de mise en route

Objectif : adapter une voix XTTS v2 a un corpus reel. Verdict a garder en tete : **le corpus decide**
(section correspondante de `SKILL.md`) ; cette fiche est la mecanique d'un essai court.

## 1. Sous-corpus de test

- Un SEUL fichier source : comparer le rapport signal/bruit du lot et garder le plus propre (mesurer,
  ne pas supposer : un enregistreur multi-prises peut varier de 12 dB entre deux fichiers).
- Fenetres de 0,5 s notees « propre » si le niveau est dans la bande utile (~-32 a -14 dBFS) et
  qu'aucun echantillon n'est sature (|x| >= 0,99). Selection d'un segment de 12 s : **70 % de fenetres
  utiles suffisent** (les pauses courtes de la parole sont normales — exiger 100 % de fenetres propres
  consecutives ne retient presque rien), aucun silence de plus de 1 s, aucune saturation.
- Resampler en **mono 22 050 Hz** : c'est la frequence de XTTS v2. Un corpus a 24 kHz serait
  reechantillonne, autant le faire une fois proprement.
- 10 min d'entrainement + 1 min de validation mise de cote.
- **Transcrire le corpus** (Whisper) : un fine-tune XTTS a besoin du texte. Format `nom|texte|texte`
  dans un `metadata_train.csv`, WAV dans `<racine>/wavs/` (formatter `ljspeech`).

## 2. Lancement

- `GPTArgs` / `GPTTrainerConfig` / `GPTTrainer` viennent de
  `TTS.tts.layers.xtts.trainer.gpt_trainer` ; le modele local est dans
  `%LOCALAPPDATA%\TTS\tts_models--multilingual--multi-dataset--xtts_v2\` (`model.pth`, `vocab.json`).
- Il faut en plus `dvae.pth` (~210 Mo) et `mel_stats.pth` (1 Ko), absents du cache d'inference.
- Lot 1 + accumulation (`grad_accum_steps`) pour tenir en 8 Go ; la VRAM monte a ~7,9/8,2 Go : ca passe
  mais sans marge.
- Reprendre la recette officielle (`recipes/ljspeech/xtts_v2/train_gpt_xtts.py`) en l'adaptant, et
  **borner en epoques** — la recette vise des dizaines de milliers de pas.

## 3. Les quatre pieges qui font echouer la mise en route

| Symptome | Cause | Correctif |
|---|---|---|
| `RecursionError` dans le chargeur, puis `PermissionError` au nettoyage | `max_wav_length` de la recette (255 995 ≈ 11,6 s) REJETTE tous les segments de 12 s ; le chargeur boucle | porter `max_wav_length` au-dessus de la duree reelle des segments (300 000 pour 12 s a 22 050 Hz) |
| `RecursionError` dans un worker DataLoader | workers multiprocessus sur Windows | `num_loader_workers = 0` (chargement dans le processus principal) |
| `XttsAudioConfig` introuvable, `multiple values for argument 'language'`, `checkpoint_path` refuse | l'API TTS a change selon les versions (`XttsArgs`, facade `TTS` sans `model_path`) | passer par le bas niveau : `Xtts.init_from_config(config)` + `load_checkpoint(config, checkpoint_dir=...)` + `inference(text=..., language=..., gpt_cond_latent=..., speaker_embedding=...)` en parametres **nommes** |
| `AssertionError: not enough samples for the evaluation set` | `eval_split_size` par defaut trop petit pour un corpus de quelques dizaines de segments | `eval_split_size = 0.02` |

Autres points de mefiance :
- Le dossier de sortie d'un run est supprime/reconstruit au demarrage : un fichier encore ouvert par un
  autre processus (run precedent) fait echouer la mise en route — verifier qu'aucun entrainement ne
  tourne avant de relancer.
- Le journal du trainer (`<run>/trainer_0_log.txt`) porte les chiffres vivants ; la sortie standard
  redirigee est **tamponnee** et donne l'impression que rien n'avance.
- `save_step` / `save_n_checkpoints` : chaque checkpoint complet pese environ 5,6 Go.

## 4. Mesure du gain (test A/B)

1. Quatre phrases, dont celles qui contiennent les termes du lexique.
2. Generer avec le modele d'origine ET avec le modele affine — **meme code, meme voix de reference,
   meme temperature** (sinon la comparaison ne vaut rien). Charger l'affine depuis une copie du dossier
   XTTS v2 ou seule la ponderation change : le cache d'inference reste intact.
3. Transcrire les deux series par Whisper, compter les termes reconnus, comparer les durees, ecouter
   les artefacts.
4. Verdict a consigner, avec le seuil de reouverture (volume de voix necessaire pour reessayer).
