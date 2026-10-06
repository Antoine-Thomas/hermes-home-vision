# Piper — narration FR longue, binaire autonome (Windows)

Piper est **deterministe** : une seule passe sur tout le script, pas de decoupage en segments, pas de
« garder le meilleur tirage », pas de GPU. Mesures sur une narration de 921 mots
(`fr_FR-tom-medium`) : **374,096 s d'audio (44100 Hz mono s16) produites en 40 s de CPU**, 0 phrase
ajoutee, 0 boucle, derniere phrase intacte.

## Installation (binaire autonome)

`https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip` —
22 477 236 o, 363 entrees : `piper.exe`, `onnxruntime.dll`, `onnxruntime_providers_shared.dll`,
`piper_phonemize.dll`, `espeak-ng.dll`, `espeak-ng-data/`, `libtashkeel_model.ort`, `pkgconfig/`.

Les releases `OHF-Voice/piper1-gpl` ne publient **que des roues Python** : inutilisables pour un
`piper.exe` autonome.

```bash
cd "$LOCALAPPDATA/hermes/data/piper" && mkdir -p voices
curl -sLf -o piper_win.zip "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"
curl -sLf -o voices/fr_FR-tom-medium.onnx      "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/tom/medium/fr_FR-tom-medium.onnx"
curl -sLf -o voices/fr_FR-tom-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/tom/medium/fr_FR-tom-medium.onnx.json"
python -c "import zipfile;zipfile.ZipFile('piper_win.zip').extractall('.')"
mv piper/* . && rmdir piper && rm piper_win.zip
```

Tailles : zip 22 477 236 o ; `fr_FR-tom-medium.onnx` 63 511 038 o, sha256
`bf65074ccdeeeeaa832e75edb1c0a513c01c9a972bdf085ff8a6e71ea234fd41` ; `.onnx.json` 4 959 o.

**`piper.exe`, ses DLL et `espeak-ng-data/` doivent rester dans le MEME dossier** — le zip les range
dans un sous-dossier `piper/`, d'ou le `mv piper/* .`. Lancer le binaire depuis ce dossier (ou lui
donner `--espeak_data`), sinon la phonemisation echoue.

## Sample rate : le lire, ne pas le supposer

`fr_FR-tom-medium` sort en **44 100 Hz**, pas en 22 050 Hz comme les autres modeles « medium » :

```bash
python -c "import json;print(json.load(open('voices/fr_FR-tom-medium.onnx.json'))['audio']['sample_rate'])"
printf 'Bonjour.\n' | ./piper.exe --model voices/fr_FR-tom-medium.onnx --output_file essai.wav --quiet
ffprobe -v error -show_entries stream=sample_rate,channels,bits_per_sample -of default=nw=1 essai.wav
```

## Generation

```bash
python -c "open('t.txt','w',encoding='utf-8').write(open('script.txt',encoding='utf-8-sig').read())"   # retirer le BOM
cat t.txt | ./piper.exe --model voices/fr_FR-tom-medium.onnx --config voices/fr_FR-tom-medium.onnx.json \
    --output_file narration.wav --quiet
```

Tout le script en **une** passe sur stdin : Piper decoupe lui-meme en phrases et ecrit un seul WAV.
Un BOM residuel en tete de flux fait partir le premier phoneme en binaire — relire en `utf-8-sig`,
reecrire en `utf-8`. Sortie : PCM s16le mono a la frequence native du modele.

## Duree cible

| cible | duree mesuree | facteur | commande |
|---|---|---|---|
| 7 min (420 s) | 374,096 s | `atempo = 374,096/420 = 0,890704` | `ffmpeg -i nat.wav -af atempo=0.890704 -ar 24000 -c:a pcm_s16le out.wav` |

`--length_scale` est l'alternative native (aucun time-stretch), mais **la duree n'est pas lineaire en
`length_scale`** : `1,12274`, calcule lineairement pour viser 420 s, a rendu **413,55 s**. Mesurer au
lieu d'extrapoler, et proposer les deux tirages en A/B (l'atempo pour la conformite a la procedure,
le natif pour la qualite).

