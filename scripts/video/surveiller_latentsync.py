# -*- coding: utf-8 -*-
"""Moniteur d'un run LatentSync (volet N) : progression reelle, VRAM, temperature, events.

Lance LatentSync lui-meme (Popen) pour capter la sortie tqdm de la boucle d'inference,
puis echantillonne le GPU toutes les 30 s et notifie Telegram au lancement, toutes les
30 min, a la fin, ou en cas d'arret d'urgence.

Arret d'urgence si : VRAM pic > 8050 Mio, Kernel-Power 41 detecte pendant le run, ou
3 events nvlddmkm ID 153 consecutifs.

Statut ecrit en continu dans moniteur_<volet>_statut.json (survit a une compression de session).

CORRECTIONS DU 20/09/2026 (regle 81 du skill talking-head-video-8gb)
  - texte envoye SANS parse_mode : un chevron brut dans l'ETA de tqdm (01:55<00:00)
    faisait rejeter TOUT le message par Telegram en HTTP 400, et le run paraissait mort ;
  - progression lue sur la barre EXTERIEURE (« Doing inference ») et non sur la derniere
    barre vue : la barre interieure « Sample frames: 16 » est reecrite ~21 fois par
    iteration et faisait osciller le pourcentage affiche entre 0 et 100 ;
  - chaque envoi est journalise (envois_<volet>.log) et un envoi reussi ecrit un battement
    de coeur (dernier_envoi_<volet>.json) : sans ca, un canal casse est indiscernable d'un
    run mort. C'est le fichier que doit lire un watchdog externe.

Usage :
  surveiller_latentsync.py <video_in> <audio_in> <video_out> <dossier> [options]

Options :
  --volet NOM       etiquette des fichiers (defaut : volet)
  --commande-json F remplace la commande d'inference par la liste d'arguments du fichier F
                    (run segmente : tests/run_latentsync_segments.py). La progression suit
                    alors les lignes « === segment i/N === » en plus de la barre tqdm.
  --python CHEMIN   interpreteur du venv LatentSync (defaut : venv/Scripts/python.exe)
  --latentsync DIR  racine du depot LatentSync (defaut : parent du dossier de ce script)

Exemple (volet 5, depuis la racine du depot) :
  venv/Scripts/python.exe tests/surveiller_latentsync.py \\
      tests/v4_talking_head_v3/source_v5_loop_344.mp4 C:/.../audio_youtube_v5.wav \\
      tests/v4_talking_head_v5/sortie_latentsync_v5.mp4 tests/v4_talking_head_v5} --volet v5
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

CHAT = "8956868107"
SEUIL_VRAM = 8050
SEUIL_NVLD_CONSECUTIFS = 3
INTERVALLE_ECHANTILLON = 30
INTERVALLE_EVENTS = 300
INTERVALLE_NOTIF = 1800
ENV_HERMES = r"C:\Users\searc\AppData\Local\hermes\.env"

# Balises de notre propre mise en forme : retirees avant envoi (texte brut, sans
# parse_mode). Ne jamais retirer les chevrons d'un texte quelconque : celui de l'ETA de
# tqdm doit rester tel quel, sinon le message annonce une progression fausse.
BALISES = ("<b>", "</b>", "<i>", "</i>", "<pre>", "</pre>", "<code>", "</code>")

RACINE_SCRIPT = os.path.dirname(os.path.abspath(__file__))
LATENTSYNC = os.path.dirname(RACINE_SCRIPT)

JOURNAL_ENVOIS = ""
BATTEMENT = ""


def jeton_telegram() -> str:
    try:
        with open(ENV_HERMES, encoding="utf-8", errors="replace") as f:
            for ligne in f:
                if ligne.startswith("TELEGRAM_BOT_TOKEN="):
                    return ligne.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


JETON = jeton_telegram()


def nettoyer(texte: str) -> str:
    for balise in BALISES:
        texte = texte.replace(balise, "")
    return texte


def journaliser_envoi(ok: bool, detail: str) -> None:
    """Journalise CHAQUE envoi et horodate le dernier succes (battement de coeur)."""
    if not JOURNAL_ENVOIS:
        return
    horo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(JOURNAL_ENVOIS, "a", encoding="utf-8") as f:
            f.write(f"{horo}\t{'OK' if ok else 'ECHEC'}\t{detail}\n")
        if ok and BATTEMENT:
            with open(BATTEMENT, "w", encoding="utf-8") as f:
                json.dump({"dernier_envoi_reussi": horo, "epoch": time.time()}, f)
    except OSError as e:
        print(f"[telegram] journal illisible : {e}", flush=True)


def telegram(texte: str, silence: bool = False) -> bool:
    if not JETON:
        print("[telegram] jeton absent, notification non envoyee", flush=True)
        return False
    if silence:
        return False
    data = urllib.parse.urlencode(
        {"chat_id": CHAT, "text": nettoyer(texte), "disable_notification": "true"}
    ).encode()
    ok, detail = False, ""
    try:
        with urllib.request.urlopen(
            f"https://api.telegram.org/bot{JETON}/sendMessage", data=data, timeout=30
        ) as r:
            ok, detail = r.status == 200, f"HTTP {r.status}"
    except urllib.error.HTTPError as e:  # 4xx/5xx : le corps dit pourquoi
        detail = f"HTTP {e.code} : {e.read()[:200].decode('utf-8', 'replace')}"
    except Exception as e:  # noqa: BLE001
        detail = repr(e)
    journaliser_envoi(ok, detail)
    if not ok:
        print(f"[telegram] echec : {detail}", flush=True)
    return ok


def arreter_arbre(proc: subprocess.Popen) -> None:
    """Tue l'enfant ET ses descendants, puis attend sa fin.

    En mode segmente l'enfant est le script de tranches et le vrai processus d'inference est
    son petit-fils : un proc.kill() laisserait le GPU occupe apres un arret d'urgence.
    """
    try:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, timeout=60)
    except Exception as e:  # noqa: BLE001
        print(f"[arret] taskkill indisponible ({e!r}), kill direct", flush=True)
    try:
        proc.kill()
    except Exception:  # noqa: BLE001
        pass


def hm(secondes: float) -> str:
    secondes = max(0, int(secondes))
    return f"{secondes // 3600}h{(secondes % 3600) // 60:02d}"


def gpu() -> tuple[int, int]:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=20,
        ).stdout.strip().splitlines()[0]
        vram, temp = out.split(",")
        return int(vram), int(temp)
    except Exception:  # noqa: BLE001
        return -1, -1


def events(requete: str) -> list[str]:
    """Derniers events System correspondant a la requete (wevtutil est en UTF-16)."""
    try:
        out = subprocess.run(
            ["wevtutil", "qe", "System", f"/q:{requete}", "/c:5", "/rd:true", "/f:text"],
            capture_output=True, timeout=60,
        ).stdout.decode("utf-16-le", errors="replace")
        return [l.strip() for l in out.splitlines() if l.strip()][:5]
    except Exception:  # noqa: BLE001
        return []


class Etat:
    def __init__(self) -> None:
        self.pourcent = 0.0
        self.avance = 0
        self.total = 0
        self.eta = ""
        self.phase = "demarrage"
        self.derniere_ligne = ""
        self.vram_pic = 0
        self.temp_max = 0
        self.nvld_total = 0
        self.nvld_consecutifs = 0
        self.kernel_power = 0
        self.kp_reference = 0
        self.nvld_reference = 0
        self.debut = time.time()
        self.fin: float | None = None
        self.arret = ""
        self.erreur = ""
        self.lignes_barre_exterieure = 0
        self.segment = 0        # mode segmente : tranche en cours
        self.n_segments = 0     # 0 = run en un seul appel


ETAT = Etat()
VERROU = threading.Lock()

# La barre EXTERIEURE est la seule qui mesure la progression du run. Sa ligne commence
# par son libelle (« Doing inference... ») ; la barre interieure commence par
# « Sample frames: 16: » et ne matche donc pas (le libelle ne peut pas contenir de « : »).
BARRE = re.compile(r"^\s*(?P<libelle>[^:]+):\s*(?P<pct>\d+)%\|[^|]*\|\s*(?P<av>\d+)/(?P<tot>\d+)")
BARRE_ATTENDUE = "Doing inference"
ECHEANCE = re.compile(r"\[([^,\]]+),\s*([^,\]]+)\]")
# Run segmente : le script de tranches annonce chaque segment ("=== segment 3/8 ===").
# Sans ca, la barre de tqdm repart de 0 a chaque tranche et le pourcentage parait reculer.
SEGMENT = re.compile(r"===\s*segment\s+(\d+)\s*/\s*(\d+)\s*===")


def lire_ligne(ligne: str) -> bool:
    """Met ETAT a jour a partir d'UNE ligne de sortie de LatentSync.

    Retourne True si la ligne etait bien la barre exterieure (l'instrumentation du test
    s'en sert ; l'appelant n'a rien a en faire).
    """
    with VERROU:
        ETAT.derniere_ligne = ligne.strip()[:180]
        ms = SEGMENT.search(ligne)
        if ms:
            ETAT.segment = int(ms.group(1))
            ETAT.n_segments = int(ms.group(2))
            ETAT.pourcent = 0.0     # nouvelle tranche : la barre repart de zero
        if "Affine transforming" in ligne:
            ETAT.phase = "detection des visages"
        elif "Restoring" in ligne:
            ETAT.phase = "restauration des visages"
        elif BARRE_ATTENDUE in ligne:
            ETAT.phase = "inference"
        m = BARRE.match(ligne)
        if not (m and BARRE_ATTENDUE in m.group("libelle")):
            return False
        ETAT.phase = "inference"
        ETAT.pourcent = float(m.group("pct"))
        ETAT.avance = int(m.group("av"))
        ETAT.total = int(m.group("tot"))
        ETAT.lignes_barre_exterieure += 1
        e = ECHEANCE.search(ligne)
        if e:
            ETAT.eta = f"{e.group(1).strip()} restant ({e.group(2).strip()})"
        return True


def lire_sortie(proc: subprocess.Popen, journal) -> None:
    """Consomme la sortie du run : tout est journalise, seule la barre exterieure compte."""
    for brut in proc.stdout:  # type: ignore[union-attr]
        ligne = brut.rstrip("\r\n")
        if not ligne.strip():
            continue
        journal.write(ligne + "\n")
        journal.flush()
        lire_ligne(ligne)


def instantane() -> str:
    with VERROU:
        ecoule = (ETAT.fin or time.time()) - ETAT.debut
        lignes = [
            f"LatentSync - {ETAT.phase}",
            f"progression : {ETAT.pourcent:.1f} %",
        ]
        if ETAT.total:
            lignes.append(f"frames     : {ETAT.avance}/{ETAT.total}")
        if ETAT.eta:
            lignes.append(f"tqdm       : {ETAT.eta}")
        if ETAT.n_segments:
            lignes.append(f"tranche    : {ETAT.segment}/{ETAT.n_segments}")
            if ETAT.total:
                global_pct = ((ETAT.segment - 1) + ETAT.pourcent / 100) / ETAT.n_segments * 100
                lignes.append(f"avancement : {global_pct:.1f} % du run")
        lignes += [
            f"ecoule      : {hm(ecoule)}" + (f"  (total {hm(ecoule)})" if ETAT.fin else ""),
            f"VRAM pic    : {ETAT.vram_pic} Mio (seuil {SEUIL_VRAM})",
            f"temp max    : {ETAT.temp_max} C",
            f"nvlddmkm 153: {ETAT.nvld_total}   Kernel-Power 41: {ETAT.kernel_power}",
        ]
        if ETAT.erreur:
            lignes.append(f"erreur : {ETAT.erreur}")
        return "\n".join(lignes)


def ecrire_statut(chemin: str) -> None:
    with VERROU:
        s = {
            "phase": ETAT.phase, "pourcent": ETAT.pourcent, "avance": ETAT.avance,
            "total": ETAT.total, "eta": ETAT.eta, "vram_pic": ETAT.vram_pic,
            "temp_max": ETAT.temp_max, "nvld_total": ETAT.nvld_total,
            "kernel_power": ETAT.kernel_power, "debut": ETAT.debut, "fin": ETAT.fin,
            "arret": ETAT.arret, "erreur": ETAT.erreur,
            "lignes_barre_exterieure": ETAT.lignes_barre_exterieure,
            "segment": ETAT.segment, "n_segments": ETAT.n_segments,
            "maj": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


def main() -> int:
    p = argparse.ArgumentParser(add_help=True, description="Moniteur de run LatentSync")
    p.add_argument("video_in")
    p.add_argument("audio_in")
    p.add_argument("video_out")
    p.add_argument("dossier")
    p.add_argument("--volet", default="volet")
    p.add_argument("--python", default="")
    p.add_argument("--latentsync", default=LATENTSYNC)
    p.add_argument("--sans-lancer", action="store_true",
                   help="n'execute pas LatentSync (test du moniteur seul)")
    p.add_argument("--commande-json", default="",
                   help="fichier JSON contenant la liste d'arguments a lancer au lieu de "
                        "scripts.inference : sert au run segmente "
                        "(tests/run_latentsync_segments.py)")
    a = p.parse_args()

    global JOURNAL_ENVOIS, BATTEMENT
    racine = os.path.abspath(a.latentsync)
    os.makedirs(a.dossier, exist_ok=True)
    dossier = os.path.abspath(a.dossier)
    v = a.volet
    journal_path = os.path.join(dossier, f"latentsync_{v}_run.log")
    statut_path = os.path.join(dossier, f"moniteur_{v}_statut.json")
    JOURNAL_ENVOIS = os.path.join(dossier, f"envois_{v}.log")
    BATTEMENT = os.path.join(dossier, f"dernier_envoi_{v}.json")
    interpreteur = a.python or os.path.join(racine, "venv", "Scripts", "python.exe")

    cmd = [
        interpreteur, "-u", "-m", "scripts.inference",
        "--unet_config_path", "configs/unet/stage2.yaml",
        "--inference_ckpt_path", "checkpoints/latentsync_unet.pt",
        # volet 7 : 25 pas et guidance 1,8 (au lieu de 20 et 1,5) pour une bouche plus nette.
        # Le correctif officiel (LatentSync 1.6 en 512x512) demande 18 Go de VRAM, indisponible ici.
        "--inference_steps", "25", "--guidance_scale", "1.8", "--enable_deepcache",
        "--video_path", os.path.abspath(a.video_in),
        "--audio_path", os.path.abspath(a.audio_in),
        "--video_out_path", os.path.abspath(a.video_out),
        "--temp_dir", os.path.join(racine, f"temp_{v}"),
    ]
    if a.commande_json:
        with open(a.commande_json, encoding="utf-8") as f:
            cmd = list(json.load(f))
        print(f"commande (run segmente) : {' '.join(cmd)}", flush=True)
    print("commande :", " ".join(cmd), flush=True)

    journal = open(journal_path, "w", encoding="utf-8", errors="replace")
    journal.write("commande : " + " ".join(cmd) + "\n")
    if a.commande_json:
        journal.write("mode : run segmente (la barre de progression est celle de la "
                      "tranche en cours)\n")
    journal.flush()

    if a.sans_lancer:
        proc = subprocess.Popen(
            [interpreteur, "-c", "print('mode test : LatentSync non lance')"],
            cwd=racine, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
    else:
        proc = subprocess.Popen(
            cmd, cwd=racine, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
    threading.Thread(target=lire_sortie, args=(proc, journal), daemon=True).start()

    _, temp0 = gpu()
    with VERROU:
        ETAT.vram_pic, ETAT.temp_max = max(0, gpu()[0]), max(0, temp0)
        # Reference des events AVANT le run : sans ca, un event historique (deja present
        # dans le journal System) serait compte comme nouveau et ferait monter le
        # compteur nvlddmkm des le premier controle.
        ETAT.kernel_power = len(events("*[System[EventID=41]]"))
        ETAT.nvld_total = len(events("*[System[(EventID=153) and (Provider[@Name='nvlddmkm'])]]"))
        ETAT.kp_reference = ETAT.kernel_power
        ETAT.nvld_reference = ETAT.nvld_total

    telegram(
        f"LatentSync {v} lance\n"
        f"debut      : {datetime.now().strftime('%H:%M')}\n"
        f"video      : {os.path.basename(a.video_in)}\n"
        f"audio      : {os.path.basename(a.audio_in)}\n"
        f"surveillance : GPU toutes les {INTERVALLE_ECHANTILLON} s, "
        f"rappel toutes les {INTERVALLE_NOTIF // 60} min\n"
        "arret d'urgence si VRAM > 8050 Mio, 3 nvlddmkm 153 consecutifs ou Kernel-Power 41."
    )

    t_dernier_event = 0.0
    t_derniere_notif = time.time()
    while True:
        code = proc.poll()
        vram, temp = gpu()
        with VERROU:
            if vram > ETAT.vram_pic:
                ETAT.vram_pic = vram
            if temp > ETAT.temp_max:
                ETAT.temp_max = temp
        ecrire_statut(statut_path)

        if time.time() - t_dernier_event >= INTERVALLE_EVENTS:
            t_dernier_event = time.time()
            kp = events("*[System[EventID=41]]")
            nv = events("*[System[(EventID=153) and (Provider[@Name='nvlddmkm'])]]")
            with VERROU:
                ETAT.kernel_power = len(kp)
                nouveaux = max(0, len(nv) - ETAT.nvld_total)
                ETAT.nvld_total = len(nv)
                ETAT.nvld_consecutifs = ETAT.nvld_consecutifs + 1 if nouveaux else 0
            if kp:
                with VERROU:
                    ETAT.arret = "Kernel-Power 41 detecte (reset/reboot GPU)"
                telegram("ARRET : " + ETAT.arret + "\n\n" + instantane())
                arreter_arbre(proc)
                break
            with VERROU:
                declenche = ETAT.nvld_consecutifs >= SEUIL_NVLD_CONSECUTIFS
            if declenche:
                with VERROU:
                    ETAT.arret = f"{SEUIL_NVLD_CONSECUTIFS} events nvlddmkm 153 consecutifs"
                telegram("ARRET : " + ETAT.arret + "\n\n" + instantane())
                arreter_arbre(proc)
                break

        if vram > SEUIL_VRAM:
            with VERROU:
                ETAT.arret = f"VRAM pic {vram} Mio > {SEUIL_VRAM} Mio"
            telegram("ARRET : " + ETAT.arret + "\n\n" + instantane())
            arreter_arbre(proc)
            break

        if time.time() - t_derniere_notif >= INTERVALLE_NOTIF:
            t_derniere_notif = time.time()
            telegram(instantane())

        if code is not None:
            with VERROU:
                ETAT.fin = time.time()
                ETAT.phase = "termine" if code == 0 else "echec"
            break
        time.sleep(INTERVALLE_ECHANTILLON)

    journal.close()
    try:
        proc.wait(timeout=60)
    except Exception:  # noqa: BLE001
        pass
    code = proc.returncode
    ecrire_statut(statut_path)

    with VERROU:
        ecoule = (ETAT.fin or time.time()) - ETAT.debut
        taille = os.path.getsize(a.video_out) if os.path.exists(a.video_out) else 0
        lignes = [
            f"LatentSync {v} termine" if code == 0 else f"LatentSync {v} en echec",
            f"code retour : {code}",
            f"duree totale: {hm(ecoule)}",
            f"progression : {ETAT.pourcent:.1f} % ({ETAT.avance}/{ETAT.total})",
            (f"tranches    : {ETAT.segment}/{ETAT.n_segments}" if ETAT.n_segments else
             "mode        : un seul appel (non segmente)"),
            f"VRAM pic    : {ETAT.vram_pic} Mio",
            f"temp max    : {ETAT.temp_max} C",
            f"nvlddmkm 153: {ETAT.nvld_total}   Kernel-Power 41: {ETAT.kernel_power}",
            f"sortie      : {a.video_out} ({taille / 1e6:.1f} Mo)",
        ]
        if ETAT.arret:
            lignes.insert(1, f"arret d'urgence : {ETAT.arret}")
        if ETAT.erreur:
            lignes.append(f"erreur : {ETAT.erreur}")
    telegram("\n".join(lignes))
    print("\n".join(lignes), flush=True)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
