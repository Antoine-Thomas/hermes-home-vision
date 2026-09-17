# Queue & System Management

> Source: `creative/comfyui/SKILL.md` — split on 2026-09-10 to meet max 200 lines rule.

```bash
# Local
curl -s http://127.0.0.1:8188/queue | python -m json.tool
curl -X POST http://127.0.0.1:8188/queue -d '{"clear": true}'    # cancel pending
curl -X POST http://127.0.0.1:8188/interrupt                      # cancel running
curl -X POST http://127.0.0.1:8188/free \
  -H "Content-Type: application/json" \
  -d '{"unload_models": true, "free_memory": true}'

# Cloud — same paths under /api/, plus:
python scripts/fetch_logs.py --tail-queue --host https://cloud.comfy.org
```
