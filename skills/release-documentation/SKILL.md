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

**`git pull --rebase` sur le home runtime : assainir l'arbre d'abord, et nommer ce qu'on met de cote.**
Le rebase refuse au preflight (`error: cannot pull with rebase: You have unstaged changes.`) et son
critere n'est pas « les fichiers qu'il va toucher » mais **l'arbre entier** : la derive chronique du
runtime (`config.yaml`, `cron/jobs.json`, `cron/usage_audit.jsonl`, `memories/*`, `profiles/**`,
`skills/.usage.json`, `skills/.curator_state`) suffit a bloquer, meme quand les commits du lot viennent
d'etre faits et que les 3 commits couvrent tout le travail. Ne pas lire ce refus comme un echec de la
mission : rien n'a bouge, aucun rebase n'a demarre (le verifier — `.git/rebase-merge` et
`.git/rebase-apply` absents — avant de parler d'avort ou de conflit). Compter les entrees bloquantes
(`git status --porcelain --untracked-files=no` : fichiers modifies **et** suppressions suivies), puis
poser UNE question : (a) recommande — `git stash push -m "wip: gel avant rebase" -- <chemins suivis>`
(jamais `-u` : les non-suivis restent en place), `git pull --rebase`, `git stash pop`, en GARDANT
l'entree de stash tant que le pop n'a pas ete verifie (conflit attendu sur un fichier que l'amont a
aussi modifie) ; (b) geler la derive dans un commit dedie — decision de l'operateur, jamais une
initiative d'agent.

**Une fois le GO donne, enchainer stash et rebase dans la MEME commande.** Le runtime reecrit ses
fichiers d'etat (`cron/jobs.json`, `*usage_audit.jsonl`, `*.usage.json`, `context_length_cache.yaml`)
toutes les minutes : un arbre « propre » est une fenetre de quelques secondes, et `pull --rebase` refuse
de nouveau si un writer est repasse entre les deux. Juste apres le stash, relire
`git status --porcelain --untracked-files=no` et **etendre le stash** si des fichiers sont revenus : la
revue d'arriere-plan ecrit dans la minute qui suit une ecriture de session, et ses fichiers de CONTENU
(skills/) se garent dans le meme stash que la derive de runtime — un preflight refuse de nouveau est un
gel a completer, pas un motif d'arret. Le conflit se lit ensuite dans `git status` : il tombe rarement ou
la consigne l'annonce (ici un journal append-only du wiki, pas `config.yaml`).

**Si la premisse de la demande est fausse** (l'artefact a copier n'est pas ce que son nom ou son
message annonce, la branche par defaut citee n'existe plus) : s'arreter AVANT d'ecrire, rapporter les
sorties brutes, preparer le fichier corrige dans `$LOCALAPPDATA/hermes/cache/scratch` avec son diff,
puis poser UNE question (option recommandee en premier). Ne jamais « appliquer la consigne litterale »
sur un artefact public : pousser du texte parasite sur une page d'accueil coute un commit de nettoyage
et laisse une trace d'historique.

**Une demande de « restauration » peut etre un NO-OP** : avant de restaurer une version que l'operateur
croit perdue, mesurer qu'elle est bien absente. Cas mesure : un « remets le README v1.4 sur main » ou le
fichier de travail, `main` local et `origin/main` portaient deja la v1.4 — meme blob
(`git rev-parse HEAD:README.md` = `git rev-parse origin/main:README.md` = `git hash-object README.md`),
`git status --porcelain -- README.md` vide, ligne de version relue dans le fichier au lieu de son sujet
de commit. Trois mesures suffisent a trancher : l'empreinte du blob sur les DEUX branches, l'etat du
fichier dans l'arbre, et la ligne de version lue dans le fichier.
**Un numero de version « introuvable » est souvent celui d'un COMPOSANT, pas du produit** : avant de
conclure qu'une vX.Y n'existe nulle part, enumerer les champs de version des composants
(`grep -n '^version'` dans les `plugin.yaml`, en-tetes des scripts de supervision). Cas mesure : un
« ANIMA 0.2 » jamais documente etait la `version: 0.2.0` d'un **plugin non suivi par git** — la version
du produit restant 0.1 partout (README, `docs/`, wiki, sauvegardes). Un fichier non commite ne se trouve
ni par `git log -S` ni par `git log --all` : seulement dans l'arbre de travail.

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
Les pages du **wiki** ne sont pas dans `docs/` : elles vivent dans le clone du wiki
(`%LOCALAPPDATA%\hermes\wiki-github`, remote `<repo>.wiki.git`, branche `master`) — le `wiki/` du
runtime est la base de connaissances L1, autre chose. Une demande qui nomme `docs/ANIMA-*.md` ou
« la page wiki X » vise ce clone : `search_files` sur `ANIMA*.md` sous `%LOCALAPPDATA%\hermes` le
confirme en une commande, et `cache/scratch/wiki_verify/` en contient des copies de verification a ne
pas prendre pour la source.

**Ce clone est un depot imbrique : ses pages ne partent pas dans le commit de `main`.** Le depot
principal ne le voit que comme un repertoire non suivi (`?? wiki-github/` — une des entrees du
`git status` du runtime, facile a confondre avec la derive), et `git add wiki-github/<page>` y indexe un
gitlink, pas un fichier. Un GO qui liste « `docs/…` **+ les pages du wiki** » en UN seul commit n'est
donc pas executable tel quel : publier ce qui est nomme sur `main` avec le message prescrit, puis
rendre le wiki comme un **cycle separe** (`git -C wiki-github add/commit/push origin master`) soumis a
son propre GO — ces pages sont publiques, et une consigne qui dit `git push origin main` n'autorise pas
le remote `.wiki.git`. Ses fichiers apparaissent en `M` dans `git -C wiki-github status`, pas dans le
porcelain du depot principal : un lot « committe » lu au seul statut du runtime peut laisser trois
pages modifiees et non publiees, sans que rien ne le signale.

### Documenter une version PREPAREE, non publiee

Bandeau avec mention de statut, ligne de tableau dont la colonne tag dit « aucun tag », section
bloqueurs avant la licence, et **aucun tag ni release dans ce pass**. Recette complete (forme des 5
elements, re-mesure des valeurs que le document affirme — y compris dans ses commandes —, **les deux
formes du passage de statut** et preuve apres push) : `references/version-preparee-non-publiee.md`.

**Si la version est publiee dans la MEME session, demander ou va le passage `preparee` -> `publiee` :**
dans le commit qui porte le tag, ou dans un commit `docs:` separe apres le push. Trancher sans le dire
laisse le document en desaccord avec l'etat reel du depot (page d'accueil annoncant « preparee » une
version deja taguee, ou l'inverse).

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
   **Le tag ne bouge pas : il reste sur le commit d'origine, donc EN ARRIERE du commit de correction.**
   C'est voulu (re-taguer pour aligner est interdit) et cela se DECLARE : comparer
   `git rev-parse <tag>^{commit}` a `git rev-parse HEAD`, dire l'ecart, et nommer ce qui sert encore
   l'ANCIEN texte — release GitHub creee apres coup, archive `git checkout <tag>`, documentation
   auto-generee. Une release creee APRES la correction le dit dans son corps ou cite le commit corrige,
   plutot que de laisser croire que le tag porte la version corrigee.
4. La page wiki corrigee n'exige une regeneration de `index.md` que si le
   **resume** a change : la ligne du catalogue vient du titre ou de la premiere
   phrase du corps, pas du paragraphe retouche. Refaire tourner `verify_wiki.py`
   (EXIT=0) reste la preuve a donner.

**Un document de recette / certification ne se reecrit pas** : ses mesures sont datees et font foi
pour leur date. Tout fait posterieur s'ajoute dans une section `## Mise a jour post-recrute` datee
(ce qui a change, ce qui est mesure, ce qui reste), la ligne de test d'origine restant en place et la
nouvelle ligne s'ajoutant a la suite ; un ecart avec une limite certifiee s'y **signale** (« ecart avec
la limite n° 1 — signale, non corrige ») au lieu de reecrire la phrase d'origine, meme quand la mesure
rend la phrase fausse.

**Le meme interdit frappe l'ETIQUETTE de version — c'est le piege principal d'un bump.** Remplacer
`ANIMA 0.1` par `ANIMA 0.2` dans un document de certification DATE fait dire au document que la **0.2**
est certifiee, alors qu'aucune re-certification n'a eu lieu : la ligne `- **Version** : …` et le verdict
(« … est certifiee DEGRADED ») portent la meme date que les mesures, et les renommer transforme un fait
date en affirmation fausse — meme quand c'est, mot pour mot, ce que la demande reclame. Traitement :
bumper l'etiquette demandee ET ajouter au document une mention datee qui rend la provenance
(« bascule documentaire vers <v> le <date> ; aucune re-certification ; les mesures ci-dessus datent du
<date> et font foi pour cette date ; etat mesure le <date> = X »), puis **declarer l'ajout dans le
rapport** : c'est une ecriture que la consigne ne demandait pas, et l'operateur peut vouloir la revoir.
Meme regle pour un document de specification (module non implemente) : le bump de l'etiquette y est
sans risque, le bump d'une phrase de STATUT ne l'est pas.

## Regles (toujours applicables)

- **UN commit pour tout le lot**, jamais un commit par livrable. Le message dit ce
  qui est documente.
- **Une demande qui nomme des FICHIERS sans nommer commit ni push reste LOCALE** : retoucher, montrer
  les hunks (`git diff -U0` + ses lignes `@@`), et s'arreter la. « Ne rien toucher d'autre » exclut de
  publier, et un push sur un depot public est une decision de l'operateur : le rapport se termine par
  l'etat de publication (`local, non committe — GO ?`).
- **Sauf cycles separes demandes** : quand l'operateur nomme plusieurs decisions distinctes (figer la
  derive, un lot documentaire, la memoire), chacune a son **propre cycle commit + push**, clos et
  rapporte (hash complet + ligne de push) avant que le suivant soit engage — rien ne se glisse d'un
  cycle dans l'autre. Dans ce mode le message porte le **compte reel** des entrees figees, et toute
  ligne que la session n'a pas ecrite (passe concurrente) se **nomme** dans le message et dans le
  rapport : un diff absorbe en silence n'est plus auditable.
- **Gate anti-secret avant tout push** : scanner le diff INDEXE, pas le working
  tree —
  `git diff --cached -U0 | grep -nE "sk-[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{30,}|nvapi-[A-Za-z0-9_-]{20,}|xoxb-|ghp_[A-Za-z0-9]{20,}|-----BEGIN.*PRIVATE KEY"`.
  Aucune correspondance (`|| echo ok`) = condition pour pousser.
  **Un motif large matche aussi des NOMS de fichiers et de la PROSE — un gate rouge n'est pas encore une
  fuite.** Avant de rapporter l'échec du gate (ou de le déclarer vert en silence), lister les lignes qui
  matchent (`git diff --cached | grep -inE '<motifs>'`) et les classer mot pour mot : un motif court vit
  dans un nom de skill ou de référence (le `sk-` de `<motif>` se retrouve au milieu d'un mot composé),
  dans un sigle de jeton d'API cité par une commande de vérification, ou dans un mot anglais courant.
  Traitement : **reformuler la doc** pour que seuls de vrais secrets puissent matcher (paraphrase du nom
  du skill ou de la référence, « un jeton d'API (préfixe `ey`) » à la place du sigle), puis re-passer le
  gate pour un vrai 0. Les noms exacts paraphrasés se **déclarent** dans le rapport : un gate vert
  obtenu en changeant le texte sans le dire laisse le prochain passage croire à un fichier disparu. Le guide du depot
  (`docs/scripts/push-to-github.md`) exige en plus le scan d'**HISTORIQUE**
  (`python docs/scripts/scan_secrets_history.py --repo .`, attendu : aucune valeur reelle) : le depot
  est public, un secret deja pousse est compromis et se retire par `git filter-repo`, pas par un
  `git rm`.
- **`git add -A` ramasse l'etat d'execution du runtime** (compteurs
  `skills/.usage.json`, caches suivis). Lire `git status --porcelain` **avant**
  d'indexer : si un fichier hors sujet apparait, le signaler dans le rapport (ou
  indexer explicitement les chemins du lot). Ne pas laisser croire que le commit
  est purement documentaire s'il porte autre chose.
- **Un chemin prescrit sous un dossier ignore ne s'indexe pas.** `git add data/rag/indexer.py` sur un
  `data/` ignore rend `The following paths are ignored by one of your .gitignore files` et **n'indexe
  rien** (verifier `git ls-files <dossier>` : 0 ligne = jamais suivi). Ne pas rattraper par `git add
  -f` : sur un depot public cela cree une SECONDE copie divergente du canon, a reconcilier a chaque
  version. Localiser le canon versionne (`git ls-tree -r origin/<branche> --name-only <zone>`) — ici
  le code RAG vit dans `scripts/rag_hybride/`, pas dans `data/rag/` —, montrer que le fichier live
  porte bien le travail (mtime + fonction nouvelle absente de la copie d'amont), et poser la question
  ne pas forcer. **Trois** corollaires une fois le GO donne : (1) **diffuser live vs canon AVANT
  d'ecraser** (`git diff --no-index <canon> <live>`) — le diff doit se limiter au delta annonce ; une
  divergence plus large signifie que l'amont porte des correctifs absents du live, donc STOP, on n'ecrase
  pas ; (2) le canon peut n'arriver qu'**avec le rebase** (il vient du commit d'amont) : ce commit se fait
  alors APRES le rebase et non a la place prevue, et l'ecart d'ordre se declare dans le rapport ;
  (3) **le jumeau versionne peut etre en RETARD sur le live, independamment du travail en cours** — ce
  depot publie sous `docs/scripts/` des copies de code qui vit ailleurs (un `data/…` ignore, un
  `plugins/…` non suivi). Apres resynchronisation, verifier la version PROPRE du jumeau : un canon reste
  en `0.1.0` alors que le live est en `0.2.0` rend faux, pour tout lecteur du depot, un CHANGELOG qui
  annonce la nouvelle version. Le dire est un point a trancher, pas une correction a faire en silence.
- **Indexer une liste blanche de plusieurs dizaines de chemins sans la taper** : generer la liste
  (statut porcelain filtre par classe, exclusions explicites) dans un fichier du scratch, puis
  `git add --pathspec-from-file=<fichier>` (un chemin par ligne ; les dossiers sont developpes, les
  fichiers ignores a l'interieur restent dehors). Controle non destructif a passer AVANT :
  `git add --dry-run --pathspec-from-file=<fichier>` (`exit 0` = rien de refuse), puis les deux gates
  habituels (`git diff --cached --name-only` filtre `.bak|cache|.pyc|__pycache__`, et le scan de
  secrets sur le diff indexe).
- **`git check-ignore -v` sur un DOSSIER (barre oblique finale) peut rendre un faux positif** — motif
  vide sur une ligne quelconque d'un `.gitignore` en CRLF — alors que les fichiers du dossier ne sont
  PAS ignores. Trancher sur un FICHIER dedans (`git check-ignore -v <dossier>/<fichier>`) ou par
  `git add --dry-run` : sinon on retire du commit des dossiers parfaitement versionnables.
- **Une ecriture sur un fichier DEJA indexe fait diverger l'index de l'arbre** : l'index porte la
  version relue et validee, l'arbre une version posterieure (`git status` rend `MM`), et le commit
  emporte la seconde. Pendant une fenetre gatee ou le lot est deja indexe, ne pas toucher un fichier du
  lot (une skill, une doc, un patch) pour y consigner une lecon : viser un fichier HORS lot ou differer
  l'ecriture. Controle avant de committer : `git diff -- <fichier du lot>` doit etre VIDE.
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
  - **message de commit committe = fichier valide** : comparer l'OBJET, jamais `git log --format=%B` —
    `%B` ajoute son propre saut de ligne final et rend un sha256 a N+1 octets ; un ecart d'UN octet
    n'est pas une alteration. Preuve : `git cat-file commit HEAD`, couper au premier `\n\n`, comparer
    le corps au fichier (egalite d'octets ET meme sha256) ; commande corrigee pour l'operateur :
    `git log -1 --format=%B | head -c -1 | sha256sum`.
  - **tag annote : le ref distant pointe l'OBJET tag, pas le commit.** `git rev-parse <tag>` rend l'objet,
    `git rev-parse <tag>^{}` le commit, et `git ls-remote --tags origin` liste les DEUX lignes
    (`refs/tags/<tag>` et `refs/tags/<tag>^{}`) : comparer la ligne qui correspond au controle fait,
    sinon un tag correct est declare en ecart. Second canal :
    `gh api repos/<o>/<r>/git/tags/<sha-objet> --jq '{tag,message,target_sha:.object.sha}'`.
  - **Relire le CONTENU, pas seulement les SHA** :
    `gh api "repos/<o>/<r>/contents/<chemin>?ref=<branche>" --jq '.name,.size'`, taille comparee au
    fichier local — `origin/main` = HEAD ne prouve que le pointeur, pas que le fichier a voyage.
- **Chaque chiffre et chaque chemin cites doivent exister dans le depot.** Si une
  valeur fournie par la demande contredit la source mesuree (latence, cout,
  nombre de pages), ecrire ce qui est demande ET signaler l'ecart avec la source
  dans le rapport : ni correction silencieuse, ni recopie silencieuse. Une valeur
  mesuree se reprend d'un fichier de mesures reel, jamais d'un souvenir :
  rechercher le chiffre dans le depot (`search_files`, ou `grep` en ligne de
  commande) avant de l'ecrire ou de la corriger. **Deux pieges de cette recherche :**
  (a) un `grep -rn` sur toute la racine du runtime ne rend pas la main — `site-packages`, `node_modules`,
  `tools/`, `installs/`, `cache/` pesent des Go ; cadrer avec `rg` et des exclusions explicites
  (`-g '!**/venv/**' -g '!**/site-packages/**' -g '!**/node_modules/**' -g '!**/cache/**'
  -g '!**/tools/**' -g '!**/installs/**'`) ; si le lot depasse quand meme le timeout, ecrire la sortie
  dans un fichier du scratch plutot que l'imprimer ;
  (b) **le runtime recopie l'enonce de la session dans ses propres fichiers** — `.hermes_history`,
  `pastes/`, `logs/agent.log`, `logs/errors.log`, et le journal du routeur
  (`data/route_ia_fix/jev_routing.jsonl`) contiennent la question telle qu'elle a ete posee. Une
  recherche du motif demande renvoie donc des occurrences qui ne sont que l'ECHO de la demande, et un
  motif introuvable ailleurs **parait trouve**. Classer les hits par FICHIER avant de conclure et
  ecarter ces cinq sources : une chaine qui n'apparait que la n'apparait nulle part.
- **Un message de commit prescrit par l'operateur se corrige quand la mesure le contredit** : avant de
  figer une affirmation, la mesurer (`hermes --version` + `grep -m1 _config_version config.yaml` pour
  la version, `netstat -ano | grep :<port>` pour un port, `Get-ScheduledTask` pour le nom reel des
  taches planifiees). Une affirmation perimee figee dans un message de commit y reste pour toujours :
  ecrire le **fait mesure** et le signaler. **Re-mesurer les chiffres cites par le message APRES la
  derniere passe d'edition :** une correction tardive (ligne d'en-tete fusionnee, ligne retiree) deplace
  les comptes (`wc -l`) deja ecrits dans le message et rend faux le `sha256` fige — refaire le fichier,
  le reafficher integralement et donner le NOUVEAU hash a valider, plutot que de committer un chiffre
  perime. Corollaire : une affirmation fausse n'est pas forcement
  une invention — etablir ce que la chose **est** avant d'ecrire qu'elle n'existe pas (un port annonce
  « inexistant » etait le port documente d'un service a l'arret depuis des mois). Pour un **compte de
  fragments RAG**, la mesure vit dans `data/rag/manifeste.json` (champ `par_source`) compare au manifeste
  de l'index d'A/B : c'est ce qui transforme « +N fragments » en fait verifie, et non recopie.
- **Une lecon apprise deux fois se FUSIONNE, elle ne s'empile pas** : quand deux passages d'un meme
  fichier disent la meme chose (une passe concurrente et la session), reduire a **un seul** traitement
  canonique et ne laisser sur l'autre site qu'un **renvoi** d'une phrase. Controler par
  `grep -c "<motif>"` avant/apres et relire le diff : aucun point voisin ne doit bouger. Un fichier ou
  la meme regle vit deux fois se contredit a la premiere correction.
- **Un diff se montre AVANT d'ecrire** : `scripts/dryrun_edit.py` reconstruit le contenu en memoire,
  imprime le diff unifie et les comptes lignes/caracteres, et n'ecrit qu'avec `--write` — c'est ce diff
  que l'operateur relit, et la preuve que le reste du fichier est intact. Trois modes couvrent les cas
  reels : `--mode replace` (defaut, `--avant`/`--apres`), `--mode append` (bloc en fin de fichier) et
  `--mode insert-before --ancre '<ligne exacte>'` (bloc a un emplacement precis, ancre conservee). Le
  nouveau texte passe par **`--text-file`**, jamais par la ligne de commande : un bloc de plusieurs
  lignes ne traverse pas un guillemet bash quand le fichier cible est en CRLF, et les antislashs y sont
  manges — ecrire le bloc dans `cache/scratch/` puis le passer par fichier. Les fins de ligne du fichier
  cible sont detectees et preservees (un fichier CRLF edite en LF devient mixte, et le diff affiche
  alors chaque ligne comme modifiee) ; l'ancre doit matcher exactement une fois, sinon refus sans
  ecriture.
- **Une ligne de tableau se remplace SANS fin de ligne finale** : le texte entrant garde son `\n`
  terminal, qui devient une **ligne vide** — et dans un tableau Markdown cette ligne vide ferme le
  tableau, les lignes suivantes ne sont plus rendues. Passer la ou les lignes par `$'ligne1\nligne2'`
  (ANSI-C, aucun `\n` terminal) ou relire le diff pour verifier que la nouvelle ligne est collee a la
  precedente ET a la suivante.
- **Un compte attendu n'est pas un critere d'arret** : les writers de runtime reviennent en quelques
  minutes (`cron/jobs.json` : `completed` +1, `last_run_at`/`next_run_at`) et l'ecriture en cours de la
  session reste visible dans le porcelain. Le critere porte sur le **contenu du commit** : indexer par
  chemin explicite, verifier `git diff --cached --name-only` = l'ensemble nomme, et `git show --stat
  HEAD` apres chaque commit d'un cycle a plusieurs commits ; toute entree restante se **rapporte**,
  jamais ne s'absorbe.
- **`cron/jobs.json` ne compte PAS comme entree de derive** : il est sale par conception (etat de
  runtime reecrit a chaque tir de job) et ne se committe que si une **definition** de job a change —
  `scripts/cron_jobs_gate.py` (skill `hermes-operations`) tranche, parce qu'un filtre `^[+-]` sans
  exclusion des deux lignes d'en-tete du diff (`--- a/…`, `+++ b/…`) ne renvoie jamais « bruit » et
  valide tout. Et un arbre propre n'est qu'un **etat de quelques minutes** : la revue d'arriere-plan
  repasse en moyenne toutes les ~15 min, donc on **gele l'ENSEMBLE** des entrees a un moment choisi
  (fin de session, avant un push important), jamais passe par passe.
- **Un conflit sur un journal append-only se resout par UNION, pas par un camp** : un fichier qui ne
  fait qu'ajouter des entrees datees (journal du wiki, CHANGELOG, log) garde les DEUX blocs, dans
  l'ordre chronologique — c'est la seule resolution qui ne perde rien. Retirer les marqueurs un par un,
  puis `grep -nE '^(<<<<<<<|=======|>>>>>>>)' <fichier>` = vide AVANT `git add`. Le commit rejoue porte
  alors un numstat plus petit que l'original (l'amont fournissait deja une partie du contenu) : c'est
  normal, ne pas « rattraper » le compte.
- **Fin d'un rebase quand `git rebase --continue` refuse a tort, et recuperation d'un stash droppe :**
  recette verifiee dans `references/rebase-et-stash-recuperation.md`.
- **Ne pas ecraser un fichier existant** sans le signaler ; ne pas modifier
  `README.md`, `docs/README.md` ou les tags si la demande ne les cite pas.

## Inspection ciblee avant d'indexer (lecture seule)

Quand le lot est annonce comme un ENSEMBLE DE CHEMINS precis (« ces N fichiers, rien d'autre »), l'etape
qui precede l'ecriture est une inspection en lecture seule, et son rapport se rend **fichier par
fichier**. Six mesures, dans cet ordre :

1. **Identifier le checkout et situer le lot dans la derive.** `git rev-parse --show-toplevel`,
   `git log -1 --format='%H %d %s'`, `git tag -l`, `git status -sb`, puis
   `git status --porcelain | wc -l` : le lot est un sous-ensemble d'un arbre souvent tres sale, et le
   rapport dit combien d'entrees restent HORS lot. Confronter le couple « commit + tag » du mandat a la
   mesure : `git cat-file -t <sha>`, puis **`git rev-parse <tag>^{commit}`** — jamais `git rev-parse
   <tag>` seul, qui sur un tag ANNOTE rend le hash de l'OBJET tag, et l'ecrire comme « le tag pointe
   <hash> » publie une affirmation fausse, jusque dans le CHANGELOG et le corps du commit — et
   `git cat-file -p <tag>` qui nomme sa cible (`object <sha>`). Les deux tiennent en une ligne :
   `git for-each-ref --format='%(refname) %(objectname) %(objecttype) %(*objectname)' refs/tags/<tag>`.
   **Un tag de version peut pointer le commit de la FONCTIONNALITE** (dont le message de tag porte le nom
   de la version) aussi bien qu'un commit de cloture posterieur : ne pas presumer l'un ou l'autre,
   mesurer. Un commit post-tag peut deja etre pousse. Le rapport dit l'ecart, il ne « corrige » pas la
   premisse en silence.
2. **Verifier l'arithmetique du perimetre.** Un dossier annonce « tout le dossier » embarque sa
   `__pycache__` (`find <dossier> -type f -printf '%s\t%p\n' | sort -k2`) : compter les fichiers SOURCE
   et faire tomber juste avec le nombre d'entrees que le mandat annonce — c'est cette egalite qui autorise
   a dire quels fichiers sont exclus (les `.pyc`). Un total qui ne tombe pas juste est un ecart de
   perimetre a trancher, pas un detail de forme.
3. **Fin de ligne, par fichier, et dire LAQUELLE des deux on rapporte.** Sur CHAQUE fichier du lot (une
   boucle, pas un fichier temoin) : `tr -dc '\r' < <f> | wc -c` et `tr -dc '\n' < <f> | wc -c`. Quand le
   depot declare `* text=auto eol=lf` (`git check-attr text eol -- <f>`) et que `git ls-files --eol` rend
   `i/lf w/crlf`, l'arbre de travail est en CRLF et l'OBJET versionne en LF — l'avertissement
   `warning: CRLF will be replaced by LF` a l'`add` le confirme. Les deux mesures se rapportent
   SEPAREMENT (« arbre de travail : N CR / N LF » et « blob HEAD : 0 CR ») : annoncer « LF only » sur la
   foi de l'index alors que le fichier sur disque est en CRLF est le mensonge classique de ce controle.
   Sur ce parc, une reecriture de masse des objets (reparation d'ACL, `takeown`) fait revenir des fichiers
   texte a 100 % CRLF alors que les blobs restent LF : ecart a declarer, puis decision (normaliser sur
   disque, ou laisser git normaliser a l'index) — jamais un silence.
   **Ce controle se rejoue APRES l'`add`, sur l'INDEX, sinon il ne repond pas a la question posee :**
   `git ls-files --eol -- <les fichiers du lot>` doit rendre `i/lf` pour chacun, et la preuve
   independante du blob indexe est le comptage d'octets CR sur `git show :<f>` (attendu : 0). **Un
   fichier anne a `eol=crlf` (`.ps1`, `.cmd`, `.bat`) rend lui aussi `i/lf`** : l'attribut ne gouverne
   que l'EXTRACTION, l'objet du depot reste normalise en LF — attendre `i/crlf` y fabrique une fausse
   alerte, et ce qui se cite alors est l'attribut (`git check-attr text eol -- <f>`), pas un echec. Un
   `i/crlf` reel sur un fichier declare `text=auto eol=lf` est, lui, un vrai ecart.
4. **Renvois : resolus sur disque ne veut pas dire versionnes** (cf. le piege des renvois ci-dessus).
   `scripts/inspection_pre_push.py <chemins> --refs` rend les deux verdicts par renvoi.
5. **Secrets : masques, classes, jamais imprimes.** Compter par fichier `N brut / N reel` et classer les
   hits — aucune valeur, meme partielle, dans le rapport, le journal ou le scratch ; seulement la
   structure (longueur, alphabet, prefixe de 8 caracteres au plus). **Un motif de DOCUMENTATION
   n'appartient pas au jeu « reel »** : `token\s*[:=]` matche tous les exemples d'un README et fait
   croire a 7 secrets reels dans un fichier qui n'en porte aucun ; un `sk-` non ancre mord dans des mots
   composes (`delegate-task-...`, `disk-space...`). Regle de classement deja etablie : une valeur
   plausible porte **au moins un chiffre ou une majuscule**. Un hit reel = STOP, aucune redaction.
6. **Ecarts de perimetre : les rendre comme decisions, un par un**, avant le STOP. (a) fichiers cites par
   les fichiers du lot mais non suivis et HORS liste (les omettre publie des liens morts, les ajouter
   sort du perimetre autorise) ; (b) artefacts d'execution que la liste embarquerait (`.pyc`, caches) ;
   (c) un controle demande qui n'a PAS de cible (« verifier que les 4 references sont presentes au §X »
   alors que ce paragraphe n'en liste aucune) ; (d) une numerotation de section qui ne correspond pas au
   fichier reel (le paragraphe vise vit dans une autre section).

**Le rapport sert les reponses demandees d'abord, les ecarts ensuite**, chacun avec la decision qu'il
attend, puis le STOP. Une inspection en lecture seule ne redige RIEN : brouillon de CHANGELOG, patches de
README et message de commit attendent le GO, meme quand le mandat les decrit dans le meme message.

## Rapport final

Le rendre en **tableau `Element | Statut`** (une ligne par livrable : fichier cree,
page wiki, index regenere oui/non, note SiYuan, hash du commit, push oui/non,
release editee oui/non, tags intacts), suivi **en clair** des points a trancher :
ecart entre une valeur demandee et la source, fichier inattendu embarque par
`git add -A`, fichier existant non ecrase. Les doutes ne se noient pas dans le
tableau — c'est la que l'utilisateur decide.

Quand la demande liste ELLE-MEME les elements attendus (typiquement un « GO combine » numerote), la
reponse suit SA numerotation et son ordre, item par item, et se termine par la liste de ce qui reste
reellement ouvert. Un diff de document se rend en **entetes de hunk par section**
(`git diff -U0` puis la ligne `@@` de chaque zone, rattachee au titre de section qu'elle touche), pas en
diff integral : l'operateur veut savoir quelle section bouge, pas relire le fichier.

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
  n'est pas une preuve d'absence. **Le meme piege frappe une cible de REMPLACEMENT prescrite** : un
    `--avant` fourni par l'operateur qui rend `0 occurrence` parce que la phrase est en gras dans le
    fichier n'est pas une cible absente — chercher la variante balisee, remplacer le VRAI texte en
    conservant les marqueurs (`**…**`), et **declarer l'ecart** dans le rapport (la cible annoncee ne
    pouvait pas matcher tel quel). S'arreter sec sur un `0 occurrence` alors que la phrase est dans le
    fichier a la ligne voisine coute un tour et laisse croire a un fichier different.
- **Ne pas corriger en silence un ecart de fait du README** (visibilite annoncee « privee » sur un
  depot public, section d'audit plus vieille que la version courante, comptage de pages faux) :
  mesurer, ecrire la valeur mesuree, et signaler l'ecart.
- **`git init` defaut le branche a `master`** : avant un PREMIER push (`gh repo create <nom> --source . --push`),
  renommer en `main` (`git branch -M main`), sinon le depot se cree avec `master` comme branche par defaut
  et le `git push -u origin main` attendu par l'operateur echoue. Confirmer ensuite le CONTENU distant complet
  plutot que se fier au seul « new branch -> main » :
  `gh api "repos/<owner>/<repo>/git/trees/main?recursive=1" --jq '.tree[].path' | sort`.
- **Un push de tag refuse par un `[remote rejected] <tag> (failed)` NU se REJOUE avant tout diagnostic.**
  Sans `(non-fast-forward)` ni `(already exists)`, et avec `gh api repos/<o>/<r>/rulesets` vide,
  l'hypothese d'une protection ne tient sur rien : relancer la MEME commande donne le verdict
  (`git push --porcelain origin <tag>` : `*` = ref cree, `!` = refuse). Ne jamais repondre a un refus par
  `--force`, et ne pas rapporter une cause (protection, hook, droit manquant) que la mesure n'a pas montree.
- **`hermes skills list-modified` mesure contre le manifeste des skills bundled, PAS contre git.** Une
  cible « skill <x> » d'un GO peut n'avoir aucun diff a committer (`git status --short -- <chemin>` muet) :
  son ecart est contre la version amont. Le fichier reellement modifie est souvent un `references/`
  voisin — non liste, donc a signaler et non a indexer. Controler chaque cible avant l'`add` et rapporter
  celles qui n'indexent rien.
- **Un `SKILL.md` qui cite des `references/` non suivis publie des liens casses.** Avant d'indexer un
  fichier de skill, confronter ses renvois au `git status --porcelain` : les non-suivis sont exactement
  ceux qui manqueront au depot public. **Exister sur le disque ne prouve rien** : le verdict se prend sur
  l'OBJET versionne (`git cat-file -e HEAD:<chemin>` ; ou `git ls-tree -r HEAD --name-only <dossier>`
  pour tout un dossier), sinon un renvoi vers un fichier present localement mais jamais committe se lit
  « resolu » — une verification par le disque rend un faux vert, et c'est le lien de la version publiee
  qui est mort. Un renvoi peut aussi viser le dossier d'une AUTRE skill (`scripts/<x>.py` decrit dans le
  texte comme appartenant a `devops/<y>`) : resoudre depuis la racine de `skills/`, jamais depuis le seul
  dossier citant. Si la liste des cibles autorisees ne contient pas ces fichiers, les SIGNALER comme
  references pendantes (commit de complement) au lieu de les rattacher en silence — et le dire AVANT le
  GO : un perimetre valide peut publier N liens morts. Verificateur pret a lancer :
  `scripts/inspection_pre_push.py <chemins> --refs`.

## Voir aussi

- Skill `github` (authentification, releases, `gh`), skill `llm-wiki` (compilation
  non-agentique du wiki). La recette locale du wiki et de SiYuan est dans
  `references/wiki-l1-et-siyuan.md`, le verificateur dans `scripts/verify_wiki.py`. L'inspection en lecture seule d'un lot de chemins
(tailles, CR/LF de l'arbre contre l'objet versionne, suivi/versionnement, renvois, secrets masques) est
dans `scripts/inspection_pre_push.py`. Les trois controles bloquants de publication, la mesure de ce qui part reellement dans un push, la recette de figeage de la derive (exclusions
locales, lecture des colonnes de `git status --porcelain`, preuve du tip distant) et le
rafraichissement d'un clone en retard, et l'**ecriture concurrente de la revue d'arriere-plan** (elle
  ecrit dans les 2 min qui suivent une ecriture de session : attendre ~3 min, prouver la stabilite par
  empreinte du lot entier (md5 + mtime + taille) relevee deux fois, s'orienter dans `skills/.curator_ledger.jsonl`, ne pas confondre
  `pending/memory/*.json` avec une ecriture) sont dans `references/publication-push-gate.md`. La mecanique de fin de rebase sur ce depot (resolution
de conflit, `--continue` qui refuse avec un index propre, `stash pop` bloque, stash droppe recuperable)
est dans `references/rebase-et-stash-recuperation.md`. L'**enumeration des sources a interroger avant
de declarer qu'une version ou un artefact n'existe pas** (historique `-S` tous fichiers, tags, branches,
stash, clone frere, arbre de travail y compris NON suivi, sauvegardes, remote), les deux pieges qui font
conclure a tort (le numero est celui d'un composant ; le runtime recopie la demande dans ses journaux)
et la recette `rg` bornee sont dans `references/prouver-absence-version.md`. Le skill
  `github` est un bundle (non modifiable) : les recettes GitHub propres a ce depot vivent donc ici,
  section « Rendre la version visible sur la page d'accueil ».
