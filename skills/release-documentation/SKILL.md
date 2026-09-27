---
name: release-documentation
description: "Use when documenting a version: changelog, wiki, release."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [documentation, release, github, wiki, siyuan, changelog, commit]
    category: devops
---

# Publication documentaire d'une version

Une note de release courte ne suffit pas : le lot documentaire complet est le
CHANGELOG detaille, la page du wiki L1, la note SiYuan, UN SEUL commit `docs:` et
l'edition du corps de la release GitHub avec le meme fichier.

## When to Use

- Une version vient d'etre publiee (tag pose, release creee) et il manque le
  CHANGELOG detaille, la page wiki, ou l'entree du second cerveau.
- Toute demande du type « complete la vX.Y avec la doc : CHANGELOG + wiki +
  SiYuan + edition de la release ».

## Le lot, dans cet ordre

1. **`docs/CHANGELOG-<v>.md`** — format Keep a Changelog : `# Changelog — Version
   <v> — <nom>`, `## [<v>] — YYYY-MM-DD`, `### Les changements en detail` (un
   paragraphe par nouveaute : ce que c'est, a quoi ca sert, mesures, fichiers
   concernes), puis `### Ajoute` / `### Modifie` / `### Corrige` / `### Supprime`
   / `### Notes de migration`. La ligne de rollback vise le **dernier commit avant
   la release** (`git rev-parse <tag>^`), pas le commit de la version.
2. **Page du wiki L1** du concept nouveau (frontmatter complet, `type` coherent
   avec le dossier, >= 2 wikiliens resolus) — regles et recette dans
   `references/wiki-l1-et-siyuan.md`.
3. **Catalogue sans LLM** : `index.md` se regenere en important
   `wiki/scripts/compile_wiki.py` et en appelant `update_index([], dry=False)`
   (l'appel au modele vit dans `main()`, pas a l'import) ; puis entree `log.md`.
   Ne JAMAIS relancer une compilation LLM pour un ajout redige a la main.
4. **Note SiYuan** dans le notebook du domaine (`createDocWithMd`, puis preuve de
   lecture) — recette dans la meme reference.
