#!/usr/bin/env python3
"""Protocole de mesure E2E pour un bridge MARI (Signal -> Porte -> Trigger -> Sequence).

Run 1 : N iterations, 2 POST espaces de DELAY_BETWEEN_SIGNALS s -> N declenchements attendus.
Run 2 : N iterations, 1 seul POST -> 0 declenchement attendu.
Latence : timestamp de la ligne journal (horodatee ISO) - instant du POST #2.

Python 3 pur (urllib uniquement). Sortie : JSON + stdout.

Usage :
    python measure_protocol.py [--run1 N] [--run2 N]

Pre-requis : un E2E minimal a deja passe (2 signaux -> 1 ligne journal),
le bridge tourne, journal.log vide ou a une ligne de reference connue.

Gardefou : un lock fichier (msvcrt, Windows) refuse un SECOND processus
concurrent — deux e1crivains sur journal.log corrompent les mesures
(latences negatives). Le lock est relache en fin de run ou au kill.
"""
import argparse
import json
import msvcrt
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

# --- Configuration (adapter au POC) ---
BRIDGE = "http://127.0.0.1:55553/fire"
JOURNAL = r"C:/mari-poc/journal/journal.log"
SIGNAL_A = "rag-slow"
SIGNAL_B = "cpu-high"
DELAY_BETWEEN_SIGNALS = 60   # s ; doit etre < fenetre de la porte
WINDOW_PURGE = 300           # s ; purge fenetre porte entre les runs
POLL_TIMEOUT = 10            # s ; attente max de la ligne journal apres POST #2
OUTPUT = r"C:/mari-poc/RESULTATS_PHASE3.json"
LOCK_FILE = r"C:/mari-poc/.run_protocol.lock"


class SingleInstanceLock:
    """Lock fichier non bloquant (Windows). Exit(2) si un autre run est actif."""
    def __init__(self, path):
        self._fd = os.open(path, os.O_CREAT | os.O_RDWR)
        try:
            msvcrt.locking(self._fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            os.close(self._fd)
            print(f"ABORT: un autre run est actif (lock {path})", flush=True)
            sys.exit(2)
        # le lock survit au process : ecrire notre PID pour le diagnostic
        os.ftruncate(self._fd, 0)
        os.write(self._fd, str(os.getpid()).encode())
        os.lseek(self._fd, 0, os.SEEK_SET)

    def release(self):
        try:
            msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
        finally:
            os.close(self._fd)


def fire(signal_name):
    body = json.dumps({"fireId": signal_name, "sourceId": "hermes"}).encode()
    req = urllib.request.Request(BRIDGE, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status


def journal_lines():
    try:
        with open(JOURNAL, "r", encoding="utf-8") as f:
            return f.read().splitlines()
    except FileNotFoundError:
        return []


def parse_ts(line):
    try:
        start = line.index("[") + 1
        end = line.index("]", start)
        dt = datetime.fromisoformat(line[start:end].replace("Z", "+00:00"))
        return dt.timestamp() * 1000
    except Exception:
        return None


def run1_one_iteration():
    n0 = len(journal_lines())
    fire(SIGNAL_A)
    time.sleep(DELAY_BETWEEN_SIGNALS)
    t_post_b = time.time() * 1000
    fire(SIGNAL_B)
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        lines = journal_lines()
        if len(lines) > n0:
            for ln in lines[n0:]:
                ts = parse_ts(ln)
                if ts is not None:
                    # latence negative = ligne ecrite par un AUTRE processus (concurrence)
                    return True, ts - t_post_b, len(lines) - n0
            break
        time.sleep(0.2)
    return False, None, len(journal_lines()) - n0


def run2_one_iteration():
    n0 = len(journal_lines())
    fire(SIGNAL_B)  # un seul signal : la porte ne doit PAS se declencher
    time.sleep(3)
    return len(journal_lines()) - n0


def main():
    lock = SingleInstanceLock(LOCK_FILE)
    try:
        ap = argparse.ArgumentParser()
        ap.add_argument("--run1", type=int, default=50)
        ap.add_argument("--run2", type=int, default=50)
        args = ap.parse_args()

        results = {"run1": {"success": 0, "total": args.run1, "latencies_ms": [], "anomalies": []},
                   "run2": {"unexpected": 0, "total": args.run2, "anomalies": []}}

        print(f"RUN 1 : {args.run1} x 2 signaux ({DELAY_BETWEEN_SIGNALS}s) ...", flush=True)
        for i in range(args.run1):
            ok, lat, delta = run1_one_iteration()
            if ok:
                results["run1"]["success"] += 1
                results["run1"]["latencies_ms"].append(round(lat, 1))
            else:
                results["run1"]["anomalies"].append({"iter": i, "nouvelles_lignes": delta})
            print(f"  iter {i+1}/{args.run1} : {'OK' if ok else 'ECHEC'} lat={lat}", flush=True)

        print(f"PURGE fenetre {WINDOW_PURGE}s ...", flush=True)
        time.sleep(WINDOW_PURGE)

        print(f"RUN 2 : {args.run2} x 1 signal ...", flush=True)
        for i in range(args.run2):
            delta = run2_one_iteration()
            if delta > 0:
                results["run2"]["unexpected"] += 1
                results["run2"]["anomalies"].append({"iter": i, "nouvelles_lignes": delta})
            print(f"  iter {i+1}/{args.run2} : {delta} declenchement(s)", flush=True)

        lats = results["run1"]["latencies_ms"]
        results["run1"]["median_ms"] = round(sorted(lats)[len(lats) // 2], 1) if lats else None
        results["run1"]["max_ms"] = round(max(lats), 1) if lats else None
        results["run1"]["min_ms"] = round(min(lats), 1) if lats else None
        results["run1"]["avg_ms"] = round(sum(lats) / len(lats), 1) if lats else None
        results["timestamp"] = datetime.now(timezone.utc).isoformat()

        with open(OUTPUT, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"TERMINE -> {OUTPUT}", flush=True)
    finally:
        lock.release()


if __name__ == "__main__":
    main()
