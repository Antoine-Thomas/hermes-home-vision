# -*- coding: utf-8 -*-
"""Livraison du volet 5 (talking head 5 min 44) sur Telegram, chat 8956868107.

Le jeton du bot est lu dans %LOCALAPPDATA%\\hermes\\.env a l'execution : il n'est jamais
affiche, jamais passe en argument de commande, jamais journalise.

Deux envois :
  1. le recap en texte ;
  2. l'apercu 1080p compresse (le fichier complet fait 239,2 Mo, au-dela de la limite
     de 50 Mo d'un bot Telegram).

Aucun parse_mode : le texte du recap contient des caracteres qui casseraient un envoi HTML
(cause exacte du silence du moniteur du run, voir la section C de la doc du 20/09).

Usage : python livrer_v5_telegram.py
"""
from __future__ import annotations

import io
import os
import sys

import requests

ENV = r"C:\Users\searc\AppData\Local\hermes\.env"
CHAT_ID = "8956868107"
API = "https://api.telegram.org/bot%s/%s"
DOSSIER = (r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\LatentSync"
           r"\tests\v4_talking_head_v5")
APERCU = os.path.join(DOSSIER, "apercu_telegram_1080p.mp4")
COMPLET = os.path.join(DOSSIER, "sortie_latentsync_v5_final_1080p.mp4")

RECAP = """LatentSync v5 — volet 5 termine
Sortie : 343,88 s (5 min 44), 8597 frames, 1920x1080 25 fps

RUN
duree        : 14 h 17 pour 5 min 44 = 149,6x le temps reel
iterations   : 538, de 116 a 127 s/it
VRAM pic     : 7877 / 8192 Mio (96,2 %), temp max 64 C
events       : aucun nouveau nvlddmkm 153, aucun Kernel-Power 41
cause de la lenteur : RAM systeme (49,0 Go sur 64), pas la VRAM
                     -> fermer Premiere a rendu la cadence a 116 s/it

GREFFE HAUTES FREQUENCES (alpha 1,0, masque visage, flou 5)
alignement   : (+0,+0) verifie avant greffe sur 5 instants
frames       : 8597 greffees, 0 sans visage
haut visage  : variance 18,3/17,3/17,1 -> 34,6/31,4/35,3
               amplitude 0,83 -> 1,15 | correlation 0,49 -> 0,60
bouche       : variance 10,5/11,1/11,8 -> 24,6/23,6/33,8
               amplitude 0,50 -> 0,78 | correlation 0,13 -> 0,46
fond         : inchange (0,55 -> 0,57), aucun bruit ajoute

FICHIERS (sur le PC)
sortie_latentsync_v5.mp4            214,0 Mo  brut du modele
sortie_latentsync_v5_hf_a1.0.mp4    237,7 Mo  greffe alpha 1,0
sortie_latentsync_v5_final_1080p.mp4 239,2 Mo  + audio d'origine 24 kHz
mesures_hf/mesures_hf.json + planche_hf.png

L'apercu joint est compresse pour passer sous la limite Telegram de 50 Mo."""


def lire_jeton() -> str:
    with io.open(ENV, encoding="utf-8", errors="replace") as fh:
        for ligne in fh:
            ligne = ligne.strip()
            if ligne.startswith("TELEGRAM_BOT_TOKEN="):
                v = ligne.split("=", 1)[1].strip().strip('"').strip("'")
                if v:
                    return v
    raise SystemExit("TELEGRAM_BOT_TOKEN introuvable dans %s" % ENV)


def redac(txt: str, jeton: str) -> str:
    return (txt or "").replace(jeton, "<jeton-masque>")[:300]


def main() -> int:
    jeton = lire_jeton()
    s = requests.Session()

    r = s.get(API % (jeton, "getMe"), timeout=30)
    if not r.ok:
        print("getMe KO :", redac(r.text, jeton))
        return 1
    print("bot : @%s" % r.json()["result"].get("username"))

    r = s.post(API % (jeton, "sendMessage"),
               data={"chat_id": CHAT_ID, "text": RECAP}, timeout=60)
    print("recap  : %s" % ("envoye (msg %s)" % r.json()["result"]["message_id"]
                           if r.ok else "ECHEC " + redac(r.text, jeton)))
    ok = r.ok

    for chemin, legende in (
        (APERCU, "Apercu 1080p compresse (pour la limite Telegram de 50 Mo). "
                 "Fichier complet 239,2 Mo sur le PC : sortie_latentsync_v5_final_1080p.mp4"),
        (COMPLET, "Version complete 1080p + audio 24 kHz"),
    ):
        if not os.path.isfile(chemin):
            print("  %s : absent, ignore" % os.path.basename(chemin))
            continue
        mo = os.path.getsize(chemin) / 1024 / 1024
        if mo > 49:
            print("  %s : %.1f Mo, au-dela de la limite de 50 Mo, non envoye"
                  % (os.path.basename(chemin), mo))
            continue
        with open(chemin, "rb") as fh:
            r = s.post(API % (jeton, "sendDocument"),
                       data={"chat_id": CHAT_ID, "caption": legende},
                       files={"document": fh}, timeout=600)
        if r.ok:
            print("  %s (%.1f Mo) envoye (msg %s)"
                  % (os.path.basename(chemin), mo, r.json()["result"]["message_id"]))
            ok = True
        else:
            print("  %s ECHEC : %s" % (os.path.basename(chemin), redac(r.text, jeton)))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
