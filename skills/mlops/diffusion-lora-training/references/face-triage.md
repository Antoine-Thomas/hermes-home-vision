# Face-first corpus triage — stills and video frames

Step 1 of the skill, in full detail. Every rule below applies to stills and to sampled video frames
alike. Content is carried over from the two merged skills (`lora-training`, `diffusion-lora-training`)
without dropping a rule; the merged skill now points here from its Step 1.

## Judge by FACE, not by image

- A 6000x4000 frame where the subject stands 5 m away yields a ~400x400 px face and is unusable; a phone
  shot with a 1000 px face is ideal (a 1958x1958 frame with a 1000x1000 px face is perfect). Filtering on
  image resolution selects the wrong photos.
- **Measure the detected face bounding box in pixels, not the image resolution.** Use a face detector
  (InsightFace, well provided by the LatentSync venv) to get the box.
- Reject: no face, more than one face, small side < 512 px, long side < 700 px.

## Sharpness — inside the box, and renormalised before comparing anything

- Sharpness = variance of the Laplacian measured **inside the face box**, never on the whole image.
- **Resize that box to a fixed square (e.g. 256x256, INTER_AREA) BEFORE comparing anything.** The
  variance scales with resolution: at equal optical sharpness a 1000 px face measures ~8x lower than a
  350 px face, so raw values silently favour the lowest-resolution source. Raw face-box numbers once
  made a 720p clip look 13x sharper than two UHD clips; normalised, the real gap was 1.25x. When
  reporting, state the figure is normalised.
- Laplacian variance is a focus/texture proxy, not an absolute quality score. It does not see
  compression noise (a 3.7 Mb/s source loses to a 97 Mb/s one at equal resolution) or bit depth
  (10-bit `yuv420p10le` beats 8-bit for crop latitude). Say so when it is the only number you have.
- **Never filter a corpus on a MEDIAN sharpness threshold.** Cutting at the median guarantees that half
  the photos are dropped by construction, however good they are: a set where the last keep is 57.1 and
  the first drop is 55.9 loses photos on a 2 % difference. Use an absolute Laplacian floor (~40 for
  multi-megapixel portraits) and report the distribution.
- Calibrating the sharpness threshold on the corpus median mechanically removes about half the corpus.
  That is acceptable as a first pass, but say it out loud: Laplacian variance is not comparable between
  a 24 Mpx close-up and a phone photo, so the cut is partly arbitrary. Offer to lower it rather than
  silently discarding photos that are probably fine.

## Exposure

- Reject if any region of the face sits at 0 or 255 over more than ~2 % of its area.

## Angles — measure them, do not classify them

- **Enforce an angle/expression mix or you will not get one.** Count the angles after triage; check the
  angle mix before training, not after. A corpus that is ~77 % frontal trains a model that only renders
  frontal faces: state the distribution and its consequence instead of declaring the dataset "fine".
- **Measure angles, do not classify them.** InsightFace buffalo_l returns a real `(pitch, yaw, roll)` in
  degrees per face — a number you can report and threshold. Reserve vision classification for expression
  and framing, where no geometric measure exists. Quote the |yaw| spread when claiming angle variety:
  material that all sits within a few degrees of frontal has none, whatever the resolution or the frame
  count.
- **Audit the corpus angles BEFORE enriching, with a measurement.** Run every source photo through
  InsightFace (`FaceAnalysis('buffalo_l')`, `.get(img)` → `face.pose` = [pitch, yaw, roll] in degrees)
  and tabulate yaw. A corpus that looks like "40 selfies" can contain literally zero profiles (max
  |yaw| 43°): no re-cropping, upsampling or step count invents the missing volume information, and the
  promised "add ~6 profiles" target may be unreachable — say so instead of spending an hour of GPU on it.
  This also classifies angles objectively, replacing a vision model's guesswork.
- Target angle mix for identity: ~35 % face, ~30 % three-quarter, ~20 % profile, ~15 % high/low angle.
  A corpus that is 75 % frontal trains a frontal-only identity; say so and let the user decide rather
  than reporting success.

## How many images, and which ones

- Aim for 25-35 images; keep 2-3 per burst, never 10 from the same series.
- Classify the kept photos with a vision model in parallel batches (one subagent per <= 8 images,
  returning compact JSON): angle, expression, background, framing, and one `doute` boolean.
- Vision classification of angle/expression can contradict itself between passes. Keep the modal value,
  flag the photo, and list the doubtful ones for the user to arbitrate — do not hide the uncertainty,
  and do not treat a doubtful label as fact when building the captions.
- **A frontal-only face dataset caps identity, and no number of steps fixes it.** Count angles before
  training: 26 crops that are 22 frontal (12 identical neutral front shots) with a single three-quarter
  and no profile produce a LoRA that learns "middle-aged man, grey hair, grey beard" but not the actual
  features — and it stays that way at 1800 and at 2500 steps. Aim for ≥ 6 three-quarter and ≥ 4 profile
  crops from the start; re-use the photos a quality filter rejected (angle variety often ranks below
  sharpness in a sharpness-sorted filter).

## Crop and rebalance

- Crop a square centred on the face with ~1.5x the face size as margin, resize to the training
  resolution (1024 for SDXL), and keep the source photos read-only.
- **Match the sharpness distribution across angle groups when rebalancing.** Newly harvested
  three-quarter crops are often the softest images in the set: pairing each of them with a frontal of
  similar Laplacian variance stops the model from learning "three-quarter = blurry", which is a
  confound that survives any amount of extra steps. Greedy nearest-value matching is enough.

## Captions

Folded here rather than kept as its own reference: the merged content is under 20 useful lines.

- Default form: `<trigger>, photo of <name>, <angle>, <expression>, <background>`.
- One caption per image: a unique trigger token plus the attributes read off the image (angle,
  expression, light/background).
- **Pick one short unique trigger word and reuse it verbatim.**
- **Keep the caption files in a folder OUTSIDE the image folder** when the trainer is the diffusers
  DreamBooth example — that script opens every entry of the instance directory as an image. The kohya
  layout wants the `.txt` beside its image instead. See `references/kohya-sd-scripts.md` (failure
  table) and `references/pitfalls.md`.

## Video sources

- **Video sources**: sample frames evenly, measure the face box and pose on those frames, then apply
  every rule above unchanged. Specs to read, the ffmpeg extraction pattern, the pose call and the
  preview-delivery recipe are in `references/video-source-audit.md`.
