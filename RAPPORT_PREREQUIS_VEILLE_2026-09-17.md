# Rapport — Finalisation des prérequis du 2ᵉ agent veille

Date : 2026-09-17 · Machine : OMATHS (Windows 11) · Hermes Agent v0.21.3 (2026.9.14, upstream 97962358)
Objectif de session : finaliser les prérequis du profil `veille`. **A2A reste désactivé.**
Périmètre : préparation uniquement — aucune activation, aucune clé ajoutée, aucun élagage sans validation.

Rapport précédent : `RAPPORT_CHANTIERS_A2A_2026-09-17.md` (4 chantiers livrés).

---

## Phase 0 — Vérification d'entrée (bloquante)

Statut : **OK — les 4 points passent.** Aucun arrêt de procédure.

| Contrôle | Attendu | Mesuré | Verdict |
|---|---|---|---|
| MEMORY.md | ~2076 / 2100 chars | 2076 / 2100 (`check_memory.ps1`) | ✓ |
| USER.md | ~1193 / 1300 chars | 1193 / 1300 (`check_memory.ps1`) | ✓ |
| `hermes doctor` | clean | 0 régression, 4 issues préexistants | ✓ (baseline) |
| Version | 0.21.3 | v0.21.3 · config v45 · `Up to date` | ✓ |
| Port 9900 | muet | aucun listener | ✓ |
| Clés `A2A_*` | 0 | 0 dans `.env`, 0 dans l'environnement du shell | ✓ |

### Détail mémoire

- `MEMORY.md` : 2076 chars, 2120 octets, 6 séparateurs `§`, **7 sections** —
  Environnement / Hermes / Second cerveau / Outils clés / Préférences / Règles transversales / Vidéo.
  Séparateurs et découpage conformes à l'état post-incident. Fin de ligne LF.
- `USER.md` : 1193 chars (lecteur `check_memory.ps1`), 1171 chars en lecture Python universelle,
  1232 octets sur disque. Écart de 22 = 22 fins de ligne CRLF conservées par `Get-Content -Raw`.
  **Écart de mesure, pas un écart de contenu** — à noter pour l'incident du 16/09.
- Deux lecteurs, deux seuils : `check_memory.ps1` alerte à 2100/1300, `config.yaml` limite à
  2200/1375. Les deux sont sous leur seuil respectif. La valeur citée ici est celle de
  `check_memory.ps1` (lecteur autoritaire côté script, cf. skill `hermes-operations`).

### Détail doctor

0 régression. Les 4 issues sont **préexistants** et sans rapport avec la session :

1. Browser tools (agent-browser) — 2 vulnérabilités npm
2. web workspace — 6 vulnérabilités npm
3. WhatsApp bridge — 4 vulnérabilités npm
4. `hermes setup` — clés API manquantes pour l'accès complet aux outils

Attendu et conforme : `⚠ a2a (system dependency not met)` — gate de configuration, pas une
dépendance manquante (A2A volontairement désactivé).

### Baseline de non-régression relevée

- Skills bureau : **98 enabled, 7 disabled** (3 hub-installed, 25 builtin, 77 local) — 105 au total.
- Services : backend 9119 → HTTP 200 ✓ ; RAG 8200 → HTTP 404 sur `/` (serveur vivant) ✓ ;
  SiYuan 6806 → HTTP 401 (auth requise, service vivant) ✓ ; OmniRoute 20128 → HTTP 307 ✓.
- `ESTOP` : absent ✓ (fonctionnement normal).
- Dépôts git : `Desktop/hermes_install` propre ; `hermes-agent` propre (aucun diff = patch annulé,
  pas de patch à moitié appliqué).

### Observations hors périmètre (état trouvé, aucune action prise)

