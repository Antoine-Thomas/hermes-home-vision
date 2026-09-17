---
name: compression-tokens
description: "Reduce LLM tokens via OmniRoute compression pipeline."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [omniroute, compression, tokens, cost, rtk, caveman]
    created: "2026-08-26"
    updated: "2026-08-26"
---

# Compression tokens (OmniRoute)

OmniRoute (local gateway, default port 20128) can compress requests before
they reach the upstream provider. Engines: RTK (tool-output filtering) and
Caveman (semantic condensation). `stacked` = RTK then Caveman.

## When to Use

Use when you want to cut token spend on a Hermes/agent session routed through
OmniRoute, or when asked to enable/verify request compression.

Verified empirically against **OmniRoute 3.8.49**.

## Authentication comes first (the CLI lies about failures)

The management API needs admin auth for **reads AND writes** — an earlier
version of this skill wrongly claimed reads were open on localhost.

Worse: `omniroute compression engine set stacked` **prints nothing, exits 0,
and changes nothing** when unauthenticated. It silently swallows the 401.
Never trust CLI silence — always read the state back.

```bash
# Reset admin password. The password is read from STDIN, NOT argv:
#   omniroute-reset-password "MyPass"   <-- argv is IGNORED
printf 'MyPass123' | omniroute-reset-password --password-stdin

# Log in and keep the auth_token cookie (HttpOnly -> stored as #HttpOnly_ line)
curl -s -c cookies.txt -X POST http://127.0.0.1:20128/api/auth/login \
  -H 'Content-Type: application/json' -d '{"password":"MyPass123"}'
# -> {"success":true}
```

Note: `grep -v '^#' cookies.txt` looks empty because curl prefixes HttpOnly
cookies with `#HttpOnly_`. The cookie is there.

## Enabling stacked compression (the real endpoint)

The compression endpoints are under **`/api/settings/compression`**, not
`/api/compression/*` (that path 404s for status). Do a read-modify-write so
you don't clobber unrelated fields:

```bash
curl -s -b cookies.txt http://127.0.0.1:20128/api/settings/compression   # GET
curl -s -b cookies.txt -X PUT http://127.0.0.1:20128/api/settings/compression \
  -H 'Content-Type: application/json' --data-binary @payload.json
```

`defaultMode: "stacked"` is the authoritative switch.

### The two-switch trap (this is why RTK "does nothing")

`engines.rtk.enabled: true` is **not sufficient**. There is a *second*,
independent switch: `rtkConfig.enabled`. Ship default is:

```json
"engines":   { "rtk": {"enabled": true,  "level": "standard"} },
"rtkConfig": { "enabled": false, "intensity": "minimal" }
```

While `rtkConfig.enabled` is false, RTK contributes **0%** and `stacked` only
runs Caveman (~3-4%). Set both:

```json
"rtkConfig": {"enabled": true, "intensity": "standard",
              "applyToToolResults": true, "enableGrouping": true}
```

Same pattern for Caveman: `engines.caveman` vs `cavemanConfig`.

## RTK only touches role="tool" messages

`applyToToolResults` means literally that. A verbose build log placed in a
`user` message gets **0% from RTK**. Benchmark with realistic agent traffic
(`role: "tool"` entries) or you will conclude RTK is broken:

| payload shape | rtk | caveman | stacked |
|---|---|---|---|
| tool output inside a `user` message | 0.0% | 3.2% | 4.0% |
| real `role:"tool"` messages | 52.3% | 0.3% | 36.3% |

Real-world Hermes traffic through the proxy: **1763 -> 562 tokens (68%)**.

## Verify with the echoed response header

```bash
curl -s -D - -o /dev/null -X POST http://127.0.0.1:20128/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'X-OmniRoute-Compression: default' \
  -d '{"model":"eco","messages":[{"role":"user","content":"hi"}],"max_tokens":8}' \
  | grep -i x-omniroute
```

Observed values for `X-OmniRoute-Compression: <mode>; source=<src>; tokens=A->B`:

| Header sent | Resolved |
|---|---|
| (none) | `stacked; source=default` (global mode applies) |
| `default` | `stacked; source=request-header` — full stack, same savings |
| `stacked` | `stacked; source=default` (not a valid header value; falls through) |
| `engine:rtk` | `rtk; source=request-header` |
| `off` | `off; source=request-header` |

`source=off` means compression did not run. Siblings: `X-OmniRoute-Provider`,
`X-OmniRoute-Model`, `X-OmniRoute-Decision`, `X-OmniRoute-Tokens-In/Out`.

## Preview endpoint (safe, no rate-limit burn)

`POST /api/compression/preview` with `{"messages":[...],"mode":"...","config":{}}`
returns `originalTokens` / `compressedTokens`. Its `mode` enum is **not** the
header grammar — `engine:rtk` is rejected. Allowed:
`off|lite|standard|aggressive|ultra|rtk|stacked|caveman`.

