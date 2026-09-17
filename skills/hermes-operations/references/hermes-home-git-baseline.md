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

### 4. Ordre de grandeur

Apres exclusions, un home Hermes complet tient en quelques milliers de fichiers et quelques Mo de
`.git` : l'essentiel est `skills/` + `profiles/*/{config.yaml,skills,cron,SOUL.md,profile.yaml}`.
Un depot qui pese des Go signale un `.gitignore` incomplet, pas un home volumineux.
