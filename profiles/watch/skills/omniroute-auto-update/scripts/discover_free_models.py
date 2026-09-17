#!/usr/bin/env python3
"""Découvre et sonde les nouveaux modèles gratuits d'OmniRoute.

Lecture seule par défaut (--dry-run). Avec --apply, ajoute à la fin du combo
"eco" les modèles qui ont passé un probe réel (HTTP 200 + contenu non vide).

API réelle (vérifiée 2026-09-02):
  GET  /v1/models          -> {"data": [{"id": ...}, ...]}
  GET  /api/combos         -> {"combos": [...]}
  PUT  /api/combos/<id>    -> écriture (Bearer key requise)

Usage:
  python discover_free_models.py            # dry-run
  python discover_free_models.py --apply    # ajoute les modèles validés
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE = "http://127.0.0.1:20128"
ENV_PATH = Path.home() / ".omniroute" / ".env"
SKILL_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = SKILL_DIR / "backups"
VERDICT_PATH = SKILL_DIR / "references" / "model_verdicts.md"

# Préfixes de providers gratuits connus (le suffixe "-free" ou le provider
# entier signalent un candidat). La liste est volontairement conservative.
FREE_PROVIDER_PREFIXES = (
    "oc/",          # OpenCode (modèles -free)
    "auto/",        # auto-routing (Z.AI/DeepSeek-V3 alias gratuit)
    "cloudflare-ai/",
    "zc/",          # ZCode local (GLM-5.3 gratuit en preview, exige l'app)
    "opencode/",
    "pol/",         # Pollinations (souvent gated 401 désormais)
)
FREE_SUFFIX = "-free"

# Modèles déjà connus comme non fiables (verdicts passés).
KNOWN_BAD = {
    "oc/hy3-free",          # reasoning-only: vide le budget, content vide
    "oc/kimi-k3",           # 401 Missing API key
    "oc/deepseek-v4-flash-free",  # 400 broken
    "pol/openai",           # 401 (Pollinations gated)
    "auto/glm",             # 502/500 chain
}


def read_api_key() -> str:
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip().lower() in ("api_key", "omniroute_api_key", "token"):
            return v.strip().strip('"').strip("'")
    return ""


def http_json(path: str, key: str, method: str = "GET", body: dict | None = None):
    url = BASE + path
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {key}")
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode("utf-8")
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "replace")[:200]}
    except Exception as e:
        return 0, {"error": str(e)}


def list_model_ids(key: str) -> set[str]:
    code, payload = http_json("/v1/models", key)
    if code != 200:
        print(f"[!] GET /v1/models -> {code}: {payload.get('error', payload)}")
        return set()
    return {m.get("id", "") for m in payload.get("data", []) if m.get("id")}


def combo_model_ids(key: str) -> dict[str, list[str]]:
    code, payload = http_json("/api/combos", key)
    if code != 200:
        print(f"[!] GET /api/combos -> {code}: {payload.get('error', payload)}")
        return {}
    out: dict[str, list[str]] = {}
    for c in payload.get("combos", []):
        out[c.get("name", "?")] = [m.get("model", "") for m in c.get("models", [])]
    return out


def is_candidate(mid: str) -> bool:
    if mid in KNOWN_BAD:
        return False
    # Seuls les signaux fiables : suffixe "-free" OU alias auto gratuits connus.
    # Le préfixe "oc/" seul matche des centaines de modèles payants — on ne le
    # garde PAS comme critère (surcharge de probes = saturation des quotas).
    if mid.endswith(FREE_SUFFIX):
        return True
    return mid in ("auto/zai", "auto/gemini", "zc/glm-5.3")


def probe(key: str, mid: str) -> tuple[bool, str]:
    body = {
        "model": mid,
        "messages": [{"role": "user", "content": "réponds 'ok'"}],
        "max_tokens": 50,
        "stream": False,
    }
    code, payload = http_json("/v1/chat/completions", key, "POST", body)
    if code != 200:
        return False, f"HTTP {code}"
    try:
        content = payload["choices"][0]["message"].get("content")
    except (KeyError, IndexError):
        return False, "pas de choices[0].message.content"
    if not content or not str(content).strip():
        return False, "content vide"
    return True, str(content).strip()[:40]


def main() -> int:
    apply = "--apply" in sys.argv
    key = read_api_key()
    if not key:
        print("[!] Clé API introuvable dans ~/.omniroute/.env")
        return 1

    model_ids = list_model_ids(key)
    combos = combo_model_ids(key)
    already = {m for models in combos.values() for m in models}

    candidates = sorted(m for m in model_ids if is_candidate(m) and m not in already)
    print(f"[*] {len(model_ids)} modèles connus, {len(candidates)} candidats gratuits hors combo")

    verified: list[tuple[str, str]] = []
    verdicts: list[str] = []
    for mid in candidates:
        ok, info = probe(key, mid)
        status = "OK " if ok else "KO "
        verdicts.append(f"| {status} | `{mid}` | {info} |")
        print(f"    {status} {mid}  ({info})")
        if ok:
            verified.append((mid, info))
        time.sleep(1)  # ne pas saturer les quotas free

    # Journaliser les verdicts datés
    verdicts_header = ["| Verdict | Modèle | Détail |", "|---|---|---|"]
    VERDICT_PATH.parent.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M")
    block = f"\n\n## {stamp}\n" + "\n".join(verdicts_header + verdicts)
    with open(VERDICT_PATH, "a", encoding="utf-8") as f:
        f.write(block)

    print(f"\n[*] {len(verified)} modèle(s) validé(s) sur {len(candidates)} candidat(s)")

    if apply and verified:
        eco = [c for c in combos]  # trouver le combo eco
        code, payload = http_json("/api/combos", key)
        target = None
        for c in payload.get("combos", []):
            if c.get("name") == "eco":
                target = c
                break
        if target is None:
            print("[!] Combo 'eco' introuvable")
            return 1
        BACKUP_DIR.mkdir(exist_ok=True)
        bpath = BACKUP_DIR / f"eco-{int(time.time())}.json"
        bpath.write_text(json.dumps(target, indent=2), encoding="utf-8")
        print(f"[*] Sauvegarde: {bpath}")

        existing = {m.get("model") for m in target.get("models", [])}
        for mid, _ in verified:
            if mid in existing:
                continue
            target["models"].append({
                "id": f"eco-model-auto-{mid.replace('/', '-')}",
                "kind": "model",
                "model": mid,
                "providerId": mid.split("/", 1)[0],
                "weight": 0,
            })
        # Nettoyer les champs que l'API rejette au PUT
        for field in ("createdAt", "updatedAt", "version", "repairNote",
                      "computed_context_length", "isActive", "isHidden",
                      "sortOrder"):
            target.pop(field, None)
        code, resp = http_json(f"/api/combos/{target['id']}", key, "PUT", target)
        print(f"[*] PUT /api/combos/{target['id']} -> {code}")
        if code not in (200, 204):
            print(f"    {resp}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
