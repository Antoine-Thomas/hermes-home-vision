# -*- coding: utf-8 -*-
"""Point de reprise du run LatentSync v5.

Ecrit un instantane de l'etat du run (progression reelle, PID, VRAM, evenements)
dans un JSON, pour pouvoir diagnostiquer ou relancer sans dependre de la session
Hermes ni du moniteur.

Lecture seule sur le run.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime

BASE = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\LatentSync"
LOG = BASE + r"\tests\v4_talking_head_v5}\latentsync_v5_run.log"
STATUT = BASE + r"\tests\v4_talking_head_v5}\moniteur_v5_statut.json"
SORTIE = BASE + r"\tests\v4_talking_head_v5\sortie_latentsync_v5.mp4"
SOURCE = BASE + r"\tests\v4_talking_head_v3\source_v5_loop_344.mp4"
AUDIO = r"C:\Users\searc\AppData\Local\hermes\data\xtts\audio_youtube_v5.wav"
POINT = r"C:\Users\searc\AppData\Local\hermes\scripts\point_reprise_v5.json"
PID_LATENTSYNC = 17476

RE_BARRE = re.compile(
    r"Doing inference\.\.\.:\s+(\d+)%\|[^|]*\|\s*(\d+)/(\d+)\s*\[([^<\]]*)<([^,\]]*),\s*([\d.]+)s/it"
)


def commande() -> str:
    try:
        brut = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter \"ProcessId={PID_LATENTSYNC}\").CommandLine"],
            capture_output=True, text=True, encoding="cp1252", errors="replace", timeout=40,
        ).stdout.strip()
        return brut or "(processus absent)"
    except Exception as e:  # noqa: BLE001
        return f"(indisponible : {e})"


def derniere_barre() -> str:
    try:
        taille = os.path.getsize(LOG)
        with open(LOG, "rb") as f:
            f.seek(max(0, taille - 200_000))
            brut = f.read().decode("utf-8", errors="replace")
        for ligne in reversed([l for l in re.split(r"[\r\n]", brut) if "Doing inference" in l]):
            if RE_BARRE.search(ligne):
                return ligne.strip()
    except Exception:
        pass
    return "(indisponible)"


def vivant() -> bool:
    try:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {PID_LATENTSYNC}", "/NH"],
                             capture_output=True, text=True, encoding="cp1252",
                             errors="replace", timeout=25).stdout.lower()
        return "python" in out
    except Exception:
        return False


def statut_moniteur() -> dict:
    try:
        with open(STATUT, encoding="utf-8") as f:
            s = json.load(f)
        return {"phase": s.get("phase"), "pourcent": s.get("pourcent"),
                "vram_pic": s.get("vram_pic"), "temp_max": s.get("temp_max"),
                "maj": s.get("maj")}
    except Exception:
        return {}


def main() -> int:
    d = {
        "ecrit_le": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latentsync_pid": PID_LATENTSYNC,
        "latentsync_vivant": vivant(),
        "commande": commande(),
        "entrees": {"source": SOURCE, "audio": AUDIO},
        "sortie_attendue": SORTIE,
        "sortie_existe": os.path.exists(SORTIE),
        "sortie_octets": os.path.getsize(SORTIE) if os.path.exists(SORTIE) else 0,
        "derniere_barre_log": derniere_barre(),
        "log_octets": os.path.getsize(LOG) if os.path.exists(LOG) else 0,
        "log_mtime": (datetime.fromtimestamp(os.path.getmtime(LOG)).strftime("%Y-%m-%d %H:%M:%S")
                      if os.path.exists(LOG) else None),
        "moniteur": statut_moniteur(),
        "note": ("LatentSync ne fait pas de checkpoint : un arret impose de repartir du debut. "
                 "Ce point de reprise sert au diagnostic et au redemarrage, pas a la reprise "
                 "au milieu du calcul."),
    }
    with open(POINT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"point de reprise ecrit : {POINT}")
    print(f"  vivant        : {d['latentsync_vivant']}")
    print(f"  derniere barre: {d['derniere_barre_log'][:110]}")
    print(f"  sortie        : {'presente' if d['sortie_existe'] else 'absente'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
