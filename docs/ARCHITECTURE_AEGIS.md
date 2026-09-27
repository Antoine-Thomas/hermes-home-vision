# Architecture Hermes Aegis — version 1.4

> **Statut : préparée, NON publiée.** Aucun tag ni release `v1.4` n'existe ; la version stable
> précédente reste la 1.3 (Psychopomp). Deux bloqueurs interdisent la publication — cf. §6.
> Ce document décrit l'état **mesuré le 27/09/2026** sur la machine d'origine
> (`%LOCALAPPDATA%\hermes`, Windows 11 natif).

Aegis = quatrième couche ajoutée à Hermes Home Vision : la configuration passe d'un empilement
« profils + services » à une architecture **4 couches** où la sécurité est un étage à part entière,
vérifiable indépendamment des trois autres.

---

## 1. Vue d'ensemble — les 4 couches

```
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║ COUCHE 1 — PROFILS (isolation)                                                            ║
║                                                                                           ║
║   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐          ║
║   │     default    │  │      watch     │  │     veille     │  │   docs-writer  │          ║
║   │  config.yaml   │  │  config.yaml   │  │  config.yaml   │  │  config.yaml   │          ║
║   │  .env dédié    │  │  .env dédié    │  │  .env dédié    │  │  .env dédié    │          ║
║   │  bot Telegram  │  │  bot Telegram  │  │  bot Telegram  │  │  (pas de bot)  │          ║
║   │ clé OmniRoute  │  │ clé hermes_    │  │ clé hermes_    │  │  DeepSeek seul │          ║
║   │                │  │      watch     │  │     veille     │  │                │          ║
║   └───────┬────────┘  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘          ║
║           │                   │                   │                   │                   ║
║   ACL de chaque .env : Système(F) · Administrateurs(F) · searc(F) — non héritées          ║
╚═══════════╪═══════════════════╪═══════════════════╪═══════════════════╪═══════════════════╝
            └───────────────────┴─────────┬─────────┴───────────────────┘
                                          │
╔═════════════════════════════════════════▼═════════════════════════════════════════════════╗
║ COUCHE 2 — ROUTAGE (LLM)                                                                  ║
║                                                                                           ║
║   ┌────────────────────────────────────┐        ┌────────────────────────────────────┐    ║
║   │        OmniRoute   20128           │        │        Proxy NIM   20200           │    ║
║   │  routeur LLM, combos + repli       │        │  Nemotron local (NVIDIA NIM)       │    ║
║   │  ordonné :                         │        │  normalise préfixes de modèles     │    ║
║   │    free-openrouter                 │        │  et paramètres rejetés             │    ║
║   │    nvidia-stack                    │        └────────────────────────────────────┘    ║
║   │    deepseek                        │                                                   ║
║   └────────────────────────────────────┘                                                   ║
║                                                                                           ║
║   Principe : gratuit d'abord, payant en dernier — chaque bascule est tracée (§5).          ║
╚═════════════════════════════════════════╪═════════════════════════════════════════════════╝
                                          │
╔═════════════════════════════════════════▼═════════════════════════════════════════════════╗
║ COUCHE 3 — CERVEAU (mémoire)                                                              ║
║                                                                                           ║
║   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐                               ║
║   │   RAG   8200  │   │ Backend  9119 │   │ SiYuan   6806 │                               ║
║   │  index 2ᵉ     │   │  cœur Hermes  │   │  base de      │                               ║
║   │  cerveau      │   │  API/dashboard│   │  connaissances│                               ║
║   └───────┬───────┘   └───────────────┘   └───────────────┘                               ║
║           │                                                                               ║
║   ┌───────▼────────────────────────────┐   ┌────────────────────────────────────────┐     ║
║   │  JEV  ·  OpenRouter                │   │  Laya  ·  ONNX local (CPU)             │     ║
║   │  décision typée : noul/choice/score│   │  accélérateur gratuit, hors ligne      │     ║
║   │  route wiki (L1) · RAG (L2)        │   │  JEV reste le décideur principal        │     ║
║   └────────────────────────────────────┘   └────────────────────────────────────────┘     ║
╚═════════════════════════════════════════╪═════════════════════════════════════════════════╝
                                          │
╔═════════════════════════════════════════▼═════════════════════════════════════════════════╗
║ COUCHE 4 — SÉCURITÉ (Aegis)                                                               ║
║                                                                                           ║
║   ACL minimales      secrets hors git      Wazuh           ports Windows                  ║
║   ─────────────      ─────────────────     ───────────     ──────────────────────         ║
║   3 ACE par .env     0 secret versionné    manager 55085    plage réservée 54985-55084    ║
║   non héritées       12 sauvegardes        indexer 9200    → remap, jamais de bind forcé  ║
║   CodexSandboxUsers  hors du dépôt         allowlist à jour                           ║
║   retirée            (hermes-secrets-                                                     ║
║                       backup\)                                                            ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. Couche 1 — Profils (isolation)

Quatre profils, chacun avec **son** `config.yaml`, **son** `.env`, **son** bot Telegram (sauf
`docs-writer`) et **sa** clé OmniRoute (sauf `docs-writer`).

| Profil | Rôle | `model.default` mesuré | Provider | Bot Telegram | Clé routeur |
|---|---|---|---|---|---|
| `default` | opérateur : code, vidéo IA, WordPress, second cerveau | `deepseek-flash` | `deepseek` | `@Hermes_assistante_2026_bot` | `OMNIROUTE_API_KEY` (poste) |
| `watch` | surveillance services + automatisations | `nvidia-stack` | `omniroute` | `@Omaths2_watch_bot` (**désactivé**) | `hermes_watch` (5 modèles) |
| `veille` | veille techno : arXiv, HuggingFace, RSS → synthèse datée | `nvidia-stack` | `omniroute` | `@Hermesveille1_veille_bot` | `hermes_veille` (7 modèles) |
| `docs-writer` | rédaction documentaire (cwd `C:/Users/searc/hermes-docs`) | `deepseek-flash` | `deepseek` (direct) | — | — |

Écarts mesurés par rapport au gabarit « 1 bot + 1 clé OmniRoute par profil » :

- `docs-writer` ne porte **que** `DEEPSEEK_API_KEY` : profil de rédaction sans canal Telegram, en
  appel direct à l'API DeepSeek (aucun passage par OmniRoute).
- `default` et `docs-writer` ont `model.default = deepseek-flash` alors que le provider `omniroute`
  du profil `default` déclare toujours `default_model: eco`. Le combo `eco` reste donc la cible
  nominale de la couche de routage, mais le modèle **effectivement** sélectionné est le payant :
  dérive documentée et surveillée dans la skill `omniroute-gateway` (un tick `eco` facturé
  `billing_provider=deepseek` est le symptôme).
- Le bot `watch` est désactivé : la surveillance passe par le profil `default` (gateway multiplexé).

**Isolation** — vérifiable et non négociable :

- un bot Telegram n'appartient qu'à un profil (deux gateways sur le même bot se neutralisent) ;
- les clés `hermes_watch` / `hermes_veille` sont restreintes à une liste de modèles et ne donnent
  pas l'administration du routeur ;
- jamais de `hermes profile create --clone` / `--clone-channels` : un profil cloné hérite de
  credentials qui ne lui appartiennent pas ;
- sur une nouvelle machine, générer de **nouvelles** clés (bots, OmniRoute, jeton SiYuan).

**ACL des `.env`** — les 4 fichiers de secrets portent exactement 3 ACE non héritées :

```
icacls ".env" /inheritance:r /grant:r "Système:(F)" "Administrateurs:(F)" "%USERNAME%:(F)"
```

Mesure du 27/09/2026 : `.env`, `profiles\watch\.env`, `profiles\veille\.env`,
`profiles\docs-writer\.env` → **3 ACE (F), 0 héritée, 0 trace `CodexSandboxUsers`**.
`CodexSandboxUsers:(I)(RX)` — héritée d'un outil tiers — a été retirée des quatre.

---

## 3. Couche 2 — Routage (LLM)

**OmniRoute** (`127.0.0.1:20128`) est le routeur unique des profils `watch` et `veille`, et
l'endpoint déclaré du profil `default` (`extra_headers: X-OmniRoute-Compression: default`,
`request_timeout_seconds: 120`). Il expose des **combos** et une **chaîne de repli ordonnée** :

| Ordre | Cible | Nature | État mesuré |
|---|---|---|---|
| 1 | `free-openrouter` / `auto/best-free` | gratuit | déclaré en repli (`auto/best-free` rend des 502 : voir limites) |
| 2 | `nvidia-stack` | gratuit (NVIDIA NIM) | modèle par défaut de `watch` et `veille` |
| 3 | `deepseek` | **payant** | dernier recours, chaque bascule est signalée |

Chaînes réellement déclarées (`config.yaml`) :

```yaml
# profil watch — fallback_providers
- provider: omniroute   ; model: openai/nvidia/nemotron-3-super-120b-a12b   # gratuit, autorisé par la clé watch
- provider: omniroute   ; model: auto/best-free
- provider: deepseek    ; model: deepseek-flash                             # payant, en dernier

