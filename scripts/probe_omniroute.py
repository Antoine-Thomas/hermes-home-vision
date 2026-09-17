"""Probe des modeles gratuits OmniRoute + maintien du combo `eco` (defaut Hermes).

Regle: le combo eco ne contient QUE des modeles gratuits, ordre = priorite.
Le script est ADDITIF par defaut et ELAGUE seulement les cibles mortes :
il ajoute en tete les modeles nouvellement vivants absents du combo, et retire
une cible apres PRUNE_AFTER echecs consecutifs a code TERMINAL (401/402/403/404
= acces ferme ou modele retire du catalogue). Les echecs transitoires (429
quota, 502/504 surcharge, timeout) ne comptent PAS : un modele rate-limite
revient tout seul, et un modele vivant n'est jamais retire.

Historique du piege: la version precedente reconstruisait eco a partir des seuls
modeles sous un seuil de latence de 5s. Quand aucun ne passait le seuil (tous
rate-limites), eco se retrouvait avec 1 seul modele, qui echouait aussi -> toutes
les requetes Hermes partaient sur le fallback PAYANT DeepSeek. Ne jamais
resserrer la liste sur les seuls "vivants" du moment : d'ou le plancher
FLOOR_MODELS qui refuse tout elagage qui viderait eco.
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
# --- Elagage des cibles mortes (decision du 17/09/2026) ---
STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "data", "omniroute", "probe_omniroute_state.json")
PRUNE_AFTER = 3      # N passages horaires consecutifs en echec TERMINAL avant retrait
FLOOR_MODELS = 2     # garde-fou : ne jamais descendre sous ce nombre de cibles
TERMINAL_CODES = {401, 402, 403, 404}   # acces ferme / modele retire du catalogue

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

# --- Phase 3: Fusion additive + elagage des cibles mortes ---
state = {}
try:
    if os.path.exists(STATE_FILE):
        state = json.load(open(STATE_FILE, encoding="utf-8")) or {}
except Exception:
    state = {}
failures = state.get("terminal_failures", {}) or {}

results_by_model = {r["model"]: r for r in results}
# Compteur d'echecs TERMINAUX consecutifs : remis a zero des qu'un modele repond.
for m in CANDIDATES:
    r = results_by_model.get(m)
    if not r:
        continue
    if r["ok"]:
        failures.pop(m, None)
    elif r["status"] in TERMINAL_CODES:
        failures[m] = failures.get(m, 0) + 1
    # transitoire (429 quota, 502/504, timeout, 200-content-vide) : ne compte pas

incoming = [m for m in alive_ids if m not in current_models]
merged = incoming + [m for m in current_models if m not in incoming]
pruned = [m for m in merged
          if m not in alive_ids
          and failures.get(m, 0) >= PRUNE_AFTER
          and results_by_model.get(m, {}).get("status") in TERMINAL_CODES]

new_model_ids = [m for m in merged if m not in pruned]
if len(new_model_ids) < FLOOR_MODELS:                 # garde-fou : ne jamais vider eco
    print(f"warn: elagage refuse ({len(new_model_ids)} cible(s) restante(s) < FLOOR_MODELS={FLOOR_MODELS})")
    pruned, new_model_ids = [], merged
changed = bool(current) and new_model_ids != current_models

state["terminal_failures"] = failures
state["updated_at"] = time.time()
try:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as sf:
        json.dump(state, sf, indent=1, ensure_ascii=False)
except Exception as e:
    print(f"warn: ecriture de l'etat impossible ({str(e)[:60]})")

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
    print(f"eco updated: {r.status_code} added={incoming} pruned={pruned} models={new_model_ids}")
else:
    reason = "aucun nouveau modele vivant" if not incoming else "eco illisible"
    print(f"eco unchanged: {len(current_models)} modeles ({reason})" + (f" | elagues={pruned}" if pruned else ""))

# --- Phase 5: Log ---
with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"ts": time.time(), "results": results, "alive": alive_ids, "dead": dead,
               "added_to_eco": incoming, "pruned_from_eco": pruned,
               "terminal_failures": failures, "prune_after": PRUNE_AFTER,
               "eco_models": new_model_ids, "changed": changed},
              f, indent=2, ensure_ascii=False)
print(f"probe done: {len(alive)}/{len(results)} alive, log={OUT}")
