# Music-Synced Montage (alternate sources on the beat)

Create a music video that alternates several source clips, cutting in sync with
the track's energy. Pure local ffmpeg + librosa — no cloud API, no NLE.

## Pipeline

1. Dedicated venv + deps (don't pollute the Hermes venv):
   `python -m venv venv_edit && venv_edit/Scripts/python.exe -m pip install librosa numpy soundfile scipy`
2. `analyse_musique.py` — librosa → tempo/beats, strong onsets, section
   boundaries, per-segment energy → `cuts.json`.
3. `montage_alternate.py` — pick source per segment by energy, render each
   segment to a temp file (scale/fps/pop-filter), xfade-chain them, then mux
   the normalized audio.

## librosa 0.11 gotchas (verified)

- `librosa.segment.agglomerative()` **no longer accepts `reference=`** (kwarg
  removed in 0.11). Don't use it for section detection. Use a novelty detector
  instead: downsampled spectral features (rms / spectral_centroid / rolloff /
  flatness, each percentile-stretched) → `np.diff` → gaussian_filter1d →
  `scipy.signal.find_peaks(distance≈6s, prominence≈0.35)`.
- `librosa.beat.beat_track` returns `tempo` as an array-like scalar; coerce
  with `float(np.atleast_1d(tempo)[0])`.

## Energy normalization (source selection)

Raw RMS + spectral-flux + centroid on a dense track (e.g. rap @ 152 BPM) skews
high; min-max and even percentile stretch leave most segments reading
"dynamic". Use **rank normalization** so the three buckets (calm / mid /
dynamic) stay balanced while preserving the track's true intensity ordering:

```python
order = np.argsort(raw_energies)
rank = np.zeros(n)
rank[order] = np.linspace(0.05, 0.95, n)
```

Then map: energy<0.3 → calm source, >0.6 → action source, else mid source.

## Cut density

A beat grid at 152 BPM is one beat every 0.39 s — cutting every beat
produces a frantic 2.5 cuts/s. The practical rule is: **2–6 s segments**,
placed on strong onsets or section boundaries, then energy-bucketed.

## Transition rules by energy (verified 2025-08-28)

| Energy bucket | Source | Transition | Duration |
|---------------|--------|------------|----------|
| < 0.3 (calm)  | B (visages SD, plans rapprochés) | fade | 0.4 s |
| 0.3–0.7 (mid) | C (stylisé 4K, plans larges, **rues** → split screen) | slideleft / slideright (alterné) | 0.5 s |
| > 0.7 (dynamic) | A (normal/action, mouvement rapide) | slideleft / slideright (alterné) | 0.5 s |

**NO circular transitions** (`circle`, `circlecrop`, `zoomin`) — they break
the cinematic look. Replaced by slides everywhere except calm passages.

## 1080p 24fps cinematic variant (2025-08-28)

Script: `montage_1080p24.py` (derived from `montage_alternate.py`)

Parameters:
- TARGET_W, TARGET_H = 1920, 1080
- TARGET_FPS = 24 (look cinéma)
- CRF-seg: 20, CRF-final: 18, preset medium
- Audio: AAC 192k, loudnorm I=-14 TP=-3

Creative rules codified:
1. **No circular transitions** — all replaced by fade (calm) or slide (mid/dynamic)
2. **Split screen for streets** — detected by `section` field containing "rue", forces source C
3. **Intentional source alternation**:
   - Source A → dynamic passages (energy > 0.7)
   - Source C → calm/wide passages (energy 0.3–0.7) + streets
   - Source B → close-ups/faces (energy < 0.3)

File protection:
- `cuts_manuel.json` is a **copy** of `cuts.json`, never overwrites original
- Existing clips preserved: `clip_final_4K60*.mp4`, `clip_jeanpaul_dub_alternate.mp4`
- Output: `clip_final_1080p24_directed.mp4` (auto-renames if exists)

## Known source files (Caen Travelling project)

| Source | Path | Specs |
|--------|------|-------|
| A | `caentravelling.mp4` | 1280×720, 50 fps |
| B | `caentravelling_1080p_lent_ stable.mp4` | 1920×1080, 60 fps (SD look) |
| C | `caentravelling2_4K60_stable.mp4` | 1920×1080, 60 fps (stylisé) |
| Audio | `Jean-Paul Dub - Pélerinage ft. Bout and Huck.wav` | 195.2 s, 152 BPM |

## Verification checklist

```bash
# Check output specs
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate,codec_name \
  -of csv=p=0 clip_final_1080p24_directed.mp4
# Expected: h264,1920,1080,24/1

ffprobe -v error -show_entries format=duration \
  -of csv=p=0 clip_final_1080p24_directed.mp4
# Expected: ~195.2 s
```

## Pitfalls

- **Windows paths**: native tools (ffmpeg, python) need `C:/...` not `/c/...`
- **ffmpeg xfade offset math**: cumulative duration minus cumulative transition time
  — the formula in `assemble()` is the only one that prevents drift.
- **Duration compensation**: sum of all xfade durations is LOST from final video.
  The pad segment at the end (same source as last segment) compensates exactly.
- **Source B already SD**: skip POP filter (unsharp/eq) to avoid double-sharpening.
- **Audio sample rate**: 48kHz required for loudnorm TP=-3; the `aresample=48000`
  in filter_complex handles it even if source WAV is 44.1kHz.
- **Temp dir cleanup**: `--keep` flag preserves segments for debugging; default
  cleans up automatically.