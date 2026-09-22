---
name: skill-curator
description: Use when curating the Hermes skill library.
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, curation, consolidation, maintenance, refactoring]
    related_skills: [agent-tooling, hermes-agent]
---

# Skill Curator — consolidation & optimisation de la bibliothèque

## When to Use

- Inventaire complet des skills (comptage, catégorie, lignes, refs)
- Analyse de redondance et proposition Avant/Après par catégorie
- Fusion vers umbrellas class-level ou split >200 lignes vers references/
- Nettoyage, archivage, vérification et rapport de consolidation

## References
- `references/skill-count-diagnostic.md` — diagnostic ecart 84 vs 143 (fantomes `_archive`, snapshot stale) et correction.

## Procedure

### 0. Sauvegarde obligatoire (bloquant)
```bash
TS=$(date +%Y%m%d_%H%M%S)
SRC="$HOME/AppData/Local/hermes/skills"
DST="$HOME/AppData/Local/hermes/skills_backup_${TS}"
cp -r "$SRC" "$DST" && ls -d "$DST" && du -sh "$DST" && find "$DST" -name "SKILL.md" | wc -l
```
Stop si sauvegarde échoue — ne jamais modifier sans backup vérifié.

### 0.1 Verification Consolidation (Verbatim)
Avant d'archiver une skill source consolidée :
1. Verifier que le contenu est *verbatim* dans `umbrella/references/<nom>.md` (comparer lignes et contenu, header de traçabilité obligatoire).
2. Ne jamais archiver sur la foi du seul comptage — la skill doit être absorbée.

### 1. Inventaire
- `find skills -name "SKILL.md" | sort` → liste canonique
- Pour chaque SKILL.md: name (frontmatter), description (1 ligne), catégorie (parent dir), `wc -l`, `references/*.md` count, `stat -c %y` / mtime
- Produire `_inventaire.md` + `_inventaire.json` triés par catégorie

### 2. Analyse de redondance (par catégorie priorisée)
Priorité: software-development > devops > productivity > creative > general > media > mlops > research
Pour chaque catégorie identifier:
a) chevauchement thématique  b) granularité excessive → umbrella  c) obsolètes/vides/doublons  d) références cassées (globs/braces ignorés)
Livrable: `_analyse_redondance.md` avec tableau Avant/Après (umbrella, sources, conservées, archivées) trié par catégorie priorisée

### 3-5. Consolidation (umbrellas + splits + protection)
- Umbrella ≤200l, refs verbatim avec header `<!-- Source: <orig>/SKILL.md (archived YYYY-MM-DD) -->`, supports `references/`/`scripts/`/`templates/` copiés
- Ne jamais toucher une skill protégée (mtime ≥7j avant date du jour) sans demande explicite — épargner aussi les >200l protégées
- Si split H2→`references/<slug>.md`, réécrire les pointeurs du SKILL.md avec préfixe `references/` complet — un bare `xxx.md` devient broken
- **Reference morte — reparation par defaut : supprimer la citation.** Retirer la seule mention en backticks et reformuler au minimum la phrase quand la citation est en milieu de phrase utile ; **ne jamais creer de fichier vide/stub** (cela invente du contenu), ne pas ajouter de commentaire « supprime/deprecated ». Editer chirurgicalement : rien d'autre ne change dans le fichier, meme pas une reformulation voisine. Seule exception : si la SKILL.md est protegee (mtime <7j) et ne doit pas etre touchee, creer alors un stub minimal dans `references/` a la place.

### 6. Vérification (lecture seule)
- `find skills -name SKILL.md ! -path */_archive/* | wc -l` → Y attendu (cible 60-85)
- Check `>200l` hors protégées: 0 violation — lister seulement, ne splitter qu'avec confirmation
- Check refs cassées: parser backticks `references/*.md`/`scripts/*`/`templates/*`, ignorer globs `*`/`{`, placeholders d'exemples; vrai broken = fichier manquant sur disque (hors faux positifs `hermes-operations→MEMORY.md` et `skill-curator` exemples)
- Check umbrellas: chaque umbrella ≤200l, frontmatter `name`+`description` valide, toutes `references/*.md` citées existent
- Test fonctionnel routing (5 cas): scorer chaque skill (name×10 + description×5 + body×0.5) pour requêtes types — ex: WordPress→wordpress-suite, code→code-quality, ffmpeg→video-assembly, SSL→ssl-monitoring, LLM→llm-ops