# profil veille — fallback_model
- provider: omniroute   ; model: openai/nvidia/nemotron-3-super-120b-a12b   # gratuit, autorisé par la clé veille
- provider: omniroute   ; model: auto/best-free
- provider: omniroute   ; model: auto/best-reasoning                        # retiré de la 1.3 côté default (alias payant)
```

**Proxy NIM** (`127.0.0.1:20200`) normalise les appels NVIDIA NIM (préfixes de modèles et
paramètres rejetés) et sert le Nemotron local. Il sert d'étage d'appoint quand la cible
`nvidia-stack` est saturée.

Règle de conception : **le gratuit d'abord, le payant en dernier**, et toute bascule vers un
provider payant est traçable (champ `billing_provider` de l'historique de cron). Un tick annoncé
`eco` mais facturé `deepseek` n'est pas un coût normal : c'est une dérive à corriger.

---

## 4. Couche 3 — Cerveau (mémoire)

| Service | Port | État mesuré le 27/09/2026 | Rôle |
|---|---|---|---|
| **RAG** | `127.0.0.1:8200` | `/sante` → `status: ok`, **2 314 fragments**, `intfloat/multilingual-e5-base`, index 7,1 Mo | recherche vectorielle du second cerveau |
| **Backend** | `127.0.0.1:9119` | en écoute (pid 19196) | cœur Hermes : API/dashboard |
| **SiYuan** | `127.0.0.1:6806` | en écoute (pid 9884), **7 notebooks** | base de connaissances (accès par `accessAuthCode`, local seulement) |

Répartition RAG par source (`/sante`, 27/09/2026) : `siyuan 483`, `skill 1742`, `wordpress 89`,
`script_v4 0`. La source `script_v4` a été **retirée** le 27/09/2026 (dossier source disparu) :
l'entrée à 0 disparaît du manifeste à la passe d'indexation suivante (03:00 quotidienne).

**JEV — décision typée.** Skill TypeSafe exposant trois primitives — `noul` (juger), `choice`
(trancher), `score` (noter) — qui route entre le **wiki** (L1, connaissances compilées dans
SiYuan) et le **RAG** (L2, recherche brute) pour les choix courts à 2-5 options.

- Transport : OpenRouter, `https://openrouter.ai/api/v1/systemone`, modèle `typesafe/jev-1.13`.
- **Vérifié en direct le 27/09/2026** : `route = wiki`, `forced = false`, confiance 0,98,
  **0,48 s**, **3,54e-05 $** par appel (mesure précédente au catalogue : 0,316 s / 1,46e-05 $ —
  le coût a été revu à la hausse).
