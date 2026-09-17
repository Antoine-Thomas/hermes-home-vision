---
name: audio-event-detection
description: Detect specific sounds with YAMNet to trigger actions.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [audio, yamnet, sound-classification, surveillance, tensorflow, sounddevice]
---

# Audio Event Detection (YAMNet)

## When to Use

- Detect a specific sound (glass breaking, door slam/forced entry, knock, siren,
  dog bark) in a live mic stream or a recording, and trigger an action on detection.
- Build a "sound trigger" (surveillance alert, capture-on-noise, event logging).
- NOT for speech/transcription (use STT/Whisper) or music analysis (use librosa).

Detect **specific sounds** (glass breaking, door slam, knock, siren, dog bark …) in a
live microphone stream or recorded audio, and **trigger an action** (capture video,
send a Telegram alert, log an event) when a target class fires with confidence.

This is the reliable, pre-trained way to do "sound-based triggers" — a persona file
(SOUL.md) or a simple loudness threshold will NOT do this. YAMNet is Google's
AudioSet model: 521 classes, runs in real time on CPU.

## Architecture

```
microphone ──sounddevice InputStream──▶ 1 s buffer ──YAMNet──▶ scores ──▶ threshold+cooldown ──▶ trigger (ffmpeg video + Telegram)
```

- **Capture**: `sounddevice.InputStream` at 16 kHz mono (YAMNet's expected rate), callback → queue.
- **Classify**: feed 1 s of float32 audio `[-1,1]` to YAMNet → `scores [num_frames, 521]`.
- **Decide**: max score over the *target class subset* ≥ threshold (0.5) → trigger. Cooldown (60 s) prevents spam.
- **Act**: ffmpeg `dshow` capture 15 s video+audio, send via Telegram `sendVideo`.

## Setup (Windows, Python 3.11)

```bash
# Pin Python 3.11 — TensorFlow has NO wheels for cp314 (max cp313). `uv venv` defaults
# to the newest Python, so force the interpreter explicitly.
uv venv --python "C:/Users/<you>/AppData/Local/Programs/Python/Python311/python.exe" venv
uv pip install --python venv/Scripts/python.exe \
  "tensorflow==2.16.1" "tensorflow-hub==0.16.1" sounddevice soundfile numpy requests
# REQUIRED: tensorflow-hub 0.16.1 imports pkg_resources, removed in setuptools>=81.
uv pip install --python venv/Scripts/python.exe "setuptools<81"
```

## YAMNet usage

```python
import tensorflow_hub as hub
import numpy as np

model = hub.load("https://tfhub.dev/google/yamnet/1")   # ~100 MB downloaded to cache on 1st run

waveform = np.zeros(16000, dtype=np.float32)             # 1 s, 16 kHz, [-1,1]
scores, embeddings, spectrogram = model(waveform)         # scores: [num_frames, 521]
```

- **Input is 1D** `[N]` — NOT a 2D batch. Passing `waveform[np.newaxis,:]` raises
  `TypeError: Can not cast TensorSpec(shape=(1,N)) to (None,)`.
- **Class map** (index → display_name) is NOT shipped in the model; fetch and cache it:
  `https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv`
- **Target subset**: match display-name keywords, then exclude false positives. For
  break-in detection:
  - `TARGET_KEYWORDS = ["glass","shatter","break","smash","door","slam","bang","crash","knock","impact"]`
  - `EXCLUDE_KEYWORDS = ["doorbell","bell","cymbal","keyboard","mouse","typewriter","engine"]`
    ("Engine knocking" matches "knock" — must exclude; "doorbell" is not a break-in.)

## Detection loop (threshold + cooldown)

- Single 1 s window with a target-class score ≥ 0.5 is enough for a **brief** event
  (glass shatter is ~200 ms). Don't require "sustained" detection or you'll miss it.
- Cooldown (60 s) stops duplicate triggers from echoes/reverb.
- Verified calibration: quiet room → `Glass 0.000` (no false trigger); real glass
  shatter sample → `Shatter 0.965` (triggers). Lower threshold to 0.3 for more
  sensitivity, raise to 0.7 for fewer false positives.

## Pitfalls (all hit in practice)

1. **TF needs Python ≤3.13.** `uv venv` picks the newest Python (3.14) by default →
   "no wheels with a matching Python ABI tag". Always `--python <3.11 path>`.
2. **`ModuleNotFoundError: pkg_resources`** on `import tensorflow_hub` → pin
   `setuptools<81` (hub 0.16.1 is pre-removal).
3. **2D input TypeError** → pass 1D waveform, and use `scores.numpy()` (full
   `[num_frames,521]`), not `[0]`.
4. **Wrong mic selected** → "Microsoft Sound Mapper" matches the substring
   "Microsoft" and grabs the default device. Match `"LifeCam" in name and "Microphone" in name`
   (or the exact device name), not just "Microsoft".
5. **Mic contention** → a second process (surveillance.ps1, OBS, Teams) holding the
   `dshow` mic will lock it. Run ONE audio consumer at a time.
6. **`Start-Process -ArgumentList '"C:\path"'`** (PowerShell backtick-quote) passes
   literal quotes → Python can't find the file. For a path with no spaces, pass the
   variable unquoted (`-ArgumentList $script`).

7. **`uv venv` python.exe is a launcher stub** — `venv/Scripts/python.exe` (~274 KB)
   spawns the base interpreter (~103 KB) as a child, so ONE script = TWO `python.exe`
   OS processes (stub + real python, same CreationDate, parent→child). When counting
   "how many instances are running", filter on `Name='python.exe'` AND the script path,
   and expect 2 processes per single script — don't kill a healthy process thinking it
   is a duplicate. A launcher/watcher check like `CommandLine -like '*script.py*'` also
   self-matches your own diagnostic command, so always filter by `Name=` too.

8. **Mechanical/continuous noise (GPU/PC fan) misclassifies as "glass" ~0.6.** A mic mounted on the PC tower picks up the graphics-card fan when it spins up; YAMNet scores it "Glass" ~0.6, above the 0.5 default → false break-in alerts. Raise `THRESHOLD` to **0.8** (real glass shatter is 0.8–0.95; fan ~0.6) and keep the cooldown. The REAL fix is physical — move the mic off the tower; a software threshold only reduces, never eliminates, the false positives. When you change `THRESHOLD`, the running loop must be RESTARTED to pick it up (an idempotent launcher like `guardian-launch.ps1` exits early while the old process is still alive — kill the `*guardian.py*` python process first, then re-run the launcher / `Start-ScheduledTask`).

## Trigger action (video + Telegram)

```python
# 15 s video+audio from the webcam, then delete after send
cmd = ["ffmpeg","-hide_banner","-loglevel","error","-y",
       "-f","dshow","-i",f"video={CAMERA}","-f","dshow","-i",f"audio={MIC}",
       "-map","0:v","-map","1:a","-t","15","-c:v","libx264","-c:a","aac",
       "-pix_fmt","yuv420p","-movflags","+faststart", out]
import requests
requests.post(f"https://api.telegram.org/bot{token}/sendVideo",
              data={"chat_id": CHAT_ID, "caption": cap}, files={"video": open(out,"rb")})
```

## Verification

- `--selftest <audio.mp3>` classifies a file and prints the best target class + score.
- Ambient clip should score ~0.0; a glass/door sample should score ≥0.5.
- See `references/yamnet-breakin.md` for the exact class list and test numbers.
