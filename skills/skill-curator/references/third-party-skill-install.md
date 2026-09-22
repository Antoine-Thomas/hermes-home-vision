# Adopter un skill tiers (vendor, GitHub) dans Hermes

## Quand

Un skill officiel de vendor, distribué pour Claude Code (`claude plugin marketplace add …`,
`npx skills add …`) ou un dépôt de skills hébergé sur GitHub, qu'on veut utiliser dans Hermes CLI.
Vaut aussi pour la mise à jour d'un skill vendor déjà installé.

## Procédure

1. **Vérifier l'amont avant d'exécuter le plan.** `git ls-remote <url>` (HEAD + tags). Un plan dicté
   par un tiers (ou par l'utilisateur) peut citer un dépôt qui n'existe pas : 2 s de vérification
   décident si le reste du plan vaut la peine d'être suivi.
2. **Cloner dans le scratch Hermes**, chemin natif à slash avant :
   ```bash
   SCRATCH="C:/Users/<user>/AppData/Local/hermes/cache/scratch/<nom>"
   rm -rf "$SCRATCH"; git clone --depth 1 <url> "$SCRATCH"
   find "$SCRATCH" -type f -not -path '*/.git/*'
   ```
   `git`/`python` sont des binaires natifs : `/c/...` n'est pas traduit. Le scratch Hermes est purgé
   sous 72 h — ne pas s'en servir comme emplacement de mise à jour.
3. **Lire le `SKILL.md` amont en entier** avant d'installer : frontmatter (`name` = nom du dossier
   cible), dépendances, commandes d'installation citées par le vendor.
4. **Installer verbatim** : copier le dossier du skill dans `%LOCALAPPDATA%/hermes/skills/<name>/`.
   Copier via `python -c "shutil.copy2(...)"` plutôt que `cp` MSYS quand l'exactitude compte, puis
   comparer (`filecmp`) pour *prouver* le verbatim au lieu de l'affirmer.
5. **Surcouche locale en fin de fichier, jamais au milieu.** Ajouter une section finale marquée
   (`## Hermes — …`) portant : version + commit amont, la route/le helper réellement câblés, les
   pointeurs vers `references/` et `scripts/`, et la façon de mettre à jour. Ne pas réécrire le corps
   amont : la mise à jour doit rester « recopier l'amont + ré-appender la section ».
6. **Emplacement des fichiers d'adaptation** : `references/<topic>.md` et `scripts/<helper>.py`.
   Jamais à la racine du skill — seule exception tolérée, le `LICENSE` amont. La racine n'apparaît
   pas dans `linked_files`, donc un helper racine est invisible pour les sessions suivantes.
7. **Vérifier la détection** : `hermes skills list | grep -i <name>` (Status = `enabled`) puis
   `skill_view(<name>)` (description lue, `linked_files` peuplé). Le snapshot de prompt s'auto-invalide
   (cf. SKILL.md) : aucun redémarrage de gateway pour un ajout.
8. **Documenter la provenance** dans la surcouche (URL, commit, tag, date, ce qui est amont vs local) :
   c'est ce qui rend la mise à jour et l'audit possibles six mois plus tard.

## Pièges

- **Les commandes d'installation du vendor ne s'appliquent pas ici.** Ne pas lancer `claude plugin …`
  ni `npx skills add …` « pour voir » : les remplacer par la copie manuelle et le dire explicitement
  dans la surcouche, sinon la prochaine session les relancera.
- **Les chiffres des docs et blogs tiers sont souvent périmés** (endpoints, noms de modèles, prix)
  et se contredisent entre eux. La doc **officielle** du vendor tranche : un endpoint cité par des
  blogs a déjà été contredit par la doc officielle. Rejouer un appel réel et écrire les mesures
  (latence, coût, ID de modèle daté tel que renvoyé par l'API) plutôt que les valeurs annoncées.
- **Contrôler une clé sans jamais l'afficher** — longueur + préfixe seulement :
  ```bash
  awk -F= '/^MA_CLE=/{v=substr($0,index($0,"=")+1); gsub(/["\r]/,"",v); print "len="length(v)" prefix="substr(v,1,3)}' "$LOCALAPPDATA/hermes/.env"
  ```
  Un appel réseau réussi vaut validation de la clé : le rapporter comme tel, pas comme « clé présente ».
- **Description du vendor souvent longue et multi-lignes** (>60 car.) : elle fonctionne comme trigger
  mais viole la convention locale `Use when …`. La signaler à l'utilisateur, ne pas la réécrire d'office
  (elle vient de l'amont et sert de base à la mise à jour).
- **`$env:TEMP` (PowerShell) ≠ `$TEMP`/`/tmp` (bash MSYS)** : un plan rédigé en `$env:TEMP` se traduit
  par le scratch Hermes, jamais par un `/tmp` passé à un binaire natif.
- **Valider les affirmations de l'utilisateur plutôt que les recopier** : un « testé avec succès, X s,
  Y $/req » annoncé se revérifie par un appel réel avant d'entrer dans un fichier de config — l'ordre de
  grandeur se confirme ou non, et c'est la valeur mesurée qu'on écrit.

## Après l'installation

- Rien à faire côté prompt (snapshot auto-invalidé). La mise à jour de `_inventaire.json` / `_index.md`
  relève du check mensuel du curator, sauf demande explicite de l'utilisateur.
