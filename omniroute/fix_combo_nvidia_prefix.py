#!/usr/bin/env python3
"""Corrige le combo OmniRoute 'nvidia-stack' : prefixe 'openai/' sur les 3 modeles Nemotron.

Pourquoi : OmniRoute resout le provider par le PREFIXE du nom de modele, pas par le champ
providerId. Les entrees 'nvidia/nemotron-*' partaient donc vers un provider 'nvidia' inexistant
-> 401 "No active credentials for provider: nvidia" (et 502 en appel par nom de combo).
Le proxy NIM (127.0.0.1:20200) attend la forme 'openai/nvidia/...' : il retire le prefixe
'openai/' avant de relayer vers https://integrate.api.nvidia.com/v1.

Idempotent : ne touche que les entrees sans prefixe 'openai/'. Backup JSON avant ecriture.
Ne touche a AUCUN autre combo (le combo 'eco', defaut Hermes, n'est pas concerne).
"""
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

API = "http://127.0.0.1:20128"
COMBO_ID = "af0fde1e-a2df-4ed8-89bf-201566be74c9"
COMBO_NAME = "nvidia-stack"
ENV = pathlib.Path(os.environ["LOCALAPPDATA"]) / "hermes" / ".env"
BK_DIR = pathlib.Path.home() / ".omniroute" / "backups"


def api_key() -> str:
    for line in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("OMNIROUTE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("[!] OMNIROUTE_API_KEY introuvable dans .env")


KEY = api_key()


def req(method: str, path: str, payload=None, timeout: int = 30):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return resp.status, (json.loads(body) if body.strip() else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def show(combo: dict) -> list:
    return [(m.get("id"), m.get("model"), m.get("providerId")) for m in combo.get("models", [])]


status, before = req("GET", f"/api/combos/{COMBO_ID}")
if status != 200 or not isinstance(before, dict):
    sys.exit(f"[!] GET /api/combos/{COMBO_ID} -> HTTP {status} : {before}")

print(f"[avant] {COMBO_NAME} :")
for e in show(before):
    print(f"    id={e[0]}  model={e[1]}  providerId={e[2]}")

BK_DIR.mkdir(parents=True, exist_ok=True)
bk = BK_DIR / f"combo_api_{time.strftime('%Y%m%d_%H%M%S')}.json"
bk.write_text(json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[backup] {bk}")

changed = []
for m in before.get("models", []):
    mid = m.get("model", "")
    if mid.startswith("nvidia/"):
        changed.append((mid, "openai/" + mid))
        m["model"] = "openai/" + mid

if not changed:
    print("[ok] idempotent : toutes les entrees portent deja le prefixe 'openai/'. Rien a faire.")
    sys.exit(0)

print("[diff]")
for a, b in changed:
    print(f"    - {a}")
    print(f"    + {b}")

status, resp = req("PUT", f"/api/combos/{COMBO_ID}", before)
print(f"[PUT] HTTP {status}")
if status not in (200, 201, 204):
    sys.exit(f"[!] echec du PUT, rien n'a ete modifie cote API : {str(resp)[:400]}")

status, after = req("GET", f"/api/combos/{COMBO_ID}")
print(f"[apres] {COMBO_NAME} :")
for e in show(after):
    print(f"    id={e[0]}  model={e[1]}  providerId={e[2]}")

ok = all(m.get("model", "").startswith("openai/") for m in after.get("models", []))
print("[verif] tous les modeles prefixes 'openai/' :", ok)
sys.exit(0 if ok else 1)