Conversion pour le pipeline video, dans la meme passe de sortie :
`ffmpeg -i out.wav -ar 16000 -c:a pcm_s16le out_16k.wav` (MuseTalk).

## Verifier une prise Piper : trois mesures, pas une

1. **Similarite mot-a-mot contre le texte d'ORIGINE** (normalisation : NFD, minuscules, ponctuation et
   tirets retires) plus la **couverture** du texte de reference.
2. **Phrases ajoutees** (transcript plus LONG que la reference) et **trous** : opcodes
   `difflib.SequenceMatcher` sur les listes de mots, seuil >= 3 mots.
3. **Boucles** : compter les 6-grammes repetes >= 3 fois.

faster-whisper `medium`, CPU `int8`, `language="fr"` — un seul fichier de 420 s, pas de decoupage.

### Tri des ecarts : artefact Whisper vs vraie faute de diction

Mesure sur la meme prise : **0,8865 brut** contre **0,9093 sigles normalises**. Sur un texte dense en
sigles, le seuil de 0,90 se joue sur ce tri — rapporter les deux chiffres, jamais un seul.

| transcription | verdict | pourquoi |
|---|---|---|
| `JEV` -> `gev` | artefact | en francais **J et G = meme son [ʒ]** |
| `Laya` -> `leia`, `Obsidian` -> `obsidien`, `Kokoclone` -> `coco clone`, `fail` -> `faille` | artefact | meme prononciation, orthographe approchee |
| `RAG` -> `rhag` / `rhybe`, `L L M` -> `LLM`, `MEMORY point M D` -> `md` | artefact | sigle reecrit, aucun mot manquant |
| `c'est` -> `cette` | artefact | homophones |
| `deux a cinq` -> `2 a 5`, `zéro virgule quatre-vingt-dix-huit` -> `0,98`, pluriels normalises | artefact | Whisper normalise nombres et accords |
| `protoagent` -> `protouage` (3x) | **faute** | mot francais deforme |
| `GitHub` -> `jhub` (2x), `git clone` -> `jclone` | **faute** | terme deforme |
| `Markdown` -> `marklan`, `ONNX` -> `ox`, `Si Yüan` -> `sidiouan` / `six duants` | **faute** | terme deforme |
| `une IA` -> `unia` (2x) | **faute** | sigle avale par la syllabe precedente |

Le tri s'automatise : lister les opcodes non egaux des mots normalises, puis separer ceux dont un cote
est un sigle / un nombre connu (`SIGLES` + `[0-9]+`) de ceux qui touchent un mot francais.

Contrairement a Chatterbox, Piper phonemise via **espeak-ng FR** : la couche graphie->phoneme est donc
celle d'XTTS/Kokoro, et ces termes deformes sont la cible naturelle d'un labo de graphies — a tester
par sonde courte avant de l'affirmer (`references/french-diction-tricks.md`). Le re-rendu complet
coutant 40 s, une passe de labo sur quelques jetons est bon marche.

## Niveaux et ecretage

```bash
ffmpeg -hide_banner -nostats -i out.wav -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
python -c "import wave,array;a=array.array('h');w=wave.open('out.wav');n=w.getnframes();a.frombytes(w.readframes(n));print('max',max(abs(x) for x in a),'ecretes',sum(1 for x in a if abs(x)>=32767),'/',n)"
```

`-v error` **supprime** la sortie de `volumedetect` (journalisee en niveau info) : l'appeler sans
`-v error`. `max_volume: 0.0 dB` ne prouve pas l'ecretage — compter les echantillons a
`abs(x) >= 32767`. Mesure : 85 echantillons sur 16 497 628 (~2 ms, inaudible), deja presents dans la
sortie brute Piper et non causes par l'atempo (23 sur le 24 kHz, 8 sur le 16 kHz).

## Shell (git-bash / MSYS)

`ffprobe` imprime des **virgules** sous locale francaise : `export LC_ALL=C` des qu'une duree est
parsee en bash, sinon `printf` echoue sur `374,095873`.
