---
name: ai-video-pipeline
description: Use when managing AI video inference and assembly.
---

# AI Video Pipeline: Best Practices

This skill covers the end-to-end management of AI video generation workflows (like LivePortrait, Wav2Lip), focusing on pre-processing, inference stability, and final assembly.

## 4K True Quality Pipeline (User Spec)

**Target**: 3840×2160 H.265 CRF 18, 45–60 Mbps, AAC 320k, 180–300 s, 800 MB–2 GB.

**Order** (each step writes to disk, next step reads):
1. Photo → GFPGAN restore → Real-ESRGAN x4 (tile=400) → 3840×2160 16:9 PNG + 2048×2048 square PNG
2. Script → XTTS-v2 (segment-by-segment, temp=0.75, speed=1.0) → concatenated WAV (24 kHz mono)
3. SadTalker 512px on square PNG + WAV → driving video (512×512, ~1 frame/s, ~1h for 5 min)
4. LivePortrait HQ on 1024 square + SadTalker driving → 1024p animated (--source-max-dim 512 for 8GB VRAM)
5. Wav2Lip HD (wav2lip_gan) on LivePortrait output + WAV → lip-synced 1024p
6. Real-ESRGAN x4 frame-by-frame (tile=400, half=True) on 1024p frames → 4K frames
7. FFmpeg: 4K frames + 4K background + logo + WAV → H.265 CRF 18 MP4
8. ffprobe verify: 3840×2160, >40 Mbps, 180–300 s, 800 MB–2 GB

**Gotchas**: GFPGAN+Real-ESRGAN combined on VIDEO = OOM (>20 GB peak). Use Real-ESRGAN alone (tile=400), then optional GFPGAN only on detected face crops.

## 8 GB VRAM Rules (RTX 3070 Ti)

- **Never process 4K frames in VRAM** — upscale only at the very end, frame-by-frame with `tile=400`.
- **SadTalker**: `--size 512` is the ceiling; 1024 OOMs. 512 → ~1 frame/s (~1h for 5 min).
- **LivePortrait**: `--source-max-dim 512` (not 1024) + `--flag-use-half-precision` + `--batch-size 1`. 1024 source OOMs at 4000+ frames.
- **Wav2Lip**: `--face_det_batch_size 4 --wav2lip_batch_size 16` (reduce to 1 if OOM).
- **Real-ESRGAN**: `tile=400` mandatory. `half=True` for speed. Frame-by-frame Python loop, never batch.
- **Never combine GFPGAN + Real-ESRGAN on video** — peak >20 GB. Real-ESRGAN alone on full video, GFPGAN only on face crops if needed.
- **Monitor**: `nvidia-smi -l 1` in side terminal. If >7.5 GB allocated, expect thrashing / crawl.
- **LivePortrait writes MP4 in streaming mode** — the `moov atom` is only written at process exit. The file appears "corrupt" (`moov atom not found`, tiny size) until the process finishes. **Do not start Wav2Lip or any consumer until the process exits and ffprobe validates the file.**
- **GPU at 98% VRAM = massive slowdown** (thrashing). If VRAM >7.5 GB during animation phase, expect <1 frame/s instead of ~9 frame/s. Consider reducing `--source-max-dim` further or accepting longer runtime.
- **Driving video denoising**: LivePortrait is extremely sensitive to jitter. Apply temporal denoise (e.g., `hqdn3d=1.5:1.5:6:6`) to driving video BEFORE inference.
- **XTTS-v2 segment generation**: Use `temperature=0.75, speed=1.0` for French. Generate segment-by-segment (one file per paragraph) so a single mangled segment can be re-generated instead of the whole ~5 min voice. Do NOT add silence padding between segments, and TRIM the ~0.6 s of silence the model already appends to each one (keep 120 ms) — otherwise every joint adds ~575 ms of blank and the voice is heard as chopped into blocks (see `tts-voice-cloning`).

