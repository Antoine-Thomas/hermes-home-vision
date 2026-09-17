#!/usr/bin/env python3
"""Wrapper cron pour la découverte des nouvelles IA gratuites OmniRoute.

Exécute discover_free_models.py en dry-run et imprime un résumé lisible
(sortie injectée comme contexte du job, ou délivrée telle quelle en no_agent).
"""
import subprocess
import sys
from pathlib import Path

SKILL_SCRIPT = (
    Path.home()
    / "AppData/Local/hermes/skills/omniroute-auto-update/scripts/discover_free_models.py"
)

def main() -> int:
    if not SKILL_SCRIPT.exists():
        print(f"[!] Script introuvable: {SKILL_SCRIPT}")
        return 1
    r = subprocess.run(
        [sys.executable, str(SKILL_SCRIPT), "--apply"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    out = r.stdout.strip()
    # Résumé concis : lignes OK uniquement + total
    lines = out.splitlines()
    ok_lines = [ln for ln in lines if ln.strip().startswith(("    OK", "    KO"))]
    summary = [ln for ln in lines if ln.strip().startswith("[*]")]
    print("\n".join(summary))
    if ok_lines:
        print("\n".join(ok_lines))
    if r.returncode != 0:
        print(r.stderr.strip()[-500:])
        return r.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
