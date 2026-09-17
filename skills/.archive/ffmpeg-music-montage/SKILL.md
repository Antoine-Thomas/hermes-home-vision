---
name: ffmpeg-music-montage
description: "Music-synced montage from librosa energy analysis."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [video, ffmpeg, montage, music, librosa, xfade, audio-analysis]
    related_skills: [video-editing-automation, media]
---

# FFmpeg Music-Synced Alternate Montage

Use this skill when the user wants a video montage assembled from multiple
source clips, cut to a music track, where each segment's **source clip** and
**transition** are chosen automatically from the **audio energy** at that
moment (calm parts → close/slow footage, energetic parts → action footage).

This is the *programmatic* path (librosa + ffmpeg, no Premiere/XML). For the
Premiere Pro XML → FFmpeg path, see `video-editing-automation`.

## When to Use

- "Montage alterné synchronisé sur la musique X à partir de N sources"
- "Cut a video to the beat / energy of this song"
- Beat- or energy-driven montage where source choice depends on musical intensity
- Any ffmpeg xfade-chain assembly where output must cover the FULL audio length

## Windows: command-line length cap (8191 chars)

A montage with MANY inputs (60+ segment files) plus a long `-filter_complex`
xfade chain blows past cmd.exe's ~8191-char limit and dies with
`The command line is too long` / `La ligne de commande est trop longue`.
Typical signature: the per-segment encode step all succeeded, but the final
concat command "never ran" (or the user says it stopped "after the clips").

Fix:
- Put the filtergraph in a file: `-filter_complex_script graph.txt`. The `-i`
  inputs alone are usually fine; the filter string is what crosses the cap.
- ffmpeg 8.x prints `-filter_complex_script is deprecated, use -/filter_complex
  <file>` — the `-/` prefix is the new spelling, the old flag still works.
- Print `len(cmd)` before launching to confirm you're under the cap (~4295c
  with 67 inputs + file-based filter is fine).

## Resuming a crashed multi-step montage (skip completed steps)

If the pipeline dies between steps (reboot, shell cap, OOM):
1. Inventory artifacts — which `seg_*.mp4` exist, is the final OUT absent?
2. Do NOT rerun the whole script: re-encoding finished segments is wasted work.
3. Write a resume script that reproduces the selection EXACTLY (same sort key,
   same TARGET_DUR) so concat order matches the files on disk.
4. Read REAL durations from encoded segments via `ffprobe -show_entries
   format=duration`, not the JSON grid (encoding rounding drifts).
5. Keep the generated filtergraph + command text next to the project for
   forensics, and make the resume step re-runnable.

Project-specific state (Caen Travelling best-of): see
`references/caen-travelling-bestof.md`.

## Core Workflow

1. **Analyze the music** → produce a cuts grid (`cuts.json`): one entry per
   segment with `start`, `end`, `duration`, `energy` (0..1).
   - Use librosa: load audio, compute RMS/energy per frame, segment by beats
     (`librosa.beat.beat_track`) or fixed windows. BPM helps size segments
     (e.g. 2–5 s at 152 BPM).
2. **Normalize energy by RANK** (critical — see Pitfalls). Map raw energy to
   0..1 by sorting all segment energies and assigning percentile rank, so the
   thresholds below are meaningful regardless of how compressed/loud the track is.
3. **Select source per segment** by normalized energy:
   - `energy < 0.3`  → source B (close-ups / slow / calm footage)
   - `0.3 ≤ energy ≤ 0.7` → source C (stylized / wide)
   - `energy > 0.7`  → source A (action / fast movement)
   (Rename A/B/C to your actual files; the rule is *calm→intimate, hot→action*.)
4. **Map transition per segment** by energy (duration ∝ energy), and ALTERNATE
   direction/type so consecutive cuts don't look identical:
   - `< 0.3`     → `fade` 0.3 s
   - `0.3..0.7`  → `slideleft`/`slideright` 0.4 s (alternate by index)
   - `> 0.7`     → `zoomin`/`circlecrop` 0.5 s (alternate by index)
5. **Encode per-segment temp clips** with seek (`-ss` BEFORE `-i`) + `-t dur`
   so each source is decoded only for its slice (fast, no re-decode of whole
   file). Apply a per-source video filter (see below).
6. **Assemble with ONE filter_complex xfade chain**:
   `[0:v][1:v]xfade=transition=<t>:duration=<T>:offset=<o>[v1];
    [v1][2:v]xfade=transition=...:offset=<o2>[v2]; ... [vN-1][N:v]xfade...[vout]`
   - `offset` for the i-th xfade = `sum(durations so far) − sum(transition durations so far)`.
   - Audio: `[A:a]atrim=0:<total>,asetpts=PTS-STARTPTS,aresample=48000,loudnorm=I=-14:TP=-3.0[aout]`.
7. **Compensate the lost duration** (see Pitfalls) so the video covers the
   entire song, then mux with `+faststart`.

## Per-Source Video Filters (example)