5. **UN SEUL commit `docs:`** avec tout le lot, puis push sur `main` — **apres avoir compte les commits
   en attente** (`git rev-list --count origin/main..HEAD`) : un push publie tout ce qui est en
   attente, pas seulement le lot. Si cette avance est faite de commits hors sujet, s'arreter au commit
   local et le dire (`push: non`, N commits d'avance). Puis les trois controles bloquants du guide du
   depot (recette, sorties attendues et pieges : `references/publication-push-gate.md`) — le
   troisieme, **arbre figé** (`git status --porcelain` vide), est rouge en permanence ici parce que le
   runtime se reecrit tout seul (`config.yaml`, `cron/jobs.json`, `skills/.usage.json`) : figer cette
   derive est un commit dedie : **decision de l'utilisateur, jamais une initiative d'agent**, et il ne
   se fait qu'apres avoir ecarte les artefacts d'outillage (`installs/`, `tools/`) et remis a HEAD un
   eventuel bloc de test laisse dans `config.yaml` — recette complete, exclusions locales et pieges de
   comptage dans `references/publication-push-gate.md`. Enfin
   `gh release edit <tag> --notes-file docs/CHANGELOG-<v>.md`.

## Rendre la version visible sur la page d'accueil (README)

La page d'accueil d'un depot rend le README de la **branche par defaut** — pas le tag de la release,
pas le wiki. « Rendre la vX.Y visible » veut donc dire trois choses a la fois : la branche par defaut
porte le bon README, ce README nomme la version courante, et la release reste marquee **Latest**.

1. **Lire l'etat reel avant d'ecrire** : `git fetch origin`, `git branch -a`,
   `git log --oneline -3 -- README.md`, puis
   `gh repo view <owner>/<repo> --json defaultBranchRef,visibility`. La branche par defaut ne se
deduit ni d'un document ni d'une session precedente : elle se relit ici, **et une seconde fois juste
avant le push**. C'est une metadonnee qui bouge en cours de session — un push destine a une branche
d'archive devient la page d'accueil si la defaut a bascule entre-temps.
2. **Lire le CONTENU, pas le sujet du commit** : `git show origin/<branche>:README.md | head -30`.
   Un commit dont le message annonce la mise a jour du README pour une version peut n'avoir fait que
   **coller du texte en tete** (prompt, transcript, specification) sans toucher au README lui-meme.
   A faire avant de copier le moindre fichier de doc d'une branche a l'autre.
3. **Partir du README le plus complet**, pas du plus ancien :
   `git diff --stat origin/<a> origin/<b> -- README.md`, `wc -l` sur les deux versions. La branche
   d'archive peut porter un README plus riche que la branche par defaut.
4. **Editer sur la branche par defaut, puis recopier le MEME fichier** sur l'autre branche
   (`git checkout <branche-source> -- README.md`, qui indexe au passage) : deux README divergents
   redeviennent faux au premier oubli.
5. **Prouver l'alignement par l'empreinte**, pas par le diff :
   `git show origin/<branche>:README.md | git hash-object --stdin` sur chaque branche — meme hash =
   memes octets (un `--stat` a zero ligne peut cacher un ecart de fin de ligne). Puis attendre
   ~45-60 s (cache GitHub) et verifier ce qui est REELLEMENT servi :
   `gh api repos/<o>/<r>/readme --jq .content | base64 -d | head -20` et
   `gh api "repos/<o>/<r>/contents/README.md?ref=<branche>" --jq .content | base64 -d | head -6`.
6. **Verifier la release et les tags** : `gh release list` (colonne `Latest`) ;
   `git ls-remote --tags origin` pour prouver les tags intacts.

**Contenu attendu du bandeau et du tableau** : bandeau version courante / precedente / originale (une
ligne chacune) ; tableau `Version | Statut | Branche / Tag | Documentation`, une ligne par version
publiee ; colonne Documentation limitee a des cibles qui existent **sur cette branche**
(`git ls-tree --name-only origin/<b> docs/ | grep -i changelog`, page du wiki verifiee dans
`.wiki.git` — un lien de wiki vers une page jamais ecrite est un 404) ; extrait d'installation
`git checkout <tag>` de la version courante ; supprimer toute phrase decrivant l'ancienne topologie
de branches (« la branche X est celle par defaut, main reste la Y »), fausse des la publication.

**`git pull` bloque par un fichier modifie localement** :
`git diff origin/<branche> -- <fichier>` (sortie vide = la modif est deja en amont, rien a perdre),
puis `git stash push -m "wip: <fichier>" -- <fichier>` → `git pull` → `git stash pop`. Rapporter le
stash/pop : le marqueur `M` qui disparait ressemble a du travail perdu quand le contenu est deja dans
le commit distant.

**Si la premisse de la demande est fausse** (l'artefact a copier n'est pas ce que son nom ou son
message annonce, la branche par defaut citee n'existe plus) : s'arreter AVANT d'ecrire, rapporter les
sorties brutes, preparer le fichier corrige dans `$LOCALAPPDATA/hermes/cache/scratch` avec son diff,
puis poser UNE question (option recommandee en premier). Ne jamais « appliquer la consigne litterale »
sur un artefact public : pousser du texte parasite sur une page d'accueil coute un commit de nettoyage
et laisse une trace d'historique.

**Pass de coherence du depot** (les faits que le README enonce sur le depot lui-meme) :

1. **Recenser AVANT de corriger** : `grep -in "<motif>" README.md` sur le mot de l'affirmation
   perimee (« priv », numero de version, nom de branche). Une correction au paragraphe de tete laisse
   faux les autres sites — bloc de securite, tableau de la documentation du depot — et le rapport doit
   dire lesquels restent, avec leur numero de ligne.
2. **La description du depot fait partie de la page d'accueil** : elle s'affiche au-dessus du README et
   porte la version courante. La lire au debut (`gh repo view <o>/<r> --json visibility,description`)
   et la corriger dans le meme pass (`gh repo edit <o>/<r> --description "..."`, relue par
   `gh repo view --json description`).
3. **Corriger chaque site avec la formulation demandee**, et signaler a part, sans les toucher, les
   sites hors perimetre (un fichier de `docs/` que la demande interdit de modifier reste faux : c'est
   une decision separee, pas une correction silencieuse).
4. **Changer la visibilite du depot n'est jamais une consequence d'un pass documentaire** : elle se
   demande. Un depot public qui annonce « prive » se corrige dans le texte, pas dans les reglages.

**Schema d'architecture (blocs ASCII du README)** :

- **Ne pas retaper le schema** : extraire le bloc entre ses fences (`t.index("```\n", i)` puis
  `t.index("\n```\n", start)`) et ne remplacer que son contenu. Une faute de frappe dans une bordure
  abime un schema que personne ne relit ligne a ligne.
- **Calculer l'alignement, ne pas le viser** : ligne de boite = `"   " + libelle` puis
  `.ljust(largeur_interne)`, bordures generees (`"┌" + "─" * n + "┐"`). Le raccord a une boite
  existante se fait en remplacant un `─` de sa bordure par `┬`/`▼` **a la colonne du connecteur** — on
  ne redimensionne jamais une boite existante pour faire rentrer la nouvelle.
- **Le contenu du schema est une affirmation technique**, pas un decor : verifier l'etiquette fournie
  par la demande contre la source du depot (provider, endpoint, mesures d'un composant dans
  `skills/<x>/references/*.md`) et ecrire la valeur mesuree, pas la reformulation de la demande. Le
  paragraphe ajoute a la suite explique le role du composant et sa place.
- **Relire le diff du bloc** : les lignes du schema deja presentes doivent en sortir inchangees ;
  seules les bordures touchees et les lignes ajoutees apparaissent.

**Identifier le checkout vivant avant tout `git`** : plusieurs clones du meme `origin` peuvent
coexister, dont un perime. Ne jamais deduire l'emplacement du depot d'une consigne ou d'une session
precedente : dans chaque candidat, `git rev-parse HEAD` + `git status -sb` + `git log --oneline -1`,
puis `git merge-base --is-ancestor <sha> HEAD` — un HEAD qui est **ancetre** de l'autre est un clone
en retard, y ecrire ne publie rien et fait diverger l'historique. Confirmer par la fraicheur d'un
fichier connu (comparer la page wiki du meme concept entre les deux copies).
**Verifie sur cette machine** : le checkout a jour est le **runtime lui-meme**
(`%LOCALAPPDATA%\hermes`, racine = runtime + `docs/` + `wiki/`, remote `hermes-home-vision`) ; un
clone sous `C:\Users\<user>\Projets\<repo>` existe et etait en **retard** — ne pas y ecrire sans
avoir verifie son HEAD, et le signaler si l'utilisateur croit publier depuis lui. `gh` fonctionne de
n'importe ou, `git` non : toujours `cd` dans le checkout retenu avant de committer.

## Retoucher un lot deja publie

Une valeur corrigee n'existe jamais a un seul endroit : le fichier de CHANGELOG,
la page wiki, la note SiYuan **et le corps de la release GitHub** portent le meme
chiffre. Le corps de la release est un **instantane copie** au moment de
`gh release edit`, pas un lien vers le fichier : corriger le fichier sans refaire
l'edition laisse la version fausse en ligne, et c'est la release que le monde lit.

1. Localiser la source de verite nommee par la demande (`references/...` du skill
   concerne, fichier de mesures) et **reprendre la valeur telle qu'elle y est
   ecrite**, fourchette comprise. Ne corriger que le chiffre fautif.
2. Corriger chaque copie : fichier, page wiki, note SiYuan (recette de correction
   d'un paragraphe dans `references/wiki-l1-et-siyuan.md`), puis re-editer la
   release avec le meme `--notes-file`.
3. **Nouveau commit**, jamais un `--amend` ni un `push --force` sur un commit
   deja publie : une correction qui suit un push est un commit de plus.
   Indexer les chemins du lot un par un (`git add <chemins>`) : entre deux
   passes, l'arbre s'est enrichi de fichiers d'execution ou de curateur hors
   sujet, et `git add -A` les embarquerait dans un commit cense etre documentaire.
   Les signaler comme non indexes dans le rapport.
4. La page wiki corrigee n'exige une regeneration de `index.md` que si le
   **resume** a change : la ligne du catalogue vient du titre ou de la premiere
   phrase du corps, pas du paragraphe retouche. Refaire tourner `verify_wiki.py`
   (EXIT=0) reste la preuve a donner.

## Regles (toujours applicables)

- **UN commit pour tout le lot**, jamais un commit par livrable. Le message dit ce
  qui est documente.
- **Sauf cycles separes demandes** : quand l'operateur nomme plusieurs decisions distinctes (figer la
  derive, un lot documentaire, la memoire), chacune a son **propre cycle commit + push**, clos et
  rapporte (hash complet + ligne de push) avant que le suivant soit engage — rien ne se glisse d'un
  cycle dans l'autre. Dans ce mode le message porte le **compte reel** des entrees figees, et toute
  ligne que la session n'a pas ecrite (passe concurrente) se **nomme** dans le message et dans le
  rapport : un diff absorbe en silence n'est plus auditable.
- **Gate anti-secret avant tout push** : scanner le diff INDEXE, pas le working
  tree —
  `git diff --cached -U0 | grep -nE "sk-[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{30,}|nvapi-[A-Za-z0-9_-]{20,}|xoxb-|ghp_[A-Za-z0-9]{20,}|-----BEGIN.*PRIVATE KEY"`.
  Aucune correspondance (`|| echo ok`) = condition pour pousser. Le guide du depot
  (`docs/scripts/push-to-github.md`) exige en plus le scan d'**HISTORIQUE**
  (`python docs/scripts/scan_secrets_history.py --repo .`, attendu : aucune valeur reelle) : le depot
  est public, un secret deja pousse est compromis et se retire par `git filter-repo`, pas par un
  `git rm`.
- **`git add -A` ramasse l'etat d'execution du runtime** (compteurs
  `skills/.usage.json`, caches suivis). Lire `git status --porcelain` **avant**
  d'indexer : si un fichier hors sujet apparait, le signaler dans le rapport (ou
  indexer explicitement les chemins du lot). Ne pas laisser croire que le commit
  est purement documentaire s'il porte autre chose.
- **`config.yaml` n'entre pas dans un commit `docs:`** : s'il apparait modifie,
  ne jamais l'indexer, et distinguer l'origine : reecriture chronique par le runtime
  (`cron/jobs.json`, `skills/.usage.json` derivent de meme) => la seule presence dans `git status`
  n'est pas un signal d'arret, la rapporter comme **preexistante** ; modification venue de la session
  (`hermes config set`) => s'arreter et demander.
- **Ne jamais toucher au tag** : `gh release edit` change le corps, pas le tag. Ne
  pas creer, supprimer ni repointer de tag, ni ceux des versions precedentes.
  Verifier apres coup `git ls-remote --tags origin` (anciens tags inchanges).
- **Prouver, ne pas annoncer** :
  - corps de la release = fichier : `gh release view <tag> --json body -q .body`
    compare au fichier (longueur ET contenu) ; « edit OK » ne suffit pas ;
  - fichiers annonces presents en amont :
    `git ls-tree origin/main --name-only <chemins>` ;
  - `origin/main` = HEAD local apres push (`git rev-parse HEAD origin/main`).
- **Chaque chiffre et chaque chemin cites doivent exister dans le depot.** Si une
  valeur fournie par la demande contredit la source mesuree (latence, cout,
  nombre de pages), ecrire ce qui est demande ET signaler l'ecart avec la source
  dans le rapport : ni correction silencieuse, ni recopie silencieuse. Une valeur
  mesuree se reprend d'un fichier de mesures reel, jamais d'un souvenir :
  rechercher le chiffre dans le depot (`search_files`, ou `grep` en ligne de
  commande) avant de l'ecrire ou de la corriger.
- **Un message de commit prescrit par l'operateur se corrige quand la mesure le contredit** : avant de
  figer une affirmation, la mesurer (`hermes --version` + `grep -m1 _config_version config.yaml` pour
  la version, `netstat -ano | grep :<port>` pour un port, `Get-ScheduledTask` pour le nom reel des
  taches planifiees). Une affirmation perimee figee dans un message de commit y reste pour toujours :
  ecrire le **fait mesure** et le signaler. Corollaire : une affirmation fausse n'est pas forcement
  une invention — etablir ce que la chose **est** avant d'ecrire qu'elle n'existe pas (un port annonce
  « inexistant » etait le port documente d'un service a l'arret depuis des mois).
- **Une lecon apprise deux fois se FUSIONNE, elle ne s'empile pas** : quand deux passages d'un meme
  fichier disent la meme chose (une passe concurrente et la session), reduire a **un seul** traitement
  canonique et ne laisser sur l'autre site qu'un **renvoi** d'une phrase. Controler par
  `grep -c "<motif>"` avant/apres et relire le diff : aucun point voisin ne doit bouger. Un fichier ou
  la meme regle vit deux fois se contredit a la premiere correction.
- **Un diff se montre AVANT d'ecrire** : `scripts/dryrun_edit.py` reconstruit le contenu en memoire,
  imprime le diff unifie et les comptes lignes/caracteres, et n'ecrit qu'avec `--write` — c'est ce diff
  que l'operateur relit, et la preuve que le reste du fichier est intact.
- **Un compte attendu n'est pas un critere d'arret** : les writers de runtime reviennent en quelques
  minutes (`cron/jobs.json` : `completed` +1, `last_run_at`/`next_run_at`) et l'ecriture en cours de la
  session reste visible dans le porcelain. Le critere porte sur le **contenu du commit** : indexer par
  chemin explicite, verifier `git diff --cached --name-only` = l'ensemble nomme, et `git show --stat
  HEAD` apres chaque commit d'un cycle a plusieurs commits ; toute entree restante se **rapporte**,
  jamais ne s'absorbe.
- **Ne pas ecraser un fichier existant** sans le signaler ; ne pas modifier
  `README.md`, `docs/README.md` ou les tags si la demande ne les cite pas.

## Rapport final

Le rendre en **tableau `Element | Statut`** (une ligne par livrable : fichier cree,
page wiki, index regenere oui/non, note SiYuan, hash du commit, push oui/non,
release editee oui/non, tags intacts), suivi **en clair** des points a trancher :
ecart entre une valeur demandee et la source, fichier inattendu embarque par
`git add -A`, fichier existant non ecrase. Les doutes ne se noient pas dans le
tableau — c'est la que l'utilisateur decide.

## Pitfalls

- **Ecrire le CHANGELOG ne suffit pas a documenter la version** : la release
  GitHub porte encore la note courte jusqu'a `gh release edit --notes-file`.
- **Un `--notes-file` absent donne un corps de release vide** : verifier que le
  fichier existe et est non vide avant l'edition.
- **Une release est « editee » au sens de l'API, pas de l'ordre** : editer le
  corps ne reecrit ni le titre ni le tag (`title:` reste « <v> — <nom> »).
- **Ne pas rejouer une etape deja faite** (index deja regenere, note deja creee) :
  relire l'etat (`git status`, `lsNotebooks`, recherche par `content LIKE`) et
  recommencer seulement ce qui manque.
- **Un fichier de doc ecrit dans un dossier ignore par `.gitignore` disparait du
  commit** : `git check-ignore -v <chemins>` avant de conclure que le lot est
  indexe.
- **Un README propre n'efface pas ce qui a ete colle** : le contenu retire du fichier courant reste
  lisible dans l'historique (`git show <sha>`), et un depot public l'expose. Le proposer comme
  decision separee (`git filter-repo` + force-push), jamais en silence.
- **`gh release view --json isLatest` est refuse** (`Unknown JSON field: "isLatest"`) : lire
  `Latest` dans `gh release list`, ou `gh api repos/<o>/<r>/releases/latest --jq .tag_name`.
- **Le README rendu est en cache** : compter ~45-60 s apres le push avant de conclure a un echec.
- **`grep` sur une phrase mise en gras ne matche pas** : « Depot public » ne trouve pas `Dépôt
  **public**` — le balisage est dans la ligne. Grep un fragment sans markdown (l'URL, un mot nu) ou
  afficher la tete du fichier servi (`... | base64 -d | sed -n '1,15p'`) ; un grep qui ne renvoie rien
  n'est pas une preuve d'absence.
- **Ne pas corriger en silence un ecart de fait du README** (visibilite annoncee « privee » sur un
  depot public, section d'audit plus vieille que la version courante, comptage de pages faux) :
  mesurer, ecrire la valeur mesuree, et signaler l'ecart.

## Voir aussi

- Skill `github` (authentification, releases, `gh`), skill `llm-wiki` (compilation
  non-agentique du wiki). La recette locale du wiki et de SiYuan est dans
  `references/wiki-l1-et-siyuan.md`, le verificateur dans `scripts/verify_wiki.py`. Les trois controles bloquants de publication, la mesure de ce qui part reellement dans un push, la recette de figeage de la derive (exclusions
locales, lecture des colonnes de `git status --porcelain`, preuve du tip distant) et le
rafraichissement d'un clone en retard, et l'**ecriture concurrente de la revue d'arriere-plan** (elle
  ecrit dans les 2 min qui suivent une ecriture de session : attendre ~3 min, prouver la stabilite par
  mtime + `wc -l`, s'orienter dans `skills/.curator_ledger.jsonl`, ne pas confondre
  `pending/memory/*.json` avec une ecriture) sont dans `references/publication-push-gate.md`. Le skill
  `github` est un bundle (non modifiable) : les recettes GitHub propres a ce depot vivent donc ici,
  section « Rendre la version visible sur la page d'accueil ».
