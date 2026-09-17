# Publier les deux dépôts sur GitHub (privé)

Deux dépôts, deux rôles :

| Dépôt local | Nom GitHub proposé | Contenu |
|---|---|---|
| `%LOCALAPPDATA%\hermes` | `hermes-home` | configuration vivante : `config.yaml`, `skills/`, `profiles/`, `scripts/`, `cron/`, `memories/` |
| `%USERPROFILE%\Desktop\hermes_install` | `hermes-install` | documentation, rapports, snapshots, scripts d'installation |

**Rien de tout ceci n'est automatique : ce guide s'exécute à la main, dans PowerShell.**

---

## 0. Avant tout push — contrôles bloquants

```powershell
# 1) aucun fichier de secret suivi (les .env.example sont des MODELES, sans valeur)
cd $env:LOCALAPPDATA\hermes
git ls-files | Select-String -Pattern '\.env|state\.db|auth\.json|\.pem$|\.key$' | Select-String -NotMatch '\.example$'
cd $env:USERPROFILE\Desktop\hermes_install
git ls-files | Select-String -Pattern '\.env|state\.db|auth\.json|\.pem$|\.key$' | Select-String -NotMatch '\.example$'
# attendu : AUCUNE ligne

# 2) aucun motif de secret dans le CONTENU des fichiers suivis (doit etre vide)
cd $env:LOCALAPPDATA\hermes
git grep -I -n -E '[0-9]{8,12}:[A-Za-z0-9_-]{30,40}|AIza[0-9A-Za-z_-]{35}|sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|hf_[A-Za-z0-9]{30,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'
cd $env:USERPROFILE\Desktop\hermes_install
git grep -I -n -E '[0-9]{8,12}:[A-Za-z0-9_-]{30,40}|AIza[0-9A-Za-z_-]{35}|sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|hf_[A-Za-z0-9]{30,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'

# 3) aucun fichier suivi de plus de 50 Mo
git ls-files | ForEach-Object { if ((Test-Path $_) -and ((Get-Item $_).Length -gt 50MB)) { $_ } }
```

> **Si un secret apparaît : ne pas pusher.** Le neutraliser dans le fichier, commiter la correction,
> **révoquer le secret aupres du fournisseur** (BotFather `/revoke`, régénération de clé…), et
> seulement ensuite publier. Supprimer la ligne ne suffit pas : le blob reste dans les commits
> précédents.

---

## 1. Créer les deux dépôts privés

```powershell
gh auth status                      # doit afficher un compte connecte
gh repo create hermes-home    --private --description "Hermes Agent - configuration personnelle (3 profils, skills, scripts)"
gh repo create hermes-install --private --description "Hermes Agent - documentation, rapports et scripts d'installation"
```

Variante sans `gh` : créer les deux dépôts à la main sur <https://github.com/new>
(**Private**, sans README ni .gitignore, pour ne pas créer de commit divergent).

> Un dépôt privé reste un dépôt : l'historique conserve tout ce qui y a été poussé. Ne jamais passer
> l'un des deux en public sans purge d'historique (`git filter-repo`, commande dans
> `ARCHITECTURE_HERMES.md` §8) **et** sans considérer comme compromis tout secret déjà poussé.

---

## 2. Pousser `hermes-home`

```powershell
cd $env:LOCALAPPDATA\hermes
git branch -M main                       # les depots locaux sont sur 'master' ; renommer si vous visez 'main'
git remote add origin https://github.com/<ton-user>/hermes-home.git
git push -u origin main
```

Sans renommage, pousser la branche existante : `git push -u origin master`.

## 3. Pousser `hermes-install`

```powershell
cd $env:USERPROFILE\Desktop\hermes_install
git branch -M main
git remote add origin https://github.com/<ton-user>/hermes-install.git
git push -u origin main
```

---

## 4. Vérifications après le premier push

```powershell
gh repo view <ton-user>/hermes-home --json visibility,name,defaultBranchRef
git ls-remote --heads origin             # la branche attendue est en tete
```

Puis, dans l'interface GitHub : parcourir l'onglet **Code** et confirmer visuellement qu'aucun
fichier `.env`, `.db`, `auth.json` ou rapport sensible n'est présent.

---

## 5. Notes d'exploitation

- **Taille poussée** : `hermes-home` ≈ 4 Mo de `.git` ; `hermes-install` ≈ 80 Mo de `.git` — ce
  volume vient de blobs anciens dé-suivis (`snapshot/state.db` de 192 Mo compressé) encore présents
  dans l'historique. Ils sont **retirables** par purge d'historique si la taille gêne, au prix d'un
  changement de tous les SHA (traçabilité des rapports).
- **Fins de ligne** : `.gitattributes` est en place dans les deux dépôts (`* text=auto eol=lf`,
  `*.ps1/*.cmd/*.bat` en `crlf`). Si `git status` signale des fichiers modifiés juste après l'ajout,
  c'est la renormalisation : la traiter une fois (`git add --renormalize .`) dans un commit dédié
  plutôt que de la laisser traîner.
- **Après un `git pull` sur la machine de travail** : relire `git status` avant de relancer une
  session — les fichiers de runtime (`.env`, `config.yaml`) ne sont pas dans le dépôt, donc un
  `checkout` ne les touche pas ; en revanche `skills/` et `scripts/` le sont.
- **Ne pas commiter** : `hermes-agent/` (dépôt upstream imbriqué), `data/`, `logs/`, `cache/`,
  `state.db*`, les `.env` réels, `auth.json`, `pastes/`, `mcp-tokens/`.
