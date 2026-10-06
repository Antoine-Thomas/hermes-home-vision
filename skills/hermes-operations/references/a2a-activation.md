<!-- Extrait de hermes-operations/SKILL.md, lignes 492-588 (compression A.3 du 2026-10-06) — contenu verbatim. -->

## A2A — procédure d'activation (préparée, non activée)

**Prérequis : un 2ᵉ agent Hermes opérationnel et joignable.** Sans pair, ne pas activer : un port
d'écoute de plus à surveiller, zéro bénéfice.

**Scripts prêts** (jamais exécutés en mode activation) :

| Script | Rôle | Options |
|---|---|---|
| `%LOCALAPPDATA%\hermes\scripts\activer_a2a.ps1` | activation, **paramétrée par profil et par port** | `-LocalProfile` (défaut `default`), `-LocalPort` (9900), `-Profile` (pair), `-Port`, `-PeerToken`, `-PeerCaps`, `-WriteEnvKeys`, `-Force`, `-SkipGateway`, `-ConfigPath`, `-SelfTest` |
| `%LOCALAPPDATA%\hermes\scripts\desactiver_a2a.ps1` | retour au défaut fail-closed, symétrique | `-LocalProfile`, `-LocalPort`, `-Profile`, `-Port`, `-Force`, `-SkipGateway`, `-ConfigPath`, `-SelfTest` |

`activer_a2a.ps1` enchaîne : sauvegarde `config.yaml.a2a-backup-<horodatage>` →
`hermes plugins enable a2a-platform` → ajout de `- a2a` dans `platform_toolsets.cli` →
`hermes config set platforms.a2a.enabled true` → `hermes config check` → redémarrage des gateways
(profil watch inclus s'il existe) → vérification du port 9900 → rappel des 5 outils A2A.
`desactiver_a2a.ps1` fait l'inverse, plus `hermes config unset platforms.a2a.enabled`.

**`-SelfTest` est le seul mode exécutable sans risque** : il rejoue insertion/retrait sur une COPIE
de `config.yaml`, vérifie l'idempotence des deux sens et l'égalité md5 après add+remove, sans toucher
ni au plugin ni aux gateways. Rejoué sur la config live le 21/09/2026 (`platform_toolsets.cli` = 18
entrées) : add 18→19, add x2 sans effet, remove 19→18, md5 de la copie identique à l'original, md5 de
`config.yaml` inchangé, aucun `a2a-platform` enabled, rien en écoute sur 9900/9901 → scripts non périmés.
Gate relu le même jour : `_a2a_tools_available()` (`plugins/platforms/a2a/tools.py`), port par défaut
9900 (`adapter.py:_DEFAULT_PORT`), `a2a_agents` lu par `.get(nom)` (`tools.py:_configured_peers`).

**Piège de lecture** : `grep -n "a2a" config.yaml` renvoie une ligne (sous `known_plugin_toolsets.cli`)
— c'est le **registre** des toolsets plugin connus, pas une activation. L'activation se lit sous
`platform_toolsets.cli` ; vérifier avec `hermes plugins list | grep a2a` → `not enabled`.

**Config minimale — les 3 clés :**

| Élément | Où | Rôle |
|---|---|---|
| `platforms.a2a.enabled: true` | `config.yaml`, **clé racine** | gate des outils A2A (`tools.py:_a2a_tools_available`) et démarrage de la plateforme entrante |
| `a2a_agents:` | `config.yaml`, racine | pairs sortants : `url`, `auth: {type: bearer, token}`, `timeout`, `capabilities`. **Table indexée par NOM de pair** (`a2a_agents: {veille: {url: …}}`), pas une liste `- name:` : `tools.py::_configured_peers()` fait `.get(nom)` sur cette clé, donc une liste ouvre le gate des outils puis casse à l'appel (`'list' object has no attribute 'get'`) |
| `A2A_BEARER_TOKEN` (partagé) ou `A2A_PEER_TOKENS="alice:tok1,bob:tok2"` (par pair) | `.env` | authentification entrante |

`gateway.platforms.a2a.enabled` **n'est pas** la clé lue par le gate des outils — `gateway/config_loader.py`
fusionne les deux emplacements côté gateway, `tools.py` lit le niveau racine. Rencontrer un cas où les
outils n'apparaissent pas malgré la plateforme active : vérifier d'abord l'emplacement de la clé.

**Sécurité** : bind `127.0.0.1` tant qu'aucun jeton n'est posé (il faut un jeton **et**
`A2A_HOST=0.0.0.0` pour élargir — l'activation ne le fait jamais d'elle-même) ; audit
`a2a_audit.jsonl` ; conversations dans `a2a_conversations/` (survivent à la compaction) ; texte
entrant filtré (prompt-injection) et slash-commands non invocables par un pair ; texte sortant
nettoyé des chaînes ressemblant à des credentials.

**Port** : 9900 (`A2A_PORT`). Agent Card servie sur `/.well-known/agent-card.json`.

**Pièges vérifiés (reproduits en isolation) :**
- `platform_toolsets.cli` est une clé **liste** : c'est `references/config-editing-safety.md` qui
  s'applique ici (jamais `config set`, insertion textuelle ciblée).
- Un aller-retour YAML complet (`ruamel.yaml` load/dump) **reformate tout `config.yaml`** :
  réindentation des séquences, rewrapping des blocs de prompts. Diff inacceptable sur le fichier live.
- Une regex qui matche `^platform_toolsets:` doit **restituer la ligne d'en-tête** : la première
  version du script la consommait et supprimait le bloc entier. C'est le `-SelfTest` (comparaison
  md5) qui l'a attrapé.
