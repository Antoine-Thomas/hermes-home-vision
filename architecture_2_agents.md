# Architecture 2 agents — Hermes bureau + Hermes veille

Statut : **document de préparation**. A2A n'est **pas** activé. Aucun port d'écoute, aucun jeton,
aucun pair configuré. Ce document décrit la cible et les faits vérifiés dans le code du plugin.

Date : 2026-09-17 · Hermes v0.21.3 (2026.9.14), upstream 97962358, install git.

---

## 1. Pourquoi A2A plutôt que delegate_task

| | `delegate_task` | A2A |
|---|---|---|
| Relation | boss → worker, hiérarchique | pair à pair, aucune autorité croisée |
| Frontière | in-process, même mémoire, mêmes credentials | traversée de processus, de machine, de framework |
| Durée de vie | l'enfant naît, rend son résultat, disparaît | les deux agents persistent, chacun son état |
| Mémoire | héritée du parent | propre à chaque agent |
| Usage naturel | découper un raisonnement lourd | fédérer des capacités autonomes |

Bornes natives de `delegate_task` (déjà réglées, à ne pas dépasser) : `max_spawn_depth: 1`,
`child_timeout_seconds: 120`, `max_concurrent_children: 3`. Aucun garde-fou de cycle ni budget de
tokens par enfant n'existe : rester à depth 1 jusqu'à ce que ces deux points soient implémentés.

---

## 2. État vérifié au 2026-09-17 (lecture seule)

| Élément | Valeur réelle | Commande de contrôle |
|---|---|---|
| Plugin `a2a-platform` | **not enabled** (bundled, v1.0.0) | `hermes plugins list` |
| `platform_toolsets.cli` | 17 toolsets, **sans `a2a`** | `grep -n "^platform_toolsets:" -A 25 config.yaml` |
| `platforms.a2a.enabled` | **clé absente** (section `platforms:` = google_chat, teams, whatsapp) | `sed -n '/^platforms:/,/^[a-z]/p' config.yaml` |
| Variables `A2A_*` dans `.env` | **0** | `grep -c "A2A_" .env` |
| Port 9900 | **aucun listener** | `netstat -ano \| grep :9900` |
| `a2a_conversations/`, `a2a_audit.jsonl` | **absents** | `ls ~/AppData/Local/hermes/a2a_conversations` |
| Profils existants | `default` (arrêté), `watch` (gateway running) | `hermes profile list` |
| Skills | 97 enabled, 7 disabled | `hermes skills list` |
| `hermes doctor` | 4 issues **préexistants** : 3× npm vulns, 1× `hermes setup` | `hermes doctor` |

**Piège de lecture :** `config.yaml` contient `- a2a` **ligne 717**, mais sous
`known_plugin_toolsets.cli` — la liste des toolsets connus, pas la liste active. Un `grep a2a`
naïf conclut à tort « A2A activé ». Le gate réel est `platform_toolsets.cli` +
`platforms.a2a.enabled` (+ `a2a_agents` pour le sortant).

---

## 3. Rôles des deux agents

