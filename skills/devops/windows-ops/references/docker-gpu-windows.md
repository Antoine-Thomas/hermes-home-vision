<!-- Source: docker-gpu-windows/SKILL.md -->
---
name: docker-gpu-windows
description: Run GPU Docker containers on Windows (Docker Desktop).
---

# Docker + GPU on Windows (Docker Desktop / WSL2)

Run GPU-accelerated containers (NGC PyTorch/CUDA images, ML models) on a Windows host.
Docker Desktop here uses a WSL2 Linux engine, so most Linux-native `docker run` flags from
tutorials need adaptation. This skill encodes the working pattern plus the pitfalls.

## When to use
- User asks to run/deploy a GPU model, PyTorch app, or NGC container on Windows via Docker.
- A Docker-based install guide uses `sudo`, `--net=host`, or interactive `-it --rm` (Linux habits).
- Installing Python deps inside an NVIDIA NGC container and pip is slow/retrying.

## 1. Start the daemon (it is often NOT running)
Docker Desktop installs but does not auto-start. WSL distros (`docker-desktop`, `Ubuntu`)
sit in `Stopped` state. The `docker` CLI then fails with:
`failed to connect ... npipe:////./pipe/dockerDesktopLinuxEngine`.

Launch it and poll until ready:
```bash
powershell.exe -NoProfile -Command "Start-Process -FilePath 'C:\Program Files\Docker\Docker\Docker Desktop.exe'"
for i in $(seq 1 36); do docker info >/dev/null 2>&1 && break; sleep 5; done
docker info --format '{{.ServerVersion}} {{.OSType}}'
```
`cmd //c start "" "..."` is unreliable from git-bash; prefer PowerShell `Start-Process`.

## 2. Verify GPU passthrough BEFORE pulling the big image
Test with a small CUDA image (~100 MB) so a broken `--gpus all` fails fast, not after a 15 GB pull:
```bash
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```
If this prints the GPU, passthrough works (WSL2 backend + host NVIDIA driver are enough;
no separate nvidia-container-toolkit install inside the docker-desktop distro is needed).
Record actual VRAM: `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader`.

## 3. Windows flag adaptations (the big three)
| Linux-tutorial flag | On Windows Docker Desktop |
|---|---|
| `sudo docker` | drop `sudo` (not needed / not present) |
| `--net=host` | UNSUPPORTED — use default bridge + `-p <port>:<port>` |
| `-it --rm` (one-shot) | replace with a **persistent named container** (below) |

`--privileged --ipc=host --ulimit memlock=-1:-1 --ulimit stack=-1:-1` all work and are fine to keep.

## 4. Persistent container pattern (multi-step installs)
A multi-step install (`git clone` → `pip install` → run demo) cannot survive `--rm -it`.
Create ONE named container that stays alive, then drive it with `docker exec`:
```bash
MSYS_NO_PATHCONV=1 docker run -d --name <name> \
  --gpus all --privileged --ipc=host \
  --ulimit memlock=-1:-1 --ulimit stack=-1:-1 \
  -v C:/path/on/host:/workspace \
  -e HF_HOME=/workspace/hf_cache \
  -p 7860:7860 \
  nvcr.io/nvidia/pytorch:24.07-py3 sleep infinity
```
- `sleep infinity` keeps it alive without an interactive TTY.
- Mount a **host dir** for code + model cache so work survives container recreation.
- `HF_HOME` (or `HF_HUB_CACHE`) inside the mount → HuggingFace models persist, no re-download.
- Clone the repo on the HOST (inspectable) and mount it; `pip install -e .` in the container
  picks it up via the mount — no in-container `git clone` needed.

## 5. NGC containers: dead pip extra-index (very common, very slow)
NGC images ship `/etc/pip.conf` with `extra-index-url=https://pypi.ngc.nvidia.com`. That
mirror no longer resolves, so EVERY `pip install` logs
`WARNING: Retrying ... Name or service not known` per package and falls back to pypi.org
(slow but eventually works). Fix by clearing the extra index:
```bash
PIP_EXTRA_INDEX_URL= pip install -e .          # or --index-url https://pypi.org/simple
```
Diagnose first: `pip config list` → if it shows `global.extra-index-url='...ngc...'`, that's the cause.
Confirm real PyPI is reachable: `curl -sI https://pypi.org/simple/ | head -1`.

## 6. MSYS path mangling (git-bash only)
In git-bash/MSYS, container paths starting with `/` (e.g. `/workspace`) may be rewritten to
`C:/Program Files/Git/...`. Prefix `docker`/`docker exec` with `MSYS_NO_PATHCONV=1` whenever a
command contains a container path that starts with `/`.

## 7. VRAM sanity check before committing to a model
bf16 weights ≈ 2 bytes/param. Check the real param count from the HF API, not the model's
marketing name (e.g. "1.5B" can be a 2.7B-param model, "7B" can be 9.3B params):
```bash
curl -s https://huggingface.co/api/models/<org>/<model> | python -c "import sys,json;print(json.load(sys.stdin)['safetensors']['total'])"
```
- ~2B params → ~4 GB; ~3B → ~6 GB; ~9B → ~18 GB.
- On an 8 GB card: ~1B-2B param models are comfortable, ~3B is tight, ~9B is impossible.
- flag this BEFORE running, don't let the user assume a big model will fit.

## 8. Verification: generate a real output, don't just launch a server
Prefer a non-interactive CLI script that produces a file over "start the Gradio server and
eyeball the log". Verify the artifact with `ls -la` + `ffprobe` (duration/size), not just exit 0.
For a web demo that must be reached from the host, note that code often binds `127.0.0.1`
unless `--share` (which sets `0.0.0.0`) — so `-p 7860:7860` alone won't expose a loopback-bound
server. Use `--share` (binds 0.0.0.0) but warn that the public URL exposes the GPU to anyone with
the link. Run servers detached with `python -u ... > /log 2>&1` so the URL flushes to the log
(block-buffered stdout otherwise holds the "Running on public URL" line indefinitely).

## Pitfalls recap
- Daemon down is the #1 "docker command fails" cause on Windows — start Docker Desktop first.
- NGC pip extra-index is dead → clear it (`PIP_EXTRA_INDEX_URL=`).
- `--net=host` and `sudo` don't exist on Docker Desktop Windows.
- `--rm -it` cannot carry a multi-step install — use a named `-d ... sleep infinity` container.
- Always `MSYS_NO_PATHCONV=1` for docker commands with `/`-prefixed container paths.

See `references/vibevoice-install.md` for a complete worked example (VibeVoice TTS on an 8 GB card).
