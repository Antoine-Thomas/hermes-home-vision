#!/usr/bin/env python3
"""Veille OmniRoute : sonde ET ajoute automatiquement les nouveaux modèles
gratuits au combo eco, puis notifie (Telegram + local + popup) si ajout.

Sortie vide = aucune notification (watchdog pattern du cron no_agent).
"""
import subprocess
import sys

DISCOVER = r"C:\Users\searc\AppData\Local\hermes\skills\omniroute-auto-update\scripts\discover_free_models.py"

r = subprocess.run([sys.executable, DISCOVER, "--apply"],
                   capture_output=True, text=True, timeout=600)
out = r.stdout or ""

# Modèles validés = ajoutés au combo eco (lignes "    OK  <model>  (<info>)")
ok_models = []
for line in out.splitlines():
    s = line.strip()
    if s.startswith("OK "):
        rest = s[3:].strip()
        mid = rest.split("  (")[0].strip()
        if mid:
            ok_models.append(mid)

if ok_models:
    msg = "🆕 Nouvelles IA gratuites ajoutées au combo eco :\n"
    for m in ok_models:
        msg += f"• {m}\n"
    msg += "\nProbe réel OK, combo sauvegardé avant écriture."
    print(msg)

    # Popup local (best-effort, non bloquant, ignoré si indisponible)
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command",
             "Add-Type -AssemblyName System.Windows.Forms; "
             "[System.Windows.Forms.MessageBox]::Show("
             f"'{len(ok_models)} nouvelle(s) IA ajoutee(s) au combo eco',"
             "'Hermes - Veille IA')"],
            shell=False,
        )
    except Exception:
        pass
# sinon : stdout vide -> le cron n'envoie rien
