# Désaturation de la mémoire (règles de décision)

But : quand MEMORY.md ou USER.md sature (> 90 % du seuil fixé), archiver dans SiYuan les entrées périmées et réécrire pour retrouver de la marge. Règles entièrement déterministes, aucune décision d'IA.

## Seuils (marges)
MEMORY.md (limite 2200, cible < 1800, seuil d'alerte 2100). USER.md (limite 1300/1375 selon le lecteur, cible < 1040, seuil d'alerte 1300).
Le seuil d'alerte (lu par `check_memory.ps1`) est celui qui declenche `--auto` ; la cible est l'objectif apres reecriture.

## Règles de décision (déterministes)
Une entrée est **candidate à l'archivage** si elle :
- contient une date > 90 jours (2025-XX-XX, XX/XX/2025, …), OU
- référence un chemin/outil qui n'existe plus sur disque, OU
- mentionne un état terminé/clos/archivé/rejeté/abandonné, OU
- est redondante avec une autre entrée (>80 % similarité de mots-clés), OU
- est superseded par une entrée plus récente sur le même sujet.

**Ne jamais archiver automatiquement** :
- Lignes de section (`## Environnement`, `## Préférences`, …)
- `jamais`, `toujours`, `obligatoire`, `règle`
- Chemins vers outils actifs (router_memoire, indexer, chercher, check_memory) — `desaturer_memoire.py` est le script qui archive : il ne se protege pas lui-meme
- Lignes de taches planifiees (HHhMM, `schtasks`, « planifie ») : elles decrivent des taches vivantes
- Ports actifs (6806, 8200, 9119) : les numeros de port cites sont des references de services vivants

## Garde-fous du script (en plus des regles ci-dessus)
- `--dry-run` est le mode par defaut : sans argument, rien n'est ecrit.
- `--auto` n'ecrit QUE si la taille depasse le seuil d'alerte de `check_memory.ps1` (MEMORY 2100, USER 1300). Entre la cible et le seuil d'alerte le script se contente de le dire dans le log.
- Redondance : seul le membre le plus long d'une paire survit (a longueur egale, le plus recent) — sur une chaine d'entrees quasi identiques il ne reste que la plus longue, le texte integral restant dans l'archive SiYuan.
- Si les candidats pesent plus de 50 % du contenu du fichier, rien n'est ecrit (condensation manuelle).

## Cas particulier : `0 candidate(s)` alors que l'alerte est franchie

Les regles ci-dessus scorrent l'**obsolescence** (chemin mort, date > 90 j, etat clos, redondance),
pas la **longueur accumulee** : un fichier peut depasser le seuil d'alerte avec neuf entrees toutes
« vivantes ». Le script logue alors `0 candidate(s)` / `aucune entree candidate`, et `--auto` ne fait
rien — c'est un angle mort de l'outil, pas une preuve que le fichier est sain. Corriger d'abord les
faits perimes retire typiquement 30-80 caracteres, ce qui ne suffit pas forcement : mesurer apres.

Condensation manuelle, dans cet ordre :