## Combos: address them by BARE NAME

Corrected — this is the reverse of what this skill previously said:

- `{"model": "eco"}` -> **200 OK**, routes through the combo.
- `{"model": "auto/eco"}` -> **400** `Unknown built-in auto combo`.

Combo order **is** priority under `strategy: fill-first`. To reorder:

```bash
# PATCH /api/combos/{id} returns 405 despite being in the OpenAPI spec. Use PUT
# with the full object (drop createdAt/updatedAt/version/computed_context_length).
curl -s -b cookies.txt -X PUT http://127.0.0.1:20128/api/combos/<id> \
  -H 'Content-Type: application/json' --data-binary @combo.json
```

`stackedPipeline` looked inert for mode resolution: rewriting its engine order
and intensities produced byte-identical savings. Treat `defaultMode` +
`rtkConfig`/`cavemanConfig` as the levers that actually matter.

## Probe combo members — dead models waste the first hop

Provider catalogues drift. On a Kiro-backed `eco` combo, 4 of 11 members
returned `400 Invalid model` on **every** call (`kr/claude-sonnet-5`,
`kr/gpt-5.6-{sol,terra,luna}`). Promoting a dead model to position 1 makes
every request burn a guaranteed failure first. Probe each member with a
5-token request, then order alive-first and demote (don't delete) the dead:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST .../v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"kr/glm-5","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
```

Confirm the routing actually landed where you intended via
`~/.omniroute/call_logs/<date>/*.json` -> `summary.provider`, `summary.model`,
`summary.comboStepId`, `summary.status`.

## Binding OmniRoute to loopback only

`HOSTNAME` in `~/.omniroute/.env` **does not work from a POSIX shell**.
bash/zsh auto-set `HOSTNAME` to the machine name, the .env loader is
first-wins, and `bin/cli/commands/serve.mjs` deliberately ignores `HOSTNAME`
when it equals `os.hostname()`. `HOST` is not read at all for the main
listener. The variable that works:

```bash
echo 'OMNIROUTE_SERVER_HOST=127.0.0.1' >> ~/.omniroute/.env
```

Verify the real socket, never the log banner (it always prints `localhost`):

```bash
netstat -ano | grep 20128 | grep -i LISTENING
# want 127.0.0.1:20128 — NOT 0.0.0.0:20128
```

`omniroute serve` runs under a supervisor that respawns the child, so
`omniroute stop` alone may leave a listener. Kill the supervisor process,
then `omniroute stop`.

### After loopback-binding, stop using `localhost` in client URLs

On Windows `localhost` resolves to IPv6 `::1` **first**. With an IPv4-only
bind, every request pays a failed-connect then retry: measured **0.21s vs
0.0026s** (~80x). Point clients at `127.0.0.1` explicitly:

```bash
hermes config set model.base_url http://127.0.0.1:20128/v1
hermes config set providers.omniroute.api http://127.0.0.1:20128/v1
hermes config set fallback_providers.0.base_url http://127.0.0.1:20128/v1  # list index works
```

## Wiring it into Hermes

`providers.<name>.extra_headers` bridges to the OpenAI client's
`default_headers`, matched by base_url. A *skill* cannot inject HTTP headers —
only config can.

```bash
hermes config set providers.omniroute.extra_headers.X-OmniRoute-Compression default
```

`default` is the right value: it yields the full global `stacked` stack with
`source=request-header`. Leaving the header off also works (`source=default`).

Confirm which provider really served a Hermes run — self-reports and
model names lie, the billing ledger doesn't:

```sql
-- ~/.hermes/state.db  (AppData/Local/hermes/state.db on Windows)
SELECT session_id, model, billing_provider, estimated_cost_usd
FROM session_model_usage ORDER BY rowid DESC LIMIT 10;
```

Free OmniRoute traffic shows `estimated_cost_usd = 0.0`; a paid fallback
shows the real provider and a non-zero cost.

## Pitfalls

- CLI writes fail **silently** without auth. Always read state back.
- Two switches per engine (`engines.<id>` + `<id>Config`). Both must be on.
- RTK only compresses `role:"tool"`; benchmark with realistic traffic.
- Bare combo name works; `auto/<combo>` 400s.
- `PATCH /api/combos/{id}` -> 405; use `PUT`.
- Compression legitimately reports `off` on tiny payloads.
- Free no-auth providers (`oc/`, `ddgw/`, `tllm/`) rate-limit fast (429). Use
  the authed `preview` endpoint instead of hammering real models.
- `ddgw/*` rejects Hermes tool schemas (400); prefer `oc/*` or `kr/*` for
  agent sessions.
- `hermes -z` is required for `model_aliases`; `hermes chat -q --model <alias>`
  fuzzy-matches to the wrong catalog model.
- `hermes config set model_aliases.X.Y` warns "not a recognized config key" —
  it still saves, and `oneshot.py` reads it. Expected, not an error.
