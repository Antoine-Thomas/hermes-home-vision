# Driving ComfyUI from a script: batches of prompts, timing, resume

Recipe and traps for processing N items (frames, images) through a ComfyUI graph by API, with
per-item timing and resume. Validated on SDXL img2img at 1280x720 on 8 GB, but nothing here is
model-specific.

## The loop per item

1. Copy the input where ComfyUI can read it: `LoadImage` resolves ONLY inside
   `<ComfyUI>/input/`. Reuse ONE temporary filename and `os.remove()` it before each copy, so its
   mtime/hash changes for every item.
2. `POST /prompt` with `{"prompt": <graph>, "client_id": "..."}` -> `prompt_id`.
3. Poll `GET /history/<prompt_id>` until the id appears. Read `status.status_str`
   (`success` / `error`) and the `messages` array: `execution_start` and `execution_success`
   carry millisecond timestamps, so **per-item duration = their difference**. That is the exact
   execution time; the wall clock around the HTTP call adds the poll interval (up to ~4 s).
4. Resolve the produced file from the `outputs` entries: each image entry carries BOTH
   `filename` and `subfolder`. Rebuild `output/<subfolder>/<filename>`.
5. Hash the produced file (md5) and journal it. Two identical consecutive hashes mean the input
   did not actually change.

## Traps that bite, in the order they cost time

- **`subfolder` is part of the path.** `SaveImage.filename_prefix = "foo"` (no slash) writes to the
  OUTPUT ROOT as `foo_00001_.png`, while `"foo/bar"` writes `output/foo/bar_00001_.png` with
  `subfolder = "foo"`. Building the path from the filename alone raises `FileNotFoundError` right
  AFTER a successful generation — the worst place to look for a bug. Prefer a prefix that embeds the
  item name (`"restyle/<stem>"`): the files are unambiguous and traceable per item.
- **ComfyUI caches node outputs, including across crashed runs.** Re-submitting a graph whose inputs
  are byte-identical (same input image, same seed) returns in ~0.1 s with the cached artifact. A
  per-item duration of ~0.1 s is a CACHE HIT, not a measurement: it invalidates any cold/warm
  timing in that batch. It happened because a failed attempt had already executed the same graph for
  that item. Verify the ARTIFACT, not the clock: mean absolute pixel difference against the source
  and against the neighbouring items (measured 7.71 / 7.73 / 7.78 out of 255 for three consecutive
  items — consistent, so the image really was processed).
- **An identical graph is not automatically re-run.** To force work, change something for real (the
  input bytes, the seed) rather than re-submitting and hoping.
- **`ImageScale` before `VAEEncode` is what fixes the sampling resolution.** Without it the sampler
  runs at the source image's own latent size, whatever width/height you passed as arguments — the
  graph silently ignores your request. Insert `ImageScale(upscale_method="lanczos", width=W,
  height=H, crop="disabled")` and state the real working resolution in the report.
- **Resume from the destination directory.** Skip any item whose destination file already exists
  with a non-zero size. This makes an interrupted batch (or a mid-batch abort) cheap to restart and
  it is the only reason a killed run costs nothing.
- **Abort on the first non-`success` item and print the raw `messages`.** Continuing past a failed
  item silently produces a batch with holes; a partial pipeline must be visible.
- **Redirect the batch output to a log file, then read the log.** Piping a long python run through
  `tail`/`head` masks its exit code: the tool reports the pipeline's status (`tail` = 0) and a crash
  looks like a success. Keep the command's own redirect as the last statement.
- **Journal every item** (`jsonl`: item, index, execution_s, wall_s, output path, md5). It is what
  lets a later session prove throughput, find the cache artefacts and resume without guessing.
- **Projection arithmetic**: first item (model load) + (n-1) x steady-state. Averaging the probe
  items instead inflated a 290-item job from 54 to 67 min on a 3-item probe.

## The img2img graph that was used

`CheckpointLoaderSimple -> LoadImage -> ImageScale -> VAEEncode -> 2 x CLIPTextEncode ->
KSampler(sampler_name="dpmpp_2m", scheduler="karras", denoise=<0.25-0.35>, seed fixed) ->
VAEDecode -> SaveImage`.

Cost measured on RTX 3070 Ti, SDXL base, 1280x720: 19.3 s for the first item, 10.9-11.2 s steady,
VRAM 5.0-5.9 GB steady / 7.1 GB peak. With `steps=25` and `denoise=0.30` only `int(25*0.30)=7`
steps are actually sampled — quote both numbers or the budget is off by 3.5x.

Freeing VRAM before a batch: `POST /free {"unload_models": true, "free_memory": true}` then confirm
with `nvidia-smi`. It does not invalidate the correctness of the batch, but it makes the first item
the real cold measurement.
