# References

> Source: `creative/p5js/SKILL.md` — split on 2026-09-10 to meet max 200 lines rule.

| File | Contents |
|------|----------|
| `references/core-api.md` | Canvas setup, coordinate system, draw loop, `push()`/`pop()`, offscreen buffers, composition patterns, `pixelDensity()`, responsive design |
| `references/shapes-and-geometry.md` | 2D primitives, `beginShape()`/`endShape()`, Bezier/Catmull-Rom curves, `vertex()` systems, custom shapes, `p5.Vector`, signed distance fields, SVG path conversion |
| `references/visual-effects.md` | Noise (Perlin, fractal, domain warp, curl), flow fields, particle systems (physics, flocking, trails), pixel manipulation, texture generation (stipple, hatch, halftone), feedback loops, reaction-diffusion |
| `references/animation.md` | Frame-based animation, easing functions, `lerp()`/`map()`, spring physics, state machines, timeline sequencing, `millis()`-based timing, transition patterns |
| `references/typography.md` | `text()`, `loadFont()`, `textToPoints()`, kinetic typography, text masks, font metrics, responsive text sizing |
| `references/color-systems.md` | `colorMode()`, HSB/HSL/RGB, `lerpColor()`, `paletteLerp()`, procedural palettes, color harmony, `blendMode()`, gradient rendering, curated palette library |
| `references/webgl-and-3d.md` | WEBGL renderer, 3D primitives, camera, lighting, materials, custom geometry, GLSL shaders (`createShader()`, `createFilterShader()`), framebuffers, post-processing |
| `references/interaction.md` | Mouse events, keyboard state, touch input, DOM elements, `createSlider()`/`createButton()`, audio input (p5.sound FFT/amplitude), scroll-driven animation, responsive events |
| `references/export-pipeline.md` | `saveCanvas()`, `saveGif()`, `saveFrames()`, deterministic headless capture, ffmpeg frame-to-video, CCapture.js, SVG export, per-clip architecture, platform export (fxhash), video gotchas |
| `references/troubleshooting.md` | Performance profiling, per-pixel budgets, common mistakes, browser compatibility, WebGL debugging, font loading issues, pixel density traps, memory leaks, CORS |
| `templates/viewer.html` | Interactive viewer template: seed navigation (prev/next/random/jump), parameter sliders, download PNG, responsive canvas. Start from this for explorable generative art |

---
