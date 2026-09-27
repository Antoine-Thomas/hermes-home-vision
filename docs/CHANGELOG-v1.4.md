# Changelog — Version 1.4 « Hermes Aegis »

> **Statut : préparée, NON publiée.** Aucun tag, aucune release, aucun `git tag v1.4`. La version
> stable reste la **1.3 « Hermes Psychopomp »**. Deux bloqueurs interdisent la publication (voir la
> dernière section).
> Toutes les valeurs ci-dessous sont **mesurées le 27/09/2026** sur la machine d'origine
> (`%LOCALAPPDATA%\hermes`, Windows 11 natif), avec Hermes Agent **v0.21.5+3779.g8f897d2**,
> config version **46**.

Thème de la 1.4 : **Aegis**, la sécurité devient une couche d'architecture à part entière. Le détail
des 4 couches, leurs limites et leurs vérifications est dans
[`ARCHITECTURE_AEGIS.md`](ARCHITECTURE_AEGIS.md).

---

## Sécurité (Aegis)

### ACL des secrets

- **`CodexSandboxUsers` retirée des 4 `.env`** (`default`, `watch`, `veille`, `docs-writer`) : ACE
  héritée d'un outil tiers, qui laissait un groupe applicatif lire les secrets. Chaque fichier porte
  désormais exactement **3 ACE non héritées** :
  `Système(F)` · `Administrateurs(F)` · `searc(F)` (mesure : 3 ACE `(F)`, 0 `(I)`, 0 trace
  `CodexSandboxUsers`).
  ```
  icacls "<fichier>.env" /inheritance:r /grant:r "Système:(F)" "Administrateurs:(F)" "%USERNAME%:(F)"
  ```
- **12 sauvegardes `.env` déplacées hors du dépôt** vers `%USERPROFILE%\hermes-secrets-backup\`,
  avec **arborescence miroir par profil** (`default\`, `veille\`, `watch\`, `docs-writer\`) — sans
  elle, les fichiers homonymes s'écrasaient entre eux. Déplacement, **pas suppression** : intégrité
  prouvée par `sha256` identique avant/après, et ACL restreinte appliquée aussi à la destination.
  Un motif `.gitignore` empêche de *publier* un `.env`, pas de le *lire* : ces copies rangées dans
  l'arbre du dépôt restaient une surface (copie de dossier, zip, indexation, sauvegarde).

### Hygiène du dépôt

- **`.gitignore` durci** :
  - `/hermes-agent/` **ancré** — le motif non ancré `hermes-agent/` avalait *aussi* le skill bundled
    `skills/autonomous-ai-agents/hermes-agent/`, qui restait donc hors du dépôt et **absent du point
    de restauration**, silencieusement (le dossier existe sur le disque). Diagnostic :
    `git check-ignore -v <chemin>` + `git ls-files <dossier>` (vide = non suivi).
  - motif **`*.bak_*`** (+ `**/*.bak_*`) — l'ancien motif littéral `.bak_` ne matchait que le
    fichier nommé exactement `.bak_` : un `git add -A` pouvait ré-indexer
    `cron/jobs.json.bak_nemotron_<ts>`.
  - **`profiles/*/skills/`** — exclut les copies de skill par profil (dérive du curateur par
    profil) ; conséquence assumée : aucun skill de profil n'est versionné.
- **4 fichiers `.bak` sortis de l'index** (`git rm --cached`), **conservés sur disque** :
  `cron/jobs.json.bak_nemotron_20260903_174404` et 3
  `profiles/veille/config.yaml.bak_20260917_{124817,125842,131451}`.

## Wazuh

- **Remap du port d'API hôte `55000` → `55085`** (conteneur inchangé, bind localhost) : Windows
  réserve des plages TCP dont **54985-55084**, qui contient 55000 — le manager restait en état
  `Created`, c'est-à-dire une pile *plus dégradée qu'avant*. Contournement : publier juste au-dessus
  de la plage exclue plutôt que de forcer le port réservé.
- **Allowlist alignée** : `data/security-monitoring/config.json` → `wazuh.api_url =
  https://localhost:55085` **et** `55085` ajouté à `ports.allowlist` (avec `9200`). Sans les deux,
  la surveillance signale sa propre correction comme « port ouvert non attendu ». Le dashboard joint
  l'API par le réseau Docker (`https://wazuh.manager:55000`) : non concerné par le remap.
