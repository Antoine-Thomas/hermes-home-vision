---
name: project-context-recovery
description: Use when a lost project or brief must be recovered.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [context, brief, sessions, forensics, verification]
    category: productivity
    related_skills: [auto-context-reset, windows-path-handling, rag-second-cerveau]
---

# Retrouver un projet perdu (contexte tronque)

But : quand une session a perdu son fil (saturation, `/new`, compaction, longue interruption),
reconstruire le VRAI projet — le brief, la cible, ce qui est livre, ce qui reste — a partir de
preuves, et le faire valider AVANT de produire quoi que ce soit.

Regle d'or : **on ne devine pas un brief, on le retrouve.** Un livrable fabrique sur un brief
suppose coute plus cher que le tour d'attente d'une confirmation.

## When to Use

- L'utilisateur dit « contexte perdu », « retrouver le vrai projet », « ce n'est pas le vrai livrable ».
- Apres une saturation ou un `/new` : la session courante ne sait plus ce qui etait demande.
- Un livrable vient d'etre produit et l'utilisateur le declare hors sujet.
- Il faut repondre « quel est le brief et quelle est la cible ? » avec des chemins et des mesures.
- L'utilisateur a redemarre sa machine SANS fermer proprement (« je ne sais plus ou on en etait ») :
  etablir d'abord l'etat (session morte, processus restants, travail interrompu) avant de chercher
  le brief — `references/commandes-de-recuperation.md`, section 6.

## Procedure (dans cet ordre)

1. **Historique d'abord.** `session_search` avec plusieurs requetes COURTES, dans le vocabulaire de
   l'utilisateur, en francais et en anglais. Le brief existe souvent **verbatim comme ancien message
   utilisateur** : le citer mot pour mot avec son lien `@session:default/<id>` vaut mieux que tout
   resume. Chercher aussi les messages de CORRECTION posterieurs : ils remplacent les bornes du brief.
2. **Disque ensuite.** Localiser par nom et par taille (`search_files target='files'` pour un motif
   de nom ; en bash, `find` avec `-size +100M` et `-printf '%s %TY-%Tm-%Td %TH:%TM %p'` pour trier
   par date), gros textes des `pastes/` (briefs colles), puis la base de connaissances (SQL sur les
   blocs). Un resultat VIDE se rapporte comme vide.
3. **Lire le SCRIPT de fabrication, pas les sorties.** Un script d'assemblage nomme ses entrees
   (`HEAD`, `AUDIO`, `PANELS`) et sa sortie (`OUT`) et fixe les timecodes : c'est la definition du
   livrable. Tester l'existence de CHAQUE chemin qu'il nomme.
4. **Verifier par mesure avant d'affirmer.** Exemple : un overlay est-il incruste ? Mesurer une
   bande de l'image (`crop` + `signalstats`, voir la reference) : uniforme = rien, non uniforme =
   contenu. Aucun GPU requis.
5. **Rapporter des candidats, puis STOP.** 3 a 5 candidats avec chemin et valeurs MESUREES
   (duree, taille, frames), la contradiction eventuelle entre versions du brief, et des questions
   numerotees. Ne rien creer, ne rien modifier, ne rien « reparer » avant la reponse.

Recettes et commandes exactes : `references/commandes-de-recuperation.md`.

## Regles

- **La mesure avant l'adjectif.** Une duree se donne en chiffres, et se compare a la facon dont
  l'utilisateur decrit la cible : « environ 6 min » pour un fichier mesure a 6:59,97 se tranche en
  donnant le chiffre, pas en arrondissant dans le sens de l'utilisateur.
- **Une absence doit etre MESUREE, pas deduite.** Un `OUT` introuvable, une entree manquante :
  l'enoncer comme un fait verifie (test d'existence `[ -e ]`, recherche sous plusieurs formes de
  chemin) — jamais comme une supposition. Une entree absente est souvent LA raison pour laquelle
  rien n'a ete livre.
- **Le nom du fichier est une information.** Un suffixe (`_sans_carte`, `_v6`, `_ALT`, `_alignee`)
  enonce un etat : le lire, et chercher le jumeau manquant qu'il sous-entend.
- **La phase de recuperation est en LECTURE SEULE.** Aucune correction, aucun nouveau brief, aucun
  skill touche avant la validation de l'utilisateur.
- **Ne pas « reparer » d'office un script dont les chemins d'entree sont perimes** : le signaler
  dans le rapport, proposer la reprise, attendre le GO.

## Pieges

- **Une sonde muette prise pour une donnee.** Une mesure dont on jette stderr rend une ligne vide
  la ou on attend une valeur : c'est un echec de chemin, pas une metadonnee absente (voir
  `windows-path-handling`, Regle 3).
- **Le brief n'est pas forcement un fichier.** Ne pas conclure « aucun brief » parce que le disque
  et la base de connaissances sont muets : il peut n'exister que dans l'historique de session.
- **Deux versions du brief coexistent souvent** (un brief initial plus des corrections, ou une
  refonte posterieure). Ne pas choisir en silence : les presenter cote a cote et demander.
- **Le livrable intermediaire n'est pas le livrable.** Un fichier nomme `..._final_v1_sans_carte`
  peut etre conforme au brief SAUF un element absent (la carte de fin) : le dire, sinon on relance
  un rendu complet pour rien.

## Voir aussi

- `auto-context-reset` — detection de la saturation et conservation du travail avant le `/new`.
- `windows-path-handling` — chemins natifs, sondes natives, sorties muettes.
