# Model prep and where to train — Windows vs WSL2, trainer, pins, model format

Step 3 of the skill, in full detail, plus the host decision and the hard rules that were carried over
from `lora-training`. Two trainers are viable and the rules below are **conditional on which one you
use**, not a choice of camp.

## Where to train — both statements are true, by condition

- **SD 1.5 at 512 px on Windows is the validated path on an 8 GB card.** Measured end to end here:
  1 800 steps in 53 min, 1.77 s/step, 3.5 GB VRAM, 0.20 GB shared memory (flat, no spill), 62 °C,
  184 W, zero nvlddmkm / Kernel-Power events. Use this when the card is 8 GB.
- **SDXL at 1024 px is the case for WSL2.** Measured on Windows: ~486 s/step at 1024 px, with
  **identical VRAM (~7970 MB) at 1024 px and at 768 px**. Changing the optimizer (8-bit Adam vs
  adafactor), the precision (fp16 vs bf16 + tf32) and the resolution moved the step time by under 2 %.
  The GPU sat at 100 % utilisation with the memory controller at ~1 % — a compute-side pathology, not a
  memory ceiling. Do not spend an evening tuning flags on Windows to fix it: move to WSL2.
- **WSL2, when you take that path.** GPU passthrough works out of the box (the Windows driver serves
  CUDA inside WSL) and `torch.cuda.is_available()` returns True without any driver work. The full stack
  (distro import, venv, torch cu121, sd-scripts clone), the kohya dataset layout, the 3-step benchmark
  command and the trainer failure table are in `references/kohya-sd-scripts.md`.
- **Honest caveat, kept from the original skill:** everything below the trainer is verified; the WSL
  training **speed** still has to be measured with the 3-step benchmark before promising a user a
  completion time.
- The three divergent s/step figures for the same SDXL 1024 px configuration (486 / 207 / 50-107) are
  collected in `references/measurement-discipline.md` with their sources and a "re-measure before
  publishing a duration" note. Do not quote one of them as settled.

## Which trainer — two repositories, and this is the usual trap

- `bmaltais/kohya_ss` is the **GUI + launcher and no longer ships the command-line training scripts**:
  a clone gives the GUI only. Do not build a chain on it.
- `kohya-ss/sd-scripts` is where the CLI lives (`sdxl_train_network.py`). Clone it and install *its*
  requirements; kohya_ss's requirements reference that sibling repo and fail with
  `./sd-scripts is not a valid editable requirement` otherwise.
- The alternative is the official diffusers example
  (`examples/dreambooth/train_dreambooth_lora_sdxl.py`), which runs on the released PyPI diffusers.

## Model format — conditional on the trainer

- **kohya / sd-scripts: use a single-file `.safetensors`.** It avoids the whole class of
  "diffusers-format folder is incomplete" failures — pointing kohya at a diffusers folder that holds
  only default weights raises
  `trying to load the model files of the variant=fp16, but no such modeling files are available`.
  Prefer the single-file checkpoint when both are available.
- **diffusers example: a folder in diffusers format is required** (not a single-file checkpoint).
  Convert locally, with no extra download:
  `StableDiffusionXLPipeline.from_single_file(src, torch_dtype=torch.float16).save_pretrained(dst)`.

## Pin the library quartet before anything else

- Pin the library set in one command, before installing anything else, and never let a major version
  float: a fresh venv resolves the newest of everything, which is how a working chain breaks.
- `transformers<5`, with the pair proven on this machine: `transformers==4.57.6` + `diffusers==0.36.0`
  (+ `peft>=0.17`, `accelerate>=1.4`). transformers 5.x breaks the diffusers and peft imports with
  messages that name peft and hide the real cause. Full rule and the traceback diagnosis:
  `references/dependency-budget-and-pins.md` and `mlops/llm-ops`.
- numpy 2.x (`numpy>=2,<3`, tested 2.4.6) is fine on torch 2.4.1+cu118 here: `torch.from_numpy` and the
  EulerDiscreteScheduler path both work. Fall back to `numpy==1.26.4` only if a specific scheduler
  actually raises `Numpy is not available`.

## Hard rules carried over from `lora-training`

- **Pin `transformers` below 5** for anything touching diffusers, peft, LTX or SDXL. transformers 5.x
  breaks diffusers and peft imports with messages that name peft, not transformers. Proven pair on this
  machine: `transformers==4.57.6` + `diffusers==0.36.0` (+ `peft>=0.17`, `accelerate>=1.4`).
- **Keep the new toolchain in its own venv** and never install into an existing AI venv (XTTS,
  LatentSync, LTX-2.3 and the ComfyUI embedded python stay untouched).
- **Count the download budget before starting.** A CUDA toolkit from NVIDIA's repo is not needed when
  you use `cu12x` torch wheels (they bundle the CUDA runtime, and WSL supplies `libcuda.so`) — skipping
  it saves ~3 GB. Prefer a torch wheel already in the pip cache: check with a `--dry-run` install before
  downloading anything large.
- A trainer that accepts a **single-file `.safetensors`** checkpoint avoids the whole class of
  "diffusers-format folder is incomplete" failures. Prefer it when both are available — that holds for
  kohya/sd-scripts (see "Model format" above for the diffusers exception).
