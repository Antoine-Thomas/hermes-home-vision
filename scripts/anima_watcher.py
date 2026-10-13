#!/usr/bin/env python3
"""ANIMA Watcher in real mode.

- Reads health_anima_state.json every 30s
- Tracks last_state per component
- Detects READY/DEGRADED -> FAILED (or BLOCKED) transitions
- On transition: POST /fire {"fireId":"anima-<component>-fail","sourceId":"anima-watcher"}
- Kill-switch: C:/mari-poc/DISABLE -> log DISABLED, exit
- Logs to C:/mari-poc/journal/watcher.log
"""

import json
import os
import time
import urllib.request
import urllib.error

STATE_FILE = "C:/Users/searc/AppData/Local/hermes/data/route_ia_fix/health_anima_state.json"
DISABLE_FILE = "C:/mari-poc/DISABLE"
FIRE_URL = "http://127.0.0.1:55553/fire"
WATCHER_LOG = "C:/mari-poc/journal/watcher.log"
CYCLE_SECONDS = 30


def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}\n"
    with open(WATCHER_LOG, "a", encoding="utf-8") as f:
        f.write(line)


def is_disabled():
    if os.path.exists(DISABLE_FILE):
        log("DISABLE file present — watcher exiting")
        return True
    return False


def read_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Extract component states: top-level keys with dict containing 'last_state'
        result = {}
        for comp, info in data.items():
            if isinstance(info, dict) and "last_state" in info:
                result[comp] = info["last_state"]
        return result
    except Exception as e:
        log(f"Error reading state: {e}")
        return {}


def post_fire(component, fire_id):
    payload = json.dumps({"fireId": fire_id, "sourceId": "anima-watcher"}).encode("utf-8")
    req = urllib.request.Request(FIRE_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        log(f"POST /fire error for {fire_id}: {e}")
        return None


def main():
    log("ANIMA Watcher started (real mode)")
    last_state = {}
    cycle = 0

    if is_disabled():
        return

    while True:
        if is_disabled():
            log("DISABLE detected during run — exiting")
            break

        cycle += 1
        state = read_state()
        transitions = []

        for component in state:
            new_val = state[component]
            old_val = last_state.get(component)

            # Detect READY/DEGRADED -> FAILED or BLOCKED
            if old_val and old_val in ("READY", "DEGRADED") and new_val in ("FAILED", "BLOCKED"):
                fire_id = f"anima-{component}-fail"
                transitions.append((component, fire_id))

        for component, fire_id in transitions:
            result = post_fire(component, fire_id)
            log(f"Transition {component}: {fire_id} -> POST result: {result}")

        summary = ", ".join(f"{k}={v}" for k, v in sorted(state.items())) if state else "state file vide"
        log(f"Cycle {cycle}: {summary}")
        last_state = state
        time.sleep(CYCLE_SECONDS)


if __name__ == "__main__":
    main()