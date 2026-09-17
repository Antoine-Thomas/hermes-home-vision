---
name: media-analysis
description: "Router: audio event detection (YAMNet sound triggers) and YouTube transcript extraction."
version: 1.0.0
metadata:
  hermes:
    tags: [media, audio, yamnet, sound-classification, surveillance, youtube, transcripts]
    category: media
---

# Media Analysis

One router for media analysis: sound-based event detection (YAMNet) and
YouTube transcript extraction / transformation.

Consolidates the former `audio-event-detection` and `youtube-content` skills
(archived under `.archive/media/`). Each original SKILL.md is preserved
verbatim under `references/` with an archive-source header; their supporting
reference/script files are copied alongside.

## When to Use

- Detect specific sounds (glass break, door slam, siren) and trigger actions -> `references/audio-event-detection.md`
- Extract a YouTube transcript and reformat it (summary, chapters, thread, blog) -> `references/youtube-content.md`

## Routing

| Request | Reference |
|---|---|
| Sound detection / sound-triggered actions (YAMNet) | `references/audio-event-detection.md` |
| YouTube transcript -> summary/thread/blog | `references/youtube-content.md` |

## Quick Start

```bash
# YouTube transcript (uv installs into the Hermes env) — full usage in references/youtube-content.md
uv pip install youtube-transcript-api
uv run python scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID" --text-only --timestamps

# Audio detection (Windows, Python 3.11) — see references/audio-event-detection.md
uv venv --python "C:/Users/<you>/AppData/Local/Programs/Python/Python311/python.exe" venv
uv pip install --python venv/Scripts/python.exe "tensorflow==2.16.1" "tensorflow-hub==0.16.1" sounddevice soundfile numpy requests
```

## References

- `references/audio-event-detection.md` — verbatim original (setup, YAMNet loop, pitfalls, trigger).
- `references/youtube-content.md` — verbatim original (setup, helper script, output formats, errors).
- `references/yamnet-breakin.md` — YAMNet break-in class list + test numbers.
- `references/output-formats.md` — YouTube transcript output formats.

## Scripts

- `scripts/guardian-watchdog.vbs` — watchdog launcher (audio detection).
- `scripts/fetch_transcript.py` — YouTube transcript fetcher.

## Key Pitfalls

- TensorFlow needs Python <=3.13; pin `setuptools<81` for tensorflow-hub 0.16.1.
- YAMNet input is 1D, not 2D; raise THRESHOLD to 0.8 to kill fan-noise false positives.
- YouTube: retry without `--language` if transcript empty; transcripts may be disabled.
