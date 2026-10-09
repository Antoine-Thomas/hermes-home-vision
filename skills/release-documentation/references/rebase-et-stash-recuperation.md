# Fin d'un rebase et recuperation de stash (depot runtime)

La chaine `stash cible -> rebase -> pop` sur le home runtime casse de trois facons previsibles. Ce
fichier donne la sortie de chaque cas, et la preuve a fournir apres coup.

## 0. Chaine de securite a poser AVANT

- `git branch backup-avant-rebase-<horodatage>` sur le tip courant, avant le premier commit.
- Tout ce qu'on s'apprete a ecarter avec `git checkout --` se copie d'abord dans le scratch **ignore**
  (`cache/scratch/<gel>/`, un sous-dossier par arborescence) : c'est ce qui permet de revenir a HEAD
  sans rien perdre, et ca se declare dans le rapport.
- **Un autre writer peut etre en vol** : `.hermes-update-in-progress` (racine du home, contient le PID +
  l'horodatage) signale un `hermes update` en cours. Le relever au debut et a la fin, et dire s'il a
  touche quelque chose — ne pas le prendre pour la cause d'un conflit sans le mesurer.

## 1. Conflit de rebase : lire, resoudre, verifier

`git pull --rebase` annonce `Rebasing (n/N)`, puis `Auto-merging <fichier>` pour les fusions reussies et
`CONFLICT (content): Merge conflict in <fichier>` + `error: could not apply <sha>` pour le reste.

1. Lister les conflits pour de vrai : `git status`, `git diff --name-only --diff-filter=U`.
2. Resoudre **par nature de fichier** :
   - journal append-only (log du wiki, CHANGELOG) -> union des deux blocs, ordre chronologique ;
   - fichier de configuration partage -> garder la version locale demandee par l'operateur, et le
     signaler ;
   - binaire ou index genere -> ne pas fusionner a la main, demander.
3. `grep -nE '^(<<<<<<<|=======|>>>>>>>)' <fichier>` = aucune ligne, puis `git add <fichier>` (un
   fichier a la fois, jamais `git add -A`).
4. `GIT_EDITOR=true git rebase --continue` (l'editeur force evite un blocage sur le message).

Le commit rejoue porte un numstat different de l'original quand l'amont fournissait deja une partie du
contenu (une entree de log deja presente, par exemple) : le diff plus court est le resultat correct de
l'union, pas une perte.

## 2. `git rebase --continue` refuse alors que l'index est propre

Message : `You must edit all merge conflicts and then mark them as resolved using git add`, repetitif,
alors que les faits disent le contraire. Echelle de diagnostic a passer une fois, puis conclure :

```
git ls-files -u                      # aucune entree non fusionnee
git diff --name-only --diff-filter=U # idem, vide
git ls-files --stage | awk '$3!=0'   # aucun stage > 0
ls .git/rebase-merge/                # msgnum = end, git-rebase-todo vide, done complet
ls .git/hooks/ | grep -v sample      # aucun hook actif
ls .git/index.lock                   # absent
git config --get core.splitIndex     # false, pas de .git/sharedindex*
GIT_TRACE=1 git rebase --continue    # aucune sous-commande tracee : echec avant tout travail
```

`git update-index --refresh` ne change rien. Ne pas boucler au-dela de quelques tentatives : le
comportement n'est pas documente et la cause reste a etablir (git 2.53 Windows l'a produit 4 fois de
suite, avec un index resolument propre).

**Fin deterministe** — l'index porte deja l'arbre resolu et indexe, le message du pick est sur disque :

```
git commit -F .git/rebase-merge/message        # commit sur le HEAD detache
git rev-parse HEAD                             # nouveau sha
git update-ref refs/heads/<branche> <sha>
git rebase --quit                              # retire l'etat de rebase, ne touche ni index ni arbre
git switch <branche>                           # HEAD se rattache : bascule a vide
git log --oneline -N ; git status -sb ; git rev-parse HEAD <branche> origin/<branche>
```

Le resultat vaut un rebase reussi (meme parent, meme message, meme arbre). Le rapport le declare comme
un **ecart assume a la consigne** (« pas de contournement ») avec la cause non identifiee : c'est la
verification qui le rend acceptable, pas la commodite.

## 3. `git stash pop` bloque apres le rebase

`error: Your local changes to the following files would be overwritten by merge: <fichier> ... Aborting`
— typiquement un fichier d'etat que le runtime a reecrit pendant le rebase, ou qu'un pop precedent vient
de restaurer. Recette, par entree de stash :

1. copier les fichiers fautifs dans le scratch (`cp -p`), et relever leur empreinte ;
2. `git checkout -- <fichiers>` (retour a HEAD ; les copies sont la) ;
3. `git stash pop` — noter `Dropped` (applique) ou `The stash entry is kept` (a reprendre) ;
4. `git ls-files -u` doit rester vide ; recommencer pour l'entree suivante.

- `git stash pop` **sans `--index` n'indexe rien** : c'est ce qui garantit qu'aucun fichier d'etat ne
  part dans le commit suivant. Si un `git add` a ete necessaire pour debloquer un conflit, desindexer
  aussitot (`git restore --staged <chemin>`) — un fichier de runtime stagé est un fichier de runtime
  commite tôt ou tard.
- Une entree qui ne sert plus (contenu deja en place) se droppe apres verification, sinon elle bloque
  l'entree suivante et la pile ne se vide jamais.
- `git stash list` doit finir vide, et l'arbre revenir au compte d'entrees suivies sales d'avant le gel
  (meme total M + D), sinon une partie du gel est perdue ou une entree est restee empilee.

## 4. Recuperer le contenu d'un stash droppe

Un stash droppe survit dans la base d'objets : il est simplement devenu inatteignable.

```
git fsck --unreachable | awk '/unreachable commit/{print $3}'
git log -1 --format=%s <sha>                    # « On <branche> : <message du stash> » identifie le bon
git show --name-only --format="" <sha> | grep -q "<chemin perdu>"   # confirme qu'il porte bien le fichier
git checkout <sha> -- <chemins>                 # restaure ET indexe
git restore --staged <chemins>                  # desindexe : le contenu reste sur disque, hors commit
```

Preuve a donner : `md5sum -c` sur un releve d'empreintes pris AVANT la manipulation (un fichier restaure
se verifie, il ne se raconte pas).

## 5. Ce qu'on verifie avant de dire « rebase OK »

- `git log --oneline -N` : la serie attendue (commits locaux rejoues, puis l'amont en dessous).
- `git rev-list --left-right --count origin/<branche>...HEAD` apres push = `0  0`.
- `git ls-remote origin refs/heads/<branche>` = HEAD local (preuve distante, pas la reference locale).
- Contenu distant relu sur un fichier temoin : `git show origin/<branche>:<chemin> | grep -n "<fait>"`.
- Le delta pousse ne contient aucun fichier d'etat : `git diff <sha-preexistant>..HEAD --name-only |
  grep -E '^(config\.yaml|cron/|memories/|profiles/)'` -> vide, et le dire explicitement (un commit
  local PREEXISTANT peut, lui, porter `config.yaml` : le nommer au lieu de le laisser attribuer au lot).
