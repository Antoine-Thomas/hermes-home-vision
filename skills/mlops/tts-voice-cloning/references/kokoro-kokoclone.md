# Kokoro-82M ONNX + Kanade 12.5 Hz (KokoClone) — install et verdict FR

Alternative locale et gratuite evaluee pour remplacer XTTS-v2 sur la diction francaise.
**Verdict : installer OK, francais KO, anglais excellent.**

## Ce que c'est

`github.com/Ashish-Patnaik/kokoclone` = deux etages :

1. **Kokoro-82M (ONNX)** — le TTS. Voix FR unique `ff_siwis` dans `voices-v1.0.bin`
   (57 voix au total, une seule francaise). Grapheme->phoneme : `misaki` + `espeak-ng`,
   via `EspeakG2P(language="fr-fr")`.
2. **Kanade 12.5 Hz** + vocodeur **Vocos 24 kHz** (poids `frothywater/kanade-*`) — conversion
   vocale zero-shot vers la voix de reference.

Point d'entree : `core/cloner.py` ->
`KokoClone.generate(text=..., lang="fr", reference_audio=..., output_path=...)`.
Sortie : **24 kHz mono PCM 16 bits**, conforme a ce qu'attend le reste du pipeline.

## Install (venv dedie, hors environnement Hermes)

- Cible : `C:\Users\searc\AppData\Local\hermes\data\kokoclone\`, Python **3.12** (pas 3.14).
- `uv venv --python 3.12 .venv` puis `uv pip install -r requirements.txt`.
- **Reparer le GPU APRES l'install par defaut : les roues tirees par defaut sont CPU.**
  torch/torchaudio cuXXX depuis l'index PyTorch + `onnxruntime-gpu`, avec le piege uv
  (« dependency confusion protection »). Commandes exactes : SKILL.md, section
  « Installer torch CUDA dans un venv dedie (Windows) ».
- **Lancer avec le CWD = racine du repo** : les modeles se telechargent en chemin RELATIF
  (`./model/kokoro.onnx` 89 Mo, `./voice/voices-v1.0.bin` 27 Mo). Poids Kanade/Vocos dans le
  cache HF. Le repo ne publie pas de SHA256 pour ces fichiers -> non verifiable, le signaler.
- Espace occupe : 3,9 Go (dont 3,8 Go de venv) + cache HF partage.

## Mesures

| | base Kokoro (TTS seul) | apres conversion Kanade |
|---|---|---|
| controle EN, 30 mots | **mot pour mot, 0 erreur** | — |
| paragraphe FR 30 mots | deraille des le 9e mot | identiquement degrade |

- Controle EN : « Hello, welcome to the seventh episode of the Hermes series... » revient exact.
  -> modele, vocodeur, venv et appel d'API sont corrects ; le defaut est la tete francaise.
- FR attendu / entendu : `la série Hermès` -> `la cédille de Metz` ; `un protoagent opensource`
  -> `un animat, c'est pour toi que je te parle` ; `sans aucune clé d'API` -> `sans aucun clé de
  pays`. Le debut est correct, puis la synthese deraille et **ne se rattrape jamais** : exactly le
  symptome que le projet promettait de supprimer.
- Traiter les accents de stress des phonemes (`ˈ`, `ˌ`) ne corrige rien (resultat pire) : le G2P
  n'est pas la cause. `ɛʁmˈɛs` pour « Hermès » et `sɛtjˈɛm` pour « septième » sont justes.
- Une duree cible annoncee a l'oreille se verifie par le nombre de mots (~130-150 mots/min) :
  18 mots annonces « 12-15 s » font ~8 s. Mesurer avant de signaler un ecart.

## Signal vs contenu — a mesurer separement

Plancher de bruit **-75,8 dBFS**, **0 ecretage**, crete -4,17 dBFS, RMS -18,97 dBFS, 0,04 s de
silence de tete, une seule pause interne de 0,66 s. **Audio propre, contenu faux.**
Ne jamais deduire « pas de bruit » => « diction OK ».

## G2P espeak FR — bug des ordinaux

`EspeakG2P(language="fr-fr")` sur `Voici le 7e volet.` -> `vwasˌi lə sˈɛt ˈə volˈɛ.`
« 7e » est lu « set e », pas « septième ». Ecrire les ordinaux en toutes lettres dans le texte
source — meme famille de correctif que le lexique de graphies XTTS.

## Diagnostic — ordre des verifications

1. **Controle anglais**, pipeline identique : separe modele/plumbing d'un probleme de langue.
2. **Base TTS seule vs apres conversion** : attribue le defaut a la bonne couche.
3. **Phonemes imprimes** : separe la graphie de l'acoustique.
4. **Aller-retour Whisper sur un paragraphe >= 20-30 mots** (`scripts/audit_tts.py`). Jamais sur un
   clip isole de moins d'une seconde : Whisper y invente.