3. **Final Assembly (FFmpeg)**
   - **Background loop for image input**: When background is a static image, use `loop=loop=-1:size=N` where N = driving video frame count (from `ffprobe -v error -select_streams v -show_entries stream=nb_frames -of default=noprint_wrappers=1:nokey=1 driving.mp4`).
   - **Face overlay**: Scale animated face to full height, center on background.
   - **Logo overlay**: Scale logo (e.g., 120px wide), position bottom-right with opacity.
   - **Audio mapping**: Map voice audio, use `-shortest` to trim to audio duration.
   - **Encoding**: H.264 CRF 18, preset slow, yuv420p; AAC 192k.
     ```bash
     ffmpeg -y \
       -i background_16_9.png \
       -i animated_face.mp4 \
       -i logo.png \
       -i voice.wav \
       -filter_complex \
       "[0:v]scale=1920:1080,format=yuv420p,loop=loop=-1:size=3262[bg]; \
        [1:v]scale=-1:1080,format=yuva420p[face]; \
        [bg][face]overlay=(W-w)/2:(H-h)/2[bgface]; \
        [2:v]scale=120:-1,format=yuva420p,colorchannelmixer=aa=0.85[logo]; \
        [bgface][logo]overlay=W-w-30:H-h-30[v]" \
       -map "[v]" -map 3:a \
       -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p \
       -c:a aac -b:a 192k -shortest \
       output.mp4
     ```

2. **Inference (LivePortrait, EchoMimicV2, etc.)**
   - **VRAM Monitoring:** Use `nvidia-smi` to monitor usage. If approaching limits, reduce resolution or close other heavy applications.
   - **Model Selection:** Choose based on need (lips-only vs. full-head) and hardware constraints (see `talking-head-video` skill for model comparison).
   - **LivePortrait V7 settings (best quality for this hardware):**
     ```bash
     --flag_stitching --flag_do_crop --flag_relative_motion --source_max_dim 512
     ```
     Note: `--batch-size` is not a valid flag for LivePortrait's `inference.py`; omit it.
     Use `--output_dir` (not `--output`) to specify output directory.
     **Path resolution**: Copy source image and driving video into the LivePortrait repo directory before running `inference.py` — it validates input paths relative to CWD.
   - **SadTalker driving video:** Use safetensors checkpoints (SadTalker_V0.0.2_512.safetensors) — they load without missing pth files. Output appears in `repo/results/<timestamp>/`.

3. **Assembly (FFmpeg)**
   - **Consistent Encoding:** Force frame rate (`-r 30`) at the OUTPUT only. NEVER `-r 30` as an INPUT option on a 25 fps source — it re-timestamps frames and TRUNCATES the video (376 s → 313 s).
   - **Bitrate:** Use high bitrates for complex detail (e.g., `-b:v 15M` for 1080p).
   - **Codec:** Prefer H.264 or H.265 with high constant quality settings.
   - **Final YouTube assembly (1920×1080, H.264 CRF 18):**
     ```bash
     ffmpeg -y \
       -loop 1 -i portrait_16_9.png \
       -stream_loop -1 -i liveportrait_output.mp4 \
       -loop 1 -i hermes_logo_icon.png \
       -i voice.wav \
       -filter_complex "\
       [0:v]scale=1920:1080,format=yuv420p[bg]; \
       [1:v]scale=-1:900,format=yuva420p[face]; \
       [bg][face]overlay=(W-w)/2:(H-h)/2[bgface]; \
       [2:v]scale=120:-1,format=yuva420p,colorchannelmixer=aa=0.85[logo]; \
       [bgface][logo]overlay=W-w-30:H-h-30[v]" \
       -map "[v]" -map 3:a \
       -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p \
       -c:a aac -b:a 192k -shortest \
       youtube_final.mp4
     ```
     - Background loops, face loops (stream_loop), logo loops, `-shortest` stops at audio end.
     - Face scaled to height 900, centered; logo scaled to 120px width, top-right with 30px margin.
     - Use `colorchannelmixer=aa=0.85` for logo opacity if PNG has alpha; else add alpha via `format=yuva420p`.

