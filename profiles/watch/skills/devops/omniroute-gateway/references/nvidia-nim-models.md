# NVIDIA NIM — Investigation Results (2026-09-02)

## Context

User was told "88 NVIDIA models available" but reality is different.
OmniRoute `dva` provider ≠ NVIDIA NIM (it's a Devin Agentic sandbox bridge).

## Real NIM API

- **Endpoint**: `https://integrate.api.nvidia.com/v1`
- **Auth**: Bearer token from `NVIDIA_API_KEY_GEMMA4` (also works for chat models)
- **Total models listed**: 82
- **NVIDIA/Nemotron models listed**: 34

## Models that WORK on this account

| Model | Size | Notes |
|---|---|---|
| `nvidia/nemotron-3.5-lightning-30b-a3b` | 30B MoE | Fast, chat ✅ |
| `nvidia/nemotron-3-super-120b-a12b` | 120B MoE | Chat/reasoning ✅ |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | 30B MoE | Reasoning ✅ |

## Models that DON'T work (404 — not deployed on this account)

- `nvidia/llama-3.1-nemotron-70b-instruct`
- `nvidia/llama-3.1-nemotron-ultra-253b-v1`
- `nvidia/llama-3.1-nemotron-51b-instruct`
- `nvidia/llama-3.1-nemotron-nano-3-30b-a3b`
- `nvidia/llama-3.1-nemotron-nano-omni-30b-a3b-reasoning`

## Slow models (>180s timeout)

- `google/gemma-4-31b-it` — very slow via NIM

## OmniRoute `dva` provider status

- Returns 500: `DEVIN_AGENTIC_HOME must be an absolute path inside the bridge sandbox`
- NOT a bug — `dva` is a completely different thing from NVIDIA NIM

## `auto/best-chat` alias behavior

- Dynamic auto-routing alias, iterates through models
- Test result (2026-09-02): resolved to `oc/mimo-v2.5-free`
- DeepSeek only appears in `fallback_providers` (paid fallback), never normal routing

## What to tell user when asked about "NVIDIA models"

"Via OmniRoute: only 2 Nemotron models via Opencode (free). Via NVIDIA NIM API directly: 3 models work. The 88 number was incorrect."

## Wiring NIM into OmniRoute — the proxy pattern (WORKING, verified 2026-09-02)

Direct attempts all fail because OmniRoute has no `nvidia-nim` provider type and
every OpenAI-compatible type rewrites the model name:

| Provider type tried | Result |
|---|---|
| `nvidia-nim` | `Invalid provider` (unknown type) |
| `openai` (baseUrl = NIM) | model rewritten `nvidia/x` → `openai/x` → NIM 404 |
| `pollinations` | `Invalid model or alias` |
| `auto` | `Invalid provider` |

Root cause: OmniRoute strips the original namespace and re-prefixes with the
provider type (`nvidia/nemotron-...` → `openai/nemotron-...`). NVIDIA NIM needs
the literal `nvidia/<name>` id. OmniRoute ALSO injects `prompt_cache_key`,
which NIM rejects with `400 Validation: Unsupported parameter(s): prompt_cache_key`.

### Fix: local normalization proxy

Script: `data/nvidia/nvidia-nim-proxy.py` (listens on `127.0.0.1:20200`).
It does three things on each `/v1/chat/completions` forward:
1. Strip known router prefixes (`openai/`, `pollinations/`, `auto/`, `oc/`, `opencode/`).
2. Re-add `nvidia/` if no namespace remains.
3. Drop `prompt_cache_key` / `prompt_cache_behavior` before forwarding.

Then register it in OmniRoute as an `openai` provider with
`baseUrl = http://127.0.0.1:20200/v1` and `apiKey` = any dummy value (the proxy
holds the real NIM key). Import the models, then create the combo with
`providerId: "openai"` (the TYPE, not the connection UUID).

### Combo providerId pitfall

`providerId` must be `"openai"` (type string). Using the connection UUID yields:
`ALL_TARGETS_SKIPPED` — "Service temporarily unavailable: all targets were
skipped by pre-dispatch filters".

### Combo (verified working)

```json
{"name":"nvidia-stack","strategy":"priority","models":[
  {"id":"n1","kind":"model","model":"nvidia/nemotron-3.5-lightning-30b-a3b","providerId":"openai","weight":0},
  {"id":"n2","kind":"model","model":"nvidia/nemotron-3-super-120b-a12b","providerId":"openai","weight":0},
  {"id":"n3","kind":"model","model":"nvidia/nemotron-3-nano-omni-30b-a3b-reasoning","providerId":"openai","weight":0}
]}
```

### Operational note

The proxy is a separate process — it does NOT survive reboot. Either add a
scheduled task (VBS hidden, like the guardian/watchdog pattern) or launch it on
demand with `python data/nvidia/nvidia-nim-proxy.py`. Without it, `nvidia-stack`
will fail.

**Launch (2026-09-08, verified):** the proxy AUTO-loads `NVIDIA_API_KEY_GEMMA4` from
`data/nvidia/.env` when `NVIDIA_API_KEY` is unset (see `main()` key-loading block),
so a plain launch works:

```bash
python data/nvidia/nvidia-nim-proxy.py   # port 20200, key auto-loaded
```

**Persistence:** hidden VBS launcher `data/nvidia/nvidia-nim-launch.vbs` (idempotent
on port 20200) + Windows scheduled task `Hermes_NVIDIA_NIM_Proxy` (ONLOGON, LIMITED).
After launching, the `NVIDIA NIM (Proxy)` connection may sit in backoff from a prior
502 (proxy down); retry `nvidia-stack` once the backoff expires — it then returns 200.

**Vision via NIM:** `meta/llama-3.2-11b-vision-instruct` responds 200 to text and
to `data:`-URI images (Hermes sends base64/data-URIs, so it works), but returns
500 on external image URLs NIM's backend cannot fetch. Use data-URIs, not remote
URLs.