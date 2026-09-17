# Alternating A/B montage via ffmpeg concat (single pass)

Use when the user wants a long montage that alternates two sources every N
seconds (e.g. "5 s A, 5 s B, loop"). Do not create one temp file per segment
and do not call Premiere `insertClip` hundreds of times when ffmpeg is available
and Premiere may be closed.

## Pattern

Generate one `concat.txt` consumed by `ffmpeg -f concat -safe 0 -i concat.txt`.
Each segment is three lines:

```
file '<absolute path to source>'
inpoint <start seconds in that source>
outpoint <start + segment_duration>
```

## inpoint math for chronological alternation

Goal: the output shows both videos advancing in parallel, 5 s at a time.
For segment index `n` (0-based), `segment_duration = 5`:

```
src  = A if n % 2 == 0 else B
t    = (n // 2) * segment_duration   # time inside the chosen source
inpoint  = t
outpoint = t + segment_duration
```

Result for 6 segments: A[0-5], B[0-5], A[5-10], B[5-10], A[10-15], B[10-15].
Total segments = floor(min(durationA, durationB) / 5). Remainder (<5 s) is
dropped; warn the user.

## Single ffmpeg invocation for mixed sources

A is 1920x1080 60 fps, B is 1280x720 50 fps — normalize at the filter, not per
segment:

```
ffmpeg -y -f concat -safe 0 -i concat.txt \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=30" \
  -c:v libx264 -preset veryfast -crf 20 -c:a aac -b:a 192k -r 30 -movflags +faststart \
  output.mp4
```

* `scale`+`pad` handles mismatched resolution; `fps=30` + `-r 30` pins output.
* `-movflags +faststart` for YouTube-friendly mp4.
* Long jobs (45 min+ output) take 10-15 min encoding: run as background
  `terminal(background=true, notify=true)` and poll; use `C:/Users/<user>/AppData/Local/Temp/concat.txt`
  for the list (native path that ffmpeg can read) and clean it after.

## Expected harmless warnings

* `Reconfiguring filter graph because video parameters changed` — at every A<->B switch.
* `Non-monotonic DTS / Queue input is backward in time` — concat of different fps.
* `DTS ... out of order` — same cause. All auto-corrected; do not abort.

## Pitfalls

* Using a single source offset `n*5` for both A and B skips half the footage — use `(n//2)*5` per source.
* Putting `-r 30` as an INPUT option re-timestamps and truncates. Put it only on output.
* MSYS paths like `/tmp/concat.txt` may not be readable by native ffmpeg — prefer the native Temp path.
