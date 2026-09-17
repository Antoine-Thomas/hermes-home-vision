---
name: nle-video-assembly
description: "Assemble Premiere/FCP into MP4 keeping only one audio track."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [ffmpeg, premiere, final-cut, video, xml, mp4, audio-replace]
    related_skills: [creative/architecture-diagram]
---

# NLE Video Assembly with FFmpeg

Turn a Premiere Pro / Final Cut Pro project into a finished MP4: clips
concatenated in project order, trimmed to their in/out points, with ALL
original audio removed and replaced by one music file (e.g. a "jeanpaul dub"
track). Common when a user has a travel/vlog master clip trimmed to a song.

## When to use
- User provides a `.prproj` and/or `.xml` plus a target audio file.
- Goal phrased like: "assemble the clips in project order, keep ONLY this
  audio track", "cut all other sounds", "export MP4 1080p".
- The source media (mp4/mov) sits in the same folder as the project.

## Key facts (read before starting)
- `.prproj` is **gzip-compressed binary**. You CANNOT read it as text and must
  not waste turns trying. Ask the user to export
  `Fichier > Exporter > Final Cut Pro XML` (xmeml v4) and hand you the `.xml`.
- The exported XML is xmeml. Clips live under
  `sequence > media > video > track[type="Video"] > clipitem`.
- Each `clipitem` carries:
  - `name` — usually the source file basename
  - `duration` — length in frames
  - `in` / `out` — source in/out **frame** numbers (the cut inside the source)
  - `start` / `end` — timeline position frames (SORT clips by `start`)
  - nested `file > pathurl` — `file://localhost/...` source path (URL-decode,
    strip the `file://localhost/` prefix)
- `sequence > rate > timebase` gives fps (e.g. 60). Convert frames↔seconds by
  dividing by timebase.
- **Framerate preservation rule**: Each segment generated via FFmpeg MUST include
  `-r 60` (or equivalent `fps=60` video filter) in its video filter chain to
  ensure consistent frame rate after xfade concatenation. Without this, xfade
  overlap produces apparent ~8fps playback even when `avg_frame_rate=60/1`
  reports in metadata — the actual displayed framerate is determined by the
  slowest segment in the chain. Always validate with `ffprobe -r_frame_rate`
  before and after assembly.
- Source media usually sits next to the XML. If `pathurl` is missing/relative,
  resolve by matching `name` against files in the source folder.

## Workflow
1. Parse the XML (Python `xml.etree.ElementTree`) → list of clips with source
   path, in/out seconds, timeline start seconds. Sort by timeline start.
   See `references/xmeml_parsing.md` for a parser skeleton.
2. **Prefer ONE FFmpeg command** over multi-step (cut-then-combine). Multi-step
   leaves half-written temp files when the process is killed/timed out, and the
   second step can fail on an unfinished first output ("moov atom not found").
3. Build the FFmpeg command (see `references/ffmpeg_recipes.md`).
4. Run in **background** (`terminal(background=true, notify_on_complete=true)`).
   Encoding a few-minute 1080p clip takes minutes; a 180s foreground timeout
   kills FFmpeg mid-write and produces a corrupt "moov atom not found" file.
5. Verify with `ffprobe` (duration, streams, codecs) before declaring done.

## Pitfalls
- **"moov atom not found" / Invalid data**: NOT real corruption — it means
  FFmpeg was interrupted before finalizing the MP4. Delete the file and re-run;
  it does NOT mean your command is wrong. The fix is letting FFmpeg finish.
- **Place `-ss` BEFORE `-i`** for fast seek (reads only the needed range).
  After `-i` it decodes from 0 and is slow.
- **`-map 0:v -map 1:a`** drops the original audio automatically — you take
  video from input 0 and audio from input 1 only, so no `-an` is needed and no
  original sound survives.
- **`-shortest`** so the music track doesn't extend past the video. If the music
  is shorter than the video, loop it: `-f lavfi -i "amovie=AUDIO:loop=0"`.
- **Timebase**: confirm fps from the XML. A 60fps project's frame numbers
  divide by 60, not 30 or 25.
- **Resolution**: source was 1280x720 in the worked example; scale to 1080p
  with `scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2`.
- Never run `pkill -f ffmpeg` / mass-destructive commands without explicit user
  consent — they get blocked. Just re-run the encode after deleting the bad file.
- **MULTI-CLIP EXTRACTION**: a real sequence has MANY `clipitem`s — not one.
  The XML repeats the same cut 3× (stacked video tracks), includes the AUDIO
  clip itself (filter it out), and may include cuts from an OLD master file.
  Extract every `clipitem`, **filter to the target source by name**, **dedupe by
  (in,out)**, then **sort by timeline `start`**. Don't trust a `track[type="Video"]`
  XPath — in some exports `<track>` has no `type` attr; iterate `findall('.//clipitem')`
  and filter on name + in/out instead. Full recipe in
  `references/multi_clip_xfade_workflow.md`.
- **UNICODE NORMALIZATION (bit a real run)**: accented filenames like
  `Jean-Paul Dub - Pélerinage ft. Bout and Huck.wav` are **precomposed** (é = U+00E9).
  If you hardcode the path in Python as `"P\u0301lerinage"` that is the DECOMPOSED
  form (P + combining acute U+0301) — a DIFFERENT byte string — and FFmpeg dies
  with `Error opening input: No such file or directory`. Always build the path by
  globbing `os.listdir()` (e.g. `next(p for p in os.listdir(FOLDER) if p.lower().startswith('jean-paul'))`)
  or paste the real filename in a shell command. Pre-check with `os.path.exists()`.
- **XFADE CONCAT (multi-clip)**: join segments with `xfade=transition=fade` and
  `offset = cumulative_prior_duration - k*XFADE`. Loop short music with
  `-stream_loop -1`; map audio as the last input index (`-map "<N>:a"`).
  Step-by-step in `references/multi_clip_xfade_workflow.md`.

## Verification
```
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 out.mp4
ffprobe -v error -show_format -show_streams out.mp4
```
Confirm: video h264 + audio aac present, and duration == (out - in) seconds.

## References
- `references/xmeml_parsing.md` — xmeml structure + Python parser skeleton.
- `references/ffmpeg_recipes.md` — known-good single-clip and multi-clip commands.
- `references/multi_clip_xfade_workflow.md` — multi-clip extraction, dedup, xfade
  concat, audio looping, and the Unicode-normalization trap (with worked numbers).
