# ASR transcription with faster-whisper (French)

Why not VibeVoice-ASR: `microsoft/VibeVoice-ASR` is 17.35 GB (8 safetensors shards, Qwen2.5-7B backbone) and won't fit the 8 GB GPU. faster-whisper is the working replacement.

## Install (once)
```
MSYS_NO_PATHCONV=1 docker exec vibevoice-dev bash -c 'PIP_EXTRA_INDEX_URL= pip install --quiet faster-whisper'
```
`PIP_EXTRA_INDEX_URL=` clears the dead NGC extra-index so pip doesn't burn retries per package. Confirm with `python -c "import faster_whisper; print(faster_whisper.__version__)"` (expect 1.x).

## Transcribe script (write to /workspace on the host, run in container)
```python
# transcribe_whisper.py
import os, re
os.environ.setdefault("HF_HOME", "/workspace/hf_cache")
os.environ.setdefault("HF_HUB_CACHE", "/workspace/hf_cache/hub")
from faster_whisper import WhisperModel

model = WhisperModel("medium", device="cuda", compute_type="float16")
segments, info = model.transcribe(
    "/workspace/<input>.wav", language="fr", beam_size=5, vad_filter=True)
text = re.sub(r"\s+", " ", " ".join(s.text.strip() for s in segments)).strip()
open("/workspace/<out>.txt", "w", encoding="utf-8").write(f"Speaker 1: {text}\n")
print("duration", round(info.duration, 2), "lang", info.language, "prob", round(info.language_probability, 3))
```
Run: `MSYS_NO_PATHCONV=1 docker exec vibevoice-dev bash -c 'cd /workspace && python transcribe_whisper.py'`

Model sizes: `small` (~461 MB), `medium` (~1.5 GB, good French default), `large-v3` (~3 GB). medium ≈ 10x real-time on GPU → 6.4 min of audio ≈ 1 min.

## Cleanup (transcription is only as good as the audio)
- The user's source audio can contain SPOKEN SSML markup (e.g. "Speak version égale 1.0 xmlns égale http ... prosody voice speak") — from a prior TTS that read its own tags aloud. Strip those blocks before synthesis or they get re-read as gibberish.
- faster-whisper mangles rare nouns: "dodécaèdre" → "dos des caèdres" (recurring across the whole clip). Restore key proper nouns.
- Normalize protagonist spelling to the canonical name ("Kaël"/"Cael" → "Kael") so the narration stays consistent with the episode text.
- Clean PROGRAMMATICALLY (exact `str.replace` on the substrings), not by retyping a 1000+ word transcript by hand.
