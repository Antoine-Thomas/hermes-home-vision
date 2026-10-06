# Techniques de consolidation — patterns code-level

## Split verbatim d'un SKILL.md >200 lignes

Objectif : garder un SKILL.md routeur ≤200l et déplacer le corps verbatim vers `references/<skill>-body/NN-slug.md` (numéroté pour préserver l'ordre), sans perte de contenu.

1. Lire le SKILL.md, splitter sur `---` pour isoler frontmatter et corps.
2. Découper le corps par lignes commençant par `## ` → liste de sections (titre, contenu).
3. Écrire chaque section dans `references/<sub>/NN-<slug>.md` avec header `<!-- Source: <rel>/SKILL.md · section '<titre>' -->`.
4. Reconstruire le SKILL.md : frontmatter intact + titre `#` + liste `- <titre> -> `references/<sub>/NN-slug.md``.
5. Conserver tels quels les `references/`, `scripts/`, `templates/` existants du skill source (déplacement de l'arborescence, jamais suppression).

Le frontmatter (name/description/version/tags) reste verbatim ; seule la structure change, pas le comportement.

## Split topical d'un gros SKILL.md sous Windows (fichiers CRLF)

Variante à préférer quand le SKILL.md pèse des dizaines de Ko et mélange plusieurs domaines : un `references/<slug>.md` par DOMAINE (jamais un par session), et un SKILL.md qui redevient un routeur — frontmatter + référence rapide + un pointeur par section déplacée + index des references. La variante `references/<skill>-body/NN-slug.md` ci-dessus reste bonne pour scinder un fichier linéaire.

1. Inventorier titres ET tailles AVANT de découper : `[(i,l) for i,l in enumerate(lines,1) if re.match(r'^#{1,6} ', l)]`, puis pour chaque titre `len('\n'.join(lines[start-1:next_start-1]).encode('utf-8'))`. Mesurer aussi la lecture hiérarchique : un H2 plus ses H3 peut dépasser le seuil alors que le H2 seul ne l'atteint pas.
2. Choisir la cible = sections > seuil, PLUS assez de sections sous le seuil pour que le routeur reste sous la cible de taille ; vérifier par soustraction (`total - somme des blocs`) avant d'écrire.
3. Écrire chaque bloc **verbatim**, précédé d'un header de traçabilité `<!-- Extrait de <skill>/SKILL.md, lignes a-b — contenu verbatim. -->`, puis relire le fichier depuis le disque et comparer OCTET à OCTET à ce qui a été écrit.
4. Remplacer chaque bloc par son titre + `Voir [references/<slug>.md](references/<slug>.md).` — préfixe `references/` complet, jamais un bare `xxx.md` (devient broken).

Pièges CRLF (Windows) — chacun coûte une passe :
- `raw.decode('utf-8').split('\n')` laisse un `\r` en fin de ligne. Travailler sur `decode('utf-8').replace('\r\n','\n')`, puis réécrire `text.replace('\n','\r\n').encode('utf-8')`.
- `(?m)^description:.*$` : le `.` matche le `\r`, donc `$` matche APRÈS lui et le remplacement supprime le CR → un LF isolé. Utiliser `^description:[^\r\n]*`.
- Une relecture en mode texte convertit `\r\n` → `\n` et fait échouer la comparaison : comparer en octets.

Asserts de non-perte (à exécuter, pas à supposer) :
- conservation : aucune ligne de corps (> 25 car., hors titres) du bloc extrait ne subsiste dans le SKILL.md reconstruit ;
- cibles : toute citation `references/*.md` ou `(references/*.md)` du routeur existe sur disque ;
- frontmatter : `yaml.safe_load` sur le bloc relu, `name` non vide ;
- détection : `hermes skills list | grep <nom>` (colonne Status) + `skill_view(<nom>)` (`linked_files` peuplé), puis `scripts/check_skills_snapshot.py <nom>` → « manifest different » = reconstruction au prochain prompt.

Si `import yaml` échoue dans le python des outils, relancer le script avec le python du venv Hermes (`$LOCALAPPDATA/hermes/hermes-agent/venv/Scripts/python.exe`) — ne pas installer de paquet.

## Check de références cassées sans faux positifs

Piège : une regex du type `(?:references/|\./references/)([A-Za-z0-9_\-/]+\.md)` capture seulement le segment APRÈS `references/`, donc `godmode-body/01-x.md` au lieu du chemin complet. Reconstruire `skill_dir / segment_tronqué` donne 100 % de faux positifs.

Règle : capturer le chemin relatif COMPLET (préfixe `references/` inclus) et vérifier `skill_dir / chemin_complet`. Ignorer les chemins contenant `*`, `{`, ou commençant par `http`. Filtrer aussi les faux positifs hors-skill : `MEMORY.md`, `recovery_runbook.md`, `apps/`, `FINETUNING.md`, et les exemples documentaires (`godmode-body/`, `_inventaire.md` cités dans skill-curator) — ne compter que les refs skill-locales (`references/`/`scripts/`/`templates/`).

## Génération de SKILL.md router

Construire le routeur par liste de lignes + `"\n".join(lines)`, pas par f-string triple-quotes.

Raison : un f-string contenant des backticks (tableaux markdown) et des triple-quotes casse à la compilation avec `SyntaxError: unmatched ...` — l'échec étant à la compilation, AUCUNE ligne du script ne s'exécute (y compris un rename/shutil.move déjà écrit avant dans le même bloc). La forme liste+join est insensible aux backticks.

## Détection de doublons

Deux skills qui partagent les mêmes titres `## ` sont quasi sûrement des doublons (variante plateforme, copie obsolète). Comparer les en-têtes H2 : si une large majorité des sections se recoupe, absorber la plus ancienne en `references/<variant>.md` dans la plus complète, puis archiver l'ancienne.
