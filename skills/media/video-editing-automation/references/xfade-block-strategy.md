# Large xfade montage — block strategy (transitions between segments)

Companion to `alternating-concat.md` (which is the no-transition path). Use THIS
when every junction needs a transition (xfade wipe/fade/dissolve), because the
concat demuxer cannot do transitions — it forces a per-segment filter graph.

## The one rule that matters: block size is the dominant speed knob

An xfade chain is O(chain_depth × total_frames): every output frame is passed
through EVERY xfade in its chain, so a single 4000-filter graph renders at
~0.1x realtime. Measured on 1080p60, filter-only (`-f null`):

| segments/block | chain depth | filter speed |
|---|---|---|
| 300 | 299 | 0.26x |
| 100 | 99 | 5.5x |
| 60 | 59 | 6.8x |
| 30 | 29 | 7.3x |

Shallow blocks (30–60) win by ~20x even though they mean more ffmpeg runs and
a deeper final concat chain. Never build one giant xfade chain for hundreds of
segments; split into blocks from the start.

## Procedure (two-pass block + concat)

1. Build the segment list (asymmetric is fine: 2 s A / 1 s B, clamped last
   segment). Total = sum(seg dur) − (n_segments−1)×xfade_dur.
2. Split into blocks of 30–60 segments. Per block write a filter script:
   `[src:v]trim=start=T0:end=T1,setpts=PTS-STARTPTS[vN]` per segment, then
   chain xfades with `offset += prev_seg_dur − xfade_dur` (offset is the
   output-timeline time where the transition STARTS).
3. Render each block to an intermediate:
   `-c:v libx264 -preset ultrafast -crf 16 -pix_fmt yuv420p -an`
   (near-transparent; the final pass re-encodes, so intermediates must be a
   notch above the final crf).
4. Concat pass: one xfade per block boundary (`offset += prev_block_dur −
   xfade_dur`), then apply grading (eq/curves/vignette) ONCE after the last
   xfade — never per block (double generation of the same grade).
5. Smoke-test 2 blocks (concat them, ffprobe duration ≈ d1+d2−xfade) before
   launching the full run.

## Pitfalls

- Drop `scale/pad/setsar/fps` from PER-SEGMENT filter chains when both sources
already match the target res/fps/SAR. `scale=...:eval=frame` re-evaluates per
frame and, multiplied across hundreds of segment chains, cost a 3x slowdown.
(This is the OPPOSITE advice from the single `-vf` in the concat-demuxer path,
where one scale/pad/fps chain on the whole output is negligible.)
- `filter_complex_script` file syntax: end every chain with `;` before the next
filter (missing it → "Trailing garbage after a filter"); write with LF newlines
(`newline='\n'` in Python) — CRLF breaks parsing.
- `-filter_complex_script` is deprecated on ffmpeg 8.x → use `-/filter_complex
<file>`.
- xfade transition names for direction-aware wipes: `wipeleft`, `wiperight`,
`fade`, `wipeup`, `wipedown`.
- The intermediate+final double encode is the cost of the block strategy; the
filter pass is fast, so x264 encode dominates wall time. Estimate from a single
block's measured `speed=Nx` before quoting ETA.
