# Free-model probe results (OmniRoute)

## Verdict (2026-09-12, probe `max_tokens=200`)

Combo `eco` = 10 modeles gratuits (`auto/best-free` en tete), verifie 200 +
content non vide. Latences mesurees avec `max_tokens=200` (petit budget =
faux "morts" sur les modeles reasoning).

| Model | HTTP | Verdict |
|---|---|---|
| oc/big-pickle | 200 (32ms-1.1s) | OK gratuit, bon candidat tete |
| oc/mimo-v2.5-free | 200 (47ms-5.7s) | OK gratuit (avait timeoute avec max_tokens=5) |
| oc/nemotron-3-ultra-free | 200 (63ms-4.2s) | OK gratuit |
| opencode/nemotron-3-ultra-free | 200 (64ms-18ms) | OK gratuit |
| auto/best-free | 200 (146-230ms) | OK gratuit, tete de combo |
| auto/zai | 200 (1.7-19s) | OK gratuit |
| auto/gemini | 200 (2.9-5.5s) | OK gratuit |
| oc/muse-spark-1.2-contributor-free | 200 (5.2-9s) | OK gratuit, parfois hang |
| oc/nemotron-3.5-lightning-free | timeout ponctuel | survivant connu, garder en fin de liste |
| oc/hy3-free | 401 "not supported" | **mort** |
| oc/laguna-s-2.1-free | 401 "not supported" | **mort** |
| oc/kimi-k3 | 402 | pas gratuit sans cle OpenCode |
| pollinations/llama-scout, llama-maverick | 401 | cle requise |
| zc/glm-5.3 | 502 | `spawn zcode ENOENT` (upstream local absent) |
| pol/openai | 401 | cle requise |
| cloudflare-ai/@cf/..., cfp/* | 502 | Account ID / navigateur Playwright absent |

## Verdict (2026-08-27) — re-run `scripts/probe_free.py` when upstreams change.
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
