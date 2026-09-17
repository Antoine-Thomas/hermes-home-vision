# Driving Video Smoothing

If the driving video for LivePortrait (or similar) is jittery or has noise, the animation will inherit that instability ("jitter").

## FFmpeg Pre-processing

Apply a temporal and spatial denoiser before inference:

```bash
# Denoising and light smoothing
ffmpeg -i input.mp4 -vf hqdn3d=1.5:1.5:6:6 -c:v libx264 -preset slow -crf 18 -c:a copy output.mp4
```

- `hqdn3d`: Reduces high-frequency noise and temporal jitter.
- Adjust `1.5:1.5` (spatial) and `6:6` (temporal) based on source noise levels.
