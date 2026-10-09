# Prouver qu'une version, un commit ou un artefact N'EXISTE PAS

Une demande commence souvent par une affirmation de l'operateur — « la vX.Y existe », « le commit
d'hier porte Z », « le README est en retard d'une version ». Le livrable de la phase d'investigation
n'est pas une confirmation aimable : c'est un verdict avec les mesures qui le soutiennent. Or
**`git log -S` ne suffit pas a prouver une absence**, et deux pieges font conclure a tort.

## Les sources a enumerer, dans cet ordre

| Source | Commande | Ce que le vide prouve |
| --- | --- | --- |
| Historique complet, tous fichiers | `git log --all --oneline -S "<motif>"` | La chaine n'a jamais ete ecrite dans un fichier SUIVI |
| Idem, cible restreinte | `git log --all --oneline -S "<motif>" -- <fichier>` | Ou elle a entre/ sorti, fichier par fichier |
| Sujets de commit | `git log --all --oneline --grep="<motif>" --since=<date>` | Rien, si le motif vit dans le corps et pas le sujet |
| Contenu AJOUTE d'un commit | `git show <sha> \| grep -c "<motif>"` | Le commit annonce X mais n'ecrit que Y |
| Tags | `git tag -l` | Aucun tag ne marque cette version |
| Branches | `git branch -a` | Une branche non fusionnee peut porter l'etat cherche |
| Stash | `git stash list` | Un travail en cours non committe |
| Clone frere | `git -C <autre clone> log --all -S "<motif>"` | Verifier son HEAD d'abord (`git rev-parse HEAD`) |
| Arbre de travail (suivi) | `git status --porcelain -- <chemin>` | Le fichier est modifie ou non |
| Arbre de travail (NON suivi) | `rg -n "<motif>"` avec exclusions | **La seule source que `git log -S` ne voit pas** |
| Sauvegardes | `find <racine> -maxdepth 3 -iname "<fichier>*"` + `grep -o "<motif>"` | Etat anterieur conserve |
| Remote | `git ls-remote origin HEAD refs/heads/<b>` | La verite distante SANS fetch |

## Piege 1 — la version cherchee est celle d'un COMPOSANT

Un numero de version retenu par l'operateur peut etre celui d'une piece et non du produit : un
`plugin.yaml` (`version: 0.2.0`), un en-tete de script de supervision, un `requirements.txt`, un
champ de config. Enumerer les champs de version avant de declarer l'absence :

```bash
grep -n '^version' <racine>/plugins/*/plugin.yaml
grep -n 'VERSION\|version' <racine>/data/**/health_*.py | head
```

Cas mesure : un « ANIMA 0.2 » documente nulle part etait la `version: 0.2.0` d'un plugin **non suivi
par git** — version du produit restee 0.1 dans le README, `docs/`, le wiki et les sauvegardes. Un
fichier non committe n'apparait ni dans `git log -S` ni dans `git log --all` : l'historique seul ne
peut pas le trouver.

## Piege 2 — le runtime recopie la demande dans ses propres fichiers

Le parc journalise les sessions : `.hermes_history`, `pastes/`, `logs/agent.log`, `logs/errors.log`,
et le journal du routeur (`data/route_ia_fix/jev_routing.jsonl`). Une recherche du motif demande
y renvoie des occurrences qui ne sont que **l'echo de la demande elle-meme**. Classer les hits par
FICHIER et ecarter ces sources : un motif qui n'apparait que la n'apparait nulle part. Le controle qui
tranche : chercher aussi une variante plausible (`0.1`, la version precedente) — si elle totalise des
centaines d'occurrences dans des fichiers legitimes, l'absence de l'autre est bien un fait.

## Recherche disque : cadrer, sinon elle ne rend pas la main

Un `grep -rn` sur toute la racine du runtime depasse le timeout (`site-packages`, `node_modules`,
`tools/`, `installs/`, `cache/`). Utiliser `rg` avec exclusions explicites et **compter par fichier**
plutot qu'imprimer les lignes :

```bash
rg -no --no-ignore --hidden \
  -g '!**/.git/**' -g '!**/node_modules/**' -g '!**/site-packages/**' \
  -g '!**/venv/**' -g '!**/.venv/**' -g '!**/cache/**' -g '!**/tools/**' -g '!**/installs/**' \
  "<motif>" "<racine>" | sed 's/:.*:/ -> /' | sort | uniq -c | sort -rn
```

`rg -l` pour la liste des fichiers, `rg -no` pour le decompose par variante. Un lot qui depasse le
timeout se relance en ecrivant la sortie dans un fichier du scratch — imprimer puis relire.

## Forme du verdict

Terminer par une phrase sans ambiguite, et **nommer l'endroit ou l'operateur croit l'avoir vu** :
« `<motif>` introuvable : ni historique (toutes branches, tous fichiers), ni README local ou distant,
ni `docs/`, ni wiki, ni sauvegarde, ni stash, ni tag. La version en vigueur partout reste `<v>` » puis
les hypotheses classees (composant · sujet de commit au numero trompeur · etat perime dans un backup).
Ne pas terminer sur un presque-vu : un rapport qui laisse entendre que la chose existe coute une
seconde session.

## L'affirmation inverse : la version est DEJA en place

Avant de restaurer un artefact que l'operateur croit perdu, mesurer qu'il est absent. Trois mesures
suffisent : l'empreinte du blob sur `HEAD` ET sur `origin/main` (`git rev-parse HEAD:<f>` /
`git rev-parse origin/main:<f>` / `git hash-object <f>` — trois hash egaux = fichier deja en place),
l'etat de l'arbre (`git status --porcelain -- <f>` vide), et la ligne de version relue dans le FICHIER
(`sed -n '1,6p' <f>`) — jamais son sujet de commit. Une demande de restauration peut etre un no-op :
le dire, et proposer ce qui manque reellement (souvent un contenu plus profond, pas la version).
