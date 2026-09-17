---
name: video-assembly
description: "Assemble, sync, and source video content — music-synced montage, cloud API video, and GIF search."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [video, ffmpeg, montage, music, gif, api, curl, descript, json2video, librosa]
    related_skills: [video-editing-automation, talking-head-video]
    merged_from: [ffmpeg-music-montage, gif-search, video-api-integration]
    archive: .archive/media/
---

# Video Assembly (Umbrella)

Use when the user wants to assemble, sync, or source video/GIF content — from
music-synced montage (programmatic ffmpeg), cloud API video assembly, or GIF
search. Covers local ffmpeg workflows, cloud API rendering, and GIF sourcing.

## 1 — Music-Synced Montage (FFmpeg + Librosa)

Cut a montage from multiple source clips to a music track. Each segment's
**source clip** and **transition** are chosen from audio energy at that moment
(calm → slow footage, energetic → action footage).

**When to use:** "Montage alterné synchronisé sur la musique X", "Cut to the
beat", beat/energy-driven montage covering full audio length.

### Windows Command-Line Cap (8191 chars)

Large montages (60+ segments + xfade filter) hit cmd.exe's length limit.
**Fix:** `-filter_complex_script graph.txt` (or `-/filter_complex <file>` on
ffmpeg 8.x).

### Segmentation (librosa onset)

```python
import librosa, numpy as np, json
y, sr = librosa.load("music.wav", sr=22050)
C = np.abs(librosa.stft(y))
onset_env = librosa.onset.onset_strength(S=C, sr=sr, aggregate=np.median)
frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, backtrack=True, units="frames")
times = librosa.frames_to_time(frames, sr=sr).tolist()
json.dump({"onsets": times, "sr": sr, "duration": float(len(y)/sr)}, open("onsets.json","w"), indent=2)
```

### Segment Selection

```python
def energy_at(onset_env, sr, t, window=0.3):
    hop = 512
    idx = int(t * sr / hop)
    w = int(window * sr / hop)
    return float(np.mean(onset_env[max(0,idx-w):idx+w+1]))

def choose_seg(energy, calm_segs, action_segs, threshold=0.4):
    pool = action_segs if energy > threshold else calm_segs
    if pool: return random.choice(pool)
    return random.choice(calm_segs + action_segs)
```

### FFmpeg Encode + Concat

- Encode segments to h264/aac fixed params, copy to `segments/`.
- Build xfade chain (xfade=fade:duration=0.5:offset=N) in `filter.txt`.
- Concat with filter script: `ffmpeg -f concat -i segments.txt -filter_complex_script filter.txt ...`
- See archived `ffmpeg-music-montage` for full script.

## 2 — Cloud Video APIs (JSON2Video / Descript)

External APIs assemble large, captioned videos without local ffmpeg.

**When to use:** Long video (>10 min), cloud rendering needed, Descript/JSON2Video
is installed.

| Provider | CLI/API | Best for | Cost |
|---|---|---|---|
| **JSON2Video** | REST + JS lib | API-driven, integrable, captions | Pay-per-min |
| **Descript** | CLI (`descript`) | Fast local templates, transcription | Subscription |

### JSON2Video

```bash
npm install json2video
```

```javascript
const json2video = require("json2video");
const movie = {
  scenes: [{ elements: [{ type: "text", text: "Title", duration: 5 }],
    transition: { type: "fade", duration: 1 } }]};
json2video.render({ movie, output: "output.mp4" }).then(() => console.log("Done"));
```

### Descript CLI

```bash
descript new-project --name "My Video"
descript add-media --project "My Video" --input clips/*.mp4
descript add-caption --project "My Video" --input script.txt --position bottom-center
descript export --project "My Video" --output output.mp4
```

## 3 — GIF Search (Tenor API)

Search and download animated GIFs from Tenor.

**When to use:** "GIF of...", search for a specific animated GIF, add a GIF to a
message.

### Requirements

- curl, jq
- Tenor API key (free: https://developers.google.com/tenor/guides/quickstart)

### One-liner

```bash
curl -s "https://tenor.googleapis.com/v2/search?q=KEYWORD&key=YOUR_KEY&limit=5&media_filter=gif" \
  | jq -r '.results[] | "\(.media_formats.gif.url)\t\(.content_description)"'
```

### Script Pattern

```bash
#!/usr/bin/env bash
Q="${1:?Query required}"; KEY="${TENOR_API_KEY:?Set TENOR_API_KEY}"
RESP=$(curl -s "https://tenor.googleapis.com/v2/search?q=$(printf '%s' "$Q" | jq -sRr @uri)&key=$KEY&limit=5&media_filter=gif")
echo "$RESP" | jq -r '.results[] | "[\(.content_description)] \(.media_formats.gif.url)"'
```

## Cross-references

- **video-editing-automation** — Premiere Pro XML → FFmpeg path (protected skill).
- **talking-head-video** — Lip-sync a portrait to audio (protected skill).
