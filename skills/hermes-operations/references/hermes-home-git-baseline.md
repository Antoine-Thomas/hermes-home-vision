## Versionner le home Hermes dans git (baseline sans secret)

But : un depot qui permet de revenir en arriere sur `skills/`, `profiles/`, `config.yaml` — et qui
ne contient **aucun** secret. Le home melange la configuration a proteger et des donnees d'execution
volumineuses ou sensibles, donc c'est le `.gitignore` qui porte la politique.

### 1. Initialiser au bon niveau

- `git init` a la **racine du home** (`%LOCALAPPDATA%\hermes`), pas dans `skills/` : `profiles/` doit
  etre versionne dans le meme depot, sinon un rollback de profil reste impossible.
- `hermes-agent/` est un depot git **imbrique** (et un venv) : l'ignorer, sinon l'index avale
  l'historique upstream.
- `data/` contient d'autres depots imbriques (`data/nim-clients/.git`) et des venv : ignorer `data/`
  en bloc.

### 2. Motifs d'exclusion, chacun pour une raison

| Motif | Raison |
|---|---|
| `.env`, `**/.env`, `.env.*`, `auth.json`, `*.sec` | secrets en clair |
| `whatsapp/`, `mcp-tokens/`, `pairing/` | sessions et jetons d'applications tierces |
| `*_token.json`, `*client_secret*.json`, `*secret*.json` | identifiants OAuth deposes en clair (Google, MCP) |
| `logs/`, `sessions/`, `cache/`, `pastes/`, `backups/`, `captures/`, `audio_cache/`, `image_cache/`, `pending_messages/`, `sandboxes/` | donnees d'execution |
| `*.db*`, `*.lock`, `*.pid`, `*.tmp`, `models_dev_cache*`, `*_cache.json`, `.hermes_history` | etat et caches regenerables |
| `*.exe`, `*.dll`, `*.onnx`, `*.safetensors`, `*.zip`, `*.tar.gz`, `.curator_backups/`, `skills_backup_*/` | volume : les poids sous `skills/` pesent des centaines de Mo |
| `nul`, `con`, `prn`, `aux`, `com1`… | noms de peripheriques Windows |
| `**/cron/ticker_*`, `**/cron/catch_up_occurrences`, `cron/output/` | reecrits chaque minute |

- **Un fichier nomme `nul` a la racine fait echouer tout `git add -A`** avec `error: invalid path 'nul'`
  et `fatal: adding files failed` : **rien** n'est indexe, alors que le dry-run semblait bon. C'est un
  fichier poubelle cree par une redirection Windows ratee ; l'ignorer suffit (ne pas le supprimer sans
  demande).
- **`.gitignore` ne detache pas un fichier deja suivi** : apres ajout d'un motif, `git rm --cached <f>`
  puis re-commit, sinon l'arbre reste sale en boucle.
- **Verifier l'arbre 1 a 2 minutes apres le commit.** Les fichiers volatils (ticker cron, heartbeats)
  ne se revelent qu'a ce delai : `git status --short` doit etre vide a froid.

### 2 bis. Auditer un depot de snapshot DEJA existant

Un depot de sauvegarde vit a cote de la config (ici `Desktop\hermes_install`). Y committer du neuf
n'autorise pas a le croire propre : **l'ensemble suivi est la seule verite**, pas son `.gitignore`.

```bash
git -C <chemin NATIF> ls-files | grep -iE '\.env|state\.db|secret|token'   # avant tout commit
git -C <chemin NATIF> remote -v                                            # aucun remote = risque local
```

