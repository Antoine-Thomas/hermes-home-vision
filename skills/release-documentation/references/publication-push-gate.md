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
`??` d'installation, de plugin-update-checks et de skills archivees). La derive bouge **pendant**
l'audit : recompter (`wc -l`) juste avant de s'engager sur un chiffre, ne jamais soustraire de tete.

Figer la derive est un commit dedie **et une decision de l'utilisateur**, jamais une initiative
d'agent : s'arreter, annoncer `push: non` avec le compte exact, et proposer les options.

### Tout ce qui derive ne se committe pas

Deux familles d'entrees de derive n'ont rien a faire dans un commit :

    ?? installs/   ~884 Mo / ~44 000 fichiers   (venv de plugins : site-packages, cacert.pem)
    ?? tools/      ~1,6 Go / ~16 000 fichiers   (chrome.dll 273 Mo, ffmpeg.exe 163 Mo, node.exe 103 Mo)

Les committer fait passer le controle **(b)** au rouge — le depot est public et GitHub refuse tout
blob > 100 Mo — et tente un push de plusieurs Go. **Les exclure LOCALEMENT**, jamais dans
`.gitignore` : ce fichier est versionne, l'y ecrire ajoute une entree de derive au commit cense la
reduire. `.git/info/exclude` ne l'est pas :

    # .git/info/exclude  (motifs ancres a la RACINE du depot)
    /installs/
    /tools/
    /plugin-update-checks/
    /source-checks/
    /plugins/.install-metadata.json
    /telegram_update_receipts_*.json

Un motif commencant par `/` ne couvre **pas** les jumeaux cote profils
(`profiles/<p>/plugin-update-checks/`, `profiles/<p>/telegram_update_receipts_*.json`) : ils restent
visibles et partent avec le commit (1 Ko chacun) — l'annoncer au lieu de croire l'exclusion totale.
Faire relire le fichier apres ecriture, puis **recompter** `git status --porcelain` : le compte reel
apres exclusions n'est pas celui annonce avant.

**Un `??` se classe par son EMPLACEMENT, pas par son statut git.** Les deux familles ci-dessus sont des
artefacts a exclure ; a l'inverse la revue d'arriere-plan cree de vrais fichiers non suivis
(`?? skills/<skill>/scripts/<outil>.py`) qui sont du **contenu** a committer. Lire le chemin avant de
trancher : arbre d'installation ou de runtime (`installs/`, `tools/`, `plugin-update-checks/`,
`source-checks/`) = exclure ; `skills/**` = committer. Un `??` laisse en derive d'un tour sur l'autre
sans traitement nomme est le signe qu'aucune des deux decisions n'a ete prise — le dire dans le rapport
plutot que le laisser pour compte.

**Avant d'ajouter une ligne, verifier ce qui est DEJA couvert** : `git check-ignore -v <chemin>` nomme
la regle qui matche (fichier + numero de ligne). Sur un repertoire de profil, `.gitignore` couvre deja
`state.db*`, `sessions/`, `cache/`, `logs/`, `workspace/` et `.env` ; seuls `plans/` et `locks/` ne le
sont pas. Donc pour un **profil de travail** qui n'a rien a publier : **une seule ligne de dossier**
(`/profiles/<nom>/`, ancree a la racine), precedee d'une ligne de commentaire qui dit pourquoi il n'est
pas versionne — jamais une ligne par fichier, et jamais une ligne redondante avec une regle existante
(elle se relit comme un oubli et noie le fichier). Preuve a rapporter : `git status --porcelain
profiles/<nom>/` vide **et** le profil absent du porcelain global.

Bonus : un chemin exclu n'est plus indexable par accident — `git add <chemin>` echoue sans `-f` (git
le liste comme ignore). L'exclusion sert donc aussi de garde-fou contre un `git add` lance trop
large.

### `cron/jobs.json` : modifie en permanence par le planificateur

Ce fichier porte les **definitions** de jobs (contenu utile) ET l'**etat de runtime** (`last_run_at`,
`next_run_at`, `completed`, `lateness_seconds`). Le planificateur le reecrit a chaque tir de job : il est
donc **TOUJOURS** sale. C'est un etat normal, pas une derive.