### 7. Backup & catégories vides
- Backup intact: `du -sh` (Windows: MSYS `du`), `find backup -name SKILL.md | wc -l` = 126, `backup ≈544M/568Mo`
- Diff à blanc: ne pas utiliser `diff -rq` avec chemins `C:/` natifs (échoue sur Windows) — comparer via `pathlib`/`bash -lc` ou comptage `file_set` ; 0 fichier commun modifié = backup intègre
- Catégories vides: supprimer (`shutil.rmtree`) seulement si 0 SKILL.md et (vide ou seul `DESCRIPTION.md`) — sinon lister et laisser tel quel

### 8. Index lisible
- Générer `skills/_index.md` (~180-200l): tableau umbrellas (nom, sources absorbées, nb refs sur disque) + par catégorie liste `**name** — description` + totaux 84/65/24

### 9. Maintenance mensuelle (cron)
- Cron `every 30d` (43200m) léger, lecture seule + rapport `_light_check_YYYYMMDD.md`: réinventaire, check tailles/refs/vides/umbrellas, recommandation backup si >30j
- `deliver=local` par défaut (sortie via `cronjob list`); passer à `telegram` si notification souhaitée
- Ne jamais recréer de backup ni toucher aux protégées sans demande

Livrable: `_analyse_redondance.md` avec tableau Avant/Après: umbrella (nom, portée), skills à fusionner, à conserver (pourquoi), à archiver/supprimer (pourquoi).

### 3. Règles d'optimisation
- Description: une phrase `Use when ...`
- SKILL.md ≤200 lignes — au-delà découper vers `references/<topic>.md`
- 1 responsabilité par fichier de référence, nom explicite par topic (pas `<date>-<incident>.md`)
- Pas de duplication — mutualiser dans référence partagée
- Métadonnées cohérentes: name, description, version, tags

### 4. Nettoyage
- Supprimer `*.bak, *.old`, doublons avérés
- Archiver (pas supprimer) via `hermes curator archive <name>` — déplace vers `.archive/` (dot, exclu du prompt) ET inscrit dans `.curator_suppressed` (anti re-seed des bundled). Ne JAMAIS utiliser `_archive/` (underscore) : non exclu du prompt, et `skills_sync` re-sème les bundled byte-identiques à chaque restart gateway.
- **Snapshot de prompt : auto-invalidé par le manifest — ne le supprime pas par réflexe.** `.skills_prompt_snapshot.json` n'est réutilisé que si `version` **et** `manifest` (signature fichier de chaque `SKILL.md`/`DESCRIPTION.md` sous `skills/`) correspondent encore au disque (`agent/prompt_builder.py:_load_skills_snapshot`). Ajouter, retirer ou éditer un skill change le manifest ⇒ reconstruction au prochain prompt, sans redémarrage de gateway. Sonde lecture seule : `scripts/check_skills_snapshot.py [nom]`.
- La suppression manuelle + `hermes gateway restart` ne se justifie donc que quand l'arbre `skills/` n'a **pas** bougé alors que le prompt doit changer — typiquement `skills.disabled` en config.yaml (aucun fichier touché) ou `.curator_suppressed`. Sonder d'abord, agir ensuite.
- Après tout ajout/archivage : vérifier la détection par `hermes skills list | grep <name>` (colonne Status) **et** `skill_view(<name>)` (description lue, `linked_files` peuplé) — un skill copié mais jamais vu par `skill_view` est un skill mal placé.
- Ne jamais archiver/supprimer une skill touchée dans les 7 derniers jours sans OK explicite

### 5. Consolidation (par umbrella validé)
1. Créer umbrella `skills/<categorie>/<umbrella>/SKILL.md` (≤200l, refs pointant vers fichiers topical)
2. Migrer contenu verbatim en `references/<topic>.md` distincts (pas un fichier par session)
3. Déplacer skills sources vers `.archive/` via `hermes curator archive <name>` (jamais `_archive/`)
4. Append `_merge_log.md` avec date, umbrella, sources, splits

