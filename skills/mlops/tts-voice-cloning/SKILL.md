---
name: tts-voice-cloning
description: Use when cloning a voice or generating speech locally — XTTS-v2 (Coqui) for natural French, VibeVoice for long-form/multi-speaker.
---

# Local TTS + Voice Cloning (XTTS-v2 + VibeVoice)

## When to use
User wants to clone a voice or generate speech locally. Two engines are installed:
- **XTTS-v2 (Coqui)** — PREFERRED for natural FRENCH (VibeVoice's French output has a foreign accent + diction bugs).
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
- **GPU Incompatibility:** XTTS-v2 requires `gpu=True` for speed, but ensure the venv has the matching CUDA torch version (cu124 for local 13.x setup usually works).

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

## Reference Files
- `references/xtts-v2-setup.md`
- `references/french-diction-tricks.md`
- `references/fine-tune-xtts.md` — recette d'entrainement (corpus, pas, A/B) et les quatre pieges qui font echouer la mise en route
