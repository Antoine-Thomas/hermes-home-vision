#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
rappel_campagne_rentree.py - Rappel du 1er septembre 2026.

Lance par le cron Hermes (job one-shot, livraison Telegram, no_agent).
La sortie de ce script EST le message envoye : il ne doit donc rien
afficher d'autre que le rappel.

Le script fait un etat des lieux reel au moment du declenchement plutot
que d'envoyer un texte figé : si la liste a change, ou si la campagne a
deja ete envoyee entre temps, le message le dit.
"""
import json
import os
import sys
from collections import Counter
from datetime import date

D = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes",
                 "data", "campagne_rentree")

# Date d'envoi prevue. Le script ne suppose PAS qu'il tourne ce jour-la :
# un test manuel, ou un cron qui rattrape son retard apres une machine
# eteinte, doivent produire un message honnete.
DATE_CIBLE = date(2026, 9, 1)


def lire_liste():
    """[(email, categorie)] depuis emails_campagne.txt"""
    p = os.path.join(D, "emails_campagne.txt")
    out = []
    if not os.path.isfile(p):
        return None
    with open(p, "r", encoding="utf-8", errors="replace") as fh:
        for ligne in fh:
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#"):
                continue
            parts = ligne.split(";")
            if len(parts) >= 4:
                out.append((parts[0], parts[3]))
    return out


def charger_json(nom, defaut):
    p = os.path.join(D, nom)
    if not os.path.isfile(p):
        return defaut
    try:
        with open(p, "r", encoding="utf-8-sig") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return defaut


def main():
    lignes = []
    auj = date.today()
    ecart = (auj - DATE_CIBLE).days

    print("RAPPEL — CAMPAGNE DE RENTREE")
    if ecart == 0:
        print("Aujourd'hui %s : c'est le jour prevu pour l'envoi."
              % auj.strftime("%d/%m/%Y"))
    elif ecart < 0:
        print("Nous sommes le %s. L'envoi est prevu le %s, dans %d jour(s)."
              % (auj.strftime("%d/%m/%Y"), DATE_CIBLE.strftime("%d/%m/%Y"), -ecart))
        print("Ceci est donc un DECLENCHEMENT ANTICIPE (test manuel) :")
        print("ne pas envoyer maintenant, le script d'envoi refusera de toute facon.")
    else:
        print("Nous sommes le %s. La date prevue (%s) est passee de %d jour(s)."
              % (auj.strftime("%d/%m/%Y"), DATE_CIBLE.strftime("%d/%m/%Y"), ecart))
        if ecart <= 3:
            print("Encore exploitable : la fenetre de rentree court jusqu'au 04/09.")
        else:
            print("La fenetre de rentree est passee. Revoir l'angle du message")
            print("avant d'envoyer, ou reporter a une autre accroche.")
    print("")

    if not os.path.isdir(D):
        print("PROBLEME : le dossier de campagne est introuvable.")
        print(D)
        return 0

    lignes = lire_liste()
    if lignes is None:
        print("PROBLEME : emails_campagne.txt est introuvable.")
        print("Regenerer avec :")
        print('  python bin\\reintegrer_contacts.py --source "..\\campagne_aout_2026" --out .')
        print("  python bin\\fusion.py --dossier .")
        return 0
    if not lignes:
        print("PROBLEME : emails_campagne.txt ne contient aucun destinataire.")
        return 0

    cats = Counter(c for _, c in lignes)
    tracking = charger_json("tracking.json", {})
    deja = len([x for x in (tracking.get("sent") or []) if isinstance(x, str)])
    stop = charger_json("blacklist.json", [])

    print("ETAT DE LA LISTE")
    print("  destinataires : %d" % len(lignes))
    for cat in ("ami", "entreprise", "particulier"):
        if cats.get(cat):
            print("    %-11s : %d" % (cat, cats[cat]))
    print("  blacklist STOP : %d adresse(s)" % (len(stop) if isinstance(stop, list) else 0))
    print("")

    if deja:
        print("ATTENTION : tracking.json contient deja %d envoi(s)." % deja)
        print("La campagne semble avoir ete lancee. Le script d'envoi ne")
        print("renverra PAS a ces adresses, mais verifie avant de relancer.")
        print("")

    # les gabarits sont-ils tous la ?
    manquants = [f for f in ("template_ami.html", "template_entreprise.html",
                             "template_particulier.html")
                 if not os.path.isfile(os.path.join(D, "templates", f))]
    if manquants:
        print("PROBLEME : gabarit(s) manquant(s) : %s" % ", ".join(manquants))
        print("")

    duree_h = len(lignes) * 120 / 3600.0
    if ecart == 0:
        print("A FAIRE MAINTENANT, DANS L'ORDRE")
    elif ecart < 0:
        print("A FAIRE LE %s, DANS L'ORDRE" % DATE_CIBLE.strftime("%d/%m/%Y"))
    else:
        print("A FAIRE, DANS L'ORDRE (en retard de %d jour(s))" % ecart)
    print("")
    print("1. Ouvrir PowerShell :")
    print('   cd "%s"' % D)
    print("")
    print("2. Relire le brouillon principal (%d destinataires) :" % cats.get("ami", 0))
    print("   notepad brouillon_ami.txt")
    print("")
    print("3. Simulation, aucun envoi :")
    print("   .\\script_envoi.ps1")
    print("")
    print("4. Test sur toi-meme (2 emails reels) :")
    print('   $env:HERMES_GMAIL_APP_PASSWORD = "le mot de passe d application"')
    print("   .\\script_envoi.ps1 -Test searching.murphy@gmail.com -Confirmer")
    print("   -> verifier le rendu sur mobile ET ordinateur avant d'aller plus loin")
    print("")
    print("5. Envoi reel :")
    print("   .\\script_envoi.ps1 -Confirmer")
    print("   duree estimee : %.1f h (%d contacts x 120 s)" % (duree_h, len(lignes)))
    print("   pour finir plus tot : -Intervalle 90")
    print("")
    print("RAPPELS")
    print("  - Quota Gmail gratuit : ~100-150 envois/jour. %d passe, c'est la" % len(lignes))
    print("    limite haute : ne rien envoyer d'autre depuis cette adresse aujourd'hui.")
    print("  - Ce soir : relever les rebonds et les demandes STOP.")
    print('    python "..\\campagne_aout_2026\\verif_reponses.py"')
    print("    Toute demande STOP va dans blacklist.json le jour meme.")
    print("  - Puis J+3 (04/09) et J+7 (08/09) pour les reponses et le bilan.")
    print("")
    print("Detail complet : commande_envoi.txt et planification.txt")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
