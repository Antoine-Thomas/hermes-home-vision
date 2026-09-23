# -*- coding: utf-8 -*-
"""Incrustations du volet 7 : carton de titre, schema d'architecture, snippet OpenRouter, CTA.

Meme modele que faire_overlays_v6.py : PNG 1920x1080 RGBA dans overlays_v7/, polices Windows,
meme palette, memes positions, horodatage dans overlay_timing_v7.json {ecran, start, end}.

ATTENTION - TEXTES EN ATTENTE DE VALIDATION (question envoyee sur Telegram le 23/09 a 22:44) :
  - titre retenu par l'utilisateur : « JEV + llmwiki avec Hermes » ;
  - le sous-titre est a choisir parmi SUBTITRES (reponse A / B / C) ;
  - les textes des 3 incrustations sont ceux du volet 6, repris tels quels : a confirmer
    (version 1.3 ? lien GitHub ? numeros de ports ?).
Ne lancer ce script qu'apres validation : chaque chaine douteuse est marquee ci-dessous.

Les valeurs techniques affichees sont celles du depot (README v1.3, branche main) :
  OmniRoute 20128, Proxy NIM 20200, Backend 9119, RAG 8200, SiYuan 6806,
  Jev / OpenRouter, modele typesafe/jev-1.13, ~0,4 s par appel, ~1,3e-05 $ (entree facturee).
Aucune vraie cle n'est affichee : le placeholder est masque (sk-or-v1-****).
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

OUT = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\overlays_v7"
W, H = 1920, 1080

# --- textes du carton de titre (volet 7) -------------------------------------------------
TITRE = "JEV  +  llmwiki  avec  Hermes"
SUBTITRES = {
    "A": "Le second cerveau qui se compile tout seul",
    "B": "JEV et Hermes : relier les LLM a ta base de connaissances",
    "C": "llmwiki + Hermes : le wiki qui se met a jour tout seul",
}
# Choix du sous-titre : variable d'environnement SOUS_TITRE=A|B|C (defaut B, choisi le 23/09).
SELECTION = os.environ.get("SOUS_TITRE", "B").strip().upper()
SOUS_TITRE = SUBTITRES.get(SELECTION, SUBTITRES["A"])
EDITION = "7e edition  \u00b7  Hermes 1.3 Psychopomp"   # a confirmer (6e edition au v6)

FONT = {
    "titre": r"C:\Windows\Fonts\segoeuib.ttf",
    "gras": r"C:\Windows\Fonts\segoeuib.ttf",
    "texte": r"C:\Windows\Fonts\segoeui.ttf",
    "mono": r"C:\Windows\Fonts\consola.ttf",
    "monob": r"C:\Windows\Fonts\consolab.ttf",
}
C_FOND = (12, 15, 20, 238)
C_CARTE = (24, 30, 40, 255)
C_BORD = (78, 161, 255, 255)
C_TITRE = (255, 255, 255, 255)
C_TEXTE = (205, 214, 228, 255)
C_ACCENT = (78, 161, 255, 255)
C_DIM = (150, 162, 180, 255)


def police(role: str, taille: int):
    return ImageFont.truetype(FONT[role], taille)


def carte(d: ImageDraw.ImageDraw, box, rayon=22, fond=C_FOND, bord=C_BORD, ep=3):
    d.rounded_rectangle(box, radius=rayon, fill=fond, outline=bord, width=ep)


def texte_centre(d, box, txt, font, couleur):
    x0, y0, x1, y1 = box
    g = d.textbbox((0, 0), txt, font=font)
    d.text(((x0 + x1 - (g[2] - g[0])) / 2 - g[0], (y0 + y1 - (g[3] - g[1])) / 2 - g[1]),
           txt, font=font, fill=couleur)


def flitre(d, x0, y0, x1, y1, couleur=C_ACCENT, ep=4, fleche="bas"):
    d.line([(x0, y0), (x1, y1)], fill=couleur, width=ep)
    t = 16
    if fleche == "bas":
        d.polygon([(x1 - t, y1 - t * 1.4), (x1 + t, y1 - t * 1.4), (x1, y1)], fill=couleur)
    elif fleche == "haut":
        d.polygon([(x1 - t, y1 + t * 1.4), (x1 + t, y1 + t * 1.4), (x1, y1)], fill=couleur)


def bloc(d, box, titre, lignes, t_titre=34, t_texte=26, bord=C_BORD):
    carte(d, box, rayon=20, fond=C_CARTE, bord=bord, ep=3)
    x0, y0, x1, y1 = box
    d.text((x0 + 26, y0 + 18), titre, font=police("gras", t_titre), fill=C_TITRE)
    y = y0 + 18 + t_titre + 16
    for l in lignes:
        d.text((x0 + 26, y), l, font=police("texte", t_texte), fill=C_TEXTE)
        y += int(t_texte * 1.34)


def vide(fond=None):
    im = Image.new("RGBA", (W, H), fond or (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def overlay_schema():
    im, d = vide()
    carte(d, (150, 90, 1770, 990), rayon=28)
    d.text((190, 118), "Architecture Hermes 1.3  \u00b7  3 profils isoles, services communs",
           font=police("gras", 38), fill=C_TITRE)

    # rangee 1 : trois profils
    y0, hb, wb, gout = 196, 168, 440, 60
    xs = [190, 190 + wb + gout, 190 + 2 * (wb + gout)]
    profils = [("default (bureau)", ["config.yaml", ".env dedie", "bot Telegram 1"]),
               ("watch", ["config.yaml", ".env dedie", "bot Telegram 2"]),
               ("veille", ["config.yaml", ".env dedie", "bot Telegram 3"])]
    for x, (nom, lignes) in zip(xs, profils):
        bloc(d, (x, y0, x + wb, y0 + hb), nom, lignes, t_titre=32, t_texte=25)
    for x in xs:
        flitre(d, x + wb / 2, y0 + hb, x + wb / 2, y0 + hb + 44, fleche="bas")
    d.line([(xs[0] + wb / 2, y0 + hb + 44), (xs[2] + wb / 2, y0 + hb + 44)], fill=C_ACCENT, width=4)
    flitre(d, W / 2, y0 + hb + 44, W / 2, y0 + hb + 58, fleche="bas")

    # rangee 2 : routeurs
    y1 = y0 + hb + 58
    bloc(d, (190, y1, 190 + 700, y1 + 130), "OmniRoute   20128",
         ["routeur LLM, combos eco / nvidia-stack"], t_titre=30, t_texte=25)
    bloc(d, (1020, y1, 1730, y1 + 130), "Proxy NIM   20200",
         ["normalise les appels NVIDIA NIM"], t_titre=30, t_texte=25)
    flitre(d, W / 2, y1 + 130, W / 2, y1 + 168, fleche="bas")

    # rangee 3 : les trois services du second cerveau
    y2 = y1 + 168
    w3, g3 = 500, 55
    x3 = [190, 190 + w3 + g3, 190 + 2 * (w3 + g3)]
    services = [("Backend   9119", ["coeur Hermes", "API + dashboard"]),
                ("RAG   8200", ["index 2e cerveau", "recherche /sante"]),
                ("SiYuan   6806", ["base de connaissances", "6 notebooks"])]
    for x, (nom, lignes) in zip(x3, services):
        bloc(d, (x, y2, x + w3, y2 + 150), nom, lignes, t_titre=30, t_texte=24)
    for x in x3:
        flitre(d, x + w3 / 2, y2 + 150, x + w3 / 2, y2 + 186, fleche="bas")
    d.line([(x3[0] + w3 / 2, y2 + 186), (x3[2] + w3 / 2, y2 + 186)], fill=C_ACCENT, width=4)
    flitre(d, W / 2, y2 + 186, W / 2, y2 + 196, fleche="bas")

    # rangee 4 : Jev
    y3 = y2 + 196
    bloc(d, (420, y3, 1500, y3 + 118), "Jev  \u00b7  OpenRouter   (typesafe/jev-1.13)",
         ["choix rapides 2-5 options  \u00b7  ~0,4 s  \u00b7  ~1,3e-05 $ / appel"], t_titre=30, t_texte=25)
    im.save(os.path.join(OUT, "overlay_01_schema.png"))
    return "overlay_01_schema.png"


def overlay_snippet():
    im, d = vide()
    carte(d, (330, 250, 1590, 830), rayon=28)
    d.text((370, 285), "Jev sur OpenRouter  \u00b7  installation", font=police("gras", 40), fill=C_TITRE)
    y = 360
    lignes = [("# fichier .env", C_DIM),
              ("OPENROUTER_API_KEY=sk-or-v1-****", C_TITRE),
              ("", C_TEXTE),
              ("# modele a appeler", C_DIM),
              ("typesafe/jev-1.13", C_TITRE),
              ("", C_TEXTE),
              ("# reponse typee, sans texte", C_DIM),
              ("noul : oui / non        choice : 2-5 options        score : note", C_TEXTE),
              ("", C_TEXTE),
              ("# mesure : 0,37-0,44 s   \u00b7   entree facturee, sortie gratuite", C_DIM)]
    for l, coul in lignes:
        d.text((378, y), l, font=police("mono", 27), fill=coul)
        y += 42
    im.save(os.path.join(OUT, "overlay_02_openrouter.png"))
    return "overlay_02_openrouter.png"


def overlay_lien():
    im, d = vide()
    carte(d, (230, 180, 1690, 900), rayon=28)
    d.text((280, 215), "Version 1.3  \u00b7  Hermes Psychopomp", font=police("gras", 46), fill=C_TITRE)
    carte(d, (280, 300, 1640, 360), rayon=14, fond=(28, 44, 72, 255), bord=C_BORD, ep=2)
    d.text((304, 316), "github.com/Antoine-Thomas/hermes-home-vision/releases/tag/v1.3",
           font=police("mono", 28), fill=C_ACCENT)
    y = 405
    d.text((280, y), "Installation rapide", font=police("gras", 32), fill=C_TITRE)
    y += 58
    for l in ["git clone https://github.com/Antoine-Thomas/hermes-home-vision.git",
              "cd hermes-home-vision",
              "git checkout v1.3"]:
        d.text((292, y), l, font=police("mono", 28), fill=C_TEXTE)
        y += 46
    d.line([(280, y + 22), (1640, y + 22)], fill=(60, 70, 88, 255), width=2)
    d.text((280, y + 52), "Depot public  \u00b7  1.1 originale (v1.1-original)  \u00b7  1.2 stable (v1.2-ameliorations)",
           font=police("texte", 27), fill=C_DIM)
    d.text((280, y + 104), "Pouce  \u00b7  Abonnement  \u00b7  Merci d'avoir suivi", font=police("gras", 32), fill=C_TITRE)
    im.save(os.path.join(OUT, "overlay_03_lien_v13.png"))
    return "overlay_03_lien_v13.png"


def taille_auto(d, txt, role="titre", maxi=96, mini=56, limite=1230):
    """Taille de police qui tient dans la largeur disponible (titre long = plus petit).

    Le volet 7 a un titre plus long que le volet 6 : a 96 px il passait sous le logo
    (x=1440). On reduit par pas de 2 px jusqu'a tenir dans « limite ».
    """
    for taille in range(maxi, mini - 1, -2):
        f = police(role, taille)
        if d.textbbox((0, 0), txt, font=f)[2] <= limite:
            return f, taille
    return police(role, mini), mini


def carton_titre():
    im, d = vide(fond=(10, 12, 16, 255))
    d.rectangle((0, 0, W, 12), fill=C_ACCENT)
    f_titre, t_titre = taille_auto(d, TITRE, "titre")
    f_sous, t_sous = taille_auto(d, SOUS_TITRE, "texte", maxi=46, mini=30)
    d.text((170, 330), TITRE, font=f_titre, fill=C_TITRE)
    d.text((170, 470), SOUS_TITRE, font=f_sous, fill=C_TEXTE)
    d.text((170, 560), EDITION, font=police("gras", 40), fill=C_ACCENT)
    print(f"taille du titre : {t_titre} px (largeur "
          f"{d.textbbox((0, 0), TITRE, font=f_titre)[2]} px) / sous-titre : {t_sous} px")
    logo = os.path.join(r"C:\Users\searc\AppData\Local\hermes\data\video_youtube",
                        "hermes_logo_icon.png")
    if os.path.exists(logo):
        lg = Image.open(logo).convert("RGBA").resize((260, 260), Image.LANCZOS)
        im.alpha_composite(lg, (1440, 380))
    d.text((170, 900), "github.com/Antoine-Thomas/hermes-home-vision", font=police("mono", 30), fill=C_DIM)
    im.save(os.path.join(OUT, "titre_intro_v7.png"))
    return "titre_intro_v7.png"


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    print(f"sous-titre retenu ({SELECTION}) : {SOUS_TITRE}")
    for f in (carton_titre(), overlay_schema(), overlay_snippet(), overlay_lien()):
        p = os.path.join(OUT, f)
        print(f"{f:32s} {Image.open(p).size}  {os.path.getsize(p)/1024:6.0f} Ko")
    print(f"dossier : {OUT}")
