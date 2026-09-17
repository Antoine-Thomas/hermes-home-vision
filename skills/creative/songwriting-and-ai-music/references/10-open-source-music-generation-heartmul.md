# 10. Open-Source Music Generation: HeartMuLa

> Source: `creative/songwriting-and-ai-music/SKILL.md` — split on 2026-09-10 to meet max 200 lines rule.

HeartMuLa is a family of open-source music foundation models (Apache-2.0) that generates music from lyrics + tags — a free, local alternative to Suno.

**When to use:** The user wants local/offline music generation, an open-source Suno alternative, or asks about HeartMuLa / heartlib.

**Hardware:** Minimum 8GB VRAM (`--lazy_load true`), recommended 16GB+. 3B model peaks at ~6.2GB VRAM with lazy loading. CPU-only is possible but extremely slow (30-60+ min per song).

**Quick setup:**
```bash
git clone https://github.com/HeartMuLa/heartlib.git && cd heartlib
uv venv --python 3.10 .venv && . .venv/bin/activate && uv pip install -e .
uv pip install --upgrade datasets transformers  # fix dependency conflicts
```

**Critical patches (required for transformers 5.x):**
In `src/heartlib/heartmula/modeling_heartmula.py`, add RoPE cache reinitialization after `reset_caches` and before the `with device:` block. In `src/heartlib/pipelines/music_generation.py`, add `ignore_mismatched_sizes=True` to all `HeartCodec.from_pretrained()` calls.

**Download models:**
```bash
hf download --local-dir './ckpt' 'HeartMuLa/HeartMuLaGen'
hf download --local-dir './ckpt/HeartMuLa-oss-3B' 'HeartMuLa/HeartMuLa-oss-3B-happy-new-year'
hf download --local-dir './ckpt/HeartCodec-oss' 'HeartMuLa/HeartCodec-oss-20260123'
```

**Basic generation:**
```bash
python ./examples/run_music_generation.py \
  --model_path=./ckpt --version="3B" \
  --lyrics="./assets/lyrics.txt" --tags="./assets/tags.txt" \
  --save_path="./assets/output.mp3" --lazy_load true
```

**Tags format:** `piano,happy,wedding,synthesizer,romantic` (comma-separated, no spaces).
**Lyrics format:** Use bracketed structural tags `[Intro]`, `[Verse]`, `[Chorus]`, `[Bridge]`, `[Outro]`.

**Key parameters:** `--max_audio_length_ms` (default 240000 = 4 min), `--topk 50`, `--temperature 1.0`, `--cfg_scale 1.5`.

**Pitfalls:**
- Do NOT use bf16 for HeartCodec — use fp32 (default). bf16 degrades audio quality.
- Tags may be ignored (known issue #90); lyrics tend to dominate.
- Triton not available on macOS — Linux/CUDA only.
- RTX 5080 incompatibility reported in upstream issues.
- Performance: RTF ≈ 1.0 — a 4-minute song takes ~4 minutes.

---
