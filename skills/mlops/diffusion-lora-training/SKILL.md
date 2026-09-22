---
name: diffusion-lora-training
description: Use when training a local diffusion LoRA.
version: 1.0.0
license: MIT
platforms: [windows, linux]
metadata:
  hermes:
    tags: [lora, sdxl, stable-diffusion, diffusers, dreambooth, dataset-curation, insightface, vram, training]
    related_skills: [llm-ops, tts-voice-cloning, python-dependency-guard]
---

# Local diffusion LoRA training (face / style)

Building a dataset, training an SDXL or SD1.5 LoRA locally, and deciding with measurements whether
the chain is viable on this machine BEFORE committing hours of GPU or a photo session.

## Standing rules for this user

- **One dedicated venv per chain**, under `%LOCALAPPDATA%\hermes\data\<chain>\venv`. Never install
  into the existing AI venvs (LatentSync, XTTS, LTX-2.3, RAG) and never touch Hermes `config.yaml`.
- **Downloads are budgeted and announced.** Measure the real download before starting: torch alone
  can be 2.5 GB before the model. Price it and check the pip cache first — a wheel already cached
  costs nothing and leaves the whole budget for the model weight. Recipe and pin discipline:
  `references/dependency-budget-and-pins.md`.
- **Pin the library set in one command before installing anything else**, and never let a major
  version float: a fresh venv resolves the newest of everything, which is how a working chain breaks.
- **Short trial before any long run** (~300 steps, or 3 steps when diagnosing). No asset collection
  (photo session, dataset purchase) until the chain has produced a checkpoint.
- **On a dependency conflict: stop and report the exact error.** Do not improvise a workaround, and
  do not escalate to a heavier alternative (Docker, another framework) without an explicit go-ahead.
- **Report measured numbers only.** No checkpoint produced means "no images" — never describe,
  invent or extrapolate a generated image, and never invent a duration, a VRAM figure or a loss.

## Step 1 — triage the corpus on FACE size, not image resolution

A 6000x4000 frame where the subject stands 5 m away yields a 400 px face and is unusable; a phone
shot with a 1000 px face is ideal. Filtering on image resolution selects the wrong photos.

- Detect the face (InsightFace, well provided by the LatentSync venv). Require exactly one face,
  small side >= 512 px, large side >= 700 px.
- Sharpness = variance of the Laplacian measured **inside the face box**, never on the whole image.
- Exposure: reject when more than ~2 % of the face area is clipped at 0 or 255.
- Calibrating the sharpness threshold on the corpus median mechanically removes about half the
  corpus. That is acceptable as a first pass, but say it out loud: Laplacian variance is not
  comparable between a 24 Mpx close-up and a phone photo, so the cut is partly arbitrary.
- Classify the kept photos with a vision model in parallel batches (one subagent per <= 8 images,
  returning compact JSON): angle, expression, background, framing, and one `doute` boolean. Expect
  the vision model to contradict itself between passes — record the doubt instead of faking certainty.
- **Check the angle mix before training, not after.** Target for identity: ~35 % face, ~30 %
  three-quarter, ~20 % profile, ~15 % high/low angle. A corpus that is 75 % frontal trains a
  frontal-only identity; say so and let the user decide rather than reporting success.
- Crop a square centred on the face with ~1.5x the face size as margin, resize to the training
  resolution (1024 for SDXL), and keep the source photos read-only.

## Step 2 — captions

One caption per image: a unique trigger token plus the attributes read off the image (angle,
expression, light/background). **Keep the caption files in a folder OUTSIDE the image folder** —
see the pitfall below.

## Step 3 — model prep

- **kohya_ss no longer ships the command-line training scripts**: a clone gives the GUI only. Do not
  build a chain on it. Use the official diffusers example script instead
  (`examples/dreambooth/train_dreambooth_lora_sdxl.py`), which runs on the released PyPI diffusers.
- **Pin the library quartet before anything else**: `transformers<5` with the pair proven on the
  machine — `transformers==4.57.6` + `diffusers==0.36.0` + `peft>=0.17` + `accelerate>=1.4`. Letting
  transformers 5.x in breaks the diffusers and peft imports with messages that name peft and hide
  the real cause. Full rule in `mlops/llm-ops`. numpy 2.x (`numpy>=2,<3`, tested 2.4.6) is fine on
  torch 2.4.1+cu118 here: `torch.from_numpy` and the EulerDiscreteScheduler path both work. Fall
  back to `numpy==1.26.4` only if a specific scheduler actually raises `Numpy is not available`.
- The example script needs the model in **diffusers format** (a folder), not a single-file
  checkpoint. Convert locally — no extra download:
  `StableDiffusionXLPipeline.from_single_file(src, torch_dtype=torch.float16).save_pretrained(dst)`.

