# 11. Audio Analysis & Visualization: songsee

> Source: `creative/songwriting-and-ai-music/SKILL.md` — split on 2026-09-10 to meet max 200 lines rule.

Generate spectrograms and multi-panel audio feature visualizations from audio files — useful for comparing outputs, debugging synthesis, or documenting audio pipelines.

**Install:** `go install github.com/steipete/songsee/cmd/songsee@latest` (requires Go).

**Quick start:**
```bash
# Basic spectrogram
songsee track.mp3

# Multi-panel visualization grid (9 types)
songsee track.mp3 --viz spectrogram,mel,chroma,hpss,selfsim,loudness,tempogram,mfcc,flux

# Time slice
songsee track.mp3 --start 12.5 --duration 8 -o slice.jpg

# From stdin
cat track.mp3 | songsee - --format png -o out.png
```

**Visualization types:** `spectrogram`, `mel`, `chroma`, `hpss` (harmonic/percussive separation), `selfsim` (self-similarity matrix), `loudness`, `tempogram`, `mfcc`, `flux` (onset detection). Multiple `--viz` types render as a grid.

**Common flags:** `--style` (classic/magma/inferno/viridis/gray), `--width`/`--height`, `--window`/`--hop`, `--min-freq`/`--max-freq`, `--start`/`--duration`.

**Notes:** WAV and MP3 decoded natively; other formats need ffmpeg. Output images can be inspected with vision tools for automated analysis.
