# Caen Travelling — best-of montage state (resume point)

Last updated: 2026-08-30 (after gateway-down + step-2 resume)

## Project layout
- Source: `C:\Users\searc\Desktop\4k\caentrav\caentravelling2_4K60_stable.mp4` (7+ GB 4K60)
- Audio: `Jean-Paul Dub - Pélerinage ft. Bout and Huck.wav`
- Cuts grid: `cuts.json` — 67 segments with `start/end/duration/energy`
- Orchestrator: `build_bestof.py` (selection: sort by `energy` desc, cap at
  TARGET_DUR=600s, re-sort chronological; per-seg encode then xfade concat)
- Segment files: `bestof_seg_0.mp4` … `bestof_seg_66.mp4` (1080p60, encoded
  step 1 — DO NOT re-encode; step 2 consumes these)
- Final OUT: `clip_bestof_jeanpaul_dub.mp4` (~162 s with 0.5s xfade)

## Why it stopped (2026-08-29 night)
Step 2 command = 67 `-i` + inline `-filter_complex` (67 xfade) > cmd.exe
8191-char cap → `La ligne de commande est trop longue`, ffmpeg never ran.

## The fix / resume script
`resume_bestof_step2.py` in the same folder:
- Replays build_bestof selection exactly (same sort, same cap) → 67 segments
- Reads REAL durations via ffprobe (not cuts.json)
- Writes filtergraph to `bestof_step2_filter.txt`, uses
  `-filter_complex_script` → cmd line ~4295 chars (safe)
- Audio: `-stream_loop -1` + `-af volume=-3dB`, `-t total_dur`
- Emits `ffmpeg_bestof_step2_cmd.txt` beside project for forensics

## Gotchas
- On 2026-08-30 the selection picks ALL 67 segments → only ~195 s of cuttable
  footage (~162 s final after xfade). If user wants longer best-of, extend
  `cuts.json` grid, not TARGET_DUR.
- ffmpeg 8.1 essentials build (choco) — `-filter_complex_script` prints a
  deprecation warning; `-/filter_complex <file>` is the new spelling.
- `bestof_seg_*.mp4` re-encode with `-crf 18 -preset medium`, xfade 0.5 s.