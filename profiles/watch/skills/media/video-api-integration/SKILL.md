---
name: video-api-integration
description: Choose JSON2Video/Descript or local ffmpeg for big video.
version: 1
author: hermes-agent
license: mit
metadata:
  hermes:
    tags: [video, api, json2video, descript, ffmpeg, 4k]
    related_skills: [windows-scheduled-tasks]
---

# Video API Integration (Hermes)

Use when the user wants to edit/generate video via API, or when deciding between a
cloud video API and local ffmpeg for a large local source.

## When to Use
- User asks to wire up Descript, JSON2Video, or another video API into Hermes.
- User has a large local source (4K/60, multi-GB) and wants cloud montage — stop
  and explain the upload cap before installing anything.
- User wants auto-subtitles, silence removal, or Studio Sound on smaller clips.
- User wants templated/social video generation from text + images.

## Decision rule (most important)
Cloud APIs cannot ingest huge local files.
- JSON2Video upload cap: **500 MB** (verified in docs). A 7 GB 4K60 source is rejected.
- For LOCAL-source editing (cut, xfade, audio swap, encode), use **ffmpeg locally**.
- Reserve cloud APIs for: templated social clips (JSON2Video) or speech editing of
  smaller files (Descript silence removal, auto subtitles, Studio Sound).
- Hybrid pattern: ffmpeg does cut/xfade/audio/encode; cloud API adds value only where
  ffmpeg can't (speech edit, auto-subtitle export, Studio Sound).

## JSON2Video — references/json2video.md
- Install: `pip install json2video` (v2.0.0, official PyPI). Works in a venv.
- SDK reality (read the package, not blog posts): classes `Movie`/`Scene` (no `Client`);
  `render()` is **async** → wrap in `asyncio.run()`; `Movie.set()` has a property
  allowlist and **"soundtrack" is NOT a key** — add audio as an `audio` element;
  auth via header **`x-api-key`** (not Bearer); caption/subtitle elements exist.
- Free tier adds a watermark; 4K counts 4x the quota. Endpoint `/v1/movies`.

## Descript — references/descript.md
- Base URL: `https://descriptapi.com/v1` (NOT `api.descript.com`). Auth:
  `Authorization: Bearer <token>`. Beta/paid — HTTP 401 without a valid token.
- **GOTCHA**: `pip install descript` is a FALSE FRIEND — it manipulates `descript.ion`
  files and is unrelated to Descript the app. There is **no official Python SDK**.
  The official client is Node `@descript/platform-cli`. Write a small REST client.
- Verified endpoints: `POST /jobs/import/project_media`, `POST /jobs/agent`
  (silence removal etc.), `POST /jobs/publish` (480p→4K), `POST /export/transcript`
  (returns SRT), `GET /jobs/{job_id}`.

## Secrets (mandatory)
Read keys from env vars: `JSON2VIDEO_API_KEY`, `DESCRIPT_API_TOKEN`. Never hardcode.
Scripts must dry-run safely when the key is absent (print payload / skip call).

## Support files
- `references/json2video.md` — SDK 2.0.0 real API shape + limits.
- `references/descript.md` — real endpoints + false-friend warning.
