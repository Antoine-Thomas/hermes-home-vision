---
name: omniroute-cost-tracker
description: "Use when tracking OmniRoute model cost (free vs paid)."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [omniroute, cost, tracking, models, llm, observability]
---

# OmniRoute Cost Tracker

## When to Use
- Want to know which models are being routed (free vs paid) and how much is being spent.
- Transposes Ruflo's cost-tracker/observability.

## Context
- OmniRoute gateway: `http://127.0.0.1:20128` (Bearer token in `~/.omniroute/.env`).
- Free routing: `auto/zai` → DeepSeek-V3. Paid: GLM-5.3 (Z.AI/ZenMux credit), DeepSeek fallback when free is down.
- The gateway logs each request with the resolved model; locate the log (typically the OmniRoute server log under `~/.omniroute/` or the daemon stdout) and parse it.

## Steps
1. **Find the logs** — check the OmniRoute log file/daemon output for per-request lines (model name, tokens, timestamp). If the location is unknown, inspect `~/.omniroute/` or `omniroute` help before assuming.
2. **Parse** — extract `model`, `prompt_tokens`, `completion_tokens` per request (regex on the log lines).
3. **Classify** — map each model to FREE or PAID (free: `auto/zai`/DeepSeek-V3; paid: GLM-5.3 and any non-free fallback). Keep the mapping in a small table at the top of a tracker script.
4. **Aggregate** — totals per model + per free/paid bucket (requests, tokens, estimated cost using a configurable $/1M-token table).
5. **Report** — a short digest: free vs paid share, top models, any shift toward paid (alert if paid share rises).

## Pitfalls
- The OmniRoute log path may differ — verify by inspecting the daemon/`~/.omniroute/` before assuming.
- Token→cost rates are estimates; keep the rate table editable and mark estimates as such.