## Step 4 — launch

```bash
V="$LOCALAPPDATA/hermes/data/sdxl_lora"
cd "$V" && "$V/venv/Scripts/python.exe" -m accelerate.commands.launch \
  --num_processes 1 --mixed_precision fp16 "$V/train_lora_sdxl.py" \
  --pretrained_model_name_or_path="$V/sdxl_base_diffusers" \
  --instance_data_dir="<images only>" --instance_prompt="<trigger>" \
  --resolution=1024 --train_batch_size=1 --gradient_accumulation_steps=4 \
  --gradient_checkpointing --optimizer=adafactor \
  --learning_rate=1e-4 --lr_scheduler=cosine --lr_warmup_steps=100 \
  --max_train_steps=3 --rank=16 --checkpointing_steps=500 --seed=42 \
  --output_dir="$V/lora_essai" --mixed_precision=fp16 --report_to=tensorboard
```

- Wrap the launch in `timeout <seconds>` for a hard cap, and sample VRAM independently in the
  background (`nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits` every 30 s into a
  file) so the max survives even if the run is killed at the cap. A ready-made sampler lives in
  `scripts/sampler_vram.sh`.
- Set `--checkpointing_steps` low enough that a trial actually writes something to test; a 500-step
  interval on a 3-step trial produces no artifact at all.
- Capture the run's log to a file and archive it before the next attempt overwrites it — an
  eight-line traceback is the whole diagnosis.

## Step 5 — decide with measurements, never with impressions

Measure, per trial: seconds per step (progress-bar timestamps), VRAM max (sampler file), loss
first/last, steps reached, and any error verbatim.

- **Sample `nvidia-smi` DURING the run and read `utilization.gpu` against `utilization.memory`.**
  100 % GPU with ~1 % memory means the kernels are slow, not the data path — that rules out
  swap/paging and points at compute.
- **Change one variable per trial and re-measure.** On this RTX 3070 Ti 8 GB, SDXL LoRA measured
  207 s/step at 1024 px and 38 s/step at 512 px, with dedicated VRAM pegged at ~7.9/8.2 GB and
  ~1.1 GB spilling into shared memory in both cases — the step time tracked the spill plus the
  compute, not resolution alone.
- **On an 8 GB card the working path is SD 1.5, not SDXL.** SD 1.5 LoRA (`train_text_to_image_lora.py`,
  512 px, rank 16, grad ckpt, 8-bit Adam) measured **~1.8 s/step, 3.4 GB VRAM, ~0.13 GB shared, 61 °C,
  ~172 W** on this machine: no spill, and it draws *more* power than SDXL because the GPU actually
  works. Same dataset, same card: SDXL 1024 = 207 s/step, SD 1.5 512 = 1.8 s/step.
- **SD 1.5 recipe pitfalls (all hit in practice).** The script needs `datasets` installed in the venv.
  `--dataloader_num_workers` must stay `0` on Windows, else workers die with `AttributeError: Can't
  pickle local object 'main.<locals>.preprocess_train'`. Images + `.txt` sidecars are NOT enough:
  `load_dataset("imagefolder")` only exposes the `text` column when a `metadata.jsonl`
  (`{"file_name": …, "text": …}` per line) sits in the folder, otherwise `--caption_column=text`
  fails with `needs to be one of: image`. `lora_alpha` is hardcoded to `args.rank` upstream — patch it
  when alpha ≠ rank. `--variant=fp16` works with the `stable-diffusion-v1-5/stable-diffusion-v1-5` repo.
  The HF repo is 45 GB total, of which ~23 GB are single-file `.ckpt`/`.safetensors` duplicates the
  diffusers script never reads.
- **300 steps is not enough to judge a face LoRA.** At 300 steps the LoRA visibly shifts the output
  (older, grey-haired man vs the base model) but weight 0.8 gives the wrong expression and weight 1.0
  deforms the face. Budget 1500–2000 steps (~1 h at 1.8 s/step) before evaluating identity.
- **1'800-step SD 1.5 baseline on 8 GB (validated end to end):** 512 px, rank 16 / alpha 8, grad ckpt,
  8-bit Adam → **53 min, 1.77 s/step, 3.5 GB VRAM, 0.20 GB shared memory (flat, no spill), 62 °C,
  184 W, zero nvlddmkm / Kernel-Power events**. Treat ~1.8 s/step and ~3.5 GB as the reference for
  any face-LoRA ETA on this class of card.
