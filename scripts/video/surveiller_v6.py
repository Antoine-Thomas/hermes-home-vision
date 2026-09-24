# -*- coding: utf-8 -*-
"""Watchdog d'un volet (template) : surveille le run LatentSync sans dependre d'une session.

Gabarit versionne : %LOCALAPPDATA%\\hermes\\scripts\\video\\surveiller_v6.py (depot git).
Copie executee par la tache planifiee Hermes (toutes les 15 min) : %LOCALAPPDATA%\\hermes\\scripts\\surveiller_v6.py
(pour un volet suivant : copier en surveiller_v7.py, passer VOLET a "7" et declarer la tache).

Ecrit son etat dans surveiller_v<VOLET>_state.json et n'envoie sur Telegram que ce qui merite
une alerte :

  - aucune progression depuis plus de 25 min  -> message d'alerte (max 1 par heure)
  - le processus LatentSync n'existe plus      -> message d'alerte (une fois)
  - sinon : battement toutes les 2 h (etat + avancement + estimation)

La progression est lue sur moniteur_<VOLET>_statut.json (tenu par le pipeline pendant l'etape f)
et, a defaut, sur la date de modification du log LatentSync.

Correctif 5 (volet 6) : l'assemblage final n'est plus lance par subprocess.run (qui bloquait le
tick cron, timeout 3600 s) mais par subprocess.Popen(..., DETACHED_PROCESS) ; la tache cron rend
la main immediatement et le suivi se fait sur le fichier final.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

VOLET = "6"
VID = os.environ.get("VIDEO_DIR", r"C:\Users\searc\AppData\Local\hermes\data\video_youtube")
DOSSIER = os.path.join(VID, "LatentSync", "tests", f"v4_talking_head_{VOLET}")
JOURNAL = os.path.join(DOSSIER, f"pipeline_latentsync_{VOLET}.log")
MONITEUR = os.path.join(DOSSIER, f"moniteur_{VOLET}_statut.json")
SORTIE = os.path.join(DOSSIER, f"sortie_latentsync_{VOLET}.mp4")
HF = os.path.join(DOSSIER, f"sortie_latentsync_{VOLET}_hf_a1.0.mp4")
RAPPORT = os.path.join(DOSSIER, f"RAPPORT_{VOLET}.md")
ASSEMBLE = os.path.join(VID, f"assemble_v{VOLET}.py")
LOG_ASSEMBLE = os.path.join(DOSSIER, f"assemble_{VOLET}.log")
FINAL = os.environ.get("SORTIE_VIDEO",
                       r"C:\Users\searc\Desktop\hermes tuto\tutotete20_jev_llmwiki.mp4")
ETAT = os.path.join(DOSSIER, f"surveiller_{VOLET}_state.json")
PIPELINE = os.path.join(VID, "pipeline_talkinghead.py")
PY_LATENTSYNC = os.path.join(VID, "LatentSync", "venv", "Scripts", "python.exe")
# SOURCE = nouveau cut 9 s, valable v6 et v7 (le rush tutotete19.mp4 de 19,12 s etait mal coupe :
# l'audit y trouvait une fenetre peu fiable). Le v6 et le v7 partagent donc le meme rush par defaut.
SOURCE = r"C:\Users\searc\Desktop\hermes tuto\tutotetenewcut.mp4"
AUDIO = r"C:\Users\searc\AppData\Local\hermes\data\xtts\audio_youtube_v6.wav"
ENV_HERMES = r"C:\Users\searc\AppData\Local\hermes\.env"
CHAT = "8956868107"
SEUIL_SILENCE = 25 * 60
SEUIL_BATTEMENT = 2 * 3600


def telegram(texte: str) -> bool:
    jeton = ""
    try:
        with open(ENV_HERMES, encoding="utf-8", errors="replace") as f:
            for ligne in f:
                if ligne.startswith("TELEGRAM_BOT_TOKEN="):
                    jeton = ligne.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    except OSError:
        return False
    if not jeton:
        return False
    donnees = urllib.parse.urlencode({"chat_id": CHAT, "text": texte}).encode()
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{jeton}/sendMessage",
                                   data=donnees, timeout=30) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def latentsync_vivant() -> bool:
    try:
        r = subprocess.run(["wmic", "process", "where", "name='python.exe'", "get", "CommandLine"],
                           capture_output=True, text=True, timeout=60)
    except Exception:  # noqa: BLE001
        return True  # on ne conclut pas a tort
    return "latentsync" in (r.stdout or "").lower()


def lit_moniteur():
    if not os.path.exists(MONITEUR):
        return {}
    try:
        with open(MONITEUR, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def lancer_assemblage_detache() -> None:
    """Correctif 5 : rend la main tout de suite, l'assemblage continue en arriere-plan."""
    with open(LOG_ASSEMBLE, "w", encoding="utf-8") as f:
        subprocess.Popen([sys.executable, ASSEMBLE], stdout=f, stderr=subprocess.STDOUT,
                         cwd=VID,
                         creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))


