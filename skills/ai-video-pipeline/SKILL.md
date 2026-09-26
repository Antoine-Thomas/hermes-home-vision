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
- **The source must cover the WHOLE audio, or the generator fills the remainder BACKWARDS.** The
  same loop-phase rule bites at the end of the render, silently: with 300 s of source for 343.8 s of
  audio, the model completed the last 44 s by inverting the loop, so the face talks backwards for
  44 s and nothing in the logs says so. Render the loop at the exact audio duration first
  (`-stream_loop -1 -i source -t <audio_s>` then downscale) — minutes of ffmpeg against hours of GPU
  — and then check the worst junction on the RENDERED file against the mean adjacent-frame
  difference of that same file (measured 0.86 against a 1.00 reference, identical to the shorter
  render). Ending mid-cycle does not matter: the video stops there, there is no joint at that end.
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
  16.6-25.6 s per step. CORRECTION (measured again 22/09/2026, same settings, 25/49/97 frames =
  1.0/2.0/4.0 s of video): totals 170.6 / 150.8 / 161.1 s, sampler 93 / 89 / 98 s. Quadrupling the
  video length moves the total by under 10 %: at this resolution the cost is a FIXED ~2.5-3 min
  per clip (dominated by reloading the 13 GB transformer and streaming it through 8 GB of VRAM),
  NOT a cost per second of video. Quote a per-clip figure and say so explicitly; the
  per-second projection only held for the first 25 frames.

Driving the server from a script over N items (one prompt per item, per-item timing read from
`/history`, `SaveImage` subfolder, node caching, resume, journal): `references/comfyui-api-batch.md`.

## Enhancing an EXISTING Video (restore / upscale / restyle, keep audio + duration)

Opposite case from generation: the source already exists, so the round trip is frames -> processing ->
reassembly with the original audio, and the risk sits in the INGEST and the MODEL CHOICE, not in the
sampler.

1. **ffprobe the source and report MEASURED values before agreeing to the brief.** The resolution in
   the request is a claim, not a fact: a clip delivered as "1080p, keep 1080p" measured
   1280x720 / 30 fps / 9.67 s / h264 + aac 48 kHz stereo. If the target is ABOVE the source, the job
   is an UPSCALE — say "upscale", never "keep", and get the go-ahead before the heavy run.
   `ffprobe -v error -show_entries format=duration,bit_rate -show_entries stream=width,height,r_frame_rate,codec_name,codec_type -of json "<src>"`
2. **Ingest**: pull the audio out first with `-vn -acodec copy` (no re-encode, original track intact),
   then the frames with `-qscale:v 1` PNG. Never touch the source file — work on copies in a frames dir.
3. **Budget the disk BEFORE extracting every frame.** A 720p PNG weighs ~0.9 MB: 9.7 s at 30 fps =
   290 frames = 256 MB, i.e. ~28 MB of PNG per second of source. Compute `duration x fps` and the size
   first; past ~a minute of source, process per SEGMENT (extract / process / reassemble slice) instead
   of dumping the whole clip, keeping the frame numbering contiguous for the reassembly.
4. **Count the extracted frames with POSIX tools** — `ls <dir> | grep -c '\.png$'` — never a cmd.exe
   pipeline through this bash terminal (`dir ... | find /c /v ""` resolves `find` to GNU find, which
   walks the filesystem and never returns; measured: killed at 180 s with all 290 PNG on disk).
5. **Reassemble at the SOURCE fps** (`-framerate <src fps> -i frame_%05d.png -c:v libx264 -crf 18
   -pix_fmt yuv420p`), then mux the original audio (`-c:v copy -c:a aac -b:a 192k -af apad -shortest`)
   and verify with ffprobe (resolution, duration, both codecs) — exit code 0 is not evidence of a
   complete file. **A bare `-shortest` silently drops the tail when the audio track is shorter than
   the image sequence**: an audio duration rarely lands exactly on `frames / fps` (measured 9.614 s of
   AAC against 9.667 s of video, i.e. the last 2 frames cut). `-af apad` pads the audio to infinity so
   `-shortest` then cuts on the VIDEO; keep the bare `-shortest` only when the brief really is "trim
   the video to the audio".
