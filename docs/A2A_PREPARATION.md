# A2A — préparation complète, activation EN ATTENTE

Date : 2026-09-17 · Hermes Agent v0.21.3 (2026.9.14) · upstream `97962358` · install git.
Statut : **PRÊT À ACTIVER, NON ACTIVÉ.** Aucun port d'écoute, aucune clé `A2A_*`, aucun pair déclaré.
Aucun secret en clair dans ce document : seules des empreintes `sha256[:16]` et des longueurs le sont.

---

## 1. État mesuré à la fin de cette préparation (les deux côtés sont OFF)

| Élément | Valeur mesurée | Commande |
|---|---|---|
| Plugin `a2a-platform` | `not enabled` (1.0.0, bundled) | `hermes plugins list` |
| `platforms.a2a` | clé **absente** (section `platforms:` = `google_chat`, `teams`, `whatsapp`) | lecture YAML du `config.yaml` |
| `platform_toolsets.cli` | **17** toolsets, `a2a` **absent** | lecture YAML |
| `a2a_agents` | clé **absente** | lecture YAML |
| Ports 9900 / 9901 | **0 listener** (les deux) | `netstat -ano \| findstr :9900` |
| Clés `A2A_*` dans les `.env` | **0** dans `default`, `watch`, `veille` | `grep -c "^A2A_"` sur les 3 `.env` |
| `md5` du `config.yaml` bureau | `0ab7397453c5febaf9d3b14ebb172f3e` — **inchangé après les deux SelfTest** | `md5sum config.yaml` |

Piège de lecture déjà connu : `known_plugin_toolsets.cli` contient `- a2a`. Ce n'est **pas** la liste
active. Le gate réel des outils sortants est `a2a_agents` non vide **ou** `A2A_PORT` posé **ou**
`platforms.a2a.enabled: true` (`plugins/platforms/a2a/tools.py::_a2a_tools_available`).

---

## 2. Ce qui est prêt (livrables de la session)

| Livrable | Chemin | Preuve |
|---|---|---|
| Script d'activation paramétré | `%LOCALAPPDATA%\hermes\scripts\activer_a2a.ps1` (355 lignes) | `-SelfTest` → `exit=0`, add idempotent, copie identique à l'original, md5 du config réel inchangé ; diff complet avant écriture (`snapshot\activer_a2a_diff.txt`, +214/-69, 6 hunks) |
| Script de rollback symétrique | `%LOCALAPPDATA%\hermes\scripts\desactiver_a2a.ps1` (264 lignes) | `-SelfTest` → `exit=0`, mêmes contrôles (`snapshot\desactiver_a2a_diff.txt`, +119/-51) |
| Sauvegardes avant modification | `%LOCALAPPDATA%\hermes\backups\chantier_triple_p2a_20260917_162652\` | contient les deux scripts d'origine + `config.yaml.bureau.avant` + `md5_config_avant.txt` |
| Jetons par pair (générés, **non posés**) | `%TEMP%\a2a_tokens_20260917_162721.txt` (559 o, à supprimer après pose) | `bureau` — len 54, sha256[:16] `9885f0a0ee963974` · `veille` — len 54, sha256[:16] `394117de841c207f` |
| Architecture A2A | `docs\architecture_2_agents.md` | document de préparation, 8 sections |
| Dette A2A en 11 points | `docs\ARCHITECTURE_HERMES.md` §5 | état vérifié |

Le script accepte désormais : `-Profile` (pair), `-Port` (port du pair), `-PeerToken`, `-LocalProfile`,
`-LocalPort`, `-PeerCaps`, `-WriteEnvKeys`, plus `-Force`, `-SelfTest`, `-SkipGateway`, `-ConfigPath`.
Tout ce qui était codé en dur (`$profile2 = "watch"`, port 9900, `.env` du profil `default`,
`hermes config get/set` sans `-p`) est paramétré. Les vérifications de port portent sur **`-LocalPort`**
(écoute locale) et sur **`-Port`** (Agent Card du pair, sondée avant activation). L'insertion dans
`platform_toolsets.cli` reste une insertion textuelle ciblée, précédée de l'**affichage du diff** et
d'une confirmation (sauf `-Force`).

---

## 3. Checklist d'activation réelle — les 11 points, un par un

Reprise de `ARCHITECTURE_HERMES.md` §5, avec l'action attendue pour chacun.

| # | Point | Action avant activation | État |
|---|---|---|---|
| 1 | A2A reste OFF par défaut | Décision explicite de l'utilisateur — **rien ne s'active sans elle** | décision en attente |
| 2 | Un pair joignable est requis | Le profil `veille` existe et son gateway tourne (`running`) | ✔ mesuré |
| 3 | Script paramétrable absent | **fait** : `-Profile`/`-Port` acceptés, `-SelfTest` passé | ✔ |
| 4 | `A2A_BEARER_TOKEN` partagé vs `A2A_PEER_TOKENS` par paire | Préférer **un jeton par pair** (identité = nom authentifié, pas l'IP) ; jetons déjà générés | ✔ prêt |
| 5 | Bind local par défaut | `A2A_HOST=127.0.0.1` ; ne passer à `0.0.0.0` que si un pair **distant** est réellement voulu, et toujours avec un jeton | à poser |
| 6 | Pas de détection de cycle | `delegation.max_spawn_depth: 1` (mesuré dans le `config.yaml` bureau) — **ne pas augmenter** | ✔ garde-fou actif |
| 7 | Piège de lecture `known_plugin_toolsets` | Contrôler `platform_toolsets.cli`, jamais un `grep a2a` global | ✔ connu |
| 8 | `hermes a2a` n'existe pas | Activation = plugin + clés de config, via le script | ✔ |
| 9 | `tasks/cancel` n'est pas un vrai abort | Ne pas bâtir de logique sur « annuler = interrompre le tour en cours » | ✔ connu |
| 10 | Une tâche entrante consomme un tour de la session live | Cadence lente : une alerte A2A = un tour de l'agent destinataire | ✔ connu |
| 11 | Non-objectifs (x402, DID/Ed25519, OAuth2, cross-framework) | À ne pas présenter comme livrés ; `mode="best"` = la réponse la plus longue | ✔ connu |

Ordre d'exécution recommandé : **côté `veille` d'abord** (il doit écouter avant d'être appelé), puis
côté `default`, puis la déclaration des pairs (§4), puis les deux redémarrages, puis les vérifications (§6).

---

## 4. Blocs YAML à écrire à la main (NON écrits ici)

⚠️ **Correction d'une affirmation du brief** : `a2a_agents` est une **table indexée par le nom du pair**,
pas une liste d'entrées `- name:`. Vérifié dans le code : `tools.py::_configured_peers()` renvoie
`config["a2a_agents"]` puis fait `.get(agent)` dessus. Une forme « liste » fait enregistrer les outils
(clé non vide ⇒ gate ouvert) puis échoue à l'appel (`'list' object has no attribute 'get'`).

**Côté bureau — `%LOCALAPPDATA%\hermes\config.yaml`** (profil `default`, appelle la veille) :

```yaml
a2a_agents:
  veille:
    url: http://127.0.0.1:9901
    auth:
      type: bearer
      token: <tok_veille>          # valeur dans %TEMP%\a2a_tokens_*.txt — jamais dans un document
    timeout: 120                   # optionnel (défaut du plugin) : utile, une veille peut être lente
    capabilities: [research, veille]
