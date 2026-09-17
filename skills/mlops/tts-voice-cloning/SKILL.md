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
- Reference audio: 24 kHz mono, 10–30 s (`mavoix5.wav` = validated take, in
  `data/vibevoice/repo/demo/voices/`).

## Lessons and Pitfalls

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

## Reference Files
- `references/xtts-v2-setup.md`
- `references/french-diction-tricks.md`
- `references/fine-tune-xtts.md` — recette d'entrainement (corpus, pas, A/B) et les quatre pieges qui font echouer la mise en route
