# JSON2Video — real SDK shape (v2.0.0, PyPI `json2video`)

Verified by reading the installed package (`site-packages/json2video/`), not blogs.

## Install
```
python -m venv .venv
.venv/Scripts/python.exe -m ensurepip   # venv may ship without pip
.venv/Scripts/python.exe -m pip install json2video requests
```
v2.0.0 is the official package — do NOT use the npm `json2video` unless you mean JS.

## API shape (definitive)
- Classes: `Movie`, `Scene` (there is NO `Client`).
- Auth: header **`x-api-key`** (NOT `Authorization: Bearer`).
- `Movie.set(...)` enforces a property allowlist. Known keys:
  `width, height, fps, scenes, audio, no_credits, quality, render_id, webhook, ...`
  **`soundtrack` is NOT a key** — add background audio as a scene `audio` element.
- `render()` is declared **async** → call via `asyncio.run(movie.render())`.
- Render endpoint: `POST /v1/movies`. Poll `GET /v1/movies/{id}` for status.
- Elements support text, image, audio, and **subtitles/captions** natively.

## Limits (verified docs)
- Upload cap: **500 MB** per media file. A 7 GB 4K60 source is rejected → use ffmpeg.
- Free tier: **adds a watermark**; 4K render counts **4× the credit cost** vs 1080p.

## Dry-run pattern
```python
import os, asyncio
from json2video import Movie
api = os.environ.get("JSON2VIDEO_API_KEY")
movie = Movie(width=1920, height=1080, fps=60, no_credits=True)
movie.add_scene(...)
if not api:
    print("[dry-run] payload would be:", movie.to_json()); raise SystemExit(0)
movie.api_key = api
asyncio.run(movie.render())
```
