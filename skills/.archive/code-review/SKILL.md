---
name: code-review
description: "Revue d'un depot Git : bugs, dette, secu, tests, issues."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [revue, code-review, git, dette-technique, securite, tests, github, issues, refactoring]
    related_skills: [codebase-inspection, github-issue-to-pr, dogfood, test-driven-development, requesting-code-review]
prerequisites:
  commands: [python, git]
---

# Revue de code d'un depot Git

Analyse un depot, produit des faits mesures (pas des impressions), redige des
issues GitHub pretes a poster, et sert de base pour ecrire les tests manquants.

Le principe : **le script mesure, l'agent juge**. Aucun finding ne doit sortir
de la revue s'il n'est pas dans le rapport du script ou verifie par lecture
du code.


## When to Use — quand l'utiliser

- "fais une revue de mon code", "analyse ce depot", "qu'est-ce qui cloche"
- "ou est ma dette technique", "de quoi j'ai besoin en tests"
- "cree les issues GitHub pour ce qu'il faut corriger"
- avant une reprise de projet, une livraison, ou l'arrivee d'un autre dev
- apres une phase de developpement rapide (verifier ce qui a ete sacrifie)

Pour une revue de code **pre-commit** sur un diff en cours, preferer
`requesting-code-review`. Ce skill-ci travaille sur le depot entier.

## Fichiers

| Chemin | Role |
|---|---|
| `~/AppData/Local/hermes/data/hermes-optim/bin/code_review.py` | l'analyseur (stdlib uniquement) |
| `<repo>/.code-review/` | sortie par defaut : `review_<stamp>.json` + `.md` + `issues/` |

## Procedure

### 1. Mesurer

```bash
cd ~/AppData/Local/hermes/data/hermes-optim
./.venv/Scripts/python.exe bin/code_review.py \
  --repo "C:/chemin/vers/le/depot" \
  --out reports/review-<nom> \
  --since "6 months ago"
```

Modules : `git,size,debt,security,tests`. Les restreindre avec
`--modules security,tests` pour une passe ciblee. `--no-issues` pour ne pas
generer les brouillons.

Couverture reelle : `--coverage` force la mesure, `--no-coverage` la coupe.
Sans option, le module s'active seul si le depot declare un harnais
(`pytest.ini`, `tox.ini`, `conftest.py`, `pyproject.toml` avec `[tool.pytest`,
`setup.cfg` avec `[tool:pytest]`, `jest.config.*`, `package.json` contenant
`"jest"`, `phpunit.xml`). Il execute alors l'outil reel (`pytest --cov`,
`jest --coverage`, `phpunit --coverage-clover`), borne par `--cov-timeout`
(300 s par defaut), et rapporte le pourcentage par fichier + les numeros de
lignes non couvertes, croises avec les points chauds git.

ATTENTION : ce module **execute la suite de tests du depot**. Ne pas le lancer
sur un depot dont les tests ecrivent en base ou appellent des API facturees.

Codes de sortie : `0` = propre, `1` = findings ELEVE, `2` = findings CRITIQUE.

Complement LOC par langage (skill `codebase-inspection`) :

```bash
pygount --format=summary --folders-to-skip=".git,node_modules,vendor,venv,dist,build" <repo>
```

### 2. Lire, verifier, hierarchiser

**Toujours lire le `.md` avec `read_file`, puis ouvrir le code aux emplacements
cites avant de conclure.** L'analyse statique produit des signatures, pas des
preuves. Un `innerHTML = '<span>x</span>'` avec une chaine litterale n'est pas
un XSS ; un `innerHTML = html` avec une variable en est un.

Ordre de traitement recommande :

1. `security` CRITIQUE / ELEVE — d'abord les secrets en dur (ils sont dans
   l'historique git meme apres suppression).
2. Croiser `git` (points chauds) avec `tests` (fichiers sans test) : **les
   fichiers qui sont dans les deux listes sont le vrai risque du projet.**
3. `size` fonctions trop longues — c'est ce qui empeche d'ecrire des tests.
4. `debt` FIXME/BUG/HACK.
5. Le reste : a planifier, pas a corriger maintenant.

### 3. Ecrire les tests manquants (cycle TDD)

Charger `test-driven-development` et appliquer strictement RED-GREEN-REFACTOR :

1. Choisir un fichier present dans les points chauds **et** sans test.
2. Ecrire un test qui **echoue** et qui decrit le comportement attendu.
3. Le faire passer sans changer l'intention du test.
4. Refactorer seulement quand le test est vert.

Ne jamais ecrire un test apres coup qui se contente de valider le comportement
actuel, bug inclus : cela verrouille le bug.

Framework selon le langage : `pytest` (Python), `jest`/`vitest` (JS/TS),
`phpunit` + `wp-phpunit` (WordPress), `go test` (Go).

### 4. Proposer un refactoring

Regles :

- Un refactoring par issue, avec le comportement observable inchange.
- Jamais de refactoring sur du code sans test : ecrire le test d'abord.
- Commencer par extraire des fonctions depuis les fonctions les plus longues :
  c'est le refactoring qui debloque tous les autres.
- Ne pas toucher a plus de fichiers que necessaire (regle utilisateur).

### 5. Creer les issues GitHub