- **A (1280×720 → 1080)**: `scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,<POP>,fps=60,format=yuv420p`
- **B (already 1080, SD look)**: `fps=60,format=yuv420p` (skip the pop filter)
- **C (1080 stylized)**: `<POP>,fps=60,format=yuv420p`
- `POP = unsharp=5:5:0.8:3:3:0.4,eq=saturation=1.12:contrast=1.06`

Target: `1920×1080`, `60 fps`, `libx264 -crf 16` for temp segments
(near-lossless, since they get re-encoded), `-crf 18` for the final mux,
`-pix_fmt yuv420p`, `-c:a aac -b:a 192k`, `-movflags +faststart`.

## Pitfalls (read before building)

### Energy rank-normalization is mandatory
Raw librosa RMS energy on **compressed EDM / loud masters gets crushed**
(typical max ≈ 0.4–0.5, everything bunched low), so fixed thresholds like
`> 0.7` would *never* trigger. Fix: sort the segment energies, assign each its
percentile rank in [0,1], and threshold on the rank. This spreads calm/mid/hot
evenly regardless of mastering. See `references/energy-and-duration.md`.

### The xfade duration-compensation trap
Each xfade of length `T` **overlaps** T seconds between adjacent clips, so the
final video is SHORTER than the sum of segment durations by `Σ T`. Over a 195 s
track with ~66 transitions you lose ~26–33 s and the video won't reach the end
of the song.

Fix: append a **pad segment** (same source/energy as the last real segment)
whose duration `P = Σ(all transition durations)`. Then the output duration
`= Σ(seg durations) + P − Σ(T) = Σ(seg durations)`, exactly covering the audio.
Trim the audio to that total with `atrim`. Full formula in
`references/energy-and-duration.md`.

### Don't repeat the same transition visually
Consecutive identical transitions (e.g. two `slideleft`) read as a glitch.
Alternate direction/type by segment index (`idx % 2`).

### Protect existing clips
Never overwrite the user's prior renders. Write test/full outputs to NEW
filenames and never open the old clips in the script.

## Verification

After encoding, `ffprobe` the output: confirm `width=1920 height=1080`
`r_frame_rate=60/1`, a video stream AND an audio stream, and that
`format.duration` ≈ the music length (post-compensation). Log the segment
count, source distribution (A/B/C counts), and transition counts in the
script's stdout so the run is auditable.

---

## Comparative Montage Pattern (Reality vs Stylised)

**When to use**: User wants a side-by-side comparison of two versions of the same footage (e.g. original vs AI-stylised, different grades, different cameras) on identical timecodes, with strict alternation.

### Core Concept
- Two sources: **Reality** (original) and **SD** (stylised/generated) — same resolution/fps
- For each extract, create TWO segments with identical in/out: one from Reality, one from SD
- Strict alternation: Reality → SD → Reality → SD (no consecutive same source)
- Transitions chosen by CONTENT TYPE, not energy:
  - **Faces/portraits** → `fade` 0.5s (smooth dissolve)
  - **Streets/buildings/churches** → `slideleft`/`slideright` 0.4s (dynamic) OR split-screen
  - Split-screen: Reality left, SD right — useful for architectural comparisons

### Multi-Focus Clips from One Project
When the project has diverse content, produce **separate comparative clips** per category:
1. Create a config per category: `cuts_visages.json`, `cuts_eglises.json`, `cuts_rues.json`
2. Each config contains ONLY extracts of that category (filtered from `extracts.json`/XML)
3. Single reusable script `montage_comparatif.py` takes `--cuts` and `--out`
4. Output files: `clip_comparatif_visages.mp4`, `clip_comparatif_eglises.mp4`, `clip_comparatif_rues.mp4`

### Configuration Pattern (config-as-copy)
- Original `cuts.json` / `extracts.json` are NEVER modified
- Each comparative clip gets its own `cuts_<category>.json` (copy + filter)
- Script reads `--cuts` argument — zero code duplication
- Existing output clips are NEVER overwritten (new filenames always)

### Transition Rules for Comparative
| Content | Transition | Duration | Notes |
|---------|-----------|----------|-------|
| Faces, portraits, close-ups | `fade` | 0.5s | Dissolve shows subtle differences |
| Streets, wide movement | `slideleft` / `slideright` | 0.4s | Alternate direction per pair |
| Churches, architecture | `slide` OR split-screen | 0.4s | Split-screen = both visible simultaneously |

### Pitfalls Added This Session
- **Windows path handling**: Python subprocess needs `C:/Users/...` not `/c/Users/...` for native tools (ffmpeg)
- **Foreground timeout**: Long encodes (>600s) must use `background=true, notify=true` + `process(wait)`
- **xfade offset formula** must match exactly: `offset_i = cumsum(durations[0..i-1]) - cumsum(T[1..i])`
- **Pad segment**: Always append a pad segment with same source/transition as last real segment to compensate total xfade overlap
- **Energy rank normalisation**: Critical for threshold stability across different tracks (see `references/energy-and-duration.md`)

### Reusable Script Template
See `scripts/montage_comparatif.py` (added below) — single script, multiple configs.