## FFmpeg Opacity Alternance 1s/1s (sans xfade, sans ecran noir)

Pattern 2s boucle via transparence alpha + overlay — deux sources avancent en parallele, V1 au-dessus de V2 :
- Pitfall : `colorchannelmixer=aa='if(eq(mod(floor(t),2),0),1,0)'` est rejete par libavfilter 11.14 sur cette build (erreur filter) — utiliser `geq` avec `alpha(X,Y)` : `geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(eq(mod(floor(T),2),0),alpha(X,Y),0)'` (noter `T` majuscule pour le temps dans geq).

```
[1:v]setpts=PTS-STARTPTS[base];
[0:v]setpts=PTS-STARTPTS,format=yuva420p,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(eq(mod(floor(T),2),0),alpha(X,Y),0)'[fg];
[base][fg]overlay=0:0:format=auto,eq=...[out]
```

- `colorchannelmixer=aa='if(eq(mod(floor(t),2),0),1,0)'` refuse sur libavfilter 11.14 (ce build) — utiliser `geq` avec `alpha(X,Y)` et `T` (pas `t`). Verifier avec test 10s + extraction frames 0.5s=V1, 1.5s=V2 avant encodage complet.
- Etalonnage chain apres overlay : `eq=contrast=1.05:saturation=1.12:brightness=0.005,curves=all='0/0 0.25/0.22 0.75/0.78 1/1'`.
- Encodage complet : `scale/pad/setsar/fps=60` sur chaque branche, `-c:v libx264 -preset veryfast -crf 20 -r 60 -pix_fmt yuv420p -an -movflags +faststart`.

## FFmpeg Single-Pass xfade Montage (5500+ segments, alternance 1s)

Quand alternance A/B mécanique avec transitions sans Premiere/MCP : construire un seul `filter_complex` chaîné via fichier (`-filter_complex_script` obligatoire au-delà de la limite shell) — jamais `-y` sans vérifier `ls -lh` que la sortie n'existe pas et que le fichier protégé (`montage_alternance_5s.mp4`) reste intact. Voir `references/ffmpeg-xfade-montage.md`.

## FFmpeg Opacity Montage 1s/1s (alternance par transparence, sans xfade)

Quand flash-cut 1s V1 / 1s V2 par alpha sans écran noir : V1 au-dessus avec `geq` alpha `if(eq(mod(floor(T),2),0),alpha(X,Y),0)` overlay sur V2, grading après overlay. Voir `references/ffmpeg-opacity-montage.md` — contient le filter validé (FFmpeg 8.1), le piège `colorchannelmixer` qui échoue, et la procédure de test 10s.
- Découper en `trim`+`setpts` par segment (`n` pair A `[(n//2),(n//2)+1]` sinon B, borné à durée `ffprobe`), appliquer `eq` différencié (A 1.05/1.10/0.01, B 1.03/1.08/0.00) + `scale=1920:1080:force_original_aspect_ratio=decrease:eval=frame,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=60`, puis chaîner `[s0][s1]xfade=transition=...:duration=...:offset=...[xf0]` séquentiellement et finir par `curves`+`vignette` global. Valider parse seul `ffmpeg -filter_complex_script ... -map "[xflast_g]" -f null - -t 2` doit retourner 0 avant l'encodage long (`-c:v libx264 -preset medium -crf 20 -r 60 -pix_fmt yuv420p -an -movflags +faststart`, 1-3h, log dans `%TEMP%`). Durée sortie = sum(segments) - sum(transitions).
- Virages : Farneback 320x180 toutes les 2s, `|mean_flow_x|>2.0` => gauche/droit, `1.0-2.0` => incertain, mapping jonction `[t-1,t+1]` : gauche->`wipeleft:0.5`, droit->`wiperight:0.5`, incertain->alterner, aucun->`fade:0.3`. Timeout analyse 900s => fallback fade partout.
Voir `references/ffmpeg-xfade-montage.md` pour le détail complet (calculs offset/durée, comptage transitions).