```

**Côté veille — `%LOCALAPPDATA%\hermes\profiles\veille\config.yaml`** (appelle le bureau) :

```yaml
a2a_agents:
  bureau:
    url: http://127.0.0.1:9900
    auth:
      type: bearer
      token: <tok_bureau>
    timeout: 120
    capabilities: [code, video, wordpress, second-brain]
```

Les `capabilities` sont ce que `a2a_orchestrate(capability, …)` filtre : elles doivent décrire ce que le
pair sait faire, pas ce qu'on attend de lui. `a2a_call` accepte aussi une URL brute, sans passer par
`a2a_agents`.

---

## 5. Clés de configuration à poser (NON posées ici)

| Clé | Où | Valeur | Rôle |
|---|---|---|---|
| `platforms.a2a.enabled` | **racine** du `config.yaml` (pas `gateway.platforms`) | `true` | gate de la plateforme entrante et des outils A2A |
| `A2A_HOST` | `.env` du profil local | `127.0.0.1` | bind local (jamais `0.0.0.0` sans décision explicite) |
| `A2A_PORT` | `.env` du profil local | `9900` (bureau) / `9901` (veille) | port d'écoute du profil **et** second chemin d'activation de la plateforme |
| `A2A_PEER_TOKENS` | `.env` du profil local | `"veille:<tok_veille>"` (bureau) / `"bureau:<tok_bureau>"` (veille) | identité par pair des appels **entrants** |
| `A2A_AGENT_NAME` | `.env` du profil local (optionnel) | ex. `bureau`, `veille` | nom annoncé dans l'Agent Card (défaut : dérivé du hostname — les deux profils annonceraient le même nom) |

Jeton généré, valeur **jamais** affichée : `bureau` sha256[:16] `9885f0a0ee963974`, `veille`
sha256[:16] `394117de841c207f` (len 54 chacun). Le script affiche le bloc à recopier, et le pose
lui-même avec `-WriteEnvKeys` (sauvegarde horodatée du `.env` avant écriture).

---

## 6. Commandes uniques (à lancer UNIQUEMENT après validation)

```powershell
# 1) cote veille : ecouter sur 9901, pair = bureau
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\hermes\scripts\activer_a2a.ps1" `
  -LocalProfile veille -LocalPort 9901 -Profile default -Port 9900 -PeerCaps "code,video,wordpress,second-brain" -WriteEnvKeys -Force

