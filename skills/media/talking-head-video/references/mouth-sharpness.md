# Mouth sharpness: measuring it, and putting real detail back

Load this when the mouth of a lip-sync output is judged blurry, or before choosing
an engine / a restoration step. The rules live in SKILL.md; this file carries the
recipes and the decision tables.

## The reference measurement

Laplacian variance on the mouth/chin band, **same framing** between output and
source. Always report the result as a **ratio output/source** — the absolute value
depends entirely on how large the face is displayed, so it means nothing alone.

```python
def lap(img):                                  # img: BGR uint8
    g = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(g, cv2.CV_32F).var())   # uint8 + CV_32F, never CV_64F
```

Profile the face in horizontal bands first — it tells you *where* the detail was
lost, and therefore what to fix. MuseTalk 1.5, ratio output/source:

| Band | Ratio |
|---|---|
| forehead | x0.80 |
| brows | x0.77 |
| eyes | x0.70 |
| nose | x0.81 |
| cheeks | x0.40 |
| upper lip | x0.16 |
| lower lip | x0.16 |
| chin | x0.04 |

The loss is concentrated under the nose — that is the generator's 256×256 working
resolution, not a global softness. Do not conclude "the whole face is blurry"
without this profile.

## Decision table: which engine

Lower-face (mouth/chin) preservation, same framing:

| Engine | Preservation | Use when |
|---|---|---|
| LatentSync 1.5 | **58 %** | mouth sharpness is the priority |
| MuseTalk 1.5 | 16 % | speed matters more |

Caveat that ruins the comparison if ignored: on 8 GB, LatentSync peaks at ~7.9 GB VRAM
and its throughput degrades during the run (3.8 → 8.2 s/it over 25 min), so its tqdm
ETA is optimistic; MuseTalk takes ~55 min end-to-end and peaks at ~7.7 GB. Neither
exposes a batch-size flag, so a bad run cannot be tuned — it has to be chosen right
the first time.

## Decision table: restoration (mouth sharpness, % of source, 7620 frames)

| Treatment | Result | GPU cost |
|---|---|---|
| none | 4 % | — |
| GFPGAN v1.4 w=0.6 | 7 % | ~30 min |
| GFPGAN + Real-ESRGAN (the portrait recipe) | 9 % | ~2 h |
| Real-ESRGAN x4 | 13 % | ~2 h 07 |
| Real-ESRGAN x4 + unsharp 0.6 | 37 % | ~2 h 07 |
| high-frequency transfer, lips unmasked | 90 % **but double lip contour** | ~4 min |
| **high-frequency transfer, lips masked keep=0.35** | **71 %** | **~4 min** |

Generative restoration plateaus at 37 %: it restores the *shape* of the mouth and
produces a smooth render poor in high frequencies. Try, in this order:
1. shrink the on-screen face square (free, biggest lever);
2. high-frequency transfer (authentic detail, ~30× cheaper than Real-ESRGAN);
3. generative restoration — last resort.

## The face-square lever (measure it before anything else)

Mouth sharpness inside the final 1920x1080 frame, same source framing:

| Face square | Upscale from a 720p source | On-screen sharpness |
|---|---|---|
| 1080 | 1.80x | 36 |
| 864 | 1.44x | 80 |
| 720 | 1.20x | 150 |
| 600 | 1.00x (native) | 288 |

The ratio against the source barely moves (62 % → 69 %) — what changes is the
**absolute** on-screen sharpness, ×8 between 1080 and 600. A 1080 square on a 720p
source forces a ×1.8 magnification that amplifies all the softness. Pick the
smallest square that still keeps the face present: this is a trade against face
prominence, so state it to the user rather than deciding silently.

## Recipe: high-frequency transfer from the source

Both engines paste the generated mouth back into the looped source frame, so
output and source are pixel-aligned. The source still holds the real texture
where the generator erased it — add it instead of hallucinating it:

```
hp   = src_crop - gaussian(src_crop, sigma=1.2)
mask = w_face * (keep + (1 - keep) * w_outside_lips)
out  = clip(mt_crop + lambda * hp * mask, 0, 255)     # lambda = 1.0, keep = 0.35
```

Geometry derived from the face bbox (works on an unseen face, no hand-tuned
ellipse):

- `w_face` — soft ellipse centred on the bbox, half-axes `1.25 × half-width` and
  `1.15 × half-height`, raised to the power 0.6 to feather the mask edge.
- `w_outside_lips` — 0 inside the lip ellipse, 1 outside. Place it at
  `0.72 × bbox_height` below the top of the bbox, with half-axes
  `0.21 × width` and `0.11 × height`.