- Un `.gitignore` ecrit en liste **partielle** (`.env.pre_update` mais pas `snapshot/.env`) laisse
  passer les copies brutes : un depot de snapshot finit par **suivre** des `.env` entiers et une copie
  de `state.db` (des centaines de Mo, avec l'historique de conversation dedans).
- Correctif : `git rm --cached <fichier>` + motifs larges (`.env*`, `*.env`, `state.db*`), puis purge
  d'historique seulement si le depot a ete pousse ou copie ailleurs. Sans remote, le risque reste
  **local** (un zip du dossier suffit) : ca change l'urgence, pas le correctif du suivi.
- **Aucun `.env` ne se versionne, sous aucune forme** — ni brut, ni `.avant_*`, ni `.bak`. Ce qui se
  committe, c'est un **config redacte** produit exprès pour le depot (empreintes `sha256[:16]` a la
  place des valeurs). Un motif generique ne suffit pas : nommer chaque chemin reellement present
  (`snapshot/.env`, `snapshot/state.db*`, `backups/**/*.env*`, `**/*.db-wal`, `**/*.db-shm`) et
  verifier le resultat par `git ls-files | grep -E '\.env|state\.db'` **vide**.
- **Chiffrer la purge avant de la proposer, et ne pas la lancer d'office.** Le `.git/` d'un depot de
  snapshot pese ce que pese son plus gros blob (ici ~80 Mo pour une copie de `state.db` de 192 Mo) :
  le mesurer (`git count-objects -vH`) et le dire. Le cout reel n'est pas le disque mais la
  **reecriture des SHA** : les identifiants de commit deja cites dans les rapports deviennent
  invalides. Annoncer le nombre de commits touches, laisser l'operateur trancher, et si la decision
  est de reporter, documenter la commande (`git filter-repo --path <f> --invert-paths`) comme
  « disponible si le depot est un jour partage » plutot que de la garder en tete.
- **`git -C` exige un chemin NATIF** (`C:/Users/...`) : un chemin MSYS `/c/Users/...` est refuse
  (`fatal: cannot change to ... No such file or directory`), ce qui fait conclure a tort « ce n'est pas
  un depot git » alors que `.git/` existe. Verifier avec `ls -la <dossier>/.git` avant de le declarer
  absent.

### 3. Scan pre-commit par empreinte (obligatoire, avant le premier commit)

Enumere les fichiers indexes (`git ls-files > liste`) puis passe chaque fichier sur les familles de
motifs : `\b[0-9]{8,12}:[A-Za-z0-9_-]{30,45}\b` (bot Telegram), `sk-[A-Za-z0-9_-]{20,}`, `AIza…`,
`ghp_`/`github_pat_`, `hf_…`, `-----BEGIN … PRIVATE KEY-----`, et une affectation generique
`(TOKEN|SECRET|PASSWORD|API_KEY)\s*[:=]\s*[…]{18,}`.

- Rapporter **fichier + longueur + `sha256[:12]`** — jamais la valeur.
- Faux positifs attendus : `tokenizer=`, `user_password=`, `ENV_API_KEY =`, `AIRTABLE_API_KEY` — des
  **noms de variables** dans des scripts et des docs.
- Le vrai piege : un **exemple `curl` dans une doc de skill** peut contenir une cle reelle
  (`-d '{"key":"sk-…"}'`). Une meme doc est dupliquee sous `skills/`, `profiles/*/skills/` et
  `.archive/` : masquer l'exemple dans **toutes** les copies, sinon la fuite revient au commit suivant.
- **Un nom de fichier ne prouve rien : scanner le CONTENU des fichiers suivis, pas seulement les noms.**
  Un fichier baptise `env.pre_update.redacted` a porte un **jeton Telegram en clair** pendant des
  semaines : le nom decrit une intention, pas un etat. Le filtre par nom (`ls-files | grep -E
  '\.env|token|secret'`) donne des faux positifs (docs de skills qui parlent de jetons) et **laisse
  passer exactement ce qu'on cherche** ; le seul controle qui tranche est
  `git grep -I -n -E '<motifs>'` sur les fichiers suivis.
