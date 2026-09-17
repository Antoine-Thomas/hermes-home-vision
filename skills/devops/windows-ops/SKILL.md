---
name: windows-ops
description: "Operations Windows: GPU Docker sur WSL2 et tuning performance."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [windows, docker, gpu, wsl2]
    category: devops
    created: "2026-09-10"
    umbrella_of: [docker-gpu-windows]
    notes: "windows-performance-tuning (protege, 42l) et windows-system-backup (hors devops, 37l) non inclus — notes seulement"
---

# Windows Ops

Operations Windows DevOps : GPU Docker et systeme.

## When to Use

- Lancer des conteneurs GPU sur Windows (Docker Desktop + WSL2)
- Besoin de `wsl --update`, `nvidia-smi`, runtime nvidia

## Docker GPU — resume

- Prerequis WSL2, driver NVIDIA, Docker Desktop.
- Verification `docker run --gpus all nvidia/cuda nvidia-smi`.
- Pieges : WSL kernel, passthrough, toolkit.

Voir `references/docker-gpu-windows.md` (108l).

## Skills lies non inclus

- `windows-performance-tuning` — protege (2026-09-03, 42l), reste independant
- `windows-system-backup` — hors devops (37l, `skills/windows-system-backup`), note seulement

## References

- `references/docker-gpu-windows.md` — procedure GPU Docker Windows