# 2) cote bureau : ecouter sur 9900, pair = veille
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\hermes\scripts\activer_a2a.ps1" `
  -LocalProfile default -LocalPort 9900 -Profile veille -Port 9901 -PeerCaps "research,veille" -WriteEnvKeys -Force
```

Puis, obligatoirement à la main (le script n'écrit pas `a2a_agents` — voir §4) : coller les deux blocs
YAML, et redémarrer les deux gateways (`hermes gateway restart` et `hermes -p veille gateway restart`)
— le script ne redémarre que le gateway du profil local qu'il traite.

**Vérifications après activation** :

```bash
netstat -ano | grep -E ":9900|:9901"                  # 2 LISTENING, 127.0.0.1
curl -s http://127.0.0.1:9900/.well-known/agent-card.json   # card locale
curl -s http://127.0.0.1:9901/.well-known/agent-card.json   # card du pair
hermes config get platforms.a2a.enabled               # true
hermes -p veille config get platforms.a2a.enabled     # true
```

Si un port reste muet alors que `platforms.a2a.enabled: true` et `A2A_PORT` sont posés : lire
`logs/gateway.log` (le gateway journalise la plateforme A2A au démarrage) avant toute autre manœuvre.

---

## 7. Rollback

```powershell
# eteindre proprement, un cote a la fois
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\hermes\scripts\desactiver_a2a.ps1" -LocalProfile veille  -LocalPort 9901 -Profile default -Port 9900 -Force
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\hermes\scripts\desactiver_a2a.ps1" -LocalProfile default -LocalPort 9900 -Profile veille  -Port 9901 -Force
```

Puis retirer à la main les blocs `a2a_agents` (§4) et les lignes `A2A_*` du `.env` (le script les laisse
en place : inertes, plugin désactivé, mais visibles). Retour arrière en une commande si le script a
cassé quelque chose : `Copy-Item <config.yaml.a2a-backup-AAAAMMJJ-HHMMSS> <config.yaml> -Force`, les
sauvegardes étant écrites **avant** toute modification.

---

## 8. Points d'attention (à lire avant de dire oui)

1. **`max_spawn_depth = 1`** est le seul garde-fou anti-récursion (aucune détection de cycle A2A) : ne
   pas l'augmenter tant que ce point n'est pas implémenté.
2. **`tasks/cancel` n'est pas un vrai abort** : la tâche est marquée annulée, mais le tour en cours de la
   session live de l'agent destinataire va au bout. Ne rien bâtir sur « annuler = libérer l'agent ».
3. **`a2a_orchestrate(mode="best")` = la réponse la plus longue**, pas un score de qualité ni de latence
   (le code le qualifie lui-même de *coarse*). Pour arbitrer, utiliser `mode="all"` et lire les réponses.
4. **x402 / DID / Ed25519 / scopes OAuth2 : non-objectifs assumés**. Rien n'est implémenté ; ne pas
   planifier dessus (le plugin est en stdlib pure, aucune dépendance à installer — le
   « ⚠ a2a (system dependency not met) » du doctor est un gate de configuration, pas un paquet manquant).
5. **Une tâche entrante consomme un tour de la session vivante** de l'agent — ce n'est pas un clone : un
   pair bavard vole du temps à l'opérateur. Cadence lente, une alerte = un appel.
6. **Un port qui écoute est un service à surveiller** : sans pair réel, c'est du bruit dans les logs et
   une surface de plus. C'est la raison de ne pas activer maintenant.
7. **`a2a_conversations/<context_id>.jsonl`** et **`a2a_audit.jsonl`** apparaîtront à la première
   conversation : ce sont eux qui tracent, pas le `.env`.

---

## 9. Ce que cette préparation ne fait pas

- A2A **n'est pas activé** : plugin off, `platforms.a2a.enabled` non posé, `a2a_agents` non déclaré,
  9900 **et** 9901 muets, zéro clé `A2A_*`.
- Les **jetons ne sont pas posés** dans les `.env` (générés dans `%TEMP%` uniquement, en attente de
  validation). Le fichier est à supprimer après usage.
- Aucun **bind distant** (`A2A_HOST` reste `127.0.0.1`), aucun second agent hors de la machine.
- Le second agent n'est **pas** une seconde machine : tout est local, ports distincts, profils séparés.
