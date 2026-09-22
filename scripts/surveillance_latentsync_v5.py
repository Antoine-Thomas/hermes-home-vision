# -*- coding: utf-8 -*-
"""Watchdog LatentSync v5 - SILENCIEUX tant que tout va bien.

Sortie vide = rien n'est envoye (le moniteur principal notifie deja toutes les 30 min).
N'ecrit que si le run est en difficulte :
  - statut du moniteur trop vieux (moniteur ou run mort)
  - arret d'urgence enregistre
  - run termine (succes ou echec)
  - VRAM pic au-dessus du seuil, events GPU
  - GPU injoignable (driver tombe)

Concu pour un cron no_agent : la sortie est livree telle quelle.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime

D = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\LatentSync"
STATUT = os.path.join(D, "tests", "v4_talking_head_v5}", "moniteur_v5_statut.json")
SORTIE = os.path.join(D, "tests", "v4_talking_head_v5", "sortie_latentsync_v5.mp4")
SEUIL_VRAM = 8050
AGE_MAX = 12 * 60  # s sans mise a jour du statut avant alerte


def hm(s: float) -> str:
    s = max(0, int(s))
    return f"{s // 3600}h{(s % 3600) // 60:02d}"


def gpu() -> tuple[int, int]:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=20,
        ).stdout.strip().splitlines()[0]
        v, t = out.split(",")
        return int(v), int(t)
    except Exception:  # noqa: BLE001
        return -1, -1


alertes: list[str] = []
notes: list[str] = []

if not os.path.exists(STATUT):
    print("LatentSync v5 - WATCHDOG\nstatut du moniteur absent : le monitoring ne tourne pas.\n"
          f"attendu : {STATUT}")
    raise SystemExit(0)

try:
    s = json.load(open(STATUT, encoding="utf-8"))
except Exception as e:  # noqa: BLE001
    print(f"LatentSync v5 - WATCHDOG\nstatut illisible ({e}) : le moniteur est peut-etre mort en pleine ecriture.")
    raise SystemExit(0)

age = time.time() - datetime.strptime(s["maj"], "%Y-%m-%d %H:%M:%S").timestamp()
ecoule = (s.get("fin") or time.time()) - s["debut"]
vram_now, temp_now = gpu()

if vram_now < 0:
    alertes.append("GPU injoignable (nvidia-smi ne repond pas) : driver tombe ou reset.")
if age > AGE_MAX and not s.get("fin"):
    alertes.append(f"statut non mis a jour depuis {hm(age)} : moniteur ou run arrete "
                   f"(derniere phase : {s['phase']}, {s['pourcent']:.1f} %).")
if s.get("arret"):
    alertes.append(f"arret d'urgence enregistre : {s['arret']}")
if s.get("vram_pic", 0) > SEUIL_VRAM:
    alertes.append(f"VRAM pic {s['vram_pic']} Mio > {SEUIL_VRAM} Mio.")
if s.get("erreur"):
    alertes.append(f"erreur : {s['erreur']}")
if not s.get("fin") and s["phase"] in ("demarrage",) and ecoule > 3 * 3600:
    alertes.append(f"toujours en phase {s['phase']} apres {hm(ecoule)} : blocage probable.")

if s.get("fin"):
    fini = os.path.exists(SORTIE)
    notes.append(f"run termine (phase {s['phase']}) en {hm(ecoule)}")
    notes.append(f"VRAM pic {s['vram_pic']} Mio, temp max {s['temp_max']} C")
    notes.append(f"nvlddmkm 153 : {s['nvld_total']}   Kernel-Power 41 : {s['kernel_power']}")
    if fini:
        notes.append(f"sortie : {os.path.getsize(SORTIE) / 1e6:.1f} Mo -> {os.path.basename(SORTIE)}")
    else:
        alertes.append("le run est termine mais le fichier de sortie est absent !")

if not alertes and not notes:
    raise SystemExit(0)  # silencieux

lignes = ["LatentSync v5 - WATCHDOG"]
if alertes:
    lignes.append("")
    lignes += ["ALERTE : " + a for a in alertes]
if notes:
    lignes.append("")
    lignes += notes
lignes += [
    "",
    f"progression : {s['pourcent']:.1f} % ({s['avance']}/{s['total']})",
    f"phase       : {s['phase']}",
    f"ecoule      : {hm(ecoule)}",
    f"GPU         : {vram_now} Mio, {temp_now} C",
]
print("\n".join(lignes))
