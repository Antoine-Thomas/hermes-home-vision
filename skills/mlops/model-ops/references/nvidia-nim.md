<!-- Source: mlops/nvidia-nim/SKILL.md (archived 2026-09-10) -->
---
name: nvidia-nim
description: Use NVIDIA NIM APIs for LLM, vision, and video detection.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [nvidia, nim, vision, llm, synthetic-video-detector, stable-diffusion, gemma]
---

# NVIDIA NIM Cloud API

## When to Use

- Need a **vision LLM** when no local vision model is available (this profile's
  `vision_analyze` has no vision backend — NVIDIA NIM fills that gap).
- Detect whether a video is **AI-generated / synthetic** (NVIDIA Synthetic Video
  Detector) — useful for YouTube AI-content disclosure checks or media forensics.
- **Image generation** via NVIDIA-hosted Stable Diffusion / SDXL / FLUX.

## Auth

- API keys start with `nvapi-`, created free at https://build.nvidia.com (one key
  works across all NIM catalog endpoints).
- This user's keys live in `C:\Users\searc\AppData\Local\hermes\data\nvidia\.env`
  (env vars `NVIDIA_API_KEY_SVD`, `NVIDIA_API_KEY_SD`, `NVIDIA_API_KEY_GEMMA4`).
  **Never** put the keys in memory or echo them in chat.

## LLM + Vision (OpenAI-compatible)

Endpoint `https://integrate.api.nvidia.com/v1/chat/completions` — drop-in
OpenAI-compatible. Model names are prefixed by vendor, e.g.
`google/gemma-4-31b-it`, `meta/llama-3.3-70b-instruct`, `nvidia/nemotron-...`.

```python
import requests
url = "https://integrate.api.nvidia.com/v1/chat/completions"
headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
payload = {
    "messages": [{"role": "user", "content": "Say OK"}],
    "model": "google/gemma-4-31b-it", "max_tokens": 16, "stream": False,
}
r = requests.post(url, headers=headers, json=payload, timeout=180)
print(r.json()["choices"][0]["message"]["content"])
```

### Vision input — use base64 data URL, not a remote URL

For LOCAL images, base64-encode and inline as a data URL. Passing a remote image
`url` makes the NVIDIA server download it, which can hang/timeout on the first
call. Base64 is deterministic:

```python
import base64
with open(img_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
content = [
    {"type": "text", "text": "Describe this image."},
    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
]
payload["messages"] = [{"role": "user", "content": content}]
```

- 31B models (gemma-4-31b) are SLOW — text-only is fine (~HTTP 200 in seconds),
  but the first vision call may take minutes (cold start + image tokens). Use a
  generous `timeout` (≥300 s) or run in `terminal(background=True)` with notify.
  `enable_thinking: True` (chain-of-thought) adds a lot of latency — omit it
  unless you want reasoning.
- **For vision, use `meta/llama-3.2-11b-vision-instruct`** — returns HTTP 200 in
  seconds. `google/gemma-4-31b-it` vision returns HTTP **504** (gateway timeout —
  too heavy for the free tier), so do NOT use gemma-4 for image input; it's fine
  for text-only chat.
- List every available model: `GET https://integrate.api.nvidia.com/v1/models`
  (Bearer key) → ~82 models across LLM, vision, code, embedding, safety, and
  translation.

## Synthetic Video Detector (SVD)

Detects AI-generated video: output is a per-frame probability in [0,1]
(0 = real, 1 = synthetic). Threshold for "synthetic" is **0.3**
(`CLASSIFICATION_THRESHOLD` in the client).

- **Function ID (NVCF cloud): `847b6e53-0133-452d-ab85-d7acf3ace723`** — required
  for the hosted/preview endpoint.
- Client: `git clone --depth 1 https://github.com/NVIDIA-Maxine/nim-clients.git`
  → `nim-clients/synthetic-video-detector/`. Run the script in `--preview-mode`
  against the hosted NVCF server (gRPC):

```bash
cd nim-clients/synthetic-video-detector/scripts
python synthetic-video-detector.py --preview-mode \
  --target grpc.nvcf.nvidia.com:443 \
  --function-id 847b6e53-0133-452d-ab85-d7acf3ace723 \
  --api-key "$NVIDIA_API_KEY_SVD" \
  --video-input /path/to/video.mp4 --save-csv
```

- Input: **MP4 with H.264 codec only**, ≤ 500 MB.
- The client needs `grpcio` + deps (`pip install -r nim-clients/synthetic-video-detector/requirements.txt`).

## Stable Diffusion / image & video gen

NVIDIA hosts diffusion models under the same key, at a model-specific base URL
`https://ai.api.nvidia.com/v1/genai/{vendor}/{slug}` (SDXL, SD 3.5, FLUX, Cosmos
video, Edify image). Video gen (Cosmos/Edify) returns `202 Accepted` + an
`NVCF-REQID` header and must be polled at
`https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{reqid}`.

### Working text-to-image (FLUX.1-schnell)

`black-forest-labs/flux.1-schnell` is the free/fast image model that actually
works on a free `nvapi-` key:

```python
url = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell"
payload = {"prompt": "...", "width": 1024, "height": 1024,
           "cfg_scale": 0, "steps": 4, "seed": 42, "mode": "base"}
r = requests.post(url, headers=H, json=payload, timeout=900)
b64 = r.json()["artifacts"][0]["base64"]   # base64 PNG → base64.b64decode + write file
```

- `mode` MUST be `"base"` (NOT `"text-to-image"` — that returns 422 `literal_error`).
- `cfg_scale` MUST be `<= 0` for schnell (422 `less_than_equal` otherwise).
- `stabilityai/sdxl-turbo` and `stabilityai/stable-diffusion-3-5-large` return
  **404** on free keys (gated) — use `black-forest-labs/flux.1-schnell`.
- First generation is slow (cold start) → long `timeout` (≥600 s) or
  `terminal(background=True)`; retry once if it times out.
- ⚠️ **Image GEN is unreliable on a free key.** This session FLUX.1-schnell
  returned HTTP **504** on EVERY generation (text-to-image AND img2img), even with
  correct params (`mode="base"`, `cfg_scale=0`) and ≥600s timeouts — retries did
  NOT recover. Chat/vision endpoints were unaffected (only image *gen* 504s).
  Don't build a workflow that hard-depends on free-tier image gen: keep a local
  fallback — PIL/ffmpeg gradient for backgrounds, or ComfyUI for real
  img2img/inpainting (e.g. adding a t-shirt to a portrait).

## Pitfalls

- **First call to a large model is slow** (cold start). A request that "times
  out" on the first try usually succeeds on retry once the model is warm — retry
  with a longer timeout before concluding the endpoint is broken.
- **Remote image URLs can hang** — always prefer base64 data URLs for local
  files.
- The `nvapi-` key is free and credit-metered; heavy use depletes fast. Pool it
  with other free providers rather than making it a high-volume primary.