- **Trier un hit avant de conclure.** Un placeholder (`sk-EXAMPLE-…`, `your_api_key`, `ghp_xxx…`,
  `0x0000…`) n'est pas une fuite ; un match complet l'est. Rapporter `fichier:ligne` + prefixe masque +
  `sha256[:16]` + **vivacite** (un `getMe`/appel API qui repond 200 = exploitable maintenant, 401 =
  deja revoque) : c'est ce tri qui fixe l'urgence.
- **Neutraliser la ligne ne retire pas le blob.** Corriger le fichier et committer la correction est
  necessaire mais insuffisant : la valeur reste dans les commits precedents. Donc **revoquer le secret
  chez le fournisseur avant tout push**, et ne presenter la purge d'historique que comme une option
  (elle reecrit les SHA et invalide les identifiants cites dans les rapports).

### 3 ter. Auditer TOUT l'historique, pas seulement HEAD

`git ls-files` et `git grep` ne voient que l'arbre **courant**. Un secret peut vivre dans des blobs
anciens — copie de `.env` de-suivie, `state.db` de plusieurs centaines de Mo, `.env.avant_*` — qui
partent **quand meme** sur le depot distant. Le scan de HEAD ne les montre pas.

```bash
python scripts/scan_history_secrets.py "C:/Users/<user>/Desktop/<depot>" --purge-cmds
```

Le script (`scripts/scan_history_secrets.py` de ce skill) enumere chaque blob de chaque commit
(`rev-list --objects --all` + `cat-file --batch-check`, puis `cat-file --batch` en flux binaire),
cherche les motifs dans le contenu et rend `blob / chemin / taille / occurrences / sha256[:16]`.
Code de sortie 1 des qu'un motif matche : utilisable comme gate. Aucune valeur n'est affichee.

- **Ordre de grandeur observe** : un brief annoncait « le secret est dans UN fichier » ; le scan en a
trouve **6 blobs** porteurs (une copie complete de `.env`, une `state.db` de 192 Mo totalisant 21
jetons de bot et 54 cles API, un `.env.avant_*`). Purger le seul fichier cite aurait laisse partir le
jeton **encore vivant** et ~57 cles. La liste des blobs decide, pas la citation du brief.
- **Planifier la purge en UNE passe** : chaque passe oubliee = une reecriture de SHA de plus. Lister
tous les chemins porteurs, puis un seul
`git filter-repo --force --invert-paths --path <p1> --path <p2> …`. Effet de bord utile : purger
`state.db` et les `.env` fait tomber un `.git` de 80 Mo a ~4 Mo.
- **Verifier la purge avec le MEME scanner**, jamais avec `git log -p | grep` : un blob de 192 Mo ne se
prouve pas par un grep de flux (et `git log -p` sur un tel blob est impayable). Attendu apres purge :
0 blob pour chaque motif.
- **Le runtime se scanne aussi.** Un seul motif `sk-` dans tout l'historique du home peut n'etre qu'un
placeholder de documentation (`sk-EXAMPLE-…`) : trier par empreinte et par vivacite avant de conclure
ou de purger quoi que ce soit.
- `pip install git-filter-repo` suffit (outil mono-fichier, se pose dans le venv actif, s'appelle
`git filter-repo`). Il **retire les remotes** et **reecrit les tags** : re-creer les tags de securite
apres la purge, et verifier le nombre de commits (`rev-list --count` identique, SHA differents).

### 3 quater. Avant de publier (push) : controles bloquants et pieges de depot

Sur **chaque** depot, dans cet ordre — un seul rouge arrete la publication :

