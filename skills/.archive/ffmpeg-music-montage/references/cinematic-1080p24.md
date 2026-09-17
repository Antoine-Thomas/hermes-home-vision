# 1080p24 Cinematic Montage Pattern

## Overview
When the user wants a **cinematic look** version of an existing montage: 1080p resolution, 24fps (film look), with specific transition rules and intentional source alternation.

## Key Changes from 4K60 Original
| Parameter | 4K60 Original | 1080p24 Cinematic |
|-----------|--------------|-------------------|
| Resolution | 3840×2160 | 1920×1080 |
| FPS | 60 | 24 (film look) |
| Encoding | CRF 18 | CRF 18 (same quality) |
| Transitions | circle, circlecrop, zoomin, fade, slide | **fade + slide ONLY** |

## Transition Rules (Anti-Circular)
**Forbidden**: `circle`, `circlecrop`, `zoomin`
**Allowed**: `fade`, `slideleft`, `slideright`

### Transition Selection by Energy
| Energy Range | Source | Transition | Duration |
|--------------|--------|------------|----------|
| < 0.3 (calm) | B (slow/close) | `fade` | 0.3s |
| 0.3–0.7 (mid) | C (stylised/wide) | `slideleft`/`slideright` (alternating) | 0.4s |
| > 0.7 (hot) | A (action) | `slideleft`/`slideright` (alternating) | 0.4s |

Note: High energy gets slides instead of circle/zoomin — keeps dynamic feel without circular artifacts.

## Intentional Source Alternation
Instead of purely energy-driven, map sources to **creative intent**:
- **Source A (normal/action)** → dynamic passages, movement, energy
- **Source C (stylised 4K)** → calm passages, wide shots, atmospheric
- **Source B (slow faces)** → close-ups, portraits, intimate moments

This is implemented in `montage_1080p24.py` with explicit energy thresholds.

## Split-Screen for Streets
When source footage contains street scenes (identified by section tags "rue" in cuts.json):
- Keep or add split-screen left/right
- Use `hstack` filter or xfade with custom geometry
- Preserves the comparative feel for architectural content

## Config Pattern
- Copy `cuts.json` → `cuts_manuel.json` (never modify original)
- Edit `cuts_manuel.json` to adjust transitions/sources per segment
- Script reads `--cuts` argument (reusable)

## Script: `montage_1080p24.py`
Key features:
- `--plan` mode: dry-run showing all segments, transitions, source distribution
- `--out` mode: full encode with progress
- Auto source selection by energy (overridable in config)
- Windows path handling: `C:/Users/...` for native ffmpeg
- Background execution for long encodes (>600s)

## Verification
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,codec_name -of csv=p=0 output.mp4
# Should show: h264,1920,1080,24/1
ffprobe -v error -show_entries format=duration -of csv=p=0 output.mp4
# Should match audio duration (~195.2s)
```

## Pitfalls
- Windows paths: use `C:/Users/...` not `/c/Users/...` in Python subprocess
- Foreground timeout: use background process with notify for encodes >10min
- Pad segment logic: must match original xfade compensation exactly
- Energy rank normalisation: copy from `references/energy-and-duration.md`