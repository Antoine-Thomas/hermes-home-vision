#!/usr/bin/env python3
"""Probe an OpenAI-compatible endpoint before wiring it into anything.

Answers the four questions a brief's literals cannot be trusted on:
  1. Which models is THIS credential actually entitled to?  (GET /v1/models)
  2. What are the real rate limits?                         (response headers)
  3. Does a candidate model return non-empty text?          (reasoning models
     can spend the whole max_tokens budget and return "")
  4. Can it call tools?                                     (agent viability)

Usage:
  python probe_openai_provider.py --base-url https://api.groq.com/openai/v1 \
      --key-env GROQ_API_KEY [--model openai/gpt-oss-120b] [--lang French]

The key is read from an environment variable and never printed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


def call(url: str, key: str, payload: dict | None = None, timeout: int = 60):
    """POST payload (or GET when None). Returns (status, headers, parsed_body)."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST" if data else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, dict(r.headers), json.loads(raw or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            body = json.loads(raw)
        except ValueError:
            body = {"raw": raw[:500]}
        return e.code, dict(e.headers), body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--key-env", required=True, help="env var holding the API key")
    ap.add_argument("--model", help="candidate model id (default: first chat-ish id)")
    ap.add_argument("--lang", default="French", help="language for the quality probe")
    args = ap.parse_args()

    key = os.environ.get(args.key_env, "").strip()
    if not key:
        print(f"FAIL: env var {args.key_env} is empty or unset")
        return 2
    print(f"key loaded from {args.key_env} ({len(key)} chars, not shown)")
    base = args.base_url.rstrip("/")

    # 1. entitlements
    status, _, body = call(f"{base}/models", key)
    if status != 200:
        print(f"FAIL: GET /models -> {status} {json.dumps(body)[:300]}")
        return 2
    ids = sorted(m["id"] for m in body.get("data", []) if m.get("id"))
    print(f"\nentitled models ({len(ids)}):")
    for i in ids:
        print("  -", i)

    model = args.model
    if model and model not in ids:
        print(f"\nWARNING: requested model {model!r} is NOT entitled to this key.")
        print("  A bundled/library catalog or a brief may advertise retired ids.")
    if not model:
        skip = ("whisper", "guard", "embed", "tts", "orpheus", "rerank")
        cands = [i for i in ids if not any(s in i.lower() for s in skip)]
        if not cands:
            print("FAIL: no chat-looking model to probe")
            return 2
        model = cands[0]
        print(f"\nno --model given, probing {model!r}")

    # 2 + 3. quality probe with rate-limit headers
    prompt = f"Answer in {args.lang}, one short sentence: say hello and name yourself."
    t0 = time.time()
    status, headers, body = call(
        f"{base}/chat/completions",
        key,
        {"model": model, "messages": [{"role": "user", "content": prompt}],
         "max_tokens": 200},
    )
    dt = time.time() - t0
    print(f"\ntext probe: HTTP {status} in {dt:.2f}s")

    limits = {k: v for k, v in headers.items() if "ratelimit" in k.lower()}
    if limits:
        print("rate limits:")
        for k in sorted(limits):
            print(f"  {k}: {limits[k]}")
        tpm = limits.get("x-ratelimit-limit-tokens")
        if tpm:
            print(f"  => fixed agent prompts must stay under {tpm} tokens/min")
    if status == 413:
        print("  413 body (carries your measured payload size):",
              json.dumps(body)[:300])

    text = ""
    if status == 200:
        text = (body.get("choices", [{}])[0].get("message", {}) or {}).get("content") or ""
        usage = body.get("usage", {})
        print(f"  usage: in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')}")
        print(f"  text : {text.strip()[:200]!r}")
        if not text.strip():
            print("  FAIL: empty completion (reasoning likely ate the token budget)")

    # 4. tool calling
    status_t, _, body_t = call(
        f"{base}/chat/completions",
        key,
        {"model": model,
         "messages": [{"role": "user", "content": "Read data.json using the tool."}],
         "tools": [{"type": "function", "function": {
             "name": "read_file", "description": "Read a file",
             "parameters": {"type": "object",
                            "properties": {"path": {"type": "string"}},
                            "required": ["path"]}}}],
         "tool_choice": "auto", "max_tokens": 200},
    )
    choice = (body_t.get("choices") or [{}])[0]
    calls = (choice.get("message") or {}).get("tool_calls")
    print(f"\ntool-calling probe: HTTP {status_t} finish={choice.get('finish_reason')}")
    print("  tool_calls:", json.dumps(calls)[:200] if calls else "NONE")

    ok = status == 200 and bool(text.strip()) and bool(calls)
    print(f"\nVERDICT for {model}: {'usable for agent work' if ok else 'NOT fully usable'}")
    print("  (quota ceiling still decides which agent preset/tool catalog fits)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
