<!-- Source: wordpress-theme/SKILL.md · section 'Image Optimization' -->

## Image Optimization

When source images are larger than their display size, resize them to match using ImageMagick or cwebp:

```bash
# Resize to display dimensions with ImageMagick
magick pic01.webp -resize 590x197 pic01.webp

# Same with cwebp (lighter output)
cwebp original.webp -resize 590 197 -o pic01.webp -q 85

# After resizing originals, regenerate WordPress thumbnails
wp media regenerate --only-missing
```

Always back up originals before resizing: `cp pic01.webp originaux/pic01.webp`.