1. **Fichiers sensibles suivis** (les modeles d'environnement sont des exceptions *nommees*) :
   `git ls-files | grep -E '\.env|state\.db|auth\.json|\.pem$|\.key$|token|secret' | grep -v '\.example$'`
   → vide. Les hits restants sont des docs de skills (`token-leak-audit.md`…) : le justifier par le
   scan de contenu, pas par le nom.
2. **Contenu des fichiers suivis** : `git grep -I -n -E '<motifs>'` (jeton Telegram, `AIza`, `sk-`,
   `ghp_`, `hf_`, PEM) → 0.
3. **Tout l'historique** (§3 ter) → 0 blob. C'est le controle qui autorise le push d'un depot
   `docs/` ou d'un snapshot.
4. **Aucun fichier suivi > 50 Mo**, et `du -sh .git` annonce ce qu'on pousse (un `.git` de plusieurs
   dizaines de Mo vient de blobs dé-suivis encore présents dans l'historique).
5. **`.gitattributes`** : `* text=auto eol=lf`, `*.ps1`/`*.cmd`/`*.bat` en `crlf`, binaires déclarés
   (`*.png`, `*.jpg`, `*.pdf`). Sans lui, `git status` s'allume tout seul après un ajout (renormalisation
   des fins de ligne) et on croit à tort à une modification de contenu.

- **`.env.*` avale `.env.example`** : un dépôt qui publie des modèles d'environnement doit les
  dé-ignorer explicitement (`!.env.example`, `!**/.env.example`) et le vérifier
  (`git check-ignore -v .env.example`), sinon le modèle ne peut jamais être committé. Le vérifier aussi
  côté contenu : seules les URL locales et les commentaires ont le droit d'être non vides.
- **Les fichiers d'état suivis ne se stabilisent jamais** (`cron/jobs.json`, `skills/.usage.json`,
  `**/.curator_state`) : le ticker et la revue de skills les réécrivent en continu. Soit on les ignore,
  soit on assume un arbre jamais parfaitement propre — et on committe l'état courant juste avant de publier.
- **La branche locale peut s'appeler `master`** quand la procédure dit `main` : le mesurer
  (`git branch --show-current`) et pousser la branche qui existe (`git push -u origin master`) ou la
  renommer (`git branch -M main`) — jamais supposer.
- **Créer les dépôts privés** : `gh repo create <nom> --private --description "…"` **sans** README ni
  `.gitignore` (sinon un commit divergent apparait et le premier push est refusé), puis
  `git remote add origin <url>` + `git push -u origin <branche>`.
- **Ne jamais pousser ni créer de dépôt sans demande explicite** : livrer la procédure écrite et
  laisser l'opérateur l'exécuter.
- Un dépôt privé n'est pas un coffre : ce qui y entre reste dans l'historique. Passage en public =
  purge (`git filter-repo --path <f> --invert-paths`) **et** rotation de tout secret déjà poussé.
- **Verifier l'existence du depot distant AVANT de planifier le push** :
  `gh api repos/<owner>/<nom>` → 404 = il reste a creer (une etape bloquante, pas une verification).
- **La sauvegarde `.git` d'un depot qu'on reecrit se pose HORS du depot.** Un `cp -r .git
  backups/…` a l'interieur du depot apparait en non-suivi, et un `git add -A` peut ensuite indexer
  des dizaines de Mo d'objets git qui contiennent les secrets qu'on venait de purger.

### 4. Ordre de grandeur

Apres exclusions, un home Hermes complet tient en quelques milliers de fichiers et quelques Mo de
`.git` : l'essentiel est `skills/` + `profiles/*/{config.yaml,skills,cron,SOUL.md,profile.yaml}`.
Un depot qui pese des Go signale un `.gitignore` incomplet, pas un home volumineux.

### 5. Restaurer le depot sur une autre machine (installeur d'abord, puis overlay)

L'installeur Hermes **cree lui-meme** `%LOCALAPPDATA%\hermes` : l'ordre des etapes n'est pas
interchangeable.

1. **Installer Hermes d'abord** (`iex (irm https://hermes-agent.nousresearch.com/install.ps1)`) : il
   pose le runtime, le venv et Python/Node/git/ripgrep/ffmpeg. Verifier `hermes --version`.
