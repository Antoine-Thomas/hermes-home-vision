# Architecture Hermes — état consolidé

Date : 2026-09-17 · Hermes Agent v0.21.3 (2026.9.14), upstream `97962358` · install git :
`%LOCALAPPDATA%\hermes\hermes-agent` (propre) · A2A **non activé**.
Aucun secret en clair dans ce document : seules des empreintes `sha256[:16]` et des longueurs sont citées.

---

## 1. Les trois profils

| | `default` (bureau) | `watch` | `veille` |
|---|---|---|---|
| Rôle | opérateur : code, vidéo, WordPress, second cerveau | second profil historique (surveillances et automatisations), porte une copie complète des skills | veille techno : arXiv, HuggingFace, RSS/Atom, catalogue et prix OpenRouter → synthèse datée |
| Modèle par défaut | `eco` (provider `omniroute`) | `eco` (provider `omniroute`) | `nvidia-stack` (provider `omniroute`) — déterministe, local, gratuit |
| Chaîne de repli | `omniroute/nvidia-stack` → `deepseek/deepseek-flash` | `deepseek/deepseek-flash` **seul** ⚠ | `omniroute/auto/best-free` → `omniroute/auto/best-reasoning` |
| Skills (`SKILL.md` sur disque) | 107 (99 activées, 7 désactivées en config) | 124 (0 désactivée en config) | 61 (50 désactivées en config) |
| Bot Telegram | `8802352038` — sha256[:16] `7da363461151846e` | `8967117033` — sha256[:16] `8b0472877252f691` | `8801969330` — `@Hermesveille1_veille_bot`, sha256[:16] `eaa8b0ce89859d68` |
| Clé OmniRoute | clé du poste, 32 car., sha256[:16] `6ebeaffc871daef9` : sert **aussi** de jeton d'administration (`Bearer` sur `/api/keys`) | la même clé que `default` (partagée) | clé dédiée `hermes_veille`, 35 car., sha256[:16] `0c79be7af82b3421`, **7 modèles autorisés** (`modelAccessMode: restricted`) |
| Gateway | tâche `\Hermes_Gateway`, PID courant publié dans `gateway_state.json` | tâche `\Hermes_Gateway_watch` | tâche `\Hermes_Gateway_veille` |

Tronc commun vérifié le 17/09 : `TELEGRAM_ALLOWED_USERS` = `TELEGRAM_HOME_CHANNEL` = `8956868107` pour
les trois profils ; le jeton SiYuan du workspace (`sha256[:16] f796af0fe004c134`, 24 car.) est présent
dans `default/.env` **et** `profiles/veille/.env` **et** `SiYuan/hermes-projects/conf/conf.json`.

Installations partagées, appelées par les trois profils : OmniRoute `127.0.0.1:20128` (routeur LLM),
proxy NIM local `127.0.0.1:20200`, SiYuan `127.0.0.1:6806`, RAG `127.0.0.1:8200`, backend `127.0.0.1:9119`.

---

## 2. Scripts source de vérité

| Chemin | Rôle | Idempotence |
|---|---|---|
| `data\rag\indexer.py` | indexation RAG (tâche planifiée 03 h) | reprise sur index existant |
| `data\rag\chercher.py`, `router_memoire.py`, `audit_rag.py` | recherche, routage hiérarchique, audit qualité de l'index | lecture seule |
| `data\rag\scan_secrets.py` | scanner de secrets — **scan uniquement, pas de mode export/redaction** | lecture seule |
| `data\rag\serveur_rag.py` | service HTTP RAG (port 8200) | service |
| `data\rag\appliquer_fraicheur.py`, `archiver_memoire.py`, `reindex_auto.py`, `pub_carte_memoire.py` | fraîcheur, archivage, ré-indexation, carte mémoire | écriture ciblée |
| `scripts\probe_omniroute.py` | sonde les modèles gratuits et maintient le combo `eco` (job cron horaire `5c9dd16aaa37`) | **additif par conception** : n'ajoute que, ne retire jamais |
| `data\omniroute\restore_eco_20260912.py` | réparation de `eco` (backup + `PUT` de 10 modèles vérifiés) | backup avant écriture |
| `data\omniroute\reorder_eco.py`, `fix_eco_combo.py`, `fix_model_default.py` | réordonnancement / réparation de combos et de modèle par défaut | backbone-up avant écriture |
| `data\nvidia\nvidia-nim-proxy.py` | proxy NIM local (20200) : normalise les noms de modèles, retire les params rejetés | service |
| `omniroute-launch.vbs` / `.cmd` | lancement silencieux d'OmniRoute, garde `LISTENING` (jamais `TIME_WAIT`) | no-op si le port écoute déjà |
| `scripts\check_memory.ps1` | contrôle de saturation mémoire (tâche 08 h) | lecture seule |
| `scripts\desaturer_memoire.py` | désaturation hebdomadaire (tâche dimanche 04 h) | écriture contrôlée |
| `scripts\check_gateways.ps1`, `audit_tasks.ps1`, `fix_monitoring.ps1` | santé des gateways, audit des tâches, veilleurs | lecture seule |
| `scripts\activer_a2a.ps1` / `desactiver_a2a.ps1` | activation / retour arrière A2A en 8 étapes | `-SelfTest` valide add/remove (md5 identique) sans rien toucher |
| `scripts\hidden_SecurityMonitoring-*.vbs` | 4 veilleurs (alertes, log, ports, mises à jour) | service |
| `Desktop\hermes_install\historique_qualite.py`, `rollback_update.ps1` | historique qualité, retour arrière de mise à jour | — |

