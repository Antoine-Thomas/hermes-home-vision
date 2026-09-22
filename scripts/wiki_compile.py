#!/usr/bin/env python3
"""Job cron « LLM Wiki compile » — SCRIPT SEUL, sans agent.

Un run d'agent pour la compilation du wiki ne peut pas aboutir :
  - le prompt systeme fait ~16 K tokens (index des skills, schemas d'outils) a
    CHAQUE tour, ce qui epuise les paliers gratuits en debit/minute ;
  - les runs cron ont un interrupt dur de 3 minutes, or une compilation en
    plusieurs tours (lecture -> ecriture -> index -> log) prend davantage.
Resultat mesure : le run meurt en boucle (429/504/`requestQueue.maxWaitMs`) ou
part sur le modele payant.

Ce lanceur appelle le script canonique du wiki, qui fait TOUT en un seul appel
LLM et sans agent : `%LOCALAPPDATA%\\hermes\\wiki\\scripts\\compile_wiki.py`.

Le script est enregistre cote cron par `hermes cron edit <id> --script
wiki_compile.py --no-agent` : le champ `script` est resolu sous
`%LOCALAPPDATA%\\hermes\\scripts\\`, d'ou ce fichier. Le cron capture sa sortie
standard (timeout par defaut : 3600 s).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERMES = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "hermes"
SCRIPT = HERMES / "wiki" / "scripts" / "compile_wiki.py"

# --rounds/--gap : les routes gratuites saturent par fenetres courtes ; 4 tours
# espaces de 120 s couvrent un cooldown sans bloquer le tick suivant.
CMD = [sys.executable, str(SCRIPT), "--rounds", "4", "--gap", "120",
       "--timeout", "900", "--max-tokens", "16000"]


def main() -> int:
    if not SCRIPT.is_file():
        print("ERREUR : script de compilation introuvable : %s" % SCRIPT, file=sys.stderr)
        return 2
    proc = subprocess.run(CMD, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=3000)
    print(proc.stdout, end="")
    if proc.stderr.strip():
        print(proc.stderr, end="", file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
