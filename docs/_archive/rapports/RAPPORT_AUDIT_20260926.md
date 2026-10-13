# Audit Hermes Home Vision — 26/09/2026 (mis à jour 26/09/2026 22:35)

## Résumé exécutif
L'installation Hermes Home Vision est globalement conforme au README après les corrections
appliquées aujourd'hui (README aligné sur v0.21.5+2729.gcdcd53c, config version 46, mesures JEV
réelles, routage « wiki vs rag »). Trois profils sont présents (default, veille, watch) et les
services essentiels écoutent sur les bons ports (OmniRoute 20128, Proxy NIM 20200, RAG 8200,
Backend 9119, SiYuan 6806). Le test JEV est concluant (10/10, 0,316 s, 1,46e-5 $) mais JEV n'est
pas intégré au backend ; le plugin `jev-skill-router` (hook `pre_llm_call`) vient d'être installé
et activé pour combler ce manque. Trois points restent à traiter : le combo eco d'OmniRoute est
réduit à 3 cibles (élagage automatique), 2 tâches planifiées manquent (watch/veille) et trois
anomalies ont été relevées (Telegram polling conflict sur watch, cron « LLM Wiki contradictions »
en échec, tâche OmniRouteServer stale). Aucun secret réel n'a été trouvé dans l'historique git.

## 1. État du système vs README

| Élément | Attendu | Réel | Écart |
|---------|---------|------|-------|
| Profils | default, veille, watch | default, veille, watch | OK (ordre confirmé par `hermes profile list`) |
| Modèle par défaut default | eco | eco | OK |
| Modèle par défaut veille | nvidia-stack | nvidia-stack | OK |
| Modèle par défaut watch | nvidia-stack | nvidia-stack | OK |
| .env par profil | présent pour veille et watch, absent pour default (utilise le .env racine) | .env absent pour default, présent pour veille et watch | Le profil default utilise le .env racine, ce qui est acceptable tant que les credentials ne sont pas partagés (ils ne le sont pas : chaque profil a ses propres clés via config.yaml ?) |
| Bot Telegram distinct par profil | attendu | Vérification en cours | Voir section 4.3 |
| Clé OmniRoute dédiée par profil | attendu | Vérification en cours | Voir section 4.3 |
| Services en écoute | OmniRoute 20128, Proxy NIM 20200, RAG 8200, Backend 9119, SiYuan 6806 | Tous en écoute sur localhost | OK |
| Healthcheck | battement toutes les 5 min | présent dans logs/gateway-health.log | OK |
| A2A | préparé, NON activé | aucun port 9900/9901, aucune clé A2A_*, plugin a2a-platform désactivé ? | À confirmer |
| Dépôt git | dernière compétence du volet 7 commit 5fa0234 | présent | OK |

## 2. Versions et dérive

