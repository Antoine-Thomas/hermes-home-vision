# -*- coding: utf-8 -*-
"""Watchdog d'un volet (template) : surveille le run LatentSync sans dependre d'une session.

Gabarit versionne : %LOCALAPPDATA%\\hermes\\scripts\\video\\surveiller_v7.py (depot git).
Copie executee par la tache planifiee Hermes (toutes les 15 min) : %LOCALAPPDATA%\\hermes\\scripts\\surveiller_v7.py

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

Correctif 6 (volet 7) : plus d'echec silencieux en fin de run. Si le script d'assemblage manque,
si le nom du livrable n'est pas renseigne, ou si les incrustations manquent, le watchdog ALERTE
au lieu d'annoncer un assemblage lance. Le nom du livrable est une decision, pas une deduction.

Correctif 7 (volet 7) : mode « attente de validation ». Quand la greffe HF est terminee mais que
les incrustations manquent, le watchdog n'annonce plus un echec : il demande une validation.
  - un seul message explicite, puis rappel toutes les 2 h (silence entre les deux) ;
  - il lit la sentinelle validation_v<VOLET>.txt : « OK » -> il enchaine l'assemblage des que
    les fichiers sont la, « STOP » -> il se met en pause et le dit ;
  - apres 24 h sans reponse : derniere alerte puis auto-pause de la tache cron (hermes cron pause),
    avec repli sur un drapeau local si la commande echoue. Aucune boucle infinie.

Correctif 8 (volet 7) : la detection du processus LatentSync passe de wmic (retire de Windows 11,
sortie vide + code 0 -> l'alerte « processus mort » ne pouvait jamais partir) a
Get-CimInstance Win32_Process par PowerShell. Sortie non numerique = on ne conclut pas.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

VOLET = "7"
VID = os.environ.get("VIDEO_DIR", r"C:\Users\searc\AppData\Local\hermes\data\video_youtube")
DOSSIER = os.path.join(VID, "LatentSync", "tests", f"v4_talking_head_{VOLET}")
JOURNAL = os.path.join(DOSSIER, f"pipeline_latentsync_{VOLET}.log")
MONITEUR = os.path.join(DOSSIER, f"moniteur_{VOLET}_statut.json")
SORTIE = os.path.join(DOSSIER, f"sortie_latentsync_{VOLET}.mp4")
HF = os.path.join(DOSSIER, f"sortie_latentsync_{VOLET}_hf_a1.0.mp4")
RAPPORT = os.path.join(DOSSIER, f"RAPPORT_{VOLET}.md")
ASSEMBLE = os.path.join(VID, f"assemble_v{VOLET}.py")
LOG_ASSEMBLE = os.path.join(DOSSIER, f"assemble_{VOLET}.log")
TIMING = os.path.join(VID, f"overlay_timing_v{VOLET}.json")
OVERLAYS = os.path.join(VID, f"overlays_v{VOLET}")
# Sentinelle de validation : ecrite a la main (ou par l'agent) pour repondre au watchdog.
SENTINELLE = os.path.join(VID, f"validation_v{VOLET}.txt")
# Livrable final du volet 7 : fige ici ou surcharge par la variable d'environnement SORTIE_VIDEO.
# NE PAS pointer sur le livrable du volet 6 (tutotete20_jev_llmwiki.mp4) : le watchdog suivrait
# le mauvais fichier et le croirait deja assemble.
FINAL = os.environ.get(
    "SORTIE_VIDEO", r"C:\Users\searc\Desktop\hermes tuto\tutotete21_jev_llmwiki_hermes.mp4")
ETAT = os.path.join(DOSSIER, f"surveiller_{VOLET}_state.json")
PIPELINE = os.path.join(VID, "pipeline_talkinghead.py")
PY_LATENTSYNC = os.path.join(VID, "LatentSync", "venv", "Scripts", "python.exe")
SOURCE = r"C:\Users\searc\Desktop\hermes tuto\tutotete19.mp4"
AUDIO = r"C:\Users\searc\AppData\Local\hermes\data\xtts\audio_youtube_v6.wav"
ENV_HERMES = r"C:\Users\searc\AppData\Local\hermes\.env"
CLI_HERMES = os.environ.get(
    "HERMES_EXE", r"C:\Users\searc\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe")
# Tache cron de ce watchdog : sert a l'auto-pause apres 24 h sans reponse.
JOB_ID = os.environ.get("JOB_ID", "3d91e98f9608")
CHAT = "8956868107"
SEUIL_SILENCE = 25 * 60
SEUIL_BATTEMENT = 2 * 3600
SEUIL_RAPPEL_ATTENTE = 2 * 3600
SEUIL_ABANDON = 24 * 3600


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
    """Un processus LatentSync tourne-t-il ?

    Correctif 8 : wmic est retire de Windows 11 et renvoyait ici une sortie vide avec un code
    de retour 0, donc l'alerte « plus de processus LatentSync » ne pouvait jamais partir.
    On interroge Win32_Process par PowerShell (Get-CimInstance). Toute erreur ou toute sortie
    non numerique renvoie True : le watchdog ne conclut jamais a tort qu'un run est mort.
    """
    cmd = ("(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' "
           "-and $_.CommandLine -match 'latentsync' }).Count")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=120)
    except Exception:  # noqa: BLE001
        return True
    sortie = (r.stdout or "").strip()
    if not sortie.isdigit():
        return True
    return int(sortie) > 0


def lit_moniteur():
    if not os.path.exists(MONITEUR):
        return {}
    try:
        with open(MONITEUR, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def lire_sentinelle() -> str:
    """Reponse de l'utilisateur : « OK » ou « STOP » (insensible a la casse)."""
    try:
        with open(SENTINELLE, encoding="utf-8", errors="replace") as f:
            return f.read().strip().upper()
    except OSError:
        return ""