Les brouillons sont dans `<out>/issues/NN-<slug>.md` avec titre et labels en
commentaires HTML, plus un script `creer_issues.sh` pret a executer.

```bash
# verifier le depot cible AVANT de poster
gh repo view

# publier
bash "<out>/issues/creer_issues.sh"
```

**Si `gh` est absent** (cas actuel de cette machine), le script le dit et ne
poste rien. Deux options :

```bash
winget install GitHub.cli && gh auth login     # puis relancer creer_issues.sh
```

ou creer les issues a la main en copiant le contenu des `.md`. Ne jamais
annoncer que les issues sont creees sans avoir vu les URLs renvoyees par
`gh issue create`.

Pour enchainer une issue vers une PR verifiee, charger `github-issue-to-pr`.

### 6. Restituer

Format de restitution attendu :

- 1 phrase d'etat (taille du code, ratio de tests, nombre de findings par severite)
- les 3 risques principaux, chacun avec le fichier et la ligne
- ce qui a ete **verifie par lecture** vs ce qui reste une **signature a confirmer**
- les issues creees (avec URLs) ou les brouillons a poster
- ce que l'analyse ne couvre pas

## Ce que l'analyseur ne fait pas

- Pas d'analyse de flux de donnees : il ne suit pas une variable d'une entree
  utilisateur jusqu'a un `echo`. Les vrais XSS/SQLi chaines lui echappent.
- Pas de couverture de tests reelle : la detection est heuristique par nom de
  fichier. Un test existant sous un autre nom passe pour absent. Pour du vrai :
  `pytest --cov`, `jest --coverage`, `phpunit --coverage-text`.
- Pas de detection de vulnerabilites de dependances — c'est le skill
  `security-audit` (`npm audit`, `pip-audit`).
- Pas de test d'execution : rien ne prouve que le code fonctionne. Pour ca,
  charger `dogfood` et exercer reellement l'application.
- Pas de mesure de complexite cyclomatique (seulement la longueur).

## Pieges (constates a l'usage)

1. **Les lockfiles faussent tout.** `package-lock.json` a 21 893 lignes remontait
   comme "fichier trop long" en tete de rapport. Exclus par `LOCKFILES`. Meme
   chose pour `style-rtl.css`, genere par WordPress.
2. **Un budget de lignes unique est faux.** Une feuille de style de 9 000 lignes
   est normale, un fichier PHP de 1 300 lignes ne l'est pas. Seuils separes :
   `MAX_FILE_LINES` (500) pour le code, `MAX_FILE_LINES_STYLE` (2500) pour CSS/HTML/MD.
3. **La regle "nonce manquant" doit etre au niveau FICHIER, pas ligne.** Au
   niveau ligne, elle flagge la ligne qui *fait* la verification
   (`wp_verify_nonce(...)` contient `$_POST[`) : 17 faux positifs sur un seul
   `functions.php` correct. Chercher `$_POST[` dans le fichier, puis l'absence
   de `wp_verify_nonce|check_admin_referer|check_ajax_referer` dans ce meme fichier.
4. **`innerHTML = 'chaine litterale'` n'est pas un XSS.** La regle doit exiger
   une variable, une concatenation ou un template `${}` a droite du `=`.
   Sinon `innerHTML = ''` remonte en ELEVE.
5. **La duplication doit comparer des fichiers de meme langage.** Sans la
   langue dans la cle de hachage, on obtient
   `page-devis-custom.php <-> style.css : 16 blocs`, qui ne veut rien dire.
6. **Le churn git ne doit compter que du code executable.** Sinon les `.md` de
   documentation arrivent en tete des "points chauds" et masquent les vrais
   fichiers a risque.
7. **Ne jamais lancer `npm audit fix --force` ni un refactoring automatique**
   dans le cadre d'une revue. La revue propose, l'utilisateur decide.
8. **`coverage` ne doit jamais faire echouer la revue.** Outil absent, suite en
   echec, timeout : c'est un `warning` dans « Limites de l'analyse », la revue
   continue. Verifie sur un theme WordPress sans harnais : la passe rend la main
   en 1,3 s avec un INFO explicite, pas une erreur.
9. **Ne pas deduire un harnais de la simple presence de fichiers `.py`/`.js`.**
   La detection exige un fichier de configuration reel, sinon `pytest` est lance
   dans des depots qui n'ont aucun test et retourne une erreur trompeuse.
10. **Le venv du depot passe avant `sys.executable`.** Un depot avec `.venv/` a
    ses propres dependances : lancer le pytest du venv de hermes-optim mesurerait
    la couverture avec les mauvais paquets.

## Verification

```bash
# non-regression des calibrages ci-dessus
python bin/code_review.py --repo <repo> --out /tmp/r --modules size
#   attendu : aucun lockfile dans "budget de lignes"
python bin/code_review.py --repo <repo> --out /tmp/r --modules security
#   attendu : aucun finding XSS sur une affectation de chaine litterale

# controle positif de la couverture (mini-depot pytest fourni)
python bin/code_review.py \
  --repo ~/AppData/Local/hermes/data/hermes-optim/samples/covdemo \
  --out reports/review-covdemo
#   attendu : "Couverture python : 63.0%", facturation.py a 41.2%,
#             lignes non couvertes 16-20 et 25-28
```