- `keep` dampens the transfer inside the lips. 0.00 → 61 %, 0.35 → 67 %,
  0.60 → 72 %; ghost risk rises with `keep`. 0.35 is the validated compromise.

Precompute the source's high frequencies once (a 5-6 s source loops) and index
them with the engine's ping-pong mapping. Throughput: ~30 img/s in plain numpy,
~4 min for 7620 frames.

### Two ways this recipe goes wrong

- **Unmasked lips.** The generated mouth does not coincide with the source's, so
the original lip edges superimpose on the new ones: a double contour / ghost,
worst when the mouth goes from closed to open. Hence the `keep` mask.
- **A difference-based mask.** Thresholding `|src - mt|` to find "where they agree"
  collapses the transfer back to 4-16 %: the generator rebuilds the whole jaw, so
the two frames differ almost everywhere in the lower face.

## Script pitfalls already paid for

- `cv2.Laplacian` + `CV_64F` on a float32 image raises
  `Unsupported combination of source format (=5), and destination format (=6)`.
- Three coordinate spaces coexist (source frame, face crop, canvas). Measure in the
  crop's own frame; add the overlay offset only for the canvas.
- `GFPGANer.enhance()` → 3 values, `RealESRGANer.enhance()` → 2 values.
- GFPGAN outputs at 2x — resize back to the original size **before** applying crop
  coordinates, or the crop lands off-target. Mechanism: with `upscale=2` and
  `bg_upsampler=None`, `facexlib`'s `paste_faces_to_input_image` rebuilds the background via
  `cv2.resize(input_img, (w*2, h*2))` (measured: 3216x1808 in -> 6432x3616 out). Consequence:
  on a 1920x1080 frame the pass returns **3840x2160**, so it already performs the "upscale 2x"
  half of a 4K round-trip — do not stack Real-ESRGAN on top just for that, and never validate
  with `out.shape == frame.shape`: that test always fails and reads as "no face was pasted"
  when in fact every face was restored.
- Loading `RealESRGAN_x4plus.pth` into an `RRDBNet(scale=2)` raises
  `size mismatch for conv_first.weight` — the two scales are not interchangeable.
  `RealESRGAN_x2plus.pth` **is** present in `sadtalker/repo/gfpgan/weights/`, next to the GFPGAN
  set: `ls` that directory before declaring a needed weight missing, then instantiate the file
  matching the scale you asked for. The `realesrgan` python package is NOT bundled with
  gfpgan/basicsr — install it before importing `RealESRGANer`.
- The Laplacian alone can lie: ghost contours inflate it. Confirm visually on a
  frame with the mouth **open**, not closed.

## Mandatory prerequisite: measure whether the generated mouth even ALIGNS with the source

The whole recipe rests on one unstated assumption: that the high frequencies you take
from the source belong where you are putting them. That holds for the *rest* of the lower
face (same skin, same folds, just softened) and it does **not** hold for the lips, which the
generator rebuilt for a different audio track. **Measure it before grafting anything**:

```python
hp_s = src_gray - cv2.GaussianBlur(src_gray, (0,0), 1.2)
hp_m = mus_gray - cv2.GaussianBlur(mus_gray, (0,0), 1.2)
# mouth box from insightface landmark_2d_106[52:72]; search the shift map, not just (0,0)
```

Measured on native-1080p footage (MuseTalk 1.5, source 532x737 px face):

| Shift | corr(hp_muse, hp_src) in the mouth |
|---|---|
| (0,0) | **-0.02 .. +0.08** |
| best of the whole +/-3 px map | +0.02 .. +0.09 |

A flat map with no lobe means **the generated mouth is a different mouth**: there is no
offset at which its detail coincides with the source's. Grafting into the lips then stacks
two unrelated contours.

**Trap — the obvious correlation is circular.** `corr(hp_out, hp_src)` on
`out = mus + lambda*hp_src*mask` reads **+0.90** and looks like proof of alignment. It is
not: `hp_out` literally *contains* a copy of `hp_src`. Only `corr(hp_muse, hp_src)`,
computed on the **untouched engine output**, answers the question.

**Ghost control that actually works: count gradient peaks through the lip edge.**
Take one axial column across the lips, `|Sobel_y|`, normalise to its max, count peaks
above 0.40 of the max separated by >=3 px. Same frame, same column:

| Version | Peaks | Reading |
|---|---|---|
| source | 6 | reference lip edges |
| MuseTalk raw | 8 | generated edges, none spurious |
| graft keep=0.00 | 8 | **identical to raw: no ghost** |
| graft keep=0.35 | 7 but one peak at y=641 matches the SOURCE's list | partial ghost |
| graft keep=1.00 | **10 = union of both sets** | double contour |

