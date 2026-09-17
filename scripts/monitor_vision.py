#!/usr/bin/env python3
"""Monitor vision gratuit OmniRoute — sonde horaire des modeles vision free.

Des qu'un modele vision gratuit repond 200 (content non vide), ce script
cree/met a jour le combo "vision" avec les modeles fonctionnels en priorite.
N'utilise que la stdlib (urllib) : aucun venv/dependance requis.
"""
import json
import os
import sys
import datetime
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:20128"
ENV = os.path.expanduser("~/.omniroute/.env")

# Candidats vision gratuits, en ordre de priorite preferee (gemini-flash d'abord).
CANDIDATES = [
    ("gemini/gemini-3.1-flash-lite", "gemini"),
    ("gemini/gemini-3-flash-preview", "gemini"),
    ("gemini/gemini-2.5-flash-lite", "gemini"),
    ("oc/gemini-3.5-flash-lite", "oc"),
    ("oc/gemini-3.1-flash-lite", "oc"),
    ("pol/qwen-vision", "pol"),
    ("pol/qwen-vision-pro", "pol"),
    ("zc/glm-4.6v", "zcode"),
]


def get_key():
    try:
        with open(ENV, encoding="utf-8") as f:
            for line in f:
                if line.startswith("OMNIROUTE_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


KEY = get_key()


def api(path, method="GET", body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Authorization", "Bearer " + KEY)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return 0, {"error": str(e)}


def probe(model):
    body = {"model": model, "messages": [{"role": "user", "content": "reponds OK"}],
            "max_tokens": 20, "stream": False}
    code, d = api("/v1/chat/completions", "POST", body)
    if code != 200 or not d:
        return False
    try:
        c = (d.get("choices", [{}])[0].get("message", {}) or {}).get("content", "")
        return bool(c.strip())
    except Exception:
        return False


def log(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        with open(os.path.expanduser("~/.omniroute/vision_monitor.log"),
                  "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    return line


def main():
    working = [(m, p) for m, p in CANDIDATES if probe(m)]
    log("sonde vision : %d/%d OK -> %s"
        % (len(working), len(CANDIDATES), [m for m, _ in working] or "aucun"))

    if not working:
        # watchdog : rester silencieux (stdout vide = aucune notification)
        return

    models = [{"id": "vision-%02d-%s" % (i, m.replace("/", "-")),
               "kind": "model", "model": m, "providerId": p, "weight": 0}
              for i, (m, p) in enumerate(working, 1)]

    # backup des combos avant ecriture
    code, data = api("/api/combos")
    combos = (data or {}).get("combos", [])
    bak = os.path.expanduser("~/.omniroute/combos_bak_vision_%s.json"
                             % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    try:
        json.dump({"combos": combos}, open(bak, "w", encoding="utf-8"), indent=2)
    except Exception:
        pass

    existing = next((c for c in combos if c["name"] == "vision"), None)
    if existing:
        body = {k: v for k, v in existing.items()
                if k not in ("createdAt", "updatedAt", "version",
                             "computed_context_length", "repairNote")}
        body["strategy"] = "priority"
        body["models"] = models
        code, d = api("/api/combos/" + existing["id"], "PUT", body)
        print("combo 'vision' mis a jour (id %s) : HTTP %d" % (existing["id"], code))
    else:
        code, d = api("/api/combos", "POST",
                      {"name": "vision", "strategy": "priority", "models": models})
        print("combo 'vision' cree : HTTP %d" % code)

    code, d = api("/v1/chat/completions", "POST",
                  {"model": "vision", "messages": [{"role": "user", "content": "reponds OK"}],
                   "max_tokens": 20, "stream": False})
    print("verification combo 'vision' : HTTP %d" % code)


if __name__ == "__main__":
    main()
