#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Santé des combos chat OmniRoute — sonde nvidia-stack (sans consommer le quota gemini).

Sans LLM (no_agent). stdout = alerte (vide = rien à signaler).
- Sonde chaque combo via OmniRoute :20128 (127.0.0.1).
- Alerte sur TRANSITION up->down, retour à la normale sur down->up.
- Anti-spam : 1 alerte/combo/heure max.
- Aucun secret : la clé OmniRoute est lue depuis .env, jamais affichée.
- État : data/route_ia_fix/sante_combos.json
"""
import json
import pathlib
import time
import urllib.error
import urllib.request

HERMES = pathlib.Path(r"C:\Users\searc\AppData\Local\hermes")
ETAT = HERMES / "data" / "route_ia_fix" / "sante_combos.json"
OMNI = "http://127.0.0.1:20128/v1/chat/completions"
COMBOS = ["nvidia-stack"]
ANTI_SPAM_S = 3600


def env_key(name):
    try:
        for l in (HERMES / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
            if l.startswith(name + "="):
                return l.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


def probe(combo, key, timeout=40):
    body = json.dumps({"model": combo,
                       "messages": [{"role": "user", "content": "Réponds exactement: pong"}],
                       "max_tokens": 10}).encode()
    req = urllib.request.Request(OMNI, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if key:
        req.add_header("Authorization", "Bearer " + key)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return "200"
    except urllib.error.HTTPError as e:
        return str(e.code)
    except Exception as e:
        return "ERR"


def main():
    now = time.time()
    key = env_key("OMNIROUTE_API_KEY")

    st = {}
    if ETAT.exists():
        try:
            st = json.loads(ETAT.read_text(encoding="utf-8"))
        except Exception:
            st = {}

    messages = []
    for combo in COMBOS:
        code = probe(combo, key)
        prev = st.get(combo, {})
        was_up = prev.get("up", True)
        is_up = (code == "200")
        last_alert = prev.get("last_alert_ts", 0.0)

        entry = {"up": is_up, "last_alert_ts": last_alert, "last_code": code,
                 "checked_at": now}
        if is_up and not was_up:
            # retour à la normale
            messages.append("✓ combo %s rétabli (200)" % combo)
            entry["last_alert_ts"] = 0.0
        elif not is_up and was_up:
            # transition up -> down : alerte (anti-spam 1/h)
            if now - last_alert >= ANTI_SPAM_S:
                messages.append("⚠️ combo %s INJOIGNABLE via OmniRoute (HTTP %s)" % (combo, code))
                entry["last_alert_ts"] = now
        elif not is_up and not was_up:
            # toujours down : rappel seulement si l'anti-spam le permet
            if now - last_alert >= ANTI_SPAM_S:
                messages.append("⚠️ combo %s toujours INJOIGNABLE (HTTP %s)" % (combo, code))
                entry["last_alert_ts"] = now
        st[combo] = entry

    ETAT.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    if messages:
        print("Santé combos OmniRoute · %s\n%s" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                                   "\n".join(messages)))


if __name__ == "__main__":
    main()
