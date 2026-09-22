# FFmpeg Encoding Best Practices

For AI-generated videos where visual stability is critical:

## Recommended Settings (1080p)

```bash
# High-quality CPU encoding
ffmpeg -i input.mp4 -c:v libx264 -crf 18 -preset slow -r 30 -b:v 15M output.mp4

# NVENC High-quality encoding (for NVIDIA GPUs)
ffmpeg -i input.mp4 -c:v h264_nvenc -preset p7 -cq 20 -b:v 0 -r 30 output.mp4
```

## Troubleshooting Stuttering
- **Force the FPS on the OUTPUT only:** `-r 30` (or the target FPS) as an OUTPUT option (frame duplication).
  An INPUT `-r 30` re-timestamps the frames and TRUNCATES the duration (measured: 376 s -> 313 s on a
  25 fps source).
- **Frames -> video round trip:** give the frame rate to the demuxer (`-framerate <src fps> -i frame_%05d.png`),
  not `-r`, so the assembly matches the clip the frames came from; then mux the original audio with
  `-c:v copy -c:a aac -b:a 192k -shortest` and verify with ffprobe.
- **Constant Bitrate:** If VBR causes artifacts in complex areas, use CBR/CQP with higher bitrates.
