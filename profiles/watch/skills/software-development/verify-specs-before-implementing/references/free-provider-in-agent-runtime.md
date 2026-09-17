# Case study: wiring a free LLM provider into a self-hosted agent runtime

Integration of **Groq** (free tier) as the LLM provider for **DeepSeek Harness
(`dsh`)** on Windows. The brief was 5 numbered steps; three of its literals were
wrong, and the real blocker was a quota ceiling nobody had measured. Verdict:
*supported and provably routing, but quota-bound* — a different answer from
"unsupported".

## What the brief got wrong

| Brief said | Reality |
|---|---|
| model `llama-3.3-70b-versatile` / `llama-3.1-8b-instant` | `404 model_not_found` — the account no longer serves any Llama chat model |
| check `GET /api/health` | returns `not found`; `/` returns 200. Real control surface is an RPC API |
| ask the user to paste the API key | key was already stored as a credential ref; never needed to be seen |

Model IDs came from the *library's bundled catalog*, which still advertised
retired models. Two sources disagreed and the credential is the authority:

```bash
curl -s https://api.groq.com/openai/v1/models -H "Authorization: Bearer $KEY"
```

Only 3 chat models intersected the bundled catalog and the account's real
entitlements. That intersection is the true candidate set.

## Reading a stored credential without exposing it

```bash
KEY=$(python -c "
import yaml
print(yaml.safe_load(open('.credentials.yaml',encoding='utf-8'))['refs']['GROQ_API_KEY'])")
echo "loaded (${#KEY} chars)"   # never echo $KEY itself
```

To show a credential file's shape, mask every value:
`KEY_NAME: <56 chars masked>`.

## Probe the model on the axes that matter

Latency alone is not enough. For an agent runtime, run three probes:

1. **Quality in the target language** — one real prompt, read the output.
2. **Function calling** — send a `tools` array; require `finish_reason ==
   "tool_calls"` with a well-formed call. A model that cannot call tools cannot
   drive an agent, however fast it is.
3. **Rate-limit headers** — `curl -D -` and read
   `x-ratelimit-limit-tokens` / `-remaining-` / `-reset-`.

Result here: `openai/gpt-oss-120b` — good French, 0.44 s, correct `tool_calls`.
A sibling 20B model returned **empty content** because reasoning consumed the
whole `max_tokens` budget: an empty completion is a real failure mode, so assert
non-empty text rather than a 200.

## The actual blocker: fixed prompt size vs TPM cap

Free tier measured `x-ratelimit-limit-tokens: 8000`. The runtime's fixed prefix
(system prompt + tool catalog) per agent preset, harvested from the `413` body's
`Requested <N>`:

| Preset | Fixed request | Verdict |
|---|---|---|
| `minimal` | ~790 tokens (786 input observed on success) | works |
| `code` | 10,032 | 413 — 1.3× over |
| `standard` | 73,172 | 413 — 9.1× over |

Lesson: on a token-per-minute-capped free tier, **the agent's own prompt is the
workload**, and the preset/tool-catalog choice decides viability. Measure it
before recommending a provider for agent work.

## Verify through the runtime, not just the provider

The provider answering is not evidence the runtime routes to it. Confirm inside
the runtime: create a session, read the selection it reports, prompt it, read
the answer back out of its history. Here that returned
`provider=groq, model=openai/gpt-oss-120b, routable=true`, 293 input / 80 output
tokens, 2.0 s, real French text — which is what turns "configured" into
"working". `scripts/dsh_probe.py` automates exactly this loop.

## Incidental finding worth reporting, not fixing

The runtime's default agent preset was a user-made copy that failed to mount
(`agent-preset-invalid`: a tool row already registered by the host), so *no*
session could start with it — unrelated to the provider work. Report such a
find, name the one-line fix, and leave the user's artifact untouched unless they
ask.

## Prefer the validating API over hand-editing config

Writes went through the runtime's own RPC `settings.update` (schema-validated,
applied hot, no restart). Back up the config file first anyway. Reading back the
file *and* re-querying the runtime's model directory confirmed both layers
agreed.
