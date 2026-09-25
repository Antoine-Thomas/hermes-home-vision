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

Correctif 9 (volet 7) : deux angles morts de la fin de run.
  - Environnement des sous-processus : la tache cron tourne avec le venv de l'agent sur
    PYTHONPATH (python 3.11, numpy 2.4.3) ; herite par le pipeline, ce chemin masquait le
    numpy 1.26.4 du venv LatentSync (python 3.10) et tuait la greffe HF. On lance maintenant
    les sous-processus sans PYTHONPATH / PYTHONHOME / PYTHONSTARTUP.
  - Etape g morte : si le moniteur a fini, que la sortie HF n'existe pas, que le journal de la
    greffe ne bouge plus et qu'aucun processus pipeline ne tourne, une alerte explicite part
    avec la fin du journal (au lieu d'« aucune progression » horaire pendant des heures).
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
SOURCE = r"C:\Users\searc\Desktop\hermes tuto\psychopompe7.mp4"
AUDIO = r"C:\Users\searc\AppData\Local\hermes\data\xtts\audio_youtube_v6.wav"
ENV_HERMES = r"C:\Users\searc\AppData\Local\hermes\.env"
CLI_HERMES = os.environ.get(
    "HERMES_EXE", r"C:\Users\searc\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe")
# Tache cron de ce watchdog : sert a l'auto-pause apres 24 h sans reponse.
JOB_ID = os.environ.get("JOB_ID", "3d91e98f9608")
# Environnement des sous-processus : sans les variables qui exposent le venv de l'agent Hermes.
# La tache cron (no_agent) tourne avec le venv de l'agent sur PYTHONPATH (python 3.11,
# numpy 2.4.3) ; herite par les etapes du pipeline, ce chemin masque le numpy 1.26.4 du venv
# LatentSync (python 3.10) et fait echouer la greffe HF (correctif 9, constat volet 7).
POISON_ENV = ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP")
ENV_SOUS_PROC = {k: v for k, v in os.environ.items() if k not in POISON_ENV}
# L'etape g ecrit son journal soit dans etapes_hfi_* (lancement par le watchdog, --depuis hf),
# soit dans cache/scratch/lancement_v7b.log (lanceur manuel lancer_volet7b.ps1). On surveille le
# plus recent de ces journaux : aucun autre fichier n'est ecrit pendant les ~6 h de greffe, donc
# sans ce repere le watchdog croirait a un blocage et alerterait toutes les heures.
SCRATCH_CACHE = r"C:\Users\searc\AppData\Local\hermes\cache\scratch"
JOURNAUX_ETAPE_G = [os.path.join(DOSSIER, f"etapes_hfi_{VOLET}.log"),
                    os.path.join(SCRATCH_CACHE, f"lancement_v{VOLET}b.log"),
                    os.path.join(SCRATCH_CACHE, f"lancement_volet{VOLET}b.log")]
CHAT = "8956868107"
SEUIL_SILENCE = 25 * 60
# Correctif 13 : la greffe HF (etape g) est relancee automatiquement quand LatentSync est fini
# sans qu'aucune sortie HF n'existe -- au plus 5 essais espaces de 30 min, puis alerte seule.
LIMITE_RELANCE_HF = 5
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


def assemblee_vivante() -> bool:
    """Un processus d'assemblage final tourne-t-il ?"""
    return processus_vivant("assemble_v7")


def hf_lisible(chemin: str) -> bool:
    """Le MP4 de greffe HF est-il utilisable ?

    Un fichier en cours d'encodage existe deja sur le disque (441 Mo au bout de 12 min pour le
    volet 7) mais n'est pas lisible : ffmpeg n'ecrit l'atome moov qu'a la toute fin. ffprobe
    renvoie alors « moov atom not found » et aucune duree. Exiger une duree exploitable evite de
    lancer l'assemblage pendant l'encodage (arrive le 24/09 a 12:01).
    """
    if not os.path.exists(chemin):
        return False
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", chemin],
                           capture_output=True, text=True, errors="replace", timeout=180)
    except Exception:  # noqa: BLE001
        return False
    try:
        return float((r.stdout or "").strip()) > 1.0
    except ValueError:
        return False


