"""Probe des modeles gratuits OmniRoute + maintien du combo `eco` (defaut Hermes).

Regle: le combo eco ne contient QUE des modeles gratuits, ordre = priorite.
Le script est ADDITIF, jamais destructif: il ajoute en tete les modeles
nouvellement vivants absents du combo, et ne retire rien. Un ancien modele qui
echoue au probe reste en place (il peut etre rate-limite ponctuellement).

Historique du piege: la version precedente reconstruisait eco a partir des seuls
modeles sous un seuil de latence de 5s. Quand aucun ne passait le seuil (tous
rate-limites), eco se retrouvait avec 1 seul modele, qui echouait aussi -> toutes
les requetes Hermes partaient sur le fallback PAYANT DeepSeek. Ne jamais
resserrer la liste sur les seuls "vivants" du moment.
"""
import concurrent.futures
import json
import os
import time

import requests

API_V1 = "http://127.0.0.1:20128/v1/chat/completions"
API_COMBO = "http://127.0.0.1:20128/api/combos"
ECO_ID = "0ca67700-be56-4553-a25c-d3906920bd8a"
KEY = os.environ.get("OMNIROUTE_API_KEY", "")
HDR = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
OUT = r"C:\Users\searc\AppData\Local\Temp\omniroute_probe_result.json"
PROBE_TIMEOUT = 40
# max_tokens realiste: avec un budget minuscule, les modeles "reasoning" mettent
# tout dans reasoning_content -> validation qualite OmniRoute -> 502 (faux mort).
MAX_TOKENS = 200

CANDIDATES = [
    # Routes concretes (provider/model reels). Les alias auto/* fonctionnent en appel
    # direct mais sont ecartes dans un combo ("No credentials for auto") : ne jamais
    # les mettre dans eco.
    "gemini/gemini-3-flash-preview",
    "gemini/gemini-2.5-flash",
    "gemini/gemini-2.5-flash-lite",
    "openai/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "openai/nvidia/nemotron-3.5-lightning-30b-a3b",
    # Pool OpenCode: 403 "free tier can only be used from within OpenCode" (acces
    # restreint au client OpenCode) — conserve pour detecter un retablissement.
    "auto/best-free",
    "oc/nemotron-3-ultra-free",
    "oc/nemotron-3.5-lightning-free",
    "oc/mimo-v2.5-free",
    "oc/big-pickle",
    "oc/muse-spark-1.2-contributor-free",
    "auto/gemini",
    "auto/zai",
    "opencode/nemotron-3-ultra-free",
    "opencode/nemotron-3.5-lightning-free",
    "oc/kimi-k3",
    "zc/glm-5.3",
    "pollinations/llama-scout",
    "pollinations/llama-maverick",
    "cloudflare-ai/@cf/meta/llama-3.3-70b-instruct-fp8-fast",
]


def slug(model):
    return model.replace("@cf/", "").replace("/", "-").replace("@", "")


def provider_for(model):
    if model.startswith("cloudflare-ai/"):
        return "cloudflare-ai"
    if model.startswith("gemini/"):
        return "gemini"
    if model.startswith("openai/"):
        return "openai"
    if model.startswith("auto/"):
        return "auto"
    if model.startswith("opencode/"):
        return "opencode"
    return "oc"


def probe(model):
    t0 = time.time()
    try:
        r = requests.post(API_V1, headers=HDR,
                          json={"model": model, "messages": [{"role": "user", "content": "dis bonjour en un mot"}],
                                "max_tokens": MAX_TOKENS, "temperature": 0},
                          timeout=PROBE_TIMEOUT)
        dt = round((time.time() - t0) * 1000)
        content = ""
        if r.status_code == 200:
            try:
                content = ((r.json().get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()
            except Exception:
                content = ""
        ok = r.status_code == 200 and bool(content)
        err = ""
        if not ok:
            try:
                err = r.json().get("error", {}).get("message", "")[:120]
            except Exception:
                err = r.text[:120]
            if r.status_code == 200:
                err = "200 mais content vide (modele reasoning / validation qualite)"
        return {"model": model, "status": r.status_code, "ok": ok,
                "latency_ms": dt, "content": content[:40], "error": err}
    except Exception as e:
        return {"model": model, "status": 0, "ok": False, "latency_ms": PROBE_TIMEOUT * 1000,
                "content": "", "error": str(e)[:120]}


# --- Phase 1: Probe ---
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    results = [f.result() for f in concurrent.futures.as_completed({ex.submit(probe, m): m for m in CANDIDATES})]
results.sort(key=lambda x: (0 if x["ok"] else 1, x["latency_ms"]))

alive = [r for r in results if r["ok"]]
dead = [r["model"] for r in results if not r["ok"]]
alive_ids = [r["model"] for r in alive]

# --- Phase 2: Read current eco (source de verite de la liste gratuite) ---
current_models = []
try:
    g = requests.get(API_COMBO, headers=HDR, timeout=15)
    combos = g.json().get("combos", g.json().get("data", []))
    current = next((c for c in combos if c.get("name") == "eco"), None)
    if current:
        current_models = [m["model"] for m in current.get("models", [])]
except Exception as e:
    print(f"warn: lecture eco impossible ({str(e)[:60]})")
    current = None

# --- Phase 3: Fusion additive (jamais de reduction de la liste) ---
incoming = [m for m in alive_ids if m not in current_models]
new_model_ids = incoming + [m for m in current_models if m not in incoming]
changed = bool(incoming) and bool(current) and new_model_ids != current_models

# --- Phase 4: Write only if a new living model is detected ---
if changed:
    new_models = [{"id": f"eco-{i:02d}-{slug(m)}", "kind": "model", "model": m,
                   "providerId": provider_for(m), "weight": 0}
                  for i, m in enumerate(new_model_ids, 1)]
    payload = {
        "models": new_models,
        "strategy": "priority",
        "config": current.get("config", {"maxRetries": 1, "retryDelayMs": 2000, "handoffThreshold": 0.85}),
    }
    r = requests.put(f"{API_COMBO}/{ECO_ID}", headers=HDR, json=payload, timeout=20)
    print(f"eco updated: {r.status_code} added={incoming} models={new_model_ids}")
else:
    reason = "aucun nouveau modele vivant" if not incoming else "eco illisible"
    print(f"eco unchanged: {len(current_models)} modeles ({reason})")

# --- Phase 5: Log ---
with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"ts": time.time(), "results": results, "alive": alive_ids, "dead": dead,
               "added_to_eco": incoming, "eco_models": new_model_ids, "changed": changed},
              f, indent=2, ensure_ascii=False)
print(f"probe done: {len(alive)}/{len(results)} alive, log={OUT}")