## Segmented Inference: Joint Integrity (video + audio)

VRAM forces long renders to be split into segments; the JOINTS are where the defects land.

- **Segment length must be a whole number of generator loop cycles.** A generator that loops a
  short source (a lip-sync model re-uses a 4-8 s source in ping-pong or forward loop) restarts the
  loop phase at EVERY invocation: the next segment resumes on source frame 0 while the previous
  stopped elsewhere, so the POSE JUMPS. Measured: 51 s segments on a moving 200-frame source gave
  5 jumps, adjacent-frame difference 6.5 against a 0.71 median (x9), each peak falling exactly on a
  segment boundary. Pick a duration that is a multiple of one full cycle (2 x 200 frames = 16 s ->
  48 s = 3 cycles). "The joint is invisible" only holds for a quasi-static source — never assume it.
- **Split the driving audio on exact samples.** `-c copy` on AAC cuts on 1024-sample frames
  (~21 ms): segment durations drift, the generated frame count leaves the cycle multiple and the
  jump comes back. Use `-ss`/`-t` with `-c:a pcm_s16le` (WAV) for the splits.
- **Check the joints on the finished file.** Downscale to 320x180 grayscale, compute the mean
  absolute difference between ALL adjacent frames and report median / p99 / max: a jump is an
  isolated peak above ~4x the median, and its frame numbers must be compared against the segment
  starts. Re-run after any change of segment length — a joint is easy to forgive at normal
  playback speed and the user will not.
- **Delivery naming (this user).** Never overwrite the last delivered `.mp4`: each iteration ships
  as a NEW file (`..._FINAL_v7.mp4`, `_v8.mp4`), the previous one stays untouched, and promoting a
  version to the canonical name happens only on an explicit go-ahead, after proving the old file
  did not move (md5 before/after). Ship 2-3 preview stills (`ffmpeg -ss <t> -frames:v 1`) with every
  delivery so the user can judge without watching the whole file.

## Local Generation in ComfyUI (text/image -> video)

For a generation branch with no real source: the model produces the frames, and the operational
traps are all in the SERVER, not in the pipeline. (The exact LTX-2.3 file set and quant choices
live in `talking-head-video-8gb`, branch C; the rules below hold for any local ComfyUI generation.)

- **A code fix only takes effect after a real restart.** An OLD instance still holding the port
  (8188) makes the new one exit silently on a port error, while `/system_stats` keeps answering
  from the old code — the fix then looks useless. Check
  `netstat -ano | grep ":8188.*LISTENING"` plus the PID and its creation time BEFORE doubting the
  fix; kill by PID (never `taskkill /IM python.exe`, rule 4 of the 8 Go skill). Delete
  `ComfyUI/user/comfyui.db` between attempts, and wait until `/system_stats` answers (~60 s to load
  the nodes) before submitting a prompt.
- **ComfyUI caches node OUTPUTS.** Re-submitting the same prompt returns `executed` in 0.00 s
  having generated nothing. To separate generation time from model loading, change an input (prompt
  or seed) instead of re-running the identical graph — and never report the duration of a run that
  FAILED before sampling as a generation time.
- **A quantized checkpoint may not populate every module.** Symptom: the sampler dies with
  `Cannot copy out of meta tensor; no data!` — i.e. parameters left on the meta device. This is a
  LOADING fault, not a missing file: measure before downloading anything.
  - read the builder's own warning first (`grep -a "Uninitialized parameters" <server log>`): the
    node names the empty modules and keeps going instead of raising;
  - compare the number of keys in the loaded state dict against the number of model parameters —
    `0 key out of N` means the dict came back EMPTY (rename ops that do not match that checkpoint's
    naming), not that the file is incomplete;
  - when the dict comes back empty, reload the checkpoint WITHOUT the rename ops and the raw names
    usually line up exactly;
  - some entries of a module list are bare `Parameter`s, not modules: guard with
    `isinstance(m, torch.nn.Module)` before calling `named_parameters()` or `.to()`, otherwise the
    instrumentation itself crashes and hides the real fault.
