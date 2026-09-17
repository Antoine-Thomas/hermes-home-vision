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
agent via A2A. **État : profil `veille` créé, A2A et gateway non activés.** Ce skill décrit le
partage des rôles et le protocole ; il ne décrit pas une installation en service.

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

### Vérification du premier run automatique (lundi 08h00)

Le job `dc15c35183aa` du profil `veille` doit partir **seul** le lundi 08h00. Un `[active]` dans
`cron list` prouve l'armement, pas la livraison : après ce run, contrôler les trois preuves.
Détail des pièges de run : copie de ce skill dans `profiles\veille\skills\` (§6, « Cadence en service »).

1. **Document SiYuan créé** — document `YYYY-MM-DD-veille` dans le notebook `veille`
   (`20260915170851-ricqsr6`), contrôle par `POST /api/filetree/searchDocs` (`{"k":"veille"}`,
   `code=0`, `hPath` attendu). Un run peut rendre « ok » côté agent et échouer côté SiYuan.
2. **Message Telegram livré** — `deliver: telegram:8956868107` via le bot veille : vérifier la
   **réception réelle**, un « ok » ne prouve pas qu'un message est arrivé.
3. **Durée du run** — `hermes -p veille cron runs dc15c35183aa` (identifiant d'exécution, statut,
   horodatage), à comparer aux **2 min 49 s / 8 appels API** du run de test du 17/09 : une durée
   qui explose signale le pool gratuit instable (`503` par vagues), pas un défaut du prompt.

Consigner les trois valeurs (c'est ce qui distingue « planifié » de « livré ») ; si l'une est rouge,
corriger avant le lundi suivant — une cadence hebdomadaire qui casse ne se voit qu'une semaine après.

## 7. Activation (non faite)

Prérequis avant d'activer : profil `veille` avec son `.env` et son gateway joignable, jetons posés,
pairs déclarés. Activation et retour arrière : `scripts\activer_a2a.ps1` / `scripts\desactiver_a2a.ps1`
(procédure détaillée dans le skill `hermes-operations`).

`hermes a2a` **n'est pas une commande** : l'activation passe par le plugin et les clés de config.

Ne pas planifier de micropaiements x402 : explicitement hors périmètre du plugin (non-objectif
assumé dans `plugins/platforms/a2a/DESIGN.md`).