- **`--checkpoints_total_limit` silently deletes the older checkpoints.** With `checkpointing_steps=300`
  and `total_limit=3`, only the last three survive (1200/1500/1800), so don't set a limit and then
  expect to inspect every intermediate. Each LoRA checkpoint is only ~13 MB of weights plus optimizer
  state — keeping all of them is cheap; cap the limit only if you truly need the disk.
- **Evaluate LoRA strength at 0.6 first, not 1.0.** At 1800 steps, scale 0.6 gives a clean, neutral
  portrait matching the references, 0.8 is acceptable but drifts, and 1.0 deforms the face. Testing at
  `cross_attention_kwargs={"scale": w}` is more reliable than fuse/unfuse cycles and keeps one loaded
  pipeline for all weights. A 3-point sweep (0.6/0.8/1.0) on the same seed is enough to pick a weight.
- **Detect a plateau before spending more GPU time.** Regenerate at the SAME seed, prompt and weight
  after extra steps and compare the two PNGs numerically (mean abs diff + correlation on the RGB
  array, numpy only). Correlation > 0.98 (≈2 % mean diff) means the extra steps changed essentially
  nothing: the LoRA has plateaued and more steps will NOT improve resemblance — the dataset is the
  bottleneck. Measure this instead of guessing, and report it.
- **A frontal-only face dataset caps identity, and no number of steps fixes it.** Count angles before
  training: 26 crops that are 22 frontal (12 identical neutral front shots) with a single three-quarter
  and no profile produce a LoRA that learns "middle-aged man, grey hair, grey beard" but not the actual
  features — and it stays that way at 1800 and at 2500 steps. Aim for ≥ 6 three-quarter and ≥ 4 profile
  crops from the start; re-use the photos a quality filter rejected (angle variety often ranks below
  sharpness in a sharpness-sorted filter).
- **Do not trust a gateway vision model for a likeness verdict.** Asked to compare references against
  generated faces, it returned "same person" and "different person" in one answer and flipped hair
  colour between calls on the same image. Build a side-by-side contact sheet instead (PIL: references
  on the top row, generations below, one label per cell) and hand THAT to the user — their eye is the
  only reliable judge. Use the vision model only for crude checks ("is there a face at all").
- **Face-embedding scores need models that may not be local.** InsightFace `buffalo_l` is a download;
  check `~/.insightface/models` and the training venv (`pip list | grep insightface`) before promising
  a cosine-similarity verdict — an unrelated Python install having the package is not enough, and
  installing it is a download that needs the user's approval.
- **Audit the corpus angles BEFORE enriching, with a measurement.** Run every source photo through
  InsightFace (`FaceAnalysis('buffalo_l')`, `.get(img)` → `face.pose` = [pitch, yaw, roll] in degrees)
  and tabulate yaw. A corpus that looks like "40 selfies" can contain literally zero profiles
  (max |yaw| 43°): no re-cropping, upsampling or step count invents the missing volume information,
  and the promised "add ~6 profiles" target may be unreachable — say so instead of spending an hour
  of GPU on it. This also classifies angles objectively, replacing a vision model's guesswork.
- **Never filter a corpus on a MEDIAN sharpness threshold.** Cutting at the median guarantees that
  half the photos are dropped by construction, however good they are: a set where the last keep is
  57.1 and the first drop is 55.9 loses photos on a 2 % difference. Use an absolute Laplacian floor
  (~40 for multi-megapixel portraits) and report the distribution.
- **Match the sharpness distribution across angle groups when rebalancing.** Newly harvested
  three-quarter crops are often the softest images in the set: pairing each of them with a frontal
  of similar Laplacian variance stops the model from learning "three-quarter = blurry", which is a
  confound that survives any amount of extra steps. Greedy nearest-value matching is enough.
- **`--random_flip` destroys left/right in captions.** With it on, "de trois-quarts gauche" and
  "de trois-quarts droit" are the same image to the model: it learns "head turned" but never which
  way. Leave it on for small datasets (it regularises), turn it off only once the set is ≥ 30 images,
  and do not advertise left/right control you cannot deliver.
- **Test angle control by measuring the generated face, not by looking at it.** Generate the same
  seed from prompts like "de trois-quarts gauche", then measure the yaw of the OUTPUT with the same
  InsightFace pass. Frontal-locked training shows |yaw| ≤ 2° on every angle prompt even though the
  images look passable; a vision model will happily claim the model "turns the head more" when the
  measured yaw is unchanged — trust the number.
- **Changing dataset composition beats adding steps by an order of magnitude.** Same seed, prompt and
  weight: enriching the dataset moved the output to correlation 0.59, while +700 steps on the old
  dataset moved it to 0.98 (nothing). If a LoRA plateaus, rebuild the dataset — do not extend the run.
