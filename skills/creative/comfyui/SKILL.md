---
name: comfyui
description: Generate images, video, and audio via diffusion workflows.
version: 5.1.0
author: [kshitijk4poor, alt-glitch, purzbeats]
license: MIT
platforms: [macos, linux, windows]
compatibility: "Requires ComfyUI (local, Comfy Desktop, or Comfy Cloud) and comfy-cli (auto-installed via pipx/uvx by the setup script)."
prerequisites:
  commands: ["python"]
setup:
  help: "Run scripts/hardware_check.py FIRST to decide local vs Comfy Cloud; then scripts/comfyui_setup.sh auto-installs locally (or use Cloud API key for platform.comfy.org)."
metadata:
  hermes:
    tags:
      - comfyui
      - image-generation
      - stable-diffusion
      - flux
      - sd3
      - wan-video
      - hunyuan-video
      - creative
      - generative-ai
      - video-generation
    related_skills: [stable-diffusion]
    category: creative
---

# ComfyUI

Generate images, video, audio, and 3D content through ComfyUI using the
official `comfy-cli` for setup/lifecycle and direct REST/WebSocket API
for workflow execution.


## What's in this skill

**Reference docs (`references/`):**

- `references/official-cli.md` — every `comfy ...` command, with flags
- `references/rest-api.md` — REST + WebSocket endpoints (local + cloud), payload schemas
- `references/workflow-format.md` — API-format JSON, common node types, param mapping
- `references/template-integrity.md` — converting `comfyui-workflow-templates` from
  editor format to API format: Reroute bypass, dotted dynamic-input keys
  (`values.a`, `resize_type.width`), Cloud quirks (302 redirect, 1 concurrent
  free-tier job, 1080p VRAM ceiling), Discord-compatible ffmpeg stitch.
  Authored by [@purzbeats](https://github.com/purzbeats). Load this whenever
  you're starting from an official template.

**Scripts (`scripts/`):**

| Script | Purpose |
|--------|---------|
| `_common.py` | Shared HTTP, cloud routing, node catalogs (don't run directly) |
| `hardware_check.py` | Probe GPU/VRAM/disk → recommend local vs Comfy Cloud |
| `comfyui_setup.sh` | Hardware check + comfy-cli + ComfyUI install + launch + verify |
| `extract_schema.py` | Read a workflow → list controllable params + model deps |
| `check_deps.py` | Check workflow against running server → list missing nodes/models |
| `auto_fix_deps.py` | Run check_deps then `comfy node install` / `comfy model download` |
| `run_workflow.py` | Inject params, submit, monitor, download outputs (HTTP or WS) |
| `run_batch.py` | Submit a workflow N times with sweeps, parallel up to your tier |
| `ws_monitor.py` | Real-time WebSocket viewer for executing jobs (live progress) |
| `health_check.py` | Verification checklist runner — comfy-cli + server + models + smoke test |
| `fetch_logs.py` | Pull traceback / status messages for a given prompt_id |

**Example workflows (`workflows/`):** SD 1.5, SDXL, Flux Dev, SDXL img2img,
SDXL inpaint, ESRGAN upscale, AnimateDiff video, Wan T2V. See
`workflows/README.md`.

## References

This skill was split to meet the max 200-line rule. Details are in `references/`:

| Section | File |
|---------|------|
| When to Use | `references/when-to-use.md` |
| Architecture: Two Layers | `references/architecture-two-layers.md` |
| Quick Start | `references/quick-start.md` |
| Core Workflow | `references/core-workflow.md` |
| Decision Tree | `references/decision-tree.md` |
| Setup & Onboarding | `references/setup-onboarding.md` |
| Image Upload (img2img / Inpainting) | `references/image-upload-img2img-inpainting.md` |
| Cloud Specifics | `references/cloud-specifics.md` |
| Queue & System Management | `references/queue-system-management.md` |
| Pitfalls | `references/pitfalls.md` |
| Verification Checklist | `references/verification-checklist.md` |

> All reference files are verbatim extracts — no logic changed.