def latentsync_vivant() -> bool:
    """Un processus LatentSync tourne-t-il ?

    Correctif 8 : wmic est retire de Windows 11 et renvoyait ici une sortie vide avec un code
    de retour 0, donc l'alerte « plus de processus LatentSync » ne pouvait jamais partir.
    On interroge Win32_Process par PowerShell (Get-CimInstance). Toute erreur ou toute sortie
    non numerique renvoie True : le watchdog ne conclut jamais a tort qu'un run est mort.
    """
    return processus_vivant("latentsync")


def processus_vivant(motif: str) -> bool:
    """Un python.exe dont la ligne de commande contient <motif> tourne-t-il ?

    Toute erreur ou toute sortie non numerique renvoie True (on ne conclut pas a tort).
    Piege corrige le 25/09 : la commande PowerShell etait mal parenthesee (la parenthese
    fermante manquait avant .Count). PowerShell sortait une erreur, stdout etait vide, et la
    fonction renvoyait donc True pour TOUS les motifs, meme absents. Consequence : plus aucune
    alerte « etape g morte », plus aucune reprise d'assemblage apres echec -- le run volet 7 est
    reste bloque 22 h a l'etape g sans que le watchdog ne s'en apercoive.
    """
    cmd = ("@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' "
           f"-and $_.CommandLine -match '{motif}' }}).Count")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, errors="replace", timeout=120)
    except Exception:  # noqa: BLE001
        return True
    sortie = (r.stdout or "").strip()
    if not sortie.isdigit():
        # On ne conclut jamais « mort » a tort, mais on le dit : une commande cassee avait rendu
        # toutes les alertes silencieusement inoperantes.
        print(f"processus_vivant({motif!r}) : sortie inexploitable {sortie!r} "
              f"(stderr {r.stderr.strip()[:140]!r}) -> True par prudence", file=sys.stderr)
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
                         cwd=VID, env=ENV_SOUS_PROC,
                         creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))


