# -*- coding: utf-8 -*-
"""Alertes Telegram du run LatentSync v5 - canal de secours.

Le moniteur principal (surveiller_latentsync_v5.py) a deux bugs qui rendent ses
notifications inutilisables :
  1. il envoie en parse_mode=HTML un texte contenant l'ETA de tqdm ("01:55<00:00"),
     le "<" brut est pris pour une balise et Telegram repond 400 ;
  2. il lit la derniere barre tqdm vue, qui est presque toujours "Sample frames: 16"
     (20 items) et non "Doing inference..." (538 items), donc il annonce 100 % a tort.

Ce script lit le LOG (source fiable) et n'ecrit QUE du texte sans chevrons, pour
que la livraison ne puisse pas casser. Il est concu pour un cron no_agent :
stdout vide = rien n'est envoye.

Lecture seule : ne touche ni au run ni au moniteur.
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

LOG = (r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\LatentSync"
       r"\tests\v4_talking_head_v5}\latentsync_v5_run.log")
STATUT = (r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\LatentSync"
          r"\tests\v4_talking_head_v5}\moniteur_v5_statut.json")
SORTIE = (r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\LatentSync"
          r"\tests\v4_talking_head_v5\sortie_latentsync_v5.mp4")
ETAT = r"C:\Users\searc\AppData\Local\hermes\scripts\alerte_v5_etat.json"

PID_LATENTSYNC = 17476
SEUIL_VRAM = 8050
GRAIN_POURCENT = 3          # message si +3 % depuis le dernier envoi
INTERVALLE_MAX = 2700       # ... ou si 45 min sans message
AGE_LOG_MAX = 900           # au-dela : le log ne bouge plus, on alerte

RE_BARRE = re.compile(
    r"Doing inference\.\.\.:\s+(\d+)%\|[^|]*\|\s*(\d+)/(\d+)\s*\[([^<\]]*)<([^,\]]*),\s*([\d.]+)s/it"
)


def lire_etat() -> dict:
    try:
        with open(ETAT, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def ecrire_etat(d: dict) -> None:
    try:
        with open(ETAT, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def progression() -> dict | None:
    """Derniere barre 'Doing inference' du log."""
    try:
        taille = os.path.getsize(LOG)
        with open(LOG, "rb") as f:
            f.seek(max(0, taille - 300_000))
            brut = f.read().decode("utf-8", errors="replace")
    except Exception:
        return None
    morceaux = [m for m in re.split(r"[\r\n]", brut) if "Doing inference" in m]
    for ligne in reversed(morceaux):
        m = RE_BARRE.search(ligne)
        if m:
            return {
                "pourcent": int(m.group(1)), "fait": int(m.group(2)),
                "total": int(m.group(3)), "ecoule": m.group(4).strip(),
                "restant": m.group(5).strip(), "vitesse": float(m.group(6)),
            }
    return None


def pid_vivant() -> bool:
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {PID_LATENTSYNC}", "/NH"],
            capture_output=True, text=True, encoding="cp1252", errors="replace", timeout=25,
        ).stdout.lower()
        return "python" in out
    except Exception:
        return True   # en cas de doute, ne pas crier au loup


def vram_pic() -> int | None:
    try:
        with open(STATUT, encoding="utf-8") as f:
            return int(json.load(f).get("vram_pic") or 0)
    except Exception:
        return None


def main() -> int:
    etat = lire_etat()
    maintenant = time.time()

    # 1. Termine ?
    if os.path.exists(SORTIE) and not etat.get("fin_annoncee"):
        mo = os.path.getsize(SORTIE) / 1e6
        print(f"LatentSync v5 TERMINE\nsortie : {os.path.basename(SORTIE)} ({mo:.0f} Mo)\n"
              f"prochaine etape : post-traitement HF, version 1080p, mesures, livraison.")
        etat["fin_annoncee"] = True
        etat["dernier_envoi"] = maintenant
        ecrire_etat(etat)
        return 0

    prog = progression()
    vivant = pid_vivant()

    # 2. Processus mort sans fichier de sortie
    if not vivant and not etat.get("arret_annonce"):
        p = f"derniere progression connue : {prog['pourcent']} % ({prog['fait']}/{prog['total']})" if prog else "log illisible"
        print(f"LatentSync v5 ARRETE sans fichier de sortie\n{p}\n"
              f"verifier le log puis relancer (voir point de reprise).")
        etat["arret_annonce"] = True
        etat["dernier_envoi"] = maintenant
        ecrire_etat(etat)
        return 0

    if not prog:
        return 0

    # 3. Log fige alors que le processus vit
    try:
        age = maintenant - os.path.getmtime(LOG)
    except Exception:
        age = 0
    if age > AGE_LOG_MAX and vivant and not etat.get("fige_annonce"):
        print(f"LatentSync v5 : log fige depuis {int(age/60)} min\n"
              f"progression : {prog['pourcent']} % ({prog['fait']}/{prog['total']})\n"
              f"processus encore vivant : verifier nvidia-smi.")
        etat["fige_annonce"] = True
        etat["dernier_envoi"] = maintenant
        ecrire_etat(etat)
        return 0
    if age <= AGE_LOG_MAX and etat.get("fige_annonce"):
        etat["fige_annonce"] = False

    # 4. Message de progression, throttle
    dernier_p = int(etat.get("dernier_pourcent") or 0)
    depuis = maintenant - float(etat.get("dernier_envoi") or 0)
    if prog["pourcent"] - dernier_p < GRAIN_POURCENT and depuis < INTERVALLE_MAX:
        ecrire_etat(etat)
        return 0

    vram = vram_pic()
    lignes = [
        f"LatentSync v5 : {prog['pourcent']} % ({prog['fait']}/{prog['total']})",
        f"cadence    : {prog['vitesse']:.0f} s/iteration",
        f"ecoule     : {prog['ecoule']}   restant : {prog['restant']}",
    ]
    if vram:
        lignes.append(f"VRAM pic   : {vram} Mio (seuil {SEUIL_VRAM})")
    lignes.append("")
    lignes.append("maj Windows en pause, redemarrage automatique bloque.")
    print("\n".join(lignes))

    etat["dernier_pourcent"] = prog["pourcent"]
    etat["dernier_envoi"] = maintenant
    ecrire_etat(etat)
    return 0


if __name__ == "__main__":
    sys.exit(main())
