---
name: video-editing-automation
description: "Automate video assembly from Premiere Pro with FFmpeg."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [video, editing, premiere-pro, ffmpeg, automation, xml, audio]
    related_skills: [media]
---

# Video Editing Automation

Use this skill when automating video editing workflows, particularly for:
- Processing Adobe Premiere Pro projects
- Assembling video clips in sequence
- Managing audio tracks with FFmpeg
- Exporting final videos with specific settings

## When to Use

- User asks to assemble clips from a Premiere Pro project
- Need to extract clip order from a Premiere Pro timeline
- Want to replace or isolate specific audio tracks
- Automate batch video processing with FFmpeg
- Create a beat-synced montage that alternates multiple source clips (music video)

## Key Workflows

### 1. Premiere Pro Project Analysis

**Important**: Adobe Premiere Pro `.prproj` files are binary/compressed and cannot be read directly as text. You must:

1. **Ask user to export XML**:
   ```
   In Premiere Pro: File > Export > Final Cut Pro XML...
   Save as: project_name.xml in the same folder
   ```

2. **The XML contains**:
   - Clip sequence order
   - Source file paths
   - In/Out points (cut points)
   - Audio/video track information

3. **Common XML structure elements**:
   - `<sequence>`: The main timeline
   - `<clipitem>`: Individual clips with `id`, `name`, `duration`
   - `<file>`: Source media files with `id`, `name`, `pathurl`
   - `<in>` and `<out>`: Trim points for each clip

4. **CRITICAL — walk every track, then dedupe.** Reading only the first
   `<video>` track makes a 4-extract timeline look like a single clip, and you
   will confidently produce the wrong film. Always:
   - iterate **all** `<clipitem>` under **all** tracks (video and audio);
   - filter on the requested source filename — an XML routinely still
     references older renders (`projet.mp4` next to `projet2_stable.mp4`);
   - **dedupe on `(in_s, out_s)`** — the same extract appears once per
     superimposed video track, so 17 raw clipitems can be only 4 real extracts;
   - sort by timeline start, not by document order;
   - persist the result to `extracts.json` so later steps and reruns share one
     source of truth.

   Convert frames to seconds with the sequence `<timebase>`, and print the
   retained extract list for the user before encoding anything.

### 2. FFmpeg Video Assembly

**Basic concatenation** (when no cuts needed):
```bash
ffmpeg -f concat -safe 0 -i clips.txt -c copy output_no_audio.mp4
```

**With specific audio track**:
```bash
ffmpeg -i output_no_audio.mp4 -i "audio_file.wav" -c:v copy -c:a aac -map 0:v -map 1:a final_output.mp4
```

**With cuts/trims** (using filter complex):
```bash
ffmpeg -i input.mp4 -ss 00:00:10 -t 00:00:30 -c copy trimmed.mp4
```

### 3. Audio Management

**Finding specific audio files**:
```bash
# Windows PowerShell
Get-ChildItem -Path "C:\path\to\folder" -Recurse -Include "*audio_name*" -File

# Bash (Windows git-bash/MSYS)
find "C:/path/to/folder" -type f -iname "*audio_name*"
```

**Isolating specific audio track**:
- Premiere Pro often has multiple audio tracks
- Identify the target track name from XML or user input
- Use only that track, remove all others

### 4. Music-Synced Montage (beat-synced alternation)

Alternate several source clips in sync with a music track: analyse the audio
with librosa (tempo, downbeats, strong onsets, section boundaries, per-segment
energy → `cuts.json`), then assemble with ffmpeg `xfade` chaining and mux the
normalized audio.

Full recipe — including the xfade chaining math, librosa 0.11 API changes
(`agglomerative` dropped `reference=`, no `zoom` transition → `zoomin`),
rank-normalized energy, and peak normalization to -3 dBFS — lives in
`references/music-synced-montage.md`.

Key points:
- Create a dedicated venv for librosa/numpy/soundfile/scipy — don't pollute the Hermes venv.
- Probe every source with `ffprobe` first (duration/resolution/fps).
- Rank-normalize energy (`np.argsort` → `linspace(0.05,0.95,n)`) so calm/mid/dynamic buckets stay balanced even on a uniformly energetic track.
- Render each segment to a temp file with `scale+pad+fps=60+format=yuv420p`, then xfade-chain; per-segment temp files beat one giant filter_complex.
- Never overwrite existing deliverables — always a new output name.

## Step-by-Step Workflow

### Phase 1: Project Analysis
1. **Check if XML exists** - Look for `.xml` file alongside `.prproj`
2. **If no XML, request export** - Ask user to export from Premiere Pro
3. **Parse XML for clip sequence** - Extract order and source paths
4. **Identify target audio** - Find the specific audio file to use

### Phase 2: Video Assembly
1. **Create clip list** - Generate `clips.txt` for FFmpeg concat
2. **Apply cuts if needed** - Use trim filters for in/out points
3. **Assemble video** - Concatenate clips in correct order
4. **Add target audio** - Replace all audio with specified track

### Phase 3: Export
1. **Set export parameters** - H.264, 1080p, MP4 container
2. **Name output file** - Use descriptive name (e.g., `clip_final.mp4`)
3. **Verify output** - Check file exists and has correct duration

## Pitfalls & Solutions

### Pitfall 1: Binary .prproj File
**Problem**: Cannot read `.prproj` directly
**Solution**: Always request XML export first

### Pitfall 2: Path Issues on Windows
**Problem**: Paths in XML may have different format
**Solution**: Normalize paths, convert `file://localhost/` to regular paths

### Pitfall 3: Multiple Audio Tracks
**Problem**: Premiere projects often have multiple audio tracks
**Solution**: Identify specific track by name, isolate it with `-map` in FFmpeg

### Pitfall 4: Codec Compatibility
**Problem**: Different clips may have different codecs
**Solution**: Re-encode with consistent codec instead of `-c copy`

## FFmpeg Common Commands

```bash
# Check video info
ffmpeg -i input.mp4

# Extract audio only
ffmpeg -i input.mp4 -vn -acodec copy audio.aac

# Replace audio
ffmpeg -i video_no_audio.mp4 -i new_audio.wav -c:v copy -c:a aac -map 0:v -map 1:a output.mp4

# Trim video
ffmpeg -i input.mp4 -ss 00:01:00 -t 00:02:00 -c copy trimmed.mp4

# Convert to 1080p H.264
ffmpeg -i input.mp4 -vf "scale=1920:1080" -c:v libx264 -crf 23 -preset medium -c:a aac output.mp4
```

## Verification Steps

1. **Output file exists** and has non-zero size
2. **Duration matches** expected total clip time
3. **Audio is present** and is the correct track
4. **Video quality** is as specified (1080p, H.264)
5. **No other audio tracks** are present (only the specified one)

## Related Tools

- **FFmpeg**: Video/audio processing
- **XML parsers**: Python `xml.etree.ElementTree`, `lxml`
- **Path utilities**: `os.path` for cross-platform path handling
- **File search**: `find`, `Get-ChildItem` for locating media files

## Supporting files

- `references/music-synced-montage.md` — librosa energy analysis + xfade recipe.
- `references/title-cards.md` — stylized title cards / intro-outro: PIL gradient
  text + Google Fonts (Cinzel/Montserrat), then ffmpeg `-loop 1` → 1080p60 video
  with fade, matching the clip's codec so it concats cleanly.