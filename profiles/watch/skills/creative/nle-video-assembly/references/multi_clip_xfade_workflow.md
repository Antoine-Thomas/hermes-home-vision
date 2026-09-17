# Multi-clip NLE assembly: extraction, xfade, audio replace

Condensed from a real caentravelling job (Premiere `.prproj` → FCP XML `xmeml v4`
→ MP4 keeping ONLY the "Jean-Paul Dub" audio track).

## 1. Extract ALL clips from the XML (don't stop at the first)

A real sequence can have **17+ `clipitem` elements**, including:
- audio clips (the music file itself, in=0 out=195.2) — must be excluded
- the SAME video cut repeated **3x** (once per stacked video track)
- clips from an OLD source file (e.g. `caentravelling.mp4`) when the user
  switched to a NEW master (`caentravelling2_4K60_stable.mp4`)

Robust extraction (Python `xml.etree`):
```python
for ci in root.findall('.//clipitem'):
    f = ci.find('.//file')
    name = ci.findtext('name') or ''
    ins, outs = ci.findtext('in'), ci.findtext('out')   # source in/out, FRAMES
    starts = ci.findtext('start')                       # timeline pos, FRAMES
    if ins is None or outs is None: continue            # skip non-trim clips
    # FILTER to the target master only:
    if not name.lower().startswith('caentravelling2_4k60_stable.mp4'): continue
    clips.append({'in_s': int(ins)/tb, 'out_s': int(outs)/tb,
                  'tl_start_s': int(starts)/tb if starts else 0})
# DEDUPE by (in,out) — stacked tracks duplicate the same cut
seen=set(); uniq=[]
for c in clips:
    k=(c['in_s'],c['out_s'])
    if k in seen: continue
    seen.add(k); uniq.append(c)
uniq.sort(key=lambda c: c['tl_start_s'])      # timeline order
```
In that job the 4 unique cuts were (seconds, in->out):
`2277.78->2298.72 (20.93)`, `2329.53->2421.97 (92.43)`,
`2595.83->2753.95 (158.12)`, `2603.50->2753.95 (150.45)`.

Gotcha: in this XML the `<track>` elements had **no `type` attribute**
(`track type=None`), so a `track[type="Video"]` XPath finds nothing.
Iterate `root.findall('.//clipitem')` and filter by name + in/out instead.

## 2. Per-segment transcode (scale to 1080p60, drop audio, light grade)

```bash
ffmpeg -y -ss {in_s} -i "{SRC}" -t {dur} -an \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=60,unsharp=3:3:0.8:3:3:0.0,eq=saturation=1.12:contrast=1.06" \
  -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -movflags +faststart seg_{i}.mp4
```
Keep segments around; the final step is the slow one. If only the final
mux fails, you can re-run step 3 without re-encoding the segments.

## 3. xfade concat + audio replace (the heavy step)

xfade offsets = cumulative duration of prior segments minus `k*XFADE`
(k = which join). With XFADE=0.5:
```
off1 = d0               - 0.5
off2 = d0+d1            - 1.0
off3 = d0+d1+d2        - 1.5
```
Command (4 segments, audio looped, normalized -3 dB):
```bash
ffmpeg -y -i seg_0.mp4 -i seg_1.mp4 -i seg_2.mp4 -i seg_3.mp4 \
  -stream_loop -1 -i "Jean-Paul Dub - Pe<e-acute>lerinage ft. Bout and Huck.wav" \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=20.4333[v0];[v0][2:v]xfade=transition=fade:duration=0.5:offset=112.3666[v1];[v1][3:v]xfade=transition=fade:duration=0.5:offset=269.9833[v]" \
  -map "[v]" -map "4:a" -af "volume=-3dB" -t 419.4333 \
  -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k -ar 44100 -movflags +faststart clip_final_4K60_v2.mp4
```
- `-stream_loop -1` on the audio **loops it** when the music (195 s) is
  shorter than the assembled video (~419 s). Otherwise the video gets cut
  short by `-shortest`.
- `-map "4:a"` because audio is the 5th input (index 4).
- `-t <total>` = sum(durations) - (n-1)*XFADE.

## 4. CRITICAL: Unicode normalization bug (this broke a real run)

The music file is `Jean-Paul Dub - Pe<e-acute>lerinage ft. Bout and Huck.wav`.
The `e-acute` is **precomposed U+00E9**. If you hardcode the path in Python as
`"Pe\u0301lerinage"` that is a **decomposed** form (P + combining acute U+0301)
- a DIFFERENT byte sequence - and FFmpeg reports
`Error opening input: No such file or directory`.

Rules to avoid it:
- NEVER hand-type accented filenames with `\u0301`. Either copy the exact
  name from `os.listdir()`, or build the path by globbing the folder:
  ```python
  audio = next(p for p in os.listdir(FOLDER) if p.lower().startswith('jean-paul'))
  ```
- In a shell command, paste the real filename (it works fine in bash/MSYS);
  the bug only appears when Python source normalizes the e-acute differently.
- Verify with `os.path.exists()` before launching FFmpeg - it would have
  caught this instantly.

## 5. Run heavy ffmpeg in background

7 GB source + 1080p60 x264 = minutes of encode. Launch with
`terminal(background=true, notify_on_complete=true)`; don't foreground-wait.