- Limite connue : score sur 10 niveaux maximum.
- Intégration : JEV n'est **pas** branché au backend 9119 (aucun hook automatique) — il est appelé
  par des scripts explicites (`wiki/scripts/jev_router.py`).
- **Repli local** : si JEV est injoignable, `jev_router.py` renvoie
  `{"route": "rag", "forced": true, "forced_reason": "Jev injoignable", "route_source": "fallback_local"}`
  et sort en code **2** — la dégradation est visible par l'appelant, jamais silencieuse. Aucun
  repli vers un second moteur.

**Laya — accélérateur local.** Modèle de décision typée non autorégressif (ModernBERT-large +
tête typée) exécuté en **ONNX sur CPU**, sans PyTorch : `onnxruntime` + `tokenizers` suffisent,
checkpoint `english` (512 ctx) sous `%LOCALAPPDATA%\hermes\data\laya-onnx\`, ~**190-200 ms par
décision**, coût nul, hors ligne.

Limites mesurées le 27/09/2026 (benchmark réel, à connaître avant tout branchement en production) :

1. **`noul` en français échoue** — état FR + question FR → 0,0259 (répond NON) là où le même
   contenu en anglais donne 0,8211 (OUI) ; Laya suit ses labels anglais. Contournement : poser la
   question en `choice` à 2 options neutres, ou tout passer en anglais.
2. **État > 512 tokens : troncature à droite** — latence ×6 (815 ms → 4 900-5 300 ms pour 4
   questions) et décisions dégradées (0,42 au lieu de 0,89 sur le cas mesuré). Contournement :
   résumer l'état sous 512 tokens avant l'appel.
3. **Budget d'options ≈ 48 tokens par option** (`(head_max_len - 16) // k`) — au-delà, la
   distribution s'aplatit. Contournement : 6-7 options courtes maximum.

