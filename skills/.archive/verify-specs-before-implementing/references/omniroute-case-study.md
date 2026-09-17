# Case study: a 6-step brief with 4 wrong literals

Task: install a local AI gateway (OmniRoute 3.8.49) as a 4th provider for
Hermes, per a numbered brief. Four prescribed literals did not survive
verification. Each was caught by a cheap probe *before* it became silent
misconfiguration.

## 1. Header value that the parser ignores

Brief said: send `X-OmniRoute-Compression: stacked` on every request.

Probe — send it and read the echoed response header:

```bash
curl -s -D - -o /dev/null -X POST http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-OmniRoute-Compression: stacked" \
  -d '{"model":"<free-model>","messages":[{"role":"user","content":"hi"}],"max_tokens":8}' \
  | grep -i x-omniroute-compression
```

Result: `x-omniroute-compression: off; source=off` — silently discarded.

Cause, in `src/shared/utils/compressionHeaderEcho.ts`: the parser accepts only
`off`, `default`, `engine:<id>`, or a *named combo*. `stacked` is a **global
mode** name, not a header value; unknown values fall through to the global
default (often `off`).

Chosen substitute: `default`. Reason — an `engine:<id>` value would have
*overridden* the global stacked mode the user later enabled. When in doubt pick
the value that defers to the user's own config rather than pinning a guess.

## 2. CLI subcommand that does not exist

Brief said: alias to `hermes model set <model>`.

Probe: `hermes model --help` -> interactive picker only, no `set` verb.
Real persistent switch: `hermes config set model.default/provider/base_url`.

## 3. A config file nothing reads

Brief said: write aliases to `~/.hermes/aliases.json`.

Probe: grep the codebase and the user's own scripts for the filename — zero
hits. Writing it would have been pure cargo-culting.

Real mechanism found by grepping for "alias": a `model_aliases:` config section
(`model_aliases.<name>.{model,provider,base_url}`).

Sting in the tail: that section is only consulted on the `--oneshot` code path.
On the `-q` path a fuzzy normalizer ran instead and silently rewrote an alias to
the nearest catalogue model — printing a "Normalized model 'X' to 'Y'" warning
that is easy to skim past. **Treat any "normalized" warning as "my identifier
was ignored".** Verified by checking which target actually served the request,
not by trusting the exit code.

## 4. Identifier shape

Brief said: `default_model: <combo-name>`.

Probe: one call with the bare name -> HTTP 400 "Unable to determine provider".
Built-in combos needed an `auto/` prefix; **user-created** combos were
addressed as bare IDs. Same object class, two shapes — only a live probe
distinguishes them. Do not generalise from one example to the other.

## 5. Vendor claim: "78-95 % savings" -> measured ~1 %

Identical 14,571-char payload (build-log noise + repeated code), same model,
sent twice:

| Compression | `tokens_in` | `compressed` | Saving |
|---|---|---|---|
| `off` | 9,737 | null | — |
| `stacked` | 9,643 | 80 | **~1 %** |

Reproduced twice. On real agent traffic (32,104 tokens): `compressed: null`,
i.e. 0 %.

Root cause, in `open-sse/services/compression/types.ts`:

```
DEFAULT_COMPRESSION_CONFIG : enabled: false, defaultMode: "off"
DEFAULT_RTK_CONFIG         : enabled: false, intensity: "minimal", enabledFilters: []
DEFAULT_CAVEMAN_CONFIG     : enabled: false, compressRoles: ["user"], minMessageLength: 50
```

The umbrella mode and **each engine** carry separate `enabled` flags. The mode
was `stacked` and the response header cheerfully reported
`stacked; source=default`, while both engines stayed `false` — so the pipeline
ran empty. This is the generalisable trap: **a self-reported "enabled" is not
evidence of effect.**

Contributing factors worth checking on any such pipeline:

- The high-yield stage shipped with an empty filter list and no filter file on
  disk. Advertised numbers assumed it was populated.
- The other stage only processed one message role and skipped short messages;
  with system-prompt preservation on, most of the payload was exempt by design.

## Measurement recipe

Per-request usage headers read 0 on providers that do not report usage, which
looks like "no data" rather than "not measured". The authoritative record was a
local call log:

```bash
cd ~/.omniroute/call_logs/$(date +%Y-%m-%d)
python -c "
import json,glob,os
for f in sorted(glob.glob('*.json'),key=os.path.getmtime,reverse=True)[:4]:
    s=json.load(open(f,encoding='utf-8')).get('summary',{})
    t=s.get('tokens',{}) or {}
    print(s.get('comboName'),s.get('provider'),'in=',t.get('in'),
          'compressed=',t.get('compressed'))"
```

Send the same payload twice (feature off, then on) and diff the real counter.

## Bonus: an unrequested security finding

Worth a port check on any "localhost only" brief. The service bound
`0.0.0.0:<port>` despite a `HOSTNAME=127.0.0.1` line already present in its
packaged env file, and was reachable from the LAN IP with **no auth**:

```bash
netstat -ano | grep LISTENING | grep ":<port>"
curl -s -m 8 -o /dev/null -w "%{http_code}\n" http://<lan-ip>:<port>/<endpoint>
```

`0.0.0.0` + HTTP 200 from the LAN IP = exposed. Restarting with the bind
variables exported in the environment fixed it (LAN -> `000`, localhost ->
`200`). Persisting it required appending to a file holding a secret — that is a
user decision; ask rather than force-write.

## Failover: prove it by outage, not by hope

To prove a fallback chain works, kill the primary outright (connection error is
a guaranteed trigger) and confirm a request still succeeds — wrapping the test
in a `trap ... EXIT` that always restarts the service. Saturation-based tests
are unreliable: a free tier may simply not hit its quota, giving an
inconclusive result. Report inconclusive as inconclusive.

Also note: fallback chains commonly trigger only on rate-limit / 5xx / network
errors. A 400 from a typo'd model name does **not** activate them.