### 6. Vérification
- `find skills -name "SKILL.md" ! -path "*/_archive/*" | wc -l` → Y (cible -30 à -50%)
- Check refs cassées: parser SKILL.md pour `references/*.md` cités, vérifier existence (ignorer globs/brace)
- Recharger: `skills_list` + `skill_view` sur chaque umbrella → valide
- `wc -l` sur chaque SKILL.md actif ≤200

### 7. Rapport
Tableau avant/après par catégorie, liste fusions/archivages/suppressions, taille gagnée, confirmation aucune skill active perdue, chemin backup, restauration `cp -r backup -> skills`.

## Désactiver un skill (non destructif — ≠ archiver)

Désactiver retire un skill du prompt sans le déplacer : le fichier reste, `enable` le rétablit.
Pour les skills jamais chargés qu'on ne veut pas perdre ; archiver (`.archive/`) reste réservé aux
doublons absorbés par un umbrella.

- **`hermes skills disable <nom>` n'existe pas.** La sous-commande est
  `{trust,…,list,…,config}`, et `config` est purement interactif. Le mécanisme réel est la clé de
  config `skills.disabled` (liste de noms) :
  ```bash
  cp "$LOCALAPPDATA/hermes/config.yaml" "$LOCALAPPDATA/hermes/config.yaml.bak_pre_disable"
  hermes config set --force skills.disabled '["skill-a","skill-b"]'
  hermes config get skills.disabled
  ```
  `--force` est obligatoire (`skills.disabled` est hors schéma reconnu, l'écriture est refusée
  sans lui). `hermes config set` réécrit tout le fichier — relire ensuite `model`, `providers`,
  `fallback_providers`, `gateway.multiplex_profiles`.
- **Le `patch`/`write_file` de l'agent refuse `config.yaml`** (« security-sensitive ») : toute
  modification de config passe par `hermes config set`, jamais par une écriture directe.
- **Les désactivés restent listés** par `hermes skills list` avec `Status: disabled` — compter la
  colonne Status, pas les lignes, sinon le total ne bouge pas :
  `hermes skills list | awk -F'│' 'NF>3 {gsub(/ /,"",$6); print $6}' | sort | uniq -c`.
- **Aucun inventaire JSON** : `hermes skills list --json` est rejeté (argument inconnu) et
  `hermes skills snapshot export <f>` ne couvre que les officiels/hub, pas les skills locaux.

## Auditer l'usage réel (source d'autorité : `.usage.json`)

`skills/.usage.json` porte par skill `use_count`, `last_used_at`, `state`, `pinned`, `created_by` ;
`.curator_ledger.jsonl` journalise les patches. `use_count == 0` sur toute la vie = jamais chargé.

- **Ne jamais déduire l'usage d'un grep** sur `state.db` ou SiYuan : les sous-chaînes explosent en
  faux positifs (`box` → « Voicebox », `record`/`windows` partout). Le compteur `.usage.json` est
  le seul signal fiable.
- **Croiser avant de désactiver** : `use_count` → `cron/jobs.json` (tâches planifiées) →
  `scripts/*.py|ps1` → SiYuan. Rester en cas de doute, et ne jamais toucher à la liste « ne jamais
  désactiver » de l'utilisateur.
- **Exclure les sources absorbées** citées dans `_index.md` : elles sont déjà archivées, leur
  `use_count: 0` est normal, les compter noie le vrai gisement.

## Balayage des references mortes (audit -> tableau -> reparation)

