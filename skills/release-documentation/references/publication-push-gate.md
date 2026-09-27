# Controles bloquants avant de pousser le depot Hermes

Le guide du depot (`docs/scripts/push-to-github.md`, section 0) impose trois controles **avant tout
push**. Commandes, sortie attendue, et ce que veut dire un rouge.

## (a) Aucun secret, dans le fichier comme dans l'HISTORIQUE

    cd %LOCALAPPDATA%\hermes
    python docs/scripts/scan_secrets_history.py --repo .
    # attendu : "RESULTAT : aucune valeur de secret reelle dans l'historique (placeholders exclus)"

Le script classe a part les placeholders (une cle d'exemple dans le `references/*.md` d'une skill,
par exemple) : ils sont imprimes avec leur empreinte et **ne comptent pas comme un rouge**. Lire la
derniere ligne, pas la liste des blobs qui matchent.

## (b) Aucun fichier suivi de plus de 50 Mo

Deux mesures ; la seconde est la vraie (ce qui part reellement dans le push) :

    git ls-files -z | xargs -0 -I{} stat -c "%s %n" "{}" | awk '$1>50000000'
    git rev-list --objects origin/main..HEAD \
      | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
      | awk '$1=="blob" {print $3, $4}' | sort -rn | head -5

Un modele volumineux (`.onnx`, `.safetensors`) doit rester dans `cache/` (ignore par `.gitignore`) :
`git ls-files | grep -E '\.onnx$'` doit etre vide. **Ancrer ou echapper le motif** : `grep laya.onnx`
matche `laya-onnx-windows.md` — le `.` est un joker — et fait croire a un fichier versionne de 1,7 Go.

## (c) Arbre figé — `git status --porcelain` vide

    git status --porcelain | wc -l        # attendu : 0

C'est le controle qui bloque en pratique : le **runtime se reecrit en permanence** (`config.yaml`,
`cron/jobs.json`, `cron/usage_audit.jsonl`, `skills/.usage.json`, `profiles/*/config.yaml`, plus les
`??` d'installation, de plugin-update-checks et de skills archivees). Mesure : 46 entrees de derive,
aucune venue des commits de la session.

Figer la derive = un commit dedie (`chore: fige la derive du runtime avant push`), et ce commit met
`config.yaml` sous version. **Decision de l'utilisateur**, jamais une initiative d'agent : s'arreter
au commit local, annoncer `push: non` avec le compte exact, et proposer les options (le figer, ou
laisser tel quel).

## Rafraichir un clone en retard

Un second clone du meme `origin` peut exister et etre en retard. Le rafraichir ne fait pas apparaitre
ce qui n'est pas pousse :

    cd <clone>                                   # cd obligatoire : git ne traduit pas les chemins MSYS
    git fetch origin
    git log --oneline HEAD..origin/main          # ce que le pull apporterait
    git pull --ff-only                           # jamais de merge ni rebase sur un clone de lecture

**Verifier qu'un contenu precis est bien en amont AVANT de promettre qu'il apparaitra** :

    git merge-base --is-ancestor <sha-du-commit> origin/main   # 0 = pousse, 1 = encore local

Un `git pull --ff-only` qui reussit sur un clone ne ramene donc pas une page ecrite dans un commit
non pousse : le dire, et ne pas lancer le pull « pour voir ». L'ecart reel a combler se mesure aussi :
`git rev-list --count HEAD..origin/main` (le clone peut etre en retard de dizaines de commits amont,
pas de deux).
