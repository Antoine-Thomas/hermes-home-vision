# Slow-step diagnostics — diffusion LoRA on a consumer GPU

Use when the training loop runs (loss moves, no OOM) but the step cost makes the run pointless.
Change ONE variable per trial and re-measure; archive each log before the next launch overwrites it.

## Measure first

```
seconds / step   from the progress-bar timestamps (step 1 -> step 2), not from the total
VRAM max         sort -n vram.log | tail -1     (written every 30 s by a background sampler)
loss             first and last value actually logged
gpu vs mem util  nvidia-smi --query-gpu=utilization.gpu,utilization.memory --format=csv,noheader
```

Take the `nvidia-smi` sample WHILE the run is active — an idle card tells you nothing.

## Decision table

| Symptom | Rules out | Next measurement |
|---|---|---|
| GPU util 100 %, memory util ~1 % | paging / swap / host-device thrashing | the work is compute-bound: look at the recompute path, the kernel/framework build, the torch wheel |
| GPU util low (10-40 %), memory util high | the GPU is starved | data loading, host-side preprocessing, or a dataloader with too few workers |
| VRAM unchanged between two resolutions | memory as the bottleneck | stop tuning memory; a smaller model or lower resolution will not speed the step up |
| VRAM unchanged across two optimizers | the optimizer's state as the memory cost | measure again after switching the precision |
| identical s/step across optimizer AND precision | both as the cause | the compute path itself (checkpointing/recompute, torch build, driver) |
| VRAM pinned at the card's ceiling with no OOM | nothing — the card is simply full | expect a crash as soon as anything spikes (checkpoint save, validation pass) |

## Reference measurement — SDXL LoRA, RTX 3070 Ti 8 GB, Windows

| Config | Optimizer | Precision | Res | s/step | VRAM |
|---|---|---|---|---|---|
| batch 1, grad-accum 4, grad checkpointing | 8-bit Adam | fp16 | 1024 | 50-107 | 7.97 Go |
| idem | adafactor | fp16 | 1024 | ~53 | 7.98 Go |
| idem, tf32 enabled | adafactor | bf16 | 1024 | ~50 | 7.97 Go |
| idem | adafactor | fp16 | 768 | ~113 | 7.98 Go |

What this table buys a future session: **the optimizer, the precision and the resolution are all
ruled out on this class of machine.** Do not re-run those three experiments — go straight to the
compute-side axis.

## Traps in the loop itself

- The progress bar reports `0/N` for a long time before the first step completes; read the timestamp
  twice, several steps apart, to get a real per-step cost rather than believing the first number.
- A trial with a high `--checkpointing_steps` produces no artifact at all — there is then nothing to
  test and nothing to show the user, which is a legitimate and reportable outcome ("no images").
- Killing the launcher does not always kill the child process: kill by matching the chain's venv
  path in the process command line, then confirm the card dropped back to idle.
- The VRAM sampler must be started before the run and stopped after it, or its last line will
  describe a different trial.