- **`common.py` — contrôle du code retour** : après le `subprocess.run` d'extraction des alertes,
  un `returncode != 0` lève désormais une erreur explicite
  (`RuntimeError("docker exec <conteneur> a echoue (code N) : <stderr>")`) au lieu de laisser passer
  un résultat vide interprété comme « aucune alerte ».
- **`config.json` — chemin du venv corrigé** : `hermes_python` pointe désormais
  `hermes-agent\venv\Scripts\python.exe` (et non plus le venv `hermes-agent\.venv`, retiré lors de la
  migration des venvs).
- Ces trois derniers fichiers vivent sous `data/`, **exclu du dépôt** : correctifs appliqués et
  documentés, mais non committables.

## JEV

- **Note corrigée : JEV est actif.** Vérification en direct le 27/09/2026 via
  `python wiki/scripts/jev_router.py --json "Qu'est-ce que le LLM Wiki ?"` →
  `route = wiki`, `forced = false`, confiance **0,98**, modèle **`typesafe/jev-1.13-20260917`**,
  latence **0,48 s**, coût **3,54e-05 $** (les chiffres antérieurs au catalogue — 0,316 s /
  1,46e-05 $ — sont à re-mesurer : le coût réel est plus élevé). JEV n'est toujours **pas** branché
  automatiquement au backend 9119 : il est appelé par des scripts explicites.
- **Repli local dans le code** (`wiki/scripts/jev_router.py`) : si JEV est injoignable, la route
  renvoyée est
  `{"route": "rag", "forced": true, "forced_reason": "Jev injoignable", "route_source": "fallback_local"}`
  et le **code de sortie reste 2** pour que l'appelant voie la dégradation. Aucun repli vers un
  second moteur ; les deux branches sont couvertes par un test rejouable.

## Laya

Limites mesurées et documentées (skill `laya-onnx-windows`) — Laya tourne en ONNX sur CPU sans
PyTorch (~190-200 ms par décision, coût nul) mais reste un **accélérateur**, pas un substitut :

1. **`noul` en français échoue** : état FR + question FR → 0,0259 (NON) contre 0,8211 (OUI) pour le
   même contenu en anglais. Contournement : `choice` à 2 options neutres, ou tout en anglais.
2. **État > 512 tokens : troncature à droite** — latence ×6 et décisions dégradées (0,42 au lieu de
   0,89). Contournement : résumer l'état sous 512 tokens.
3. **Budget d'options ≈ 48 tokens/option** (`(head_max_len - 16) // k`) — au-delà, distribution
   aplatie. Contournement : 6-7 options courtes maximum.

Accord mesuré JEV ↔ Laya : 6/10 sur le routage RAG/SiYuan (60 %, cible 80 %) → **JEV reste le
décideur principal**.

## Skills

- **98/98 skills actifs** (le parc était retombé à 95) : 3 skills devops perdus lors d'un gel sur
  branche ont été restaurés (`hermes-stack-audit`, `wazuh-agent-lifecycle`,
  `windows-driver-integrity`) ainsi que le skill de récupération d'espace disque (script `delete-targets.py`).
  Régression causée par un `git checkout` : les fichiers non suivis committés sur la branche ont
  disparu de l'arbre en revenant sur `main`.
- **`hermes-agent` versionné** : le skill était totalement invisible de git (motif non ancré, cf.
  Sécurité) — il est désormais suivi, avec son routeur de 37 lignes, ses 28 références et les
  **6 références upstream récupérées** (`desktop-plugins`, `tui-widgets`, `themes`, `petdex`,
  `portal-auth-for-third-party-apps`, et la référence de diagnostic du plafond de concurrence de `delegate_task`). Le routeur pointe
  désormais explicitement vers ces 6 fichiers.

