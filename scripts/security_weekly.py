#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
security_weekly.py - Wrapper cron pour l'audit de securite hebdomadaire.

Appele par le job cron 'Audit securite hebdomadaire'. Sa sortie stdout est
injectee dans le prompt de l'agent (mode par defaut) ou livree verbatim
(mode no_agent=True).

Ne prend aucun argument : tout le perimetre vient de targets.json.
Ne leve jamais d'exception non geree : un wrapper cron qui plante en silence
est pire qu'un audit manquant.

Variante watchdog (zero token, silence si tout va bien) :
  ajouter "--quiet-if-clean" dans EXTRA_ARGS ci-dessous.
"""
import os
import subprocess
import sys

BASE = os.path.expanduser("~/AppData/Local/hermes/data/hermes-optim")
if not os.path.isdir(BASE):  # Linux / macOS
    BASE = os.path.expanduser("~/.hermes/data/hermes-optim")

SCANNER = os.path.join(BASE, "bin", "security_scan.py")
CONFIG = os.path.join(BASE, "targets.json")
VENV_PY = os.path.join(BASE, ".venv", "Scripts", "python.exe")
VENV_PY_POSIX = os.path.join(BASE, ".venv", "bin", "python")

EXTRA_ARGS = []  # ex: ["--quiet-if-clean"]


def pick_python():
    for cand in (VENV_PY, VENV_PY_POSIX):
        if os.path.isfile(cand):
            return cand
    return sys.executable


def main():
    if not os.path.isfile(SCANNER):
        print("ERREUR AUDIT : scanner introuvable -> %s" % SCANNER)
        print("Le job cron ne peut pas s'executer. Verifier le dossier hermes-optim.")
        return 0
    if not os.path.isfile(CONFIG):
        print("ERREUR AUDIT : perimetre introuvable -> %s" % CONFIG)
        return 0

    cmd = [pick_python(), SCANNER, "--config", CONFIG] + EXTRA_ARGS
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=900,
                           encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        print("ERREUR AUDIT : timeout apres 15 min. Reduire le perimetre dans targets.json")
        return 0
    except Exception as exc:
        print("ERREUR AUDIT : %s" % exc)
        return 0

    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()

    if out:
        print(out)
    if err:
        print("\n--- stderr ---")
        print(err[:1500])
    if not out and not err:
        print("Audit execute, aucune sortie (mode quiet-if-clean : rien a signaler).")

    print("\n[code de sortie scanner : %d  (0=ok, 1=eleve, 2=critique)]" % p.returncode)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
