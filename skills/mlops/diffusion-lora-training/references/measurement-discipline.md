# Measurement and spend discipline

Step 5 of the skill, in full detail, plus the measurement rules carried over verbatim from
`lora-training`. This is the file that decides whether a long run is worth starting and whether a
produced LoRA is worth publishing.

## What to measure per trial

Measure, per trial: seconds per step, VRAM max (sampler file), loss first/last, steps reached, and any
error verbatim.

- **The published s/step figure is the end-of-run aggregate: total elapsed ÷ completed steps.** Read the
  final summary line of the run. The progress bar is only a liveness check — a live bar read early and
  divided by hand gave "53 s/step" for a run whose final line said `3/3 [24:17, 485.88s/it]`, a 9x error
  already reported before it was caught. Say which of the two you did.
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
- **If VRAM is identical across two resolutions, memory is not the bottleneck** — so a smaller
  model (SD 1.5) fixes OOM, not speed. Do not spend a download on the wrong axis, and say so when
  the obvious next move is the wrong one.
- Run 3 steps to price a step; only launch hundreds of steps once the per-step cost fits the time
  budget. The remaining axis when optimizer, precision and resolution are all ruled out is
  compute-side — see `references/training-speed-diagnostics.md`.

## The s/step figures disagree — do not publish a duration until re-measured

Three measurements of the same nominal configuration (RTX 3070 Ti 8 GB, SDXL LoRA, batch 1,
grad-accum 4, gradient checkpointing, fp16, 1024 px) are carried in this library and they do not agree:

| Source | s/step @1024 px | s/step @768 px | Resolution effect claimed |
|---|---|---|---|
| `lora-training` SKILL.md (now here) | ~486 | not measured | "identical", < 2 % |
| this skill's Step 5 + Pitfalls | 207 (and 38 at 512 px) | not measured | — (512 px = 38) |
| `references/training-speed-diagnostics.md` | 50-107 (8-bit Adam) / ~53 (adafactor) | ~113 | **x2, in the opposite direction** |

The 2.3x gap between 486 and 207, and the reversal of the resolution effect, cannot describe the same
run. **Neither figure is corrected here and none of them may be quoted as settled**: re-measure with
the 3-step benchmark on the exact configuration before publishing any completion time. What survives
all three texts is the operational rule — *benchmark 3 steps before any long run*.

## Order that is not negotiable (carried over verbatim from `lora-training`)

1. **Triage the dataset before touching a trainer.** A LoRA is only as good as the mix it sees.
2. **Benchmark 3 steps before any long run.** Never launch 500+ steps without a measured
   seconds-per-step from the exact same configuration. Three steps cost minutes and either
   green-light the real run or save hours.
3. **Report the end-of-run aggregate, never a mid-run sample.** See the measurement pitfall below.
4. **Never buy the corpus before the pipeline runs.** Do not run a photo session for more
   training material while the trainer itself is unproven — more photos do not fix a broken stack.

## Measurement discipline (carried over verbatim from `lora-training` — this cost two wrong reports)

- **Read the end-of-run aggregate, not a mid-run progress bar.** A live bar read early and
  divided by hand gave "53 s/step" for a run whose final line said `3/3 [24:17, 485.88s/it]` —
  a 9x error already reported before it was caught. Read the final summary line, or divide total
  elapsed by completed steps, and say which one you did.
- **Do not declare a long installation failed while it is still running.** A distro install
  queried too early answers `WSL_E_DISTRO_NOT_FOUND`, indistinguishable from a real failure; the
  retry then races the first attempt and wastes work. Confirm completion before changing strategy.
- Report measurements as delivered, including correcting your own earlier figure. Say which
  number is verified and which is an estimate; never fill a gap with a plausible value.
- **Drive measurements from a re-runnable script file, not inline code.** Write the `.py` with
  the file tool and run it with the target venv's python: quoting/heredoc errors bite on Windows,
  and a file survives to be re-read and corrected. Give it a flag that re-measures
  already-produced intermediates (extracted frames, saved crops) so iterating on a metric never
  repeats the expensive upstream step.

## Deciding whether the produced LoRA is any good

- **300 steps is not enough to judge a face LoRA.** At 300 steps the LoRA visibly shifts the output
  (older, grey-haired man vs the base model) but weight 0.8 gives the wrong expression and weight 1.0
  deforms the face. Budget 1500–2000 steps (~1 h at 1.8 s/step) before evaluating identity.
- **1'800-step SD 1.5 baseline on 8 GB (validated end to end):** 512 px, rank 16 / alpha 8, grad ckpt,
  8-bit Adam → **53 min, 1.77 s/step, 3.5 GB VRAM, 0.20 GB shared memory (flat, no spill), 62 °C,
  184 W, zero nvlddmkm / Kernel-Power events**. Treat ~1.8 s/step and ~3.5 GB as the reference for
  any face-LoRA ETA on this class of card.
- **Evaluate LoRA strength at 0.6 first, not 1.0.** At 1800 steps, scale 0.6 gives a clean, neutral
  portrait matching the references, 0.8 is acceptable but drifts, and 1.0 deforms the face. Testing at
  `cross_attention_kwargs={"scale": w}` is more reliable than fuse/unfuse cycles and keeps one loaded
  pipeline for all weights. A 3-point sweep (0.6/0.8/1.0) on the same seed is enough to pick a weight.
- **Detect a plateau before spending more GPU time.** Regenerate at the SAME seed, prompt and weight
  after extra steps and compare the two PNGs numerically (mean abs diff + correlation on the RGB
  array, numpy only). Correlation > 0.98 (≈2 % mean diff) means the extra steps changed essentially
  nothing: the LoRA has plateaued and more steps will NOT improve resemblance — the dataset is the
  bottleneck. Measure this instead of guessing, and report it.
- **Changing dataset composition beats adding steps by an order of magnitude.** Same seed, prompt and
  weight: enriching the dataset moved the output to correlation 0.59, while +700 steps on the old
  dataset moved it to 0.98 (nothing). If a LoRA plateaus, rebuild the dataset — do not extend the run.
- **Test angle control by measuring the generated face, not by looking at it.** Generate the same
  seed from prompts like "de trois-quarts gauche", then measure the yaw of the OUTPUT with the same
  InsightFace pass. Frontal-locked training shows |yaw| ≤ 2° on every angle prompt even though the
  images look passable; a vision model will happily claim the model "turns the head more" when the
  measured yaw is unchanged — trust the number.
- **Do not trust a gateway vision model for a likeness verdict.** Asked to compare references against
  generated faces, it returned "same person" and "different person" in one answer and flipped hair
  colour between calls on the same image. Build a side-by-side contact sheet instead (PIL: references
  on the top row, generations below, one label per cell) and hand THAT to the user — their eye is the
  only reliable judge. Use the vision model only for crude checks ("is there a face at all").
- **Face-embedding scores need models that may not be local.** InsightFace `buffalo_l` is a download;
  check `~/.insightface/models` and the training venv (`pip list | grep insightface`) before promising
  a cosine-similarity verdict — an unrelated Python install having the package is not enough, and
  installing it is a download that needs the user's approval.
- **Confirm the target ComfyUI has a matching base checkpoint before calling a LoRA deployed.**
  `models/loras/` holding the file is not usability: a LoRA trained on SD 1.5 is inert in an install
  whose `models/checkpoints/` only contains an unrelated architecture (e.g. LTX video). Check both,
  and flag the missing base model rather than reporting success.