def fichiers_incrustations():
    """Fichiers declares dans l'horodatage (les PNG a afficher)."""
    attendus = []
    try:
        with open(TIMING, encoding="utf-8") as f:
            entrees = json.load(f)
    except (OSError, json.JSONDecodeError):
        return attendus
    for e in entrees:
        if isinstance(e, dict) and e.get("fichier"):
            attendus.append(os.path.join(VID, e["fichier"].replace("/", os.sep)))
    return attendus


def manque_assemblage():
    """Tout ce qui empeche l'assemblage de partir. Vide = rien ne manque."""
    manque = []
    if not os.path.exists(ASSEMBLE):
        manque.append(f"script d'assemblage absent : {ASSEMBLE}")
    if not FINAL:
        manque.append("nom du livrable non renseigne (SORTIE_VIDEO vide)")
    if not os.path.exists(TIMING):
        manque.append(f"horodatage des incrustations absent : {TIMING}")
    if not os.path.isdir(OVERLAYS):
        manque.append(f"dossier d'incrustations absent : {OVERLAYS}")
    for p in fichiers_incrustations():
        if not os.path.exists(p):
            manque.append(f"incrustation absente : {p}")
    return manque


def etat_incrustations() -> str:
    """Liste lisible des fichiers a valider : present (taille) ou manquant."""
    lignes = []
    if os.path.exists(TIMING):
        lignes.append(f"  [ok] {os.path.basename(TIMING)}")
    else:
        lignes.append(f"  [--] {os.path.basename(TIMING)}   MANQUANT")
    for p in fichiers_incrustations():
        nom = os.path.relpath(p, VID).replace(os.sep, "/")
        if os.path.exists(p):
            lignes.append(f"  [ok] {nom}   ({os.path.getsize(p) // 1024} Ko)")
        else:
            lignes.append(f"  [--] {nom}   MANQUANT")
    if len(lignes) == 1 and not os.path.exists(TIMING):
        lignes.append(f"  [--] {os.path.basename(OVERLAYS)}/   MANQUANT")
    return "\n".join(lignes)


def message_attente(manque, motif="EN ATTENTE DE VALIDATION") -> str:
    return (f"VOLET {VOLET} - {motif}\n"
            f"Manque : overlays_v{VOLET}/ ou overlay_timing_v{VOLET}.json\n"
            f"Fichiers a valider :\n{etat_incrustations()}\n"
            f"Detail :\n" + "\n".join(f"  - {m}" for m in manque) + "\n\n"
            f"Reponds OK pour lancer l'assemblage, ou STOP pour mettre en pause.\n"
            f"Je ne lis pas les messages Telegram : ecris OK (ou STOP) dans\n"
            f"{SENTINELLE}\n"
            f"(ou reponds-moi dans la session, je le fais pour toi).")


