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
- **Generate segment-by-segment** (one file per paragraph, then concat with a
  ~0.35 s gap) so a single mangled segment can be re-generated alone instead of
  redoing the whole ~5 min voice.
- Reference audio: 24 kHz mono, 10–30 s (`mavoix5.wav` = validated take, in
  `data/vibevoice/repo/demo/voices/`).

## Lessons and Pitfalls

- **Phonetic Pronunciation:** French proper nouns or technical terms (like \"Hermes Agent\") may be cut or mispronounced.
  - **Fix:** Use phonetic spelling in the text (e.g., \"Hermès ... Agent\" with an accent and ellipsis for a natural pause).
  - **Verification:** Always generate a short test (10-15s) with the target phrase before committing to a 5-minute render.
- **GPU Incompatibility:** XTTS-v2 requires `gpu=True` for speed, but ensure the venv has the matching CUDA torch version (cu124 for local 13.x setup usually works).

## Reference Files
- `references/xtts-v2-setup.md`
- `references/french-diction-tricks.md`
