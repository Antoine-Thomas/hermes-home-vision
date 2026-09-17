# Architecture Hermes — état consolidé

Date : 2026-09-17 · Hermes Agent v0.21.3 (2026.9.14), upstream `97962358` · install git :
`%LOCALAPPDATA%\hermes\hermes-agent` (propre) · A2A **non activé**.
Aucun secret en clair dans ce document : seules des empreintes `sha256[:16]` et des longueurs sont citées.

---

## 1. Les trois profils

| | `default` (bureau) | `watch` | `veille` |
|---|---|---|---|
| Rôle | opérateur : code, vidéo, WordPress, second cerveau | second profil historique (surveillances et automatisations), porte une copie complète des skills | veille techno : arXiv, HuggingFace, RSS/Atom, catalogue et prix OpenRouter → synthèse datée |
| Modèle par défaut | `eco` (provider `omniroute`) | `nvidia-stack` (provider `omniroute`) — déterministe, gratuit | `nvidia-stack` (provider `omniroute`) — déterministe, local, gratuit |
| Chaîne de repli | `omniroute/nvidia-stack` → `deepseek/deepseek-flash` | `omniroute/nemotron-3-super-120b-a12b` → `omniroute/auto/best-free` → `deepseek/deepseek-flash` | `omniroute/auto/best-free` → `omniroute/auto/best-reasoning` ⚠ (1er repli **mort** : 502, voir §7) |
| Skills (`SKILL.md` sur disque) | 107 (99 activées, 7 désactivées en config) | 124 (0 désactivée en config) | 61 (50 désactivées en config) |
| Bot Telegram | `8802352038` — sha256[:16] `7da363461151846e` | `8967117033` — sha256[:16] `8b0472877252f691` | `8801969330` — `@Hermesveille1_veille_bot`, sha256[:16] `eaa8b0ce89859d68` |
| Clé OmniRoute | clé du poste, 32 car., sha256[:16] `6ebeaffc871daef9` : sert **aussi** de jeton d'administration (`Bearer` sur `/api/keys`) | clé dédiée `hermes_watch`, 35 car., sha256[:16] `b62e9571e3543591`, **5 modèles autorisés** (`restricted`) | clé dédiée `hermes_veille`, 35 car., sha256[:16] `0c79be7af82b3421`, **7 modèles autorisés** (`modelAccessMode: restricted`) |
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
| `scripts\probe_omniroute.py` | sonde les modèles gratuits et maintient le combo `eco` (job cron horaire `5c9dd16aaa37`) | **additif + élagage** (depuis le 17/09) : ajoute les modèles vivants, retire une cible après 3 échecs terminaux consécutifs, plancher 2 cibles, état dans `data\omniroute\probe_omniroute_state.json` |
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
| `profiles\watch\.env` | **nettoyé le 17/09** : jeton Telegram du bureau retiré, puis **bloc `EMAIL_*` (6 lignes) retiré** → plus aucun credential partagé avec `default`, `hermes profile list` n'avertit plus. Restent le jeton du bot propre (`8967117033`, `@Omaths2_watch_bot`) et la clé OmniRoute dédiée `hermes_watch`. En revanche `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`, `KIMI_API_KEY`, `NVIDIA_API_KEY_GEMMA4` et `WHATSAPP_*` restent **identiques à `default`** (mêmes comptes) : ce ne sont pas des identités de canal — la détection de collision ne les voit pas — mais ils partagent les mêmes budgets d'API | ok : plus d'identité de canal partagée ; la migration multiplex n'est plus refusée pour ce motif |
| `Desktop\hermes_install` — dépôt git **externe** | **nettoyé le 17/09** : `snapshot\.env`, `snapshot\state.db` (192,1 Mo) et les copies `backups\veille\.env*` sont **dé-suivis** (`git rm --cached`) et exclus par motifs. Vérifié : plus aucun `.env` ni `state.db` suivi | les blobs subsistent dans `.git/` (80 Mo) : **purge d'historique non faite** → voir §8 |
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