- `is_connected()` lit `extra.enabled`, pas le champ typé `enabled` : l'état « connecté » affiché
  peut être faux alors que la plateforme tourne. Se fier à `netstat` sur 9900.

**Vérification après activation** : `hermes config check`, `netstat -ano | findstr :9900` (attendu :
`127.0.0.1:9900` en LISTENING), `hermes plugins list` (`a2a-platform` enabled).

**Désactivation** : `scripts\desactiver_a2a.ps1`, puis vérifier que 9900 n'écoute plus. Les jetons
`A2A_*` restent dans `.env` (inertes plugin désactivé) : les retirer à la main si besoin.

## A2A — cas d'usage stratégiques (lus dans le code, non activés ici)

| Cas | Ce que ça donne | Exemple concret | État vérifié |
|---|---|---|---|
| Fédération multi-machines | un agent Hermes par machine, chacun sa mémoire, ses clés, son modèle ; découverte par Agent Card | le bureau (PC) appelle l'agent veille (serveur / VM) pour une synthèse ; le distant garde ses propres credentials | Supporté (`#25176`, `#689` : agent↔agent inter-machines). Distant ⇒ `A2A_HOST` **et** jeton. Aucun pair configuré ici |
| Délégation cross-framework | appeler un agent non-Hermes | un agent LangChain / CrewAI / Google ADK / OpenClaw qui annonce une capacité devient un pair comme un autre | Interopérabilité **annoncée** dans `plugin.yaml` (JSON-RPC v1.0). Jamais testée localement : aucun pair non-Hermes dans le parc — ne pas la présenter comme acquise |
| Orchestration de capacités | `a2a_orchestrate(capability, message, mode)` diffuse à tous les pairs annonçant la capacité (`*` = tous) | « Cherchez les 5 dernières publications arXiv et croisez les résultats » avec 3 agents de recherche | Outil présent, modes `all` / `first` / `best` réels |
| Service callable (inbound) | Hermes devient un pair découvrable | un workflow n8n / Make découvre `/.well-known/agent-card.json` et envoie un `message/send` | Actif seulement avec `platforms.a2a.enabled: true`. La tâche entre dans la **session live** : elle occupe un tour réel de l'agent |
| Paiement à la requête (x402) | facturer un appel | — | **Hors périmètre** : `DESIGN.md` liste DID/Ed25519, scopes OAuth2 et x402 (`#14559` bindu) comme non-objectifs assumés. Ne pas planifier dessus |

### Pièges propres à A2A

- **Piège de lecture de config** : `grep -n a2a config.yaml` remonte `- a2a` (ligne ~717) sous
  `known_plugin_toolsets.cli` — la liste des toolsets *connus*, pas la liste *active*. Le gate réel
  est `platform_toolsets.cli` + `platforms.a2a.enabled`. Un grep naïf conclut « A2A activé » à tort.
- `hermes a2a` **n'existe pas** : activation par le plugin et les clés de config uniquement.
- **Aucune hook d'interception** dans le plugin (ni middleware ni call-site) : un guard de sécurité
  passe par un wrapper documenté, jamais par un branchement interne.
- `tasks/cancel` marque la tâche annulée et abandonne la réponse mais **ne coupe pas** le tour en
  cours de la session live : ce n'est pas un vrai abort.
- Une tâche entrante consomme un tour de l'agent destinataire — cadence lente, une alerte = un appel.
- `a2a_orchestrate(mode="best")` = **la réponse la plus longue**, pas un score de qualité ni de
  latence (le code se qualifie lui-même de « coarse »). Pour arbitrer, utiliser `all`. Les résultats
  sont triés par nom de pair, donc déterministes.
- Distant = `A2A_HOST` **et** un jeton ; sans jeton le bind reste `127.0.0.1` même si `A2A_HOST`
  est posé.
- L'interopérabilité cross-framework et les micropaiements x402 ne sont pas des fonctionnalités
  livrées : un brief qui les présente comme « working in production » mélange une issue-source
  d'exigences (`#11025` : injection session live, filtres, persistance, auth) et un non-objectif.

