---
name: vibevoice-tts
description: "Use for VibeVoice TTS: voice cloning and long-form audio."
---

# VibeVoice TTS (voice cloning + long-form synthesis)

VibeVoice is a local text-to-speech model (community fork `vibevoice-community/VibeVoice`, since the Microsoft repo was emptied then restored without code). The user uses it to clone their own voice and narrate podcast episodes / animated-character dialogue. It is long-form (up to ~90 min, up to 4 speakers) using next-token diffusion.

## Environment (already installed on the user's tower)
- Docker container `vibevoice-dev` (image `nvcr.io/nvidia/pytorch:24.07-py3`), GPU passthrough working.
- Root dir `C:\Users\searc\AppData\Local\hermes\data\vibevoice\` is mounted at `/workspace` inside the container:
  - `repo/` = the fork clone (editable install already done via `pip install -e .`)
  - `hf_cache/` = HuggingFace cache (models already downloaded)
  - `voices_personnages/` = user's voice-reference .wav files + `README.txt` (recording guide: mono, 16 kHz min / 24 kHz ideal, 10-30 s, calm)
  - `outputs_*/` = generated WAVs
- Launcher script: `vibevoice.sh` (subcommands: `demo`, `clone`, `stream`, `infer`, `status`, `stop`). Run with `bash vibevoice.sh ...` from the root dir.
- GPU: RTX 3070 Ti, 8 GB VRAM (64 GB RAM).

## Models (verified sizes — trust these, not marketing numbers)
- `vibevoice/VibeVoice-1.5B` = 2.7B params (~5.4 GB bf16). Long-form 64K ctx, up to 4 speakers. FITS on 8 GB.
- `microsoft/VibeVoice-Realtime-0.5B` = 1.0B params (~2 GB). Streaming.
- `vibevoice/VibeVoice-7B` / "Large" (`aoi-ot/VibeVoice-Large`) = 9.3B params (~18.7 GB). DOES NOT fit 8 GB — do not attempt.

## CRITICAL VRAM constraint
Only ONE 1.5B model fits at a time (~5.4 GB of 8 GB). The Gradio demo and any CLI inference each load the model. Therefore:
- Before any CLI cloning/generation: STOP the demo (`bash vibevoice.sh stop`, or kill the `gradio_demo.py` process — see references/docker-windows-gotchas.md for the safe kill pattern).
- Running the demo and a CLI inference simultaneously = CUDA OOM.

## Voice cloning mechanism (zero-shot)
`demo/inference_from_file.py` scans `repo/demo/voices/*.wav` and maps filename → speaker name (strips `_...` and language `-...` prefixes: `en-Alice_woman.wav` → `Alice`; `MaVoix.wav` → `MaVoix`).
- To clone a custom voice: place a reference .wav in `repo/demo/voices/` (24 kHz mono, 10-30 s), then reference it with `--speaker_names <Name>`.
- Text goes in a FILE via `--txt_path`, in `Speaker 1: ...` format. Multi-speaker = `Speaker 2: ...` lines + `--speaker_names A B` (order follows first appearance; up to 4 speakers).
- Cloning is ON by default (`is_prefill=True`); `--disable_prefill` turns it off.

## Commands
Clone a single voice (ffmpeg-normalizes to 24 kHz mono, copies into `demo/voices/<Name>.wav`, generates a test clip):
```
bash vibevoice.sh clone --ref voices_personnages/Jean.wav --name Jean --text "Bonjour." --out outputs_clone
# output: outputs_clone/Jean_generated.wav
```
Long-form generation (full episode/narration), direct:
```
docker exec -it vibevoice-dev bash -c "cd /workspace/repo && python demo/inference_from_file.py --model_path vibevoice/VibeVoice-1.5B --txt_path /workspace/episode2.txt --speaker_names MaVoix --output_dir /workspace/outputs_episode2"
```
Gradio UI: `bash vibevoice.sh demo` → http://localhost:7860

## Pitfalls
- Text is passed via a FILE (`--txt_path`), never inline, in `Speaker N: ...` format.
- French text pasted by the user routinely LOSES its elision apostrophes (`l'Anima`→`lAnima`, `n'était`→`nétait`, `s'élevaient`→`sélevaient`). RESTORE them before synthesis or the reading is wrong.
- The Gradio UI has NO voice-upload field; its "Speaker N" dropdowns only list `demo/voices/*.wav` (populated at launch). To use a custom voice in the UI, copy its .wav into `demo/voices/` and restart the demo.
- Reference audio: mono 24 kHz ideal; the `clone` helper's ffmpeg step auto-converts (handles 48 kHz stereo).
- flash-attn is optional (falls back to sdpa); the NGC pytorch container already bundles it, so no extra install is needed.
- Throughput: RTF ≈ 1.8-2.0x → ~4 min of audio takes ~7 min to generate. Use `terminal(background=true, notify_on_complete=true)` for long runs.
- Model output is 24 kHz mono WAV. To pick the "best" reference clip without listening, compare `ffmpeg -i x.wav -af volumedetect -f null -` — highest `mean_volume` with a clean (non-clipping) peak wins.
- **ASR (transcription): `microsoft/VibeVoice-ASR` is 17.35 GB (8 shards, Qwen2.5-7B backbone) and will NOT fit 8 GB VRAM.** Don't attempt it on this tower. Use `faster-whisper` instead (already `pip install`ed in the container): `WhisperModel("medium", device="cuda", compute_type="float16").transcribe(wav, language="fr", beam_size=5, vad_filter=True)` → ~1-2 min for a 6-min clip, no GPU pressure. The ASR demo script (`vibevoice_asr_inference_from_file.py`) has NO `--output_dir` arg — it prints to stdout only, so capture and write the txt yourself.
- **`pkill -f gradio_demo` self-kills inside `docker exec bash -c '...'`** (the shell's own cmdline contains the pattern → exit 143/SIGTERM). To check VRAM instead, just run `nvidia-smi`; nothing else needs killing if the container was freshly started.
- **VoiceMapper strips `_...` suffixes and the LAST file wins.** `MaVoix_v2.wav` → stripped key `MaVoix`, which OVERWRITES the key set by `MaVoix.wav`. VERIFIED 2026-08-24: with both files present, `--speaker_names MaVoix` resolved to `MaVoix_v2.wav` (the log line `Speaker 1 ('MaVoix') -> Voice: MaVoix_v2.wav` states which file was actually used — always read it). An earlier version of this note claimed the exact filename key survives; that is WRONG. To target a specific file unambiguously, either pass the full suffixed name (`--speaker_names MaVoix_v2`) or keep only one `MaVoix*.wav` in `demo/voices/`. (In practice `MaVoix.wav` and `MaVoix_v2.wav` are byte-identical — same md5 `87f28bcc...` — so the swap is harmless there.)
- **The finetune script takes NO single-wav / voice-name arguments.** `vibevoice/finetune/train_vibevoice.py` (invoked as `python -m vibevoice.finetune.train_vibevoice`) requires a DATASET: `--dataset_name <hf_repo>` or `--train_jsonl <path>` with `{text, audio}` records whose text is `"Speaker 1: ..."`. There is no `--voice_sample`, no `--name`. So requests like "fine-tune on this one .wav" cannot be honored as-is — and are unnecessary: zero-shot prefill cloning is the native mechanism and needs no training. The repo's own `FINETUNING.md` example targets a 24 GB card (batch 8) and warns the implementation is unvalidated by the authors; its recommended single-voice setting (`voice_prompt_drop_rate 1.0`) DISABLES voice cloning on the resulting model.
- **Docker Desktop is often not running.** Symptom: `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`. Fix: launch `"/c/Program Files/Docker/Docker/Docker Desktop.exe"` with `terminal(background=true)` (a bare `&` is rejected by the tool), poll `docker info` until it succeeds (~10-30 s), then `docker start vibevoice-dev` — the container is usually left in `Exited (255)` after a host reboot.
- **Check `nvidia-smi` BEFORE generating: the user's Adobe apps eat the VRAM.** Premiere Pro 2026 + Photoshop 2026 + Edge WebViews routinely hold ~5 GB of the 8 GB, leaving ~3 GB — not enough for the 5.4 GB model. `nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv` names the culprits. Ask the user to close them rather than killing their work; poll `memory.free` until ≥ 6000 MiB. Reference: a 12 s clip generated in 21.8 s (RTF 1.82x) once VRAM was free.
- Voice files live in `C:\Users\searc\Desktop\the cypher\clone\` (NOT `...\smll talk\clone\` — that path doesn't exist). That folder holds **`mavoix1.wav` … `mavoix6.wav` — there is NO `MaVoix.wav` there.** All six are 5 721 294 bytes, 48 kHz stereo, 29.72 s, but they are SIX DISTINCT TAKES (different md5). The folder is NOT mounted in the container; copy the needed wav into `/workspace/...` host-side rather than recreating the container.
- **`mavoix5.wav` is the validated take.** VERIFIED 2026-08-24: `ffmpeg -i mavoix5.wav -ac 1 -ar 24000 -c:a pcm_s16le out.wav` reproduces md5 `87f28bcc...` byte-for-byte — the exact content of the already-approved `demo/voices/MaVoix.wav` and `MaVoix_v2.wav`. It is also the objectively best take (`mean_volume -16.5 dB`, peak `-1.3 dB`, no clipping; the others sit at -18 dB). Default to mavoix5 unless the user asks otherwise. To re-identify a take after the fact, normalize each candidate and compare md5 against the reference in `demo/voices/`.
- **Output filename is derived from the txt basename**, not from the voice: `--txt_path /workspace/texte_gen.txt` → `<output_dir>/texte_gen_generated.wav`. Use a distinct txt name per run and previous outputs in the same `--output_dir` are preserved untouched (important: the user is adamant that validated artifacts must never be overwritten).
- **Naming a copied reference to force an explicit mapping:** `get_voice_path()` tries an EXACT key match first, and `voice_presets.update(new_dict)` only overwrites the *stripped* keys — so full names like `MaVoix_cypher` always resolve to `MaVoix_cypher.wav` even when `MaVoix.wav`/`MaVoix_v2.wav` coexist. Confirm with the log line `Speaker 1 ('X') -> Voice: X.wav` before trusting a run. (Bare `MaVoix` would instead hit whichever `MaVoix_*` sorts last alphabetically.)

## Reference
- `references/docker-windows-gotchas.md` — Docker-on-Windows (git-bash) gotchas that bite when operating this container.
