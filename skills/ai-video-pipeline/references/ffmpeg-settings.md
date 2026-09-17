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
- **Force Input/Output FPS:** Ensure both input and output flag `-r 30` (or target FPS).
- **Constant Bitrate:** If VBR causes artifacts in complex areas, use CBR/CQP with higher bitrates.
