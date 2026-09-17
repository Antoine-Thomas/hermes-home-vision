# Techniques de consolidation — patterns code-level

## Split verbatim d'un SKILL.md >200 lignes

Objectif : garder un SKILL.md routeur ≤200l et déplacer le corps verbatim vers `references/<skill>-body/NN-slug.md` (numéroté pour préserver l'ordre), sans perte de contenu.

1. Lire le SKILL.md, splitter sur `---` pour isoler frontmatter et corps.
2. Découper le corps par lignes commençant par `## ` → liste de sections (titre, contenu).
3. Écrire chaque section dans `references/<sub>/NN-<slug>.md` avec header `<!-- Source: <rel>/SKILL.md · section '<titre>' -->`.
4. Reconstruire le SKILL.md : frontmatter intact + titre `#` + liste `- <titre> -> `references/<sub>/NN-slug.md``.
5. Conserver tels quels les `references/`, `scripts/`, `templates/` existants du skill source (déplacement de l'arborescence, jamais suppression).

Le frontmatter (name/description/version/tags) reste verbatim ; seule la structure change, pas le comportement.

## Check de références cassées sans faux positifs

Piège : une regex du type `(?:references/|\./references/)([A-Za-z0-9_\-/]+\.md)` capture seulement le segment APRÈS `references/`, donc `godmode-body/01-x.md` au lieu du chemin complet. Reconstruire `skill_dir / segment_tronqué` donne 100 % de faux positifs.

Règle : capturer le chemin relatif COMPLET (préfixe `references/` inclus) et vérifier `skill_dir / chemin_complet`. Ignorer les chemins contenant `*`, `{`, ou commençant par `http`. Filtrer aussi les faux positifs hors-skill : `MEMORY.md`, `recovery_runbook.md`, `apps/`, `FINETUNING.md`, et les exemples documentaires (`godmode-body/`, `_inventaire.md` cités dans skill-curator) — ne compter que les refs skill-locales (`references/`/`scripts/`/`templates/`).

## Génération de SKILL.md router

Construire le routeur par liste de lignes + `"\n".join(lines)`, pas par f-string triple-quotes.

Raison : un f-string contenant des backticks (tableaux markdown) et des triple-quotes casse à la compilation avec `SyntaxError: unmatched ...` — l'échec étant à la compilation, AUCUNE ligne du script ne s'exécute (y compris un rename/shutil.move déjà écrit avant dans le même bloc). La forme liste+join est insensible aux backticks.

## Détection de doublons

Deux skills qui partagent les mêmes titres `## ` sont quasi sûrement des doublons (variante plateforme, copie obsolète). Comparer les en-têtes H2 : si une large majorité des sections se recoupe, absorber la plus ancienne en `references/<variant>.md` dans la plus complète, puis archiver l'ancienne.
