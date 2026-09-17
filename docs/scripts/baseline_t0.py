#!/usr/bin/env python3
"""Baseline T0 du parc Hermes — mesure l'etat reel et ecrit snapshot/baseline_T0.json.

Usage : python baseline_t0.py [chemin_sortie]
Le fichier produit est la reference comparee par scripts/verif_24h.ps1.
Aucune ecriture ailleurs : lecture seule (HTTP local + fichiers d'etat).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ["LOCALAPPDATA"]) / "hermes"
OUT_DEFAULT = Path(__file__).resolve().parent.parent / "snapshot" / "baseline_T0.json"
TIMEOUT = 8


def http_code(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def http_json(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return {}


def siyuan_token() -> str:
    env = HOME / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            if line.startswith("SIYUAN_TOKEN="):
                return line.split("=", 1)[1].strip()
    conf = Path(r"C:\Users\searc\SiYuan\hermes-projects\conf\conf.json")
    if conf.is_file():
        try:
            return json.loads(conf.read_text(encoding="utf-8"))["api"]["token"]
        except Exception:
            pass
    return ""


def siyuan_notebooks() -> dict:
    tok = siyuan_token()
    if not tok:
        return {"code": None, "notebooks": 0, "ids": [], "error": "no_token"}
    req = urllib.request.Request(
        "http://127.0.0.1:6806/api/notebook/lsNotebooks",
        data=b"{}",
        headers={"Authorization": f"Token {tok}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"code": None, "notebooks": 0, "ids": [], "error": str(e)[:80]}
    nbs = (d.get("data") or {}).get("notebooks") or []
    return {
        "code": d.get("code"),
        "notebooks": len(nbs),
        "ids": [n.get("id") for n in nbs],
        "names": [n.get("name") for n in nbs],
    }


def gateway(name: str) -> dict:
    path = HOME / ("" if name == "default" else f"profiles/{name}") / "gateway_state.json"
    if not path.is_file():
        return {"state": "absent"}
    try:
        d = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as e:
        return {"state": "unreadable", "error": str(e)[:60]}
    # gateway_state.json garde des entrees de plateformes PERIMEES (ex. "email" reste liste
    # apres le retrait du credential) : le nombre de plateformes REELLEMENT servies se lit dans
    # le log ("Gateway running with N platform(s)"). Ne jamais conclure sur state_platforms seul.
    log = HOME / ("" if name == "default" else f"profiles/{name}") / "logs" / "gateway.log"
    served = None
    if log.is_file():
        txt = log.read_text(encoding="utf-8", errors="replace")
        hits = re.findall(r"Gateway running with (\d+) platform", txt)
        served = int(hits[-1]) if hits else None
    return {
        "state": d.get("gateway_state"),
        "pid": d.get("pid"),
        "state_platforms": sorted((d.get("platforms") or {}).keys()),
        "log_platforms_served": served,
        "code_version": d.get("code_version"),
    }


def cron_veille() -> dict:
    try:
        out = subprocess.run(
            ["hermes", "-p", "veille", "cron", "list"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90,
        ).stdout
    except Exception as e:
        return {"error": str(e)[:80]}
    m_id = re.search(r"^\s+([0-9a-f]{12})\s+\[(\w+)\]", out, re.M)
    m_next = re.search(r"Next run:\s+(\S+)", out)
    m_last = re.search(r"Last run:\s+(\S+)\s+(\S+)", out)
    return {
        "job_id": m_id.group(1) if m_id else None,
        "status": m_id.group(2) if m_id else None,
        "next_run": m_next.group(1) if m_next else None,
        "last_run": m_last.group(1) if m_last else None,
    }


def healthcheck_task() -> dict:
    try:
        out = subprocess.run(
            ["schtasks", "/query", "/tn", "Hermes_Gateway_HealthCheck", "/fo", "LIST"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        ).stdout
    except Exception as e:
        return {"error": str(e)[:80]}
    m = re.search(r"Prochaine ex[^\s]*\s*:\s*(\S+\s+\S+)", out)
    s = re.search(r"Statut\s*:\s*(\S+)", out)
    return {
        "next_run": m.group(1) if m else None,
        "status": s.group(1) if s else None,
        "raw_ok": "Hermes_Gateway_HealthCheck" in out,
    }


def listening(port: int) -> bool:
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60).stdout
    except Exception:
        return False
    return any(f":{port} " in ln and "LISTENING" in ln.upper() for ln in out.splitlines())


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT_DEFAULT
    version = ""
    try:
        version = subprocess.run(["hermes", "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60).stdout.split("\n")[0]
    except Exception:
        pass
    snap = {
        "t0": datetime.now().astimezone().isoformat(timespec="seconds"),
        "hermes_version": version.strip(),
        "siyuan": siyuan_notebooks(),
        "rag": {**{"endpoint": "/sante", "http": http_code("http://127.0.0.1:8200/sante")}, **http_json("http://127.0.0.1:8200/sante")},
        "services": {p: http_code(f"http://127.0.0.1:{p}/") for p in (6806, 8200, 9119, 20128, 20200)},
        "gateways": {n: gateway(n) for n in ("default", "watch", "veille")},
        "cron_veille": cron_veille(),
        "healthcheck": healthcheck_task(),
        "a2a": {
            "port_9900_listening": listening(9900),
            "env_keys_present": sum(
                1 for f in (HOME / ".env", HOME / "profiles/watch/.env", HOME / "profiles/veille/.env")
                if f.is_file() and any(l.startswith("A2A_") for l in f.read_text(encoding="utf-8-sig", errors="replace").splitlines())
            ),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snap, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
    print(f"\n-> ecrit dans {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
