---
name: veille-2-agent
description: "Use when piloting the 2nd Hermes veille agent over A2A."
version: 1.0.0
author: searching-murphy
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [a2a, veille, research, arxiv, huggingface, multi-agent, profil]
    related_skills: [hermes-operations, arxiv, rss-feeds, research-content, rag-second-cerveau]
---

# Veille — 2ᵉ agent Hermes (A2A)

Second agent Hermes dédié à la veille techno continue et à la recherche, appelable par le premier
agent via A2A. **État au 17/09/2026 : profil `veille` en service sur son propre gateway (Telegram
`@Hermesveille1_veille_bot`) et veille hebdomadaire planifiée côté profil ; A2A toujours non
activé.** Ce skill décrit le partage des rôles, la cadence réelle (§6) et le protocole A2A à
activer (§7).

Préparation côté architecture : `Desktop\hermes_install\architecture_2_agents.md`.
Profil côté machine : `Desktop\hermes_install\profil_veille.md`.

## 1. Rôles

| | Agent bureau (`default`) | Agent veille (`veille`) |
|---|---|---|
| Déclencheur | l'opérateur, en direct | cadence (cron du profil) |
| Périmètre | code, vidéo, WordPress, second cerveau | veille, recherche, synthèse |
| Sortie | actions sur le système | synthèse datée + alertes à signal fort |
| Credentials | clés perso | clés de recherche dédiées, jamais celles du bureau |

L'agent veille n'exécute pas d'actions sur le système du bureau. Il produit du texte ; le bureau
décide quoi en faire.

## 2. Ce que fait l'agent veille

- **Sources** : arXiv (skill `arxiv`, API REST sans clé), flux RSS/Atom (skill `rss-feeds`),
  HuggingFace (modèles, datasets, papers), OpenRouter (catalogue et prix), veille concurrentielle
  (skill `competitor-news-monitor`).
- **Synthèse hebdomadaire** : liste datée, un paragraphe par sujet retenu, chaque affirmation
  rattachée à sa source (URL + date). Pas de sujet sans source : les skills de veille produisent
  des listes, l'agent ajoute la lecture critique.
