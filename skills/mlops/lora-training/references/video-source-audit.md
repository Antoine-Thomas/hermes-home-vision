# Video as a face-dataset source — audit procedure

Applies when the corpus is video: a clip the user shot, a talking-head render, a download.
Every triage rule in SKILL.md still applies — only the measurement front-end changes, because
the material must be sampled into frames first. Treat the whole audit as **read-only**: extract
to a scratch directory, never write into the source or into the existing dataset.

## Step 0 — write a script, do not drive code inline

Author the audit as a `.py` with the file tool and run it with the interpreter that carries the
detector. Quoting and heredoc errors bite on Windows when multi-line Python goes through an
inline code path, and a file is re-runnable. Give the script a `--recalcul` flag that re-measures
frames already on disk, so tuning a metric never re-runs ffmpeg.

Interpreter carrying InsightFace + OpenCV on this machine (shared — never install into it):
`data\video_youtube\LatentSync\venv\Scripts\python.exe`.

## Step 1 — technical specs before any measurement

```bash
ffprobe -v error \
  -show_entries format=duration,bit_rate,size,format_name \
  -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,pix_fmt \
  -of json "<video>"
```

Read four things:

- **`r_frame_rate` vs `avg_frame_rate`** — a mismatch means variable frame rate. Normalise with
  `-vsync cfr` before extracting a dataset; otherwise frame numbering drifts against wall-clock
  time and "frame N" means something different in the dataset than in the clip.
- **`pix_fmt`** — `yuv420p10le` is 10-bit and carries more tonal latitude for crops and grading
  than `yuv420p`. Prefer the 10-bit source when both exist.
- **bitrate** — a low-bitrate clip carries compression texture that penalises small-detail
  learning next to a high-bitrate one at the same resolution.
- **resolution is not face size** — see step 5.

## Step 2 — sample frames at even intervals

Ten spread frames per clip characterise it. Seek *before* the input so ffmpeg does not decode
from the start each time:

```bash
ffmpeg -hide_banner -loglevel error -y \
  -ss <t> -i "<video>" -frames:v 1 -q:v 2 "<out>/frame_<i>.jpg"
```

with `t = duration * (i + 0.5) / N`. The half-step offset keeps the first and last sample off the
very ends of the clip, where a fade or a black frame is most likely. Assert the file exists and is
non-empty after each call — a silently missing frame skews every aggregate that follows.

## Step 3 — face detection and pose

```python
import os
import onnxruntime as ort
from insightface.app import FaceAnalysis

providers = ort.get_available_providers()
ctx_id = 0 if "CUDAExecutionProvider" in providers else -1   # deliberate CPU fallback
app = FaceAnalysis(name="buffalo_l", root=os.path.expanduser("~/.insightface"))
app.prepare(ctx_id=ctx_id, det_size=(640, 640))

faces = app.get(image_bgr)
face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))
face.pose        # (pitch, yaw, roll) in DEGREES — that order, from the 1k3d68 landmarks
face.bbox        # x1, y1, x2, y2
face.det_score
```

- **Do not point `root=` at an arbitrary project folder.** The buffalo_l pack lives in
  `~/.insightface/models/buffalo_l`, which the default root resolves. A script that passed a
  project path found no pack. Confirm the three files that matter are present: `det_10g.onnx`,
  `2d106det.onnx`, `1k3d68.onnx` — the last one supplies the 3D landmarks.
- `face.pose` is `None` when the 3D landmark model is absent: report "pose unavailable" rather
  than writing a zero, which reads downstream as "perfectly frontal".
- Record `det_score`, the box in pixels, and the box area as a fraction of the frame. That
  fraction is the real framing metric — a large face in a small frame beats the reverse.

## Step 4 — renormalise sharpness before comparing sources

**This step inverts conclusions if skipped.** Variance of the Laplacian scales with resolution:
at equal optical sharpness a 1000 px face measures ~8x lower than a 350 px one. Always measure it
on the face box resized to a fixed square:

```python
crop = img[y1:y2, x1:x2]
crop = cv2.resize(crop, (256, 256), interpolation=cv2.INTER_AREA)   # INTER_AREA when downscaling
lap = cv2.Laplacian(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
```

Raw face-box values once showed a 720p clip 13x "sharper" than two UHD clips; normalised to
256x256 the true gap was 1.25x. When reporting, state the figure is normalised.

## Step 5 — the usability call

A 512x512 training crop centred on the face needs **>~512 px of real face**, otherwise the crop
is pure interpolation:

| face box width | verdict |
|---|---|
| >= 512 px | usable as a training source |
| 350-512 px | marginal — upscale territory; use only if nothing better exists |
| < 350 px | control reference only, never a training source in the 512-1024 px regime |

State the face box width in pixels, not the frame resolution: a UHD frame with a small face is a
worse source than a 720p frame with a large one. Also report per-clip dispersion (std of yaw, std
of normalised sharpness) — it tells the user whether a clip is a steady capture or a moving one
far better than a mean alone.

## Step 6 — deliver previews

Four frames per clip, scaled to ~1280 px wide, sent as one Telegram media group per clip with a
metrics caption on the first item. Keep the full-size frames on disk as evidence.

- Read the bot token from `.env` at run time. **Never pass it as a command argument** — it lands
  in the process list — and never print it. Redact it out of any API error before printing, and
  print only the `getMe` username, not the token.
- `sendMediaGroup` with `attach://f0`-style multipart and the caption on the first item:
  `data={"chat_id": ..., "media": json.dumps([...])}`, `files={"f0": open(path, "rb"), ...}`.
  Close the file handles in a `finally`.
- Confirm delivery from the returned `message_id` list and report *sent vs expected* ("12/12").
  A 200 response does not by itself prove every photo landed.

## Writing the result up

If the target run log is kept **newest-first** (a status header followed by dated update blocks),
insert the new block directly beneath that header — appending to the end files it as the oldest
entry. Read the existing headings first and match their depth and style.

Close the report by verifying the constraints you were given rather than asserting them: absent
packages, unchanged source mtimes, untouched LoRA/dataset files. A README claiming "read-only"
is worth less than a timestamp comparison.
