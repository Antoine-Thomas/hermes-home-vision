"""Helper Jev (TypeSafe System One) pour Hermes — routé via OpenRouter.

Route   : https://openrouter.ai/api/v1/systemone
          (contrat vérifié sur https://openrouter.ai/docs/guides/community/typesafe-sdk)
Modèle  : typesafe/jev-1.13 — l'ID nu "jev-1.13" est aussi accepté (mappé par
          OpenRouter sur le namespace typesafe/). La réponse porte un ID daté,
          ex. "typesafe/jev-1.13-20260917".
Clé     : OPENROUTER_API_KEY — variable d'environnement d'abord, sinon
          %LOCALAPPDATA%\\hermes\\.env. La clé n'est jamais journalisée.

Usage :
    from jev_helper import jev, noul, choice, score
    r = noul("My payouts have failed for 3 days.",
             "is_urgent", "Is this urgent?")
    print(r["answers"], r["usage"], r["_elapsed_s"])

    python jev_helper.py          # auto-test des 3 primitives
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = "https://openrouter.ai/api/v1/systemone"
DEFAULT_MODEL = "typesafe/jev-1.13"
TIMEOUT = 30
ENV_FILE = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / ".env"

# Primaire/falbacks Hermes (config.yaml) — Jev ne les remplace jamais :
#   primary  : deepseek-flash (deepseek)         payant
#   fallback : omniroute/eco + omniroute/nvidia-stack (gratuit)


def _key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:].lstrip()
            if line.startswith("OPENROUTER_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val
    raise RuntimeError("OPENROUTER_API_KEY introuvable (env, puis %s)" % ENV_FILE)


def jev(state, questions, model: str = DEFAULT_MODEL, timeout: int = TIMEOUT) -> dict:
    """Évalue `state` contre des questions typées.

    Args:
        state: texte ou objet JSON-sérialisable (dict/liste) décrivant la situation.
        questions: {id: {"type": "noul|choice|score", "instructions": str, "criteria": ...}}
                   noul  -> pas de criteria (criteria optionnel {true:..., false:...})
                   choice-> criteria: {option: description}
                   score -> criteria: [niveau0, niveau1, ...] (ordonné)
        model: ID OpenRouter (défaut typesafe/jev-1.13).
        timeout: secondes.

    Returns:
        {"model": ..., "answers": {...}, "usage": {...}, "_elapsed_s": float}
        noul  -> {"type": "noul",  "noul": 0.98}
        choice-> {"type": "choice","choice": "<option>", ...}
        score -> {"type": "score", "score": 1.05, ...}
    """
    payload = json.dumps(
        {"model": model, "state": state, "questions": questions}
    ).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={
            "Authorization": "Bearer " + _key(),
            "Content-Type": "application/json",
        },
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError("Jev HTTP %s: %s" % (exc.code, detail)) from None
    except urllib.error.URLError as exc:
        raise RuntimeError("Jev injoignable: %s" % exc.reason) from None
    out["_elapsed_s"] = round(time.perf_counter() - start, 3)
    return out


def noul(state, qid, instructions, criteria=None, **kw) -> dict:
    """Probabilité yes/no (0-1). Un noul par étiquette quand plusieurs peuvent être vraies."""
    q = {"type": "noul", "instructions": instructions}
    if criteria:
        q["criteria"] = criteria
    return jev(state, {qid: q}, **kw)


def choice(state, qid, instructions, options, **kw) -> dict:
    """Choix d'une option parmi N. `options`: {option: description}."""
    return jev(state, {qid: {"type": "choice", "instructions": instructions,
                             "criteria": options}}, **kw)


def score(state, qid, instructions, levels, **kw) -> dict:
    """Note sur une échelle ordonnée. `levels`: liste de niveaux, du plus bas au plus haut."""
    return jev(state, {qid: {"type": "score", "instructions": instructions,
                             "criteria": list(levels)}}, **kw)


def _main() -> int:
    ticket = "Help! My payouts are failing for 3 days. This is blocking my business."
    print("state :", ticket)
    print("modele:", DEFAULT_MODEL)
    r1 = noul(ticket, "is_urgent", "Is this urgent for the sender?")
    r2 = choice(ticket, "dept", "Which team should handle this?",
                {"billing": "Payments, charges and payouts", "tech": "Bugs and outages"})
    r3 = score(ticket, "frustration", "How frustrated is the sender?",
               ["Calm", "Frustrated", "Very angry"])
    for label, r in (("noul", r1), ("choice", r2), ("score", r3)):
        print("%-6s -> %-60s %ss  cout=%s" % (
            label, json.dumps(r.get("answers"), ensure_ascii=False),
            r["_elapsed_s"], r.get("usage", {}).get("cost")))
    print("modeles servis :", r1.get("model"), "|", r2.get("model"), "|", r3.get("model"))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
