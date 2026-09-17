---
name: model-ops
description: "Model Hub + NVIDIA NIM APIs — download/upload models from HuggingFace, inference via NVIDIA cloud."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [huggingface, nvidia, nim, models, datasets, vision, llm, image-gen]
    category: mlops
    created: "2026-09-10"
    umbrella_of: [huggingface-hub, nvidia-nim]
---

# Model Ops — HuggingFace Hub + NVIDIA NIM

Router for model hub operations and NVIDIA cloud inference. Each sub-skill is a standalone reference.

## When to Use

- **HuggingFace Hub** (`hf` CLI): search, download, upload models/datasets/spaces
- **NVIDIA NIM**: vision LLM, image generation (Stable Diffusion/SDXL/FLUX), synthetic video detection
- Do NOT use for local LLM ops (`llm-ops`), TTS/voice cloning (`tts-voice-cloning`), or long-form TTS (`vibevoice-tts`) — those are protected standalone skills

## HuggingFace Hub — routing

Use when: installing `hf` CLI, authenticating, downloading/uploading models or datasets, managing repos, spaces, or gated access.

Key commands: `hf download`, `hf upload`, `hf auth login`, `hf repos create`, `hf repos duplicate`, `hf mirror set`, `hf scan cache`.

Auth: `HF_TOKEN` env var or `--token` flag. API keys: `hf_` prefix from huggingface.co/settings/tokens.

See `references/huggingface-hub.md` (81l).

## NVIDIA NIM — routing

Use when: need a vision LLM, image generation via cloud, or synthetic video detection (NVIDIA Synthetic Video Detector).

Key points:
- API keys start with `nvapi-`, free at build.nvidia.com
- Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions` (OpenAI-compatible)
- Vision input: use base64 data URL, not remote URL
- Image gen: `https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl`
- SVD: `https://ai.api.nvidia.com/v1/genai/nvidia/synthetic-video-detector`

See `references/nvidia-nim.md` (145l).

## Proteges — non inclus

- `llm-ops` (protege, 85l, 2026-09-08) — inference locale GGUF/vLLM
- `tts-voice-cloning` (protege, 46l, 2026-09-07) — XTTS-v2 Coqui
- `vibevoice-tts` (protege, 68l, 2026-09-04) — long-form TTS

## References

- `references/huggingface-hub.md` — verbatim from `mlops/huggingface-hub/` (archived 2026-09-10)
- `references/nvidia-nim.md` — verbatim from `mlops/nvidia-nim/` (archived 2026-09-10)
