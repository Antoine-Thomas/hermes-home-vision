# Creative Divergence (use only when user requests experimental/creative/unique output)

> Source: `creative/p5js/SKILL.md` — split on 2026-09-10 to meet max 200 lines rule.

If the user asks for creative, experimental, surprising, or unconventional output, select the strategy that best fits and reason through its steps BEFORE generating code.

- **Conceptual Blending** — when the user names two things to combine or wants hybrid aesthetics
- **SCAMPER** — when the user wants a twist on a known generative art pattern
- **Distance Association** — when the user gives a single concept and wants exploration ("make something about time")

### Conceptual Blending
1. Name two distinct visual systems (e.g., particle physics + handwriting)
2. Map correspondences (particles = ink drops, forces = pen pressure, fields = letterforms)
3. Blend selectively — keep mappings that produce interesting emergent visuals
4. Code the blend as a unified system, not two systems side-by-side

### SCAMPER Transformation
Take a known generative pattern (flow field, particle system, L-system, cellular automata) and systematically transform it:
- **Substitute**: replace circles with text characters, lines with gradients
- **Combine**: merge two patterns (flow field + voronoi)
- **Adapt**: apply a 2D pattern to a 3D projection
- **Modify**: exaggerate scale, warp the coordinate space
- **Purpose**: use a physics sim for typography, a sorting algorithm for color
- **Eliminate**: remove the grid, remove color, remove symmetry
- **Reverse**: run the simulation backward, invert the parameter space

### Distance Association
1. Anchor on the user's concept (e.g., "loneliness")
2. Generate associations at three distances:
   - Close (obvious): empty room, single figure, silence
   - Medium (interesting): one fish in a school swimming the wrong way, a phone with no notifications, the gap between subway cars
   - Far (abstract): prime numbers, asymptotic curves, the color of 3am
3. Develop the medium-distance associations — they're specific enough to visualize but unexpected enough to be interesting
