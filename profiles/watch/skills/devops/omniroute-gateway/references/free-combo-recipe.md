# Free-combo reorder recipe (OmniRoute)

## One-shot reorder script
Save as `reorder_eco_free.py` in the OmniRoute data dir, run with `--apply` after verifying dry-run.

```python
#!/usr/bin/env python3
"""Reorder 'eco' combo to 100% free models that actually return content.

Run: python reorder_eco_free.py [--apply]
"""
import json, subprocess, os, sys

BASE = "http://127.0.0.1:20128"
COMBOS = BASE + "/api/combos"
HERE = os.path.dirname(os.path.abspath(__file__))
COOKIES = os.path.join(HERE, "or_cookies.txt")
APPLY = "--apply" in sys.argv

def curl(args):
    return subprocess.run(["curl", "-s", "-b", COOKIES] + args,
                          capture_output=True, text=True).stdout

def get_combos():
    return json.loads(curl([COMBOS]))["combos"]

def slug(m): return m.replace("@cf/","").replace("/","-").replace("@","")

# Verified 2026-08-27: only nemotron-3-ultra-free reliably produces text.
# hy3-free = reasoning model (empty content -> 502). auto/gemini, nemotron-3.5-lightning
# often in circuit-breaker. mimo/big-pickle = 429. kimi-k3 = 401.
FREE_ORDER = [
    "oc/nemotron-3-ultra-free",
    "auto/gemini",
    "oc/nemotron-3.5-lightning-free",
    "oc/mimo-v2.5-free",
    "oc/big-pickle",
    "oc/hy3-free",          # reasoning model, last resort
]

def build():
    return [{"id": f"eco-model-{i:02d}-{slug(m)}",
             "kind": "model", "model": m, "providerId": "opencode" if m.startswith("oc/") else ("auto" if m.startswith("auto/") else "cloudflare-ai"),
             "weight": 0} for i, m in enumerate(FREE_ORDER, 1)]

def main():
    combos = get_combos()
    eco = next(c for c in combos if c["name"] == "eco")
    bak = os.path.join(HERE, f"combos_bak_{os.path.basename(__file__).split('.')[0]}_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    json.dump({"combos": combos}, open(bak, "w", encoding="utf-8"), indent=2)
    print("Backup:", bak)

    body = {k: v for k, v in eco.items() if k not in ("createdAt","updatedAt","version","computed_context_length")}
    body["strategy"] = "priority"
    body["models"] = build()

    print("New eco:", len(body["models"]), "models")
    for i, m in enumerate(body["models"], 1):
        print(f"  {i:2d}. {m['model']}")

    if not APPLY:
        print("(dry-run) add --apply to write"); return

    tmp = os.path.join(HERE, "_eco.json")
    json.dump(body, open(tmp, "w"))
    out = curl(["-X", "PUT", f"{COMBOS}/{eco['id']}", "-H", "Content-Type: application/json",
                "--data-binary", "@" + tmp, "-w", "\nHTTP=%{http_code}"])
    os.remove(tmp)
    print("PUT ->", out.strip().splitlines()[-1])

if __name__ == "__main__": main()
```

## Model probe table (single-call verification)

Run once per candidate with `max_tokens=50`. Only trust non-empty `content`.

| Model | HTTP | `content` non-empty? | Notes |
|-------|------|---------------------|-------|
| `oc/nemotron-3-ultra-free` | 200 | ✅ | **Primary free workhorse** |
| `auto/gemini` | timeout/000 | ❌ | Circuit-breaker |
| `oc/nemotron-3.5-lightning-free` | timeout/000 | ❌ | Circuit-breaker |
| `oc/mimo-v2.5-free` | 429 | ❌ | Rate limited |
| `oc/big-pickle` | 429 | ❌ | Rate limited |
| `oc/hy3-free` | 200/502 | ❌ | **Reasoning model** — all tokens to `reasoning_content`, empty `content` → OmniRoute rejects 502 |
| `oc/kimi-k3` | 401 | ❌ | Not free without key |
| `oc/deepseek-v4-flash-free` | 400 | ❌ | Broken |
| `cloudflare-ai/@cf/meta/llama-3.3-70b-instruct` | 503 | ❌ | Circuit breaker |

**Probe command (copy-paste):**
```bash
curl -s -X POST http://127.0.0.1:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"oc/nemotron-3-ultra-free","messages":[{"role":"user","content":"dis bonjour"}],"max_tokens":50,"stream":false}' \
  --max-time 30 | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('model'), repr(d['choices'][0]['message'].get('content',''))[:80])"
```

## Verify combo after edit
```bash
curl -s -X POST http://127.0.0.1:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"eco","messages":[{"role":"user","content":"dis bonjour"}],"max_tokens":50,"stream":false}' \
  --max-time 120 | python -c "import sys,json; d=json.load(sys.stdin); print('model:', d.get('model'), '| content:', repr(d['choices'][0]['message'].get('content',''))[:80])"
```
Expected: free model ID + non-empty content. If `fallback_providers: []`, NO paid model ever returned.