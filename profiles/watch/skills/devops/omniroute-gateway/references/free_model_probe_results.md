# Free-model probe results (OmniRoute)

Dated live probe verdicts — re-run `scripts/probe_free.py` when upstreams change.
Each candidate hit with a single non-stream completion, no API key configured.

## Verdict (2026-08-27)

| Model | HTTP | Verdict |
|---|---|---|
| oc/hy3-free | 200 | OK, keyless — reliable free head |
| oc/nemotron-3.5-lightning-free | 200 | OK, keyless — replaced phantom north-mini-code-free |
| oc/nemotron-3-ultra-free | timeout (000) | keyless per README; transient |
| oc/mimo-v2.5-free | 429 | keyless per README; rate-limited when hit |
| oc/big-pickle | 429 | keyless per README; rate-limited when hit |
| opencode/big-pickle | 429 | same as above (prefer oc/ over opencode/) |
| auto/gemini | timeout (000) | likely needs Gemini key; unreliable |
| oc/kimi-k3 | 401 | **NOT free** — "Missing API key" (OpenCode key required) |
| oc/deepseek-v4-flash-free | 400 | broken upstream |
| cloudflare-ai/@cf/meta/llama-3.3-70b-instruct | 503 | circuit breaker (CF key required?) |

## Rule of thumb
- Put only models that returned **200 with no key** at the head: `oc/hy3-free`,
  `oc/nemotron-3.5-lightning-free`.
- `nemotron-3-ultra-free` / `mimo-v2.5-free` / `big-pickle` are keyless but
  rate-limited — keep them in the free block, mid/late.
- `kimi-k3`, `deepseek-v4-flash-free`, `cloudflare-*` are effectively NOT free
  without keys/working upstreams — never place them first; they only matter if
  a key gets added later.
- The `eco` combo verified routing to `nemotron-3.5-lightning-free` 3/3 times
  (free, never paid) after the reorder — confirms free-first fallback works.

## Schema notes
- No ELO / scores table exists: `/api/model-intelligence` → 404, no storage.sqlite.
  Order by live probe, not by a stale scores file.
- Compression is GLOBAL (`/api/settings/compression`), no per-model `compress` flag.
- Combo PUT body must drop `createdAt/updatedAt/version/computed_context_length`.
