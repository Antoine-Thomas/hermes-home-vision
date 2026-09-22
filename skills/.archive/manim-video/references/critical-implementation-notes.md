# Critical Implementation Notes

> Source: `creative/manim-video/SKILL.md` — split on 2026-09-10 to meet max 200 lines rule.

### Raw Strings for LaTeX
```python
# WRONG: MathTex("\frac{1}{2}")
# RIGHT:
MathTex(r"\frac{1}{2}")
```

### buff >= 0.5 for Edge Text
```python
label.to_edge(DOWN, buff=0.5)  # never < 0.5
```

### FadeOut Before Replacing Text
```python
self.play(ReplacementTransform(note1, note2))  # not Write(note2) on top
```

### Never Animate Non-Added Mobjects
```python
self.play(Create(circle))  # must add first
self.play(circle.animate.set_color(RED))  # then animate
```
