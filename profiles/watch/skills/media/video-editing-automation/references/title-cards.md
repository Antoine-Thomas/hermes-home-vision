# Stylized title cards / intro-outro (PIL + Google Fonts + ffmpeg)

Generate cinematic title cards ("lettrages stylés") as stills, then convert to
clip-matching video ready to paste at the start/end of a clip.

## Fonts (download once)
```bash
mkdir -p "$LOCALAPPDATA/hermes/data/<projet>_titres" && cd "$_"
curl -sL -o Cinzel.ttf     "https://github.com/google/fonts/raw/main/ofl/cinzel/Cinzel%5Bwght%5D.ttf"
curl -sL -o Montserrat.ttf "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf"
```
Variable fonts: `ImageFont.truetype(path, size)` loads the default instance;
`font.set_variation_by_axes([wght])` sets weight (wrap in try/except — it
silently no-ops on fonts without that axis). Cinzel = display serif (title),
Montserrat = clean sans (small caps / credits).

## PIL render (1920×1080)
- **Background** dark + soft center halo: `Image.radial_gradient("L").resize((W,H))`
  inverted, composited through a low-opacity warm/teal color.
- **Gradient text**: render text to an `"L"` mask; fill a vertical gradient only
  over the text's bbox; `Image.paste(grad, (0,0), mask)`.
- **Glow**: `mask.filter(ImageFilter.GaussianBlur(9))` as alpha for a warm tint
  layer, composited BEHIND the sharp text.
- **Letter-spacing (tracking)** for small caps: render char-by-char, advancing x
  by `draw.textlength(c, font=font) + tracking`.
- Thin separator line via `draw.line(...)` for the classic title-card look.

## Convert to clip-matching video (7 s, 1080p60, fade in/out)
```bash
ffmpeg -y -loop 1 -framerate 60 -i titre_intro.png \
  -f lavfi -i anullsrc=r=44100:cl=stereo -t 7 \
  -vf "fade=t=in:st=0:d=1,fade=t=out:st=6:d=1,format=yuv420p" \
  -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k -ar 44100 -shortest -movflags +faststart titre_intro.mp4
```
Match the clip's codec/fps/res exactly (H.264 1080p60 yuv420p + AAC 44.1 kHz
stereo) and keep the silent AAC track so a `-f concat -c copy` with the main
clip works. Deliver both `.png` (quick preview) and `.mp4` (mount-ready).

## Scrolling credits (défilement de bas en haut — movie credits roll)
For an end-credits roll, render ONE TALL image (e.g. 1920×3500) with the content
stacked in **reading order** (title at the TOP of the tall image, "merci/bisous"
at the BOTTOM), plus ~1080px of blank padding above and below the content. Then
pan the crop window from top to bottom with `crop`:

```bash
ffmpeg -y -loop 1 -framerate 60 -i generique_tall.png \
  -f lavfi -i anullsrc=r=44100:cl=stereo -t 40 \
  -vf "crop=1920:1080:0:'(ih-oh)*t/40',fade=t=out:st=37.5:d=2.5,format=yuv420p" \
  -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k -ar 44100 -shortest -movflags +faststart generique_scroll.mp4
```

- `(ih-oh)*t/D` pans crop-y from 0 → (ih-oh). With content in READING order this
  is ALREADY the correct credits roll: the first line enters from the bottom of
  the screen first and scrolls up, the last line exits last. Do NOT reverse the
  content — reading order + top→bottom pan is correct; reversing content +
  bottom→top pan is the mirror-image and easy to get backwards.
- Scroll speed = `(ih-oh)/D` px/s; ~55–70 px/s is comfortable to read. 40 s for
  a ~2500px scroll is a good default.
- Fade out ONLY at the very end (`st=D-2.5:d=2.5`), no fade-in — credits start
  from the blank top pad.
- Content height must EXCEED 1080px (generous line spacing, big title) so it
  actually scrolls rather than just sitting on screen.

## Emoji in credits (monochrome → color)
PIL has no color-emoji support. Render the emoji with the Windows emoji font and
color it like any other glyph (mask → solid/gradient paste):
- Font: `ImageFont.truetype(r"C:\Windows\Fonts\seguiemj.ttf", size)`.
- For a mixed line ("bisous à tous 😚"), render parts side-by-side (Montserrat for
  the words, seguiemj for the emoji), measure each with `textlength`, center the
  whole group, and paste each part's colored mask in turn, advancing x by each
  part's width.

## Palette (user preference — searching-murphy)
The user chose this palette for the Caen Travelling cards/credits over "dark +
gold cinema": bg dark teal `#284543` (radial-halo lighter center), title/accent
gold `#fdc502`, secondary teal `#0c9f93`, soft text light-teal `#cbe8e8`. Keep
the render as pure color constants so a palette variant is a one-line swap.

## Pitfalls
- `ImageDraw.textbbox` returns FLOATS — cast `int()` before using the coords in
  `range()` for the gradient loop, else `TypeError: 'float' object cannot be
  interpreted as an integer`.
- Without a vision model, verify the render programmatically: sample the bg
  corner (expect dark) and count "gold"-ish pixels across the text band (expect
  thousands) before encoding.
- **Teal text is invisible to a brightness check.** `#0c9f93` has luminance ~114,
  so a ">120 brightness" pixel check reports teal lines as EMPTY (false negative).
  Detect teal by channel dominance instead: `g > 120 and g > r + 30 and b > 90`.
  Gold/cream read fine as "bright"; teal does not.
- Offer a palette variant cheaply: the render is just color constants — swap
  the constants and re-run; do NOT re-download fonts or re-encode by hand.
