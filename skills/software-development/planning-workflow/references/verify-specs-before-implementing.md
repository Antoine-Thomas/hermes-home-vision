<!-- Source: software-development/verify-specs-before-implementing/SKILL.md — migrated to umbrella planning-workflow on 2026-09-10 -->

---
name: verify-specs-before-implementing
description: "Verify prescribed commands and values before implementing."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [verification, setup, integration, config, honesty, measurement]
    created: "2026-08-26"
---

# Verify specs before implementing

When a request arrives as a numbered brief with exact commands, config keys,
header names, or API values ("run X, set `key: value`, add header `H: v`"),
those literals are a *hypothesis about the system*, not ground truth. Briefs
are often assembled from blog posts, changelogs, or another tool's conventions.
Implementing them verbatim produces config that looks right, applies cleanly,
and silently does nothing.

## When to Use

Any "install/configure/integrate X with these exact settings" task, especially
when the brief names specific header values, CLI subcommands, config keys, or
file paths — and whenever a vendor advertises a performance/savings number you
are about to repeat.

## The check, before writing any config

For each literal in the brief, confirm it exists in *this* installation:

1. **CLI subcommands** — `<tool> --help`, `<tool> <cmd> --help`. Do not assume
   a verb exists because it is idiomatic elsewhere.
2. **Config keys** — grep the actual source/schema for the key name. A key the
   loader never reads is indistinguishable from a working one in the file.
3. **File paths the brief tells you to write** — grep the codebase for the
   filename. If nothing reads it, writing it is cargo-culting; find the real
   mechanism instead.
4. **Header / enum / magic values** — find the parser and read its accepted
   set. Then send one live request and read what the server echoes back.
5. **Identifier shapes** — probe one real call. Prefix conventions differ
   between built-in and user-created objects far more often than docs admit.
6. **Model / resource IDs the brief names** — list what *this credential* is
   actually entitled to (`GET /v1/models`, `<tool> models list`) before wiring
   one in as a default. A brief's model names age badly: providers retire IDs,
   and a *bundled catalog shipped inside the library* keeps advertising models
   the account no longer serves, so the local catalog and the account disagree.
   A 404 `model_not_found` with a valid key is that disagreement, not a bad key.
7. **Quota and rate limits, before declaring a free tier "viable"** — read the
   limit headers on one real response (`x-ratelimit-limit-tokens`,
   `-remaining-`, `-reset-`). A free tier that answers a one-line prompt in
   0.4 s can still be unusable for the actual workload; see "Sizing the real
   payload" below.

## Sizing the real payload, not the smoke test

A latency/quality probe with a 10-token prompt proves the credential works. It
does not prove your *workload* fits. Agent-style workloads carry a large fixed
prefix (system prompt + tool catalog + instructions) that dwarfs the user turn,
and the fixed prefix is what collides with a tokens-per-minute cap.

So measure the fixed cost per configuration mode before choosing one, and report
it as a table. A real measurement from one such integration:

| Mode | Fixed request size | vs 8,000 TPM cap |
|------|-------------------|------------------|
| lightest | ~790 tokens | fits |
| mid | 10,032 tokens | 413, 1.3× over |
| full | 73,172 tokens | 413, 9.1× over |

The provider reports this for you: a `413` whose body names `Requested <N>` is a
free measurement of your own payload. Harvest that number instead of guessing,
and pick the mode from the data.

## Distinguish "unsupported" from "unaffordable"

When an integration fails, separate the two verdicts explicitly, because they
lead to opposite recommendations:

- **Unsupported** — the capability genuinely is not there. Say so plainly and
  propose the simple alternative instead of forcing an elaborate workaround.
- **Supported but quota-bound** — the wiring is correct and provably routes
  (confirm it: the runtime reports the route and answers a small request), and
  only a plan limit blocks the intended scale. Report it as *working, with this
  ceiling*, plus which modes fit under the ceiling. Do not present a quota wall
  as "the integration does not work".


Cheap probe pattern for an HTTP value: send the request, dump response
headers, and see how the server *reports* what it did rather than trusting the
request went through as intended.

## Report corrections, do not silently comply

