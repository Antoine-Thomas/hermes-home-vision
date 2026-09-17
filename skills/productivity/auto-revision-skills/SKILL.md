---
name: auto-revision-skills
description: "Use when l'inventaire des skills doit etre revise."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Hermes, Skills, Maintenance, Qualite]
---

# Auto-revision des skills

## When to Use

Trois declencheurs, le premier atteint suffit :

1. **10 nouveaux skills** crees depuis la derniere revision ;
2. **un mois** sans revision ;
3. **sur demande explicite** de l'utilisateur.

Seuil de revision : **10 nouveaux skills** ou **1x/mois** (30 jours).

L'etat se lit en une commande : `inventaire_skills.py --etat` (nombre de skills, date de la
revision precedente, et si un declencheur est atteint).

A faire aussi quand un doute apparait : « ce skill existe-t-il deja ? », « ce skill parle d'un
outil qui n'existe plus ? », « je refais cette tache a la main pour la troisieme fois ».

## Quick Reference

```
SK="%LOCALAPPDATA%\hermes\skills\productivity\auto-revision-skills\scripts\inventaire_skills.py"

python "%SK%" --etat                                  # ou en est le declencheur
python "%SK%"                                         # rapport du jour (dossier courant)
python "%SK%" --sortie "C:\...\rapport_revision.md"    # rapport a un endroit precis
```

Le rapport contient quatre sections : doublons possibles, skills a references disparues, taches
sans skill, etat du declencheur. Le script est **en lecture seule sur les skills**.

## Procedure

1. **Verifier le declencheur** : `inventaire_skills.py --etat`. Si rien n'est atteint et que la
demande n'est pas explicite, s'arreter la et le dire.
2. **Lancer l'inventaire**, puis **lire le rapport** en entier. Les trois sections ne se valent
   pas : les references mortes sont des faits, les doublons et les manques sont des pistes.
3. **Verifier chaque piste avant de la proposer** : ouvrir les deux skills d'un doublon presume et
   comparer leur `When to Use` — deux skills peuvent partager du vocabulaire sans partager le role.
4. **Ecrire les propositions** a l'utilisateur, une par une, avec la raison et le geste precis :
   fusionner (`references/` du skill conserve), archiver (`hermes curator archive <nom>`),
   corriger une reference, creer un skill a partir d'un script recurrent.
5. **Attendre la validation.** Ne rien appliquer avant. C'est un rapport, pas une execution.

## Pitfalls

- **Ne jamais modifier, deplacer ou supprimer un skill sans validation explicite.** Ni renommer,
  ni fusionner, ni archiver « pour faire propre ». Le rapport propose, l'utilisateur decide.
- La detection de doublons travaille sur le nom et la description : elle produit des faux positifs
  (deux skills qui parlent du meme domaine mais font des choses differentes). Toujours lire avant
  de proposer une fusion.
- La liste des « taches sans skill » est volontairement large : elle signale tout script non
  mentionne. Un script lance une fois n'a pas besoin d'un skill ; c'est la repetition qui compte.
- Un skill peut citer un chemin valide mais perime dans le fond (un dossier deplace, un outil
  renomme). La verification automatique ne voit que l'absence, pas l'obsolescence de sens.
- Le fichier d'etat `revision_skills_etat.json` est ecrit **apres** le rapport : ne pas le
  supprimer, c'est lui qui compte les nouveaux skills.

## Verification

```
python "%SK%" --etat                 # affiche les compteurs et le verdict du declencheur
python "%SK%"                        # ecrit le rapport, affiche le resume
```

Le rapport doit afficher les quatre sections et un resume du type
`skills invoques : N | doublons possibles : N | references mortes : N | scripts sans skill : N`.
Un skill propose a la fusion/archivage/creation est considere traite seulement quand l'utilisateur
l'a valide — et alors, l'index du RAG doit etre relance (`rag-second-cerveau`).

## Historique des revisions

| Date | Skills | Doublons | References mortes | Scripts sans skill | Suite donnee |
|---|---|---|---|---|---|
| 16/09/2026 | 104 | 2 (faux positifs verifies) | 6 | 79 | 7 desactives, 3 meta-skills crees, aucune fusion |
| 15/09/2026 | 96 | 1 (`photo` ~ `record`) | 10 | 74 | en attente de validation utilisateur |

Detail complet : SiYuan `hermes-skills / auto-revision-skills`.