1. **Gateway `default` non démarré.** `hermes gateway status` → `✗ No gateway process detected`.
   Log : arrêt propre le **17/09/2026 à 00:02:07** — `Received UNKNOWN as a planned gateway stop —
   exiting cleanly`, `parent_pid=21884 parent_cmdline='(unknown)'`. `gateway_state.json` est en
   `"gateway_state":"draining"`. C'est le motif documenté « gateway orphelin dont le parent
   (Task Scheduler) est mort ». **Antérieur à cette session** (00:02 vs session ouverte à 12:04) :
   ce n'est pas une régression, mais le bot Telegram du profil `default` est muet depuis.
   Le gateway `watch` tourne (PID 22876, démarré 16/09 19:19:13).
2. **Deux tâches gateway pour le profil par défaut** : `Hermes_Gateway` (schtasks, état Ready,
   dernier run 16/09 19:18:35) et `HermesGateway` (sans underscore, `Hidden`, déclenche
   `pwsh -NoProfile -Command "hermes gateway start"` au logon, dernier run 13/09 16:23:32).
   `HermesGateway` ressemble à un vestige supersédé. À traiter ou non — décision opérateur.
3. **9 tâches planifiées `Hermes*`** recensées : check memory, désaturer memoire, Reindex RAG,
   serve backend, Hermes-PurgeReports, HermesGateway, Hermes_Gateway, Hermes_Gateway_watch,
   Hermes_NVIDIA_NIM_Proxy.
4. **`Hermes-PurgeReports`** : `LastTaskResult=1` (échec) le 17/09 à 02:00 — sans rapport avec
   la session, à examiner séparément.
5. Profil `veille` : créé, isolé, **gateway arrêté**, `.env` présent mais **vide de toute clé**
   (en-tête de commentaires uniquement). `config.yaml` : `default: eco`, `provider: omniroute`,
   `base_url: http://127.0.0.1:20128/v1`, `plugins.enabled: []`. `SOUL.md` = 667 octets (défaut).

---

## Phase 1 — Proxy NVIDIA NIM (diagnostic réalisé, décision en attente)

### Verdict : ENCORE UTILE — mais hors du chemin par défaut, et actuellement mort.

Le proxy n'est pas un vestige : il est référencé par une connexion OmniRoute **active** et par un
combo dédié. Il est en revanche **hors du chemin par défaut** (le modèle Hermes `eco` ne l'utilise
pas) et **en panne silencieuse** depuis le 13/09.

### Ce qui consomme le port 20200 — un seul consommateur, identifié