So on a source whose lips do not coincide with the generated ones, `keep=0.35` (the
"validated compromise" of rule 37) is already enough to leak a source edge into the lips.
`keep=0.00` is the only setting that leaves the lip profile bit-identical to the raw engine
output, and it is the honest choice when the request is a *credible* mouth rather than a
*measured* one. Report the ratio for the lips and for the mouth surroundings **separately** —
only the second one is real.

## The ratio is not portable across source qualities

The 71 % figure above was measured on footage that had been upscaled from a 720p source, so
the untreated base sat at 4 % of a *soft* reference and the ceiling was generous. On native
1080p footage the source is far sharper (mouth lapvar 200-320 instead of ~36), so the same
recipe lands much lower. Same pipeline, measured here:

| Region | MuseTalk raw | graft keep=0.00 lam=3.0 | graft keep=0.35 lam=3.0 |
|---|---|---|---|
| lower face **outside** the lips | 19.0 % | **106 %** (amp 0.958) | 118 % |
| the mouth box (lips) | 5.8 % | 5.8 % (untouched by design) | 51 % (with ghost) |

Tune `lambda` on the **outside-the-lips** zone, targeting high-frequency amplitude 1.00
(`std(hp_out)/std(hp_src)` on that zone): lambda 2.5 -> 0.83, **3.0 -> 0.958**, 3.5 -> 1.085
(over-sharpened). The mask's face feather and vertical ramp attenuate the dose, so the
reference's `lambda = 1.0` is not the right value once a ramp is in the mask.

**Give the ratios their display size.** The same output scored 5.8 % on the tight mouth box
and 19 % on the lower face outside the lips; quoting one number alone makes the result look
better or worse than it is.

Beware the band profile for the same reason: a horizontal band spans the **full width** of the
face, so `levre_sup` / `levre_inf` (measured 0.68-0.76 and 0.76-0.84 of the face height) still
contain the cheeks either side of the mouth. On the delivered file these bands read 94 % / 66 %
while the tight landmark mouth box reads **7.1 %**. The bands show where the *skin* came back;
only the landmark box answers "is the mouth sharp". Report both, never the bands alone.

## Ghost test that survives re-encoding: compare against a no-graft control at the same CRF

Counting gradient peaks across two files at different CRFs measures the **codec**, not the
graft: MuseTalk raw is usually CRF 23 and the treated file CRF 16, and the higher bitrate alone
adds local maxima. A first pass of this test looked like the untreated graft had a ghost; it
had not. **Encode a control with the identical settings and no graft** (`-c:v libx264 -preset
slow -crf 16`), then measure the per-pixel difference:

```python
# in the LIPS (landmark box), per frame:
d = hp(out) - hp(control)          # what the graft actually added
corr(d, hp(source))                # is that addition the source's own detail?
amp = d.std() / hp(source).std()   # how much of it was added?
```

Measured on the delivered files, 6 frames:

| Variant | amp injected into lips | corr with source HF | reading |
|---|---|---|---|
| keep=0.00 | 0.205 | **+0.001** | residual is codec prediction noise, source not injected |
| keep=0.35 | 0.596 | **+0.775** | 60 % of the source's lip edges laid onto generated lips |

Cross-check with the Laplacian on the landmark box: `out_keep0 / control` = **1.007-1.076**
(lips untouched within codec noise) versus `out_keep0.35 / control` = **4.2-13.1x**. The
correlation and the ratio agree, which is what makes the conclusion safe.

## Restrict the graft to a region of interest — it is exact and ~2.3x faster

The mask is `np.clip(1 - r, 0, 1)**0.6`, so it is **exactly 0** outside the face ellipse. Grafting
the whole 1920x1080 frame therefore wastes ~10 full-frame float32 temporaries per image and caps
the pass at 4.8 img/s. Crop to a ROI that clears the ellipse (half-axes 0.625*w and 0.575*h
around the centre -> a 0.40*w / 0.25*h margin is ample), do the high-pass, mask and blend on the
ROI, paste back. The elliptical feather is 0 at the ROI border, so the differing
`cv2.GaussianBlur` edge behaviour is multiplied by zero.

Verified: **0 pixels differing** from the full-frame version over 6 frames x 4 dose
combinations, mask outside the ROI exactly 0. Throughput 10.8 img/s instead of 4.8 (ROI = 44 %
of the frame). Precompute the coordinate grids `YY, XX` once — rebuilding them per frame is a
large part of the original cost. Encoder is not the bottleneck: the numpy graft is, and the two
run in separate processes so total rate tracks the graft rate.

Run the two doses as two parallel processes: each pipeline is one graft thread plus a multi-
threaded x264, so on 12 cores the pair finishes in about the time one would.
