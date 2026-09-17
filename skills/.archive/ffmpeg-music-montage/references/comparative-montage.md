# Comparative Montage Pattern — Reality vs Stylised

## Overview
When the user wants a **direct comparison** of two versions of the same footage (original vs AI-stylised, different color grades, different cameras) on identical timecodes, use this pattern.

## Key Differences from Energy-Driven Montage
| Energy-Driven (`ffmpeg-music-montage`) | Comparative (`montage_comparatif.py`) |
|----------------------------------------|----------------------------------------|
| 3+ sources (A/B/C), selected by energy | Exactly 2 sources: Reality + SD |
| Transition by energy level | Transition by CONTENT TYPE |
| Single output covering full track | Multiple focused outputs per category |
| Auto-segmented by librosa | Segments pre-defined in config JSON |

## Content-Based Transition Rules
| Content Type | Transition | Duration | Rationale |
|--------------|------------|----------|-----------|
| Faces, portraits, close-ups | `fade` | 0.5s | Smooth dissolve reveals subtle texture differences |
| Streets, wide movement, action | `slideleft`/`slideright` (alternating) | 0.4s | Directional wipe matches motion direction |
| Churches, architecture, static wide | `slide` OR split-screen | 0.4s | Split-screen = simultaneous visibility |

## Multi-Clip Strategy
Instead of one long comparative clip, produce **separate clips per category**:
1. Parse `extracts.json` (from XML export) → classify each extract by name/content
2. Create `cuts_<category>.json` for each category (visages, eglises, rues, etc.)
3. Each config contains alternating Reality/SD pairs for that category only
4. Run same script with different `--cuts` and `--out`

## Config Files (never modify originals)
- `cuts_visages.json` — calm segments (energy < 0.3), faces/portraits
- `cuts_eglises.json` — mid-energy architectural segments
- `cuts_rues.json` — high-energy street/movement segments

Each config format:
```json
{
  "audio_file": "...",
  "duration": 195.2,
  "tempo_bpm": 152,
  "segments": [
    {"start": 0.0, "end": 4.2, "duration": 4.2, "in": 12.5, "out": 16.7, "source": "reality", "transition": "fade"},
    {"start": 4.2, "end": 8.4, "duration": 4.2, "in": 12.5, "out": 16.7, "source": "sd", "transition": "fade"},
    ...
  ]
}
```

Note: `in`/`out` are source timecodes (identical for reality/sd pair), `start`/`end` are timeline positions.

## Reusable Script
See `scripts/montage_comparatif.py` — single script handles all categories via `--cuts` argument.

## Verification Checklist
- [ ] `ffprobe` output: 1920×1080, 24fps, H.264 CRF 18, AAC 192k
- [ ] Duration matches expected (sum of segment durations)
- [ ] Strict alternation: no two consecutive same-source segments
- [ ] Correct transitions per category
- [ ] No circular transitions (circle, circlecrop, zoomin)
- [ ] Original clips untouched