- **Confirm the target ComfyUI has a matching base checkpoint before calling a LoRA deployed.**
  `models/loras/` holding the file is not usability: a LoRA trained on SD 1.5 is inert in an install
  whose `models/checkpoints/` only contains an unrelated architecture (e.g. LTX video). Check both,
  and flag the missing base model rather than reporting success.
- **If VRAM is identical across two resolutions, memory is not the bottleneck** — so a smaller
  model (SD 1.5) fixes OOM, not speed. Do not spend a download on the wrong axis, and say so when
  the obvious next move is the wrong one.
- Run 3 steps to price a step; only launch hundreds of steps once the per-step cost fits the time
  budget. The remaining axis when optimizer, precision and resolution are all ruled out is
  compute-side — see `references/training-speed-diagnostics.md`.

## Pitfalls

- **Sample `\GPU Adapter Memory(*)\Shared Usage` (Windows perf counter) during the pricing run — the
  WDDM spill, not the config, is the real speed killer on an 8 GB card.** Shared usage > 0 GB means
  GPU memory is being paged to system RAM: dedicated stays pegged (~7.9/8.2 GB) and steps run 25–140×
  slower than the kernels warrant. Measured here: SDXL DreamBooth-LoRA 1024 px = 207 s/step, 512 px =
  38 s/step, ~1.1 GB shared in both cases, while an isolated UNet LoRA fwd+bwd (rank 16, grad ckpt,
  batch 1) is ~1 s and a 4096³ fp16 matmul runs at 41 TFLOPS. The static footprint (SDXL UNet fp16
  ~5.2 GB + both text encoders ~1.6 GB + VAE fp32 ~0.34 GB) is what exceeds the budget, so lowering
  resolution speeds up compute but does not remove the spill.
- **`nvlddmkm` ID 153 (`Error occurred on GPUID: 100`) is a separate, intermittent problem.** Repeated
  entries mean a driver reset under load, and one was seen mid-run even with a validated 850 W PSU
  and reduced VRAM. Investigate driver/thermals; do not confuse it with the shared-memory spill, and
  do not blame the PSU until the spill has been ruled out.
- **Do not install xFormers on this machine (Windows + torch 2.4.x+cu118).** The last cu118 wheel
  (`0.0.27.post2`) pins torch 2.4.0, so the install silently downgrades torch 2.4.1→2.4.0, which
  breaks numpy 2.x (see the pin rule above) and forces a torchvision downgrade to 0.19.0. Without
  Triton (absent on Windows — `A matching Triton is not available`) xFormers then runs a slow
  fallback: measured 208 s/step vs ~50 s/step with SDPA at 1024 px, a 4× regression for ~0.2 GB
  VRAM saved (7.98→7.78 GB). SDPA is already the diffusers default — leave attention alone.
- **The diffusers example script treats every entry of `--instance_data_dir` as an image.** A `.txt`
  caption beside the images raises `UnidentifiedImageError`; a `captions/` subfolder raises
  `PermissionError`. The instance dir must contain images only, nothing else.
- **The example script's version guard rejects a PyPI install**: it raises
  "This example requires a source install from HuggingFace diffusers" through
  `check_min_version("<next>.dev0")`, because the released version is lower than a `.dev0`. No need
  to install from source — neutralize that single line and the script runs on the pinned release.
- **`--report_to=none` is not a valid value for accelerate 1.4** (`ValueError: Unsupported logging
  capability: none`). Install tensorboard and pass `tensorboard`.
- **Check a flag exists in the script's own argparse before using it.** `--use_adafactor` does not
  exist; the accepted form is `--optimizer=<name>`. A guessed flag fails after the model load and
  wastes a full cycle. In the current diffusers DreamBooth LoRA SDXL script the only valid names are
  `adamW` (pair with `--use_8bit_adam`) and `prodigy`: `--optimizer=adafactor` logs "Unsupported
  choice of optimizer" and silently falls back to AdamW, so an "adafactor" run measures AdamW.
- **A flag accepted by one version of accelerate is not accepted by another**: values that a tool
  documents as "none" or "off" may be rejected outright, and the error surfaces from the launcher,
  not from your script — read the traceback bottom-up to find whose parser refused it.
- **Do not present an untested hypothesis as a fix.** When optimizer, precision and resolution are
  all measured as irrelevant, report "the cause is compute-side, one variable at a time" — do not
  tell the user a specific option will solve it before it has been measured.

## Support files

- `references/training-speed-diagnostics.md` — slow-step decision table: symptom, what it rules out,
  the measurement to take next, plus the reference measurements above.
- `references/dependency-budget-and-pins.md` — caching and download-budget recipe, known-good pin
  sets, and why a dependency traceback usually names the wrong package.
- `scripts/sampler_vram.sh` — background VRAM sampler to pair with any launch.
