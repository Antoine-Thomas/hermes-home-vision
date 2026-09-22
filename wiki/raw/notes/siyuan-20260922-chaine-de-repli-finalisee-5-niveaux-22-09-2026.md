---
source_url: siyuan://20260921223640-38gbwri/20260922152700-125b409
ingested: 2026-09-22
sha256: c2ea227e6044f3ad015320ae57461f6397b44948280a3d1336c79f0b9e31dae2
---

# Chaine de repli finalisee 5 niveaux - 22-09-2026

---
title: Chaine de repli finalisee 5 niveaux - 22-09-2026
date: 2026-09-22T15:27:00+02:00
lastmod: 2026-09-22T15:27:00+02:00
---

# Chaine de repli finalisee 5 niveaux - 22-09-2026

# Chaîne de repli finalisée (5 niveaux) - 22-09-2026

## 1. Doublon retiré et 5e niveau ajouté

Avant : `Primary: auto/best-reasoning`​ **et** entrée 2 du fallback = `auto/best-reasoning` (doublon),  
chaîne de 3 entrées sans OpenRouter.

`hermes config set fallback_providers`​ (backup `config.yaml.bak.repair_20260922_151935`​) →  
​`hermes fallback list` relu :

    Primary:   auto/best-reasoning  (via omniroute)  
    Fallback chain (4 entries):  
      1. eco                 (via omniroute)  
      2. free-openrouter     (via omniroute)   <- NOUVEAU  
      3. nvidia-stack        (via omniroute)  
      4. deepseek-flash      (via deepseek)

Doublon supprimé : oui. `eco-fast`​ et `vision`​ **non touchés** (5 combos inchangés :  
​`eco`​ 3, `eco-fast`​ 8, `free-openrouter`​ 3, `nvidia-stack`​ 3, `vision`​ 1 membres, tous `priority`).

## 2. Tests mesurés (100 % pong)

|Étage|Commande|Résultat|Latence|
| ------------| ----------| -----------| ---------|
|Primaire|`hermes -z "…pong-primary"`|`pong-primary`|**46,9 s**|
|Fallback 1|`--provider omniroute -m eco`|`pong`|7,3 s|
|Fallback 2|`--provider omniroute -m free-openrouter`|`pong`|9,8 s|
|Fallback 3|`--provider omniroute -m nvidia-stack`|`pong`|23,2 s|
|Fallback 4|`--provider deepseek -m deepseek-flash`|`Pong! Je suis là. Que puis-je faire pour toi ?`|6,5 s|

Preuve `state.db`​ (`session_model_usage`) :

    1001 | 20260922_152405_0505f8 | auto/best-reasoning | custom   | api_call_count=1   <- primaire, 1 seul appel  
    1002 | 20260922_152458_9f3097 | eco                 | custom   | 1  
    1003 | 20260922_152505_677f21 | free-openrouter     | custom   | 1   <- le combo repond par son nom  
    1004 | 20260922_152515_cb78d9 | nvidia-stack        | custom   | 1  
    1005 | 20260922_152538_29f290 | deepseek-flash      | deepseek | 1

Variance a noter : le primaire `auto/best-reasoning`​ a servi 13,6 s (test precedent) puis **46,9 s**  
(ce test), toujours avec `api_call_count = 1`​ — donc c'est la variance de l'amont, pas une bascule de  
chaîne. Ne pas interpreter une latence haute comme un echec du primaire : lire `state.db` avant de  
conclure.

## 3. Mise a jour Hermes : NON effectuee (consentement requis)

La commande groupee (version + `hermes update --backup`​ + lancement en fond) a ete **bloquee** par  
l'approbation : `hermes update`​ est classe sensible et la fenetre de confirmation a expire sans  
reponse. Aucune mise a jour n'a ete lancee, **rien n'a ete modifie**, et je ne l'ai pas relancee  
(consigne : ne pas insister).

Etat reel mesure :

- Version en service : **v0.21.4 (2026.9.21)** , upstream `c7c2df1a`​, install method `git`​,  
  ​`hermes --version` affiche « Up to date ».
- **Ce « Up to date » est trompeur** : il se base sur la ref locale `origin/main`​ (jamais rafraichie  
  depuis l'install). `git ls-remote origin HEAD`​ (lecture seule, sans fetch) renvoie  
  ​**​`e2f8a0731bf26e95b31e35d73e71e183a1045b81`​**​ ≠ HEAD local `c7c2df1a536d62b45fda8907bb1898981721794d`​  
  (dernier commit local : `2026-09-21 18:24:39 +0000 fmt(js): npm run fix on merge (#118435)`​).  
  Il y a donc **au moins un commit en amont plus recent** a recuperer.
- Rollback disponible si besoin : `git reset --hard c7c2df1a`​ dans  
  ​`C:\Users\searc\AppData\Local\hermes\hermes-agent`​ + backups `config.yaml.bak.*`.

## 4. Automatismes intacts

- Crons : **9 total, 7 actifs, 2 en pause** — `Campagne SM (step)`​ [paused], `Relance candidatures Caen`​ [paused], `Relance fin de vacances`​, `Audit securite hebdomadaire`​, `Mémoire auto-consolidation`​, `OmniRoute découverte IA gratuites`​, `Monitoring vision gratuite OmniRoute`​,  
  ​`Consolidation legere skills (30j)`​, `omniroute-eco-autorefresh`.
- Gateway : tâche `Hermes_Gateway`​ enregistree, process **running (PID 24580)** .
- Profils : `veille`​ et `watch`​ intacts (gateway running, `nvidia-stack`).
- `.env` : 7/7 cles presentes (GROQ, GOOGLE, DEEPSEEK, OPENROUTER, OMNIROUTE, SIYUAN, XIAOMI) —  
  fichier jamais modifie.

## 5. Avertissement `hermes doctor` (a trancher)

    model.default 'auto/best-reasoning' is vendor-prefixed but model.provider is 'omniroute'.  
    Either set model.provider to 'openrouter', or drop the vendor prefix.

C'est un **faux positif** : `auto`​ n'est pas un vendeur, c'est l'alias de routeur interne d'OmniRoute,  
et la config fonctionne (mesuree 200, primaire reellement servi). Ne pas suivre la suggestion du  
doctor : passer `model.provider`​ a `openrouter`​ sortirait d'OmniRoute. Deuxieme point du doctor  
(« Run hermes setup to configure missing API keys ») est generique et deja couvert par `.env`.
