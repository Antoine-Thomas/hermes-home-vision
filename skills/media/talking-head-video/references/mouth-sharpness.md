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
  coordinates, or the crop lands off-target.
- Only `RealESRGAN_x4plus.pth` ships: loading it into an `RRDBNet(scale=2)` raises
  `size mismatch for conv_first.weight`.
- The Laplacian alone can lie: ghost contours inflate it. Confirm visually on a
  frame with the mouth **open**, not closed.
