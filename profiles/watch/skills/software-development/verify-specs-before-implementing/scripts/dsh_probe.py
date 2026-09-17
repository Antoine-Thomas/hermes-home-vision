#!/usr/bin/env python3
"""Verify a DeepSeek Harness (`dsh`) host end-to-end, through its own RPC API.

Proves the runtime really routes to the configured LLM provider, and measures
each agent preset's fixed request size against the provider's rate limit.

Why this exists: the upstream provider answering `curl` says nothing about
whether the runtime's route + credential ref + preset compose. Only the
runtime's own session API can answer that.

Usage:
  python dsh_probe.py                        # routes + default session round-trip
  python dsh_probe.py --preset minimal code standard
  python dsh_probe.py --base-url http://127.0.0.1:3080 --cwd C:/work

Notes
  - RPC envelope: POST /api/<method> with
      {"type":"client-request","rpcId":<any>,"method":<name>,"payload":{...}}
    Content-Type MUST be application/json (415 otherwise). The configuration
    plane is loopback-only, so send an Origin matching the base URL.
  - There is no /api/health. `/` answering 200 is the liveness signal.
  - Useful methods: llm.providers, llm.models, agentPreset.list, session.create,
    session.models, session.prompt, session.history, settings.describe,
    settings.update.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:3080"


def rpc(method: str, payload: dict, base: str = BASE, timeout: int = 90):
    body = json.dumps({"type": "client-request",
                       "rpcId": f"probe-{int(time.time() * 1000)}",
                       "method": method, "payload": payload}).encode()
    req = urllib.request.Request(
        f"{base}/api/{method}", data=body,
        headers={"Content-Type": "application/json", "Origin": base}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        result = json.loads(r.read().decode())["result"]
    if not result.get("ok"):
        raise RuntimeError(f"{method} refused: {json.dumps(result.get('error'))[:300]}")
    return result["value"]


def show_routes(base: str) -> None:
    provs = rpc("llm.providers", {}, base)["providers"]
    live = [p for p in provs if p.get("active")]
    print(f"active provider routes ({len(live)} of {len(provs)} declared):")
    for p in live:
        print(f"  - {p['provider']} ({p.get('displayName')}) ns={p.get('settingsNs')}")
    for g in rpc("llm.models", {}, base)["groups"]:
        ids = ", ".join(m["id"] for m in g["models"])
        print(f"  [{g['id']}] {ids}")
    print("  NOTE: a route serves its library catalog unless a `models` list")
    print("        narrows it — retired ids stay selectable and 404 at runtime.")


def round_trip(base: str, cwd: str, preset: str | None, prompt: str) -> None:
    payload: dict = {"cwd": cwd}
    if preset:
        payload["agentPreset"] = preset
    try:
        sess = rpc("session.create", payload, base)
    except RuntimeError as e:
        # agent-preset-invalid means the preset composition fails to mount --
        # a broken preset blocks every session and is unrelated to the LLM route.
        print(f"  preset {preset or '(default)'}: session.create FAILED -> {e}")
        return
    sid = sess["sessionId"]
    used = sess.get("agentPreset") or preset or "(default)"
    cur = rpc("session.models", {"sessionId": sid}, base)
    sel = cur.get("current", {})
    print(f"  preset {used}: route={sel.get('provider')}/{sel.get('model')} "
          f"routable={cur.get('routable')}")

    t0 = time.time()
    rpc("session.prompt", {"sessionId": sid, "mode": "queue",
                           "content": [{"type": "text", "text": prompt}]}, base)

    text, usage, requested, finish = "", {}, None, None
    for _ in range(30):
        time.sleep(2)
        evs = rpc("session.history", {"sessionId": sid, "maxMessages": 40}, base)["events"]
        blob = json.dumps(evs, ensure_ascii=False)
        m = re.search(r"Requested (\d+)", blob)      # 413 body = free measurement
        if m:
            requested = int(m.group(1))
            break
        for e in evs:
            ev = e.get("event", {})
            data = ev.get("data", {})
            ch = data.get("chunk", {})
            if ch.get("type") == "usage" and ch.get("usage", {}).get("inputTokens"):
                usage = ch["usage"]
            if ch.get("type") == "finish":
                finish = ch.get("reason", {}).get("kind")
            if ev.get("type") == "assistant/message":
                for b in (data.get("message", {}).get("content") or []):
                    if isinstance(b, dict) and b.get("type") in ("text", "output_text"):
                        text += b.get("text", "")
        if text.strip() or finish == "error":
            break

    dt = time.time() - t0
    if requested:
        print(f"    -> 413: {requested} tokens requested (fixed prompt too big "
              f"for the plan's TPM cap)")
    elif text.strip():
        print(f"    -> OK in {dt:.1f}s | in={usage.get('inputTokens')} "
              f"out={usage.get('outputTokens')}")
        print(f"    -> {text.strip()[:200]!r}")
    else:
        print(f"    -> no text after {dt:.0f}s (finish={finish}); inspect the UI")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=BASE)
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--preset", nargs="*", default=[None],
                    help="presets to measure; omit for the configured default")
    ap.add_argument("--prompt", default="Reply with one short sentence: say hello.")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    try:
        urllib.request.urlopen(base, timeout=10)
    except Exception as e:  # noqa: BLE001 - liveness check only
        print(f"host not reachable at {base}: {e}")
        print("start it with: node node_modules/@deepseek-ai/dsh/lib/bin.js web")
        return 2
    print(f"host up at {base}\n")

    show_routes(base)
    print("\npresets:")
    try:
        names = [p.get("id") for p in rpc("agentPreset.list", {}, base).get("presets", [])]
        print(f"  available: {', '.join(n for n in names if n)}")
    except Exception as e:  # noqa: BLE001
        print(f"  (agentPreset.list unavailable: {e})")

    print("\nround-trips:")
    for preset in args.preset:
        round_trip(base, args.cwd, preset, args.prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
