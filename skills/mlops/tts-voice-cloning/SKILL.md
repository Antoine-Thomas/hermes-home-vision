---
name: tts-voice-cloning
description: "Clone a voice or TTS locally: XTTS-v2, Piper, VibeVoice."
---

# Local TTS + Voice Cloning (XTTS-v2 + Piper + VibeVoice)

## When to use
User wants to clone a voice or generate speech locally. Three engines are installed:
- **XTTS-v2 (Coqui)** — PREFERRED for natural FRENCH with a CLONED voice (VibeVoice's French output has a foreign accent + diction bugs).
- **Piper `fr_FR-tom-medium`** — PREFERRED for a LONG, stable narration: deterministe, CPU, 40 s pour 6 min d'audio, 0 phrase ajoutee, 0 boucle. A sortir des qu'un moteur autoregressif (XTTS, Chatterbox) fait payer le tirage trop cher.
- **VibeVoice** (community fork `vibevoice-community/VibeVoice`) — long-form / multi-speaker dialogue.

## XTTS-v2 (Coqui) — preferred for French voice cloning

Dedicated venv at `data/xtts/` (torch 2.5.1+cu124 + `coqui-tts`). Two mandatory import patches + a ToS bypass — full detail in `references/xtts-v2-setup.md`.

Clone + generate (24 kHz mono WAV out):
```python
from TTS.api import TTS
from TTS.utils.manage import ModelManager
ModelManager.ask_tos = staticmethod(lambda path: True)  # bypass Coqui license prompt

tts = TTS(\"tts_models/multilingual/multi-dataset/xtts_v2\", gpu=True)
tts.tts_to_file(text=texte, speaker_wav=\"voix_reference.wav\", language=\"fr\",
                temperature=0.75, speed=1.0, file_path=\"out.wav\")
```

- **Delivery (this user's preference)**: `temperature=0.75, speed=1.0` = regular,
  steady, no word dragging. Lower temp → robotic; higher → words drag / glitch
  (an \"incomprehensible passage\").
- **Generate segment-by-segment** (one file per paragraph) so a single mangled
  segment can be re-generated alone instead of redoing the whole ~5 min voice —
  but add NO gap between segments, and trim the silence the model already puts at
  the end of each one (see the joint pitfall below).
- **Un seul reglage, en livraison comme au labo de diction : `temperature=0.75, speed=1.0`.**
  Le labo doit reproduire les conditions de livraison, sinon la graphie qu'il valide ne prouve
  rien ; pour la robustesse on tire plusieurs fois et on garde le meilleur tirage, on ne monte
  jamais la temperature. Mesure sur la voix livree du volet 5 (873 mots, 343,8 s, 13 tranches) :
  12 tranches sur 13 a score Whisper >= 0,90, la 13e a 0,88 (un nvidia mal orthographie).
  Toute affirmation du genre 0,85 minimum pour eviter une diction monotone est fausse : la cause
  etait des phrases longues ou mal construites, et tous les scripts v4/v5 de `data/xtts/`
  tournent a 0,75 / 1.0.
- Reference audio: 24 kHz mono, 10–30 s (`mavoix5.wav` = validated take, in
  `data/vibevoice/repo/demo/voices/`).

## Lessons and Pitfalls

- **A long voice must be re-transcribed SEGMENT BY SEGMENT, not only end to end.** Whisper's
  transcript of the assembled file shows the defects as multi-word nonsense (`gère des sites` →
  `j'ai à décider`, `pas avec celles des autres` → `par excel des autres`, `vous choisissez` →
  `je suis c'est`) — passages the listener would hear as gibberish. Fix them by REWRITING the
  sentence short (lists become separate sentences, `pas avec celles des autres` becomes
  `Il n'utilise pas celles des autres`), regenerate only the affected chunk, and re-transcribe.
  Do not try to correct by tweaking temperature or speed: the construction is the cause.
  Single-word deviations that are homophones (`demandez`/`demander`, `clonez`/`cloné`,
  `stocke`/`stock`) are Whisper's own spelling, not TTS defects — do not chase them.
- **XTTS adds a parasite word at the end of some sentences** (measured: `… sous le nom
  Antoine-Thomas.` came back as `Antoine Thomas Spencer`, `Il appartient à Antoine Thomas.` as
  `Et appartient à Antoine Thomas-Pontes`). Prefer short standalone sentences for proper nouns and
  check the tail of every long sentence in the transcript.
- **Trailing silence per segment is what makes a long voice sound "choppy".** XTTS-v2
  ends every segment with 0.56-0.63 s of silence (measured over 38 segments).
  Concatenating them as-is adds ~575 ms of blank at EVERY joint — 21.3 s over a 288 s
  voice — and some of those pauses land mid-sentence, because the text chunker cuts on
  a comma before falling back to a hard cut at the character limit. The listener reports
  "jumps" or sound drops in the voice.
  **Fix:** before concatenating, trim each segment to keep 120 ms of trailing silence and
  40 ms of leading silence (threshold 3 % of that segment's RMS). Measured after
  trimming: median trailing silence 120 ms, max 126 ms. Add no gap on top of that.
- **Do not go looking for clicks at the joints.** Segments start and end inside silence,
  so the sample-to-sample discontinuity there is nil. Diagnose with the RMS envelope
  (20 ms windows) and by measuring leading/trailing silence per segment — the defect is
  pauses, not clicks.
- **Phonetic Pronunciation:** French proper nouns or technical terms (like "Hermes Agent") may be cut or mispronounced.
  - **Fix:** Use phonetic spelling in the text (e.g., "Hermès ... Agent" with an accent and ellipsis for a natural pause).
  - **Verification:** Always generate a short test (10-15s) with the target phrase before committing to a 5-minute render.
  - **Systematic spelling lab:** generate one short sentence per candidate spelling, transcribe each with faster-whisper (`small` is enough), keep the spelling that comes back correct — do not tune by ear. Measured table + the sentence structures XTTS mangles in `references/french-diction-tricks.md`.
  - **Make the lab a reusable lexicon, not a one-off test.** Four files, all beside the project script:
    `lexique_diction.json` (each entry: canonical spelling, TTS spelling, REJECTED spellings, note),
    `preparer_script_tts.py` (script text → TTS text, input never modified),
    `corriger_transcription.py` (Whisper transcript → canonical spellings for human reading),
    and the test files that produced the table. Run the lab once per engine and per reference voice:
    graphies are engine-specific.
    - **Never chain two substitutions where one output contains the other's pattern.**
      `hermes-home-vision → "Hermesse, home vision"` followed by `Hermes → Hermesse` turned
      `Hermesse` into `Hermessese` — the whole 5-minute voice said a made-up word, and Whisper
      transcribed it as `hermes et 16`. Order the rules from most specific to most general, use
      `\bHermes\b`, and test the lexicon on a string that contains BOTH forms before rendering.
      A double substitution is silent: nothing crashes, the text just becomes wrong.
    - **Never put a common word in the Whisper-return list.** Adding bare `Local` (to normalise
      "Local by Flywheel") silently rewrote the ordinary French word `local` on every occurrence
      and produced `Local by Flywheel by Flywheel`. Return lists accept only unambiguous forms;
      check the corrected file for double substitutions right after the first run.
    - **Keep the rejected spellings in the JSON.** They are what a future session would otherwise
      re-introduce (e.g. `vé-pé cé-èle-i` for WP-CLI, `ène-jine-ixe` for nginx).
    - **Verify both scripts leave their input untouched** (`md5sum` before/after) — they only write
      a new output file.
    - A transcript with ZERO phonetic spellings is the expected result when the graphies worked:
      Whisper writes `Nginx`, `WP-CLI`, `MySQL` directly. The return script is a safety net for
      later takes, not evidence that the lexicon did nothing.
- **Freeze the chunking before correcting anything.** The chunker re-cuts from the script on every
  run, so editing one sentence reflows every boundary after it and invalidates all cached segments.
  Dump the chunk list to `chunks_v5.json`, have the generator read that cache, and regenerate only
  the indices listed in `REJOUER`. Measured: a full 11-chunk re-render is 3,5 min, a targeted one
  is 35-96 s. Copy the old segments to their new indices (last first) when a chunk is split.
- **Correction keys must be SINGLE sentences.** The chunker accumulates whole sentences and never
  cuts inside one, so a multi-sentence key can straddle two chunks and silently match nothing
  (observed twice). Test each key's presence and assert it matches exactly one chunk before running.
- **Normalise apostrophes before matching.** A corrections file written with `’` (U+2019) against a
  script using `'` (U+0027) matches nothing and fails silently. Compare on one canonical form.
- **When a word breaks in EVERY chunk where it appears, replace the word — do not re-roll.**
  Measured: « passerelle » came back as « passeraient les vivantes », « passerait l'an » and
  « il me passera il » in all three chunks that contained it; re-rolling did not help. Rewriting it
  to « service » fixed all three at once. A single-chunk failure is a draw, a repeated failure is
  the word.
- **A chunk that generates disproportionately long audio is dragging, and defects follow.**
  Measured: one chunk produced 42,5 s of audio for 74 words (104 mots/min) against a usual ~150,
  and every re-draw added a fresh nonsense passage. Split into two chunks, the same text came out at
  154 mots/min and clean. Watch the seconds-per-word ratio of each chunk while generating.
- **Cap the normalisation gain to protect the crest.** Aiming at an exact level (e.g. −17 dBFS) can
  push the peak to 1,000 exactly, i.e. clipping. Take `min(gain, 0.98/peak)` and report the level
  actually reached (−17,06 dBFS measured) rather than a target that would have clipped.
- **A run of identical sentence structures makes XTTS derail around proper nouns.**
  "Il y a NVIDIA. Il y a Gemini. Il y a Cloudflare. Il y a MiniMax." never once transcribed
  cleanly, while each of those same names passed alone in the lab. Rewrite with varied
  structures ("Le premier s'appelle…", "Ensuite vient…", "… complète la liste") and cap the
  density: four foreign proper nouns in 30 s was fatal, two per chunk was fine. Splitting the
  chunk in two brought both halves back above 0,90.
- **Some words are simply not pronounceable by the model — drop them, don't ship them.**
  DeepSeek failed on all five graphies tried ("d'hypsique", "deep-sea-camel", "DeepSync 1.6",
  and one 12,9 s gibberish loop that dragged for 13 s of audio). Test four or five, and if all
  fail, remove the word from the spoken text and say so in the report — a mangled brand name is
  worse than an absent one. Keep a passing graphy list in the JSON so the next take doesn't retry.
- **Read the écart details before rewriting a chunk.** A chunk scored 0,880 with a single
  "deviation": the lexicon graphy "N Vidia" (two tokens) transcribed as "nvidia" (one token) —
  the audio was correct and the score was an artefact. Same for "quatre-vingt-onze" -> "91",
  "troisieme" -> "3e", "dix" -> "10": Whisper normalises numbers and splits compounds. A low
  score with only spelling/homophone noise is a PASS.
- **When a chunk drags, a re-draw can be enough — try it before splitting.** Measured: the same
  text re-drawn went from 45,6 s to 37,9 s (104 -> 152 mots/min) with no defect change. Splitting
  is the fallback when the drag repeats or when defects cluster.
- **Keep the BEST draw, never the last.** A loop that rewrites the chunk file on every attempt
  destroys a good take: one 0,925 draw was overwritten by four worse ones. Score each attempt,
  copy the wav aside when it improves, and restore the best at the end.
- **When the chunking is frozen in a cache, editing the script is not enough.** The generator
  re-reads the cache, so corrected sentences are regenerated with the OLD text (observed, and it
  silently wasted four chunks of GPU). Patch the cached texts with the same strict
  match-exactly-once check, then regenerate only the affected indices.
- **This shell has no `bc`.** A `[ "$(echo "$s >= 0.90" | bc -l)" = "1" ]` test always failed, so
  the loop never stopped. Use a bash pattern (`case "$s" in 0.9*|1.0*)`) or awk, or write the
  loop in Python.
- **Re-transcribe the assembled voice** with faster-whisper and diff it against the script
  before rendering video: a 15 s hole in the transcript is not silence (check the RMS) —
  it is an unintelligible passage that has to be rewritten.
- **Installer torch CUDA dans un venv dedie (Windows) — PyPI ne suffit pas.** La roue `torch`
  publiee sur PyPI pour Windows est un build **CPU** : elle s'annonce `2.14.1+cpu` et
  `torch.cuda.is_available()` renvoie `False`. Le CUDA ne vient que de l'index PyTorch, et il faut
  choisir l'index d'apres le CUDA UMD affiche par `nvidia-smi` :
  ```bash
  curl -s https://download.pytorch.org/whl/cu130/torch/ | grep -oE 'torch-[0-9.]+%2Bcu130-cp312-cp312-win_amd64' | sort -uV | tail -6
  uv pip install --python "$VENV/Scripts/python.exe" --index-url https://download.pytorch.org/whl/cu130 \
      --no-deps --reinstall-package torch --reinstall-package torchaudio "torch==2.14.1+cu130" "torchaudio==2.11.0+cu130"
  ```
  Le `+` des noms de roues est encode `%2B` dans ces listings : un `grep '\+cu130'` ne trouve rien.
  **Piege uv :** avec `--extra-index-url https://pypi.org/simple`, uv REFUSE la roue `+cuXXX`
  (« dependency confusion protection » : il voit `torch` sur PyPI d'abord et s'arrete la).
  Installer depuis l'index PyTorch SEUL, version epinglee, avec `--no-deps` — les dependances sont
  deja presentes. Verifier : `python -c "import torch;print(torch.__version__, torch.cuda.is_available(), torch.version.cuda)"`.
- **onnxruntime-gpu remplace onnxruntime (meme nom d'import) : desinstaller l'ancien d'abord.**
  `uv pip uninstall onnxruntime && uv pip install onnxruntime-gpu`, puis verifier
  `ort.get_available_providers()`. L'echec du TensorRT EP est normal sans les libs TensorRT : le
  repli sur `CUDAExecutionProvider` est automatique et non bloquant — ne pas le traiter en panne.

## Fine-tuner XTTS : le corpus decide, pas la VRAM

Avant de proposer un fine-tune, COMPTER la voix reelle disponible : sur 8 Go c'est presque toujours
la donnee qui bloque, pas la carte (un fine-tune LoRA tient dans 6-8 Go).

- Il faut 30 minutes a plusieurs heures de parole propre : une seule voix, sans musique ni bruit de
  fond, avec des phrases qui couvrent le vocabulaire vise.
- **Piege de methode — la synthese n'est pas un corpus.** Tout ce qui sort de XTTS est de la
  synthese : `data/xtts/voix_xtts_*.wav` et `segments/` ne sont PAS des donnees de voix, et s'en
  servir apprend au modele a imiter sa propre sortie. La voix reelle est celle d'une prise de vue ;
  les versions « clean » du prep peuvent etre SANS piste audio, verifier avec
  `ffprobe -v error -select_streams a -show_entries stream=codec_name -of csv=p=0 <fichier>`.
- Sous une minute de voix : conclure « pas maintenant » et le dire franchement. Le sur-apprentissage
  degrade la voix au lieu de corriger la diction, pour des heures de GPU.
- **Un essai court AVANT tout engagement de duree.** Extraire un sous-corpus propre (le meilleur
  fichier du lot seulement : comparer le rapport signal/bruit, garder celui qui est propre),
  entrainer quelques milliers de pas, puis MESURER le gain. Mesure reelle sur 10 min de corpus
  (~2 000 pas, 2 h sur 8 Go) : perte -7 %, et pourtant **diction inchangee** — 4 termes techniques
  reconnus sur 40 avant, 5 apres. Conclusion : sous une heure de donnees, le fine-tune ne corrige pas
  les termes techniques, alors que le lexique de graphies les regle deja. Ne pas promettre de run
  complet sans cette mesure.
- **Juger par un test A/B mesure, jamais a l'oreille seule.** Generer les memes phrases avec le
  modele d'origine et le modele affine (meme code, meme voix de reference, meme temperature),
  transcrire les deux par Whisper, compter les termes techniques reconnus, mesurer la DUREE (un
  modele affine parle plus lentement : +13 a +22 % pour le meme texte) et reperer les artefacts
  (mots ajoutes en fin de phrase).
- **Un checkpoint complet pese plusieurs Go** (~5,6 Go) : regler `save_step` et `save_n_checkpoints`,
  puis ne garder qu'une archive et supprimer les runs intermediaires — l'espace part tres vite.
  Verifier avant de supprimer qu'un checkpoint candidat est bien un doublon (taille identique) de
  l'archive conservee, et que `voix_reference.wav` a le meme MD5 avant et apres.
- **Ne JAMAIS faire `pip install <paquet>` sans pin dans le venv du pipeline talking-head
  (LatentSync, Python 3.10).** numpy 2.x y casse `scikit-image` 0.22.0 (`numpy.dtype size
  changed`) et une roue cp311 casse `cv2` ; on installe uniquement par le fichier de contraintes
  `data\video_youtube\requirements-latentsync.txt`
  (`LatentSync\venv\Scripts\python.exe -m pip install -r requirements-latentsync.txt`), qui fige
  numpy 1.26.4 + scikit-image 0.22.0 + insightface + les roues cu121. Tableau de compatibilite,
  messages d'erreur exacts et commande de verification : `references/dependances-venv.md`.
- Le vrai levier sur la diction reste le labo de graphies (`references/french-diction-tricks.md`)
  et une couche de correction lexicale appliquee au texte AVANT la synthese : zero GPU, effet
  immediat, et verifiable par aller-retour Whisper.

## Voicebox — evalue, pas installe (16/09/2026)

`jamiepine/voicebox` : studio vocal open source (interface type DAW, 7 moteurs TTS, API REST,
serveur MCP) avec un plugin Hermes officiel (`pip install hermes-voicebox`).

**Ce n'est PAS un remplacement du pipeline XTTS** — c'est un orchestrateur qui appelle les memes
moteurs. Aucun gain de qualite vocale a en attendre : si la diction decevrait, elle decevrait autant
sous Voicebox.

A considerer en **Phase 4**, apres le LoRA visage, et seulement si un besoin d'interface vocale
apparait (dictee, montage audio, comparaison de moteurs). Prerequis : application desktop ou Docker
sur `127.0.0.1:17493`. Doc : SiYuan `veille / Voicebox - studio vocal local`.

## Etat reel du clone de voix (verifie 19/09/2026)

`C:\Users\searc\Desktop\ma voix 12` **n'est pas un clone de voix** : c'est le CORPUS — 2 prises Zoom
brutes (ZOOM0004 56 min, ZOOM0005 47 min ; 48 kHz stereo PCM 24 bits ; 1,7 Go ; 1 h 43). Aucun `.pth`,
`.ckpt`, `.index`, `.onnx`, `config.json` ni `speakers_xtts.pth` dedans. Ne pas repartir chercher un
modele entraine la-bas.

Le clone utilisable est **zero-shot** : XTTS-v2 + `data\xtts\voix_reference.wav` (24 kHz mono,
29,72 s, MD5 `2c786188c443...`). Le seul modele entraine est
`data\xtts\corpus_test\loRA_archive_best_model_1568.pth` (5,6 Go) — gain mesure marginal, run
supprime : archive de poids, pas un `checkpoint_dir` chargeable.

**Mesures du chemin valide (a citer, elles evitent un nouveau test a blanc)** : RTF **1,01x**
(6 s de generation pour 5,43 s d'audio), modele charge en 16 s, **VRAM pic 2,03 Go** sur 8 Go,
GPU 52 -> 53 degC, memoire rendue apres le run. Le fine-tune, lui, montait a 7,9 Go.

- **faster-whisper sur CUDA echoue dans le venv `hermes-agent`** :
  `RuntimeError: Library cublas64_12.dll is not found or cannot be loaded` (torch cu118).
  Use `WhisperModel("small", device="cpu", compute_type="int8")` — quelques secondes pour 5 s d'audio.
  Modeles deja en cache : `faster-whisper-base`, `-small`, `-medium`.
- **Envoyer un WAV sur Telegram : passer par le MP3.** `sendAudio` n'accepte en lecteur que `.mp3` /
  `.m4a` ; un WAV arrive en document (a telecharger pour ecouter). Convertir en MP3 192k et envoyer
  le MP3 par `sendAudio`, le WAV par `sendDocument` pour l'archive.

## TTS cloud MiniMax (quand le local ne convient pas)

MiniMax T2A v2 est une alternative cloud (voix FR natives). Endpoint, voix, codes d'erreur et
pieges (`.env` qui corrompt la cle, concat multi-chunks) : `references/minimax-tts-api.md`.
Regle : un `status_code=1008 'insufficient balance'` signifie cle VALIDE mais compte a sec —
le signaler, ne pas fabriquer d'audio, et ne pas boucler sur d'autres modeles/hotes.

## Kokoro / KokoClone — evalue, francais inutilisable en narration

`Ashish-Patnaik/kokoclone` = Kokoro-82M ONNX (voix FR `ff_siwis`) + Kanade 12.5 Hz (conversion
vocale zero-shot). Installe et mesure : toute la chaine technique fonctionne, **le francais ne
passe pas**. Ne pas refaire l'installation sur l'espoir d'un meilleur tirage — l'anglais et le
francais passent par le meme modele, seul le francais casse.

Mesure decisive, pipeline identique : un paragraphe de 30 mots en **anglais** revient mot pour mot
sans une erreur ; le meme en **francais** deraille des le 9e mot (`la série Hermès` ->
`la cédille de Metz`, `un protoagent opensource` -> `un animat, c'est pour toi que je te parle`).
Dossier, recette d'install, mesures et commandes : `references/kokoro-kokoclone.md`.

Regles qui en sortent — valables pour l'evaluation de N'IMPORTE QUEL moteur TTS local :

- **Faire tourner un CONTROLE dans une autre langue sur le pipeline identique avant d'accuser
  l'installation.** Si l'anglais est parfait et le francais casse, le modele, le venv, le vocodeur
  et l'appel d'API sont innocentes : c'est la tete linguistique du moteur. Sans ce controle on
  cherche des heures un bug d'installation qui n'existe pas.
- **Isoler les couches avant d'accuser le clonage.** Transcrire l'audio AVANT conversion (TTS seul)
  et APRES. Ici les deux sont egalement degrades : la conversion vocale n'y est pour rien.
- **Ne jamais juger sur un clip isole de moins d'une seconde.** Whisper invente sur les clips courts
  (`la série` -> `Voici d'y`, `Hermès` -> `E-mess !`) : ces transcriptions ne prouvent rien.
  Toujours juger sur un paragraphe d'au moins 20-30 mots. `scripts/audit_tts.py` fait l'aller-retour.
  **La regle vaut aussi pour le SYNTHETISEUR, pas seulement pour Whisper** : une phrase courte isolee
  fait derailler le moteur lui-meme (Chatterbox force l'EOS et abime la fin de phrase), et un jeton qui
  echoue dans une sonde de 8 mots peut ressortir a 1,000 dans une phrase de longueur naturelle. Un
  echec de sonde est un tirage, pas un verdict — re-tester le jeton dans une phrase reelle avant de
  changer la graphie, de reecrire le script ou de supprimer le mot.
- **Verifier la couche graphie->phoneme separement de l'acoustique.** Imprimer les phonemes
  (`EspeakG2P(language="fr-fr")(texte)[0]`) : phonemes justes + audio faux = defaut de synthese,
  pas de graphie. Supprimer les accents de stress (`ˈ`, `ˌ`) ne corrige rien quand la synthese est
  en cause — c'est meme pire.
- **Ecrire les ordinaux en toutes lettres.** Le G2P espeak FR lit `7e` comme `sˈɛt ˈə` (« set e »)
  au lieu de `sɛtjˈɛm` ; `septième` rend correctement. Vaut pour tout moteur phonemise par
  espeak-ng (Kokoro, Piper) — meme famille de correctif que le labo de graphies XTTS.
- **Un signal propre n'est pas une diction correcte.** Mesurer bruit/crete SEPAREMENT du contenu :
  ici plancher -75,8 dBFS et 0 ecretage, et pourtant inintelligible. Ne pas conclure « pas de
  bruit » = « diction OK ».
- **Une duree cible annoncee a l'oreille se verifie par le nombre de mots** (~130-150 mots/min)
  avant de signaler un ecart : 18 mots annonces « 12-15 s » font en realite ~8 s.

## Piper (fr_FR-tom-medium) — narration FR stable, CPU, 40 s par rendu

Moteur retenu pour la narration longue quand le tirage d'un moteur autoregressif coute trop cher.
**Deterministe et non autoregressif** : un seul passage pour tout le script, aucun decoupage en
segments, aucun « garder le meilleur tirage », aucun GPU. Mesures sur une narration de 921 mots :
374,096 s d'audio (44100 Hz mono s16) en **40 s de CPU**, 0 phrase ajoutee, 0 boucle, derniere phrase
intacte. Installation, commandes exactes et tri des ecarts : `references/piper-narration-fr.md`.

- **Installer le binaire autonome, pas la roue.** `piper_windows_amd64.zip` de la release
  `rhasspy/piper` 2023.11.14-2 (22,5 Mo) : `piper.exe` + les 4 DLL + `espeak-ng-data/` doivent rester
  ENSEMBLE dans le meme dossier (le zip les met dans un sous-dossier `piper/` : deplacer le CONTENU
  puis supprimer le dossier vide). Les releases `OHF-Voice/piper1-gpl` ne publient que des roues
  Python — inutiles pour un `piper.exe`. Voix : `rhasspy/piper-voices` sur HuggingFace, `.onnx` **et**
  `.onnx.json` (le json porte le `sample_rate` et la voix espeak).
- **Ne pas supposer le sample rate d'une voix : le lire.** `fr_FR-tom-medium` sort en **44 100 Hz**,
  pas en 22 050 Hz comme les autres « medium ». Lire `audio.sample_rate` du `.onnx.json` et confirmer
  par `ffprobe` sur un essai de 5 s AVANT de calculer quoi que ce soit (atempo, resample, duree).
- **Alimenter par stdin, en UTF-8 sans BOM, tout le script en UNE passe.**
  `cat texte_utf8.txt | ./piper.exe --model voix.onnx --config voix.onnx.json --output_file out.wav --quiet`.
  Le script du projet peut avoir un BOM (`utf-8-sig`) : le relire en `utf-8-sig` et le reecrire en
  `utf-8` avant de l'envoyer, sinon le premier phoneme part en binaire.
- **Le texte doit rester SANS chiffres** (c'est deja le cas des scripts du projet) : Piper phonemise
  via espeak-ng FR, donc la regle « ordinaux en toutes lettres » et toute la classe nombres / port /
  URL s'appliquent ici comme sur Kokoro.
- **Ralentir : `atempo = duree_mesuree / duree_cible`, et ne PAS extrapoler `--length_scale`.**
  Mesure : 374,096 s -> 420 s = `atempo 0,890704` (`ffmpeg -af atempo=… -ar 24000` dans la meme
  passe, voix 12,3 % plus lente). L'alternative native `--length_scale 1,12274` (= 420/374,096 suppose
  lineaire) a rendu **413,55 s** : la duree n'est pas lineaire en `length_scale`. Garder l'atempo pour
  la conformite a la procedure, mais proposer le rendu natif en variante A/B.
- **Sortir les trois fichiers avec des noms explicites** : `…_nat` (44,1 kHz, sortie brute du moteur),
  le livrable ralenti 24 kHz, et `…_16k` pour MuseTalk (`ffmpeg -i final.wav -ar 16000 -c:a pcm_s16le`).
  Les confondre fait perdre la trace de ce qui a ete ralenti.
- **Trier les ecarts Whisper avant de conclure a un echec de diction.** Sur un texte dense en sigles,
  le seuil demande (0,90) se joue entierement sur ce tri : mesure **0,8865 brut / 0,9093 sigles
  normalises** sur la MEME prise. Artefact (audio juste) : `JEV` -> `gev` (en francais **J et G = meme
  son [ʒ]**), `Laya` -> `leia`, `RAG` -> `rhag`/`rhybe`, `L L M` -> `LLM`, `c'est` -> `cette`
  (homophones), `deux a cinq` -> `2 a 5`, `zéro virgule quatre-vingt-dix-huit` -> `0,98`, pluriels
  normalises, `Obsidian` -> `obsidien`, `Kokoclone` -> `coco clone`, `fail` -> `faille`. Vraie faute
  (mot francais ou terme deforme) : `protoagent` -> `protouage`, `GitHub` -> `jhub`, `git clone` ->
  `jclone`, `Markdown` -> `marklan`, `Si Yüan` -> `sidiouan`, `ONNX` -> `ox`, `une IA` -> `unia`,
  `MEMORY point M D / USER point M D` -> `md et usée md`. Automatiser : lister les opcodes non egaux
  de `difflib.SequenceMatcher` sur les mots normalises, puis separer ceux dont un cote est un
  sigle/nombre connu de ceux qui touchent un mot francais. **Rapporter les DEUX similarites.**
- **Verifier trois choses, pas une** : similarite, phrases AJOUTEES (transcript plus long que la
  reference), BOUCLES (6-grammes repetes >= 3x). 0 ajout et 0 boucle la ou un moteur autoregressif
  ajoutait une phrase parasite en fin de segment : c'est l'argument principal en faveur de Piper.
- **Chiffrer le rapport avec le bon outillage** : `ffprobe` imprime des VIRGULES sous locale francaise
  (`export LC_ALL=C` des qu'une duree est parsee en bash, sinon `printf` echoue sur `374,095873`),
  et `ffmpeg -v error` SUPPRIME la sortie de `volumedetect` (journalisee en info — l'appeler sans
  `-v error`). `max_volume: 0.0 dB` ne prouve pas l'ecretage : compter les echantillons a
  `abs(x) >= 32767` (ici 85 sur 16 497 628, ~2 ms, deja presents dans la sortie brute Piper, non
  causes par l'atempo).

## Chatterbox (chatterbox-tts 0.1.7) — narration FR clonee

Moteur de narration longue retenu a la place d'XTTS. Meme discipline que XTTS (sonder, segmenter,
verifier par Whisper), mais **aucune graphie phonetique** : le texte reste de l'orthographe normale,
donc lisible et corrigeable — et c'est une INTERDICTION, pas un confort (mesure ci-dessous). Recette
de sonde, API, mesures et pieges : `references/chatterbox-narration.md`.

- **Le labo de graphies d'XTTS NE TRANSFERE PAS a Chatterbox.** Respeller en phonetique fait epeler le
  sigle ou le denature, mesure sur les 11 segments d'une narration : `Ji-E-Vé` rendu `J V` / `JLV` /
  `J.E.V` (la graphie d'origine `JEV` passait telle quelle), `Si You-an` rendu `C-U-N`, `Omi-Raoute`
  rendu `au miraout` / `Omira ou Turag` (`Omni Route` rendait `OmniRoute`), `La-ya` rendu `l'aia`.
  Les deux seules reecritures qui aident (`Obsidian`->`Obsidiane`, `L L M`->`Èle-Èle-Ème` rendu `LLM`)
  ne compensent pas : moyenne des similarites **0,856 -> 0,839**, verdict complet **2/10 -> 1/11**.
  Seule reecriture utilisable : **reformuler la phrase** (`un repli regex : fail open,` ->
  `un repli par règle expresse : en cas de panne, la décision passe quand même,`), jamais respeller
  le terme.
- **Une reecriture phonetique n'est pas locale : elle change le tirage de TOUT le segment.** Le modele
  regenere differemment autour du terme touche — `trois piliers, JEV` (rendu juste au tirage
  precedent) est devenu `3 PIDs, JLV et`, une phrase entiere s'est ajoutee en fin de deux segments, et
  un segment a perdu ~35 mots. Juger une variante sur le segment ENTIER et sur tous les termes qui y
  apparaissent, jamais sur le seul terme reecrit ; pour comparer deux runs, recalculer la MEME
  metrique sur les deux jeux de transcriptions.

- **Venv dedie `data/chatterbox/.venv`** (torch 2.6.0+cu124). Mesures : LOAD 13-16 s, VRAM pic
  3,9 Go, ~9-12 s par phrase courte, sortie 24 kHz mono. `ChatterboxMultilingualTTS.from_pretrained(device="cuda")`
  puis `model.generate(texte, language_id="fr", audio_prompt_path=<voix_reference.wav>)`.
  **Deux installs coexistent :** `data/chatterbox` = 0.1.7 (`MODEL_VARIANT v2`, pas de `t3_model`) et
  `data/chatterbox_v3` = clone master (`MULTILINGUAL_T3_MODELS` present,
  `from_pretrained(device="cuda", t3_model="v3")`, LOAD_S 11,6, VRAM pic 4 461 Mo, 310 s de GPU pour
  11 segments / 268,0 s d'audio). Verifier `inspect.signature(...).parameters` au lieu de supposer la
  variante.
- **Le rapport mots/seconde par segment est le detecteur le moins cher d'un contenu perdu ou ajoute**,
  et il ne coute aucun GPU. Base mesuree sur 11 segments : **2,6-3,6 mots/s**. Un segment a
  5,33 mots/s (27,2 s pour 145 mots quand le tirage precedent en prenait 40,0) avec un transcript plus
  COURT que la reference = du contenu manque ; un transcript plus LONG que la reference = une phrase
  ajoutee. Les deux se sont produits sur le meme run, invisibles au seul score de similarite.
- **`ModuleNotFoundError: No module named 'pkg_resources'` au chargement de perth** = setuptools >= 81 :
  `uv pip install --python <venv>/Scripts/python.exe "setuptools<81"`. Sans ce correctif le modele
  plante a l'instanciation du watermarker, avant toute generation.
- **Pas de parametre `speed` dans 0.1.7.** Ralentir avec ffmpeg `atempo`, et CALCULER le facteur :
  `atempo = duree_mesuree / duree_cible`. **Le debit mesure sur des sondes courtes sous-estime le debit
  reel** : 128 mots/min sur des phrases isolees contre **187 mots/min mesures sur une narration complete**
  (921 mots -> 294,9 s). Ne jamais extrapoler une duree depuis des phrases isolees : mesurer le WAV
  concatene. Annoncer le facteur ET sa consequence audible : ici `294,9/420 = 0,702`, soit -30 % de
  debit, ce qui s'entend — le signaler, pas l'appliquer en silence.
- **Sonder les jetons risques AVANT la narration complete** : une phrase courte par graphie candidate,
  toutes dans UN SEUL processus (le chargement du modele coute plus cher que les generations), puis
  transcription Whisper `medium` en CPU et jugement sur mots de contenu MANQUANTS + mots EN TROP +
  presence de chaque jeton technique — la similarite seule ne suffit pas (0,990 avec une fin avalee).
- **Nombres, ports, URL et noms composes sont la classe qui casse : les retirer du texte parle plutot
  que de chercher une graphie.** Mesure : « 8 200 » passe (« 8200 ») mais « 6 806 » est perdu
  (« porc si croisant 6 »), et le passage d'URL echoue deux tirages de suite a l'identique (« GitHub »
  -> « Jtube », les deux « tiret » disparus). Mettre le port et le lien a l'ecran / dans la description
  YouTube — c'est aussi ce qui rend le script reutilisable par un autre utilisateur. « point com » se
  reduit proprement a « .com » : ne pas le corriger.
- **Compter les forcages d'EOS** (handler `logging` sur le logger racine, motifs `forcing EOS` /
  `repetition of token`) : present sur 3/3 des sondes y compris celles qui transcrivent parfaitement —
  signal de risque, pas preuve de defaut. Ce qui prouve la troncature est la disparition du DERNIER
  mot de contenu attendu (`indexe mes notes` -> `index mi-note`), pas l'horodatage du dernier segment.
- **Verdict par segment** : similarite >= 0,90 ET aucun jeton technique absent. Quatre pieges de ce
  verdict, tous mesures :
  - **Une variante morphologique ou une normalisation de Whisper est un PASS.** `indexe` transcrit
    `index`, `Niveau un` -> `Niveau 1`, `cinq principes` -> `5 principes`, `zéro virgule
    quatre-vingt-dix-huit` -> `0,98`, `Omni Route` -> `OmniRoute` : Whisper normalise nombres et
    composes, le score baisse alors que l'audio est juste. Un controle mot-a-mot strict fabrique des
    faux KO et fait reecrire un texte bon.
    **Filtrer le -s muet AVANT de juger, y compris sur les jetons critiques et les mots manquants.**
    Mesure du 04/10 sur 3 segments de complement : `En open source. Deja configures.` est revenu
    `deja configure.` et `mets un like` est revenu `met un like` — le -s final du pluriel francais est
    muet, Whisper ecrit ce qu'il entend, et le verdict automatique a rendu `A REVOIR` sur DEUX segments
    justes (sim 0,800 et 0,917). Trois faux KO emboites : la similarite, la liste des mots manquants
    (`configures` vs `configure`), ET la liste de jetons critiques comparee a l'orthographe de
    REFERENCE contre une hypothese deja normalisee. Recette : normaliser ref, hyp et la liste critique
    avec la meme regle (retirer le -s final des mots de 4 lettres et plus, appliquee des deux cotes
    donc sans risque), rapporter les DEUX similarites, et ne decider que sur la triee. Apres triage :
    0,800 -> 1,000 et 0,917 -> 1,000.
    **Sonder la SOURCE avant de coller, pas seulement les segments.** Une generation Chatterbox peut
    recoller un bout de phrase ULTERIEURE au milieu d'une phrase : mesure du 04/10, « Abonne-toi si tu
    veux suivre la suite de la serie [commentaire. Ca aide vraiment la chaine a se faire connaitre.
    Merci a tous] si tu veux suivre la suite de la serie Hermes. » au lieu de la phrase simple. Un
    diagnostic par blocs peut le manquer : relire la CTA mot a mot, horodatee, avant de conclure.
    **Placer une coupe sur le TIMING DES MOTS des que la zone a retirer est de la parole continue.**
    Un minimum d'energie ne trouve un blanc que s'il y en a un : la clause dupliquee ci-dessus etait
    continue (-12 dBFS de moyenne), et la coupe au minimum d'energie a laisse « ...serie a serie... »
    a l'oreille. Couper a la frontiere de mot donnee par Whisper (word_timestamps) + fondus de 8 ms :
    saut max a la collure 0,4-0,5x le p99,999 du fichier = pas de clic audible.
    **Juger sur la similarite CANONICALISEE, pas brute.** Whisper ne rend pas stablement les sigles
    epeles, les noms propres ni les nombres : texte lu correctement, on mesure 0,8917 brut / 0,8981
    apres triage du -s muet / 0,9560 apres canonicalisation (MEMORY point M D, Omni Route, zero
    virgule quatre-vingt-dix-huit -> 0,98, L L M, JEV/Laya/Si Yuan/GitHub). Sans cette etape on
    declare l'audio infidele a tort et on regenere pour rien.
    **Ne jamais dire qu'une phrase est absente avec un appariement par fenetre exacte.** Sur un texte
    a phrases proches ou repetees il fabrique ~50 fausses absences (mesure du 04/10) sur un audio bon.
    Mesurer les etendues non appariees (opcodes difflib) et la presence des mots de contenu.
  - **Une similarite haute ne prouve rien.** 0,955 avec `Shatterbox` (Chatterbox) et `Coco clone`
    (Kokoclone) dedans : ce qui fait le travail est la liste de jetons critiques construite depuis le
    texte du segment, pas le seuil.
  - **Accepter les graphies equivalentes d'un meme jeton** (espaces, accents, `point M D` rendu
    `.md`), sinon le controle fabrique des KO sur des segments bons.
  - **Comparer la similarite au texte D'ORIGINE, pas au texte respelle.** Les graphies a tirets se
    decoupent en plusieurs jetons (`A-nima` en deux), ce qui fait chuter le score d'une diction juste
    et rend le chiffre incomparable aux runs precedents. Mesurer aussi la similarite contre le texte
    respelle, mais c'est la premiere qui sert de critere.
  Segmenter par 6-12 phrases / 75-80 mots : **un segment trop long casse** (147 mots -> 0,708, phrases
  reordonnees et boucle en fin). Ne jamais fusionner le reliquat dans le dernier segment pour lui
  eviter d'etre court — lui donner son propre segment court.
- **Garder le MEILLEUR tirage, jamais le dernier, et le scorer AVANT de remplacer.** Mesure sur 11
  segments : regenerer a degrade 6 segments sur 11 (moyenne prise 1 = 0,835, prise 2 = 0,840) et un
  pipeline qui ecrase la prise 1 sans comparer detruit les bonnes (0,957 -> 0,879). Copier le WAV de
  cote quand le score s'ameliore, puis reconstruire l'assemblage depuis les meilleurs fichiers.
- **Si la premiere passe echoue au seuil sur la plupart des segments, arreter de regenerer.** Le
  tirage est une piece de monnaie, pas un levier (11 KO, 11 reprises, aucune amelioration moyenne).
  Le correctif est dans le TEXTE (retirer le jeton, le reecrire court) ou dans le choix du moteur :
  le rapport doit le dire et proposer les options, pas boucler sur le GPU.

## Reference Files
- `references/piper-narration-fr.md` — Piper : installation du binaire autonome, commandes, atempo vs length_scale, tri des ecarts Whisper, niveaux/ecretage
- `references/chatterbox-narration.md` — Chatterbox : API, recette de sonde, mesures des jetons risques, atempo
- `references/kokoro-kokoclone.md` — Kokoro-82M ONNX + Kanade : install, mesures, verdict FR
- `scripts/audit_tts.py` — aller-retour Whisper sur un WAV genere (audit de diction d'un moteur)
- `references/minimax-tts-api.md` — MiniMax T2A v2 : endpoint, voix FR, erreurs, pieges d'env
- `references/xtts-v2-setup.md`
- `references/french-diction-tricks.md`
- `references/fine-tune-xtts.md` — recette d'entrainement (corpus, pas, A/B) et les quatre pieges qui font echouer la mise en route
- `references/dependances-venv.md` — pins numpy/scikit-image du venv LatentSync (Python 3.10) : jamais de `pip install` sans pin