def main() -> int:
    maintenant = time.time()
    etat = {}
    if os.path.exists(ETAT):
        with open(ETAT, encoding="utf-8") as f:
            etat = json.load(f)

    # Repere de debut de run (correctif 12) : le livrable d'un run precedent porte le meme nom
    # de fichier et va etre ecrase par le nouvel assemblage. Sans ce repere, le watchdog
    # annoncerait « assemblage termine » sur l'ancien livrable et ne lancerait jamais le nouveau.
    if "debut" not in etat:
        etat["debut"] = maintenant
        print(f"nouveau run : repere de debut a {time.strftime('%H:%M:%S')}", file=sys.stderr)

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

        # Correctif 11 : n'assembler que sur une greffe HF reellement lisible. Le fichier existe
        # des le debut de l'encodage mais sans atome moov : l'assemblage de 12:01 est parti sur un
        # MP4 non finalise, a refuse (bien) et rien ne relancait ensuite (assemble_lance=true).
        hf_ok = hf_lisible(HF)
        encours_hf = processus_vivant("post_hf_transfer") or processus_vivant("pipeline_talkinghead")
        # Correctif 12 : un livrable plus ancien que le debut du run courant est celui du run
        # precedent (meme nom de fichier) : on l'ignore, sinon l'assemblage ne partirait jamais.
        final_recent = (os.path.getmtime(FINAL) >= etat["debut"]) if os.path.exists(FINAL) else False
        if os.path.exists(FINAL) and not final_recent:
            print("livrable anterieur a ce run (ignore : il sera ecrase par le nouvel assemblage)",
                  file=sys.stderr)
        if final_recent:
            if etat.get("assemble_fait") is not True:
                taille = os.path.getsize(FINAL) / 2 ** 20
                telegram(f"Volet {VOLET} : assemblage final termine\n{FINAL}\n{taille:.0f} Mo")
                etat["assemble_fait"] = True
                print(f"assemblage termine : {FINAL} ({taille:.0f} Mo)")
            else:
                print("assemblage deja fait", file=sys.stderr)
        elif not hf_ok:
            # Pendant l'encodage le MP4 existe sans etre lisible : silence, c'est normal.
            if encours_hf:
                print("greffe HF en cours d'ecriture (MP4 non finalise) : pas d'assemblage",
                      file=sys.stderr)
            elif maintenant - etat.get("alerte_hf_illisible", 0) > 3600:
                telegram(f"ALERTE : greffe HF inutilisable pour le volet {VOLET}.\n"
                         f"Fichier : {HF}\n"
                         f"ffprobe : aucune duree lisible (moov atom manquant) = encodage "
                         f"interrompu.\n"
                         f"Etapes a-f et hf_det_{VOLET}.npz intacts : seule l'etape g est a "
                         f"relancer.")
                etat["alerte_hf_illisible"] = maintenant
                print("alerte : HF illisible et plus aucun processus", file=sys.stderr)
        elif (etat.get("assemble_lance") is not True
              or (etat.get("assemble_essais", 1) < 3 and not assemblee_vivante()
                  and maintenant - etat.get("assemble_dernier", 0) > 900)):
            essais = etat.get("assemble_essais", 0) + 1
            print(f"lancement de l'assemblage final en tache detachee (essai {essais}/3)",
                  file=sys.stderr)
            lancer_assemblage_detache()
            telegram(f"Volet {VOLET} : assemblage final lance en tache de fond (essai {essais}/3)\n"
                     f"suivi : {LOG_ASSEMBLE}")
            etat["assemble_lance"] = True
            etat["assemble_essais"] = essais
            etat["assemble_dernier"] = maintenant
        else:
            # Trois essais sans livrable et plus rien qui tourne : alerte exploitable.
            if (not assemblee_vivante() and maintenant - etat.get("assemble_dernier", 0) > 900
                    and etat.get("assemble_essais", 0) >= 3
                    and maintenant - etat.get("alerte_assemble_echec", 0) > 3600):
                queue = ""
                try:
                    with open(LOG_ASSEMBLE, encoding="utf-8", errors="replace") as f:
                        queue = "".join(f.readlines()[-12:]).strip()[-700:]
                except OSError:
                    pass
                telegram(f"ALERTE : l'assemblage du volet {VOLET} a echoue "
                         f"{etat.get('assemble_essais')} fois.\n"
                         f"Aucun processus d'assemblage et pas de livrable.\n"
                         f"Journal : {LOG_ASSEMBLE}\n{queue}")
                etat["alerte_assemble_echec"] = maintenant
                print("alerte : assemblage en echec repete", file=sys.stderr)
            else:
                print("assemblage en cours (tache detachee)", file=sys.stderr)
        enregistre(etat)
        return 0

    mon = lit_moniteur()

    # Fin du run detache (le moniteur ecrit "fin") : relancer les etapes g a i, que le
    # pipeline n'enchaine pas lui-meme quand LatentSync part en tache de fond.
    # Correctif 13 (25/09) : la relance ne depend plus d'un drapeau a usage unique. Le 24/09 un
    # lancement premature (13:37, avant la fin de LatentSync) avait pose hfi_lance = True ; la
    # greffe a echoue et RIEN ne l'a relancee quand LatentSync a vraiment fini a 18:34 -- le run
    # est reste bloque 22 h. On relance donc des que le moniteur a fini, que la sortie HF manque
    # et qu'aucun pipeline ne tourne, avec 30 min entre deux essais et 5 essais au maximum.
    if mon.get("fin") is not None and not os.path.exists(HF):
        if (not processus_vivant("pipeline_talkinghead")
                and maintenant - etat.get("hfi_relance", 0) > 1800
                and etat.get("hfi_relance_nb", 0) < LIMITE_RELANCE_HF):
            log = os.path.join(DOSSIER, f"etapes_hfi_{VOLET}.log")
            cmd = [PY_LATENTSYNC, PIPELINE, "--source", SOURCE, "--audio", AUDIO,
                   "--volet", VOLET, "--depuis", "hf"]
            # en tache de fond : la greffe HF peut durer une heure, on ne bloque pas le tick du watchdog
            with open(log, "w", encoding="utf-8") as f:
                subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=VID,
                                 env=ENV_SOUS_PROC,
                                 creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
            essai = etat.get("hfi_relance_nb", 0) + 1
            telegram(f"Volet {VOLET} : LatentSync termine, greffe HF / mesures / rapport lancees en "
                     f"tache de fond (essai {essai}/{LIMITE_RELANCE_HF})\nsuivi : {log}")
            etat["hfi_lance"] = True
            etat["hfi_relance"] = maintenant
            etat["hfi_relance_nb"] = essai
            etat.pop("alerte_hf_morte", None)   # nouvelle tentative : on repart d'un etat propre
            print(f"etapes hf/mesures/rapport lancees (essai {essai}/{LIMITE_RELANCE_HF}) : {log}",
                  file=sys.stderr)

    # Correctif 9 : etape g morte. Le moniteur a fini, la sortie HF n'existe pas, le journal de
    # la greffe ne bouge plus et plus aucun processus pipeline ne tourne. Sans cette detection,
    # le watchdog se contentait d'« aucune progression » horaire pendant des heures (volet 7 :
    # etape g morte a 02:41, alerte exploitable seulement a 10:41).
    if (etat.get("hfi_lance") is True and not os.path.exists(HF)
            and etat.get("alerte_hf_morte") is not True):
        presents = [q for q in JOURNAUX_ETAPE_G if os.path.exists(q)]
        log_hf = max(presents, key=os.path.getmtime) if presents else JOURNAUX_ETAPE_G[0]
        age = (maintenant - os.path.getmtime(log_hf)) if presents else -1.0
        if age > 20 * 60 and not processus_vivant("pipeline_talkinghead"):
            queue = ""
            try:
                with open(log_hf, encoding="utf-8", errors="replace") as f:
                    queue = "".join(f.readlines()[-10:]).strip()[-800:]
            except OSError:
                pass
            texte = (f"ALERTE : l'etape g (greffe HF) du volet {VOLET} ne tourne plus.\n"
                     f"Aucun processus pipeline, journal arrete depuis {age/60:.0f} min.\n"
                     f"Journal : {log_hf}\n"
                     f"Dernieres lignes :\n{queue}")
            if etat.get("hfi_relance_nb", 0) >= LIMITE_RELANCE_HF:
                texte += (f"\nRelances automatiques epuisees "
                          f"({etat.get('hfi_relance_nb')}/{LIMITE_RELANCE_HF}) : intervention "
                          f"manuelle necessaire.")
            telegram(texte)
            etat["alerte_hf_morte"] = True
            print("alerte : etape g morte (aucun processus pipeline)", file=sys.stderr)

    ref = 0.0
    for p in (MONITEUR, JOURNAL, SORTIE, HF, *JOURNAUX_ETAPE_G):
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
    # Pendant la greffe HF (etape g), la sortie du script est capturee par le pipeline et
    # n'arrive qu'a la fin : aucun fichier surveille ne bouge pendant ~6 h. Un processus
    # pipeline vivant est alors le seul repere ; on n'alerte que sur un depassement franc
    # (garde-fou contre la pagination de 14 h du volet 5) au lieu d'« aucune progression » horaire.
    vivant = processus_vivant("pipeline_talkinghead") if silence > SEUIL_SILENCE else False
    seuil = 8 * 3600 if vivant else SEUIL_SILENCE
    if silence > seuil:
        if maintenant - etat.get("derniere_alerte", 0) > 3600:
            if vivant:
                envoyer, motif = True, (f"ALERTE : etape en cours depuis "
                                        f"{silence/3600:.1f} h sans sortie ecrite")
            else:
                envoyer, motif = True, f"ALERTE : aucune progression depuis {silence/60:.0f} min"
            etat["derniere_alerte"] = maintenant
    elif not latentsync_vivant() and silence > 10 * 60:
        if etat.get("alerte_mort") is not True:
            envoyer, motif = True, "ALERTE : plus de processus LatentSync"
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