## RAG

- **Source `script_v4` retirée** : le dossier source `Desktop\hermes_tuto_v4` n'existe plus
  (suppression définitive, corbeille vide, aucune copie ailleurs) — la source était devenue un
  **no-op silencieux** (`if not os.path.isdir(...): return []`), donc 714 fragments perdus sans
  aucun avertissement. Retrait de `("script_v4", source_scripts)` de la boucle `construire()` et de
  l'entrée `script_v4` du manifeste `par_source` dans `data/rag/indexer.py` (hors dépôt) ;
  `source_scripts()` reste définie et inerte pour ne casser aucun import. Index courant :
  **2 314 fragments** (`siyuan 483`, `skill 1742`, `wordpress 89`).
- Reste cosmétique : 4 fichiers nomment encore `script_v4` comme valeur de filtre acceptable
  (`serveur_rag.py`, `router_memoire.py`, `audit_rag.py`, `chercher.py`). Aucun effet fonctionnel.

## Dépendances

- **`js-yaml` 4.3.1 (high)** dans le checkout `hermes-agent` : avis « `maxTotalMergeKeys` does not
  limit CPU use for empty merge sources » ; correctif **4.3.2** disponible (non semver-major).
  Aucun correctif local n'est possible **par conception** : `hermes doctor --fix` ignore son
  argument `should_fix` pour ce contrôle, et chaque `hermes update` réinstalle l'état épinglé du
  lockfile via `npm ci` — un `npm audit fix` local ne persiste pas. **Suivi amont** :
  `NousResearch/hermes-agent#125576` (synthèse npm audit), `#106775` (advisories dev-tree dont le
  correctif existe mais reste derrière la porte de 14 jours), `#68736`, `#107356`, et `#116774`
  cité dans le code du doctor. `package.json` / `package-lock.json` volontairement **non modifiés**.
  Sans impact sur les outils navigateur (`agent-browser` est un binaire préemballé, hors audit npm).

---

## Bloqueurs de publication de la v1.4

| # | Bloqueur | État mesuré le 27/09/2026 |
|---|---|---|
| **B1** | **MP4 livrable absent** (ex-« tronqué ») | `Desktop\hermes tuto\tutotete20_jev_llmwiki.mp4` : **introuvable** — dossier supprimé, corbeille vide, aucune copie ailleurs. Le blocage n'est plus « réparer un fichier tronqué » mais **réassembler** un livrable absent (`assemble_v6.py`, CRF 20 preset fast). |
| **B2** | **Watchdog volet6 en pause** | Tâche planifiée Windows `volet6-watchdog` = `Disabled` ; cron job Hermes `4a646bb6eab4` (`every 15m`) = `enabled: false`, `paused_at 2026-09-23T13:10:09+02:00`, `last_status: ok`. |

Tant que B1 et B2 sont ouverts : **pas de tag, pas de release, pas d'annonce de livraison** — la
`README.md` doit continuer à présenter la 1.3 comme version stable et la 1.4 comme *préparée*.

## À faire avant de publier la v1.4

- [ ] Réassembler le MP4 (B1) et valider le livrable par `ffprobe` (durée + streams).
- [ ] Trancher le sort du watchdog `volet6-watchdog` (B2) : réactiver la tâche Windows
      (`schtasks /change /tn "volet6-watchdog" /enable`) et le cron Hermes, ou acter son abandon.
- [ ] Trancher la copie des scripts `data/video_youtube/*.py` dans le dépôt (suivi des correctifs).
- [ ] Rejouer `python docs/scripts/scan_secrets_history.py --repo .` avant tout passage public.
- [ ] Créer le tag `v1.4` et la release **seulement** après les deux bloqueurs.

---

*Le post-mortem détaillé de la production du volet 6 (7 erreurs E1-E7, fichiers touchés,
corrections) reste dans [`CHANGELOG-v1.4-draft.md`](CHANGELOG-v1.4-draft.md) — document de travail,
non publié.*
