# Changelog — Version 1.2

Toutes les modifications notables de ce dépôt sont consignées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) — convention de version : **SemVer** (`MAJEUR.MINEUR`).

- `1.1` — état figé de `main` au 17/09/2026, conservé intact (tag `v1.1-original`).
- `1.2` — mise en version et documentation du dépôt (branche `v1.2-ameliorations`).

---

## [1.2] — 2026-09-21

Version documentaire : **aucune modification de comportement du runtime**. `config.yaml`,
`cron/jobs.json`, `skills/`, `scripts/`, `profiles/` et `gateway-service/` sont identiques à la 1.1.

### Ajouté

- `docs/IMPROVEMENTS.md` — fiche détaillée des améliorations 1.1 → 1.2, avec pour chaque point
  l'état **réel** de la 1.1, l'état de la 1.2, le bénéfice et les fichiers concernés.
- `docs/CHANGELOG-v1.2.md` — ce changelog, séparé de la fiche d'améliorations.
- **Wiki GitHub de 8 pages** : `Home`, `Version-1.1`, `Version-1.2`, `Installation-1.2`,
  `Ameliorations-detaillees`, `Migration-depuis-1.1`, `Archives-1.1`, `FAQ`.
- Section **« Choisir sa version »** en tête du `README.md` : tableau comparatif 1.1 / 1.2 avec
  branche, tag et documentation de chaque version.
- Section **« Voir aussi »** dans le `README.md` : renvois vers la fiche d'améliorations, le
  changelog et le Wiki.
- Bandeau de version en tête du `README.md` : version actuelle (`1.2`) et lien vers la 1.1.

### Modifié

- `README.md` — bandeau de version, section « Choisir sa version », section « Voir aussi » ;
  §8 « Sécurité » complété du résultat de l'audit du 21/09/2026 ; §9 « Documentation » complété des
  deux nouveaux documents. **Le contenu technique existant n'est pas réécrit.**
- `README.md` (mention de visibilité) — le texte annonçait « Dépôt privé » alors que le dépôt est
  **public** (vérifié : `gh repo view --json visibility` → `PUBLIC`). Formulation corrigée.

### Corrigé

- Ambiguïté sur la « version » du dépôt : le README citait la version d'Hermes Agent (`v0.21.3`)
  sans qu'aucune version du dépôt n'existe. Le dépôt a désormais ses propres `1.1` et `1.2`.
- Contrôle de sécurité jamais rejoué depuis le passage du dépôt en public : l'audit
  `docs/scripts/scan_secrets_history.py` a été exécuté sur **tout l'historique** le 21/09/2026.
  Résultat : `telegram_bot_token: 0`, `google_api_key: 0`, `github_token: 0`,
  `huggingface_token: 0`, `pem_private_key: 0`, et **1 blob `sk_*` classé placeholder**
  (16 caractères, exemple pédagogique dans une référence de skill). Aucun `.env`, `state.db` ou
  `auth.json` suivi par git.

### Supprimé

- Rien. Aucun fichier de la 1.1 n'est supprimé, déplacé ou réécrit.

### Notes de migration

- Depuis la 1.1 : **aucune action obligatoire**. La 1.2 étant identique au runtime près, il suffit
  de basculer de branche. Procédure, sauvegarde et rollback :
  [`Migration-depuis-1.1`](../../wiki/Migration-depuis-1.1).
- Retour arrière : `git checkout v1.1-original`.

### Archives

- Version 1.1 conservée intacte : branche `main` (commit `1f1f089`), tag `v1.1-original`,
  [release 1.1](../../releases/tag/v1.1-original),
  [ZIP](../../archive/refs/tags/v1.1-original.zip).

---

## [1.1] — 2026-09-17

État initial figé, rétro-tagué `v1.1-original` le 21/09/2026. Contenu de référence :

- Runtime Hermes multi-profils (`default`, `watch`, `veille`), Hermes Agent **v0.21.3 (2026.9.14)**,
  upstream `97962358`.
- `README.md` de 293 lignes (9 sections), `docs/` de 164 fichiers (rapports, snapshots, scripts).
- `docs/scripts/bootstrap.ps1` (remise en route, `DryRun` par défaut),
  `docs/scripts/scan_secrets_history.py` (audit d'historique),
  `scripts/check_gateways.ps1` (healthcheck), `scripts/verif_24h.ps1` (rapport T+24 h).
- A2A préparé mais **non activé** ; aucune licence déclarée.
