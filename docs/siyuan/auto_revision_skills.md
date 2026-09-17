# auto-revision-skills

> **Statut** : actif
> **Dernière mise à jour** : 15/09/2026

## Fait

Le skill `productivity/auto-revision-skills` et son outil `scripts/inventaire_skills.py` forment la
revision periodique du dossier de skills : ils **inventorient** et **proposent**, l'utilisateur
decide.

Trois declencheurs, le premier atteint suffit :

1. **10 nouveaux skills** crees depuis la derniere revision ;
2. **une semaine** sans revision (le vendredi) ;
3. **sur demande explicite**.

Ce que l'outil detecte, mecaniquement :

| Section | Ce qu'elle cherche | Nature |
|---|---|---|
| Doublons possibles | deux skills dont le nom ou la description se recouvrent (similarite ≥ 0,34) | **piste** — a lire avant de proposer une fusion |
| Skills a references disparues | chemins de fichiers et commandes cites qui n'existent plus sur la machine | **fait** |
| Taches sans skill | scripts de travail qu'aucun skill ne mentionne | **piste large** — c'est la repetition qui compte |
| Etat du declencheur | compteurs « nouveaux skills » et « jours depuis la revision » | fait |

Ce qu'il ne fait **jamais** : modifier, deplacer, renommer, fusionner, archiver ou supprimer un
skill. Le rapport propose ; rien ne s'applique sans validation explicite.

### Premiere revision — 15/09/2026

| Indicateur | Resultat |
|---|---|
| Skills inventaries | **96** |
| Doublons possibles | 1 — `photo` et `record` (0,36 de recouvrement) |
| References mortes | 10 skills citent un chemin ou une commande introuvable |
| Scripts sans skill | 74 |
| Declencheur | « 10 nouveaux skills » non atteint, « une semaine » non atteinte (premiere revision) |

Aucune proposition appliquee : la liste attend la validation de l'utilisateur.

## Reste a faire

- **Attendre l'arbitrage de l'utilisateur** sur les trois listes de la premiere revision. C'est le
  seul point ouvert de ce chantier.
- `photo` et `record` sont deux skills courts sur la capture (webcam / ecran) : a lire ensemble
  avant toute fusion. Le recouvrement de description ne prouve pas le doublon.
- Les 10 skills a references mortes : verifier si c'est le chemin qui a bouge (correction) ou
  l'outil qui a disparu (archivage).
- Le premier vendredi tombera le **vendredi 18/09/2026** : relancer alors `--etat` pour voir si le
  declencheur hebdomadaire s'active comme prevu.

## Pieges

- La detection de doublons produit des **faux positifs** par construction (deux skills d'un meme
  domaine, roles differents). Toujours comparer les sections `When to Use` avant de proposer.
- La liste « taches sans skill » est volontairement large : elle inclut des scripts lances une
  seule fois. Un script merite un skill a partir de la **deuxieme** utilisation manuelle.
- L'outil voit ce qui **manque**, pas ce qui est **perime** : un chemin peut exister encore alors
  que le contenu a change de sens. La relecture humaine reste indispensable.
- Le fichier d'etat `revision_skills_etat.json` est ecrit **apres** le rapport, dans le dossier du
  skill. Ne pas le supprimer : c'est lui qui compte les nouveaux skills depuis la derniere revision.
- Le script s'execute avec un Python qui a `re` et `json` seulement : n'importe quel venv convient,
  aucun besoin de GPU.

## Commandes

```
SK="%LOCALAPPDATA%\hermes\skills\productivity\auto-revision-skills\scripts\inventaire_skills.py"

python "%SK%" --etat                                   # ou en est le declencheur
python "%SK%"                                          # rapport du jour
python "%SK%" --sortie "C:\Users\searc\docs\rapport_revision.md"

# appliquer une proposition, seulement apres validation
hermes curator archive <nom-du-skill>

# apres toute modification de skill : relancer l'index du RAG
%LOCALAPPDATA%\hermes\data\rag\venv\Scripts\python.exe %LOCALAPPDATA%\hermes\data\rag\indexer.py
```

Skill : `productivity/auto-revision-skills` (section « Historique des revisions » tenue a jour).
