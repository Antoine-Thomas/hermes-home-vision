#!/usr/bin/env python3
"""Probe each candidate 'free' model: does it answer WITHOUT an API key?

Reports HTTP code + first content token for each model. Run from the
OmniRoute data dir (or pass cookie path as argv[1]).

Usage: python probe_free.py [or_cookies.txt]
"""
import json
import subprocess
import sys

BASE = "http://127.0.0.1:20128"
COOKIES = sys.argv[1] if len(sys.argv) > 1 else "or_cookies.txt"

CANDIDATES = [
    "oc/hy3-free",
    "oc/nemotron-3.5-lightning-free",
    "oc/nemotron-3-ultra-free",
    "oc/mimo-v2.5-free",
    "oc/big-pickle",
    "opencode/big-pickle",
    "auto/gemini",
    "oc/kimi-k3",
    "oc/deepseek-v4-flash-free",
    "cloudflare-ai/@cf/meta/llama-3.3-70b-instruct",
]


def ask(model):
    cmd = [
        "curl", "-s", "-b", COOKIES, "-X", "POST", BASE + "/v1/chat/completions",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": "dis bonjour en un mot"}],
            "max_tokens": 5, "stream": False,
        }),
        "-w", "\nHTTP=%{http_code}", "--max-time", "25",
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=35).stdout
    except Exception as e:
        return ("ERR", str(e)[:60])
    m = None
    for line in out.splitlines():
        if line.startswith("HTTP="):
            m = line[5:]
    body = out[:out.rfind("\nHTTP=")] if m else out
    try:
        d = json.loads(body)
        if "error" in d:
            return (m, "ERR: " + d["error"].get("message", "")[:50])
        content = d.get("choices", [{}])[0].get("message", {}).get("content", "")
        return (m, "OK: " + content[:40].replace("\n", " "))
    except Exception:
        return (m, "RAW: " + body[:50].replace("\n", " "))


if __name__ == "__main__":
    print("%-50s | HTTP | resultat" % "modele")
    print("-" * 100)
    for mod in CANDIDATES:
        code, res = ask(mod)
        print("%-50s | %s | %s" % (mod, code, res))