---

## 3. Tâches planifiées Windows

| Tâche | Déclenchement | Rôle |
|---|---|---|
| `\Hermes - Reindex RAG` | quotidien 03 h 00 | ré-indexation du second cerveau |
| `\Hermes - check memory` | quotidien 08 h 00 | contrôle de saturation mémoire |
| `\Hermes - desaturer memoire` | dimanche 04 h 00 | désaturation mémoire |
| `\Hermes - serve backend` | au démarrage | backend 9119 |
| `\Hermes-PurgeReports` | quotidien 02 h 00 | purge des rapports |
| `\Hermes_Gateway` | récurrent (watchdog) | gateway du profil `default` |
| `\Hermes_Gateway_watch` | récurrent (watchdog) | gateway du profil `watch` |
| `\Hermes_Gateway_veille` | récurrent (watchdog) | gateway du profil `veille` |
| `\Hermes_Gateway_HealthCheck` | récurrent | healthcheck des gateways |
| `\Hermes_NVIDIA_NIM_Proxy` | récurrent | proxy NIM 20200 |
| `\OmniRouteServer`, `\OmniRoute-AutoLaunch`, `\OmniRoute-Watchdog` | démarrage + watchdog 5 min | serveur OmniRoute et sa relance |
| `\HermesGateway` | — | **désactivé** : vestige d'avant le renommage des tâches |

---

## 4. Points de fuite connus (fichiers non chiffrés, hors dépôt git)

| Point | Nature | État |
|---|---|---|
| `%LOCALAPPDATA%\hermes\auth.json` | jetons de plateformes et OAuth, **unique pour l'install** (pas de `auth.json` par profil) | exclu du dépôt ; à considérer comme partagé entre profils |
| `profiles\watch\.env` | contient **deux** jetons Telegram (`8967117033` et celui du bureau) → `hermes profile list` avertit « credential partagé », et la migration multiplex refuse | à trancher : bot propre pour `watch` ou retrait du doublon |
| `Desktop\hermes_install\snapshot\.env` et `env.pre_update` | **copies complètes du `.env` du bureau en clair** (avant les rotations du 17/09) : les jetons Telegram/SiYuan/OmniRoute y sont morts, mais DeepSeek/OpenRouter/Kimi/NVIDIA/EMAIL y sont vivants | hors dépôt Hermes, non chiffré → à nettoyer ou déplacer sur un support protégé |
| `cache\terminal\hermes-snap-*.sh` | snapshots du shell : le sandbox y déverse l'environnement du profil (`declare -x SIYUAN_TOKEN=…`) | renouvelé à chaque commande → toute passe de nettoyage doit inclure ce dossier |
| `.hermes_history` | historique de saisie : un secret **collé** dans le chat y atterrit en clair, dans un fichier de blocs `# horodatage` + `+texte` | nettoyé aujourd'hui ; reste un point d'entrée à surveiller après chaque collage |
| `state.db` (+ index FTS `messages_fts`, `messages_fts_trigram`) | conserve messages et **sorties d'outils** : un dump de config y recrée la fuite | nettoyé aujourd'hui (`UPDATE` + `rebuild`), même vigilance |
| `mcp-tokens\scite*.json`, `google_token.json`, `google_client_secret.json`, `whatsapp\session\` (1954 fichiers) | identifiants tiers en clair | **exclus du dépôt git**, pas chiffrés |
| Jeton SiYuan | un seul jeton par workspace (`type API struct{ Token string }`), donc partagé `default` + `veille` + `conf.json` par construction | rotation = un seul endroit à changer (Réglages → À propos) puis répercuter les deux `.env` |

---

## 5. Dette A2A — 11 points (aucune action)

1. **A2A reste OFF** : plugin `a2a-platform` non activé, `platforms.a2a.enabled` non posé, aucune clé `A2A_*`, port 9900 muet (0 listener), `a2a_agents` non déclaré.
2. **Aucun pair joignable** : activer A2A sans second agent en service A2A ouvrirait un port d'écoute sans bénéfice.
3. **`scripts\activer_a2a.ps1` n'accepte pas `-Port` ni `-Profile`** : l'activation ne peut cibler ni un autre port que 9900, ni un autre profil que celui par défaut du contexte. À ajouter avant toute activation réelle.
4. `A2A_BEARER_TOKEN` (partagé, identité retombant sur l'IP) vs `A2A_PEER_TOKENS="pair:jeton"` (un jeton par pair) : **non posés** ; le second est préférable.
5. **Passage distant non préparé** : le bind reste `127.0.0.1` sans jeton, et il faut `A2A_HOST` **et** un jeton pour élargir — l'activation ne le fait jamais d'elle-même.
6. **Pas de détection de cycle** dans les délégations ; `delegation.max_spawn_depth = 1` est le seul garde-fou anti-récursion (`tools/delegate_tool.py`).
7. **Piège de lecture de config** : `grep a2a config.yaml` remonte `- a2a` sous `known_plugin_toolsets.cli` (toolsets *connus*), pas sous `platform_toolsets.cli` (liste *active*) — un grep naïf conclut à tort que c'est activé.
8. **`hermes a2a` n'existe pas** dans 0.21.3 : l'activation passe par le plugin et les clés de config.
9. **`tasks/cancel` n'est pas un vrai abort** : la tâche est marquée annulée mais le tour en cours de la session live va au bout.
10. Une **tâche entrante consomme un tour** de l'agent destinataire (session live, pas un clone) : cadence lente, une alerte = un appel.
11. **Non-objectifs assumés**, à ne pas présenter comme livrés : micropaiements x402, DID/Ed25519, scopes OAuth2, interopérabilité cross-framework ; et `a2a_orchestrate(mode="best")` = **la réponse la plus longue**, pas un score de qualité.

---

## 6. Commandes utiles

Rotation d'un secret (jamais la valeur dans le chat) :

```powershell
# Telegram : BotFather > /mybots > API Token > Revoke  → coller le nouveau dans le .env DU PROFIL
# puis preuve par test négatif / positif, sans afficher la valeur :
$t = (Select-String -Path "$env:LOCALAPPDATA\hermes\profiles\veille\.env" -Pattern '^TELEGRAM_BOT_TOKEN=').Line -replace '^TELEGRAM_BOT_TOKEN=',''
curl.exe -s -o NUL -w "nouveau: %{http_code}\n" "https://api.telegram.org/bot$t/getMe"   # 200 attendu
curl.exe -s -o NUL -w "ancien : %{http_code}\n" "https://api.telegram.org/bot<ANCIEN>/getMe"  # 401 attendu
```

```bash
# Gateway d'un profil : redémarrer et vérifier
hermes -p veille gateway restart && hermes -p veille gateway status
# état machine (telegram connected) :
grep -o '"telegram":{"state":"[a-z]*"' "$LOCALAPPDATA/hermes/profiles/veille/gateway_state.json"