Ne le committer que quand une **definition** change. Garde-fou, a lancer avant le `git add` :

    git diff -U0 cron/jobs.json | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' \
      | grep -vE '"(completed|next_run_at|last_run_at|updated_at|scheduled_at|dispatched_at|lateness_seconds)"'

Sortie **vide** = 100 % de bruit de runtime = on ne committe pas. Sortie **non vide** = une definition a
bouge = on committe (le diff est alors petit et lisible, donc utile).

Les deux lignes d'en-tete du diff (`--- a/...`, `+++ b/...`) matchent aussi `^[+-]` : sans le
`grep -vE '^(\+\+\+|---)'`, la sortie n'est **jamais** vide et le garde-fou valide le bruit comme du
contenu. Mesure (27/09/2026) sur un diff de 24 lignes 100 % runtime : sans l'exclusion, deux lignes de
sortie ; avec, zero. Un garde-fou se teste sur un cas de bruit **avant** d'etre fige, sinon il ne dit rien.

Mesure (27/09/2026) : 24 lignes de diff (12 ajouts, 12 suppressions), dont **0** touchant une definition —
les 24 se repartissent sur `completed` (4), `next_run_at` (4), `last_run_at` (4), `scheduled_at` (4),
`dispatched_at` (4), `lateness_seconds` (2), `updated_at` (2), produites par 2 jobs sur 14. Le nombre de
lignes varie donc avec le nombre de jobs qui tirent, pas avec le contenu : un seuil du type « moins de
10 lignes = bruit, plus de 20 = contenu » classe a tort un diff de 24 lignes comme du contenu. Le fichier
fait 697 lignes dont 87 (12,5 %) d'etat de runtime, et l'historique ne le committe que par figeage.

Corollaire : dans tout releve de porcelain, la ligne ` M cron/jobs.json` **ne compte pas** comme une
entree de derive. Un porcelain de 10 entrees dont 1 est `cron/jobs.json` = 9 vraies entrees.

### Les deux colonnes de `git status --porcelain` apres un `git add`

Un porcelain **non vide apres un `git add` n'est pas une anomalie** : les fichiers indexes passent en
**premiere** colonne (`M  fichier`), les modifications restant a indexer en seconde (` M fichier`),
les non suivis en `??`. Lire les colonnes, pas le nombre de lignes :

    git status --porcelain | grep -cE '^[MADR]'   # indexe
    git status --porcelain | grep -cE '^.[MD]'    # reste a indexer
    git status --porcelain | grep -c '^??'        # non suivi

Deux pieges de comptage : git **regroupe une suppression et son ajout en `R`** (40 chemins nommes =
38 lignes de porcelain), et un `git add` par lots (artefacts de runtime / contenu / archivage) se
controle apres chaque lot avec `git diff --cached --name-only | wc -l`. Garde-fous avant de
committer : `git diff --cached --name-only | grep -E "^(installs|tools)/"` vide, et les plus gros
blobs indexes lus en `sort -rn` sur leur taille.

**Une liste de fichiers annoncee n'est pas un contrat.** Entre deux releves espaces de 5 min,
`cron/jobs.json` est revenu modifie (`completed` +1, `last_run_at` et `next_run_at` avances par le
planificateur) et l'ecriture que la session vient de faire pour un cycle ulterieur reste dans le
porcelain. Le critere d'arret porte donc sur le **contenu du commit** : indexer le sous-ensemble
nomme, prouver `git diff --cached --name-only` == cet ensemble, `git show --stat HEAD` apres chaque
commit, et **rapporter** les entrees restantes (writer de runtime, ecriture en attente) au lieu de
les absorber ou d'annoncer un echec.

Corollaire : **le chemin d'un fichier cite par la demande est un souvenir, pas une reference.**
Relever le chemin exact dans `git status --porcelain` (nouveaux fichiers compris) avant l'`add` : un
fichier annonce a la racine du depot peut vivre sous `skills/<skill>/scripts/`. Un `git add` a
plusieurs chemins dont un faux n'echoue que pour ce pathspec et indexe **les autres** — l'index
partiel se voit au seul controle `git diff --cached --name-only` == l'ensemble nomme.