- **Alerte à signal fort** : émise dès détection, hors cadence hebdomadaire. Un signal fort est un
  changement qui invalide une décision en cours (mise à jour majeure d'un outil utilisé, rupture
  d'API, changement de licence, vulnérabilité dans une dépendance du parc).
- **Filtre** : ne remonter que ce qui est actionnable pour le parc de l'opérateur. Une nouveauté
  qui ne touche ni ses outils ni ses projets est du bruit, pas de la veille.

### Sources et outils suivis (vérifiés)

| Source | Type | Note |
|---|---|---|
| arXiv `2609.04894` — *From Language Models to World-Acting Systems: Progress and Limits of Agentic AI across Digital, Social, Virtual, and Physical Environments* | Article de revue, 29 p., 1 fig., 3 tab., cs.AI/cs.LG/cs.MA — https://arxiv.org/abs/2609.04894 | **Publié le 2026-09-04** (v1). Ne pas dater du 07/09 : la date se vérifie via l'API arXiv, pas de mémoire. Déjà cité dans la note `2026-09-17-veille`. |
| Scite.ai Assistant — https://scite.ai/assistant | Assistant de recherche académique avec citations vérifiables (page vérifiée le 17/09/2026 : « answers grounded in scholarly literature », 250M+ papers) | Chaque affirmation est liée à des articles ; montrer les preuves pour/contre (Smart Citations) ; mode Table pour comparer des études. Utile pour trancher une affirmation scientifique ambigue — la page renvoie 403 à `curl` sans User-Agent navigateur. |

Règle de vérification avant d'ajouter une source : l'existence se contrôlle par l'API de la source
(arXiv `export.arxiv.org/api/query?id_list=…`, pas un titre recopié) ; une URL qui répond 200 avec un
`<title>` et une meta description cohérents compte comme vérifiée, sinon la source se marque « à
vérifier » et ne se cite pas comme un fait.

## 3. Ce que fait l'agent bureau du résultat

1. Lecture de la synthèse (message A2A ou fichier poussé).
2. Dépôt dans le second cerveau SiYuan (notebook projet concerné) — voir le skill `siyuan`.
3. Le RAG suit automatiquement : l'indexation planifiée ramasse les nouveaux contenus
   (`%LOCALAPPDATA%\hermes\data\rag\`, ré-indexation programmée). Ne pas réindexer à la main pour
   chaque synthèse — attendre le passage planifié, ou le déclencher si la synthèse est urgente.
4. Si la synthèse contredit une note existante, c'est la contradiction qu'il faut enregistrer, pas
   le remplacement silencieux.

## 4. Protocole A2A

Les cinq outils sortants sont fournis par le plugin bundled `a2a-platform` : `a2a_discover`,
`a2a_call`, `a2a_list`, `a2a_history`, `a2a_orchestrate`. Port par défaut : 9900. Card servie sur
`/.well-known/agent-card.json`.

### Sens 1 — le bureau interroge la veille

```
a2a_call(agent="veille", message="Qu'as-tu trouvé cette semaine sur les agents autonomes ?")
```

- Le pair `veille` doit être déclaré côté **appelant** (`a2a_agents.veille.url` +
  `auth: {type: bearer, token: ...}` + `capabilities: [research, veille]`).
- Passer un `context_id` pour poursuivre un fil : `a2a_history(context_id)` permet de relire une
  conversation enregistrée après compaction ou redémarrage (`a2a_conversations/<context_id>.jsonl`).
- Pour interroger plusieurs agents de recherche sur la même question :
  `a2a_orchestrate(capability="research", message="...", mode="all")`. Modes réels : `all`
  (tous, réponses étiquetées — le bon choix pour arbitrer soi-même), `first` (premier succès), `best`
  (**la réponse la plus longue**, critère grossier — pas un score de qualité ni de latence).

### Sens 2 — la veille pousse vers le bureau

Deux voies, dans cet ordre de préférence :

1. **Appel sortant** de la veille vers le bureau : déclarer le pair `bureau` dans le
   `a2a_agents` du profil `veille`, puis `a2a_call(agent="bureau", message=<alerte>)`.
2. **Push notification** : la veille fournit une config de webhook (`tasks/pushNotificationConfig`),
   signée HMAC-SHA256 (`X-A2A-Signature`), SSRF-guardée. Utile si le bureau n'a pas de pair
   configuré en entrée.

Une tâche A2A entrante est injectée dans la **session live** de l'agent destinataire (ce n'est pas
un clone jetable) : elle occupe un tour de l'agent qui parle à son opérateur. Ne pas envoyer de
rafales — une alerte = un appel.

## 5. Sécurité et périmètre

| Règle | Détail |
|---|---|
| Isolation credentials | Le profil `veille` a son propre `.env`. **Ne jamais** le remplir depuis le `.env` du bureau, et ne jamais créer le profil avec `--clone` |
| Clés dédiées | Clés de recherche propres au profil. Sans clé dans son `.env`, le profil hérite des variables du **shell** : vérifier l'environnement avant de lancer son gateway |
| Bind | `127.0.0.1` par défaut. Ne s'élargit à `0.0.0.0` qu'avec un jeton **et** `A2A_HOST` explicite |
| Jetons | `A2A_PEER_TOKENS="veille:tok1"` (un jeton par pair, identité = nom authentifié) plutôt que `A2A_BEARER_TOKEN` partagé (identité retombant sur l'IP) |
| Entrant | texte filtré (prompt-injection) ; un pair ne peut **pas** invoquer les slash-commands de l'opérateur |
| Sortant | chaînes ressemblant à des credentials nettoyées ; audit dans `a2a_audit.jsonl` |
| Bot Telegram | ne pas cloner les channels (`--clone-channels`) : deux profils sur un même token de bot se neutralisent |

Ce que l'agent veille a le droit de voir : ses clés de recherche, son workspace.
Ce qu'il ne voit pas : le `.env` du profil bureau, les bots, `channel_directory.json`, les sessions
de l'opérateur.

## 6. Cadence

Les tâches planifiées sont **par profil** : `hermes -p veille cron list`. Créer la veille récurrente
côté `veille` (pas côté bureau), et faire délivrer les rapports lourds en local ou vers un canal
messagerie — jamais via un `deliver` qui bloque le tour du gateway.

Cron côté bureau = livrer du signal, pas tout le corpus : une tâche qui parle à chaque tick finit
ignorée.

### Cadence en service

| | |
|---|---|
| Job | `veille-hebdo` — id `dc15c35183aa`, profil `veille` |
| Schedule | `0 8 * * 1` (lundi 08h00, heure locale) |
| Modèle | suit `model.default` du profil : `auto/best-reasoning` (OmniRoute 20128), fallback `nvidia-stack` puis `auto/best-free` |
| Deliver | Telegram — `telegram:8956868107` (bot veille) |
| Sortie 2 | document `YYYY-MM-DD-veille` dans le notebook SiYuan `veille` (`20260915170851-ricqsr6`) |
| Skills | `siyuan` (création du document) |

Création :

```
hermes -p veille cron create "0 8 * * 1" "$(cat prompt.txt)" \
  --name veille-hebdo --deliver telegram --skill siyuan
```

Test immédiat : `hermes -p veille cron run dc15c35183aa` — le job part au tick suivant (< 1 min).
Durée mesurée du premier run : 2 min 49 s, 8 appels API. Le pool gratuit d'OmniRoute a renvoyé
plusieurs 404/400/403 avant de servir le modèle : sans conséquence, mais ça allonge le run et ça
remplit `logs/errors.log`.

Le prompt du job doit rester auto-portant (aucun contexte de session) et exiger : URL par item,
verdict d'impact (`impact direct` / `à surveiller` / `bruit`), 3 à 5 items par thème, et une
mention explicite quand rien n'est actionnable — c'est ce qui empêche le modèle d'inventer.

Pièges constatés en run réel :

- **`execute_code` est bloqué dans un job cron** : « Cron jobs run without a user present to
  approve arbitrary local Python ». Écrire en `terminal` (`curl`) + `write_file`, jamais en Python.
- **Le pool gratuit d'OmniRoute est instable** : `503 ALL_TARGETS_SKIPPED` et « Maximum combo retry
  limit reached » arrivent par vagues (premier appel à 95 s). Un run peut échouer puis réussir deux
  minutes plus tard — retenter `hermes -p veille cron run <job>` avant de suspecter la clé.
- **Deux runs le même jour créent deux documents `YYYY-MM-DD-veille`** : SiYuan accepte les
  doublons de titre (ids différents). Nettoyer après un test manuel.

### Vérification du premier run automatique (lundi 08h00)

Le job `dc15c35183aa` doit partir **seul** le lundi 08h00. Un `[active]` dans `cron list` prouve
l'armement, pas la livraison : après ce run, contrôler les trois preuves et les consigner.

1. **Document SiYuan créé** — document `YYYY-MM-DD-veille` dans le notebook `veille`
   (`20260915170851-ricqsr6`) :
   ```bash
   curl -s -X POST http://127.0.0.1:6806/api/filetree/searchDocs \
     -H "Authorization: Token $SIYUAN_TOKEN" -H 'Content-Type: application/json' \
     -d '{"k":"veille"}'      # code=0 et hPath « veille/AAAA-MM-JJ-veille »
   ```
   Un run peut rendre « ok » côté agent et échouer côté SiYuan (jeton absent, notebook fermé).
2. **Message Telegram livré** — `deliver: telegram:8956868107` via le bot veille. Vérifier la
   **réception réelle** : le run peut rendre « ok » avec une livraison refusée par Telegram.
3. **Durée du run** — `hermes -p veille cron runs dc15c35183aa` (identifiant d'exécution, statut,
   horodatage). Comparer aux **2 min 49 s / 8 appels API** du run de test : une durée qui explose
   signale le pool gratuit instable (vagues de `503`), pas un défaut du prompt.

Si les trois sont vertes : la cadence est en service. Sinon, corriger avant le lundi suivant —
un job hebdomadaire qui échoue une fois ne se voit qu'une semaine plus tard.

## 7. Activation (non faite)

Prérequis avant d'activer : profil `veille` avec son `.env` et son gateway joignable, jetons posés,
pairs déclarés. Activation et retour arrière : `scripts\activer_a2a.ps1` / `scripts\desactiver_a2a.ps1`
(procédure détaillée dans le skill `hermes-operations`).

`hermes a2a` **n'est pas une commande** : l'activation passe par le plugin et les clés de config.

Ne pas planifier de micropaiements x402 : explicitement hors périmètre du plugin (non-objectif
assumé dans `plugins/platforms/a2a/DESIGN.md`).