Accord JEV ↔ Laya mesuré : 6/10 sur le routage RAG/SiYuan (60 %, sous la cible 80 %). **JEV reste
le décideur principal ; Laya est un accélérateur gratuit, pas un substitut.**

---

## 5. Couche 4 — Sécurité (Aegis)

| Domaine | Implémentation | Vérification |
|---|---|---|
| **ACL des secrets** | 4 `.env` en `Système(F) + Administrateurs(F) + searc(F)`, héritage coupé (`icacls /inheritance:r`), `CodexSandboxUsers` retirée | `icacls <fichier>` → **3 ACE (F), 0 (I)** sur les 4 fichiers (mesuré 27/09/2026) |
| **Secrets hors dépôt** | aucun `.env` suivi par git ; 12 sauvegardes rangées dans `%USERPROFILE%\hermes-secrets-backup\<profil>\` (arborescence miroir, ACL restreinte) | `git ls-files \| grep -E '\.env$'` → **0** ; `find hermes-secrets-backup -name '.env*'` → **12** |
| **Hygiène du dépôt** | `.gitignore` durci : `/hermes-agent/` **ancré**, `data/`, `bin/`, motif `*.bak_*` / `**/*.bak_*`, `profiles/*/skills/` | `git check-ignore -v <chemin>` nomme le motif ; 4 fichiers `.bak` sortis de l'index (conservés sur disque) |
| **Wazuh** | manager API `127.0.0.1:55085` (conteneur 55000), indexer `0.0.0.0:9200`, allowlist alignée | `curl -sk -X POST "https://localhost:55085/security/user/authenticate?raw=true"` → **200 + un jeton d'API** (préfixe `ey`) ; ports 55085 et 9200 en écoute |
| **Ports Windows** | aucune tentative de forcer un port réservé : remap au-dessus des plages exclues | `netsh int ipv4 show excludedportrange protocol=tcp` |
| **Audit d'historique** | `docs/scripts/scan_secrets_history.py` (tous les blobs) | dernier passage complet : **0 valeur réelle** ; contrôle avant publication : 0 occurrence sur les 9 motifs |

Le dépôt est **public** : un dépôt n'est pas un coffre. Tout ce qui entre reste dans l'historique,
y compris ce qui est supprimé ensuite — d'où la règle « rien de sensible ne rentre ».

### Limites connues et contournements

**Wazuh — plage de ports réservée par Windows.** Le manager publie son API sur `55000`, mais
Windows réserve des plages TCP à Hyper-V/WSL, dont **54985-55084** (mesuré :
`49552-49651`, `50000-50059`, `54885-54984`, `54985-55084`, `64630-64929`). `55000` tombe donc
dans une plage exclue : la pile Wazuh démarre en état `Created` au lieu de `Running` — plus
dégradée qu'avant le changement. Contournement retenu : **remap du port hôte juste au-dessus de la
plage exclue**, port interne inchangé, bind sur localhost :

```yaml
ports:
  - "127.0.0.1:1514:1514"
  - "127.0.0.1:1515:1515"
  - "127.0.0.1:514:514/udp"
  - "127.0.0.1:55085:55000"      # 55000 est dans 54985-55084 → publication sur 55085