### La sequence complete du figeage, puis push immediat

L'ordre qui fonctionne, et ce qui doit etre prouve a chaque etape :

1. `git status --porcelain` **et** le decompte par famille (` M`, ` D`, `??`) — annoncer un chiffre
   **lu**, jamais soustrait de tete : apres exclusion des artefacts lourds et apres remise a HEAD
   d'un fichier d'aplomb, le total est plus bas que ce que la demande annonce.
2. `git add` **par lots nommes** (artefacts de runtime / contenu / archivage curator), en imprimant
   `git diff --cached --name-only | wc -l` apres chaque lot : un add nomme est auditable, un `-A`
   embarque l'etat d'execution.
3. Relire le porcelain **par colonne** (voir ci-dessus) et prouver que le lot ne porte ni
   `config.yaml` ni chemin lourd :
   `git diff --cached --name-only | grep -E "(^config\.yaml$|^(installs|tools)/|\.onnx$)"` vide,
   plus gros blob indexe lu en `sort -rn`.
4. Commit avec **le compte reel dans le message** — il documente ce qui a ete fige :
   `chore(runtime): freeze local drift before push (40 entries)`.
5. Push immediat, puis double preuve du tip (voir « Verifier le tip distant sans ambiguite »). La
   derive peut redevenir non vide en quelques minutes (le runtime reecrit
   `cron/usage_audit.jsonl`, `skills/.usage.json`, `.curator_state`) : c'est l'etat normal apres un
   figeage, pas un echec.

### Un ` M` sur un fichier identique a HEAD = cache de stat, pas un contenu

Apres avoir remis un fichier d'aplomb (retrait du bloc de test laisse dans `config.yaml`),
`git status` peut encore afficher ` M` alors que `git diff` est vide : effet de fin de ligne
(`.gitattributes` `* text=auto`) plus cache de stat. Trancher par les **trois empreintes**, filtres
appliques :

    git hash-object --path=<fichier> <fichier>     # worktree, filtres CRLF appliques
    git ls-files -s <fichier> | awk '{print $2}'   # index
    git rev-parse HEAD:<fichier>                   # HEAD

Identiques = contenu identique ; `git update-index --refresh -- <fichier>` (metadonnees de stat
seulement, aucun contenu) fait disparaitre le `M`. Ne pas annoncer « diff restant » sur la seule
colonne de `git status`.

**Un `sha256sum` brut ne se compare JAMAIS avec un sha256 d'index, de blob ou de ledger.** Le fichier
sur disque est en CRLF, `.gitattributes` (`* text=auto eol=lf`) le normalise en LF a l'index : les
empreintes different toujours (mesure : trois valeurs distinctes pour un fichier d'aplomb — disque,
blob indexe, sha256 du ledger). Comparer des **blobs** (`git hash-object --path`), pas des sha256
bruts, et le dire plutot que de partir chasser un drift de contenu inexistant.

La preuve la plus courte que le commit contient exactement l'etat du disque, **et** que le clone a le
meme contenu : `git hash-object --path=<f> <f>` == `git rev-parse HEAD:<f>` cote depot canonique **et**
cote clone — meme blob = meme contenu normalise, quelle que soit la fin de ligne locale.

### Verifier le tip distant sans ambiguite

`git ls-remote origin main` est la reference : aucun cache intermediaire. L'API
`/commits?per_page=N` piege un `grep '"sha"'` — la premiere occurrence est le sha du commit, la
**deuxieme est le sha de son tree**, ce qui ressemble a un commit inconnu intercale dans l'historique.
Comparer `git rev-parse HEAD`, `git rev-parse origin/main` et `git ls-remote origin main` ; lire
`git status -sb` : `## main...origin/main` **sans** `ahead/behind` prouve l'alignement.

Note d'outillage : `write_file` refuse d'ecraser un fichier qui a ete lu plus tot avec pagination
(« last read with offset/limit ») — passer par `patch`, qui preserve le reste du fichier.

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