1. **`eco` : décision tranchée et appliquée le 17/09 — option A (élagage), option C écartée faute de 2ᵉ clé Google, option B refusée** (128 K incompatibles avec les sessions longues du bureau, mesurées à ~262 K). `model.default` du bureau **reste `eco`** (rapide sur petit prompt, le repli gratuit `nvidia-stack` absorbe les échecs gros contexte).
   - **Appliqué** : `scripts\probe_omniroute.py` élague désormais une cible après **3 échecs consécutifs à code terminal** (401/402/403/404), avec un **plancher `FLOOR_MODELS = 2`** qui refuse tout élagage vidant `eco`, et un état persistant dans `data\omniroute\probe_omniroute_state.json`. Les échecs transitoires (429 quota, 502/504, timeout, 200-content-vide) **ne comptent pas** : un modèle rate-limité revient seul, un modèle vivant n'est jamais retiré.
   - **Résultat mesuré** (6 passes = 6 ticks simulés) : `eco` passe de **15 à 8 cibles** — les 7 cibles mortes retirées sont les 5 `oc/*` + les 2 `opencode/*` (403/402). Restent les 5 cibles saines (`gemini/gemini-3-flash-preview`, `gemini/gemini-2.5-flash`, `-flash-lite`, les 2 `openai/nvidia`) et `auto/gemini`, `auto/zai`, `auto/best-free`. Les 2 `gemini-2.5-*` (404 « no longer available to new users ») tomberont au fil des ticks **si** elles continuent de renvoyer 404 : actuellement elles flappent en 429 (cooldown), donc le compteur est volontairement remis à zéro.
   - **Retour arrière** : `backups\decision1_eco_20260917_160700\` (script, `restore_eco_20260912.py`, `eco_combo_avant.json` — les 15 cibles).
   - **Qui écrit eco** : le job cron `5c9dd16aaa37` `omniroute-eco-autorefresh` (`0 * * * *`, script `scripts\probe_omniroute.py`, actif). Il est **additif** : il ajoute les modèles vivants, ne retire jamais → 10 des 15 cibles sont mortes : 7 × `oc/opencode` (403 « OpenCode's free tier can only be used from within OpenCode », 402), `gemini/gemini-2.5-flash` et `-flash-lite` (404 « no longer available to new users »). Cibles vivantes : `gemini/gemini-3-flash-preview` (**1 048 576** ctx, souvent en cooldown 429) et les 3 `openai/nvidia/*` (**128 000** ctx).
   - **Mesuré le 17/09** : `eco` répond **vite** quand il est appelé (2,0 s / 2,7 s / 4,8 s sur 3 appels — servi par gemini puis nemotron-nano), là où `nvidia-stack` prend 11,0 s / 18,3 s / 12,3 s. L'échec réel d'`eco` se produit sur les **gros contextes** (> 128 K, comme la session de travail du jour à ~262 K) : seul gemini peut servir, et quand il est en cooldown les 14 autres cibles échouent → repli.
   - **Consommateurs** : `model.default` de `default` + l'alias `model_aliases.eco` ; **2 jobs cron épinglent `eco` explicitement** (« Relance fin de vacances », « Mémoire auto-consolidation ») ; 5 autres jobs héritent du modèle du profil ; **aucun script d'exécution** n'appelle `eco` (seuls les scripts de maintenance écrivent le combo).
   - **Option A — élaguer `eco`** : effort = 1 patch de `probe_omniroute.py` (retirer les familles mortes, purger au-delà de N échecs) + 1 nettoyage du combo. Gain = moins d'essais inutiles, logs propres, latence stable. **Ne résout pas** le gros contexte. Risque = c'est le script qui réécrit `eco` chaque heure : un bug qui vide `eco` envoie tout le trafic sur le payant (réparation : `data\omniroute\restore_eco_20260912.py`).
   - **Option B — bureau sur `nvidia-stack`** : effort = 1 édition de `config.yaml` (+ 2 jobs à réépingler). Gain = déterministe, gratuit, plus de 503 ni de bascule payante involontaire. Coût = **128 K au lieu de 1 M** (compression bien plus agressive sur les sessions longues) et **~4-6× plus lent**, avec 7 jobs actifs + les sessions sur 3 cibles NIM seulement (risque de 504 sous charge).
   - **Angle racine (option C)** : le point de défaillance unique est le quota Gemini — une seconde clé Google (nouvelle connexion) rétablirait la route 1 M rapide, l'option A suffisant alors pour le reste. **Procédure complète en §7.1** (documentation seule, aucune action faite).
2. **Repli « gratuit » de `veille` corrigé le 17/09** : `fallback_model` = `openai/nvidia/nemotron-3-super-120b-a12b` → `auto/best-free` → `auto/best-reasoning` (les 3 autorisés par la clé `hermes_veille`). Prouvé par échec primaire simulé : la session est servie par le nemotron-super (gratuit), plus par le payant. Le diagnostic reste vrai pour `auto/best-free` : **502** mesuré (felo 400, oc 400) — il est conservé en repli 2 pour détecter un rétablissement.
3. **`config.yaml` du bureau modifiable par plusieurs sessions en parallèle** : le 17/09 la session « MCP scite » a réécrit la fin du fichier (`mcp_servers.scite.enabled: true`, `auth: oauth`) et supprimé un bloc de commentaires `# ── Fallback Model ──`, sans perte fonctionnelle. Recommandation : **ne pas éditer le `config.yaml` du bureau en parallèle d'une session MCP** — une seule session à la fois sur les fichiers de configuration.
4. `profiles\watch\.env` : **jeton du bureau retiré le 17/09** (ligne commentée `# TELEGRAM_BOT_TOKEN=8802352038:…` supprimée ; le fichier ne contient plus que le jeton de `watch`, `@Omaths2_watch_bot`, `getMe` 200). **Credential email partagé : tranché et appliqué le 17/09 — option A (retrait).** Le motif réel de l'avertissement était bien `EMAIL_PASSWORD` (seule clé email retenue par la détection de collision : elle filtre les clés se terminant par `_PASSWORD/_TOKEN/_KEY/…`, ce qui exclut `EMAIL_ADDRESS`, `EMAIL_IMAP_HOST`, `EMAIL_SMTP_HOST`, `EMAIL_POLL_INTERVAL`). Les **6 lignes `EMAIL_*`** ont été retirées de `profiles\watch\.env` (backup `backups\chantier_triple_p1a_20260917_161834\env.watch.avant`, sha256[:16] avant `1603f5ea039e9eeb`, après `21fe62abfcd8f03e`), puis gateway `watch` redémarré : `✓ Gateway running with 1 platform(s)` (log) et `hermes profile list` **ne signale plus rien**. Preuve du diagnostic : `gateway_state.json` de `watch` annonçait `email: connected` avant le retrait — le profil tenait donc un **second poller IMAP sur la même boîte** (`searching.murphy@gmail.com`) que `default`, avec 0 session email traitée et 0 job cron côté `watch`. **Option B (mot de passe d'application dédié) écartée** : elle ferait taire l'avertissement mais laisserait les deux gateways sur la **même boîte** (le mot de passe n'est pas l'identité du canal) ; si `watch` doit un jour traiter l'email, la correction est une **boîte distincte**, pas un second mot de passe. Rollback : restaurer le backup puis `hermes -p watch gateway restart`.
5. **Dépôt externe** : dé-suivi et motifs faits (§8) ; **purge d'historique reportée** (décision du 17/09 : aucun remote, risque local, et les identifiants de commit servent à la traçabilité actuelle).
6. Le scanner de secrets (`data\rag\scan_secrets.py`) **n'a pas de mode export/redaction** : `snapshot\config.yaml.redacted` ne peut pas être régénéré proprement — à implémenter ou à abandonner volontairement.

### 7.1 Piste 2ᵉ clé Google — procédure (documentation seule, aucune action effectuée)

**But** : rétablir la fiabilité de la route rapide à 1 M de contexte d'`eco`. Aujourd'hui le pool
Gemini d'OmniRoute ne contient **qu'un seul compte** : dès que ce compte prend un `429` sur
`gemini-3-flash-preview`, la cible est écartée et il ne reste que les cibles 128 K (NIM).

**Preuve mesurée (17/09)** :

- log `~/.omniroute/logs/application/app.log` : `gemini | all 1 active accounts cooling down for model gemini-3-flash-preview (reset after 24s/56s)` → la rotation de comptes existe, mais son pool est de taille 1.
- `GET /api/providers` : **une seule** connexion `provider: gemini` (nom `hermes`, `testStatus: active`), à côté de `openai` (proxy NIM), `minimax`, `cloudflare-ai`, `oc`, `g4f-pollinations`… 12 connexions au total.

**Procédure (à faire le jour où la décision est prise)** :

1. Créer une clé API gratuite sur un **second compte Google** : <https://aistudio.google.com/apikey>. Coût 0 €. Une clé émise sur le **même** compte partage le même quota — le second compte est le point clé, pas la clé.
2. Déclarer la connexion dans OmniRoute (dashboard → *Connections*, ou API) en gardant le même `provider` que la connexion existante :
   ```bash
   curl -X POST http://127.0.0.1:20128/api/providers \
     -H "Authorization: Bearer $OMNIROUTE_API_KEY" -H 'Content-Type: application/json' \
     -d '{"name":"Gemini Account 2","provider":"gemini","authType":"apikey","apiKey":"<CLE>","isActive":true}'
   ```
3. Vérifier : `GET /api/providers` → **2** connexions `provider: gemini`, `testStatus: active`, `apiKeyHealth: ok` (relire, ne pas se fier au retour de création).
4. Vérifier la rotation réelle : laisser venir un `429` sur le compte 1 puis lire `app.log`. Attendu : le message ne dit plus *all **1** active accounts*, mais signale un compte restant disponible. **C'est cette ligne qui valide la piste** — pas le nombre de connexions affiché.
5. **Aucune modification d'`eco`** : le combo pointe toujours `gemini/gemini-3-flash-preview` ; c'est la résolution de compte dans le provider qui change. Ne rien ajouter au combo.
6. La clé vit **dans OmniRoute**, pas dans un `.env` Hermes : elle n'a rien à faire dans `%LOCALAPPDATA%\hermes\.env` ni dans un profil.

**Limites** : le quota gratuit reste par compte Google (une seconde clé ne débloque pas un modèle retiré du catalogue) ; les familles `oc/*` et `opencode/*` restent mortes (403/402) indépendamment de cette piste ; le nombre de comptes n'est pas un réglage documenté d'OmniRoute — le point 4 est donc la seule validation recevable.

---

## 8. Dépôt externe (`Desktop\hermes_install`) — règle et état

- **Règle : ni `.env`, ni `state.db` — jamais, même masqués.** Motifs ajoutés au `.gitignore` du dépôt :
  `.env`, `.env.*`, `**/.env`, `**/.env.*`, `**/state.db`, `snapshot/state.db*`, `**/*.db-wal`, `**/*.db-shm`, `backups/**/*.env*`.
- **Fait le 17/09** (commit « gitignore: retirer secrets et DB du suivi ») : `git rm --cached` sur
  `snapshot\.env` (24 230 o), `snapshot\state.db` (**192,1 Mo**), `backups\veille\.env.avant_telegram.20260917_134303`,
  `.env.avant_3d.*` et `.env.final.MASQUE`. Vérifié : `git ls-files | grep -E '\.env|state\.db'` → **vide**.
- **Purge d'historique : reportée le 17/09** — les blobs subsistent dans `.git/` (**80 Mo**, l'essentiel étant le
  `state.db` de 192 Mo compressé). **Commande disponible si un jour le dépôt est partagé ou envoyé à un tiers** :
  `git filter-repo --path snapshot/state.db --path snapshot/.env --invert-paths` (ou BFG) → **tous les SHA
  changent** (80 commits) et les identifiants de commit cités dans les rapports existants deviennent invalides ;
  gain ≈ 80 Mo. À ne lancer que sur décision explicite, en connaissance de ce coût de traçabilité.

## 9. Consolidation — état au 17/09

| Chantier | État |
|---|---|
| `watch` : clé OmniRoute dédiée + repli gratuit | **fait** : clé `hermes_watch` (5 modèles, `restricted`), `model.default: nvidia-stack`, repli `nemotron-3-super-120b` → `auto/best-free` → `deepseek-flash`, prouvé par échec primaire simulé (servi en gratuit, pas en payant) |
| `eco` dégradé | **traité le 17/09 (option A)** : `probe_omniroute.py` élague après 3 échecs terminaux consécutifs (plancher 2 cibles) → `eco` passe de **15 à 8 cibles** ; les échecs transitoires ne comptent pas. Option B refusée (128 K), option C sans 2ᵉ clé Google (piste ouverte) |
| Dépôt externe : secrets et volumes | **fait** (dé-suivi + motifs) ; purge d'historique **reportée** (commandée documentée en §8) |
