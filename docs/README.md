# docs — documentation de l'installation Hermes

Ce dossier contient **la documentation, les rapports et les références** de l'installation décrite à
la racine de ce dépôt. Il provient de l'ancien dépôt `hermes_install`, fusionné ici le 17/09/2026
(historique préservé, secret purgé — détail plus bas).

- Ce n'est **pas** un dépôt à cloner seul : la racine est le runtime Hermes, `docs/` est sa
  documentation. Le dépôt `hermes-home-vision` se clone en une fois et restaure l'ensemble.
- L'ordre d'installation est décrit dans le **README à la racine** (`../README.md`) : les trois
  `.env` à créer, les tâches planifiées à recréer, les services à démarrer dans l'ordre, puis les
  vérifications.

## Contenu

| Chemin | Contenu |
|---|---|
| `ARCHITECTURE_HERMES.md` | architecture consolidée : les 3 profils, scripts source de vérité, tâches planifiées, points de fuite connus, dette A2A (11 points), points ouverts, mode observation 24 h |
| `A2A_PREPARATION.md` | procédure complète d'activation A2A (préparée, **non activée**) : checklist, blocs de config, commandes uniques, rollback, points d'attention |
| `architecture_2_agents.md` | décision d'architecture du pair local (bureau ↔ veille) : pourquoi A2A plutôt que `delegate_task`, périmètre du plugin |
| `RAPPORT_*.md`, `INSTALL_LOG.md` | rapports de session et journal d'installation, commande par commande avec les résultats réels |
| `snapshot/` | baselines et copies de référence : `baseline_T0.json`, `config.yaml`, `config.watch.yaml`, `config.veille.yaml`, scripts livrés, diffs, `git_log_*` |
| `scripts/` | `baseline_t0.py` (mesure la référence), `scan_secrets_history.py` (scanne tout l'historique git d'un dépôt), `push-to-github.md` (publication) |

## Notes de fusion

- **Les 10 fichiers `skills/` de l'ancien dépôt de documentation n'ont pas été repris** : c'étaient
  des copies figées de skills vivants (`hermes-memory`, `omniroute-gateway`, `veille-2-agent`,
  `auto-revision-skills`…), en retard sur la version servie par le runtime. Elles restent
  consultables dans l'historique de l'ancien dépôt, dont un backup complet est conservé hors dépôt
  (`Desktop\hermes_install_GIT_BACKUP_20260917_170506_AVANT_PURGE`). Les réintroduire ici
  dupliquerait des skills actifs — ne pas le faire.
- **Trace d'une fuite purgée** : `snapshot/env.pre_update.redacted` est un **placeholder** (aucune
  valeur). L'original contenait un jeton Telegram actif et des clés API ; le blob et les autres
  fichiers sensibles du même dépôt (`snapshot/.env`, `snapshot/state.db`, copies `.env`) ont été
  retirés de **tout l'historique** par `git filter-repo` avant la fusion. Détail en
  `ARCHITECTURE_HERMES.md` §4 et dans le README racine §8.
- Le contrôle est reproductible : `python scripts/scan_secrets_history.py --repo ..`
  (0 occurrence attendue sur les 6 motifs : jeton Telegram, clé Google, `sk-`, `ghp_`, `hf_`, PEM).

## Règle

Rien qui doive rester hors dépôt ne va ici : ce dossier est **versionné**. Les `.env`, les `state.db`
et les sauvegardes de secrets sont exclus par `docs/.gitignore`, mais un fichier de secret ne doit pas
être créé ici « pour plus tard » — il finirait dans un commit.