**Prouver que le pull a apporte le contenu**, pas seulement que le HEAD a bouge : les lignes
`create mode ... <chemin>` de la sortie du pull nomment les fichiers arrives ; puis `ls -l` sur la
page attendue et lecture d'un marqueur interne (`grep -m1 'updated:' <fiche>`). Un `git rev-parse
HEAD` egal de part et d'autre ne dit rien du contenu reellement present.

## Ecriture concurrente du curator (revue d'arriere-plan)

### 1. Le phenomene et son minutage

Une **revue d'arriere-plan** (fork du curateur) tourne apres le travail d'une session et ecrit dans les
**memes** fichiers que celle-ci : les `SKILL.md` et `references/*.md` des skills, et
`memories/MEMORY.md`. Un `git add` peut donc capturer un etat a moitie ecrit par elle — et un porcelain
qui « bouge tout seul » ne vient pas forcement du runtime.

Mesure sur cette machine : skill patche a 12:22:41, memoire ecrite a 12:22:43, fin du tour de revue a
12:22:52 (`Background review complete ... result=skill+memory`, `origin=background_review`) — soit
**dans les 2 minutes** autour des ecritures de la session. Elle suit la session de tres pres : profil
cree a 12:36, section documentaire ecrite par la revue a 12:37:19.

**Elle repasse PENDANT une longue session, pas seulement apres.** Sur un seul tour de travail : deux
passes a ~35 min d'intervalle, la seconde reecrivant 4 fichiers que la session venait de committer
~40 min plus tot — la derive est ainsi repassee de 1 a 10 entrees sans que la session ait touche a une
seule skill. Trois consequences a tenir : un arbre propre juste apres un commit est un etat
**transitoire**, pas un acquis ; ne pas recommitter sa derive a chaque cycle (c'est un commit par passe)
mais la **grouper** dans un gel dedie ; et ne pas lire sa reapparition comme un echec du commit
precedent.

**Consequence pratique de la cadence (~15 min) : un depot propre n'est pas un objectif atteignable, c'est
un etat de quelques minutes.** Mesure (27/09/2026) : 4 passes en 1 h 04 — 13:20, 13:56, 14:08, 14:24 —
chacune pendant que la session travaillait. La regle des 3 min de stabilite reste, mais elle devient :
**verifier la stabilite, geler l'ENSEMBLE des entrees curator, pousser, accepter la re-derive** dans les
15 min. Le gel se fait donc a un moment **choisi** (fin de session, fin d'heure, avant un push important),
jamais une passe apres l'autre.

### 2. Comment le detecter

`skills/.curator_ledger.jsonl` est la source de verite : une ligne JSON par ecriture, avec
`"actor": "agent"` = la session elle-meme, `"actor": "curator"` = la revue, `evidence.session_id` (la
session a l'origine de la revue), `evidence.file_path`, et les sha256 `before`/`after` ; les contenus
sont archives dans `.curator_backups/blobs/`.

**Angle mort du ledger** : il ne journalise que les ecritures passees par l'outillage de skill
(`skill_manage` / patch) — une ecriture **directe** du fichier (script, `write_file`, redirection
shell) n'y laisse **aucune** entree. Fait, mesure et parade : **point 6**.

Mesure par horodatage, avant tout commit d'un fichier de cette famille :

    stat -c '%y  %n' <fichiers> ; wc -l <fichiers>
    sleep 30
    stat -c '%y  %n' <fichiers> ; wc -l <fichiers>      # identiques = stable

**Sur un lot, une empreinte par fichier vaut mieux qu'un `stat` ligne a ligne** : un `wc -l` identique
ne dit rien d'une reecriture a nombre de lignes constant. Prendre une photo **complete** du lot, puis
la comparer a la seconde photo — une seule commande couvre les N fichiers et un seul `diff` tranche :

    for f in <fichiers>; do printf '%s  %s  %s\n' "$(md5sum "$f" | cut -c1-32)" "$(stat -c '%Y %s' "$f")" "$f"; done > "$TMPDIR/t0.txt"
    sleep 180
    ... meme boucle ... > "$TMPDIR/t1.txt"
    diff "$TMPDIR/t0.txt" "$TMPDIR/t1.txt" && echo IDENTIQUE

`diff` muet = md5, mtime **et** taille inchanges sur tout le lot. Refaire la photo **juste avant le
`git add`** : la fenetre de 3 min prouve le passe, pas l'instant de l'indexation.

**Prouver qu'aucune nouvelle passe n'a eu lieu PENDANT la fenetre** : relever `wc -l
skills/.curator_ledger.jsonl` et le `ts` de sa derniere ligne avant et apres le `sleep`. Compte et
horodatage inchanges = la revue n'est pas repassee pendant la mesure ; un `ts` plus recent = elle est
revenue et la stabilite des fichiers est a reprendre. Les deux controles sont complementaires : la photo
des fichiers prouve l'immobilite, le ledger dit **par qui** et **quand** — et il est la seule source qui
permette d'attribuer a la revue une derive que la session n'a pas produite.

Le reste de l'identification (inventaire des processus reellement actifs, propositions en attente) est
dans la section « revue d'arriere-plan » du skill `hermes-operations`.

### 3. Discipline avant de committer

Apres la derniere ecriture documentaire : **attendre ~3 min**, prouver la stabilite (horodatages releves
deux fois a >= 30 s d'ecart, plus `wc -l`), puis `git add` **par chemin explicite** — jamais `-A`,
jamais un repertoire entier. Sinon on fige un etat a moitie ecrit : le diff valide n'est plus celui qui
part. Et **un diff qui porte des lignes qu'on n'a pas ecrites se NOMME** dans le message de commit et
dans le rapport (par exemple « passes concurrentes fusionnees ») au lieu d'etre absorbe en silence.

### 4. `pending/memory/*.json` : propositions sans effet

Les propositions de **memoire** de la revue vivent dans `pending/memory/*.json` (`origin:
"background_review"`) et **n'ont aucun effet tant qu'elles ne sont pas approuvees** : `MEMORY.md` n'est
pas modifie par une proposition en attente. Observe sur un meme tour de revue : un **ajout** a ete
applique directement (`logs/agent.log` : `tool memory completed`, quelques centaines de caracteres) tandis
que la **reecriture d'une entree existante** restait en attente. Le backlog s'accumule : 7 propositions
entre le 17/09 et le 27/09, aucune appliquee.

### 5. Le piege de la sonde par debut de texte

Prouver qu'une proposition est **appliquee** par la **FIN** du texte propose, jamais par son debut :
quand seule la tete de l'entree change (`v0.21.3` -> `v0.21.5`), les 70 premiers caracteres sont
identiques et la comparaison conclut a tort « applique ». Confirmer par un controle direct du fait
introduit (`grep -c "v0.21.5" memories/MEMORY.md`).

### 6. L'angle mort du ledger

**Le fait.** Le ledger ne journalise que les ecritures passees par l'outillage de skill (`skill_manage`,
`patch`). Une ecriture **directe** du fichier — script Python, `write_file`, redirection shell, redaction
manuelle — n'y laisse **aucune** entree, ni cote `curator` ni cote `agent` : la derniere entree pour ce
fichier peut donc etre **plus ancienne que le fichier lui-meme** (mesure : fusion ecrite a 12:44:18,
derniere entree du ledger 12:40:06 — ecart non journalise).

**La regle.** La date du ledger n'est **pas** une preuve d'immobilite : « pas d'entree curator apres mon
ecriture » ne prouve pas qu'aucun tiers n'a ecrit. Le ledger sert a **attribuer** une ecriture a son
auteur, jamais a **enumerer** les ecritures.

**La parade.** La preuve d'immobilite reste `stat -c '%y  %n'` + `wc -l` releves deux fois a >= 30 s
d'ecart (regle du point 3). Une ecriture faite par script etant invisible dans l'historique du fichier,
un diff qui porte des lignes qu'on n'a pas ecrites se **nomme** dans le message de commit.