- **Judge the output by measurement, not by the absence of an error.** A successful job can still be
  a flat or frozen image: compute the spatial standard deviation per frame (a uniform image gives
  ~0) and the mean absolute difference between adjacent frames (motion), and look at one extracted
  still. Report measured numbers, never "it ran".
- **Budget realistically on 8 Go.** Measured reference (LTX-2.3 Q4_K_S, 640x384, 25 frames, 24 fps,
  8 steps, distilled mode, offload on): 133 s cold and 205 s warm, i.e. 5.3-8.2 s per frame,
  16.6-25.6 s per step — 127x to 197x real time, or 2 to 3.5 minutes of GPU per second of video.
  State the per-second-of-video cost to the user instead of a per-clip figure.

## Pitfalls

- **Never put `shortest=1` on an overlay whose second input is a non-looped still image.** `[bgface][logo]overlay=...:shortest=1` fed by a plain `-i logo.png` (single-frame input) truncates the ENTIRE output to one frame: FFmpeg exits 0 and writes a ~1 s file that looks like a success. Either loop the still (`-loop 1 -i logo.png`) or drop `shortest=1` from the overlays and let the muxer's `-shortest` trim the export to the audio. Always `ffprobe` the result and compare its duration against the voice track (`ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 out.mp4`) before declaring the render done — exit code 0 is not evidence the video is complete.
- **Jitter Sensitivity:** AI models like LivePortrait amplify source jitter. If the output looks unstable, stabilize the source FIRST — smooth the driving video with FFmpeg (`smooth_driving_video.py`: `hqdn3d`/`gblur`) into `*_smoothed.mp4` and point `run_liveportrait_volet3.py` `DRIVING` to it (keep `sys.argv[1]` override).
- **FPS Drift:** Any mismatch in FPS throughout the chain leads to stuttering and out-of-sync audio. Set `-r 30` on the OUTPUT only (frame duplication) — the input stays at its native 25 fps (an input `-r 30` truncates duration). In `assemble_final_volet3_blur.py`, put `-r 30` in the encode options, NOT before `-i`.
- **VRAM Saturation:** High-resolution inference will fail or run extremely slowly if VRAM is near capacity. Monitor continuously with `nvidia-smi` BEFORE launching — require ~7+ Go free on 8 Go card; `7.7/8.1 Go + 100% GPU` during LivePortrait starves the Hermes gateway and triggers `shutdown_watchdog` exit 75. For unattended jobs use `deliver=local` on cron, never `deliver=telegram` (blocks event loop).
- **Confirming render/export completion:** a render is done when the output file's size stops growing (stable across two checks ~30 s apart) AND `ffprobe` reads a clean, non-truncated duration matching the source. Do NOT trust the process's cumulative CPU (`Get-Process ... CPU`) — it is a lifetime total that stays high after completion (Premiere Pro, `ffmpeg`, SadTalker all idle at high cumulative CPU). Check the file size + the actual writing process (Adobe Media Encoder / `dynamiclinkmanager`), not the CPU.
- **A tool call reporting a timeout does not mean the job stopped.** Long jobs (renders, re-indexing, downloads) are launched in the background with their output redirected to a log file; when the launch call comes back with a timeout, the job has usually RUN TO COMPLETION (full log, exit code 0, no matching process left). Verify before doing anything: log size and last lines, exit code, then count the processes. Relaunching blind doubles the work and can leave two processes writing the SAME output file (index, mp4). A job that truly died is restarted with resume of the segments already written.

See `references/ffmpeg-settings.md` for specific encoding settings and `references/jitter-smoothing.md` for pre-processing unstable driving videos. encoding templates.