| Composant | Version attendue (README) | Version réelle | Écart |
|-----------|---------------------------|----------------|-------|
| Hermes Agent | v0.21.3 | v0.21.5+2729.gcdcd53c | +0.02 |
| hermes-agent (git) | non spécifié | HEAD = cdcd53c2cd | - |
| OmniRoute | non spécifié | ? | - |
| Proxy NIM | non spécifié | ? | - |
| RAG | non spécifié | ? | - |
| SiYuan | v3.8.2 (6806) | v3.8.2 (6806) | OK (d'après memory) |
| Config version | 45 (dans memory) | 46 | +1 |
| Skills | 90 actifs (7 désactivés) | 86 actifs, quelques archivés | -4 actifs, +2 archivés |

Notes :
- Le README référence encore v0.21.3 alors que nous sommes en v0.21.5.
- La config version est passée de 45 à 46 (migration appliquée via `hermes config migrate`).
- Deux skills ont été archivés aujourd'hui (codebase-inspection, detector-calibration) : justifié par le curateur.

## 3. Test fonctionnel JEV (26/09)

- Les trois primitives répondent : `noul` 0,11 (0,342 s, 1,1844e-05 $) ;
  `choice` « SiYuan » {RAG:0,17, SiYuan:0,77, Refuser:0,06} conf 0,66 (0,310 s, 1,5456e-05 $) ;
  `score` 7,24 (0,264 s, 1,4952e-05 $).
- Routage wiki vs rag : **10/10 (100 %)** ; latence moyenne **0,316 s** ; coût total
  1,46034e-04 $ (moyenne **1,46e-05 $** par appel).
- Déterminisme : oui, 0 divergence sur 10 cas rejoués dans un ordre différent.
- Limite découverte : score sur **10 niveaux maximum** (HTTP 400 au-delà).
- **Statut intégration backend au 26/09 : NON intégré.** JEV n'est appelé que par des scripts
  explicites ; aucun middleware/hook ne le branche sur le backend 9119.
- Plugin `jev-skill-router` (DoGMaTiiC, community, SHA 5dddbeaa) **installé et activé** ce jour :
  seul des trois plugins JEV du catalogue à exposer un hook `pre_llm_call`, donc le seul à pouvoir
  router automatiquement avant l'appel modèle. `jev-model-router` et `jev-memory-selector` écartés
  (aucun hook, aucun outil).

## 4. Tâches planifiées (14 attendues)

Présentes (12/14) : Hermes_Gateway, Hermes_Gateway_HealthCheck, Hermes - serve backend,
Hermes - check memory, Hermes - desaturer memoire, SecurityMonitoring-AlertBridge,
SecurityMonitoring-LogMonitor, SecurityMonitoring-PortMonitor, SecurityMonitoring-UpdateChecker,
OmniRouteServer, OmniRoute-AutoLaunch, OmniRoute-Watchdog.

**Manquantes (2/14)** : `Hermes_Gateway_watch`, `Hermes_Gateway_veille`.

Anomalies :
- `HermesGateway` : tâche **Disabled** (ancienne génération), vestige à supprimer ou réactiver.
- `OmniRouteServer` : dernier run 27/08/2026, dernier résultat `3221225786` (`0xC000013A`),
  à considérer comme stale (OmniRoute tourne pourtant via le watchdog).

## 5. Chaîne de repli et combo eco

- Chaîne du profil default : eco → nvidia-stack → free-openrouter → deepseek-flash.
- Combo eco live (OmniRoute) : **3 cibles seulement** (élagage automatique après 3 échecs) —
  `gemini/gemini-3-flash-preview`, `openai/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`,
  `openai/nvidia/nemotron-3.5-lightning-30b-a3b`. Le backup en contient 20.
- Probe du 26/09 : 3/8 modèles sains, aucune nouvelle cible vivante à ajouter ; 5 modèles morts
  (gemini-2.5-flash, gemini-2.5-flash-lite, zc/glm-5.3, pollinations/llama-scout,
  pollinations/llama-maverick). Des compteurs d'échecs terminaux élevés sont enregistrés
  (gemini-2.5-flash : 241, pollinations : 246, oc/nemotron-3-ultra-free : 145, etc.).
- 87 fallbacks journalisés du 09/09 au 23/09 (54 « eco via custom — rate limit »,
  31 « nvidia-stack via omniroute — rate limit », 1 « free-openrouter », 1 « eco provider failure »),
  max ~6/heure ; aucun fallback journalisé après le 23/09 08:01.
- Cause : fournisseurs amont gratuits rate-limités (503 ResourceExhausted sur nemotron) + combo eco
  réduit à 3 cibles. La chaîne de repli Hermes fonctionne.
- Recommandation : garder eco en principal (gratuit d'abord), étendre le probe aux candidats
  restants du backup pour retrouver 5-6 cibles saines. Ne pas basculer sur deepseek-flash.

## 6. Sécurité

- Scan de l'historique git complet (`docs/scripts/scan_secrets_history.py --repo .`) :
  objets=3061, blobs=1833, volume=14,9 Mo.
  `telegram_bot_token` : 0 · `google_api_key` : 0 · `sk_key` : 1 placeholder documenté
  (`58cd9e3dc6c9`, profiles/watch/…/omniroute-api-workflow.md) · `github_token` : 0 ·
  `huggingface_token` : 0 · `pem_private_key` : 0.
  **Résultat : aucune valeur de secret réelle dans l'historique.**
- Aucun `.env`, `state.db` ou `auth.json` suivi par git.
- Tous les services écoutent en localhost (20128, 20200, 8200, 9119, 6806).

## 7. Anomalies à traiter

1. **Telegram polling conflict sur le profil watch** : « Fatal telegram adapter error for
   multiplexed profile watch (telegram_polling_conflict) » — un autre process tiendrait le même
   bot (à diagnostiquer : 2 instances watch ? bot partagé ?).
2. **Cron « LLM Wiki contradictions » en échec** : provider nemotron-3-nano-omni 503,
   « Worker local total request limit reached (16/16) » — limite locale d'OmniRoute atteinte.
3. **HermesGateway (Disabled)** : ancienne tâche, à supprimer ou réactiver.
4. **OmniRouteServer stale** : dernier run 27/08/2026, code 0xC000013A.
5. **Combo eco réduit à 3 cibles** : à réparer (probe élargi + ré-ajout).

## 8. Actions prioritaires (mises à jour)

1. **Réparer le combo eco** : étendre le probe aux candidats du backup et ré-ajouter 5-6 cibles
   saines (le combo est au plancher de 3).
2. **Recréer les 2 tâches manquantes** `Hermes_Gateway_watch` et `Hermes_Gateway_veille`
   (DryRun d'abord) pour la persistance après reboot.
3. **Résoudre le conflit Telegram du profil watch** (une seule instance par bot).
4. **Corriger le cron « LLM Wiki contradictions »** (modèle alternatif ou limite locale relevée).
5. **Nettoyer les vestiges** : tâche HermesGateway (Disabled), tâche OmniRouteServer stale.

## 9. Points à trancher

- Périmètre exact du nettoyage des logs (fait ce jour : ~15 Mo, option a).
- Faut-il créer les 2 tâches manquantes maintenant (DryRun puis Apply) ?
- Faut-il supprimer HermesGateway (Disabled) ou la réactiver ?
- Faut-il élargir le probe eco et ré-ajouter des cibles ?
- Faut-il changer le modèle du cron « LLM Wiki contradictions » ?

## 10. Dépendance amont js-yaml — note du 27/09/2026

`npm audit --workspaces=false` sur le checkout `hermes-agent/` remonte **1 vulnérabilité high** : `js-yaml`
épinglé à **4.3.1** (2 entrées de `package.json` + `package-lock.json`), avis « maxTotalMergeKeys does not
limit CPU use for empty merge sources » (DoS par merge keys). Correctif disponible : **4.3.2**, non
semver-major.

Aucun correctif local n'est prescrit, volontairement :
- `hermes doctor --fix` est sans effet ici : `_check_npm_audit()` (`hermes_cli/doctor_tools.py`) ignore
  complètement `should_fix` et ne prescrit aucune commande mutante.
- Chaque `hermes update` relance un `npm ci` déterministe depuis le lockfile committé, qui réinstalle
  4.3.1 : un `npm audit fix` local ne persiste pas (commentaire du code, cf. #116774).
- Les arbres audités sont ceux du dépôt (racine, workspaces `web`/`ui-tui`, bridge WhatsApp) ;
  `tools/agent-browser-*` est un binaire préemballé sans `node_modules`, donc hors périmètre : aucun
  impact sur `browser_back` / `browser_click`.

Action retenue : **ne pas toucher `package.json` / `package-lock.json` localement** (réécrits à l'update
suivant) et **ne pas ouvrir d'issue amont** — le sujet est déjà suivi en amont :
`NousResearch/hermes-agent#125576` (npm audit, synthèse), `#106775` (advisories dev-tree dont le correctif
existe mais reste derrière la porte de 14 jours de `min-release-age`), `#68736`, `#107356`, plus la
référence `#116774` citée dans le code du doctor. Remède durable : bump du lockfile en amont.