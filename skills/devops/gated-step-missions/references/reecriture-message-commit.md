# Reecrire le message d'un commit existant (amend, sans toucher aux fichiers)

Classe de mission : « je veux changer UNIQUEMENT le message de ce commit ». Aucun `git add`, aucun
fichier modifie, aucun autre commit touche, un GO entre chaque etape.

## 0. Localiser la cible avant tout

Le GO doit porter trois choses : chemin absolu du depot, branche, hash court (ou « HEAD »). S'il en
manque une, DEMANDER et s'arreter — pas de recherche large sur le disque (regle « une cible non
identifiee se DEMANDE » du SKILL.md).

## 1. Etat actuel (lecture seule)

```bash
cd <depot>
git branch --show-current
git log -1 --pretty=full
git log -1 --stat
git status --short
git status -sb                 # [ahead N] = commit jamais pousse
ARBRE_AVANT=$(git rev-parse HEAD^{tree})
git diff --cached --quiet && echo "index propre" || echo "INDEX NON PROPRE"
```

Noter aussi `git rev-parse HEAD` (hash AVANT).

## 2. Le message passe par un FICHIER, hors du depot

Ecrire le message exact (titre, ligne vide, corps) dans
`${TMPDIR:-$LOCALAPPDATA/Temp}/msg_commit.txt` — **jamais dans le depot** : un fichier neuf y
apparaitrait aussitot comme un fichier change. Puis :

```bash
git commit --amend -F /chemin/msg_commit.txt --cleanup=verbatim
```

- `-F` evite le quoting d'un texte multi-lignes accentue en argv, et empeche qu'un secret finisse sur
  une ligne de commande.
- `--cleanup=verbatim` conserve les lignes vides et toute ligne commencant par `#` (le nettoyage par
  defaut les retire).
- Sans `-F` ni `-m`, l'amend ouvre un editeur : echec en shell non interactif.
- **Aucun `git add`** : l'amend reutilise l'index courant. Si rien n'est stage, l'arbre du nouveau
  commit reste identique a l'octet.

## 3. Verifier (preuve de non-changement)

```bash
git rev-parse HEAD          # hash APRES — different, c'est normal
git rev-parse HEAD^{tree}   # DOIT etre egal a $ARBRE_AVANT
git log -1 --pretty=full    # nouveau message
git show --stat HEAD        # memes fichiers, memes N/M lignes
git status --short          # inchange depuis l'etape 1
```

L'egalite des DEUX hash d'arbre est la preuve ; `git show --stat` la rend lisible. Rapport :
`hash avant -> hash apres`, diff du message, « fichiers identiques : oui/non ».

## 4. Pousser — sur GO explicite

```bash
git status -sb      # pas de "up to date" + [ahead N] = jamais pousse -> push normal
git branch -vv      # [origin/<branche>] portant le MEME hash = deja publie
```

- Jamais pousse : `git push origin <branche>`.
- Deja publie : montrer `git push --force-with-lease origin <branche>` et n'executer qu'apres GO.
  Jamais `--force` nu : `--force-with-lease` refuse si le distant a bouge, et un refus se RAPPORTE,
  il ne se contourne pas (`git fetch` d'abord si le refus vient d'une reference locale perimee).
- Verifier : `git log -1 --pretty=oneline origin/<branche>` = HEAD local.

## 5. Rollback

L'ancien commit reste accessible par `git reflog` (l'amend ne supprime rien) : le hash AVANT est le
point de retour. Le journal de mission porte hash avant, hash apres, message applique, statut push.

## Pieges

- **Un amend ramasse ce qui est STAGE.** Si l'index porte une modification, `--amend` l'incorpore au
  commit : l'arbre change et le « changement de message » devient un changement de fichier masque.
  Exiger `git diff --cached --quiet` VRAI avant d'amender, sinon s'arreter et le dire.
- **Un commit qui n'est pas HEAD ne s'amende pas.** `git commit --amend` ne touche que HEAD ; reecrire
  un commit plus ancien impose un `rebase -i` (reword), qui reecrit TOUS les descendants et change
  leurs hash. Le refuser, l'expliquer, demander un GO dedie.
- **Un depot de travail sale n'interdit pas l'amend — mais interdit de pretendre « arbre propre ».**
  Mesurer `git status --short`, dire ce qui est modifie et confirmer que ces fichiers ne sont PAS dans
  le commit, au lieu de refuser l'etape. Les clones de configuration Hermes sont durablement sales
  (bruit des outils) : voir la skill `hermes-provider-config`.
- **`git show --stat` est plus faible que l'egalite des arbres** : deux contenus differents peuvent
  donner les memes N/M lignes. Rapporter les deux preuves.
- **Une cible « qui parle du meme sujet » n'est pas la cible.** Si l'artefact demande n'existe pas
  (aucun depot ne porte ce commit, le code vit dans un dossier ignore par git), le rapport dit l'ecart
  entre la premisse et la mesure et rend la question — il n'amende pas le commit voisin, et il ne
  demande pas de GO pour autre chose.
- Interdits a rappeler dans le rapport : `--no-verify`, `git add`, stash silencieux, `reset`, edition
  d'un autre commit.
- Apres un push reecrit, tout ce qui pointait l'ancien hash (clone secondaire, note, CI) reste sur
  l'ancien objet : le signaler AVANT de pousser, pas apres.
