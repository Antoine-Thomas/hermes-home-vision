---
source_url: siyuan://20260921223640-38gbwri/20260922144715-utu0y2v
ingested: 2026-09-22
sha256: 06dd372f578da57b38622ccf7c87c5806187cd4e2e196b44a34844b43c41e646
---

# OpenRouter dans OmniRoute + combo free-openrouter - 22-09-2026

---
title: OpenRouter dans OmniRoute + combo free-openrouter - 22-09-2026
date: 2026-09-22T14:47:15+02:00
lastmod: 2026-09-22T14:47:15+02:00
---

# OpenRouter dans OmniRoute + combo free-openrouter - 22-09-2026

# OpenRouter dans OmniRoute + combo free-openrouter - 22-09-2026

## 1. Primaire Hermes : `auto/best-reasoning`

`hermes config set model.default auto/best-reasoning`​ (backup  
​`config.yaml.bak.avant_reasoning_20260922_143535`​). `hermes fallback list` :

    Primary:   auto/best-reasoning  (via omniroute)  
    Fallback chain (3 entries): 1. eco  2. auto/best-reasoning  3. deepseek-flash

Test `hermes -z "Réponds uniquement par: pong-reasoning"`​ -> `pong-reasoning`​ en **13,6 s**, et  
​`state.db`​ confirme que **le primaire a servi** : `session_model_usage`​ rowid **997**,  
​`model = auto/best-reasoning`​, `api_call_count = 1`​, `billing_base_url = http://127.0.0.1:20128/v1`​.  
(Contre 34,7 s pour le primaire mort `auto/best-free`​, qui etait facture `model = eco`.)

Note : l'entree 2 du fallback (`auto/best-reasoning`) fait doublon avec le primaire — inoffensif  
(couvre le cas ou le primaire echoue une fois), mais retirable si l'on veut 2 etages utiles.

## 2. Connexion OpenRouter creee dans OmniRoute

Schema reel (OpenAPI embarquee, `dist/docs/openapi.yaml`​) : `ProviderConnectionCreate`​ **exige**​**​`provider`​**​ **ET** **​`url`​**​ ; `apiKey`​, `name`​, `isActive`​, `maxConcurrent` sont optionnels.

    POST /api/providers  
    {"provider":"openrouter","name":"OpenRouter","url":"https://openrouter.ai/api/v1",  
     "apiKey":"<OPENROUTER_API_KEY de .env>","isActive":true}

-> **HTTP 201**, `id = bebc9056-0bdc-4099-99da-309eb18ad1d7`​. La reponse enveloppe l'objet dans  
​`{"connection": {...}}`​. `POST /api/providers/{id}/test`​ -> `{"valid": true, "latencyMs": 218}`​ :  
la cle `.env`​ est valide. `GET /api/providers/{id}/models`​ -> **444 modeles importes** (catalogue live  
OpenRouter, ids bruts type `xiaomi/mimo-v2.6-pro-ultraspeed`).

**Le prefixe de routage est le type de provider** : les modeles apparaissent dans `/v1/models`​ sous  
​`openrouter/<id upstream>`​ (ex. `openrouter/nvidia/nemotron-3-super-120b-a12b:free`​), avec des variantes  
de budget de raisonnement `-low`​ / `-medium`​. Comme pour le proxy NIM, OmniRoute resout le provider par  
le **prefixe du nom de modele**, pas par `providerId`.

## 3. Combo `free-openrouter`

`GET /api/combos`​ : 4 combos avant (`eco`​, `eco-fast`​, `nvidia-stack`​, `vision`​) ; backup ecrit dans  
​`C:\Users\searc\.omniroute\backups\combos_avant_free-openrouter_20260922_144642.json`.

Structure d'une entree (calquee sur `eco`​) :  
​`{"id":"<combo>-NN-<provider>-<modele avec /->-","kind":"model","model":"openrouter/<id>","providerId":"openrouter","weight":0}`​,  
combo `{"name":"free-openrouter","models":[...],"strategy":"priority","config":{...copie de eco...}}`​.  
​`POST /api/combos`​ -> **HTTP 201**. Membres poses :

|#|Modele|
| ---| --------|
|1|`openrouter/nvidia/nemotron-3-super-120b-a12b:free`|
|2|`openrouter/cohere/north-mini-code:free`|
|3|`openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`|

Test du combo **par son nom** (`{"model":"free-openrouter"}`​) : 2 tirs, **HTTP 200** les deux fois —  
amont `cohere/north-mini-code:free`​ (3,8 s) puis `nvidia/nemotron-3-super-120b-a12b:free` (1,0 s). Le  
combo resolue bien et les deux membres vivent.

## 4. Les 2 modeles demandes qui n'existent plus

Sur les 3 demandes, **2 n'existent plus en**  **​`:free`​** chez OpenRouter (erreur explicite d'OmniRoute) :

- `openrouter/qwen/qwen3-coder:free`​ -> `400 Model 'qwen/qwen3-coder:free' is not available in the active live catalog for provider 'openrouter'`​. Restent payants : `qwen/qwen3-coder-next`​,  
  ​`qwen/qwen3-coder-plus`​, `qwen/qwen3-coder-flash`​, `qwen/qwen3-coder-30b-a3b-instruct`.
- `openrouter/deepseek/deepseek-r1:free`​ -> meme `400`​. Restent : `deepseek/deepseek-r1`​,  
  ​`deepseek/deepseek-r1-0528`​, `deepseek/deepseek-r1-distill-llama-70b`.

Le catalogue live ne compte que **21 modeles**  **​`:free`​**. Remplacements retenus apres mesure :

|Modele teste|Resultat|
| --------------| -------------------------------------------------------|
|`nvidia/nemotron-3-super-120b-a12b:free`|**200** — 1,64 s|
|`cohere/north-mini-code:free`|**200** — 0,97 s|
|`nvidia/nemotron-3-ultra-550b-a55b:free`|**200** — 4,13 s|
|`z-ai/glm-5.2:free`|200 — 11,5 s (utilisable, lent)|
|`nvidia/nemotron-3.5-lightning:free`|200 — **116 s** (inutilisable : depasse tout timeout de tour)|
|`qwen/qwen3.8-27b:free`|**429** `All credentials for model ... are cooling down`|

## 5. Etat final

- Chaine Hermes inchangee par cette etape : `auto/best-reasoning`​ -> `eco`​ -> `auto/best-reasoning`​ ->  
  ​`deepseek-flash`​. `free-openrouter`​ **n'est pas encore** dans la chaine (demande non formulée).
- `eco`​, `eco-fast`​, `nvidia-stack`​, `vision` intacts ; 5 combos au total maintenant.
- `.env` non modifie (clé OpenRouter lue depuis le fichier, jamais passée en ligne de commande).
- Backup combos : `~/.omniroute/backups/combos_avant_free-openrouter_20260922_144642.json`.
