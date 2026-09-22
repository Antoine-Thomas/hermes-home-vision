# Creative Direction

> Source: `creative/manim-video/SKILL.md` — split on 2026-09-10 to meet max 200 lines rule.

### Color Palettes

| Palette | Background | Primary | Secondary | Accent | Use case |
|---------|-----------|---------|-----------|--------|----------|
| **Classic 3B1B** | `#1C1C1C` | `#58C4DD` (BLUE) | `#83C167` (GREEN) | `#FFFF00` (YELLOW) | General math/CS |
| **Warm academic** | `#2D2B55` | `#FF6B6B` | `#FFD93D` | `#6BCB77` | Approachable |
| **Neon tech** | `#0A0A0A` | `#00F5FF` | `#FF00FF` | `#39FF14` | Systems, architecture |
| **Monochrome** | `#1A1A2E` | `#EAEAEA` | `#888888` | `#FFFFFF` | Minimalist |

### Animation Speed

| Context | run_time | self.wait() after |
|---------|----------|-------------------|
| Title/intro appear | 1.5s | 1.0s |
| Key equation reveal | 2.0s | 2.0s |
| Transform/morph | 1.5s | 1.5s |
| Supporting label | 0.8s | 0.5s |
| FadeOut cleanup | 0.5s | 0.3s |
| "Aha moment" reveal | 2.5s | 3.0s |

### Typography Scale

| Role | Font size | Usage |
|------|-----------|-------|
| Title | 48 | Scene titles, opening text |
| Heading | 36 | Section headers within a scene |
| Body | 30 | Explanatory text |
| Label | 24 | Annotations, axis labels |
| Caption | 20 | Subtitles, fine print |

### Fonts

**Use monospace fonts for all text.** Manim's Pango renderer produces broken kerning with proportional fonts at all sizes. See `references/visual-design.md` for full recommendations.

```python
MONO = "Menlo"  # define once at top of file

Text("Fourier Series", font_size=48, font=MONO, weight=BOLD)  # titles
Text("n=1: sin(x)", font_size=20, font=MONO)                  # labels
MathTex(r"\nabla L")                                            # math (uses LaTeX)
```

Minimum `font_size=18` for readability.

### Per-Scene Variation

Never use identical config for all scenes. For each scene:
- **Different dominant color** from the palette
- **Different layout** — don't always center everything
- **Different animation entry** — vary between Write, FadeIn, GrowFromCenter, Create
- **Different visual weight** — some scenes dense, others sparse
