# Worked example: VibeVoice TTS in Docker on Windows (RTX 3070 Ti, 8 GB)

Verified end-to-end Aug 2026. Community fork `vibevoice-community/VibeVoice` (official
`microsoft/VibeVoice` was removed then restored "without code"; the fork adds fine-tuning).
Depos: `torch` unpinned (keep the container's), `transformers==4.51.3`, `accelerate==1.6.0`,
`diffusers`, `gradio==5.50.0`, `librosa`, `av`, `aiortc`, `numba`/`llvmlite` — all have wheels.

## Corrected facts (guides get these wrong)
- Extra name is `streaming-web`, NOT `streamingtts` → `pip install -e .[streamingtts]` fails.
- Realtime demo script is `demo/streaming_inference_from_file.py`, NOT `vibevoice_realtime_demo.py`.
- "Streaming-0.5B" == HF model `microsoft/VibeVoice-Realtime-0.5B`.
- Real model sizes (HF API): 1.5B = 2.70B params (~5.4 GB), 7B/"Large" (`aoi-ot/VibeVoice-Large`
  or `vibevoice/VibeVoice-7B`) = 9.34B (~18.7 GB), Realtime-0.5B = 1.02B (~2 GB).
- On 8 GB: 0.5B and 1.5B run; 7B does NOT fit.
- `flash_attention_2` is requested by the demos on CUDA but has an automatic `sdpa` fallback —
  flash-attn is optional, skip the 30-60 min source build.

## Working commands (run inside `vibevoice-dev` container, from git-bash)
```bash
# install
MSYS_NO_PATHCONV=1 docker exec vibevoice-dev bash -c "cd /workspace/repo && PIP_EXTRA_INDEX_URL= pip install -e ."

# 1.5B — non-interactive, produces a wav (verify with ffprobe)
MSYS_NO_PATHCONV=1 docker exec vibevoice-dev bash -c "cd /workspace/repo && python demo/inference_from_file.py --model_path vibevoice/VibeVoice-1.5B --txt_path /workspace/test_1p.txt --speaker_names Alice --output_dir /workspace/outputs_1p --dtype bfloat16"

# Realtime-0.5B — streaming
MSYS_NO_PATHCONV=1 docker exec vibevoice-dev bash -c "cd /workspace/repo && python demo/streaming_inference_from_file.py --model_path microsoft/VibeVoice-Realtime-0.5B --txt_path /workspace/test_streaming.txt --speaker_name Emma --output_dir /workspace/outputs_streaming"

# Gradio web demo (1.5B) — detached, unbuffered so the URL flushes
MSYS_NO_PATHCONV=1 docker exec -d vibevoice-dev bash -c "cd /workspace/repo && python -u demo/gradio_demo.py --model_path vibevoice/VibeVoice-1.5B --share > /workspace/gradio.log 2>&1"
# then: grep -aE 'Running on' /workspace/gradio.log
```

## Text-input format
- `inference_from_file.py` (1.5B/7B): lines prefixed `Speaker 1: <text>`; `--speaker_names`
  maps `Speaker 1` → the name, which resolves to `demo/voices/en-<Name>_*.wav`.
- `streaming_inference_from_file.py` (0.5B): plain text, single speaker; `--speaker_name`
  resolves to `demo/voices/streaming_model/<name>.pt` (Emma, Carter, Mike, ...).

## Measured results (8 GB card)
- 1.5B: 10.5 s audio in 18.3 s (RTF 1.74x) — comfortable for short/medium text.
- Realtime-0.5B: 6.1 s audio in 7.7 s (RTF 1.25x).

## Notes
- One harmless pip warning: `cudf 24.4.0 requires pyarrow<15` — NGC ships RAPIDS; VibeVoice
  never imports cudf, ignore it.
- Project layout on host (mounted at /workspace): `repo/`, `hf_cache/`, `outputs_1p/`,
  `outputs_streaming/`, plus `test_1p.txt` / `test_streaming.txt` test scripts.
