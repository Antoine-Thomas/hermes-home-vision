# Creative Direction

> Source: `creative/p5js/SKILL.md` — split on 2026-09-10 to meet max 200 lines rule.

### Aesthetic Dimensions

| Dimension | Options | Reference |
|-----------|---------|-----------|
| **Color system** | HSB/HSL, RGB, named palettes, procedural harmony, gradient interpolation | `references/color-systems.md` |
| **Noise vocabulary** | Perlin noise, simplex, fractal (octaved), domain warping, curl noise | `references/visual-effects.md` § Noise |
| **Particle systems** | Physics-based, flocking, trail-drawing, attractor-driven, flow-field following | `references/visual-effects.md` § Particles |
| **Shape language** | Geometric primitives, custom vertices, bezier curves, SVG paths | `references/shapes-and-geometry.md` |
| **Motion style** | Eased, spring-based, noise-driven, physics sim, lerped, stepped | `references/animation.md` |
| **Typography** | System fonts, loaded OTF, `textToPoints()` particle text, kinetic | `references/typography.md` |
| **Shader effects** | GLSL fragment/vertex, filter shaders, post-processing, feedback loops | `references/webgl-and-3d.md` § Shaders |
| **Composition** | Grid, radial, golden ratio, rule of thirds, organic scatter, tiled | `references/core-api.md` § Composition |
| **Interaction model** | Mouse follow, click spawn, drag, keyboard state, scroll-driven, mic input | `references/interaction.md` |
| **Blend modes** | `BLEND`, `ADD`, `MULTIPLY`, `SCREEN`, `DIFFERENCE`, `EXCLUSION`, `OVERLAY` | `references/color-systems.md` § Blend Modes |
| **Layering** | `createGraphics()` offscreen buffers, alpha compositing, masking | `references/core-api.md` § Offscreen Buffers |
| **Texture** | Perlin surface, stippling, hatching, halftone, pixel sorting | `references/visual-effects.md` § Texture Generation |

### Per-Project Variation Rules

Never use default configurations. For every project:
- **Custom color palette** — never raw `fill(255, 0, 0)`. Always a designed palette with 3-7 colors
- **Custom stroke weight vocabulary** — thin accents (0.5), medium structure (1-2), bold emphasis (3-5)
- **Background treatment** — never plain `background(0)` or `background(255)`. Always textured, gradient, or layered
- **Motion variety** — different speeds for different elements. Primary at 1x, secondary at 0.3x, ambient at 0.1x
- **At least one invented element** — a custom particle behavior, a novel noise application, a unique interaction response

### Project-Specific Invention

For every project, invent at least one of:
- A custom color palette matching the mood (not a preset)
- A novel noise field combination (e.g., curl noise + domain warp + feedback)
- A unique particle behavior (custom forces, custom trails, custom spawning)
- An interaction mechanic the user didn't request but that elevates the piece
- A compositional technique that creates visual hierarchy

### Parameter Design Philosophy

Parameters should emerge from the algorithm, not from a generic menu. Ask: "What properties of *this* system should be tunable?"

**Good parameters** expose the algorithm's character:
- **Quantities** — how many particles, branches, cells (controls density)
- **Scales** — noise frequency, element size, spacing (controls texture)
- **Rates** — speed, growth rate, decay (controls energy)
- **Thresholds** — when does behavior change? (controls drama)
- **Ratios** — proportions, balance between forces (controls harmony)

**Bad parameters** are generic controls unrelated to the algorithm:
- "color1", "color2", "size" — meaningless without context
- Toggle switches for unrelated effects
- Parameters that only change cosmetics, not behavior

Every parameter should change how the algorithm *thinks*, not just how it *looks*. A "turbulence" parameter that changes noise octaves is good. A "particle size" slider that only changes `ellipse()` radius is shallow.