6. **Inventory the models BEFORE proposing a strategy: the strategy depends on what is on disk.**
   `ls -la` each of `checkpoints/ diffusion_models/ unet/ text_encoders/ vae/ clip_vision/ loras/
   upscale_models/ controlnet/`. The 0-byte `put_*_here` entries are placeholders, real weights are
   GB-sized, so a directory holding only markers means that family is ABSENT. An install holding ONLY
   the generation branch (GGUF unet + its VAEs, no SD/Flux checkpoint) cannot run a frame-by-frame
   restyle: say so and ask before downloading. Two traps measured on this machine: a checkpoint can
   live OUTSIDE ComfyUI (an SDXL single-file under `hermes\data\sdxl_lora\`, made visible with a hard
   link `os.link()` — same inode, zero extra bytes, and `st_nlink == 2` proves it), and a checkpoint
   that IS in the folder may not be the one you think: read the safetensors header (tensor count,
   families `model.diffusion_model` / `cond_stage_model.transformer` / `first_stage_model`, and the
   declared tensor range against the real file size — a truncated file loads with an opaque error
   much later). Announce the strategy after the inventory, never before.
7. **img2img restyle strength (user spec)**: denoise 0.25-0.35 gains detail while keeping the
   composition, 0.40-0.55 changes more at the cost of pose drift. State the value actually used.
8. **Reading a workflow JSON you did not author: the per-node `mode` decides the real path** — 0
   active, 2 muted, 4 bypassed. Nodes left at 4 (API-based text encoders, typically) are NOT the ones
   feeding the conditioning; follow the wires to the active node instead (a local text-encoder loader).
   For a 1080p decode on 8 Go, look for the tiled decode node (`LTXVTiledVAEDecode`) rather than a
   plain VAE decode.
9. **A per-frame generative pass is gated by the INTER-FRAME FLICKER, and that gate is measured
   before the full run — on ~8 CONSECUTIVE frames.** Every frame is synthesized independently, so the
   texture is re-invented frame to frame; the defect only shows in motion, never on a still. Metric:
   high-pass both source and render (sigma ~1.8), take the difference between adjacent frames in that
   band, and report the ratio render/source PLUS the correlation between the two difference signals.
   Measured on SDXL img2img, 1280x720, denoise 0.30, fixed seed, real portrait clip: ratio 1.48-1.52
   (quote both aggregations — mean of the per-pair ratios and ratio of the means straddle a 1.5
   threshold) with a difference correlation of 0.106, i.e. the render's frame-to-frame changes no
   longer follow the source's. Add a per-pixel temporal standard deviation pass: in the 42.7 % of
   pixels the source keeps static, the render adds 1.6 level out of 255 of shimmer (0.6 %). REPORT
   THE ABSOLUTE AMPLITUDE, not only the ratio — the denominator is biased low by the codec, which
   freezes static blocks (0.4 level), so a 4x ratio can still describe something invisible.
10. **Fix the flicker by REPLACING the high-frequency band, never by an additive graft.** Both are
    measured on the same 8 probe frames with numpy, no GPU (the frames are already produced, so the
    test costs nothing):

    | variant | flicker ratio | diff. correlation | HF amplitude | HF correlation | Laplacian |
    |---|---|---|---|---|---|
    | raw render | 1.48 | 0.106 | 0.93 | 0.700 | 169 |
    | render + 0.7 x source HF (usual graft) | 1.60 | 0.405 | 1.13 | 0.832 | 291 |
    | low-pass(render) + source HF | 1.05 | 0.755 | 0.91 | 0.934 | 188 |
    | low-pass(render) + temporally smoothed render HF + 0.7 x source HF | 1.23 | 0.502 | 0.97 | 0.870 | 189 |

    The additive graft AMPLIFIES the incoherence while adding the most sharpness; full replacement
    brings the flicker down to the source's own level and even IMPROVES structural fidelity
    (0.700 -> 0.934), because the band then comes entirely from a real, temporally coherent source.
    Whatever the variant, test the candidate fix ON THE PROBE FRAMES before asking for another GPU
    run — that is what turns a failed gate into a decision instead of a dead end.
11. **Cost the frames, and never extrapolate from a mean that includes the cold item.** SDXL img2img
    at 1280x720 measured 19.3 s for the first frame (model load) then 10.9-11.2 s steady, VRAM
    5.0-5.9 GB steady / 7.1 GB peak. `denoise 0.30` with `steps 25` samples only `int(25 x 0.30) = 7`
    steps — quote that pair explicitly, otherwise the estimate is off by 3.5x. Projection = first item
    + (n-1) x steady; averaging a 3-item probe inflated a 290-frame job from 54 to 67 min.
12. **Restyle at the SOURCE resolution, then upscale — never the reverse.** Restyling after an
    upscale pays 2.25x the pixels (720p -> 1080p) for the same result, and the diffusion pass costs
    more than the upscale (11 s vs 3.5 s per frame measured).
13. **The upscale implementation decides the throughput: measure the interpreter, not the model.**
    Real-ESRGAN x4 with tile=400 / tile_pad=10 / half=True, on the same 20 frames of 720p -> 5120x2880,
    measured on this machine: the Python/CUDA path (`from realesrgan import RealESRGANer`) ran at
    3.55 s per image, while the ncnn/Vulkan executable ran at ~70 s per image — 20x for identical
    output. Pick Python/CUDA whenever CUDA is available; the ncnn binary is the fallback when there is
    no PyTorch stack. Instantiating the model needs BOTH `realesrgan` and `basicsr` in the same
    interpreter (`basicsr` alone is not enough, it only provides `RRDBNet`), so prove it with the
    import before choosing the interpreter. Throughput is also resolution-bound, so time 20 images of
    the ACTUAL size before projecting a full run — a figure inherited from another project at another
    resolution will be wrong by a large factor.
14. **When a probe was agreed with a threshold, STOP on breach and report — and spend the stop on a
    measurement, not on a rerun.** The gate is the deliverable at that point: give the raw numbers,
    say plainly that the heavy run was not launched, and test the candidate FIX on the frames already
    produced (see item 10 — a numpy pass over 8 frames turned a failed gate into a measured
    alternative). Do not chain a second GPU run, and do not present an unvalidated workaround as the
    plan; propose the options with their measured or estimated cost and let the user choose.
15. **At the UPSCALED stage the flicker ratio stops measuring flicker — run a CONTROL chain with the
    same instrument before judging it.** The gate is only interpretable where the reference IS the real
    source at the same resolution. Measured against a Lanczos-upscaled reference, a chain containing no
    generative model at all (upscale of the source + additive graft, which cannot flicker by
    construction) scored 1.643 with a difference correlation of 0.210, i.e. it breaches the 1.5 stop on
    its own — because at that resolution the metric mostly counts the detail that was ADDED, against a
    soft, temporally frozen reference. So: (a) always measure the control and quote its number next to
    yours; (b) when the question is "did the generative pass make it worse", compare the two candidate
    chains against EACH OTHER at the same resolution rather than against a resampled reference — the
    SDXL chain came out at +7 % over the control with a difference correlation three times better
    (0.672 against 0.210), the opposite conclusion from its raw 1.76. A ratio quoted without its
    control is not a verdict.
    **Do not carry the HF replacement (item 10) up to the upscaled stage.** Replacement cures the
    flicker by taking the whole band from the source, so applied AFTER the upscaler it throws away
    exactly what the upscaler produced: measured Laplacian 62, against 177 for the upscale alone and
    233 with the additive graft. The recipe satisfying both gates: restyle at source resolution ->
    REPLACE the high frequencies at that resolution -> upscale -> additive graft from the (upscaled)
    source as the very last step.
16. **Run the heavy chain as a resumable per-stage orchestrator, and KEEP the expensive intermediate.**
    One orchestrator, one stage per step (restyle / HF band / upscale / final graft / mux), each stage
    skipping the items already on disk so an interruption resumes instead of restarting, each stage
    aborting the chain with its raw output on failure. Do not delete the big intermediate (the 4x
    upscaled frames): it is what makes a late "try another graft alpha / another mask" cost minutes
    instead of re-paying the whole diffusion pass. Say so in the cost report — it is what makes a
    post-delivery tweak cheap.
17. **Measured end-to-end run (290 frames, 720p -> 1080p portrait, RTX 3070 Ti): the numbers to
    calibrate against.** Stages and wall clock: restyle 58.6 min, HF replacement 0.5, Real-ESRGAN x4
    16.2, final graft 1.9, encode+mux 0.2 = 77.4 min total for a 9.67 s clip (5.3x the clip's own
    GPU-on time budget is not the limit — disk streaming and per-item overhead are). Sharpness
    (Laplacian, one instrument over 12 frames spread across the clip): plain Lanczos 1080p 59.3,
    SDXL 720p 174.3, + HF replacement 196.5, + upscale 169.1, final 229.1 — i.e. 3.9x a plain
    upscale, and equal to the SOURCE's own 720p sharpness (228.2) at 2.25x the pixel count. Flicker
    over ALL 290 pairs: raw restyle 1.619 (diff. corr. 0.116) -> after HF replacement 1.092
    (0.739), reproducing the 8-frame probe, so the fix holds across the clip and not just on the
    sample. Colour check before delivering: mean channel values must match the upscaled source
    within a fraction of a level (measured B 90.8 / G 96.3 / R 113.0 against 90.8 / 96.5 / 113.8,
    luminance 100.0 against 100.4 = no drift); a generative pass can silently shift tint.
    Tooling that did the job, reusable as-is: `restyle_frames.py` (batch img2img through the ComfyUI
    API, per-frame timing from the history timestamps, resume, journal), `chaine_v2.py` (subcommands
    rh / ref1080 / final [--mode greffe|remplacement] / planche), `pipeline_v2.py` (the orchestrator),
    `qa_final.py` (per-stage metrics + flicker over the whole clip), `comparer_final.py` (labelled
    N-column visual sheet). Keep the 5120x2880 intermediate: re-doing only the final graft after the
    delivery cost 2 min instead of the 58.6 min restyle.

## Long Unattended Runs (multi-hour GPU)

A 5-minute render is a multi-hour engagement (~47x real time measured on 8 Go). The session that
launched it can be compressed or closed before it ends, so nothing may live in the conversation:
the plan goes into files and notifications. Full recipe (command, monitor skeleton, thresholds,
event queries): `references/long-run-monitoring.md`.

- **Launch the inference FROM the monitor process**, not the other way round. Only a parent can read
  the child's stdout, and the pipeline prints a real tqdm bar on its inference loop
  (`Doing inference...`): parse `(\d+)%\|.*\|\s*(\d+)/(\d+)` for percent/frames and
  `\[([^,\]]+),\s*([^,\]]+)\]` for the ETA. The output file appears only at the end and the temp dir
  holds just the pre-processed source — never derive progress from either, and never report a
  percentage you did not read.
- **Extrapolating a total duration from a short run is wrong.** Two runs, same machine, same config,
  same 5.48 s output: 1.11 s/frame and 1.89 s/frame. Model load, full-video face detection and
  writing are a fixed cost that does not dilute. Announce the measured ratio (~47 min of GPU per
  minute of video), call it an estimate, and replace it with the real ETA at the first progress
  notification. The ratio also collapses once the run stops fitting in host RAM: measured 127 s per
  iteration and ~13.5 h projected against 4.5 h announced, because the machine was paging to disk —
  check the RAM budget below BEFORE launching, not at hour twelve.
- **Sample the GPU every 30 s, not every 2 s**, via
  `nvidia-smi --query-gpu=memory.used,temperature.gpu --format=csv,noheader,nounits`.
- **For a MULTI-STAGE pipeline, derive the watchdog's progress from the CURRENT stage's output
  directory** (count the produced files; map the stage from the last stage header in the journal),
  never from the pipeline's stdout: a stage that logs every 10 items says nothing for minutes on end,
  while the file count is always truthful. Deduplicate the message against a small state file so the
  watchdog stays quiet when nothing moved, and alert when the active directory has not changed for
  ~20 min. Progress plus a rough ETA needs only the stage's measured seconds-per-item.
- **Document each stage's MEASURED numbers in the knowledge base as it completes**, not only at the
  end: this user asks for it, and it is what a later session resumes from. Append the block to the
  branch document that already exists for that work instead of creating one note per run. SiYuan
  answers `code: 0` even when an inline markdown payload is truncated at the first newline, so send
  the payload from a FILE and confirm by re-exporting — compare the character count and the heading
  list against the pre-append export. Read the API token from `.env`; never echo it, print it or
  paste it into the transcript.
- **Take the Windows event-log baseline BEFORE launching, and decode it as UTF-16** (`wevtutil`
  output makes `grep` answer `Binary file matches`): decode `utf-16-le` in Python, `tr -d '\0'` in
  shell. A monitor counting from zero treats a historical `nvlddmkm` 153 as a fresh one.
- **Write a status JSON at every sample** (phase, percent, frames, ETA, VRAM peak, temp max, event
  counts, start, end, stop reason): that file is what lets a later session resume the follow-up and
  what a watchdog reads.
- **Notify from the monitor's OWN process**, in plain HTTP — it involves the gateway in no way and
  survives the session. A complementary cron watchdog (`no_agent=True`, every 15 min) that stays
  SILENT unless something is wrong is the right shape: empty stdout sends nothing in `no_agent`
  mode, so it never duplicates the routine notifications. Note the existing caution above about
  `deliver='telegram'` on cron for unattended jobs; keep the watchdog silent-first so the gateway
  only delivers on a real alert.
- **Verify the notification CHANNEL, never assume it.** A monitor ran 12 h and delivered nothing:
  its text carried a raw `<` (a tqdm ETA like `01:55<00:00`) while the send used `parse_mode=HTML`,
  so every `sendMessage` answered HTTP 400 — while the launch message, whose text has no `<`, went
  through fine. Twelve hours of silence was read as a dead render. So: no HTML parse mode for
  machine-generated text (escape `<`, `>`, `&`, or send plain text); log the HTTP result of EVERY
  send; validate the RECURRING message, not just the launch one; and have the notifier write a
  heartbeat only after a send SUCCEEDS, with the watchdog alerting when the last success is older
  than ~2x the reminder interval. A watchdog that only checks the monitored process's liveness stays
  silent through a 100 % delivery failure — check the DELIVERY, not just the monitor. A silent
  watchdog's own delivery path is untested until it fires, so exercise it once.
  Concrete fix in this project: `LatentSync\tests\surveiller_latentsync.py` sends WITHOUT
  parse_mode, anchors the progress regex on the outer `Doing inference` label, appends one line
  per send to `envois_<volet>.log` and rewrites `dernier_envoi_<volet>.json` only after a
  successful send (that file is the heartbeat a watchdog should read).
  `LatentSync\tests\tester_moniteur.py` replays a FINISHED run's log through the parser — 23 085
  fragments, no GPU, no new run — and checks that the inner bar is rejected, the percentage is
  monotone, and the send payload carries no parse_mode while keeping the raw `<` of the ETA.
- **Budget the host RAM before launching, not after.** LatentSync decodes the whole video into host
  memory at SOURCE resolution: `frames x width x height x 3` bytes. Measured on 1080p, 8600 frames:
  53 GB theoretical, 49 GB actually held, with 2.6 GB left of 64 GB and 39 GB of page file in use —
  paging, 127 s per iteration instead of ~25-30, and a cadence that degrades as the run goes on. If
  the arithmetic does not fit in free RAM, SEGMENT before launching (multiples of the loop cycle for
  the video, exact samples for the audio) instead of discovering the wall hours in, and free the
  desktop's VRAM too — a working set that spills through WDDM costs the same factor.
  Concrete fix in this project: `pipeline_talkinghead.py --segmenter auto` picks the largest
  multiple of the loop cycle that fits in 60 % of free RAM (at 1080p / cycle 135: 4050 frames =
  23.5 GB when 40 GB are free, 810 frames = 4.7 GB when 8 GB are left) and arms
  `LatentSync\tests\run_latentsync_segments.py`, which cuts source and audio per slice, runs one
  inference per slice, concatenates with `-c copy` and RESUMES already-produced slices. Without
  segmentation the step stops with the budget in plain sight (`49.8 GB needed for 43.6 GB free`).
  The monitor watches such a run through `--commande-json`, so its emergency stop must kill the
  process TREE (`taskkill /PID <pid> /T /F`) — the inference is the wrapper's grandchild and a
  plain `kill()` leaves the GPU busy. `LatentSync\tests\tester_segments.py` verifies slice sizing,
  the step-f wiring and the real slice plan without a GPU.
- **Never restart a monitor mid-run.** Killing it can orphan the inference (which keeps writing its
  output) and a second monitor launches a SECOND inference: two models in 8 Go is a GPU reset. If
  the monitor is misconfigured, let it finish.
- **Verify the monitor's own files exist at the path you expect before walking away**, and search for
  them (`find . -name ...`) if not: a stray character in a launch argument silently creates a
  differently named directory, while the run itself — using its own arguments — proceeds correctly.
  Related: a single log line printed by the monitor is not evidence its files landed where you think.

## Pitfalls

- **Never put `shortest=1` on an overlay whose second input is a non-looped still image.** `[bgface][logo]overlay=...:shortest=1` fed by a plain `-i logo.png` (single-frame input) truncates the ENTIRE output to one frame: FFmpeg exits 0 and writes a ~1 s file that looks like a success. Either loop the still (`-loop 1 -i logo.png`) or drop `shortest=1` from the overlays and let the muxer's `-shortest` trim the export to the audio. Always `ffprobe` the result and compare its duration against the voice track (`ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 out.mp4`) before declaring the render done — exit code 0 is not evidence the video is complete.
- **Jitter Sensitivity:** AI models like LivePortrait amplify source jitter. If the output looks unstable, stabilize the source FIRST — smooth the driving video with FFmpeg (`smooth_driving_video.py`: `hqdn3d`/`gblur`) into `*_smoothed.mp4` and point `run_liveportrait_volet3.py` `DRIVING` to it (keep `sys.argv[1]` override).
- **FPS Drift:** Any mismatch in FPS throughout the chain leads to stuttering and out-of-sync audio. Set `-r 30` on the OUTPUT only (frame duplication) — the input stays at its native 25 fps (an input `-r 30` truncates duration).

## Leçons du volet 7 — LatentSync (commits 93b255d → f403ed3, 23→26/09/2026)

1. **Tranche par contenu, pas par existence** : chaque slice LatentSync se contrôle via le hash de contenu du segment audio, pas via la présence d'un fichier .npy ou .mp3. Un fichier existant mais appartenant à un audio différent doit être recomputé. Voir `processus_vivant()` (commit ad158bc) : avant ce correctif, `processus_vivant()` renvoyait True pour tout motif, bloquant le run pendant 22 h.

2. **`processus_vivant()` ne doit jamais renvoyer True pour tout motif** : le correctif ad158bc a verrouillé la condition de sortie — `processus_vivant()` ne doit bloquer que sur motifs de fond réel, pas sur toute activation. Un tel comportement verrouille la GPU pendant des heures sans avancer.

3. **Le PYTHONPATH du cron masquait numpy et tuait la greffe HF** : commit 76eeaaf. Le cron configurait un PYTHONPATH qui écrasait numpy 1.26.4 (nécessaire par requirements-latentsync.txt), ce qui provoquait l'échec de la greffe HF (high-frequency graft). La solution est d'isoler le PYTHONPATH du cron et de s'assurer que numpy reste dans l'environnement actif du script.

4. **Never assemble on an un-finalized HF graft** : commit e34a482. La greffe HF (high-frequency graft) doit uniquement être assemblée sur une source audio totalement finalisée — jamais sur un fichier source en cours d'écriture ou en attente de validation. L'assemblage prématuré corrompt l'amplitude haute du signal.

- **FPS Drift:** Any mismatch in FPS throughout the chain leads to stuttering and out-of-sync audio. Set `-r 30` on the OUTPUT only (frame duplication) — the input stays at its native 25 fps (an input `-r 30` truncates duration). In `assemble_final_volet3_blur.py`, put `-r 30` in the encode options, NOT before `-i`.
- **VRAM Saturation:** High-resolution inference will fail or run extremely slowly if VRAM is near capacity. Monitor continuously with `nvidia-smi` BEFORE launching — require ~7+ Go free on 8 Go card; `7.7/8.1 Go + 100% GPU` during LivePortrait starves the Hermes gateway and triggers `shutdown_watchdog` exit 75. For unattended jobs use `deliver=local` on cron, never `deliver=telegram` (blocks event loop).
- **Confirming render/export completion:** a render is done when the output file's size stops growing (stable across two checks ~30 s apart) AND `ffprobe` reads a clean, non-truncated duration matching the source. Do NOT trust the process's cumulative CPU (`Get-Process ... CPU`) — it is a lifetime total that stays high after completion (Premiere Pro, `ffmpeg`, SadTalker all idle at high cumulative CPU). Check the file size + the actual writing process (Adobe Media Encoder / `dynamiclinkmanager`), not the CPU.
- **A tool call reporting a timeout does not mean the job stopped.** Long jobs (renders, re-indexing, downloads) are launched in the background with their output redirected to a log file; when the launch call comes back with a timeout, the job has usually RUN TO COMPLETION (full log, exit code 0, no matching process left). Verify before doing anything: log size and last lines, exit code, then count the processes. Relaunching blind doubles the work and can leave two processes writing the SAME output file (index, mp4). A job that truly died is restarted with resume of the segments already written.

See `references/ffmpeg-settings.md` for specific encoding settings and `references/jitter-smoothing.md` for pre-processing unstable driving videos. encoding templates.
