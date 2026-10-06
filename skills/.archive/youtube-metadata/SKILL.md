---
name: youtube-metadata
description: "Use when writing YouTube titles, chapters and tags."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [youtube, metadata, seo, chapters, video, publication]
    category: social-media
---

# Metadonnees YouTube d'une video

## When to use

En fin de production, une fois le livrable fige : titre, description, chapitres, tags, hashtags,
prets a coller dans YouTube Studio. Vaut pour toute video publiee (serie, tutoriel, demo).

Le principe qui gouverne tout le reste : **les metadonnees se derivent du media, pas du brief**. Le
brief decrit ce que l'utilisateur veut ; seuls le SRT, le texte de narration et les titres reellement
affiches a l'ecran disent ce que la video contient.

## Ordre

1. Lire le **SRT aligne sur le livrable** : seule source fiable des timecodes. Verifier que son dernier
timecode correspond a la duree du fichier livre — un SRT d'une version precedente place les sections
au mauvais endroit.
2. Lire le **texte de narration** pour rediger la phrase d'explication de chaque chapitre.
3. Relever les **titres EXACTS affiches a l'ecran** (source du generateur de panneaux, ou relecture du
   PNG). Ni les libelles du brief ni ceux de la narration ne font foi : un panneau peut s'intituler
   « Recherche hybride + RRF » alors que la voix dit « dense + BM25 + RRF ». L'explication du chapitre
   ajoute ce que la voix dit, le titre reste celui de l'ecran.
4. **Compter les caracteres avec un script** (titre, tags) avant de livrer, jamais a l'oeil.
5. Ecrire le fichier de metadonnees, chaque bloc pret a copier-coller, sections dans l'ordre demande.
6. Rapporter le contenu du fichier in extenso + les ecarts au brief.

## Regles dures

Elles font echouer le lot ENTIER, pas seulement la ligne concernee.

- Premier chapitre exactement a `00:00`, au moins 3 chapitres, et **chaque chapitre >= 10 s**. Un seul
  chapitre trop court fait rejeter la liste entiere : l'utilisateur croit avoir des chapitres et n'en a
  aucun. Fusionner le dernier creneau trop court dans le precedent, et le signaler explicitement.
- Titre **<= 60 caracteres** (compte exact). Tags : **500 caracteres maximum** pour le total du CSV.
- Un chapitre invalide demande dans le brief ne s'applique pas : livrer la version VALIDE et signaler
  l'incoherence. Appliquer la consigne a la lettre livrerait des metadonnees silencieusement cassees.
- Ne rien inventer : aucun terme absent de la video dans les tags (modele, techno ou buzzword cite
  nulle part). Un tag non defendable est un risque si la plateforme audite la pertinence.
- Nettoyer le balisage avant collage : une description issue d'un script contient souvent du gras
  markdown ou des sequences echappees qui cassent la detection automatique des chapitres.
- Garder le vocabulaire volontairement divergent entre l'ecran et la voix (nom de marque ecrit,
  graphie phonetique prononcee). Ne pas « harmoniser » sans le demander.

## Structure du livrable

Un fichier unique, sections dans cet ordre :

1. **TITRE recommande** — le titre, son compte de caracteres, le mot-cle cible, l'argument CTR.
2. **TITRES ALTERNATIFS** — chacun mesure, avec l'argument et le mot-cle.
3. **DESCRIPTION complete** — accroche dans les ~150 premiers caracteres (seuls visibles avant
   « Plus »), puis la liste des points, puis les chapitres avec une ligne d'explication chacun.
4. **CHAPITRES** — bloc collable seul (format `MM:SS Titre`), avec le controle des seuils rappele.
5. **TAGS CSV** — avec le compte sur 500.
6. **MOTS-CLES viraux** — requetes a viser, reutilisables en commentaire epingle ou en Shorts.
7. **HASHTAGS** — rappeler que 3 seulement s'affichent au-dessus du titre, les autres sont indexes.
8. **NOTES** — strategie, ecarts au brief, et tout ce qui reste a valider.

## Quand la video est refaite

Un changement de mise en page (taille d'incrustation, duree d'affichage, respiration entre sections)
ne deplace pas forcement les departs de chapitres : **verifier avant de reecrire** les timecodes.
Mettre a jour l'en-tete (nom du nouveau fichier livre), ajouter une note de structure, et garder
titre, tags, hashtags et mots-cles si le contenu parle n'a pas bouge.

Ne pas annoncer comme livre un fichier qui n'existe pas encore (rendu non lance, ou gate sur une
validation) : le dire, et donner le nom comme une intention.

## Rapport

Contenu du fichier in extenso, nom du fichier video final, liste des chapitres, ecarts au brief.

## Notes

- Un rendu de video distinct (mise en page, duree) est un autre chantier : ce skill ne produit que les
  metadonnees, et suppose le livrable fige.
