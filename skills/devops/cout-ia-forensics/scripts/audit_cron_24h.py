#!/usr/bin/env python
"""Audit LECTURE SEULE des jobs cron Hermes sur une fenetre glissante.

Usage:
    python audit_cron_24h.py [heures] [filtre_job ...]

Par defaut 24 h, tous les jobs. Un filtre est un fragment d'id ou de nom de job.
Source : cron/executions.db sous %LOCALAPPDATA%\hermes (ou $HOME/hermes).
Sortie par job : nombre de runs, statuts, livraisons (delivered / suppressed / failed),
liste horodatee des alertes livrees, anomalies. Aucune ecriture.

Pourquoi ce script : `cron/output/<job_id>/` est rotationne (~50 fichiers, ~13 h) et le fichier
d'etat d'une sonde est un instantane — aucun des deux ne repond a « depuis N h ». Les horodatages
de `executions.db` sont des TEXT naifs : un filtre de temps en SQL matche TOUT, d'ou le parsing
en Python ci-dessous.
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib
import sqlite3
import sys
from collections import Counter

HERMES = pathlib.Path(os.environ.get("LOCALAPPDATA") or pathlib.Path.home()) / "hermes"
DB = HERMES / "cron" / "executions.db"
JOBS = HERMES / "cron" / "jobs.json"
FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
)


def parse_ts(value):
    """Horodatage naif -> datetime (ne JAMAIS comparer ces chaines en SQL)."""
    text = str(value)[:26]
    for fmt in FORMATS:
        try:
            return datetime.datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def connect(path):
    """Read-only : mode=ro via as_uri (un chemin brut a antislashs casse l'URI)."""
    return sqlite3.connect(pathlib.Path(path).as_uri() + "?mode=ro", uri=True)


def job_names():
    if not JOBS.exists():
        return {}
    raw = json.loads(JOBS.read_text(encoding="utf-8"))
    jobs = raw.get("jobs", raw) if isinstance(raw, dict) else raw
    jobs = list(jobs.values()) if isinstance(jobs, dict) else jobs
    return {str(j.get("id")): str(j.get("name")) for j in jobs}


def main(argv):
    hours = 24.0
    if argv and argv[0].replace(".", "", 1).isdigit():
        hours = float(argv.pop(0))
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
    names = job_names()

    con = connect(DB)
    cur = con.cursor()
    cur.execute("SELECT job_id, finished_at, status, delivery_outcome, error FROM executions")
    rows = cur.fetchall()
    con.close()

    per_job = {}
    for job_id, finished, status, delivery, error in rows:
        ts = parse_ts(finished)
        if ts is None or ts < cutoff:
            continue
        per_job.setdefault(str(job_id), []).append((ts, status, delivery, error))

    if not per_job:
        print("aucun run dans les %g dernieres heures" % hours)
        return 1

    shown = 0
    for job_id in sorted(per_job, key=lambda k: -len(per_job[k])):
        label = names.get(job_id, "?")
        if argv and not any(a in job_id or a.lower() in label.lower() for a in argv):
            continue
        shown += 1
        runs = per_job[job_id]
        print("\n%s (%s) — %d runs sur %gh" % (label, job_id, len(runs), hours))
        print("  statut    : %s" % dict(Counter(r[1] for r in runs)))
        print("  livraison : %s" % dict(Counter(r[2] for r in runs)))
        delivered = sorted(r[0] for r in runs if r[2] == "delivered")
        print("  alertes parties (%d) :" % len(delivered))
        for ts in delivered:
            print("     %s" % ts.strftime("%d/%m %H:%M:%S"))
        for ts, status, _delivery, error in runs:
            if status != "completed" or error:
                print("  ANOMALIE %s %s %s" % (ts.strftime("%d/%m %H:%M:%S"), status, str(error)[:120]))

    if not shown:
        print("aucun job ne correspond au filtre %s" % " ".join(argv))
        return 1
    print("\nRappel : cron/output/<job_id>/ est rotationne (~50 fichiers) — ne pas y repondre "
          "\u00ab depuis Nh \u00bb, et un job `paused` en cours de route garde last_status=ok.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
