# Publier le dépôt sur GitHub (dépôt **public** depuis le 22/09/2026)

**Un seul dépôt désormais** : `hermes-home-vision`
(`https://github.com/Antoine-Thomas/hermes-home-vision`). Il contient le runtime Hermes à la racine
**et** sa documentation sous `docs/` — la fusion des deux anciens dépôts a eu lieu le 17/09/2026
(historique préservé, secret purgé).

**État au 22/09/2026** : le dépôt est **public** (`gh repo view … --json visibility` répond
`PUBLIC`), branche par défaut `main` (v1.3), tags `v1.3`, `v1.2`, `v1.1-original`. Il a été créé
privé, audité le 21/09/2026 (`scan_secrets_history.py` : 0 occurrence) puis publié le 22/09.
Toute modification de visibilité (public → privé ou l'inverse) exige de rejouer cet audit —
cf. contrôles §0 et notes §5.

| Élément local | Où | Contenu |
|---|---|---|
| Runtime | `%LOCALAPPDATA%\hermes` (racine) | `config.yaml`, `skills/`, `profiles/`, `scripts/`, `cron/`, `memories/`, `gateway-service/` |
| Documentation | `%LOCALAPPDATA%\hermes\docs\` | rapports, architecture, snapshots, scripts d'installation |

**Rien de tout ceci n'est automatique : ce guide s'exécute à la main, dans PowerShell.**

---

## 0. Avant tout push — contrôles bloquants

```powershell
cd $env:LOCALAPPDATA\hermes

# 1) aucun fichier de secret suivi (les .env.example sont des MODELES, sans valeur)
git ls-files | Select-String -Pattern '\.env|state\.db|auth\.json|\.pem$|\.key$' | Select-String -NotMatch '\.example$'
# attendu : AUCUNE ligne

# 2) aucun secret dans TOUT l'historique (pas seulement HEAD) — c'est le controle qui compte
python docs\scripts\scan_secrets_history.py --repo .
# attendu : "aucune valeur de secret reelle dans l'historique" (les placeholders sont signales a part)

# 3) aucun fichier suivi de plus de 50 Mo
git ls-files | ForEach-Object { if ((Test-Path $_) -and ((Get-Item $_).Length -gt 50MB)) { $_ } }

# 4) arbre propre (sinon figer la derive du runtime en un commit avant de pousser)
git status --short

# 5) visibilite : le depot est public depuis le 22/09/2026.
#    Toute bascule public <-> prive exige de rejouer le controle 2) (scan d'historique) avant.
```

> **Si un secret apparaît : ne pas pusher.** Le retirer du fichier **et le purger de l'historique**
> (`git filter-repo`, cf. §5), puis révoquer le secret auprès du fournisseur. Supprimer la ligne ne
> suffit jamais : le blob reste dans les commits précédents et `git clone` le ramène.

---

## 1. Le dépôt existe-t-il ?

```powershell
gh api repos/Antoine-Thomas/hermes-home-vision --jq '"\(.name) private=\(.private) size=\(.size)"'
```

- `404 Not Found` alors que le dépôt existe dans le navigateur → **problème de portée du jeton**, voir §2.
- `size > 0` → le dépôt contient déjà quelque chose (un README créé à la main, par exemple) : un
  `push` sera refusé en non-fast-forward. Le vider ou cloner puis fusionner avant de pousser.
- Créer le dépôt à la main : <https://github.com/new> → nom `hermes-home-vision`, **Public** (état
  actuel) — ou **Private** si l'audit d'historique n'a pas encore tourné, à publier après re-scan.
  Ne cocher **ni** README **ni** .gitignore **ni** licence (sinon un commit divergent apparaît).

---

## 2. Si le jeton ne voit pas le dépôt (cas rencontré le 17/09)

Symptôme : `gh repo list` ne montre que des dépôts **publics** et `gh api repos/.../hermes-home-vision`
répond `404`. `gh auth status` indique un `github_pat_…` (jeton **fine-grained**).

Cause : un PAT fine-grained n'a accès qu'aux dépôts listés dans sa portée. Un dépôt privé créé après
la génération du jeton n'y figure pas — il est donc invisible **et** imprenable en écriture (403 au
`push`).

Deux sorties, par ordre de simplicité :

1. **Éditer le jeton existant** (30 s, aucun risque) — Settings → *Developer settings* →
   *Personal access tokens* → *Fine-grained tokens* → le jeton → **Repository access** : ajouter
   `hermes-home-vision` (ou choisir *All repositories*) ; **Permissions** : `Contents: Read and write`
   (et `Administration: Read` si on veut lister/configurer). Enregistrer.
2. **Se reconnecter avec un jeton classique** ayant la portée `repo` :
   ```powershell
   gh auth login --scopes repo
   ```

Vérification après correction :
```powershell
gh api repos/Antoine-Thomas/hermes-home-vision --jq '.private, .size'   # false (dépôt public), size > 0
```

---

## 3. Pousser

```powershell
cd $env:LOCALAPPDATA\hermes
git branch -M main                       # le depot local est sur 'master' ; le README documente 'main'
git remote add origin https://github.com/Antoine-Thomas/hermes-home-vision.git
git push -u origin main
```

Sans renommage, pousser la branche existante : `git push -u origin master` — mais alors adapter le
`git fetch --depth 1 origin main` des instructions d'installation du README.

Durée : quelques secondes. Après la purge, le dépôt pèse **~4 Mo** (`.git` local 4,4 Mo, `size` API
3587 Ko au 22/09/2026), pas 80.

---

## 4. Vérifications après le premier push

```powershell
gh repo view Antoine-Thomas/hermes-home-vision --json visibility,name,defaultBranchRef
git ls-remote --heads origin              # 'main' en tete, bon SHA
git ls-files | Measure-Object -Line       # nombre de fichiers pousses, a comparer au local
```

Puis dans l'interface GitHub : onglet **Code** — vérifier la présence de `README.md`, `config.yaml`,
`profiles/`, `skills/`, `scripts/` **et** `docs/` ; confirmer visuellement qu'aucun `.env`, `.db` ou
`auth.json` n'apparaît.

Contrôle de l'historique en ligne : l'onglet **Commits** doit montrer les deux lignées (le commit de
fusion « fusion depots A+B (historique preserve, secret purge) »).

---

## 5. Notes d'exploitation

- **Purge d'historique (déjà faite une fois, à savoir refaire)** : retirer un chemin de *tout*
  l'historique, puis vérifier par re-scan :
  ```powershell
  git filter-repo --force --invert-paths --path <chemin>
  python docs\scripts\scan_secrets_history.py --repo .
  ```
  Une purge **change tous les SHA** ; les identifiants de commit cités dans les rapports deviennent
  des références historiques, pas des adresses.
- **Fins de ligne** : `.gitattributes` est unique, à la racine (`* text=auto eol=lf`, `*.ps1/*.cmd/*.bat`
  en `crlf`). Si `git status` signale des fichiers modifiés juste après, c'est la renormalisation :
  la traiter une fois (`git add --renormalize .`) dans un commit dédié.
- **Le runtime dérive en permanence** (`skills/.usage.json`, `cron/jobs.json`, `cron/usage_audit.jsonl`
  sont réécrits par le gateway). Un `git status` non vide n'est pas une anomalie : figer en un commit
  avant de pousser.
- **Ne pas commiter** : `hermes-agent/` (dépôt upstream imbriqué), `data/`, `logs/`, `cache/`,
  `state.db*`, les `.env` réels, `auth.json`, `pastes/`, `mcp-tokens/`, `whatsapp/`, `pairing/`.
- **Modifier la visibilité exige un re-scan complet** : le dépôt est **public** depuis le 22/09/2026
  (audit d'historique passé avant la bascule). Avant tout passage public → privé ou privé → public,
  rejouer `python docs\scripts\scan_secrets_history.py --repo .` et exiger 0 occurrence. Un dépôt
  n'est pas un coffre : tout secret déjà poussé doit être considéré comme compromis — retiré du
  fichier **et** purgé de l'historique (§0), puis révoqué chez le fournisseur.
- **Sauvegardes conservées hors dépôt après la fusion** :
  `Desktop\hermes_install_GIT_BACKUP_20260917_170506_AVANT_PURGE` (état **avant** purge, 80 Mo, contient
  les anciens blobs — à garder hors de tout dépôt) et
  `Desktop\hermes_install.archive` (l'ancien dépôt de documentation, dé-suivi de son rôle).