# Cron d'un profil
hermes -p veille cron list ; hermes -p veille cron status ; hermes -p veille cron runs <job_id>
hermes -p veille cron create "0 8 * * 1" "$(cat prompt.txt)" --name veille-hebdo --deliver telegram --skill siyuan

# Healthcheck / tâches
schtasks /query /tn "Hermes_Gateway_HealthCheck" ; powershell -c "Start-ScheduledTask -TaskName Hermes_Gateway_HealthCheck"

# Services locaux (vérif de vivacité, pas de route racine sur certains)
for p in 6806 8200 9119 20128 20200; do curl -s -o /dev/null -w "$p -> %{http_code}\n" "http://127.0.0.1:$p/"; done

# État des profils + dépôt de configuration
hermes profile list ; hermes gateway list
cd "$LOCALAPPDATA/hermes" && git log --oneline -5 && git status --short
```

---

## 7. Points ouverts (à trancher, non corrigés ici)

1. **`eco` est dégradé** : le combo essaie ses 15 cibles et les épuise (`oc/*` et `opencode/*` en 403/402 — pool gratuit OpenCode fermé hors OpenCode, `gemini/gemini-3-flash-preview` en cooldown 429, Cloudflare en 502 « requires an Account ID », Pollinations désactivé le 17/09). Deux options : nettoyer les cibles mortes d'`eco`, ou passer `default` en `nvidia-stack` déterministe comme `veille`. **Ne pas improviser** : le job horaire `omniroute-eco-autorefresh` réécrit `eco` à chaque passage.
2. **`watch` n'a aucun repli gratuit** (`deepseek/deepseek-flash` seul) : même risque de bascule payante que `default` avant le 17/09. Alignement possible sur `[omniroute/nvidia-stack, deepseek/deepseek-flash]`.
3. **`watch` partage la clé OmniRoute du poste** (donc les droits d'administration) : une clé dédiée serait cohérente avec `veille`.
4. `profiles\watch\.env` porte le jeton du bot du bureau (avertissement `hermes profile list`) : à nettoyer avant toute migration multiplex.
5. `Desktop\hermes_install\snapshot\.env` : copie du `.env` du bureau en clair, à nettoyer (voir §4).
6. Le scanner de secrets (`data\rag\scan_secrets.py`) **n'a pas de mode export/redaction** : `snapshot\config.yaml.redacted` ne peut pas être régénéré proprement — à implémenter ou à abandonner volontairement.
