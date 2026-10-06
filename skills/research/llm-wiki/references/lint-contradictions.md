# Lint contradictions (cron « LLM Wiki contradictions »)

Le lint contradictions est un travail de LECTURE + COMPARAISON : faisable en UN tour
d'agent sur un wiki < ~40 pages. Ne pas chercher a le scripter (contrairement a la
compilation, cf. `compilation-non-agentique.md`).

## When to Use (Quand utiliser)

- Run du job cron « LLM Wiki contradictions » (`0 3 * * *`), ou tout lint
  contradictions demande a la main.
- Une page du wiki cite une source qui pourrait dire autre chose : verifier avant
  d'ecrire l'arbitrage.
- Un fait de configuration du wiki (primaire, `fallback_providers`, ports) doit etre
  confronte a l'etat reel.

## Procedure qui marche

1. Lire `wiki/scripts/prompts/contradictions.md` (il fait foi), `SCHEMA.md`,
   `index.md` et les dernieres lignes de `log.md`.
2. Lire TOUTES les pages en un tour (`read_file` en batch), plus les notes
   `raw/notes/` citees par les pages suspectes.
3. Comparer en priorite : les couples deja `contested: true`, les valeurs
   numeriques (latences, ports, PID, versions, seuils) et les faits d'architecture
   (composition de `fallback_providers`, identite du modele primaire).
4. Relever l'etat reel de `config.yaml` (`%LOCALAPPDATA%\hermes\config.yaml`) :
   c'est la source la plus fraiche pour tout fait de configuration, elle tranche
   souvent seule et confirme ou infirme les notes ingerees.
5. Ecrire avec `patch` (find/replace), jamais un `write_file` complet.

## Pieges mesures

- **Une page peut citer une source qui dit le contraire.** Relire la note `raw/`
  avant d'ecrire « Position A (source X) » : sur ce wiki, `primary-model.md`
  affirmait « primaire = eco » en citant une note qui posait en realite
  `model.default: auto/best-free`.
- **`patch` sur un append en fin de fichier** : ancrer sur UNE ligne finale unique,
  jamais sur les 2-3 dernieres avec leur indentation — le matcher flou a avale une
  phrase de l'entree precedente (`(aucune affirmation ecrasee).`) et a reindente les
  lignes ajoutees de 2 espaces. Toujours relire le diff rendu et corriger.
- **`execute_code` est bloque en run cron** (`approvals.cron_mode`) : passer par
  `terminal` + un script ecrit dans le scratch (`$TMPDIR`), jamais dans le wiki.
- **Verifier par un script independant** du travail d'ecriture : frontmatter complet,
  `type` coherent avec le dossier, tags de la taxonomie, sources de `raw/`
  existantes, liens resolus, `contested`/`contradictions` reciproques, `index.md`
  == fichiers du disque. ~100 lignes de stdlib suffisent.
- **`contested: true` sans `contradictions: [...]`** (ou l'inverse) est une erreur :
  le frontmatter est la source de verite machine, `contradictions.md` n'est que le
  registre lisible. Ne jamais ecraser une position : ajouter une section datee avec
  les deux positions et l'arbitrage, et incrementer `updated`.
- Le job peut tourner DEUX fois dans la meme journee : la 2e entree de `log.md`
  porte la meme date que la 1re — preciser « second passage » dans le corps.