def main() -> int:
    maintenant = time.time()
    etat = {}
    if os.path.exists(ETAT):
        with open(ETAT, encoding="utf-8") as f:
            etat = json.load(f)

    if os.path.exists(HF):
        # Seule preuve que LatentSync a fini et que la greffe HF (etape g) est passee :
        # le RAPPORT est ecrit une premiere fois au demarrage du run, il ne sert pas de signal.
        # On enchaine alors l'assemblage final, en tache detachee (subprocess.run bloquait le
        # tick cron pendant 15-25 min et timeoutait a chaque passage : correctif 5).
        if os.path.exists(FINAL):
            if etat.get("assemble_fait") is not True:
                taille = os.path.getsize(FINAL) / 2 ** 20
                telegram(f"Volet {VOLET} : assemblage final termine\n{FINAL}\n{taille:.0f} Mo")
                etat["assemble_fait"] = True
                print(f"assemblage termine : {FINAL} ({taille:.0f} Mo)")
            else:
                print("assemblage deja fait", file=sys.stderr)
        elif etat.get("assemble_lance") is not True:
            print("pipeline termine : lancement de l'assemblage final en tache detachee",
                  file=sys.stderr)
            lancer_assemblage_detache()
            telegram(f"Volet {VOLET} : assemblage final lance en tache de fond\nsuivi : {LOG_ASSEMBLE}")
            etat["assemble_lance"] = True
        else:
            print("assemblage en cours (tache detachee)", file=sys.stderr)
        with open(ETAT, "w", encoding="utf-8") as f:
            json.dump(etat, f, ensure_ascii=False, indent=1)
        return 0

    mon = lit_moniteur()

    # Fin du run detache (le moniteur ecrit "fin") : relancer les etapes g a i, que le
    # pipeline n'enchaine pas lui-meme quand LatentSync part en tache de fond.
    if mon.get("fin") is not None and etat.get("hfi_lance") is not True:
        log = os.path.join(DOSSIER, f"etapes_hfi_{VOLET}.log")
        cmd = [PY_LATENTSYNC, PIPELINE, "--source", SOURCE, "--audio", AUDIO,
               "--volet", VOLET, "--depuis", "hf"]
        # en tache de fond : la greffe HF peut durer une heure, on ne bloque pas le tick du watchdog
        with open(log, "w", encoding="utf-8") as f:
            subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=VID,
                             creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        telegram(f"Volet {VOLET} : LatentSync termine, greffe HF / mesures / rapport lancees en tache "
                 f"de fond\nsuivi : {log}")
        etat["hfi_lance"] = True
        print(f"etapes hf/mesures/rapport lancees : {log}", file=sys.stderr)

    ref = 0.0
    for p in (MONITEUR, JOURNAL, SORTIE):
        if os.path.exists(p):
            ref = max(ref, os.path.getmtime(p))
    if ref == 0.0:
        ref = maintenant  # rien encore produit : on ne crie pas
    avance = etat.get("avance", ref)
    if ref > avance:
        etat["avance"] = ref
    silence = maintenant - etat.get("avance", ref)

    resume = []
    if mon:
        for cle in ("frames_traitees", "frames_total", "pourcent", "eta", "debit",
                    "date", "phase", "statut"):
            if cle in mon:
                resume.append(f"{cle}={mon[cle]}")
    fichier_ok = os.path.exists(SORTIE)
    taille = os.path.getsize(SORTIE) / 2 ** 20 if fichier_ok else 0.0
    corps = (f"avancement : {' | '.join(resume) if resume else 'statut indisponible'}\n"
             f"derniere activite : il y a {silence/60:.0f} min\n"
             f"sortie : {'%.0f Mo' % taille if fichier_ok else 'pas encore ecrite'}")

    envoyer, motif = False, ""
    if silence > SEUIL_SILENCE:
        if maintenant - etat.get("derniere_alerte", 0) > 3600:
            envoyer, motif = True, f"ALERTE : aucune progression depuis {silence/60:.0f} min"
            etat["derniere_alerte"] = maintenant
    elif not latentsync_vivant() and silence > 10 * 60:
        if etat.get("alerte_mort") is not True:
            envoyer, motif = True, "ALERTE : plus de processus LatentSync et pas de sortie"
            etat["alerte_mort"] = True
    elif maintenant - etat.get("dernier_battement", 0) > SEUIL_BATTEMENT:
        envoyer, motif = True, f"battement volet {VOLET}"
        etat["dernier_battement"] = maintenant

    if envoyer:
        ok = telegram(f"{motif}\n{corps}")
        # stdout reste vide quand il n'y a rien a dire : la tache planifiee peut donc
        # livrer stdout sans spammer (mode no_agent : stdout vide = aucun message).
        print(f"{motif}\n{corps}\n(envoi Telegram : {'OK' if ok else 'ECHEC'})")
        print(f"envoi : {motif} -> {'OK' if ok else 'ECHEC'}", file=sys.stderr)
    else:
        print(f"silence {silence/60:.0f} min, rien a signaler", file=sys.stderr)

    with open(ETAT, "w", encoding="utf-8") as f:
        json.dump(etat, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
