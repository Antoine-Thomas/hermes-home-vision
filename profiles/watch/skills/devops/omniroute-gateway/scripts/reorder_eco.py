#!/usr/bin/env python3
"""Dry-run/--apply reorder of the OmniRoute 'eco' combo: free-first.

Saves /api/combos before writing. Puts keyless-verified free models at the
head (priority strategy => list order = priority), paid models last.

Usage: python reorder_eco.py [--apply]
"""
import json
import subprocess
import sys
import os
import datetime

BASE = "http://127.0.0.1:20128"
COMBOS = BASE + "/api/combos"
HERE = os.path.dirname(os.path.abspath(__file__))
COOKIES = os.path.join(HERE, "..", "or_cookies.txt")  # data dir cookie
APPLY = "--apply" in sys.argv
NOW = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# Order = power descending among keyless-verified frees; broken/doubtful frees
# pushed to end of free block (still before paid, but never head).
# Re-derive from a fresh probe_free.py run if upstreams change.
FREE_ORDER = [
    "oc/hy3-free",                     # 200 OK keyless
    "oc/nemotron-3.5-lightning-free",  # 200 OK keyless (replaces phantom north-mini-code-free)
    "oc/nemotron-3-ultra-free",        # keyless, timeout ponctuel
    "oc/mimo-v2.5-free",               # keyless, 429 si sollicite
    "oc/big-pickle",                   # keyless, 429 si sollicite
    "auto/gemini",                     # timeout (cle ?)
    "oc/kimi-k3",                      # 401 Missing API key (PAS gratuit sans cle)
    "oc/deepseek-v4-flash-free",       # 400 broken upstream
    "cloudflare-ai/@cf/meta/llama-3.3-70b-instruct",  # 503 circuit breaker
]
PAID_ORDER = [
    "kr/deepseek-3.2", "kr/claude-sonnet-4.5", "kr/claude-haiku-4.5",
    "kr/minimax-m2.5", "kr/minimax-m2.1", "kr/glm-5", "kr/qwen3-coder-next",
    "kr/claude-sonnet-5", "kr/gpt-5.6-sol", "kr/gpt-5.6-terra",
    "kr/gpt-5.6-luna", "oc/deepseek-v4-pro", "opencode/big-pickle",
    "oc/big-pickle",
]


def curl(args):
    return subprocess.run(["curl", "-s", "-b", COOKIES] + args,
                          capture_output=True, text=True).stdout


def get_combos():
    return json.loads(curl([COMBOS]))["combos"]


def slug(model):
    return model.replace("@cf/", "").replace("/", "-").replace("@", "")


def provider_for(model):
    if model.startswith("cloudflare-ai/"):
        return "cloudflare-ai"
    if model.startswith("auto/"):
        return "auto"
    if model.startswith("kr/"):
        return "kiro"
    return "opencode"  # oc/* and opencode/*


def build_models():
    out, seq = [], 1
    for model in FREE_ORDER + PAID_ORDER:
        out.append({
            "id": "eco-model-%02d-%s" % (seq, slug(model)),
            "kind": "model", "model": model,
            "providerId": provider_for(model), "weight": 0,
        })
        seq += 1
    return out


def main():
    combos = get_combos()
    eco = next((c for c in combos if c["name"] == "eco"), None)
    if eco is None:
        sys.exit("Combo 'eco' introuvable !")
    bak = os.path.join(HERE, "..", "combos_before_reorder_%s.json" % NOW)
    with open(bak, "w", encoding="utf-8") as fh:
        json.dump({"saved_at": NOW, "combos": combos}, fh, indent=2)
    print("Sauvegarde -> %s" % bak)

    new_models = build_models()
    body = {k: v for k, v in eco.items()
            if k not in ("createdAt", "updatedAt", "version", "computed_context_length")}
    body["strategy"] = "priority"
    body["models"] = new_models

    print("Nouveau eco : %d modeles" % len(new_models))
    for i, m in enumerate(new_models, 1):
        tag = "GRATUIT" if i <= len(FREE_ORDER) else "payant "
        print("  %2d. %-50s [%s]" % (i, m["model"], tag))
    if not APPLY:
        print("\n(dry-run) relancer avec --apply pour ecrire")
        return
    tmp = os.path.join(HERE, "_reorder_eco.json")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(body, fh)
    out = curl(["-X", "PUT", "%s/%s" % (COMBOS, eco["id"]),
                "-H", "Content-Type: application/json",
                "--data-binary", "@" + tmp, "-w", "\nHTTP=%{http_code}"])
    os.remove(tmp)
    print("\nPUT eco -> %s" % out.strip().splitlines()[-1])
    after = next(c for c in get_combos() if c["name"] == "eco")
    print("VERIF strategy=%s n=%d" % (after.get("strategy"), len(after["models"])))
    for i, m in enumerate(after["models"], 1):
        print("  %2d. %s" % (i, m["model"]))


if __name__ == "__main__":
    main()
