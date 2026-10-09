# Pitfalls — measured traps on this machine

The Pitfalls section of the skill, in full detail, plus the kohya failure-table rows that no other
reference carries. Every entry here was hit in practice, not predicted.

## GPU and driver

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

## The diffusers example script

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

## kohya failure-table rows carried over from `lora-training`

Rows that the other references do not already carry. The full kohya table, including the four rows
reproduced above in diffusers form, is in `references/kohya-sd-scripts.md`.

| Symptom | Cause | Fix |
|---|---|---|
| `trying to load the model files of the variant=fp16, but no such modeling files are available` | pointing at a diffusers-format folder that holds only default weights | pass the single-file `.safetensors` checkpoint (native kohya format), or write the fp16 variant |
| `./sd-scripts is not a valid editable requirement` | kohya's requirements reference an uncloned sibling repo | clone `kohya-ss/sd-scripts` and install *its* requirements |
| 50-500 s/step, GPU at 100 % with the memory controller at ~1 % | compute-side pathology on the Windows stack, not a memory ceiling | move training to WSL2 (`references/kohya-sd-scripts.md`) |