| Élément | Constat |
|---|---|
| Connexion provider OmniRoute `NVIDIA NIM (Proxy)` | `id=1910f7a8-8037-4e0a-9024-674fde7df9b7`, `provider=openai`, `auth_type=apikey`, **`is_active=1`**, `test_status=active` |
| URL déclarée | `provider_specific_data.baseUrl = http://127.0.0.1:20200/v1` |
| Dernier test OmniRoute | `last_tested = 2026-09-17T08:51:42Z`, `updated_at = 2026-09-17T08:52:41Z` |
| Combo dépendant | `nvidia-stack` — 3 modèles, tous `providerId: "openai"` (donc via le proxy) |
| Modèles du combo | `nvidia/nemotron-3.5-lightning-30b-a3b`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` |
| Autres références | **aucune** — pas dans `config.yaml`, pas dans `.env` (hors `NVIDIA_API_KEY_GEMMA4`, lu *par* le proxy), aucune occurrence dans `scripts/`, aucune autre tâche planifiée |
| Combo `eco` (défaut Hermes) | 0 modèle nvidia → le défaut ne dépend pas du proxy |

### Preuve de panne : 272 appels échoués, encore hier soir

`ECONNREFUSED 127.0.0.1:20200` enregistré dans `proxy_logs` (200) et `call_logs` (72).

| Jour | Échecs |
|---|---|
| 2026-09-16 | 45 (dont 20:59:51Z = 22:59 heure locale, **après** le redémarrage d'OmniRoute de 22:09) |
| 2026-09-12 | 7 |
| 2026-09-10 | 20 |
| 2026-09-09 | 5 |
| 2026-09-08 | 19 |
| 2026-09-07 | 85 |
| 2026-09-03 | 18 |
| 2026-09-02 | 1 |

Aucun échec le 17/09 : le combo `nvidia-stack` n'a simplement pas été sollicité depuis.

### État exact de la tâche planifiée

| Champ | Valeur |
|---|---|
| Nom | `Hermes_NVIDIA_NIM_Proxy` |
| État / Enabled | `Ready` / **`Enabled: True`** |
| Déclencheur | `MSFT_TaskLogonTrigger` — **au logon uniquement**, `StartBoundary 2026-09-08T19:11:00` |
| Action | `wscript.exe "…\data\nvidia\nvidia-nim-launch.vbs"` |
| LastRunTime | **13/09/2026 16:23:29** |
| LastTaskResult | `0` |
| NextRunTime | **vide** |
| NumberOfMissedRuns | 0 |
| LogonType | `InteractiveToken`, `DisallowStartIfOnBatteries: true` |

Dernier logon machine : **13/09/2026 16:23:29** (Event 7001) — la tâche a donc bien tiré à ce logon
et rien depuis, faute de nouvelle session. Elle n'a **aucune répétition ni redémarrage sur échec** :
une fois le process mort, il ne revient qu'au prochain logon.

Le lanceur `nvidia-nim-launch.vbs` est idempotent (si 20200 écoute déjà, il sort) et démarre le proxy
détaché, fenêtre masquée (`0, False`).

### État du proxy lui-même

- Port 20200 : **aucun listener**. `curl http://127.0.0.1:20200/health` → échec de connexion.
- **Aucun fichier de log** dans `data/nvidia/` : le proxy écrit sur stdout, la fenêtre est masquée →
  la sortie est perdue. C'est ce qui rend la panne invisible.
- Clé : `NVIDIA_API_KEY` n'est posée ni au niveau utilisateur ni machine ; le script retombe sur
  `data/nvidia/.env` → `NVIDIA_API_KEY_GEMMA4` (présente). Le lancement est donc fonctionnel une
  fois relancé.
- Rôle du proxy : traduire les noms de modèles préfixés `openai/` envoyés par OmniRoute vers le
  format NVIDIA NIM et relayer vers `https://integrate.api.nvidia.com/v1`.

### Ce qui est cassé concrètement

Toute utilisation du combo `nvidia-stack` échoue immédiatement (connexion refusée), sans message
visible côté Hermes puisque l'échec est consommé par OmniRoute. Le coût est réel : 3 modèles
NVIDIA (dont Nemotron 3 Super 120B et Lightning 30B) sont annoncés dans le catalogue OmniRoute
mais inutilisables.

### Options soumises à décision

| # | Option | Contenu | Effet |
|---|---|---|---|
| A | **Relancer et durcir** | Redémarrer le proxy maintenant + corriger la tâche : ajouter `-StartWhenAvailable` et une répétition (ex. toutes les 15 min avec `-MultipleInstances IgnoreNew`), rediriger la sortie du proxy vers un log | Le combo `nvidia-stack` redevient utilisable ; l'état du proxy devient observable |
| B | **Retirer proprement** | Désactiver la tâche (désactivation explicite, pas de suppression) + désactiver la connexion provider `NVIDIA NIM (Proxy)` et le combo `nvidia-stack` côté OmniRoute | Plus d'appels condamnés ; les 3 modèles NVIDIA disparaissent du catalogue utilisable |
| C | **Statut quo documenté** | Ne rien changer, acter que le combo est HS et que la tâche ne tire qu'au logon | Zéro modification, mais la panne silencieuse demeure |

Aucune action n'a été effectuée : lecture seule. Décision opérateur requise.


## Phase 2 — Cohérence Hermes_Gateway_watch

*(en attente)*

## Phase 3 — Configuration du profil veille

*(en attente)*

## Phase 4 — Décision A2A

*(en attente)*