| | Agent 1 — Hermes bureau (profil `default`) | Agent 2 — Hermes veille (profil `veille`) |
|---|---|---|
| Tâches | UI, code, vidéo IA, WordPress, second cerveau | veille techno continue, arXiv / HuggingFace / OpenRouter, synthèse |
| Pilote | l'utilisateur, en direct | autonome, cadencé par cron |
| Modèle | OmniRoute eco (gratuits d'abord) | modèle dédié recherche (à choisir, payant en dernier recours) |
| Mémoire | contexte personnel complet | contexte veille : articles lus, tendances, alertes émises |
| Credentials | clés perso (`.env` du profil default) | clés dédiées, **aucune reprise du `.env` default** |
| Disponibilité | quand l'utilisateur travaille | 24/7 (gateway dédié) |
| Sortie | actions sur le système, livrables | synthèses signées, alertes à signal fort |

Règle d'isolation : le profil `veille` ne doit **jamais** hériter du `.env` du bureau — donc pas de
`hermes profile create veille --clone`. Clonage interdit aussi pour les channels
(`--clone-channels`) : deux profils sur un même bot Telegram se neutralisent.

---

## 4. Communication A2A (cible, non activée)

### 4.1 Découverte

Chaque agent expose une Agent Card sur `/.well-known/agent-card.json` (chemin canonique v1.0 ;
l'ancien `/.well-known/agent.json` reste servi pour les clients pré-1.0). La card annonce nom,
description, compétences (dérivées des toolsets annoncés) et exigences d'auth.
Côté sortant, `a2a_discover(url)` récupère et résume une card distante.

### 4.2 Les 5 outils sortants (fournis par le plugin)

| Outil | Rôle |
|---|---|
| `a2a_discover` | interroger la card d'un pair (que sait-il faire ?) |
| `a2a_call` | envoyer une tâche à un pair, recevoir la réponse |
| `a2a_list` | pairs configurés, conversations enregistrées, métriques |
| `a2a_history` | relire une conversation A2A sauvegardée par `context_id` |
| `a2a_orchestrate` | diffuser une tâche aux pairs annonçant une capacité (`*` = tous) |

`a2a_orchestrate(capability, message, mode)` — sémantique **réelle** lue dans `tools.py` :

- `all` : tous les pairs traitent la tâche, réponses concaténées et étiquetées (défaut)
- `first` : premier succès, les pairs non démarrés sont annulés
- `best` : la **réponse la plus longue** parmi les succès — critère grossier, *pas* un score de
  qualité ni de latence. Pour juger, utiliser `all` et arbitrer soi-même.

### 4.3 Sens d'appel

- Sens 1 (bureau → veille) : `a2a_call("veille", "Qu'as-tu trouvé cette semaine sur les agents autonomes ?")`.
- Sens 2 (veille → bureau) : la veille appelle le bureau, ou pousse une notification via
  `tasks/pushNotificationConfig` (callbacks signés HMAC-SHA256, `X-A2A-Signature`, SSRF-guardés).

### 4.4 Entrant : session live, pas un clone

Une tâche A2A entrante est **injectée dans la session gateway vivante** de l'agent
(`adapter._prepare_task`) — le même agent qui parle à son opérateur, avec sa mémoire complète.
Ce n'est pas un clone jetable. Conséquence : une tâche A2A entrante occupe le tour de l'agent,
elle n'est pas parallèle à la conversation locale.

Binde : `message/send`, `message/stream` (SSE), `tasks/get|list|cancel|subscribe`, push config.
`tasks/cancel` marque la tâche annulée et abandonne la réponse, **mais ne coupe pas** le tour en
cours de la session live — ce n'est pas un vrai abort.

### 4.5 Transport et dépendances

Transport **stdlib pur** (`http.server` + `urllib`). `requires_env: []`, aucune dépendance
`a2a-sdk`, rien à installer. Le `⚠ a2a (system dependency not met)` du doctor est un **gate de
configuration** (toolset classé off par défaut), pas une dépendance manquante : ne pas chercher de
package à installer.

---

## 5. Sécurité et périmètre du second agent

| Point | Réalité du code |
|---|---|
| Bind par défaut | `127.0.0.1` (défaut `A2A_HOST`). L'élargissement à `0.0.0.0` exige **un token ET** l'opt-in `A2A_HOST` — jamais automatique |
| Jetons | `A2A_PEER_TOKENS="alice:tok1,bob:tok2"` (préféré : un credential par pair, identité = nom authentifié) ou `A2A_BEARER_TOKEN` (partagé, identité retombe sur l'IP) |
| Entrant | texte filtré (prompt-injection), slash-commands de l'opérateur **non invocables** par un pair |
| Sortant | chaînes ressemblant à des credentials nettoyées |
| Audit | `a2a_audit.jsonl`, une ligne par échange |
| Persistance | `a2a_conversations/<context_id>.jsonl` — hors pipeline de compaction, survit aux redémarrages |
| Interception | **aucune** hook middleware/call-site dans le plugin : un guard de sécurité doit passer par un wrapper documenté, pas par un branchement interne |

Ce que l'agent 2 a le droit de voir : ses propres clés de recherche, son `.env` de profil.
Ce qu'il ne voit pas : le `.env` du profil `default` (clés Telegram, DeepSeek, OmniRoute, SMTP,
Vision), les bots, le `channel_directory.json`.

### Hors périmètre explicite du plugin (DESIGN.md)

- `a2a-sdk`, bindings gRPC et HTTP+JSON : seul le binding JSON-RPC est servi
- champs `tenant`, Agent Card étendue, `stateTransitionHistory`
- vrai abort de tâche
- identité DID / Ed25519, scopes OAuth2, **micropaiements x402** (référence #14559 / bindu)

Les micropaiements x402 ne sont donc **pas** un adaptateur existant : c'est un non-objectif assumé,
à revisiter seulement s'il y a une demande réelle. Ne pas planifier dessus.

---

## 6. Prérequis avant activation (résumé)

1. Le profil `veille` existe, a son propre `.env`, et son gateway peut tourner (port distinct).
2. Un jeton est choisi : `A2A_PEER_TOKENS` par paire si possible, sinon `A2A_BEARER_TOKEN`.
3. Le pair est déclaré en sortant : `a2a_agents.<nom>.url` + `auth.type: bearer` + `capabilities`.
4. L'activation passe par `scripts\activer_a2a.ps1` (8 étapes, sauvegarde horodatée de
   `config.yaml`), et se vérifie par `hermes config check`, `netstat` sur 9900, `hermes plugins list`.
   Retour arrière : `scripts\desactiver_a2a.ps1`.
5. Ne pas activer tant que le second agent n'est pas joignable : un port d'écoute de plus à
   surveiller pour zéro bénéfice.

`hermes a2a` **n'existe pas** comme commande CLI. L'activation ne se fait pas par une commande
dédiée mais par le plugin + les clés de config ci-dessus.

---

## 7. Corrections au brief transmis (à ne pas propager)

| Affirmation du brief | Réalité vérifiée |
|---|---|
| « La PR #14559 documente un adaptateur Bindu qui ajoute des micropaiements x402 » | **Faux.** #14559 est cité dans `DESIGN.md` sous « Deliberately out of scope (future, not this pass) ». Aucune mention dans `README.md` ni `plugin.yaml`. Rien d'implémenté |
| « La PR #11025 documente le cas cross-framework Claude Code → revue de code, working in production » | **Faux dans l'interprétation.** #11025 est une issue-source d'exigences, tracée dans DESIGN.md sur 4 lignes : injection en session live, filtres de confidentialité + redaction sortante + audit, persistance hors compaction, auth localhost-default. Rien sur Claude Code ni une revue de code en production |
| « mode=best : le meilleur score (qualité, latence) » | **Faux.** `best` = la réponse la plus longue. Le code le qualifie lui-même de « coarse » |
| « hermes a2a » (sous-entendu commande CLI) | N'existe pas. `hermes --help` ne la liste pas |
| « A2A_BEARER_TOKEN partagé » | Correct, mais `A2A_PEER_TOKENS` (un jeton par pair) est la voie préférée |
| « A2A sur port 9900 », « /.well-known/agent-card.json », « a2a_conversations/ » | Corrects |
| `delegate_task` = boss/worker in-process, A2A = pair à pair | Correct |

---

## 8. Non-objectifs de ce chantier

- Ne pas activer A2A (plugin off, aucune clé, 9900 muet).
- Ne pas créer le second agent sur une autre machine : profil local uniquement.
- Ne pas modifier `config.yaml` du profil `default`.
