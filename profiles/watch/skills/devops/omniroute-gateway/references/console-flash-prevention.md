# OmniRoute Gateway Management

OmniRoute is a local LLM routing proxy (npm `omniroute`) running at
`http://127.0.0.1:20128` (dashboard + `/api` on :20128, inference on `/v1`).

## Installation & Background Launch
Run OmniRoute as a silent daemon without flashing windows on Windows:
```bash
omniroute serve --daemon --no-open
```
If creating a scheduled task, use a VBScript wrapper (see `windows-performance-tuning` skill `references/console-flash-prevention.md`).

## API & Model Discovery
- List available models: `GET /v1/models` (with Bearer token).
- List combos: `GET /api/combos`
- Read model verdicts from `scripts/discover_free_models.py`.