1. **La source de verite est le disque, pas le chiffre du rapport.** Un rapport d'auto-revision
donne une *estimation* (« 6 references mortes »). Recompter sur disque, annoncer le nombre reel
(4, 5 ou 7) et le detail par fichier. Ne jamais recreer un fichier pour retomber sur le chiffre
annonce, et ne pas relancer l'audit pour le faire coller.
2. **Verifier que la skill est ACTIVE avant de juger une citation.** `_inventaire.json` peut lister
une skill dont le dossier n'existe plus dans l'arbre actif (absorbee puis deplacee en `.archive/`) :
ses citations remontent alors en faux positifs. Chemin actif absent = rien a corriger, le signaler
tel quel (conclure « faux positif, skill archivee »).
3. **Balayer avec le script, pas a l'œil** : `scripts/scan_references.py` parcourt les SKILL.md
actifs, extrait les citations backticks `references/...` et teste leur existence. Comparateur
correct : normaliser les separateurs (`/` vs `\`), tester le chemin relatif exact, puis retomber sur
le *basename* pour proposer le chemin corrige — un comparateur naif rend 200+ faux positifs et fait
croire a une hecatombe. Ignorer les globs `*`/`{` et les placeholders d'exemple.
4. **Livrer le tableau Avant/Apres AVANT d'appliquer** et attendre l'accord :
`| Skill | Reference cassee | Statut fichier | Correction proposee |`.
5. **Choix de correction** : chemin obsolete -> chemin reel (existence verifiee) ; outil disparu ->
retirer la mention ou mettre l'equivalent actuel ; URL morte -> nouvelle URL ou retrait ; fichier
manquant dont le contenu serait a inventer -> retirer la citation.
6. Apres reparation : reindexer le RAG (`data/rag`, voir la skill `rag-second-cerveau`) puis
committer en citant les fichiers touches.

## Pitfalls

- Archive avant suppression — `hermes curator archive <name>` vers `.archive/` garde rollback ET supprime du re-seed; move manuel vers `_archive/` est inefficace (pas exclu, re-sémé) et casse les imports.
- Vérifie le mtime 7 jours avant toute fusion/archivage — les skills protégées récentes échouent silencieusement si ignorées et forcent une restauration.
- Backup d'abord, inventaire ensuite — sans `skills_backup_<TS>` vérifié, toute erreur de migration devient irréversible.
- Ignore les globs et braces lors du check refs cassées — `references/*.md` n'est pas un fichier manquant.
- Le check de refs cassées doit capturer le chemin COMPLET `references/...` dans son groupe de regex — un groupe non-capturant qui mange le préfixe (`(?:references/|...)`) renvoie `godmode-body/01-x.md` au lieu de `references/godmode-body/01-x.md`, donc 100 % de faux positifs en reconstruisant `skill_dir / chemin_tronqué`.
- Ne touche jamais `nle-video-assembly` et `surveillance-control` sans validation explicite — contraintes utilisateur fortes.
- Split >200l par extraction topical, pas par troncature — couper brutalement perd les procédures que le split devait préserver.
- Un umbrella = une classe de tâche, pas un sac de sessions — un `references/` par session est un échec de forme, pas un objectif.
- Génère les SKILL.md router par liste de lignes + `'\n'.join()`, jamais par f-string triple-quotes — un f-string qui contient backticks et triple-quotes casse à la compilation ('unmatched delimiter'), et l'échec étant atomique, un rename/move écrit plus tôt dans le même script ne s'exécute pas non plus.

## Adopter un skill tiers (vendor / GitHub)

Un skill officiel de vendor arrive distribué pour Claude Code (`claude plugin marketplace add`, `npx skills add`) : ici c'est Hermes CLI, on l'installe à la main. Procédure, commandes et pièges : `references/third-party-skill-install.md`.

- Vérifier l'amont (`git ls-remote <url>`) **avant** d'exécuter un plan d'installation dicté : un plan qui cite un dépôt inexistant invalide tout le reste.
- `SKILL.md` amont **verbatim** ; surcouche locale appendue en fin de fichier, datée de la version + du commit amont ⇒ la mise à jour reste une recopie.
- Fichiers d'adaptation en `references/` et `scripts/`, jamais à la racine du skill — la racine n'est pas exposée dans `linked_files`, un helper racine devient invisible pour les sessions suivantes.
- Rejouer les chiffres du vendor (endpoint, latence, coût, ID de modèle) au lieu de les recopier : les docs/blog tiers se contredisent entre eux, la doc officielle du vendor tranche. Documenter la mesure, pas l'annonce.

## References

- `references/third-party-skill-install.md` — adopter/adapter/mettre à jour un skill de vendor dans Hermes : vérif d'amont, clone en scratch, surcouche locale, emplacement des fichiers, détection, mesures à rejouer
- `scripts/check_skills_snapshot.py` — sonde lecture seule : snapshot de prompt à jour ou non, et si un skill donné est bien vu sur disque
- `references/consolidation-techniques.md` — techniques code-level : split verbatim par `##`, check de refs cassées sans faux positifs, génération de router SKILL.md, détection de doublons
- `scripts/scan_references.py` — balayage lecture seule des citations `references|scripts|templates/*.md` des SKILL.md actifs : tableau skill/citation/statut/correction + liste des entrees d'inventaire perimees
