# Descript API — real endpoints (beta / paid)

Verified by fetching the live API spec (`https://docs.descriptapi.com`).

## Base URL & auth
- Base: **`https://descriptapi.com/v1`** (NOT `api.descript.com` — that 404s).
- Auth: `Authorization: Bearer <token>`.
- Status: HTTP **401** with no/valid-but-unauthorized token (closed beta / paid tier).
  Endpoint reachable; access gated behind a paid plan.

## FALSE FRIEND — do NOT install
`pip install descript` installs an unrelated PyPI package that manipulates
`descript.ion` sidecar files. It has **nothing** to do with Descript the app.
There is **no official Python SDK**. The official client is Node:
`npm i @descript/platform-cli`. For Hermes, write a small REST client.

## Verified endpoints
- `POST /jobs/import/project_media` — import/upload a media file (signed upload).
- `POST /jobs/agent` — run an agent action (e.g. remove silence, cut filler words).
- `POST /jobs/publish` — export; resolutions 480p → 4K.
- `POST /export/transcript` — export transcript, including **SRT** subtitles.
- `GET /jobs/{job_id}` — poll job status.

## Dry-run / secret pattern
```python
import os, requests
token = os.environ.get("DESCRIPT_API_TOKEN")
if not token:
    print("[dry-run] no DESCRIPT_API_TOKEN set"); raise SystemExit(0)
r = requests.get("https://descriptapi.com/v1/status",
                 headers={"Authorization": f"Bearer {token}"})
print(r.status_code, r.text[:200])
```
Key env var: **`DESCRIPT_API_TOKEN`** (never hardcode).
