# Fixed-Interval Alternating Montage (FFmpeg concat demuxer)

Programmatic A/B loop without Premiere/XML: two long sources, fixed interval (e.g. 5 s) alternating to one MP4 in a single encode. Companion to `music-synced-montage.md` (energy-driven) and the XML→FFmpeg path.

## When to use
- "5 s de A puis 5 s de B en boucle" from two continuous rushes
- Any `nb_segments = floor(min(durA, durB) / interval)` alternating cut
- User explicitly wants FFmpeg, not MCP/Premiere bridge

## Procedure

### 1. Probe both sources (gate)
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate,avg_frame_rate -of default=nw=1 "A.mp4"
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of default=nw=1 "A.mp4"
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "A.mp4"
# repeat for B.mp4
```
Also `ffprobe -show_entries stream=index,codec_type,codec_name -of csv` to detect missing audio (0 vs 1 audio stream).

### 2. Decide normalisation, do not abort on mismatch
- Video codec/resolution/FPS mismatches and audio sample-rate mismatches are handled in the final filter, not as a blocker.
- Critical mismatch: one source has no audio stream. Concat demuxer then produces an output with audio gaps / DTS errors. Fix before concat.

### 3. If one source lacks audio: generate silence-track copy
```bash
# copy video (no re-encode), synthesize 48 kHz stereo silence up to shortest input
ffmpeg -y -i "A_no_audio.mp4" -f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=48000" \
  -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$TEMP/A_silence.mp4"
```
Verify: `ffprobe -show_entries stream=codec_name,sample_rate -of csv "$TEMP/A_silence.mp4"` and duration matches original.
Use this `A_silence.mp4` as the A entry in the concat demuxer.

### 3b. Integral mode (no second lost) — when the user wants the full length of both sources
- Default truncated mode: `nb = floor(min(durA, durB) / interval)` — discards the tail (`min % interval`) and the second half implied by parallel stride `t=(n//2)*interval`.
- Full-length mode: `nb = ceil(max(durA, durB) / interval)` — user explicitly wants every second kept.
- For each `n` in `0..nb-1`: `src = A if n even else B`, `t = (n//2)*interval`.
- Guard at list generation (do not produce an invalid inpoint):
  - if `t >= dur(src)` → skip that segment (source exhausted, the other continues alone)
  - if `t+interval > dur(src)` → clamp `outpoint = dur(src)` (final segment may be < interval — intentional, never discard remainder)
- Warn before encoding: parallel stride covers ~half the wall-clock range per source (`t_max ≈ (nb/2)*interval`). To cover `0..durA` fully in parallel, `nb` would need `≈ ceil(durA/interval)*2` and output `≈ durA+durB`. Clarify with the user which interpretation was requested — the spec `ceil(max/5)` is ambiguous.
- Verify after encode against `nb*interval` (clamped tail within 0.1 s), not against `max(durA,durB)` alone — the latter will be off by `ceil(max/5)*5 - max`.
- Always print the 6 first + 4 last segments table before launching encoding so the user can spot the stride mismatch. list (B stays original). This is faster and lossless vs re-encoding 45 min of video.

### 4. Compute plan
```
duree = min(durA, durB)
nb_segments = floor(duree / interval)   # e.g. floor(2753.95/5)=550
encoded = nb_segments * interval         # remainder duree % interval ignored
# chronological-parallel alternation: each source advances every 2 segments
for n in 0..nb_segments-1:
  src = A if n%2==0 else B
  t   = (n//2) * interval
  segment n = src[t : t+interval]
```
Print the 6 first rows (n, src, [t, t+interval]) as a sanity table before launching.

### 5. Generate concat list in native TEMP
- Path: `%TEMP%/concat_alternance.txt` (or `$TEMP` / `$LOCALAPPDATA/Temp` on Windows). Native temp avoids MSYS path-translation mismatches.
- Format (FFmpeg concat demuxer):
```
file 'C:/absolute/path/to/A_silence.mp4'
inpoint 0
outpoint 5
file 'C:/absolute/path/to/B.mp4'
inpoint 0
outpoint 5
...
```
- Use forward slashes `C:/` and `-safe 0`. Backslashes or `C:` without `safe 0` fail on Windows.
- Write with Python or printf, then verify with `cat` and `wc -l` (expect `nb_segments*3` lines) before encoding.

### 6. Single-pass encode (background + poll)
```bash
ffmpeg -y -f concat -safe 0 -i "$TEMP/concat_alternance.txt" \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease:eval=frame,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=60" \
  -af "aresample=48000:async=1" \
  -c:v libx264 -preset veryfast -crf 20 -c:a aac -b:a 192k -movflags +faststart "output.mp4"
```
Adapt `-vf`/`-af` to actual mismatch: keep `scale/pad/setsar/fps` + `aresample` even when sources look identical — it makes the job idempotent. For differing resolutions only: same scale/pad. For FPS difference: `fps=` harmonises. When both sources already identical 1920x1080 60 fps 48 kHz, the filters are no-ops with negligible cost.
- Launch background (`notify=true`) and poll/wait until exit code 0. Do not declare done on first wait timeout — ffmpeg for ~2750 s at 60 fps takes 25-35 min even at >1.3x speed.
- Expected benign log: `Auto-inserting h264_mp4toannexb bitstream filter` each segment, occasional `Non-monotonic DTS / Queue input is backward` without pre-normalisation (harmless, ffmpeg corrects). With silence-track + aresample these disappear.

### 7. Verify output
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate -of default=nw=1 "output.mp4"
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of default=nw=1 "output.mp4"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 "output.mp4"
```
Checks: file exists and size>0, `duration ≈ nb_segments*interval` within 0.1 s, resolution/FPS as encoded, audio 48 kHz stereo. Report actual vs expected delta.

### 8. Cleanup
Remove `$TEMP/concat_alternance.txt` and any `$TEMP/A_silence.mp4` copy. Keep only final output.

## Pitfalls

- Probe stream count before building the list — assuming every source has audio produces a concat with audio gaps and `Non-monotonic DTS` storms. If `a:0` is missing, synthesize silence via `-c:v copy` first.
- Use forward-slash absolute paths with `-safe 0` on Windows/MSYS — Git Bash rewrites `C:/` to `/c/` for native ffmpeg and backslash paths fail the demuxer.
- Write the concat list to native `%TEMP%`/`$LOCALAPPDATA/Temp`, not `/tmp` alias alone — native ffmpeg must be able to open the path byte-for-byte as written.
- Derive segment count from `floor(min(durA,durB)/interval)` and ignore the remainder — using `max` or `ceil` emits an `inpoint` beyond the shorter file and aborts mid-encode.
- Alternate chronologically in parallel (`t=(n//2)*interval` per source) — sequential timecode `t=n*interval` on both files skips half the rushes and duplicates nothing useful.
- Never re-encode a whole 45-min source just to add a silence track — `-c:v copy` with `anullsrc` is ~300x faster and lossless; re-encoding is minutes wasted plus generation loss.