Implement what works; for each literal that does not, say plainly what you
sent, what came back, and what you used instead. This user acts on corrections
(they reprioritise and finish blocked steps themselves), so surfacing a wrong
spec is more valuable than quietly making the file look correct.

Never "fix" a broken value by picking a plausible substitute without saying so.
And when a substitute could *override* the setting the user actually wants,
choose the neutral value that defers to their global config instead of pinning
your own guess.

## Separate measured from advertised

Report vendor claims and your own measurements as different things, always:

- "Measured here: X" vs "Vendor claims: Y (not reproduced)".
- A feature reporting itself as *enabled* is not evidence it is *effective*.
  Enabled-and-doing-nothing is extremely common: umbrella modes frequently have
  per-engine / per-stage `enabled` flags that default to `false`, so the mode
  turns on while every stage stays inert.
- Measure the same payload twice — once with the feature off, once on — and
  diff the real counter. If the counter reads 0, find the authoritative local
  record (log file, DB) rather than concluding "no change".
- If a number cannot be measured, say so instead of quoting the brochure.

## Pitfalls

- A brief's numbered steps may not be independent: a later step often reveals
  an earlier one was impossible. Read the whole brief and probe the risky
  literals first, before building on them.
- Some steps need a human (interactive OAuth/social login, choosing a password,
  writing a secret). Stop and ask; never invent credentials or dig them out of
  logs.
- Config-writing helpers may refuse to touch security-sensitive files. Use the
  tool's own `config set`-style command rather than editing the file directly.
- Structured values (lists of objects) often pass fine as inline JSON through a
  `config set` command — try that before hand-editing YAML.
- Verify a header/flag is not only accepted but *scoped*: confirm it is sent to
  the intended endpoint and not leaked to every other provider.
- Health-check URLs in briefs are frequently invented. `/api/health` answering
  "not found" while `/` answers 200 means the brief guessed, not that the
  service is down. Find the real control surface in the package's own types or
  README (an RPC method map, a generated API contract) before reporting failure.
- The brief's *install* command can be the wrong one for this host even when the
  package is right: a global install may leave the binary off `PATH`, and a
  `npx`-style runner may sit there resolving instead of printing help. Install
  into a project directory and invoke the package's real entry script directly.
- Before running an unfamiliar package a brief tells you to install — especially
  one that starts a local server and executes files — confirm its identity
  first (registry metadata, repo URL, license, version). Legitimate is not the
  same as assumed-legitimate, and this check costs one command.
- Secrets the tool already stores: load them into a shell variable and use them
  without echoing. When you must show the credential file's shape, print key
  names with values masked (`<56 chars masked>`), never a prefix of the value.
- Config written through the tool's own validating API (an RPC `settings.update`
  or `config set`) is checked against the live schema and can apply hot; the
  same YAML hand-edited is unvalidated and may need a restart. Prefer the API,
  and always back up the config file first.

## Worked example

`references/omniroute-case-study.md` — a six-step brief where four literals
were wrong (an ignored header value, a non-existent CLI subcommand, a config
file nothing reads, a bad identifier shape), plus a vendor "78-95 % savings"
claim that measured ~1 % because two per-engine `enabled` flags defaulted to
false. Includes the two-run measurement recipe.

`references/free-provider-in-agent-runtime.md` — wiring a free-tier LLM provider
into a self-hosted agent runtime. Three brief literals wrong (retired model ids
still advertised by the library's bundled catalog, an invented `/api/health`, a
key the brief wanted pasted that was already stored), and the real blocker was
an unmeasured 8,000 TPM cap versus fixed prompt sizes of 790 / 10,032 / 73,172
tokens per preset. Verdict framing: *supported and provably routing, but
quota-bound*.

## Re-runnable probes

- `scripts/probe_openai_provider.py --base-url <url> --key-env <ENV>` — lists the
  models the credential is actually entitled to, prints rate-limit headers, and
  asserts non-empty text plus working tool calls before you wire a model in.
- `scripts/dsh_probe.py [--preset minimal code standard]` — verifies a DeepSeek
  Harness host through its own RPC API: active routes, served catalog, and one
  real session round-trip per preset, harvesting `Requested <N>` from any 413 to
  measure each preset's fixed prompt size.