```

Effets de bord à ne pas oublier : `data/security-monitoring/config.json` doit voir son `api_url`
**et** l'entrée correspondante de `ports.allowlist` alignées — sinon la surveillance s'alarme de sa
propre correction (« port ouvert non attendu »). Le dashboard, lui, joint l'API par le réseau
Docker (`https://wazuh.manager:55000`) : le remap hôte ne le concerne pas, ne pas y toucher.

**Autres limites assumées**

- `auto/best-free` est instable (502 côté fournisseurs) : il reste en repli 2, jamais en cible
  nominale ; le repli 1 est un modèle gratuit concret et autorisé par la clé du profil.
- `model.default` payant sur `default` / `docs-writer` : dérive surveillée, pas silencieuse.
- JEV non intégré au backend (appel explicite uniquement) et Laya non substituable (60 % d'accord).
- `%LOCALAPPDATA%\hermes\data\` (venvs, modèles, index RAG) et `hermes-agent\` (upstream) restent
  hors dépôt : une restauration complète exige de les reconstruire.

---

## 6. Bloqueurs de publication de la v1.4

| # | Bloqueur | État mesuré le 27/09/2026 |
|---|---|---|
| **B1** | **MP4 livrable absent** (ex-« tronqué ») | `Desktop\hermes tuto\tutotete20_jev_llmwiki.mp4` introuvable (dossier supprimé, corbeille vide, aucune copie ailleurs) → **réassemblage complet** requis |
| **B2** | **Watchdog volet6 en pause** | tâche Windows `volet6-watchdog` = `Disabled` ; cron Hermes `4a646bb6eab4` (`every 15m`) = `enabled: false`, `paused_at 2026-09-23T13:10:09+02:00` |

Tant que B1 et B2 sont ouverts, la 1.4 reste **préparée et non publiée** : aucun tag, aucune
release, et cette page ne doit pas être annoncée comme livrée. Voir
[`CHANGELOG-v1.4.md`](CHANGELOG-v1.4.md).

---

## 7. Comment vérifier cette architecture (commandes)

```bash
# Couche 1 — profils et isolation
hermes profile list                       # 4 profils ; un seul gateway multiplexé les sert
icacls "%LOCALAPPDATA%\hermes\.env"       # 3 ACE (F), 0 héritée

# Couche 2 — routage
curl -s -m 5 http://127.0.0.1:20128/v1/models | head -c 200     # OmniRoute
curl -s -m 5 http://127.0.0.1:20200/                            # proxy NIM

# Couche 3 — cerveau
curl -s -m 5 http://127.0.0.1:8200/sante                        # RAG + répartition par source
python wiki/scripts/jev_router.py --json "Qu'est-ce que le LLM Wiki ?"   # JEV (code 2 = repli local)
python skills/mlops/laya-onnx-windows/scripts/laya_onnx.py --self-test  # Laya

# Couche 4 — sécurité
git ls-files | grep -E '\.env$'           # attendu : vide
git check-ignore -v skills/autonomous-ai-agents/hermes-agent/SKILL.md   # attendu : vide (non ignoré)
netsh int ipv4 show excludedportrange protocol=tcp                       # plages réservées
```

---

*Document créé le 27/09/2026 pour la v1.4 « Hermes Aegis » (préparée, non publiée). Toutes les
valeurs de cette page sont mesurées sur la machine d'origine à cette date ; toute dérive ultérieure
doit être re-mesurée, pas présumée.*
