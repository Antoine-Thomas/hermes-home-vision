# Hermes — documentation et rapports

Dépôt de **documentation** de l'installation Hermes décrite dans le dépôt principal (le runtime
`%LOCALAPPDATA%\hermes`). Séparé volontairement : les rapports de session, snapshots et procédures
n'ont rien à faire dans le runtime, et inversement le runtime ne doit pas transporter des dizaines de
rapports dans son historique.

Version de référence : **Hermes Agent v0.21.3 (2026.9.14)**, upstream `97962358`.
Aucun secret dans ce dépôt : les valeurs sont remplacées par des empreintes `sha256[:16]` ou des
placeholders. Audit de secrets rejoué le 17/09/2026 : 0 occurrence.

---

## Rôle

| Ce dépôt contient | Ce dépôt ne contient pas |
|---|---|
| l'architecture consolidée, les décisions et les points ouverts | la configuration vivante (`config.yaml`, `.env`) |
| les rapports de session et les procédures de reprise | les bases de sessions (`state.db`) |
| les snapshots de référence (configs, baseline T0) | les skills, scripts du runtime (ils vivent dans le dépôt principal) |
| les scripts d'installation : `bootstrap.ps1`, `restore-from-github.md`, `push-to-github.md` | les gros volumes (`data/`, venvs, modèles) |

---

## Documents clés

| Document | Contenu |
|---|---|
| `ARCHITECTURE_HERMES.md` | architecture des 3 profils, scripts source de vérité, tâches planifiées, points de fuite connus, dette A2A (11 points), points ouverts (§7) et mode observation 24 h (§10) |
| `A2A_PREPARATION.md` | procédure complète d'activation A2A : état mesuré, checklist des 11 points, blocs `a2a_agents`, clés de config, commandes uniques, rollback, points d'attention |
| `architecture_2_agents.md` | décision d'architecture (pair local bureau ↔ veille), why A2A plutôt que `delegate_task`, périmètre du plugin |
| `RAPPORT_PREREQUIS_VEILLE_2026-09-17.md` | rapport de session : mise en place du profil `veille`, prérequis et écarts |
| `RAPPORT_CHANTIERS_A2A_2026-09-17.md` | rapport de session : chantiers A2A (préparation, script, dette) |
| `RAPPORT_INSTALLATION.md`, `INSTALL_LOG.md` | journal d'installation détaillé, commande par commande, avec les résultats réels |
| `snapshot\` | baselines et copies de référence : `baseline_T0.json`, `config.yaml`, `config.watch.yaml`, `config.veille.yaml`, scripts livrés, diffs des scripts modifiés, `git_log_*` |
| `profil_veille.md`, `ARBITRAGE_SKILLS_*.md`, `historique_qualite.md` | documents de travail du parc |
| `scripts\` | `baseline_t0.py` (mesure la baseline), `bootstrap.ps1` (restaure une machine vierge), `restore-from-github.md`, `push-to-github.md` |

---

## Comment utiliser ce dépôt

**Ce n'est pas un dépôt à cloner sur une nouvelle machine pour réinstaller Hermes.** C'est la
documentation de l'installation existante.

Pour réinstaller ailleurs :

```powershell
cd $env:TEMP
git clone https://github.com/<ton-user>/hermes-install.git
cd hermes-install
.\scripts\bootstrap.ps1 -RepoUrl https://github.com/<ton-user>/hermes-home.git
```

Le bootstrap installe Hermes, pose la configuration du dépôt principal, crée les `.env` vides,
recrée les tâches planifiées, démarre les services et dit précisément ce qui reste à faire à la main
(bots Telegram, clé OmniRoute, jeton SiYuan, bot). Détail pas-à-pas :
`scripts\restore-from-github.md`. Publication des dépôts : `scripts\push-to-github.md`.

### Ordre d'installation recommandé

1. `iex (irm https://hermes-agent.nousresearch.com/install.ps1)` — crée `%LOCALAPPDATA%\hermes`.
2. Poser la configuration du dépôt principal (`git init` + `fetch` + `checkout`, jamais `git clone`
   dans un dossier non vide).
3. Créer les `.env` depuis les `.env.example`, puis les remplir.
4. Recréer les tâches planifiées et démarrer les services (`bootstrap.ps1`).
5. Vérifier (`verif_24h.ps1`, `hermes profile list`, `hermes doctor`).

### Règle de sécurité

Un dépôt **privé** n'est pas un coffre : ce qui y entre reste dans l'historique même après
suppression. Avant tout passage en public, purger l'historique (`git filter-repo`, commande en
`ARCHITECTURE_HERMES.md` §8) **et** considérer tout secret déjà poussé comme compromis — donc le
révoquer.
