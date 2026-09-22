# -*- coding: utf-8 -*-
"""Veille de la chaine B1 v2 : n'ecrit quelque chose que s'il y a du nouveau.

Utilise comme script de cron en mode no_agent : la sortie est envoyee telle quelle, et une sortie
vide n'envoie rien. L'etat est conserve dans un fichier pour ne pas repeter le meme message.

  - progression nouvelle (nombre d'images produites par l'etage en cours) -> une ligne
  - video finale presente -> annonce unique
  - aucune image nouvelle depuis plus de 20 min et pas de video -> alerte
"""
import json
import os
import re
import time

TUTO = r"C:\Users\searc\Desktop\hermes tuto"
TRAVAIL = os.path.join(TUTO, "b1v2")
LOG = os.path.join(TRAVAIL, "pipeline_v2.log")
VIDEO = os.path.join(TUTO, "portrait-hyperrealiste-1080p-sdxl.mp4")
ETAT = os.path.join(TRAVAIL, "veille_etat.json")
ATTENDU = 290

# etage -> (libelle, dossier de sortie, secondes par image pour l'ETA)
ETAGES = {
    "1": ("restyle SDXL", "frames_sdxl", 11.0),
    "2": ("remplacement des hautes frequences", "frames_v2_720p", 0.15),
    "3": ("Real-ESRGAN x4 CUDA", "frames_v2_720p_esr", 3.6),
    "4": ("greffe finale 1080p", "frames_finales", 0.3),
    "5a": ("encodage video", None, 0.0),
    "5b": ("montage audio", None, 0.0),
}
SORTIE_VIDEO_BRUTE = os.path.join(TRAVAIL, "video_no_audio.mp4")


def compter(dossier):
    if not dossier or not os.path.isdir(dossier):
        return 0
    return len([f for f in os.listdir(dossier) if f.lower().endswith(".png")])


etat = {}
if os.path.exists(ETAT):
    try:
        with open(ETAT, encoding="utf-8") as f:
            etat = json.load(f)
    except Exception:
        etat = {}

messages = []
if os.path.exists(VIDEO) and not etat.get("annonce"):
    taille = os.path.getsize(VIDEO) / 1e6
    messages.append("B1 v2 TERMINE : %s (%.1f Mo) - a verifier avant diffusion" % (VIDEO, taille))
    etat["annonce"] = True
elif not etat.get("annonce"):
    etape = None
    if os.path.exists(LOG):
        with open(LOG, "r", encoding="utf-8", errors="ignore") as f:
            contenu = f.read()
        annonces = re.findall(r"=== etape (\S+?) ", contenu)
        if annonces:
            etape = annonces[-1].rstrip(":")
    if etape in ETAGES:
        libelle, dossier, par_image = ETAGES[etape]
        images = compter(os.path.join(TRAVAIL, dossier) if dossier else None)
        if dossier is None:
            progression = "etape 5 en cours (encodage/montage)"
        else:
            reste = max(0, ATTENDU - images) * par_image / 60.0
            progression = "etape %s (%s) : %d/%d images%s" % (
                etape, libelle, images, ATTENDU,
                " | reste ~%.0f min" % reste if images and reste > 1 else "")
        if progression != etat.get("derniere_ligne"):
            # on ne signale que si quelque chose a bouge depuis le dernier passage
            if images or etat.get("derniere_ligne") is None:
                messages.append("B1 v2 - " + progression)
            etat["derniere_ligne"] = progression
        # surveillance du silence : le dossier doit avoir bouge recemment
        dossier_actif = os.path.join(TRAVAIL, dossier) if dossier else SORTIE_VIDEO_BRUTE
        if os.path.exists(dossier_actif):
            silence = (time.time() - os.path.getmtime(dossier_actif)) / 60.0
            if silence > 20:
                messages.append("ALERTE B1 v2 : plus rien de nouveau depuis %.0f min "
                                "(etape %s, %d/%d images) - voir b1v2/pipeline_v2.log"
                                % (silence, etape, images, ATTENDU))

with open(ETAT, "w", encoding="utf-8") as f:
    json.dump(etat, f, ensure_ascii=False)

print("\n".join(messages))