2. **Poser la configuration du depot par-dessus, sans `git clone`** (refuse un dossier non vide) :
   `git init -b main` → `git remote add origin <url>` → `git fetch --depth 1 origin main` →
   `git checkout -f -b main origin/main`. Le checkout ecrit les fichiers suivis et **ne supprime pas**
   ceux propres a la machine (`.env`, `state.db`, `cache/`).
3. **Creer les `.env` depuis les `.env.example`** (un `.env` existant ne s'ecrase jamais), puis les
   remplir a la main : le script ne peut pas creer de secret a la place de l'operateur.
4. **Recreer les taches planifiees et demarrer les services** en distinguant trois groupes : recréables
   depuis le depot (lanceurs VBS/scripts versionnes), dépendant de fichiers **hors depot**
   (`%USERPROFILE%\SiYuan\*.vbs`, `C:\ProgramData\Hermes\*.ps1`, `data\**\*.vbs` — a **lister**, pas a
   pretendre recreer), et vestiges desactives (a ne pas recreer).
5. **Nouvelles cles par machine** : bots Telegram, cle du routeur, jeton SiYuan. Reutiliser celles de la
   machine d'origine casse l'isolation des profils et fait repondre deux machines sur un meme bot.

### 6. Fusionner deux depots en un seul (runtime + docs)

Objectif courant : un depot prive unique contenant le runtime **et** la documentation rangee sous
`docs/`, avec l'historique des deux preserve.

1. **Ne jamais fusionner dans l'arbre vivant.** Cloner le runtime dans un dossier de travail
   (`git clone <home> <scratch>`), y faire la fusion, puis avancer le runtime en `--ff-only`. Une
   fusion faite sur place **materialise** les fichiers de l'autre depot dans le runtime — dont une
   copie `skills/` perimee qui ecrase ou duplique les skills vivants.
2. **Precalculer les collisions** : `comm -12 <(git ls-files) des deux depots` donne la liste exacte
   des chemins presents des deux cotes. Resoudre par `git checkout --ours -- <chemin>` quand les copies
   du second depot sont des versions perimees (`git diff --stat` sur chacune pour le prouver), et
   compter les **identiques** : un `.gitattributes` pose des deux cotes ne demande aucun arbitrage.
3. `git merge --allow-unrelated-histories --no-commit <ref-distante>` puis resolution, puis commit.
   Verifier le total : `rev-list --count` = A + B + 1 **calcule en direct** (les deux comptes bougent
   entre la redaction du brief et l'execution).
4. **Un chemin resolu en `--ours` disparait de l'arbre** (le README du second depot, typiquement) : le
   restaurer depuis sa propre histoire dans le commit de rangement —
   `git show <ref-distante>:README.md > docs/README.md`.
5. **Ranger sous `docs/` dans un commit ULTERIEUR** : `git mv` sur la liste des entrees de
   `git ls-tree --name-only <ref-distante>`, en **excluant les dossiers dupliques** (le `skills/` d'un
   depot de docs). Aucune reecriture de chemin n'est necessaire — c'est ce qui garde les SHA d'origine
   lisibles par les rapports qui les citent.
6. **Les fichiers NON suivis du second depot ne bougent pas** (`.env` reels, `state.db`, caches) : ils
   resteraient dans le runtime comme surface de fuite. `git status --short --ignored` liste ce qu'un
   deplacement physique traînerait — un depot de docs peut peser 700 Mo dont 613 non suivis.
7. Le depot fusionne se pousse **apres** l'audit de son historique (§3 ter) : le controle porte sur le
   resultat de la fusion, pas sur les deux depots d'origine.
8. Ne rien supprimer du second depot avant d'avoir compare les inventaires
   (`git ls-files docs/ | wc -l` vs `git -C <second> ls-files | grep -v '^skills/' | wc -l`) et propose
   de le renommer en `*.archive` plutot que de le supprimer.