1. `cp` un `.bak` horodate (dans ce cas le script n'en cree aucun).
2. Choisir **une** entree : la note de chantier d'un projet termine est le candidat type
   (« segment 1 fait le … », pointeurs de travail, plan d'execution). La reduire a son noyau durable
   et remplacer le detail par un pointeur vers le skill qui le porte desormais.
3. Editer sur les **OCTETS** : verifier que le motif survient **exactement 1 fois** (`bytes.count`)
   avant de remplacer, et jamais via `read_text`/`write_text` — ils reecrivent toutes les fins de
   ligne en LF et le diff passe d'une ligne a des centaines. Preserver le CRLF et compter les
   separateurs `\r\n§\r\n` avant/apres : le nombre d'entrees ne doit pas bouger.
4. Verifier : `check_memory.ps1` repasse sous le seuil **et** le nombre de separateurs est inchange.
   Ne pas conclure sur un `len(open(f).read())` : universal newlines lit 2 caracteres par ligne de moins.
5. Archiver le texte retire **a cote du `.bak`** (`archive_<FICHIER>_<entree>.txt`) quand SiYuan ne
   doit pas etre touche ; la voie scriptee, elle, archive dans SiYuan — c'est la seule difference.

## Sécurité (ordre strict)
1. **Toujours archiver dans SiYuan avant de modifier MEMORY.md.**
2. Si SiYuan (6806) ne répond pas → ne rien faire, log l'erreur.
3. Écrire `MEMORY.md.bak` avant modification.
4. Vérifier nouvelle taille sous le seuil après écriture, sinon rollback.

## Pièges
- **Ne jamais archiver sans SiYuan actif** : toute perte serait irréversible.
- **Ne jamais forcer sans avoir lu le `--dry-run`** : le dry-run montre exactement ce qui partirait, à visualiser avant toute exécution.
- Les fichiers mémoire sont dans `%LOCALAPPDATA%\hermes\memories\` (sous-dossier), pas à la racine — vérifier là avant de chercher ailleurs.
- **Seuil USER.md = 1300, pas 1375** : c'est `check_memory.ps1` qui définit la limite, et il utilise 1300. Condenser en dessous.

## Procédure concrète d'archivage

**Voie scriptée (normale, depuis 2026-09-17)** : `python "%LOCALAPPDATA%\hermes\scripts\desaturer_memoire.py" --dry-run`
(lire la sortie), puis `--auto`. La tache planifiee « Hermes - desaturer memoire » (dimanche 04h00) lance
`--auto` toute seule ; re-executer ma tache avec `scripts/creer_tache_desaturation.ps1`. Log : `scripts/desaturation.log`.
Tout est automatise : archive SiYuan, `.bak`, reecriture, rollback, garde-fous.

**Voie manuelle (repli, ou condensation plus large que ce que le script ose faire)** : API SiYuan, en 3 étapes.

1. **Lire** le fichier source (`memories/MEMORY.md` ou `memories/USER.md`).
2. **Archiver** dans SiYuan : POST `/api/filetree/createDocWithMd` avec le notebook `20260915170850-sjbhg88` (notebook « journal » du workspace hermes-projects ; le champ API est `notebook`, pas `box`), path `/Archive MEMORY - YYYY-MM-DD` et, si ce chemin est deja pris, `/Archive MEMORY - YYYY-MM-DD-HHMMSS`. Format `markdown`. Le body contient le texte complet de l'ancien fichier wrappe dans un header markdown (verifie : le doc `Archive MEMORY - 2026-09-16` vit bien a la racine du notebook, pas sous `daily note/`).
3. **Réécrire** le fichier avec une version condensée (mêmes infos, sans doublons, sans redites entre USER.md et MEMORY.md). Vérifier la taille en **caractères** avec `scripts/check_memory.ps1` (le lecteur qui fait foi pour l'alerte), ou `len(open(path, encoding='utf-8').read())` — jamais `wc -c`, qui compte les **octets** et gonfle le chiffre (les accents pèsent 2 octets). Le script mesure le CRLF brut : un comptage Python en universal newlines lit ~2 caractères/ligne de MOINS, et n'est donc pas lui qui déclenche l'alerte.
4. **Rollback** : `check_memory.ps1` est **lecture seule** — il n'écrit rien sur disque et ne crée aucun `.bak`. Le backup doit être fait par toi à l'étape 3 (`MEMORY.md.bak`). Ne pas compter sur un backup préexistant : il n'y en a pas.

Exemple de body SiYuan :
```python
api('/api/filetree/createDocWithMd', {
    'notebook': '20260915170850-sjbhg88',   # notebook « journal »
    'path': '/Archive MEMORY - 2026-09-16',  # racine du notebook
    'markdown': f'# Archive {filename} - {date}\n\n> **Statut** : archive\n> **A reverifier** : jamais\n\n{original_content}'
})
```
`desaturer_memoire.py` fait exactement cet appel (jeton SIYUAN_TOKEN lu dans `%LOCALAPPDATA%\hermes\.env`).