def pause_cron() -> bool:
    """Auto-pause de la tache planifiee. Repli : le drapeau local « pause » suffit a l'arreter."""
    try:
        r = subprocess.run([CLI_HERMES, "cron", "pause", JOB_ID],
                           capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            return True
        print(f"pause cron : code {r.returncode} {r.stderr.strip()[:200]}", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print(f"pause cron impossible : {e}", file=sys.stderr)
    return False


def enregistre(etat) -> None:
    with open(ETAT, "w", encoding="utf-8") as f:
        json.dump(etat, f, ensure_ascii=False, indent=1)


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
        sent = lire_sentinelle()
        manque = manque_assemblage()

        # 1. Reponse de l'utilisateur par sentinelle (prioritaire sur tout le reste).
        if sent.startswith("OK"):
            if not etat.get("ok_recu"):
                print(f"sentinelle OK : reponse enregistree (manque restant : {len(manque)})",
                      file=sys.stderr)
            etat["ok_recu"] = True
            etat.pop("pause", None)
        elif sent.startswith("STOP"):
            if etat.get("pause") != "stop":
                telegram(f"Volet {VOLET} : en pause sur ta demande.\n"
                         f"Aucun assemblage lance.\n"
                         f"Pour reprendre : ecris OK dans {SENTINELLE} "
                         f"(ou reponds OK) et je relance au tick suivant.")
                etat["pause"] = "stop"
                enregistre(etat)
            print("pause demandee par l'utilisateur (sentinelle STOP)", file=sys.stderr)
            return 0

        # 2. Deja en pause (demande utilisateur ou auto-pause 24 h) : silence total.
        if etat.get("pause"):
            print(f"en pause ({etat['pause']}) : rien a faire", file=sys.stderr)
            enregistre(etat)
            return 0

        # 3. Incrustations manquantes : attente de validation, pas d'assemblage.
        if manque:
            if etat.get("ok_recu"):
                # Reponse deja recue : plus de compte a rebours, on attend les fichiers.
                etat.pop("attente_debut", None)
                if maintenant - etat.get("alerte_ok", 0) > 3600:
                    telegram(f"VOLET {VOLET} - OK recu, fabrication toujours incomplete\n"
                             f"Manque :\n" + "\n".join(f"  - {m}" for m in manque) + "\n\n"
                             f"L'assemblage partira des que ces fichiers seront la.")
                    etat["alerte_ok"] = maintenant
                    print("OK recu mais fichiers manquants : message envoye", file=sys.stderr)
                else:
                    print("OK recu, fichiers encore manquants, silencieux", file=sys.stderr)
                enregistre(etat)
                return 0
            if "attente_debut" not in etat:
                etat["attente_debut"] = maintenant
                etat["attente_alerte"] = maintenant
                ok = telegram(message_attente(manque))
                print(message_attente(manque))
                print(f"envoi : attente de validation -> {'OK' if ok else 'ECHEC'}", file=sys.stderr)
            else:
                ecoule = maintenant - etat["attente_debut"]
                if ecoule > SEUIL_ABANDON:
                    if etat.get("alerte_24h") is not True:
                        telegram(f"Volet {VOLET} : 24 h sans reponse a la demande de validation.\n"
                                 f"Je me mets en pause : plus aucune alerte, plus aucun assemblage.\n"
                                 f"Pour reprendre : ecris OK dans {SENTINELLE} et relance la tache.")
                        etat["alerte_24h"] = True
                    etat["pause"] = "auto : 24 h sans reponse"
                    print(f"auto-pause (24 h sans reponse) ; pause cron = {pause_cron()}",
                          file=sys.stderr)
                elif maintenant - etat.get("attente_alerte", 0) > SEUIL_RAPPEL_ATTENTE:
                    telegram(message_attente(manque, f"EN ATTENTE DE VALIDATION (rappel, "
                                                     f"{ecoule/3600:.1f} h)"))
                    etat["attente_alerte"] = maintenant
                    print("rappel d'attente de validation envoye", file=sys.stderr)
                else:
                    print(f"attente de validation depuis {ecoule/60:.0f} min, silencieux",
                          file=sys.stderr)
            enregistre(etat)
            return 0

        # 4. Rien ne manque : l'attente eventuelle est finie.
        etat.pop("attente_debut", None)
        etat.pop("attente_alerte", None)

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
        enregistre(etat)
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

    enregistre(etat)
    return 0


if __name__ == "__main__":
    sys.exit(main())
